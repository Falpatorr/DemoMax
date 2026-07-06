Produis le digest hebdomadaire de veille « droit des affaires » en suivant
exactement la méthode, le plan et les règles de rédaction de CLAUDE.md.

Données sources (déjà préparées, ne relance aucun script de collecte) :
- data/raw.json — clé "textes" (sommaires JORF de la semaine) et clé
  jurisprudence (arrêts Judilibre) ;
- data/presse.json — articles de presse générale et de sites juridiques.

Méthode, dans cet ordre et sans étape superflue :
1. Lis CLAUDE.md, data/raw.json et data/presse.json.
2. Sélectionne les textes JORF pertinents (10 maximum). Pour les textes
   retenus dont le sommaire ne suffit pas à rédiger un résumé fiable,
   récupère le contenu via scripts/legifrance_text.py — uniquement pour
   ces textes-là, jamais pour l'ensemble.
3. Rédige le digest complet au format V5 de CLAUDE.md et écris
   output/digest.html puis output/subject.txt.

Termine immédiatement une fois les deux fichiers écrits. Ne modifie aucun
autre fichier, ne fais aucun commit.