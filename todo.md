# Plan : Développement du jeu Taboo

## TL;DR
Créer un jeu Taboo jouable sur smartphone, hébergé sur GitHub Pages. Architecture simple : (1) fichier JSON statique avec 3000 cartes, (2) interface web légère avec minuteur 2min et score, (3) génération via OpenAI gpt-4o-mini par lots de 50 avec validation locale. Budget ~5 $.

---

## Steps

### Phase 1 : Calibration & Préparation (2–3 jours)
1. Télécharger lexique français (Lexique 3), filtrer NOM/VERBE/ADJ, créer `mots_sources.json` (3000 mots + rang fréquence + niveau)
2. Écrire script Python : `generate_cards.py` avec validation locale stricte (5 interdits, pas variante du mot cible, pas génériques)
3. Calibration sur 10 cartes : mesurer taux rejet réel, coût, ajuster prompt

### Phase 2 : Génération des 3000 cartes (1 jour + runtime API)
4. Lancer script par lots de 50 (60 lots total) via gpt-4o-mini
5. Post-traitement : vérifier doublons, distribution niveaux, sampling manuel 20–30 cartes

### Phase 3 : Interface web (2–3 jours)
6. Créer `index.html` + `style.css` + `game.js` (mobile-first responsive)
7. Implémenter : affichage mot + 5 interdits, minuteur 2min, boutons "Deviné"/"Passer", score live, fin partie + restart

### Phase 4 : Déploiement GitHub Pages (1 jour)
8. Repo GitHub + activation Pages, fichiers : `index.html`, `style.css`, `game.js`, `cards.json`
9. Tester accès https://[username].github.io/taboo

### Phase 5 : Tests (1–2 jours)
10. Tests manuels desktop + mobile (Chrome, Safari)
11. Tests qualité : 50 cartes jouées réellement, vérifier pertinence des interdits

---

## Relevant files
- `data/mots_sources.json` — 3000 mots source (rang fréquence + niveau)
- `scripts/generate_cards.py` — Pipeline génération (lots → API → validation)
- `index.html` — Page jeu
- `style.css` — Responsive mobile-first
- `game.js` — Logique jeu (minuteur, score, transitions)
- `cards.json` — 3000 cartes finales

---

## Verification
1. Phase 1 : Premier lot 10 cartes OK, taux rejet <10%, coût estimé <5 $
2. Phase 2 : 3000 cartes générées, ~1000 par niveau, <2% bizarres, coût final <5 $
3. Phase 3 : Jeu jouable mobile + desktop, minuteur exact, score OK, restart OK
4. Phase 4 : GitHub Pages actif, cartes chargées sans erreur
5. Phase 5 : 3 parties test sans bug, variance >80% entre rejeu

---

## Decisions
- Lexique : Lexique 3 (français, public, fiable)
- Modèle : gpt-4o-mini (coût/qualité optimal)
- Lot : 50 mots par appel API
- Niveaux : 3 tranches par rang fréquence
- Stockage : JSON statique GitHub Pages (pas backend)
- Minuteur : 2 min/partie (pas par carte)
- Plateforme : Web mobile-first

---

## Further Considerations
1. **V2 packs thématiques** — Sport, Cinéma, Sciences. Ne pas bloquer v1, mais folder structure prête.
2. **Performance** — 3000 cartes ~500 KB OK, considérer compression si >10k futures.
3. **Analytics (optionnel)** — Pas prioritaire v1.




# Lancement en test :
Depuis le dossier du projet, lance :

python3 -m http.server 8000

Puis ouvre dans le navigateur :

http://localhost:8000/



Point important :


Le script lit OPENAI_API_KEY depuis les variables d’environnement. Si ta clé est seulement dans .env, pense à charger ce fichier avant d’exécuter le script, par exemple :

source .env




# Gestion du python 
source .venv/bin/activate
python -m pip install -r requirements.txt

Vérif : 
which python
python -m pip --version


# Création de nouvelles cartes :
Si votre objectif est d’atteindre 6000 cartes valides dans cards.json, le plus simple est de relancer sur la fenêtre complète 1 à 6000 ; le script sautera les déjà présentes et tentera uniquement les manquantes :

source .venv/bin/activate
python scripts/generate_cards.py \
  --start 0 \
  --count 6000 \
  --batch-size 50 \
  --output cards.json \
  --rejected data/rejected_cards.json

NB les ''' sont importants
Puis vérifiez :
python scripts/validate_cards.py --cards cards.json