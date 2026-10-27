"""Mesure l'apport du comptage des cartes, selon la valeur de bonus_imbattable."""

import time

from arene import afficher, match, nouvel_executeur
from joueurs import JoueurCompteur, JoueurPetit, REGLAGES_RECHERCHE

if __name__ == "__main__":
    with nouvel_executeur() as executeur:
        for bonus in [0, 5, 10, 20]:
            debut = time.perf_counter()
            resultats = match([JoueurCompteur(bonus, **REGLAGES_RECHERCHE),
                               JoueurPetit(**REGLAGES_RECHERCHE)],
                              n_donnes=10_000, executeur=executeur)
            print(f"\nbonus_imbattable = {bonus}   ({time.perf_counter() - debut:.0f} s)")
            afficher(resultats)
