"""Les joueurs experts gagnent-ils à utiliser les règles validées dans leur heuristique ?"""

import time

from arene import afficher, match, nouvel_executeur
from joueurs import (JoueurFinal, JoueurFinalAmeliore, JoueurPimcAmeliore, REGLAGES_RECHERCHE)

N_DONNES = 5000      # JoueurFinal+ contre JoueurFinal : 10 000 parties, environ 1 à 2 minutes
AVEC_PIMC = False    # True : aussi JoueurPimc+ contre JoueurFinal (lent : environ 20 minutes)
N_DONNES_PIMC = 1000

if __name__ == "__main__":
    with nouvel_executeur() as executeur:
        debut = time.perf_counter()
        afficher(match([JoueurFinalAmeliore(), JoueurFinal(**REGLAGES_RECHERCHE)],
                       N_DONNES, executeur=executeur))
        print(f"({time.perf_counter() - debut:.0f} s)")

        if AVEC_PIMC:
            # à comparer aux 56,3 % de JoueurPimc contre JoueurFinal
            debut = time.perf_counter()
            print()
            afficher(match([JoueurPimcAmeliore(pioche_max=2), JoueurFinal(**REGLAGES_RECHERCHE)],
                           N_DONNES_PIMC, executeur=executeur))
            print(f"({time.perf_counter() - debut:.0f} s)")
