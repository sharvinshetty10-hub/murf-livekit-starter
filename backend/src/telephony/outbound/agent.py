# ruff: noqa: E402
"""Outbound telephony agent — places calls and talks to whoever answers.

Unlike the inbound agent, this one does the dialling. It waits to be dispatched
into a room with a phone number in the job metadata, then asks LiveKit to call
that number and bridge it into the room.

Run the worker with:

    uv run python src/telephony/outbound/agent.py dev

Then trigger a call from another terminal:

    uv run python src/telephony/outbound/dial.py --to +15551234567

See src/telephony/README.md for the trunk setup.
"""

import asyncio
import contextlib
import html
import json
import logging
import os
import sys

# Windows Unicode Terminal Encoding Safeguard to prevent UnicodeEncodeError in logs/console prints
if sys.platform == "win32":

    class SafeStream:
        def __init__(self, original_stream):
            self.original_stream = original_stream

        @property
        def encoding(self):
            return "utf-8"

        def write(self, data):
            if isinstance(data, bytes):
                with contextlib.suppress(Exception):
                    data = data.decode("utf-8", errors="replace")
            try:
                self.original_stream.write(data)
            except UnicodeEncodeError:
                try:
                    safe_data = data.encode("ascii", errors="replace").decode("ascii")
                    self.original_stream.write(safe_data)
                except Exception:
                    pass
            except Exception:
                pass

        def flush(self):
            with contextlib.suppress(Exception):
                self.original_stream.flush()

        def __getattr__(self, name):
            if name == "encoding":
                return "utf-8"
            return getattr(self.original_stream, name)

    sys.stdout = SafeStream(sys.stdout)
    sys.stderr = SafeStream(sys.stderr)


# Custom logging filter to convert Devanagari/Hindi Unicode characters to ASCII-safe placeholders
# in log records. This prevents console handlers from raising UnicodeEncodeError on Windows.
class SafeLoggingFilter(logging.Filter):
    def filter(self, record):
        try:
            if isinstance(record.msg, str):
                record.msg = record.msg.encode("ascii", errors="replace").decode(
                    "ascii"
                )
            if record.args:
                new_args = []
                for arg in record.args:
                    if isinstance(arg, str):
                        new_args.append(
                            arg.encode("ascii", errors="replace").decode("ascii")
                        )
                    elif isinstance(arg, dict):
                        import json

                        try:
                            str_repr = json.dumps(arg, ensure_ascii=True)
                            new_args.append(json.loads(str_repr))
                        except Exception:
                            new_args.append(arg)
                    else:
                        new_args.append(arg)
                record.args = tuple(new_args)
        except Exception:
            pass
        return True


# Register the logging filter
logging_filter = SafeLoggingFilter()
logging.getLogger().addFilter(logging_filter)
logging.getLogger("livekit").addFilter(logging_filter)
logging.getLogger("livekit.plugins").addFilter(logging_filter)

