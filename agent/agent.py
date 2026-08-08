"""Flujo minimo de Pipecat para probar interaccion por voz en tiempo real.

Transporte: WebRTC nativo (aiortc), sin dependencia de daily-python
(que no publica wheels para Windows). Se sirve un cliente web local
para hablar con el bot desde el navegador.

Pipeline: WebRTC (audio in) -> Deepgram (STT) -> Gemini (LLM) -> Cartesia (TTS) -> WebRTC (audio out).

Uso:
    python bot.py
    # abre http://localhost:7860 en el navegador
"""

import logging
import os

from dotenv import load_dotenv
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.google.llm import GoogleLLMService
from pipecat.transcriptions.language import Language
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.workers.runner import WorkerRunner

from agent.rag.tool import knowledge_base_tool

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Eres Larry, un asistente de voz que conversa siempre en espanol. "
    "Tus respuestas se convierten a audio, asi que evita emojis, markdown o "
    "cualquier formato que no se pueda hablar. Responde de forma breve, clara "
    "y natural, como en una conversacion hablada, siempre en espanol. "
    "Cuando el usuario pregunte sobre cuidados, sintomas o indicaciones post "
    "operatorias, usa la herramienta buscar_en_base_de_conocimiento antes de "
    "responder en vez de inventar informacion."
)

transport_params = {
    "webrtc": lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
    ),
}


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info("Starting bot")

    stt = DeepgramSTTService(
        api_key=os.environ["DEEPGRAM_API_KEY"],
        settings=DeepgramSTTService.Settings(
            model="nova-2-general",
            language=Language.ES,
        ),
    )

    tts = CartesiaTTSService(
        api_key=os.environ["CARTESIA_API_KEY"],
        settings=CartesiaTTSService.Settings(
            voice=os.environ["CARTESIA_VOICE_ID"],
            language=Language.ES,
        ),
    )

    llm = GoogleLLMService(
        api_key=os.environ["GOOGLE_API_KEY"],
        settings=GoogleLLMService.Settings(
            model="gemini-3.6-flash",
            system_instruction=SYSTEM_PROMPT,
        ),
    )

    context = LLMContext(tools=[knowledge_base_tool])
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        idle_timeout_secs=runner_args.pipeline_idle_timeout_secs,
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")
        context.add_message(
            {"role": "developer", "content": "Saluda al usuario y pregunta en que puedes ayudarlo."}
        )
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await worker.cancel()

    runner = WorkerRunner(handle_sigint=runner_args.handle_sigint)

    await runner.add_workers(worker)
    await runner.run()


async def bot(runner_args: RunnerArguments):
    """Punto de entrada del bot (compatible con Pipecat Cloud)."""
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
