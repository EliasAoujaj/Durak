"""Mesure l'apport du PIMC quand la pioche est presque vide."""

import time

from arene import afficher, match, nouvel_executeur
from joueurs import JoueurFinal, JoueurPimc, REGLAGES_RECHERCHE

N_DIAGNOSTIC = 10     # donnes par réglage pour le diagnostic (20 parties)
N_MATCH = 1000        # donnes du vrai match (2000 parties)

# réglages essayés : (pioche_max, n_mondes)
ESSAIS = []   # diagnostic déjà fait
REGLAGE_MATCH = dict(pioche_max=2, n_mondes=10)   # à ajuster d'après le diagnostic

def diagnostic(pioche_max: int, n_mondes: int) -> None:
    pimc = JoueurPimc(pioche_max=pioche_max, n_mondes=n_mondes, **REGLAGES_RECHERCHE)
    debut = time.perf_counter()
    match([pimc, JoueurFinal(**REGLAGES_RECHERCHE)], n_donnes=N_DIAGNOSTIC)
    ms = (time.perf_counter() - debut) / (2 * N_DIAGNOSTIC) * 1000
    total = pimc.pimc_decisions + pimc.pimc_abandons
    print(f"pioche_max={pioche_max} n_mondes={n_mondes:<3} {ms:7.0f} ms par partie   "
          f"décisions PIMC {total:4}   abandons {pimc.pimc_abandons / max(total, 1):6.1%}   "
          f"mondes abandonnés {pimc.mondes_abandonnes / max(pimc.mondes_tentes, 1):6.1%}")


if __name__ == "__main__":
    print("Diagnostic (un cœur) :")
    for pioche_max, n_mondes in ESSAIS:
        diagnostic(pioche_max, n_mondes)

    with nouvel_executeur() as executeur:
        debut = time.perf_counter()
        resultats = match([JoueurPimc(**REGLAGE_MATCH, **REGLAGES_RECHERCHE),
                           JoueurFinal(**REGLAGES_RECHERCHE)],
                          n_donnes=N_MATCH, executeur=executeur)
        print(f"\nMatch avec {REGLAGE_MATCH} : {time.perf_counter() - debut:.0f} s")
        afficher(resultats)