# Add src/ to sys.path so we can import database.py safely
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from dotenv import load_dotenv
from livekit import api, rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    ChatContext,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    room_io,
    tokenize,
)
from livekit.plugins import (
    deepgram,
    google,
    murf,
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from database import get_user, init_db, save_user

logger = logging.getLogger("outbound-agent")

load_dotenv(".env.local")

# Required — create this with `lk sip outbound create` (see src/telephony/README.md).
OUTBOUND_TRUNK_ID = os.getenv("LIVEKIT_SIP_OUTBOUND_TRUNK_ID")

# Optional — a phone number to transfer people to when they ask for a human.
TRANSFER_TO_NUMBER = os.getenv("TRANSFER_TO_NUMBER")

# Change this prompt to change what your outbound agent does.
SYSTEM_PROMPT = """IDENTITY:
You are Saathi, a patient, warm, and highly encouraging AI voice tutor helping school students in India with their studies. Today, you are placing an OUTBOUND call to the student for their daily practice review.

OBJECTIVES:
- Introduce yourself immediately and state that you are calling for their daily practice session. Be respectful of their time.
- Welcoming them warmly: "Namaste! Main hoon Saathi. Aapke daily practice session ke liye maine aapko call kiya hai. Agar aap is call ko abhi ya aage kabhi rokna chahte hain, toh bas 'Stop call' ya 'opt out' bol dijiye. Kya hum shuru karein?"
- Break down complex topics into simple, relatable examples (using Indian cultural contexts like rotis, cricket runs, chocolate bars, or local markets).
- Check for understanding and invite the student to work through a simple, step-by-step example together.

KNOWLEDGE LIMITS:
- You are highly knowledgeable across academic, professional, and general science/humanities topics.
- CRITICAL MATH RULE: You are strictly forbidden from answering or explaining ANY mathematics, arithmetic, geometry, calculus, algebra, linear algebra, fractions, equations, or numbers-related questions yourself. You MUST immediately explain that you are handing them off to the Maths Specialist and call the `transfer_to_maths` tool. Do not explain the math yourself.
- If you don't know something, say so honestly rather than guessing.

LANGUAGE (Code-Mixing & Hinglish):
- Support Hinglish (mixing Hindi and English) dynamically! Mirror the student's language register.
- Keep answers very short (1-2 sentences at a time, maximum 3) since this is a voice conversation.
- Always write every language in its own native script:
  - Hindi → Devanagari (नमस्ते), never romanized (never "namaste").
  - Same rule for all non-English languages.

EDUCATIONAL GUARDRAILS:
- Incorrect Answers: Never shame a wrong answer. Do not agree with incorrect answers. If the student gives an incorrect answer, gently correct them and guide them to the right answer.
- Learning Struggling & Disability: Reassure them warmly that everyone learns at their own pace.
- Distress & Safety Escalation: If the user talks about self-harm, severe danger, or distress, use the exact helpline script: "Main ek AI learning helper hoon. Agar aapko koi dikkat ho rahi hai ya aap pareshan hain, toh please apne kisi teacher, parents, ya trusted adult se baat karein. Aap National Child Helpline 1098 par bhi call kar sakte hain. Main aapke saath padhai ki baatein hi kar sakta hoon."

MEMORY & TOOLS:
- On your very first turn (before you say anything else to the caller), you MUST call the `lookup_caller` tool to check if you have spoken with them before.
- Once you receive the tool output:
  - If it indicates "New Caller", continue with the standard greeting: "Namaste! Main hoon Saathi, aapka study partner. Aap aaj kya padhna chahte hain?" On your very next turn, you MUST ask for their name (e.g., "Aapka naam kya hai?").
  - If it returns "Returning User Profile" (containing their name, last topic, level, etc.): Greet them warmly by name (e.g., "Namaste Ramesh! Yeh aapka daily practice session hai. Pichli baar humne {last_topic} padha tha na? Chalo aaj practice karein!").
- Asking before saving (CRITICAL RULE): The moment the user tells you their name, you MUST immediately ask for permission in Hinglish to save it (e.g., "Achha [Name], kya main aapki details save kar sakti hoon taaki agli baar hum yahin se shuru karein?"). You are strictly forbidden from teaching or answering other questions until you have asked for this permission.
- If and ONLY if the user says yes, call the `save_caller_info` tool to store their name, current level, topics covered, and mistakes. If they say no, do NOT call the tool.
- Word Lookup: If the student asks for the meaning of a word, call the `lookup_word_definition` tool. Explain it in simple Hinglish and state the timestamp out loud.
- Quiz Game: If they want to play a game or answer questions, call the `fetch_quiz_question` tool. Present the question and choices in Devanagari Hinglish.
- Failure Handling Out Loud: If any API tool fails or times out (returns an "Error:" prefix), explain this politely to the caller in Hinglish instead of going silent.
- If the person asks for a human, use the transfer_to_human tool. If you reach a voicemail, use the detected_answering_machine tool. When the call is finished, use the end_call tool.
- Human Handoff / Teacher Escalation (STRICT CONDITION): If the student is repeatedly struggling (e.g., fails multiple times, sounds distressed, or says "kuch samajh nahi aa raha"), or specifically asks to talk to a teacher/human tutor, first show empathy using Hinglish fillers (e.g., "अरे, aap bilkul pareshan mot hoiye, main samajh sakti hoon..."), and ask for their verbal permission to escalate (e.g., "Kya main aapki details apne teacher ko bhej sakti hoon taaki wo aapki help karein?"). If and ONLY if they agree, invoke the `create_escalation` tool. For all normal learning, explanations, word lookups, or successful quizzes, DO NOT invoke the tool under any circumstance to ensure both test paths are distinct. Read out the generated ticket ID and next steps clearly.
- Specialist Handoff (Maths): If the student explicitly asks to study mathematics, practice math, learn fractions, algebra, or solve math problems, you MUST announce the handoff in Hinglish (e.g., "Main aapko hamare Maths specialist se connect karti hoon. Ek second rukiye.") and call the `transfer_to_maths` tool immediately.
"""

# The first thing the person hears when they pick up.
GREETING = "Namaste! Main hoon Saathi. Aapke daily practice session ke liye maine aapko call kiya hai. Agar aap is call ko abhi ya aage kabhi rokna chahte hain, toh bas 'Stop call' ya 'opt out' bol dijiye. Kya hum shuru karein?"

# The identity LiveKit gives the person we call. Used to transfer them later.
CALLEE_IDENTITY = "phone-user"


MATH_PROMPT = """IDENTITY:
You are Samar, Saathi's specialized Math Tutor. You are patient, warm, and highly encouraging, focused exclusively on helping the student practice and master mathematics.

OBJECTIVES:
- Teach and practice mathematics concepts (like addition, division, fractions, geometry, algebra).
- Break down complex equations and math problems into simple, child-friendly Hinglish examples (like dividing rotis, sharing chocolate bars, or counting cricket runs).
- Check for understanding and solve problems step-by-step with the student.
- Greet them by saying you are taking over the session as the Maths Specialist.

KNOWLEDGE LIMITS:
- You ONLY handle math topics. If the student asks about language, history, general science, or other non-math subjects, gently guide them back to math (e.g., "Main aapka maths partner hoon, chalo maths ka ek question solve karein!").

LANGUAGE & SCRIPT:
- Support Hinglish (mixing Hindi and English) dynamically!
- Keep answers very short (1-2 sentences at a time).
- Always write every language in its own native script:
  - Hindi → Devanagari (नमस्ते), never romanized (never "namaste").
  - Same rule for all non-English languages.
"""


class MathSpecialist(Agent):
    def __init__(self, user_id: str, chat_ctx: ChatContext | None = None) -> None:
        self.user_id = user_id
        self.call_outcome = "Success"
        self.failure_reason = None
        super().__init__(
            instructions=MATH_PROMPT,
            chat_ctx=chat_ctx,
            tts=murf.TTS(
                voice="Samar",
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True,
            ),
        )

    async def on_enter(self) -> None:
        logger.info(f"MathSpecialist entered session for user_id: {self.user_id}")
        await self.session.generate_reply(
            instructions="Introduce yourself warmly in Devanagari Hinglish as the Maths Specialist (Samar) taking over, and ask what math topic they want to solve or practice today."
        )


class OutboundAgent(Agent):
    def __init__(self, ctx: JobContext, user_id: str) -> None:
        self.user_id = user_id
        self.call_outcome = "Failure"
        self.failure_reason = "Incomplete"
        super().__init__(instructions=SYSTEM_PROMPT)
        self.ctx = ctx

    @function_tool
    async def lookup_caller(self, context: RunContext) -> str:
        """Looks up the profile of the current caller.
        Always call this at the very beginning of the session.
        """
        logger.info(f"Tool lookup_caller called for user_id: {self.user_id}")
        user_data = get_user(self.user_id)
        if user_data:
            return f"Returning User Profile: name='{user_data['name']}', current_level='{user_data['current_level']}', topics_covered='{user_data['topics_covered']}', mistakes_kept_making='{user_data['mistakes_kept_making']}'"
        return "New Caller: No profile found."

    @function_tool
    async def transfer_to_maths(self, context: RunContext) -> tuple[Agent, str]:
        """Transfer the student to the Maths Specialist when they want to study mathematics, practice math, learn fractions, algebra, or solve math problems."""
        logger.info(f"Handoff triggered: transfer_to_maths for user_id: {self.user_id}")
        math_agent = MathSpecialist(
            user_id=self.user_id, chat_ctx=self.chat_ctx.copy(exclude_instructions=True)
        )
        return (
            math_agent,
            "Main aapko hamare Maths specialist se connect karti hoon. Ek second rukiye.",
        )

    @function_tool
    async def save_caller_info(
        self,
        context: RunContext,
        name: str,
        current_level: str = "Beginner",
        topics_covered: str = "",
        mistakes_kept_making: str = "",
    ) -> str:
        """Saves the student's name and learning details to memory.
        You must ask the user for permission in Hinglish before invoking this tool.
        """
        logger.info(
            f"Tool save_caller_info called for user_id {self.user_id}: name={name}"
        )
        save_user(
            self.user_id,
            name,
            "Hinglish",
            current_level,
            topics_covered,
            mistakes_kept_making,
        )
        return "Successfully saved user info to memory."

    @function_tool
    async def lookup_word_definition(self, context: RunContext, word: str) -> str:
        """Fetches the definition, part of speech, and an example sentence of an English word.
        Call this tool when the user asks for the meaning, definition, or explanation of a specific English word.

        Args:
            word: The English word to define (e.g. 'celebrate', 'gravity').
        """
        import json
        import urllib.parse
        import urllib.request
        from datetime import datetime

        logger.info(f"Looking up word definition for: '{word}'")
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}"
        timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            # 3 second timeout for quick response
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode("utf-8"))
                meanings = data[0]["meanings"]
                part_of_speech = meanings[0]["partOfSpeech"]
                definition = meanings[0]["definitions"][0]["definition"]

                # Try to get an example sentence
                example = meanings[0]["definitions"][0].get("example", "")
                example_str = f" Example sentence: '{example}'." if example else ""

                self.call_outcome = "Success"
                self.failure_reason = None
                return f"Word: '{word}' [{part_of_speech}]. Definition: {definition}.{example_str} (Fetched live as of {timestamp})"
        except urllib.error.HTTPError as he:
            if he.code == 404:
                return f"Error: The word '{word}' was not found in the dictionary. (Checked live as of {timestamp})"
            return f"Error: Failed to reach dictionary server (HTTP {he.code}). Please try again later. (Checked live as of {timestamp})"
        except Exception as e:
            logger.error(f"Error in lookup_word_definition: {e}")
            return f"Error: Dictionary lookup timed out or failed. Please check your internet connection. (Checked live as of {timestamp})"

    @function_tool
    async def fetch_quiz_question(self, context: RunContext) -> str:
        """Fetches a random primary-school level trivia question (General Knowledge / Science) with multiple choice options.
        Call this tool when the student says they want to play a game, solve a quiz, answer a question, or practice.
        """
        import json
        import urllib.request
        from datetime import datetime

        logger.info("Fetching quiz question...")
        url = "https://opentdb.com/api.php?amount=1&category=9&difficulty=easy&type=multiple"
        timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            # 3 second timeout
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode("utf-8"))
                if data["response_code"] == 0:
                    result = data["results"][0]
                    # Decode HTML entities in text
                    question = html.unescape(result["question"])
                    correct_answer = html.unescape(result["correct_answer"])
                    incorrect_answers = [
                        html.unescape(ans) for ans in result["incorrect_answers"]
                    ]

                    options = [*incorrect_answers, correct_answer]
                    import random

                    random.shuffle(options)

                    self.call_outcome = "Success"
                    self.failure_reason = None
                    return json.dumps(
                        {
                            "question": question,
                            "options": options,
                            "correct_answer": correct_answer,
                            "timestamp": f"Fetched live as of {timestamp}",
                        }
                    )
                return f"Error: Quiz server returned code {data['response_code']}. Please try again. (Checked as of {timestamp})"
        except Exception as e:
            logger.error(f"Error in fetch_quiz_question: {e}")
            return f"Error: Quiz server timed out or is temporarily unavailable. Please try again in a moment. (Checked as of {timestamp})"

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        reason: str,
        urgency: str = "Medium",
        follow_up_method: str = "Phone Call",
    ) -> str:
        """Create a human help request / ticket when the student is repeatedly struggling,
        needs a real teacher's help, or is frustrated.

        Before invoking this tool, you MUST explicitly ask the student for permission in Hinglish.

        Args:
            reason: The topic/reason why the student needs help (e.g. 'Struggling with Division').
            urgency: How urgent this request is ('Low', 'Medium', 'High'). Default is 'Medium'.
            follow_up_method: How the teacher should follow up (e.g. 'Phone Call').
        """
        import json
        import os
        import urllib.request
        from datetime import datetime

        from database import create_ticket, get_user

        logger.info(
            f"Tool create_escalation called for user_id {self.user_id}: reason={reason}"
        )

        self.call_outcome = "Failure"
        self.failure_reason = "Upset/Struggled"

        # Look up student's details
        name = "Unknown Student"
        topics_covered = ""
        user_data = get_user(self.user_id)
        if user_data:
            name = user_data.get("name", "Unknown Student")
            topics_covered = user_data.get("topics_covered", "")

        # Create ticket in local database
        ticket_id = create_ticket(
            self.user_id, name, reason, topics_covered, urgency, follow_up_method
        )

        # Discord Webhook Notification
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if webhook_url:
            embed_color = (
                16711680
                if urgency.lower() == "high"
                else (16776960 if urgency.lower() == "medium" else 65280)
            )
            payload = {
                "embeds": [
                    {
                        "title": "🚨 Human Escalation Triggered!",
                        "color": embed_color,
                        "fields": [
                            {"name": "Ticket ID", "value": ticket_id, "inline": True},
                            {"name": "Student Name", "value": name, "inline": True},
                            {"name": "Urgency", "value": urgency, "inline": True},
                            {"name": "Reason for Help", "value": reason},
                            {
                                "name": "Topics Covered",
                                "value": topics_covered or "None",
                            },
                            {
                                "name": "Follow-up Method",
                                "value": follow_up_method,
                                "inline": True,
                            },
                        ],
                        "timestamp": datetime.now().isoformat(),
                    }
                ]
            }
            try:
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0",
                    },
                )
                with urllib.request.urlopen(req, timeout=3) as res:
                    logger.info(
                        f"Escalation successfully posted to Discord! Status: {res.status}"
                    )
            except Exception as ex:
                logger.error(f"Failed to post escalation to Discord webhook: {ex}")

        return f"Escalation ticket created successfully. Reference Ticket ID is '{ticket_id}'."

    @function_tool
    async def transfer_to_human(self, context: RunContext) -> str:
        """Transfer the person to a human colleague.

        Use this when they explicitly ask for a person, or when you cannot help
        them with their request.
        """
        if not TRANSFER_TO_NUMBER:
            return "Transfers are not available on this line. Offer to have someone call back instead."

        # Tell them before transferring — the SIP transfer cuts off the audio.
        await context.session.generate_reply(
            instructions="Tell them you're connecting them to a colleague now."
        )

        logger.info("transferring call to %s", TRANSFER_TO_NUMBER)
        try:
            await self.ctx.api.sip.transfer_sip_participant(
                api.TransferSIPParticipantRequest(
                    room_name=self.ctx.room.name,
                    participant_identity=CALLEE_IDENTITY,
                    transfer_to=f"tel:{TRANSFER_TO_NUMBER}",
                    play_dialtone=True,
                )
            )
        except Exception:
            logger.exception("transfer failed")
            return "The transfer did not go through. Apologize and offer a call back."

        return "Transferred."

    @function_tool
    async def detected_answering_machine(self, context: RunContext) -> str:
        """Hang up because the call reached a voicemail or answering machine.

        Use this as soon as you hear a recorded greeting rather than a live person.
        """
        logger.info("answering machine detected — hanging up")
        await self._hangup()
        return "Call ended."

    @function_tool
    async def end_call(self, context: RunContext) -> str:
        """Hang up the call.

        Use this once the conversation is finished and you have said goodbye.
        """
        await context.session.generate_reply(
            instructions="Thank them for their time and say a short goodbye."
        )

        logger.info("ending call")
        await self._hangup()
        return "Call ended."

    async def _hangup(self) -> None:
        """Delete the room, which drops the SIP leg and ends the phone call."""
        await self.ctx.api.room.delete_room(
            api.DeleteRoomRequest(room=self.ctx.room.name)
        )


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


