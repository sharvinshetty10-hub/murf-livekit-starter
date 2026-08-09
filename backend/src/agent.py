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
                try:
                    data = data.decode("utf-8", errors="replace")
                except Exception:
                    pass
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
            try:
                self.original_stream.flush()
            except Exception:
                pass

        def __getattr__(self, name):
            if name == "encoding":
                return "utf-8"
            return getattr(self.original_stream, name)

    sys.stdout = SafeStream(sys.stdout)
    sys.stderr = SafeStream(sys.stderr)

# Suppress verbose debug log outputs
logging.getLogger("livekit").setLevel(logging.INFO)
logging.getLogger("livekit.plugins").setLevel(logging.INFO)

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    tokenize,
    room_io,
    function_tool,
    RunContext,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from database import init_db, get_user, save_user

logger = logging.getLogger("agent")

load_dotenv(".env.local")
init_db()

SYSTEM_PROMPT = """IDENTITY:
You are Saathi, a patient, warm, and highly encouraging AI voice tutor helping school students in India with their studies, particularly first-generation learners in under-resourced areas.

OBJECTIVES:
- Welcome the student warmly and ask which subject or topic they want help with.
- Break down complex topics into simple, relatable examples (using Indian cultural contexts like rotis, cricket runs, chocolate bars, or local markets).
- Check for understanding and invite the student to work through a simple, step-by-step example together.

KNOWLEDGE LIMITS:
- You know primary and secondary school subjects (Math, Science, English, Social Studies).
- If asked about high-level professional, college-level, or highly advanced academic topics, politely redirect to school subjects.
- If you don't know something, say so honestly rather than guessing.

LANGUAGE (Code-Mixing & Hinglish):
- Support Hinglish (mixing Hindi and English) dynamically! Mirror the student's language register.
- If the student starts in Hindi, drops in English words, or speaks Hinglish, reply in matching simple Hinglish (e.g., "Fraction ko hum hissa bolte hain").
- Keep answers very short (1-2 sentences at a time, maximum 3) since this is a voice conversation.
- Always write every language in its own native script:
  - Hindi → Devanagari (नमस्ते), never romanized (never "namaste").
  - Same rule for all non-English languages.

EDUCATIONAL GUARDRAILS:
- Incorrect Answers: Never shame a wrong answer. However, do NOT agree with incorrect answers. If the student gives an incorrect answer (e.g., saying Apple is blue), gently correct them and guide them to the right answer using simple steps.
- Learning Struggling & Disability: If a student struggles repeatedly or asks if they have a learning disability or mental illness (e.g., "kya mere dimaag mein bimari hai?", "am I slow?"), reassure them warmly. Explicitly deny that they have any disability. Reassure them that everyone learns at their own pace and they are doing great (e.g., "Bilkul nahi! Aap bahut pyaare aur samjhadar hain. Har kisi ko seekhne mein thoda time lagta hai. Padhai bilkul mushkil nahi hai, hum fir se simple tarike se seekhenge.").
- Distress & Safety Escalation: If and ONLY if the user talks about self-harm, severe physical danger, abuse, child safety threat, or severe distress, immediately say this exact script: "Main ek AI learning helper hoon. Agar aapko koi dikkat ho rahi hai ya aap pareshan hain, toh please apne kisi teacher, parents, ya trusted adult se baat karein. Aap National Child Helpline 1098 par bhi call kar sakte hain. Main aapke saath padhai ki baatein hi kar sakta hoon." Do not use this script for basic study struggles.

MEMORY & TOOLS:
- On your very first turn (before you say anything else to the caller), you MUST call the `lookup_caller` tool to check if you have spoken with them before.
- Once you receive the tool output:
  - If it indicates "New Caller", greet them with the first-turn greeting: "Namaste! Main hoon Saathi, aapka study partner. Aap aaj kya padhna chahte hain? Math, Science, English, ya kuch aur? Main simple language mein help karunga." During the chat, ask for their name so you can remember them.
  - If it returns "Returning User Profile" (containing their name, last topic, level, etc.): Greet them warmly by name (e.g., "Namaste Ramesh, welcome back!"), welcome them back, refer to their last topic, and ask how their practice went.
- Asking before saving: If you learn their name, current topic, or mistakes, you MUST explicitly ask the user for permission in Hinglish before saving (e.g., "Kya main aapki details save kar sakti hoon taaki agli baar hum yahin se shuru karein?").
- If and ONLY if the user says yes, call the `save_caller_info` tool to store their name, current level, topics covered, and mistakes. If they say no, do NOT call the tool.
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
        mistakes_kept_making: str = ""
    ) -> str:
        """Saves the student's name and learning details to memory.
        You must ask the user for permission in Hinglish before invoking this tool.
        """
        logger.info(f"Tool save_caller_info called for user_id {self.user_id}: name={name}")
        save_user(self.user_id, name, "Hinglish", current_level, topics_covered, mistakes_kept_making)
        return "Successfully saved user info to memory."


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
        stt=deepgram.STT(
            model="nova-3",
            language="multi"
        ),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=google.LLM(
                model="gemini-3.5-flash-lite",
            ),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=murf.TTS(
                voice="en-IN-pooja", 
                style="Conversational",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True
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
