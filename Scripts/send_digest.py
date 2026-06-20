"""
send_digest.py

Envoie le digest par e-mail via Resend.
Lit output/digest.html (corps) et output/subject.txt (objet), tous deux ecrits
par Claude. Fonctionne en local (.env) et en CI (secrets).

Variables attendues :
  RESEND_API_KEY, DIGEST_FROM, DIGEST_TO (destinataires separes par des virgules)

Usage :
  python3 scripts/send_digest.py
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("RESEND_API_KEY")
expediteur = os.getenv("DIGEST_FROM")
destinataires = os.getenv("DIGEST_TO")

if not (api_key and expediteur and destinataires):
    sys.exit("ERREUR : RESEND_API_KEY / DIGEST_FROM / DIGEST_TO manquants "
             "(.env en local, secrets en CI).")

# Lecture des fichiers produits par Claude
try:
    with open("output/digest.html", encoding="utf-8") as f:
        html = f.read()
    with open("output/subject.txt", encoding="utf-8") as f:
        objet = f.read().strip()
except FileNotFoundError as e:
    sys.exit(f"ERREUR : fichier de sortie introuvable ({e.filename}). "
             "Lance d'abord la generation du digest (claude -p).")

if not html.strip():
    sys.exit("ERREUR : output/digest.html est vide, envoi annule.")

r = requests.post(
    "https://api.resend.com/emails",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "from": expediteur,
        "to": [d.strip() for d in destinataires.split(",") if d.strip()],
        "subject": objet or "Veille droit des affaires",
        "html": html,
    },
    timeout=30,
)

if r.status_code >= 300:
    print(f"ECHEC envoi : HTTP {r.status_code}")
    print(r.text[:600])
    sys.exit(1)

print("Envoye. id =", r.json().get("id"))