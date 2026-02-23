"""
AI Avatar - Hlavní FastAPI aplikace
"""
import json
import logging
import uuid

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from langdetect import detect, LangDetectException
from pathlib import Path

from fastapi.responses import FileResponse, Response, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import BASE_DIR, FALLBACK_RESPONSE, MAX_MESSAGES, SITE_URL

# Načtení textů z texts.json
TEXTS_JSON_PATH = BASE_DIR / "texts.json"
TEXTS_DATA: dict = {}


def _load_texts() -> None:
    """Načte texts.json do paměti při startu."""
    global TEXTS_DATA
    if TEXTS_JSON_PATH.exists():
        TEXTS_DATA = json.loads(TEXTS_JSON_PATH.read_text(encoding="utf-8"))
    else:
        TEXTS_DATA = {"cs": {}, "en": {}}
from services.context_service import (
    build_core_prompt,
    get_messages_to_compress,
    format_conversation_for_compression,
)
from services.llm_service import generate_response, compress_conversation
from services.tts_service import generate_speech

# Odpověď pro nepodporované jazyky (SK, DE, ...)
UNSUPPORTED_LANG_RESPONSE = "I am sorry, can you please speak in Czech or English?"

# In-memory session storage (efemérní - reset při restartu serveru)
# sessions[session_id] = {"messages": [...], "conversation_lang": "cs"|"en"|None}
sessions: dict[str, dict] = {}


def _get_or_create_session(session_id: str | None) -> str:
    """Vrátí session_id, vytvoří novou seanci pokud chybí."""
    if not session_id:
        session_id = str(uuid.uuid4())
    if session_id not in sessions:
        sessions[session_id] = {"messages": [], "conversation_lang": None}
    return session_id


def _compress_if_needed(session_id: str) -> None:
    """Provede kompresi konverzace při dosažení limitu zpráv."""
    messages = sessions[session_id]["messages"]
    if len(messages) < MAX_MESSAGES:
        return

    to_compress, remaining = get_messages_to_compress(messages)
    compressed_text = compress_conversation(to_compress)

    # Komprimovaný blok nahradíme jedinou syntetickou zprávou
    # Formát: "Kontext předchozí konverzace:\n{compressed}"
    context_message = {
        "role": "user",
        "content": f"[Předchozí kontext konverzace]\n{compressed_text}",
    }

    sessions[session_id]["messages"] = [context_message] + remaining


TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle: načtení Core promptu a texts.json při startu."""
    _load_texts()
    build_core_prompt()
    yield
    sessions.clear()


app = FastAPI(
    title="AI Avatar",
    description="Interaktivní mluvící životopis",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None
    text_only: bool = Field(default=False, description="Pouze text, bez TTS")
    page_lang: str | None = Field(default=None, description="Jazyk stránky: 'cs' | 'en' – fallback pro krátké zprávy")
    force_lang: str | None = Field(default=None, description="Ruční přepnutí jazyka: 'cs' | 'en' – přepíše conversation_lang")


class ChatResponse(BaseModel):
    response: str
    session_id: str
    audio_available: bool
    unsupported_lang_audio: bool = Field(
        default=False, description="True = přehrát přednahranou hlášku pro nepodporovaný jazyk"
    )


def _detect_user_language(text: str) -> str:
    """
    Detekuje jazyk zprávy. Vrátí 'cs', 'en' nebo 'other'.
    Pro krátké zprávy (< 5 znaků) vrací 'other' – fallback na page_lang v _resolve_conversation_lang.
    """
    text = (text or "").strip()
    if len(text) < 5:
        return "other"
    try:
        detected = detect(text)
        if detected == "cs":
            return "cs"
        if detected == "en":
            return "en"
        return "other"
    except LangDetectException:
        return "other"


def _resolve_conversation_lang(
    session_id: str,
    detected: str,
    message: str,
    page_lang: str | None,
    force_lang: str | None,
) -> str:
    """
    Určí jazyk konverzace. Závazný jazyk se nastaví při první zprávě a drží se do zavření chatu.
    Krátká zpráva (< 5 znaků): fallback na page_lang.
    """
    sess = sessions[session_id]
    if force_lang in ("cs", "en"):
        sess["conversation_lang"] = force_lang
        return force_lang

    if sess["conversation_lang"] is not None:
        return sess["conversation_lang"]

    # První zpráva – detekce nebo fallback
    if detected in ("cs", "en"):
        sess["conversation_lang"] = detected
        return detected
    if len((message or "").strip()) < 5:
        fallback = page_lang if page_lang in ("cs", "en") else "en"
        sess["conversation_lang"] = fallback
        return fallback
    return "other"


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Zpracuje dotaz, vrátí odpověď a případně audio."""
    session_id = _get_or_create_session(request.session_id)
    sess = sessions[session_id]
    messages = sess["messages"]

    detected = _detect_user_language(request.message)
    user_lang = _resolve_conversation_lang(
        session_id, detected, request.message, request.page_lang, request.force_lang
    )

    if user_lang == "other":
        return ChatResponse(
            response=UNSUPPORTED_LANG_RESPONSE,
            session_id=session_id,
            audio_available=False,
            unsupported_lang_audio=True,
        )

    # Přidáme dotaz do historie
    messages.append({"role": "user", "content": request.message})

    # Komprese před voláním LLM (pokud jsme přes limit)
    _compress_if_needed(session_id)

    # Generování odpovědi s explicitní jazykovou instrukcí
    core_prompt = build_core_prompt(language=user_lang)
    response_text = generate_response(
        user_message=request.message,
        conversation_history=messages[:-1],
        system_instruction=core_prompt,
    )

    # Přidáme odpověď do historie
    messages.append({"role": "model", "content": response_text})

    audio_available = False
    if not request.text_only and response_text != FALLBACK_RESPONSE:
        audio_available = generate_speech(response_text, language=user_lang) is not None

    return ChatResponse(
        response=response_text,
        session_id=session_id,
        audio_available=audio_available,
    )


