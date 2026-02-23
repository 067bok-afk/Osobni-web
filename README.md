# AI Avatar – Interaktivní mluvící životopis

AI avatar slouží jako interaktivní, mluvící CV. Odpovídá výhradně na základě informací ze zdrojů pravdy (`Master_CV.txt` a `Personal_Description.txt`).

## Požadavky

- Python 3.10+
- API klíče: Google Gemini, ElevenLabs

## Instalace

### 1. Vytvoření virtuálního prostředí

```powershell
cd "p:\AI - cursor\PROJEKT_AI AVATAR"
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Instalace závislostí

```powershell
pip install -r requirements.txt
```

### 3. Konfigurace

Zkopírujte `.env.example` do `.env` a vyplňte klíče:

```powershell
copy .env.example .env
```

Upravte `.env`:

```
GEMINI_API_KEY=váš_gemini_klíč
ELEVENLABS_API_KEY=váš_elevenlabs_klíč
ELEVENLABS_VOICE_ID_CS=id_českého_hlasu
ELEVENLABS_VOICE_ID_EN=id_anglického_hlasu
```

**Získání Voice ID:** ElevenLabs dashboard → Voices → vyberte hlas → zkopírujte Voice ID.

### 4. Obsah zdrojů pravdy

Upravte soubory v `data/`:

- `data/Master_CV.txt` – strukturované CV
- `data/Personal_Description.txt` – osobní a profesní popis

## Spuštění

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Otevřete v prohlížeči: **http://localhost:8000**

## API Endpointy

| Metoda | Endpoint | Popis |
|--------|----------|-------|
| POST | `/api/chat` | Odeslání dotazu, vrací odpověď |
| POST | `/api/audio` | Generuje TTS pro daný text |
| POST | `/api/reset` | Vymaže paměť seance |

## Architektura

- **Core prompt:** Statický systémový prompt s obsahem Master_CV + Personal_Description
- **Short-Term Memory:** Historie konverzace (max 100 zpráv)
- **Komprese:** Při dosažení limitu se nejstarších 20 % zpráv zkomprimuje (odstraní balast, zachová fakta)
- **Fallback:** Při chybě API se vrátí: „Omlouvám se, momentálně jsem nedostupný.“

## Struktura projektu

```
PROJEKT_AI AVATAR/
├── data/
│   ├── Master_CV.txt
│   └── Personal_Description.txt
├── services/
│   ├── context_service.py
│   ├── llm_service.py
│   └── tts_service.py
├── static/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── config.py
├── main.py
├── requirements.txt
└── .env
```
