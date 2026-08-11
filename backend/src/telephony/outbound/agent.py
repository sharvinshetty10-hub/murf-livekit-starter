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
from dotenv import load_dotenv  # noqa: E402
from livekit import api, rtc  # noqa: E402
from livekit.agents import (  # noqa: E402
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    room_io,
    tokenize,
)
from livekit.plugins import (  # noqa: E402
    deepgram,
    google,
    murf,
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel  # noqa: E402

from database import get_user, init_db, save_user  # noqa: E402

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
- Welcoming them warmly: "Namaste! Main hoon Saathi. Aapke daily practice session ke liye maine aapko call kiya hai. Kya aapke paas 2 minute hain?"
- Break down complex topics into simple, relatable examples (using Indian cultural contexts like rotis, cricket runs, chocolate bars, or local markets).
- Check for understanding and invite the student to work through a simple, step-by-step example together.

KNOWLEDGE LIMITS:
- You know primary and secondary school subjects (Math, Science, English, Social Studies).
- If asked about high-level professional or advanced topics, politely redirect to school subjects.
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
  - If it indicates "New Caller", continue with the standard greeting: "Namaste! Main hoon Saathi, aapka study partner. Aap aaj kya padhna chahte hain?"
  - If it returns "Returning User Profile" (containing their name, last topic, level, etc.): Greet them warmly by name (e.g., "Namaste Ramesh! Yeh aapka daily practice session hai. Pichli baar humne {last_topic} padha tha na? Chalo aaj practice karein!").
- Asking before saving: If you learn their name, current topic, or mistakes, you MUST explicitly ask the user for permission in Hinglish before saving (e.g., "Kya main aapki details save kar sakti hoon taaki agli baar hum yahin se shuru karein?").
- If and ONLY if the user says yes, call the `save_caller_info` tool to store their name, current level, topics covered, and mistakes. If they say no, do NOT call the tool.
- Word Lookup: If the student asks for the meaning of a word, call the `lookup_word_definition` tool. Explain it in simple Hinglish and state the timestamp out loud.
- Quiz Game: If they want to play a game or answer questions, call the `fetch_quiz_question` tool. Present the question and choices in Devanagari Hinglish.
- Failure Handling Out Loud: If any API tool fails or times out (returns an "Error:" prefix), explain this politely to the caller in Hinglish instead of going silent.
- If the person asks for a human, use the transfer_to_human tool. If you reach a voicemail, use the detected_answering_machine tool. When the call is finished, use the end_call tool.
"""

# The first thing the person hears when they pick up.
GREETING = "Namaste! Main hoon Saathi. Aapke daily practice session ke liye maine aapko call kiya hai. Kya aapke paas 2 minute hain?"

# The identity LiveKit gives the person we call. Used to transfer them later.
CALLEE_IDENTITY = "phone-user"


class OutboundAgent(Agent):
    def __init__(self, ctx: JobContext, user_id: str) -> None:
        self.user_id = user_id
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

    # Start the session while the phone is still ringing so the models are warm
    # by the time somebody picks up.
    session_started = asyncio.create_task(
        session.start(
            agent=OutboundAgent(ctx, user_id=user_id),
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
