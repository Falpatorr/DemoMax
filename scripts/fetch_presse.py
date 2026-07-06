#!/usr/bin/env python3
"""
fetch_presse.py — Récupère les articles de presse générale et d'actualité
juridique via leurs flux RSS, filtre sur la semaine écoulée (J-7 → J-1),
dédoublonne, et écrit data/presse_AAAAMMJJ.json.

Bibliothèque standard uniquement. Chaque flux est indépendant : un flux en
panne (403, timeout, XML invalide) est signalé dans les logs mais ne fait
jamais échouer le run.
"""

import json
import os
import re
import sys
import ssl
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, date
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")

# ---------------------------------------------------------------------------
# Configuration des flux
# ---------------------------------------------------------------------------
# categorie : "presse" (presse générale) ou "juridique" (sites juridiques).
# En cas de changement d'URL d'un flux, c'est ici et seulement ici qu'on édite.
FEEDS = [
    {
        # Le flux RSS direct de lesechos.fr renvoie 403 aux clients non
        # navigateurs ; on passe par le flux Google News filtré sur la source,
        # qui fournit titres, dates et liens (redirection vers lesechos.fr).
        # La requête cible le champ juridique / vie des affaires pour éviter
        # de charger tout le journal (sport, international, etc.).
        "source": "Les Échos",
        "categorie": "presse",
        "url": ("https://news.google.com/rss/search"
                "?q=site:lesechos.fr%20when:7d%20"
                "(droit%20OR%20juridique%20OR%20justice%20OR%20tribunal"
                "%20OR%20r%C3%A9glementation%20OR%20concurrence"
                "%20OR%20fusion%20OR%20acquisition%20OR%20AMF"
                "%20OR%20redressement%20OR%20liquidation%20OR%20fiscalit%C3%A9)"
                "&hl=fr&gl=FR&ceid=FR:fr"),
        "strip_title_suffix": r"\s*-\s*Les\s*[ÉE]chos\s*$",
        "drop_desc": True,  # descriptions Google News = HTML sans valeur
        "max_items": 30,    # plafond de sécurité par run
    },
    {
        "source": "Le Monde",
        "categorie": "presse",
        "url": "https://www.lemonde.fr/economie/rss_full.xml",
    },
    {
        "source": "BBC",
        "categorie": "presse",
        "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "max_items": 25,
    },
    {
        "source": "The New York Times",
        "categorie": "presse",
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        "max_items": 25,
    },
    {
        "source": "Dalloz Actualité",
        "categorie": "juridique",
        "url": "https://www.dalloz-actualite.fr/actualites/feed.xml",
    },
    {
        "source": "Actu-Juridique",
        "categorie": "juridique",
        "url": "https://www.actu-juridique.fr/feed/",
    },
    {
        "source": "Village de la Justice",
        "categorie": "juridique",
        "url": "https://www.village-justice.com/articles/spip.php?page=backend",
    },
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)

STATE_FILE = Path("state/presse_seen.json")
DATA_DIR = Path("data")
SEEN_RETENTION_DAYS = 30
MAX_DESC_CHARS = 400


# ---------------------------------------------------------------------------
# Fenêtre de dates : digest hebdomadaire → les 7 jours précédant le run
# (J-7 → J-1). Quel que soit le jour d'exécution du cron, la semaine
# glissante couverte est cohérente avec le reste du pipeline.
# ---------------------------------------------------------------------------
WINDOW_DAYS = 7


def compute_window(today: date) -> tuple[date, date]:
    return today - timedelta(days=WINDOW_DAYS), today - timedelta(days=1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_date(raw: str):
    """Retourne un datetime aware (Paris) ou None."""
    if not raw:
        return None
    raw = raw.strip()
    # RFC 822 (RSS 2.0)
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=PARIS)
        return dt.astimezone(PARIS)
    except (ValueError, TypeError):
        pass
    # ISO 8601 (Atom / dc:date)
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=PARIS)
        return dt.astimezone(PARIS)
    except ValueError:
        return None


