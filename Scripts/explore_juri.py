"""
explore_juri.py

Exploration du fonds JURI (jurisprudence judiciaire) via l'endpoint /search.

Objectif : voir la STRUCTURE d'un resultat de jurisprudence (a-t-on un champ
'formation' pour reperer la chambre commerciale ? une date ? un id JURITEXT ?
un titre ?) avant d'ecrire fetch_juri.py.

La requete est volontairement minimale et sure (recherche large, tri par date
decroissante). On affinera le filtrage (chambre + fenetre de dates) ensuite,
une fois la structure connue.

La reponse complete est ecrite dans data/sample_juri.json.

Usage :
  python3 scripts/explore_juri.py
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
        print(r.text[:800])
        sys.exit(1)
    return r.json()


# Requete minimale : recherche large dans JURI, triee par date decroissante.
REQUETE = {
    "fond": "JURI",
    "recherche": {
        "champs": [
            {
                "typeChamp": "ALL",
                "criteres": [
                    {"typeRecherche": "UN_DES_MOTS", "valeur": "société", "operateur": "ET"}
                ],
                "operateur": "ET",
            }
        ],
        "operateur": "ET",
        "typePagination": "DEFAUT",
        "pageNumber": 1,
        "pageSize": 5,
        "sort": "DATE_DESC",
    },
}


def main():
    token = get_token()
    data = post(token, "/search", REQUETE)

    os.makedirs("data", exist_ok=True)
    with open("data/sample_juri.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Cles de premier niveau :", list(data.keys()))
    print("Nombre total de resultats :", data.get("totalResultNumber") or data.get("totalNbResult"))

    # Affiche la structure du premier resultat pour comprendre les champs dispo
    results = data.get("results") or data.get("items") or []
    if results:
        print("\n--- Cles du premier resultat ---")
        print(list(results[0].keys()))
        print("\n--- Premier resultat (apercu) ---")
        print(json.dumps(results[0], ensure_ascii=False, indent=2)[:1500])
    else:
        print("Aucun resultat dans la reponse. Inspecte data/sample_juri.json.")


if __name__ == "__main__":
    main()