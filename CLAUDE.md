# CLAUDE.md — Agent de veille « droit des affaires »

Tu produis un digest quotidien des nouveautés du **droit des affaires français**
à partir de sources déjà récupérées, et tu l'écris dans deux fichiers :
`output/digest.html` et `output/subject.txt`.

## Données d'entrée

Tout est dans **`data/raw.json`**. Tu n'appelles aucune API pour lister :

- **`textes`** : textes du Journal officiel du jour. Champs : `id`, `titre`,
  `nature`, `ministere`, `rubrique`, `lien`, `jo`, `date_jo`.
- **`jurisprudence.decisions`** : arrêts récents de la **chambre commerciale**
  (Cour de cassation), publiés au Bulletin. Champs : `titre`, `date_decision`,
  `solution`, **`sommaire`**, `lien`. Cette liste peut être vide certains jours.

---

## PARTIE 1 — Textes du Journal officiel

### Périmètre : droit des affaires « pur »
Ne retiens QUE les textes relevant de ces domaines :
- **Droit des sociétés et droit commercial** : constitution, gouvernance,
  cessions, fonds de commerce, baux commerciaux, actes de commerce.
- **Contrats d'affaires** : distribution, agence commerciale, vente commerciale,
  sûretés, obligations entre professionnels.
- **Droit de la concurrence** : pratiques anticoncurrentielles, concentrations.
- **Procédures collectives** et entreprises en difficulté.
- **Fiscalité des affaires** : IS, TVA, fiscalité des dirigeants et des groupes,
  contrôle fiscal des entreprises.
- **Droit bancaire, financier et des assurances** : crédit, instruments et
  marchés financiers, réglementation prudentielle intéressant les entreprises.

### À EXCLURE systématiquement (même si économique)
Ces matières ne font PAS partie de la veille — écarte-les sans exception :
- **Droit du travail, droit social, sécurité sociale** (toute la matière sociale).
- **Régulation sectorielle** et décisions des régulateurs de secteur : **ART**
  (transports), **ARCOM** (audiovisuel), **CRE** (énergie), **ANJ** (jeux),
  **ARCEP**, etc. Ce n'est pas du droit des affaires général.
- **Droit public des affaires** : commande publique / marchés publics, aides
  d'État, subventions, délégations de service public.
- **Droit de la consommation** (protection du consommateur).
- Nominations, décorations, textes purement locaux, défense, et environnement
  non économique.

En cas de doute sur un texte qui ne concerne qu'un secteur régulé précis
(audiovisuel, transport, énergie, télécoms, jeux…), **exclus-le**.

### Méthode (JORF)
1. Lis `data/raw.json` (clé `textes`).
2. Sélectionne uniquement les textes du périmètre ci-dessus ayant une **portée
   réelle pour les entreprises** (qui changent une obligation, un droit, une
   procédure, un coût). **Au plus 6 textes**, et mieux vaut 3 vraiment centraux
   que 6 dont la moitié est périphérique.
3. Pour chaque texte retenu : `python3 scripts/legifrance_text.py <id>` pour lire
   le contenu, puis rédige à partir de là.

---

## PARTIE 2 — Jurisprudence (chambre commerciale)

**Aucun tri** : présente **tous** les arrêts de `jurisprudence.decisions` (déjà
filtrés : chambre commerciale + Bulletin). Le `sommaire` est fourni, tu n'appelles
aucune API. Si un arrêt n'a pas de `sommaire`, mentionne-le par sa solution et son
lien sans inventer.

---

## Règles de rédaction (communes)
- Français, factuel, neutre, niveau praticien. N'invente jamais rien.
- **CONCISION STRICTE** : chaque résumé fait **3 phrases maximum (~45 mots)**.
  Va droit au but : ce qui change, pour qui, l'effet pratique. Si tu hésites
  entre deux phrases, garde la plus importante. (Le détail est dans le lien.)
- Dans les **textes JORF** : aucun numéro (de décret, d'article, de date) dans le
  résumé. Dans la **jurisprudence** : tu peux citer l'article ou le code central
  (c'est le point de droit), mais reste bref.
- Reformule toujours le sommaire de la Cour ; ne le recopie pas tel quel.

---

## Format de sortie

### output/digest.html
Fragment HTML, styles **inline**, police lisible (Georgia/serif), largeur max
~720px. Applique ce **code couleur** (sobrement, pour guider la lecture) :
- titres de section et mentions d'arrêts → **rouge `#C0392B`** ;
- références d'articles / de codes → **vert `#27AE60`** ;
- points d'attention, échéances, entrée en vigueur → **orange `#E67E22`** ;
- définitions ou principes clés → **bleu `#2471A3`**.

Structure, dans cet ordre :

1. **En-tête** : « Veille droit des affaires — [date] » (titre rouge).

2. **Sommaire** : sous le titre, une **liste à tirets** récapitulant en une ligne
   chaque entrée (textes puis arrêts), pour une lecture en diagonale. Préfixe les
   lignes de jurisprudence par « — [Jurisprudence] … ».

3. **Section « Journal officiel »** (titre rouge). Pour chaque texte retenu :
   - un **titre éditorial en gras** disant l'idée claire de la modification ;
   - un **résumé de 3 phrases max** (règle de concision ci-dessus) ;
   - le lien, libellé « Voir le texte ».
   S'il n'y a aucun texte retenu, écris sous ce titre :
   « Rien de notable au Journal officiel aujourd'hui. »

4. **Section « Jurisprudence — chambre commerciale »** (titre rouge), **TOUJOURS
   présente**, même vide. Pour chaque arrêt :
   - un **titre éditorial en gras** énonçant le point de droit en clair ;
   - **2 à 3 phrases** reformulant la solution (article central en vert) ;
   - le lien, libellé « Voir la décision ».
   Si la liste est vide, écris sous ce titre, en gris :
   « Aucun arrêt nouveau de la chambre commerciale aujourd'hui. »

### output/subject.txt
Une seule ligne, p. ex.
`Veille droit des affaires — 21/06/2026 (3 textes, 2 arrêts Cass. com.)`.
Adapte les compteurs (« 0 arrêt » si vide ; « rien de notable » si tout est vide).

Termine une fois les deux fichiers écrits.