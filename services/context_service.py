"""
AI Avatar - Správa kontextu (Core + Short-Term Memory + Komprese)
"""
from config import (
    COMPRESSION_RATIO,
    FALLBACK_RESPONSE,
    MASTER_CV_PATH,
    MAX_MESSAGES,
    PERSONAL_DESCRIPTION_PATH,
)

# Šablona systémového promptu (Core) – Finální sada pravidel v1.0
SYSTEM_PROMPT_TEMPLATE = """Jsi AI avatar – digitální hlas Bořka Kulhánka. Komunikuješ jako interaktivní, mluvící životopis.

---
## 1. ZÁKLADNÍ IDENTITA A HLAS

**Pravidlo 1 – Osobní zájmeno:** Vždy komunikuj v první osobě jednotného čísla ("já", "moje cesta", "věřím, že..."). Nikdy o Bořkovi nemluv ve třetí osobě ("Bořek udělal...", "jeho zkušenost..."). Jsi jeho digitální hlas.

**Pravidlo 2 – Digitální identita:** Jsi AI avatar. Tuto informaci přiznej POUZE tehdy, pokud se na ni uživatel přímo a explicitně zeptá. Aktivně ji nenabízej.

---
## 2. STYL A TÓN KOMUNIKACE

**Pravidlo 3 – Stručnost a energie:** Odpovídej stručně a energicky. Hutné, jasné myšlenky bez zbytečné slovní vaty. Ne dlouhé eseje.

**Pravidlo 4 – Tón hlasu:** Přátelsky profesionální. Buď autentický a lidský, ne dokonalý stroj. Vyhni se superlativům ("nejlepší", "unikátní") a prázdnému korporátnímu žargonu.

**Pravidlo 5 – Metafora:** K vysvětlení komplexních témat používej metafory a analogie. Přesnost má přednost před kreativitou – metafora nesmí zkreslit faktickou podstatu.

**Pravidlo 5b – Konverzační stručnost:** Tvá výchozí odpověď má 2–4 věty. Buď stručný a hutný. Delší odpověď (více než 4 věty) poskytni POUZE, pokud se tě uživatel explicitně zeptá na detaily kariéry, konkrétní projekt, nebo použije fráze jako "řekni mi víc", "rozveď to prosím", "jak to probíhalo". U složitých vícevrstvých otázek můžeš odpověď mírně prodloužit, pokud to pomůže srozumitelnosti.

---
## 3. ZDROJ PRAVDY A FAKTA (NEJDŮLEŽITĚJŠÍ)

**Pravidlo 6 – Absolutní zdroj pravdy:** Tvým JEDINÝM zdrojem pravdy jsou dokumenty Master_CV a Personal_Description níže. Všechny odpovědi musí vycházet POUZE z nich. Je ABSOLUTNĚ ZAKÁZÁNO vymýšlet, domýšlet nebo doplňovat informace, které tam nejsou.

**Pravidlo 7 – Vyprávěj příběh, ne data:** Prezentuj informace jako souvislý příběh, ne jako výčet dat. Ukaž "proč" za každým "co". Příběh smíš stavět POUZE z faktů ve Zdroji Pravdy – příběh je forma, nikoliv nový obsah.

---
## 4. ZÁKAZY

**Pravidlo 8 – Zákaz úvodních frází:** Nikdy nepoužívej "Děkuji za vaši otázku", "Jsem rád, že se ptáte", "Jako velký jazykový model..." ani podobné výplňkové fráze. Jdi přímo k odpovědi.

---
## DOPLŇKOVÁ PRAVIDLA
- Jazyk: Mluvím pouze česky a anglicky. Odpovídej v jazyce, ve kterém se uživatel ptá. Na dotazy v jiných jazycích odpovím prosbou o přepnutí do češtiny nebo angličtiny.
- Mimo rozsah: Pokud se ptá na něco mimo profesní profil, zdvořile nasměruj zpět.
- Ochrana detailu: U obecných dotazů odpovídej obecně, u konkrétních konkrétně.

---
## ZDROJ PRAVDY – Master CV
{master_cv}

---
## ZDROJ PRAVDY – Osobní popis
{personal_description}
"""

# Prompt pro kompresi konverzace (odstranění balastu, zachování faktů)
COMPRESSION_PROMPT = """Proveď KOMPRESI následující části konverzace. Nekrať ji sumarizací.

PRAVIDLA:
1. ODSTRANÍŠ pouze "balast": pozdravy (ahoj, dobrý den), výplňková slova, zdvořilostní fráze.
2. ZACHOVÁŠ 100% faktických informací: jména firem, projektů, technologií, konkrétní otázky a odpovědi.
3. Výstup musí být čitelný a zachovat smysl konverzace.
4. Formát: zachovej strukturu "Uživatel: ..." a "Avatar: ...".
5. Odpověz POUZE komprimovaným textem, bez úvodu nebo vysvětlení.

KONVERZACE KE KOMPRESI:
{conversation}
"""


def load_knowledge_base() -> tuple[str, str]:
    """Načte obsah Master_CV a Personal_Description."""
    master_cv = MASTER_CV_PATH.read_text(encoding="utf-8") if MASTER_CV_PATH.exists() else ""
    personal_desc = (
        PERSONAL_DESCRIPTION_PATH.read_text(encoding="utf-8")
        if PERSONAL_DESCRIPTION_PATH.exists()
        else ""
    )
    return master_cv, personal_desc


def build_core_prompt(language: str | None = None) -> str:
    """Sestaví Core část systémového promptu. language: 'cs' | 'en' pro explicitní jazykovou instrukci."""
    master_cv, personal_desc = load_knowledge_base()
    base = SYSTEM_PROMPT_TEMPLATE.format(
        master_cv=master_cv or "(Soubor Master_CV.txt je prázdný nebo chybí.)",
        personal_description=personal_desc or "(Soubor Personal_Description.txt je prázdný nebo chybí.)",
    )
    if language == "cs":
        return base + "\n\n---\n**KRITICKÉ:** Uživatel píše/mluví česky. Odpovídej VÝHRADNĚ česky. Ani jedno slovo v jiném jazyce."
    if language == "en":
        return base + "\n\n---\n**CRITICAL:** The user is writing/speaking in English. Respond EXCLUSIVELY in English. Not a single word in any other language."
    return base


def format_messages_for_llm(messages: list[dict]) -> list[dict]:
    """
    Formátuje zprávy pro Gemini API.
    messages: [{"role": "user"|"model", "content": "..."}, ...]
    """
    return [
        {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
        for m in messages
    ]


def get_messages_to_compress(messages: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Vrátí (zprávy ke kompresi, zbývající zprávy).
    Ke kompresi jde 20% nejstarších zpráv.
    """
    n = len(messages)
    compress_count = max(1, int(n * COMPRESSION_RATIO))
    to_compress = messages[:compress_count]
    remaining = messages[compress_count:]
    return to_compress, remaining


def format_conversation_for_compression(messages: list[dict]) -> str:
    """Formátuje zprávy do textu pro kompresní prompt."""
    lines = []
    for m in messages:
        role = "Uživatel" if m["role"] == "user" else "Avatar"
        lines.append(f"{role}: {m['content']}")
    return "\n\n".join(lines)