UNSUPPORTED_LANG_AUDIO_PATH = BASE_DIR / "static" / "audio" / "unsupported-lang.mp3"


@app.get("/api/audio")
def get_audio(text: str, language: str | None = None):
    """Vygeneruje a vrátí audio pro daný text."""
    if not text or len(text) > 5000:
        raise HTTPException(status_code=400, detail="Neplatný text")
    audio_bytes = generate_speech(text, language=language or "en")
    if not audio_bytes:
        raise HTTPException(status_code=503, detail="TTS nedostupný")
    return Response(content=audio_bytes, media_type="audio/mpeg")


@app.get("/api/audio/unsupported-lang")
def get_unsupported_lang_audio():
    """Vrátí přednahranou hlášku pro nepodporované jazyky (anglický hlas)."""
    if UNSUPPORTED_LANG_AUDIO_PATH.exists():
        return FileResponse(str(UNSUPPORTED_LANG_AUDIO_PATH), media_type="audio/mpeg")
    # Fallback: vygenerovat on-the-fly
    audio_bytes = generate_speech(UNSUPPORTED_LANG_RESPONSE, language="en")
    if audio_bytes:
        return Response(content=audio_bytes, media_type="audio/mpeg")
    raise HTTPException(status_code=503, detail="Audio nedostupné")


class ResetRequest(BaseModel):
    session_id: str


@app.post("/api/reset")
def reset_session(request: ResetRequest):
    """Vymaže Short-Term Memory a conversation_lang pro danou seanci."""
    session_id = request.session_id
    if session_id in sessions:
        sessions[session_id] = {"messages": [], "conversation_lang": None}
    return {"status": "ok", "session_id": session_id}


STATIC_DIR = BASE_DIR / "static"


def _get_base_url(request: Request) -> str:
    """Vrátí základní URL webu (pro canonical, hreflang, og:image)."""
    if SITE_URL:
        return SITE_URL
    return str(request.base_url).rstrip("/")


@app.get("/")
def index(request: Request):
    """Serves the frontend (CV stránka s AI chatem) – česká verze."""
    if not TEXTS_DATA:
        _load_texts()
    t = TEXTS_DATA.get("cs") or TEXTS_DATA.get("en") or {}
    base_url = _get_base_url(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"t": t, "lang": "cs", "base_url": base_url},
    )


@app.get("/en")
def index_en(request: Request):
    """Serves the English version of the frontend."""
    if not TEXTS_DATA:
        _load_texts()
    t = TEXTS_DATA.get("en") or TEXTS_DATA.get("cs") or {}
    base_url = _get_base_url(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"t": t, "lang": "en", "base_url": base_url},
    )


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt(request: Request):
    """Serves robots.txt for crawlers."""
    base_url = _get_base_url(request)
    return f"""User-agent: *
Allow: /
Disallow: /api/

Sitemap: {base_url}/sitemap.xml
"""


@app.get("/sitemap.xml", response_class=Response)
def sitemap_xml(request: Request):
    """Serves sitemap.xml for search engines."""
    base_url = _get_base_url(request)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
    <loc>{base_url}/</loc>
    <xhtml:link rel="alternate" hreflang="cs" href="{base_url}/"/>
    <xhtml:link rel="alternate" hreflang="en" href="{base_url}/en"/>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>{base_url}/en</loc>
    <xhtml:link rel="alternate" hreflang="cs" href="{base_url}/"/>
    <xhtml:link rel="alternate" hreflang="en" href="{base_url}/en"/>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
"""
    return Response(content=xml, media_type="application/xml")


@app.get("/Borek.png")
def serve_borek_image():
    """Serves hero image if exists."""
    img = BASE_DIR / "Borek.png"
    if img.exists():
        return FileResponse(str(img), media_type="image/png")
    raise HTTPException(status_code=404, detail="Obrázek nenalezen")


# Statické soubory (HTML, JS, CSS)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
