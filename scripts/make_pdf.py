#!/usr/bin/env python3
"""
make_pdf.py — Convertit output/digest.html en output/digest.pdf (WeasyPrint).

Étape déterministe du pipeline : aucune intervention de l'API, aucun coût.
En cas d'échec, on sort en erreur mais l'appelant peut choisir de continuer
(le mail HTML reste envoyable sans la pièce jointe).
"""

import sys
from pathlib import Path

SRC = Path("output/digest.html")
DST = Path("output/digest.pdf")

PAGE_CSS = """
@page {
    size: A4;
    margin: 14mm 13mm 16mm 13mm;
    @bottom-center {
        content: "La Une du droit des affaires — page " counter(page) " / " counter(pages);
        font-family: Arial, Helvetica, sans-serif;
        font-size: 8pt;
        color: #6b6558;
    }
}
body { background: #fdfcf8 !important; }
a { color: #1a1a1a; }
"""


def main() -> int:
    if not SRC.exists() or not SRC.read_text(encoding="utf-8").strip():
        print("ERREUR : output/digest.html absent ou vide, PDF non genere.")
        return 1
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        print("ERREUR : weasyprint non installe (pip install weasyprint).")
        return 1

    HTML(filename=str(SRC), base_url=str(SRC.parent)).write_pdf(
        str(DST), stylesheets=[CSS(string=PAGE_CSS)]
    )
    size_kb = DST.stat().st_size // 1024
    print(f"PDF genere : {DST} ({size_kb} Ko)")
    return 0


if __name__ == "__main__":
    sys.exit(main())