"""
AI Avatar - Konfigurace aplikace
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Načtení .env ze složky projektu (nezávisle na CWD)
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# SEO – základní URL webu (pro sitemap, canonical; prázdné = odvozeno z requestu)
SITE_URL = os.getenv("SITE_URL", "").rstrip("/")

# Cesty k datovým souborům
DATA_DIR = BASE_DIR / "data"
MASTER_CV_PATH = DATA_DIR / "Master_CV.txt"
PERSONAL_DESCRIPTION_PATH = DATA_DIR / "Personal_Description.txt"

# API klíče
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# ElevenLabs
ELEVENLABS_VOICE_ID_CS = os.getenv("ELEVENLABS_VOICE_ID_CS", "")
ELEVENLABS_VOICE_ID_EN = os.getenv("ELEVENLABS_VOICE_ID_EN", "")

# LLM
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Limity kontextu
MAX_MESSAGES = 100
COMPRESSION_RATIO = 0.2  # 20 % nejstarších zpráv pro kompresi

# Fallback odpověď při chybě API
FALLBACK_RESPONSE = "Omlouvám se, momentálně jsem nedostupný."
