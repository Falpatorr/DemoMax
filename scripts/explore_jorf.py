"""
Exploration du sommaire d'un Journal officiel via /consult/jorfCont.

Objectif : voir la STRUCTURE d'un sommaire de JO (comment sont organises
les textes : sections, intitules, NOR...) avant d'ecrire fetch_jorf.py.

Le sommaire complet est ecrit dans data/sample_jorfcont.json pour inspection
dans VS Code. Un resume des cles est affiche dans le terminal.

Usage :
  python3 explore_jorf.py
"""

import os
import sys
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
    sys.exit("ERREUR : identifiants introuvables dans .env")

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


token = get_token()
print("Jeton OK.")

# 1. Recuperer le dernier conteneur JO
last = post(token, "/consult/lastNJo", {"nbElement": 1})
container = last["containers"][0]
cid = container["id"]
print(f"Dernier JO : {container.get('titre')}  (id={cid}, idEli={container.get('idEli')})")

# 2. Recuperer son sommaire
sommaire = post(token, "/consult/jorfCont", {"id": cid})

# 3. Sauvegarder le sommaire complet pour inspection
os.makedirs("data", exist_ok=True)
out = "data/sample_jorfcont.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(sommaire, f, ensure_ascii=False, indent=2)
print(f"\nSommaire complet ecrit dans : {out}")

# 4. Resume rapide de la structure dans le terminal
print("\n--- Cles de premier niveau du sommaire ---")
print(list(sommaire.keys()))