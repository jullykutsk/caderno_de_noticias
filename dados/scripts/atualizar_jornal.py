import datetime
import hashlib
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "dados" / "edicoes.json"

FEEDS = [
    {
        "categoria": "Brasil & Mundo",
        "origem_nome": "Agência Brasil",
        "url": "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml",
    },
    {
        "categoria": "Clima & Pets",
        "origem_nome": "Jornal da USP",
        "url": "https://jornal.usp.br/feed/",
    },
    {
        "categoria": "Psicologia & Neurociência",
        "origem_nome": "Agência FAPESP",
        "url": "https://agencia.fapesp.br/rss/",
    },
    {
        "categoria": "Curiosidades & Hobbies",
        "origem_nome": "BBC News Brasil",
        "url": "https://feeds.bbci.co.uk/portuguese/rss.xml",
    },
]


def clean_text(raw: str) -> str:
    if not raw:
        return ""
    no_tags = re.sub(r"<[^>]+>", " ", raw)
    unescaped = html.unescape(no_tags)
    return re.sub(r"\s+", " ", unescaped).strip()


def fetch_rss_items(feed_cfg: dict, limit: int = 3) -> list[dict]:
    req = urllib.request.Request(
        feed_cfg["url"],
        headers={"User-Agent": "CadernoDeNoticiasBot/1.0 (+https://github.com)"},
    )
    items = []
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_bytes = resp.read()
        root = ET.fromstring(xml_bytes)

        entries = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
        for entry in entries[:limit]:
            title = clean_text(
                entry.findtext("title")
                or entry.findtext("{http://www.w3.org/2005/Atom}title")
                or ""
            )
            desc = clean_text(
                entry.findtext("description")
                or entry.findtext("summary")
                or entry.findtext("{http://www.w3.org/2005/Atom}summary")
                or ""
            )
            link = clean_text(entry.findtext("link") or "")
            if not link:
                link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                if link_el is not None:
                    link = link_el.attrib.get("href", "").strip()

            if not title or not link:
                continue

            resumo = desc[:260] + ("..." if len(desc) > 260 else "") if desc else (
                f"Matéria publicada em {feed_cfg['origem_nome']}."
            )
            uid = hashlib.sha1(f"{title}|{link}".encode("utf-8")).hexdigest()[:10]

            items.append(
                {
                    "id": uid,
                    "categoria": feed_cfg["categoria"],
                    "titulo": title,
                    "resumo": resumo,
                    "conexao": "Leitura selecionada para ampliar repertório sem excesso de estímulos.",
                    "reflexao": "Observa o que esta notícia desperta no teu pensamento e anota uma ideia própria.",
                    "origem_nome": feed_cfg["origem_nome"],
                    "origem_url": link,
                }
            )
    except Exception as exc:
        print(f"[AVISO] Falha ao ler {feed_cfg['origem_nome']}: {exc}")
    return items


def main() -> None:
    tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.datetime.now(tz)

    collected = []
    seen_ids = set()
    for feed_cfg in FEEDS:
        for item in fetch_rss_items(feed_cfg, limit=2):
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                collected.append(item)

    if len(collected) >= 2:
        mid = len(collected) // 2
        dia_items = collected[:mid]
        noite_items = collected[mid:]
    elif len(collected) == 1:
        dia_items = collected
        noite_items = collected
    else:
        if OUTPUT_PATH.exists():
            existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
            dia_items = existing.get("edicoes", {}).get("dia", [])
            noite_items = existing.get("edicoes", {}).get("noite", [])
        else:
            dia_items = []
            noite_items = []

    payload = {
        "atualizado_em": now.strftime("%Y-%m-%d %H:%M BRT"),
        "edicoes": {
            "dia": dia_items,
            "noite": noite_items,
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Atualizado com sucesso em {payload['atualizado_em']} (Dia: {len(dia_items)}, Noite: {len(noite_items)})")


if __name__ == "__main__":
    main()
