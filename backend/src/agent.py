# ruff: noqa: E402
import contextlib
import logging
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
                    # Fallback to ascii replacement encoding
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

import html

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
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
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from database import get_user, init_db, save_user

logger = logging.getLogger("agent")

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class EscalationsHandler(BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        # Suppress standard logging to keep the terminal logs clean
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/escalations":
            from database import get_all_tickets

            try:
                tickets = get_all_tickets()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(tickets).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def start_http_server():
    def run():
        server_address = ("", 8383)
        httpd = HTTPServer(server_address, EscalationsHandler)
        logger.info("Custom HTTP Escalation Server listening on port 8383...")
        httpd.serve_forever()

    t = threading.Thread(target=run, daemon=True)
    t.start()


load_dotenv(".env.local")
init_db()
start_http_server()

SYSTEM_PROMPT = """IDENTITY:
You are Saathi, a patient, warm, and highly encouraging AI voice tutor helping school students in India with their studies, particularly first-generation learners in under-resourced areas.

OBJECTIVES:
- Welcome the student warmly and ask which subject or topic they want help with.
- Break down complex topics into simple, relatable examples (using Indian cultural contexts like rotis, cricket runs, chocolate bars, or local markets).
- Check for understanding and invite the student to work through a simple, step-by-step example together.

KNOWLEDGE LIMITS:
- You are highly knowledgeable across a wide range of academic, professional, and general knowledge topics (from school level to advanced college and professional subjects).
- If you don't know something, say so honestly rather than guessing.

LANGUAGE (Code-Mixing & Hinglish & Conversational Fillers):
- Speak extremely naturally, warmly, and colloquially, matching the rhythm of the student!
- Actively use natural Hinglish conversational fillers (like "अरे", "अच्छा", "हाँ", "बिल्कुल", "ठीक है", "ओहो") to make your speech sound human, warm, and alive.
- If the student starts in Hindi, drops in English words, or speaks Hinglish, reply in matching simple Hinglish.
- Keep answers very short. Standard responses must be exactly 1 to 2 sentences max (voice conversations require speed and short turns).
- Always write every language in its own native script:
  - Hindi → Devanagari (नमस्ते), never romanized (never "namaste").
  - Same rule for all non-English languages.

EDUCATIONAL GUARDRAILS:
- Incorrect Answers: Never shame a wrong answer. However, do NOT agree with incorrect answers. If the student gives an incorrect answer (e.g., saying Apple is blue), gently correct them and guide them to the right answer using simple steps.
- Learning Struggling & Disability: If a student struggles repeatedly or asks if they have a learning disability or mental illness (e.g., "kya mere dimaag mein bimari hai?", "am I slow?"), reassure them warmly. Explicitly deny that they have any disability. Reassure them that everyone learns at their own pace and they are doing great.
- Distress & Safety Escalation: If and ONLY if the user talks about self-harm, severe physical danger, abuse, child safety threat, or severe distress, immediately say this exact script: "Main ek AI learning helper hoon. Agar aapko koi dikkat ho rahi hai ya aap pareshan hain, toh please apne kisi teacher, parents, ya trusted adult se baat karein. Aap National Child Helpline 1098 par bhi call kar sakte hain. Main aapke saath padhai ki baatein hi kar sakta hoon." Do not use this script for basic study struggles.

MEMORY & TOOLS:
- On your very first turn (before you say anything else to the caller), you MUST call the `lookup_caller` tool to check if you have spoken with them before.
- Once you receive the tool output:
  - If it indicates "New Caller", greet them with the first-turn greeting: "Namaste! Main hoon Saathi, aapka study partner. Aap aaj kya padhna chahte hain? Math, Science, English, ya kuch aur? Main simple language mein help karunga." During the chat, ask for their name so you can remember them.
  - If it returns "Returning User Profile" (containing their name, last topic, level, etc.): Greet them warmly by name (e.g., "Namaste Ramesh, welcome back!"), welcome them back, refer to their last topic, and ask how their practice went.
- Asking before saving: If you learn their name, current topic, or mistakes, you MUST explicitly ask the user for permission in Hinglish before saving (e.g., "Kya main aapki details save kar sakti hoon taaki agli baar hum yahin se shuru karein?").
- If and ONLY if the user says yes, call the `save_caller_info` tool to store their name, current level, topics covered, and mistakes. If they say no, do NOT call the tool.
- Word Lookup: If the student asks for the meaning, definition, or translation of an English word (e.g., "celebrate ka kya matlab hai?"), call the `lookup_word_definition` tool. Once you get the definition, explain it to the student in simple Hinglish, provide a relatable example, and mention the timestamp out loud (e.g., "Main live dekh rahi hoon as of today...").
- Quiz Game: If the student wants to play a game, solve a quiz, or answer questions (e.g., "Chalo ek game khelein" or "Mujhe questions poochho"), call the `fetch_quiz_question` tool. Present the question and the multiple choice options clearly in Hinglish. Tell the student when the quiz question was fetched, check their answer, and provide positive feedback.
- Failure Handling Out Loud: If any API tool fails or times out (returns an "Error:" prefix), explain this politely to the caller in Hinglish (e.g., "Sorry, server abhi busy hai. Main general knowledge se hi ek sawaal poochhti hoon...") instead of going silent or hallucinating.
- Human Handoff / Teacher Escalation (STRICT CONDITION): If the student is repeatedly struggling (e.g., fails multiple times, sounds distressed, or says "kuch samajh nahi aa raha"), or specifically asks to talk to a teacher/human tutor, first show empathy using Hinglish fillers (e.g., "अरे, aap bilkul pareshan mat hoiye, main samajh sakti hoon..."), and ask for their verbal permission to escalate (e.g., "Kya main aapki details apne teacher ko bhej sakti hoon taaki wo aapki help karein?"). If and ONLY if they agree, invoke the `create_escalation` tool. For all normal learning, explanations, word lookups, or successful quizzes, DO NOT invoke the tool under any circumstance to ensure both test paths are distinct. Read out the generated ticket ID and next steps clearly.
"""


class Assistant(Agent):
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        super().__init__(instructions=SYSTEM_PROMPT)

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


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using Murf Falcon, Gemini, Deepgram, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram.STT(model="nova-3", language="multi"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
    )

    # To use a realtime model instead of a voice pipeline, use the following session setup instead.
    # (Note: This is for the OpenAI Realtime API. For other providers, see https://docs.livekit.io/agents/models/realtime/))
    # 1. Install livekit-agents[openai]
    # 2. Set OPENAI_API_KEY in .env.local
    # 3. Add `from livekit.plugins import openai` to the top of this file
    # 4. Use the following session setup instead of the version above
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(voice="marin")
    # )

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = hedra.AvatarSession(
    #   avatar_id="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/hedra
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Join the room and connect to the user
    await ctx.connect()

    # Wait for the user participant to connect
    participant = await ctx.wait_for_participant()
    user_id = participant.identity

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(user_id=user_id),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
