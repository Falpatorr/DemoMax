"""
legifrance_text.py <JORFTEXT_ID>

Recupere le texte integral d'un texte du JO via /consult/jorf et l'affiche
en texte lisible (balises HTML retirees). C'est le helper que Claude appelle
pour lire un texte qu'il a retenu.

Sauvegarde aussi la reponse brute dans data/sample_jorf_text.json (utile pour
inspecter la structure si besoin).

Usage :
  python3 scripts/legifrance_text.py JORFTEXT000054280280
"""

import os
import sys
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

ENV = "production"
URLS = {
    "production": {
        "token": "https://oauth.piste.gouv.fr/api/oauth/token",
        "api": "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app",
    },
    "sandbox": {
        "token": "https://sandbox-oauth.piste.gouv.fr/api/oauth/token",
        "api": "https://sandbox-api.piste.gouv.fr/dila/legifrance/lf-engine-app",
    },
}

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


def post(token, path, payload):
    r = requests.post(
        f"{api_url}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=payload,
        timeout=30,
    )
    if r.status_code != 200:
        print(f"ECHEC sur {path} : HTTP {r.status_code}")
        print(r.text[:600])
        sys.exit(1)
    return r.json()


def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def collecter_contenu(obj, out):
    """Ramasse recursivement les champs de contenu (HTML) du texte."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("content", "contenu", "texteHtml") and isinstance(v, str) and v.strip():
                t = strip_html(v)
                if t:
                    out.append(t)
            else:
                collecter_contenu(v, out)
    elif isinstance(obj, list):
        for it in obj:
            collecter_contenu(it, out)


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage : python3 scripts/legifrance_text.py <JORFTEXT_ID>")
    text_id = sys.argv[1]

    token = get_token()
    data = post(token, "/consult/jorf", {"textCid": text_id})

    os.makedirs("data", exist_ok=True)
    with open("data/sample_jorf_text.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    parts = []
    collecter_contenu(data, parts)
    texte = "\n\n".join(parts)

    if texte:
        print(texte[:4000])
        if len(texte) > 4000:
            print(f"\n[... {len(texte)} caracteres au total ...]")
    else:
        print("Aucun champ de contenu trouve.")
        print("Cles de premier niveau :", list(data.keys()))
        print("Inspecte data/sample_jorf_text.json pour voir la structure exacte.")


if __name__ == "__main__":
    main()