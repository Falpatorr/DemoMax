"""
fetch_juri.py  (version Judilibre)

Recupere les arrets de la Cour de cassation, CHAMBRE COMMERCIALE, publies au
Bulletin, via l'API Judilibre, et les fusionne dans data/raw.json (cle
'jurisprudence'), a cote des textes du JORF.

Cadence QUOTIDIENNE avec DEDUPLICATION : on balaie une fenetre large (pour
absorber le delai de publication), mais on ne rapporte chaque arret qu'UNE fois,
grace a un registre des arrets deja envoyes (state/juri_seen.json).

Le sommaire (resume du point de droit) est fourni directement par Judilibre :
aucun appel supplementaire n'est necessaire.

A lancer APRES fetch_jorf.py (qui cree data/raw.json).

Usage :
  python3 scripts/fetch_juri.py
"""

import os
import sys
import json
import requests
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

ENV = "production"

# --- Reglages -----------------------------------------------------------------
JOURS = 30        # fenetre de rattrapage (la dedup evite les repetitions)
CHAMBRE = "comm"  # chambre commerciale
PUBLICATION = "b" # publie au Bulletin
# ------------------------------------------------------------------------------

URLS = {
    "production": {
        "token": "https://oauth.piste.gouv.fr/api/oauth/token",
        "api": "https://api.piste.gouv.fr/cassation/judilibre/v1.0",
    },
    "sandbox": {
        "token": "https://sandbox-oauth.piste.gouv.fr/api/oauth/token",
        "api": "https://sandbox-api.piste.gouv.fr/cassation/judilibre/v1.0",
    },
}

LIEN_JUDILIBRE = "https://www.courdecassation.fr/decision/{}"
SEEN_PATH = "state/juri_seen.json"

client_id = os.getenv("PISTE_CLIENT_ID")
client_secret = os.getenv("PISTE_CLIENT_SECRET")
if not client_id or not client_secret:
    sys.exit("ERREUR : identifiants PISTE introuvables (.env en local, secrets en CI)")

token_url = URLS[ENV]["token"]
api_url = URLS[ENV]["api"]


def get_token():
    r = requests.post(
        token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "openid",
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def export_page(token, start, end, batch):
    """Un lot de /export pour la fenetre et la chambre voulues."""
    r = requests.get(
        f"{api_url}/export",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        params={
            "date_start": start.isoformat(),
            "date_end": end.isoformat(),
            "chamber": CHAMBRE,
            "publication": PUBLICATION,
            "batch_size": 1000,
            "batch": batch,
            "order": "desc",
        },
        timeout=60,
    )
    if r.status_code != 200:
        print(f"ECHEC /export : HTTP {r.status_code}")
        print(r.text[:800])
        sys.exit(1)
    return r.json()


def charger_seen():
    if os.path.exists(SEEN_PATH):
        with open(SEEN_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def sauver_seen(seen, today):
    # Purge : on retire ce qui ne peut plus revenir dans la fenetre.
    limite = (today - timedelta(days=JOURS + 10)).isoformat()
    seen = {i: d for i, d in seen.items() if d >= limite}
    os.makedirs(os.path.dirname(SEEN_PATH), exist_ok=True)
    with open(SEEN_PATH, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)


def main():
    today = datetime.now(ZoneInfo("Europe/Paris")).date()
    start = today - timedelta(days=JOURS)
    print(f"Fenetre Judilibre : {start} -> {today} (chambre commerciale, Bulletin)")

    token = get_token()
    seen = charger_seen()

    # 1. Recuperer toutes les decisions de la fenetre (pagination par batch)
    brut = []
    batch = 0
    while True:
        page = export_page(token, start, today, batch)
        results = page.get("results", [])
        brut += results
        if page.get("next_batch") is None or not results:
            break
        batch += 1
        if batch > 20:  # garde-fou
            break

    # 2. Ne garder que les NOUVEAUX arrets (absents du registre)
    nouveaux = []
    for d in brut:
        did = d.get("id")
        if not did or did in seen:
            continue
        sommaire = d.get("summary")
        nouveaux.append({
            "id": did,
            "titre": f"Cass. com., {d.get('decision_date')}, n° {d.get('number')}",
            "date_decision": d.get("decision_date"),
            "solution": d.get("solution"),
            "sommaire": sommaire,
            "lien": LIEN_JUDILIBRE.format(did),
        })
        seen[did] = d.get("decision_date") or today.isoformat()

    nouveaux.sort(key=lambda x: x["date_decision"] or "", reverse=True)

    # 3. Fusion dans data/raw.json
    raw_path = "data/raw.json"
    data = {}
    if os.path.exists(raw_path):
        with open(raw_path, encoding="utf-8") as f:
            data = json.load(f)
    else:
        print("(data/raw.json absent : lance d'abord fetch_jorf.py. Fichier partiel cree.)")
        os.makedirs("data", exist_ok=True)

    data["jurisprudence"] = {
        "nb_decisions": len(nouveaux),
        "decisions": nouveaux,
    }
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    sauver_seen(seen, today)

    print(f"{len(brut)} arret(s) dans la fenetre, {len(nouveaux)} NOUVEAU(X) -> {raw_path}")
    for d in nouveaux:
        s = (d["sommaire"] or "")[:70]
        print(f"  {d['date_decision']} | {d['solution']} | {s}")


if __name__ == "__main__":
    main()