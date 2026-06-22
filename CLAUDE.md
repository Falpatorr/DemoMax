# CLAUDE.md — Agent de veille HEBDOMADAIRE « droit des affaires »

Tu produis un digest HEBDOMADAIRE des nouveautes du **droit des affaires
francais** de la **semaine ecoulee**, a partir de sources deja recuperees, et tu
l'ecris dans deux fichiers : `output/digest.html` et `output/subject.txt`.

## Donnees d'entree

Tout est dans **`data/raw.json`**. Tu n'appelles aucune API pour lister :

- **`periode`** : `{debut, fin}` = la semaine couverte (sert au titre).
- **`textes`** : tous les textes du Journal officiel publies sur la semaine
  (plusieurs JO). Champs : `id`, `titre`, `nature`, `ministere`, `rubrique`,
  `lien`, `jo`, `date_jo`.
- **`jurisprudence.decisions`** : arrets de la **chambre commerciale** (Cour de
  cassation) publies au Bulletin sur la periode. Champs : `titre`,
  `date_decision`, `solution`, **`sommaire`**, `lien`. Peut etre vide.

---

## PARTIE 1 — Textes du Journal officiel

### Perimetre : droit des affaires « pur »
Ne retiens QUE les textes relevant de ces domaines :
- **Droit des societes et droit commercial** : constitution, gouvernance,
  cessions, fonds de commerce, baux commerciaux, actes de commerce.
- **Contrats d'affaires** : distribution, agence commerciale, vente commerciale,
  suretes, obligations entre professionnels.
- **Droit de la concurrence** : pratiques anticoncurrentielles, concentrations.
- **Procedures collectives** et entreprises en difficulte.
- **Fiscalite des affaires** : IS, TVA, fiscalite des dirigeants et des groupes,
  controle fiscal des entreprises.
- **Droit bancaire, financier et des assurances** : credit, instruments et
  marches financiers, reglementation prudentielle interessant les entreprises.

### A EXCLURE systematiquement (meme si economique)
- **Droit du travail, droit social, securite sociale** (toute la matiere sociale).
- **Regulation sectorielle** et decisions des regulateurs de secteur : **ART**
  (transports), **ARCOM** (audiovisuel), **CRE** (energie), **ANJ** (jeux),
  **ARCEP**, etc.
- **Droit public des affaires** : commande publique / marches publics, aides
  d'Etat, subventions, delegations de service public.
- **Droit de la consommation** (protection du consommateur).
- Nominations, decorations, textes purement locaux, defense, environnement non
  economique.
En cas de doute sur un texte propre a un seul secteur regule (audiovisuel,
transport, energie, telecoms, jeux...), **exclus-le**.

### Methode (JORF)
1. Lis `data/raw.json` (cle `textes`) : c'est une semaine entiere, donc beaucoup
   de textes. Parcours-les tous.
2. Selectionne les textes du perimetre ayant une **portee reelle pour les
   entreprises**. Comme c'est un recap hebdomadaire, tu peux en retenir
   **jusqu'a 12**, les plus marquants de la semaine — mais reste selectif :
   privilegie l'impact, ecarte le periferique.
3. Pour chaque texte retenu : `python3 scripts/legifrance_text.py <id>` pour lire
   le contenu, puis redige a partir de la.

---

## PARTIE 2 — Jurisprudence (chambre commerciale)

**Aucun tri** : presente **tous** les arrets de `jurisprudence.decisions` (deja
filtres : chambre commerciale + Bulletin). Le `sommaire` est fourni. Si un arret
n'a pas de `sommaire`, mentionne-le par sa solution et son lien sans inventer.

---

## Regles de redaction (communes)
- Francais, factuel, neutre, niveau praticien. N'invente jamais rien.
- **CONCISION STRICTE** : chaque resume fait **3 phrases maximum (~45 mots)**.
  Va droit au but : ce qui change, pour qui, l'effet pratique.
- Dans les **textes JORF** : aucun numero dans le resume. Dans la
  **jurisprudence** : tu peux citer l'article ou le code central, mais bref.
- Reformule toujours le sommaire de la Cour ; ne le recopie pas.

---

## Format de sortie

### output/digest.html
Fragment HTML, styles **inline**, police lisible (Georgia/serif), largeur max
~720px. Applique ce **code couleur** (sobrement) :
- titres de section et mentions d'arrets -> **rouge `#C0392B`** ;
- references d'articles / de codes -> **vert `#27AE60`** ;
- points d'attention, echeances, entree en vigueur -> **orange `#E67E22`** ;
- definitions ou principes cles -> **bleu `#2471A3`**.

Structure, dans cet ordre :

1. **En-tete** : « Veille hebdomadaire droit des affaires — semaine du [debut] au
   [fin] » (titre rouge), en utilisant les dates du champ `periode` (format
   JJ/MM).

2. **Sommaire** : sous le titre, une **liste a tirets** recapitulant en une ligne
   chaque entree (textes puis arrets), pour une lecture en diagonale. Prefixe les
   lignes de jurisprudence par « — [Jurisprudence] … ».

3. **Section « Journal officiel de la semaine »** (titre rouge). Pour chaque texte
   retenu : un **titre editorial en gras**, un **resume de 3 phrases max**, et le
   lien « Voir le texte ». Si aucun texte retenu : « Rien de notable au Journal
   officiel cette semaine. »

4. **Section « Jurisprudence — chambre commerciale »** (titre rouge), **TOUJOURS
   presente**, meme vide. Pour chaque arret : un **titre editorial en gras**,
   **2 a 3 phrases** reformulant la solution (article central en vert), et le lien
   « Voir la decision ». Si vide : en gris, « Aucun arret nouveau de la chambre
   commerciale cette semaine. »

### output/subject.txt
Une seule ligne, p. ex.
`Veille hebdo droit des affaires — semaine du 16 au 22/06 (5 textes, 8 arrets)`.
Adapte les compteurs.

Termine une fois les deux fichiers ecrits.