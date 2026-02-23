"""
Skript pro vygenerování přednahrané hlášky pro nepodporované jazyky.
Spusť jednou: python scripts/generate_unsupported_audio.py
"""
import sys
from pathlib import Path

# Přidání kořene projektu do path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services.tts_service import generate_speech

UNSUPPORTED_TEXT = "I am sorry, can you please speak in Czech or English?"
OUTPUT_PATH = ROOT / "static" / "audio" / "unsupported-lang.mp3"


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print("Generuji audio...")
    audio = generate_speech(UNSUPPORTED_TEXT, language="en")
    if not audio:
        print("CHYBA: TTS nedostupný. Zkontroluj ELEVENLABS_API_KEY v .env")
        sys.exit(1)
    OUTPUT_PATH.write_bytes(audio)
    print(f"OK: Uloženo do {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
