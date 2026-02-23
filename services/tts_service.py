"""
AI Avatar - Integrace s ElevenLabs TTS
"""
import logging

from elevenlabs.client import ElevenLabs
from elevenlabs.types import VoiceSettings

from config import (
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID_CS,
    ELEVENLABS_VOICE_ID_EN,
)


def _detect_language(text: str) -> str:
    """Jednoduchá heuristika: převaha českých znaků = čeština."""
    cs_chars = sum(1 for c in text if c in "ěščřžýáíéúůďťň")
    return "cs" if cs_chars > 2 else "en"


def generate_speech(text: str, language: str | None = None) -> bytes | None:
    """
    Vygeneruje audio přes ElevenLabs.
    Vrátí bytes audio nebo None při chybě.
    """
    if not ELEVENLABS_API_KEY:
        logging.warning("TTS: ELEVENLABS_API_KEY není nastaven")
        return None

    lang = language or _detect_language(text)
    voice_id = ELEVENLABS_VOICE_ID_CS if lang == "cs" else ELEVENLABS_VOICE_ID_EN

    if not voice_id:
        voice_id = ELEVENLABS_VOICE_ID_CS or ELEVENLABS_VOICE_ID_EN

    if not voice_id:
        logging.warning("TTS: žádný voice_id (ELEVENLABS_VOICE_ID_CS/EN)")
        return None

    # Nižší stability = živější, energičtější hlas (méně monotónní/utahaný)
    voice_settings = VoiceSettings(
        stability=0.35 if lang == "cs" else 0.5,
        similarity_boost=0.75,
    )
    try:
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        audio_stream = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            voice_settings=voice_settings,
        )
        result = b"".join(audio_stream)
        logging.info("TTS: OK, %d bytes", len(result))
        return result
    except Exception as e:
        logging.error("TTS chyba: %s", e)
        return None
