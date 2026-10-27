"""Mesure l'apport du minimax en fin de partie."""

import time

from arene import afficher, match, nouvel_executeur
from joueurs import JoueurCompteur, JoueurFinal, REGLAGES_RECHERCHE

N_DIAGNOSTIC = 25     # donnes par réglage pour le diagnostic (50 parties)
N_MATCH = 2000        # donnes du vrai match (4000 parties)
MAX_CARTES = 12       # réglage utilisé pour le vrai match : à ajuster d'après le diagnostic


def diagnostic(max_cartes: int) -> None:
    """Vitesse et répartition des décisions de fin de partie, sur un seul cœur."""
    final = JoueurFinal(max_cartes=max_cartes, **REGLAGES_RECHERCHE)
    debut = time.perf_counter()
    match([final, JoueurCompteur(**REGLAGES_RECHERCHE)], n_donnes=N_DIAGNOSTIC)
    ms = (time.perf_counter() - debut) / (2 * N_DIAGNOSTIC) * 1000
    total = final.resolus + final.abandons + final.ignorees
    print(f"max_cartes={max_cartes:<3} {ms:6.0f} ms par partie   "
          f"résolues {final.resolus / total:6.1%}   abandons {final.abandons / total:6.1%}   "
          f"trop grosses {final.ignorees / total:6.1%}")


if __name__ == "__main__":
    print("Diagnostic (un cœur) :")
    for max_cartes in [8, 10, 12, 14]:
        diagnostic(max_cartes)

    with nouvel_executeur() as executeur:
        debut = time.perf_counter()
        resultats = match([JoueurFinal(max_cartes=MAX_CARTES, **REGLAGES_RECHERCHE),
                           JoueurCompteur(**REGLAGES_RECHERCHE)],
                          n_donnes=N_MATCH, executeur=executeur)
        print(f"\nMatch avec max_cartes={MAX_CARTES} : {time.perf_counter() - debut:.0f} s")
        afficher(resultats)