def parse_metadata(ctx: JobContext) -> tuple[str | None, str]:
    """Read the number to dial and the user_id out of the dispatch metadata."""
    metadata = ctx.job.metadata
    if not metadata:
        return None, ""
    try:
        data = json.loads(metadata)
        return data.get("phone_number"), data.get("user_id", "")
    except json.JSONDecodeError:
        # Allow a bare phone number as metadata too, for quick tests.
        return metadata.strip() or None, ""


@server.rtc_session(agent_name="outbound-agent")
async def outbound_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    phone_number, user_id = parse_metadata(ctx)
    if not phone_number:
        logger.error(
            "no phone number in job metadata — dispatch with "
            '{"phone_number": "+15551234567"}'
        )
        ctx.shutdown()
        return

    if not OUTBOUND_TRUNK_ID:
        logger.error("LIVEKIT_SIP_OUTBOUND_TRUNK_ID is not set — cannot place calls")
        ctx.shutdown()
        return

    await ctx.connect()

    # Same voice pipeline as src/agent.py — see that file for the annotated version.
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    # Create OutboundAgent instance
    agent_instance = OutboundAgent(ctx, user_id=user_id)

    from datetime import datetime

    from database import create_call_record, get_user, update_call_outcome

    start_time = datetime.now()
    call_id = ctx.room.name

    # Try to resolve user's name if they have a profile already
    user_profile = get_user(user_id)
    name = user_profile.get("name", "New Learner") if user_profile else "New Learner"

    # Log call start
    create_call_record(call_id, user_id, name, "SIP")

    # Register shutdown callback
    async def on_shutdown():
        # Retrieve latest user profile again (in case they saved their name during the call)
        up = get_user(user_id)
        latest_name = up.get("name", name) if up else name

        # Calculate duration
        duration = int((datetime.now() - start_time).total_seconds())

        # Read final stats from agent_instance
        outcome = agent_instance.call_outcome
        failure_reason = agent_instance.failure_reason

        # Update name in database just in case they added a name
        from database import get_db_connection

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE calls SET name = ? WHERE call_id = ?", (latest_name, call_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating call name in db: {e}")

        # Log outcome
        update_call_outcome(call_id, outcome, duration, failure_reason)
        logger.info(
            f"Session closed: call_id={call_id}, user={latest_name}, duration={duration}s, outcome={outcome}, reason={failure_reason}"
        )

    ctx.add_shutdown_callback(on_shutdown)

    # Start the session while the phone is still ringing so the models are warm
    # by the time somebody picks up.
    session_started = asyncio.create_task(
        session.start(
            agent=agent_instance,
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    # BVCTelephony is tuned for the narrow frequency range of phone audio.
                    noise_cancellation=lambda params: (
                        noise_cancellation.BVCTelephony()
                        if params.participant.kind
                        == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                        else noise_cancellation.BVC()
                    ),
                ),
            ),
        )
    )

    logger.info("dialing %s", phone_number)
    try:
        # wait_until_answered means this returns once the call connects — if the
        # number is busy, declines, or never answers, it raises instead.
        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=OUTBOUND_TRUNK_ID,
                sip_call_to=phone_number,
                participant_identity=CALLEE_IDENTITY,
                participant_name="Phone user",
                wait_until_answered=True,
            )
        )
    except api.TwirpError as e:
        logger.error(
            "call to %s was not answered: %s (%s)",
            phone_number,
            e.message,
            e.metadata.get("sip_status"),
        )
        session_started.cancel()
        ctx.shutdown()
        return

    await session_started

    # Speak first — they just picked up an unexpected call and won't say anything.
    await session.say(GREETING, allow_interruptions=True)


if __name__ == "__main__":
    init_db()  # Ensure database schema is initialized
    cli.run_app(server)
