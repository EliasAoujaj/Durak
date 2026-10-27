"""Recherche automatique des meilleurs réglages de JoueurPetit."""

import random
import time

from arene import demi_intervalle, match
from joueurs import JoueurPetit

# Les valeurs essayées pour chaque réglage
ESPACE = {
    "bonus_atout": [5, 10, 15, 20, 30],
    "pioche_fin": [-1, 0, 4, 8, 12],
    "bonus_fin": [0, 5, 10, 20],
    "seuil_ajout": [8, 10, 12, 15, 30],
    "seuil_transfert": [10, 12, 15, 30],
    "seuil_defense": [15, 20, 25, 30, 100],
}


def tirer_reglages(rng: random.Random) -> dict:
    """Un réglage au hasard pour chaque paramètre."""
    return {nom: rng.choice(valeurs) for nom, valeurs in ESPACE.items()}


def evaluer(reglages: dict, n_donnes: int) -> float:
    """Taux de victoire de ces réglages contre la version de base."""
    resultats = match([JoueurPetit(**reglages), JoueurPetit()], n_donnes)
    return resultats[0].taux_victoire


def recherche(n_candidats: int, n_donnes: int, n_finalistes: int, n_donnes_finale: int,
              seed: int = 0) -> None:
    rng = random.Random(seed)
    debut = time.perf_counter()

    # Tour 1 : beaucoup de candidats, évalués rapidement
    candidats = []
    for i in range(n_candidats):
        reglages = tirer_reglages(rng)
        taux = evaluer(reglages, n_donnes)
        candidats.append((taux, reglages))
        print(f"[{i + 1}/{n_candidats}] {taux:.1%}  {reglages}")
    candidats.sort(key=lambda c: c[0], reverse=True)

    # Tour 2 : les meilleurs, réévalués sur des donnes nouvelles et plus nombreuses
    print(f"\nFinale : les {n_finalistes} meilleurs sur {n_donnes_finale} nouvelles donnes")
    finalistes = []
    for taux_tour1, reglages in candidats[:n_finalistes]:
        resultats = match([JoueurPetit(**reglages), JoueurPetit()], n_donnes_finale,
                          seed_depart=1_000_000)
        taux = resultats[0].taux_victoire
        marge = demi_intervalle(taux, resultats[0].parties)
        finalistes.append((taux, reglages))
        print(f"tour 1 : {taux_tour1:.1%}   finale : {taux:.1%} ± {marge:.1%}   {reglages}")

    meilleur_taux, meilleurs = max(finalistes, key=lambda c: c[0])
    print(f"\nMeilleurs réglages : {meilleurs}")
    print(f"Taux de victoire contre la version de base : {meilleur_taux:.1%}")
    print(f"Durée totale : {time.perf_counter() - debut:.0f} s")


if __name__ == "__main__":
    recherche(n_candidats=60, n_donnes=500, n_finalistes=5, n_donnes_finale=3000)