def make_ssl_context() -> ssl.SSLContext:
    """Certificats système par défaut ; bascule sur certifi s'il est installé
    (utile en local sur macOS, où le Python de python.org n'a pas accès aux
    certificats du système)."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


SSL_CONTEXT = make_ssl_context()


def fetch_url(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, "
                      "application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as resp:
        return resp.read()


def local(tag: str) -> str:
    """Nom local d'une balise, sans espace de noms."""
    return tag.rsplit("}", 1)[-1]


def parse_feed(xml_bytes: bytes) -> list[dict]:
    """Parse RSS 2.0 ou Atom, retourne des items bruts {title, link, date, desc}."""
    root = ET.fromstring(xml_bytes)
    items = []

    def find_text(node, names):
        for child in node:
            if local(child.tag) in names and child.text:
                return child.text
        return ""

    if local(root.tag) == "feed":  # Atom
        for entry in root:
            if local(entry.tag) != "entry":
                continue
            link = ""
            for child in entry:
                if local(child.tag) == "link":
                    if child.get("rel") in (None, "alternate"):
                        link = child.get("href", "") or link
            items.append({
                "title": find_text(entry, {"title"}),
                "link": link,
                "date": find_text(entry, {"published", "updated"}),
                "desc": find_text(entry, {"summary", "content"}),
            })
    else:  # RSS 2.0 (et variantes RDF)
        for item in root.iter():
            if local(item.tag) != "item":
                continue
            items.append({
                "title": find_text(item, {"title"}),
                "link": find_text(item, {"link"}),
                "date": find_text(item, {"pubDate", "date"}),
                "desc": find_text(item, {"description", "encoded"}),
            })
    return items


def load_seen() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("[presse] AVERTISSEMENT : presse_seen.json illisible, réinitialisé.")
    return {}


def save_seen(seen: dict, today: date) -> None:
    cutoff = (today - timedelta(days=SEEN_RETENTION_DAYS)).isoformat()
    pruned = {k: v for k, v in seen.items() if v >= cutoff}
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(pruned, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    today = datetime.now(PARIS).date()
    d_from, d_to = compute_window(today)
    print(f"[presse] Fenêtre : {d_from} → {d_to}")

    seen = load_seen()
    collected = []

    for feed in FEEDS:
        label = feed["source"]
        try:
            raw = fetch_url(feed["url"])
            entries = parse_feed(raw)
        except urllib.error.HTTPError as e:
            print(f"[presse] ÉCHEC {label} : HTTP {e.code} — flux ignoré.")
            continue
        except Exception as e:  # timeout, XML invalide, DNS…
            print(f"[presse] ÉCHEC {label} : {type(e).__name__}: {e} — flux ignoré.")
            continue

        kept = 0
        suffix_re = feed.get("strip_title_suffix")
        max_items = feed.get("max_items")
        for entry in entries:
            if max_items is not None and kept >= max_items:
                break  # les items non retenus ne sont pas marqués « vus »
            link = (entry["link"] or "").strip()
            title = strip_html(entry["title"] or "")
            if suffix_re:
                title = re.sub(suffix_re, "", title).strip()
            if not link or not title:
                continue
            dt = parse_date(entry["date"])
            # Sans date exploitable : on garde (le dédoublonnage évite les répétitions).
            if dt is not None and not (d_from <= dt.date() <= d_to):
                continue
            if link in seen:
                continue
            seen[link] = today.isoformat()
            chapo = "" if feed.get("drop_desc") \
                else strip_html(entry["desc"] or "")[:MAX_DESC_CHARS]
            collected.append({
                "source": label,
                "categorie": feed["categorie"],
                "titre": title,
                "lien": link,
                "date": dt.isoformat() if dt else None,
                "chapo": chapo,
            })
            kept += 1
        print(f"[presse] {label} : {len(entries)} entrées, {kept} retenues.")

    # Tri anti-chronologique (les items sans date à la fin)
    collected.sort(key=lambda x: x["date"] or "", reverse=True)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / "presse.json"
    out.write_text(
        json.dumps(collected, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    save_seen(seen, today)
    print(f"[presse] {len(collected)} articles → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())