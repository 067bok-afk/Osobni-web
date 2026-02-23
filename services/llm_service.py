"""
AI Avatar - Integrace s Google Gemini
"""
import logging

import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL, FALLBACK_RESPONSE

logger = logging.getLogger(__name__)
from services.context_service import (
    build_core_prompt,
    COMPRESSION_PROMPT,
    format_conversation_for_compression,
    format_messages_for_llm,
)


def _get_simple_model():
    """Vrátí model pro kompresi (bez system instruction)."""
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel(GEMINI_MODEL)


def generate_response(
    user_message: str,
    conversation_history: list[dict],
    system_instruction: str | None = None,
) -> str:
    """
    Vygeneruje odpověď pomocí Gemini.
    Při chybě vrátí FALLBACK_RESPONSE.
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY není nastaven v .env")
        return FALLBACK_RESPONSE

    try:
        system_instruction = system_instruction or build_core_prompt()
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=system_instruction,
        )
        genai.configure(api_key=GEMINI_API_KEY)

        # Historie předchozích turnů (bez aktuálního dotazu)
        history = format_messages_for_llm(conversation_history)

        chat = model.start_chat(history=history)
        response = chat.send_message(
            user_message,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )

        return response.text.strip() if response.text else FALLBACK_RESPONSE

    except Exception as e:
        logger.exception("Gemini API chyba: %s", e)
        return FALLBACK_RESPONSE


def compress_conversation(messages: list[dict]) -> str:
    """
    Zkomprimuje část konverzace (odstraní balast, zachová fakta).
    Vrátí komprimovaný text nebo původní při chybě.
    """
    if not GEMINI_API_KEY or not messages:
        return format_conversation_for_compression(messages)

    try:
        model = _get_simple_model()
        conversation_text = format_conversation_for_compression(messages)
        prompt = COMPRESSION_PROMPT.format(conversation=conversation_text)

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=2048,
            ),
        )

        if response.text:
            return response.text.strip()
        return conversation_text

    except Exception:
        return format_conversation_for_compression(messages)
