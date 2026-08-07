import logging

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
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

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

EDUCATIONAL GUARDRAILS:
- Incorrect Answers: Never shame a wrong answer. However, do NOT agree with incorrect answers. If the student gives an incorrect answer (e.g., saying half is 3 parts out of 4), gently correct them and guide them to the right answer using simple steps (e.g., "Arre, half toh do barabar hisso mein se ek hota hai. 3 parts out of 4 toh three-fourths hoga na! Koi baat nahi, let's try again.").
- Learning Struggling & Disability: If a student struggles repeatedly or asks if they have a learning disability or mental illness (e.g., "kya mere dimaag mein bimari hai?", "am I slow?"), reassure them warmly. Explicitly deny that they have any disability. Reassure them that everyone learns at their own pace and they are doing great (e.g., "Bilkul nahi! Aap bahut pyaare aur samjhadar hain. Har kisi ko seekhne mein thoda time lagta hai. Padhai bilkul mushkil nahi hai, hum fir se simple tarike se seekhenge.").
- Distress & Safety Escalation: If and ONLY if the user talks about self-harm, severe physical danger, abuse, child safety threat, or severe distress, immediately say this exact script: "Main ek AI learning helper hoon. Agar aapko koi dikkat ho rahi hai ya aap pareshan hain, toh please apne kisi teacher, parents, ya trusted adult se baat karein. Aap National Child Helpline 1098 par bhi call kar sakte hain. Main aapke saath padhai ki baatein hi kar sakta hoon." Do not use this script for basic study struggles.

STYLE & GREETING:
- First-Turn Greeting: "Namaste! Main hoon Saathi, aapka study partner. Aap aaj kya padhna chahte hain? Math, Science, English, ya kuch aur? Main simple language mein help karunga."
"""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

    # To add tools, use the @function_tool decorator.
    # Here's an example that adds a simple weather tool.
    # You also have to add `from livekit.agents import function_tool, RunContext` to the top of this file
    # @function_tool
    # async def lookup_weather(self, context: RunContext, location: str):
    #     """Use this tool to look up current weather information in the given location.
    #
    #     If the location is not supported by the weather service, the tool will indicate this. You must tell the user the location's weather is unavailable.
    #
    #     Args:
    #         location: The location to look up weather information for (e.g. city name)
    #     """
    #
    #     logger.info(f"Looking up weather for {location}")
    #
    #     return "sunny with a temperature of 70 degrees."


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
            language="hi"
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
        turn_detection="vad",
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

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(),
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

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
