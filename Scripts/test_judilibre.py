"""
test_judilibre.py

Valide l'acces a l'API Judilibre (Cour de cassation) en deux temps :
  1. Obtention d'un jeton OAuth (memes identifiants PISTE que Legifrance)
  2. Appel GET /search minimal -> confirme la souscription Judilibre active
     et montre la structure d'une reponse.

La reponse est sauvegardee dans data/sample_judilibre.json.

Usage :
  python3 scripts/test_judilibre.py
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
        "api": "https://api.piste.gouv.fr/cassation/judilibre/v1.0",
    },
    "sandbox": {
        "token": "https://sandbox-oauth.piste.gouv.fr/api/oauth/token",
        "api": "https://sandbox-api.piste.gouv.fr/cassation/judilibre/v1.0",
    },
}

client_id = os.getenv("PISTE_CLIENT_ID")
client_secret = os.getenv("PISTE_CLIENT_SECRET")
if not client_id or not client_secret:
    sys.exit("ERREUR : identifiants PISTE introuvables dans .env")

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


def main():
    print("[1/2] Demande de jeton OAuth ...")
    token = get_token()
    print("OK : jeton obtenu.")

    print("[2/2] Appel GET /search (Judilibre) ...")
    r = requests.get(
        f"{api_url}/search",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        params={"query": "société", "page_size": 3},
        timeout=30,
    )

    if r.status_code != 200:
        print(f"ECHEC : HTTP {r.status_code}")
        print(r.text[:800])
        print("\nSi 401/403 : verifie que l'application PISTE est bien souscrite a")
        print("Judilibre ET que tu as valide les CGU Judilibre (production).")
        sys.exit(1)

    data = r.json()
    os.makedirs("data", exist_ok=True)
    with open("data/sample_judilibre.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("OK : API Judilibre accessible.")
    print("Total decisions correspondantes :", data.get("total"))
    results = data.get("results", [])
    if results:
        print("\n--- Cles du premier resultat ---")
        print(list(results[0].keys()))
        print("\n--- Premier resultat (apercu) ---")
        print(json.dumps(results[0], ensure_ascii=False, indent=2)[:1200])
    print("\nReponse complete -> data/sample_judilibre.json")
    print("\nSUCCES : authentification + acces Judilibre operationnels.")


if __name__ == "__main__":
    main()