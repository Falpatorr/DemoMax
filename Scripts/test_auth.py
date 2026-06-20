"""
Test isolé de l'authentification PISTE et de l'accès à l'API Légifrance.

Diagnostic en deux étapes :
  1. Obtention d'un jeton OAuth  -> valide identifiants + URL de jeton + scope
  2. Appel /list/ping avec ce jeton -> valide la souscription de l'app à l'API
     Légifrance et la cohérence de l'environnement (sandbox/production)

Usage :
  pip install requests python-dotenv
  python test_auth.py
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

# --- Choisis l'environnement correspondant a TES identifiants : "production" ou "sandbox"
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
    sys.exit("ERREUR : PISTE_CLIENT_ID / PISTE_CLIENT_SECRET introuvables dans .env")

token_url = URLS[ENV]["token"]
api_url = URLS[ENV]["api"]

# --- Etape 1 : obtenir un jeton -------------------------------------------------
print(f"[1/2] Demande de jeton ({ENV}) ...")
r = requests.post(
    token_url,
    data={  # form-urlencoded : PISTE refuse le JSON ici, bien utiliser data=
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "openid",
    },
    timeout=20,
)

if r.status_code != 200:
    print(f"ECHEC etape 1 : authentification refusee (HTTP {r.status_code})")
    print(r.text[:500])
    sys.exit(1)

token = r.json()["access_token"]
print(f"OK etape 1 : jeton obtenu (valide {r.json().get('expires_in')} s)")

# --- Etape 2 : verifier l'acces via un endpoint fonctionnel reel ---
print("[2/2] Test d'acces a l'API Legifrance (/consult/lastNJo) ...")
r2 = requests.post(
    f"{api_url}/consult/lastNJo",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    },
    json={"nbElement": 1},
    timeout=20,
)

if r2.status_code == 200:
    data = r2.json()
    print("OK etape 2 : API Legifrance accessible.")
    print("Apercu de la reponse :", str(data)[:300])
    print("\nSUCCES : authentification PISTE + acces Legifrance operationnels.")
else:
    print(f"ECHEC etape 2 : HTTP {r2.status_code}")
    print(r2.text[:500])
    sys.exit(1)