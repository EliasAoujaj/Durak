"""Plan d'expériences factoriel : on mesure TOUTES les combinaisons de règles de
JoueurAmeliore contre JoueurPetit réglé, pour estimer l'effet de chaque règle
et les interactions entre règles (une règle vaut-elle plus, ou moins, quand une
autre est présente ?)."""

import math
import time
from itertools import combinations
from statistics import mean

from arene import demi_intervalle, match, nouvel_executeur
from joueurs import JoueurAmeliore, JoueurPetit, REGLAGES_RECHERCHE, REGLES_AMELIORATION

N_DONNES = 2000          # par combinaison : 4000 parties
N_DONNES_FINALE = 10000  # pour la vérification finale : 20 000 parties
REGLES = REGLES_AMELIORATION


def evaluer(avec: frozenset, n_donnes: int, seed_depart: int) -> float:
    """Taux de victoire d'une combinaison de règles contre JoueurPetit réglé.
    Toutes les combinaisons jouent les MÊMES donnes : leurs écarts ne viennent pas du hasard des cartes."""
    return match([JoueurAmeliore(avec=tuple(avec)), JoueurPetit(**REGLAGES_RECHERCHE)],
                 n_donnes, seed_depart)[0].taux_victoire


if __name__ == "__main__":
    lignes = []

    def ecrire(texte: str = "") -> None:
        print(texte)
        lignes.append(texte)

    combos = [frozenset(r for i, r in enumerate(REGLES) if (masque >> i) & 1)
              for masque in range(2 ** len(REGLES))]
    debut = time.perf_counter()
    with nouvel_executeur() as executeur:
        taches = {c: executeur.submit(evaluer, c, N_DONNES, 0) for c in combos}
        taux = {c: t.result() for c, t in taches.items()}
        ecrire(f"{len(combos)} combinaisons mesurées en {time.perf_counter() - debut:.0f} s "
               f"({2 * N_DONNES} parties chacune)")

        # incertitude d'une mesure (loi binomiale), puis des moyennes de plusieurs mesures
        v = 0.25 / (2 * N_DONNES)
        ic_effet = 1.96 * math.sqrt(4 * v / len(combos))           # moyenne de 64 contre 64
        ic_interaction = 1.96 * math.sqrt(16 * v / len(combos))    # 4 moyennes de 32

        # 1. effets principaux
        base = taux[frozenset()]
        ecrire(f"\nRéférence, aucune règle : {base:.1%} (doit être proche de 50 %)")
        ecrire(f"\n1. EFFET DE CHAQUE RÈGLE (moyenne sur toutes les combinaisons, ± {ic_effet:.1%})")
        effets = {}
        for r in REGLES:
            effets[r] = (mean(t for c, t in taux.items() if r in c)
                         - mean(t for c, t in taux.items() if r not in c))
        for r, e in sorted(effets.items(), key=lambda x: -x[1]):
            verdict = "utile" if e > ic_effet else ("nuisible" if e < -ic_effet else "sans effet net")
            ecrire(f"   {r:<26} {e:+6.1%}   {verdict}")

        # 2. interactions entre paires de règles
        ecrire(f"\n2. INTERACTIONS (de combien l'effet de A change quand B est présente, ± {ic_interaction:.1%})")
        interactions = []
        for a, b in combinations(REGLES, 2):
            cellule = lambda avec_a, avec_b: mean(
                t for c, t in taux.items() if (a in c) == avec_a and (b in c) == avec_b)
            delta = ((cellule(True, True) - cellule(False, True))
                     - (cellule(True, False) - cellule(False, False)))
            interactions.append((delta, a, b))
        interactions.sort(key=lambda x: -abs(x[0]))
        for delta, a, b in interactions[:10]:
            marque = "  ← significatif" if abs(delta) > ic_interaction else ""
            sens = "plus utile" if delta > 0 else "moins utile"
            ecrire(f"   {a} est {sens} avec {b} : {delta:+.1%}{marque}")

        # 3. meilleures combinaisons
        ecrire("\n3. LES 5 MEILLEURES COMBINAISONS (premier tour)")
        classement = sorted(taux.items(), key=lambda x: -x[1])
        for c, t in classement[:5]:
            ecrire(f"   {t:6.1%}   {sorted(c) or 'aucune règle'}")

        # 4. vérification sur des donnes neuves (contre la malédiction du vainqueur)
        utiles = frozenset(r for r, e in effets.items() if e > ic_effet)
        finalistes = [c for c, _ in classement[:3]]
        if utiles not in finalistes:
            finalistes.append(utiles)
        ecrire(f"\n4. VÉRIFICATION sur {2 * N_DONNES_FINALE} parties neuves")
        for c in finalistes:
            res = match([JoueurAmeliore(avec=tuple(c)), JoueurPetit(**REGLAGES_RECHERCHE)],
                        N_DONNES_FINALE, seed_depart=1_000_000, executeur=executeur)[0]
            nom = "règles utiles seules" if c == utiles else "combinaison du classement"
            ecrire(f"   {res.taux_victoire:6.1%} ± {demi_intervalle(res.taux_victoire, res.parties):.1%}"
                   f"   {sorted(c) or 'aucune règle'}   ({nom})")

    ecrire(f"\nDurée totale : {time.perf_counter() - debut:.0f} s")
    with open("plan_experiences.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")
    print("Rapport enregistré dans plan_experiences.txt")
