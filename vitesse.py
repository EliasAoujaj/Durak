"""Compare les deux solveurs, puis mesure ce que permet le solveur rapide."""

import time

from arene import match
from joueurs import JoueurCompteur, JoueurFinal, JoueurPetit, REGLAGES_RECHERCHE
from moteur import actions_legales, appliquer, fin_de_partie, joueur_actif, nouvelle_partie
from rapide import SolveurRapide
from solveur import BudgetDepasse, Solveur, copier


def fins_de_partie(n, max_cartes):
    """Les positions où la pioche vient de se vider, dans des parties entre heuristiques."""
    positions = []
    seed = 0
    while len(positions) < n:
        etat = nouvelle_partie(seed)
        seed += 1
        joueur = JoueurPetit(**REGLAGES_RECHERCHE)
        for _ in range(2_000):   # garde-fou : les règles permettent des boucles infinies
            if fin_de_partie(etat)[0]:
                break
            if not etat.pioche and not etat.table:
                if sum(len(m) for m in etat.mains) <= max_cartes:
                    positions.append(copier(etat))
                break
            actif = joueur_actif(etat)
            appliquer(etat, joueur.choisir(etat, actif, actions_legales(etat)))
    return positions


def chronometrer(classe, positions, budget):
    debut = time.perf_counter()
    valeurs = []
    for etat in positions:
        try:
            valeurs.append(classe(etat.attaquant, budget).evaluer(etat))
        except BudgetDepasse:
            valeurs.append(None)
    return time.perf_counter() - debut, valeurs


if __name__ == "__main__":
    # 1. Les deux solveurs sur les mêmes positions
    positions = fins_de_partie(100, 10)
    t_lent, v_lent = chronometrer(Solveur, positions, 200_000)
    t_rapide, v_rapide = chronometrer(SolveurRapide, positions, 200_000)
    differences = sum(a != b for a, b in zip(v_lent, v_rapide) if a is not None and b is not None)
    print(f"100 fins de partie (au plus 10 cartes) : lent {t_lent:.1f} s, rapide {t_rapide:.1f} s, "
          f"accélération x{t_lent / t_rapide:.1f}, valeurs différentes : {differences}")

    # 2. Ce que le solveur rapide permet : JoueurFinal avec des fins de partie plus grosses
    print("\nJoueurFinal rapide contre JoueurCompteur (25 donnes, un cœur) :")
    for max_cartes in [12, 14, 16, 18]:
        final = JoueurFinal(max_cartes=max_cartes, **REGLAGES_RECHERCHE)
        debut = time.perf_counter()
        match([final, JoueurCompteur(**REGLAGES_RECHERCHE)], n_donnes=25)
        ms = (time.perf_counter() - debut) / 50 * 1000
        total = final.resolus + final.abandons + final.ignorees
        print(f"max_cartes={max_cartes:<3} {ms:6.0f} ms par partie   "
              f"résolues {final.resolus / total:6.1%}   abandons {final.abandons / total:6.1%}   "
              f"trop grosses {final.ignorees / total:6.1%}")
