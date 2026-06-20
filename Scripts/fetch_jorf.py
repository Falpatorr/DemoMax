"""
fetch_jorf.py

Recupere les textes du Journal officiel sur la fenetre voulue
(J-1 en semaine ; vendredi -> dimanche le lundi), aplatit l'arbre du
sommaire et ecrit data/raw_AAAAMMJJ.json.

Ce script ne fait AUCUN tri par matiere : il extrait tous les textes avec
leurs metadonnees. La selection de ce qui releve du droit des affaires est
faite ensuite par Claude, a partir de ce fichier brut.

Fonctionne a l'identique en local (.env) et dans GitHub Actions (secrets).

Usage :
  python3 fetch_jorf.py
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

# Mettre a True pour ignorer la fenetre et traiter simplement le dernier JO
# disponible (pratique pour tester un week-end ou un jour ferie).
FORCE_DERNIER_JO = False

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

LIEN_LEGIFRANCE = "https://www.legifrance.gouv.fr/jorf/id/{}"

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


def fenetre():
    """Fenetre de publication a couvrir (dates incluses)."""
    today = datetime.now(ZoneInfo("Europe/Paris")).date()
    if today.weekday() == 0:               # lundi -> rattrape vendredi, samedi, dimanche
        start = today - timedelta(days=3)
    else:                                  # autres jours -> la veille
        start = today - timedelta(days=1)
    return start, today - timedelta(days=1)


def date_eli(id_eli):
    """'/eli/jo/2026/6/20/0143' -> date(2026, 6, 20)."""
    p = id_eli.strip("/").split("/")       # ['eli','jo','2026','6','20','0143']
    return date(int(p[2]), int(p[3]), int(p[4]))


def collecter_textes(tm, chemin):
    """Parcourt recursivement un noeud de l'arbre 'tms' et ramasse les liensTxt."""
    chemin = chemin + [tm.get("titre", "")]
    textes = []
    for lien in tm.get("liensTxt", []):
        textes.append({
            "id": lien.get("id"),
            "titre": lien.get("titre"),
            "nature": lien.get("nature"),
            "ministere": lien.get("ministere") or lien.get("emetteur"),
            "rubrique": " > ".join(c for c in chemin if c),
            "lien": LIEN_LEGIFRANCE.format(lien.get("id")),
        })
    for enfant in tm.get("tms", []):
        textes += collecter_textes(enfant, chemin)
    return textes


def main():
    token = get_token()
    last = post(token, "/consult/lastNJo", {"nbElement": 6})
    containers = last.get("containers", [])

    if FORCE_DERNIER_JO:
        retenus = [(containers[0]["id"], date_eli(containers[0]["idEli"]),
                    containers[0].get("titre"))]
        print(f"[mode test] dernier JO uniquement : {retenus[0][2]}")
    else:
        start, end = fenetre()
        print(f"Fenetre de publication : {start} -> {end}")
        retenus = []
        for c in containers:
            if not c.get("idEli"):
                continue
            d = date_eli(c["idEli"])
            if start <= d <= end:
                retenus.append((c["id"], d, c.get("titre")))

    if not retenus:
        print("Aucun JO sur la fenetre (week-end ou jour ferie ?). Rien a ecrire.")

    tous_textes = []
    for cid, d, titre in retenus:
        somm = post(token, "/consult/jorfCont", {"id": cid})
        structure = somm["items"][0]["joCont"].get("structure", {})
        textes = []
        for tm in structure.get("tms", []):
            textes += collecter_textes(tm, [])
        for t in textes:
            t["jo"] = titre
            t["date_jo"] = d.isoformat()
        print(f"  {titre} : {len(textes)} textes")
        tous_textes += textes

    os.makedirs("data", exist_ok=True)
    out = "data/raw.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "nb_textes": len(tous_textes),
            "textes": tous_textes,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n{len(tous_textes)} textes ecrits dans {out}")


if __name__ == "__main__":
    main()