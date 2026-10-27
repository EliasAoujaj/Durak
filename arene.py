"""Fait s'affronter des stratégies et mesure leurs performances."""

import math
import os
import time
from concurrent.futures import Executor, ProcessPoolExecutor
from dataclasses import dataclass

from joueurs import Joueur, JoueurAleatoire, JoueurPetit
from moteur import actions_legales, appliquer, fin_de_partie, joueur_actif, nouvelle_partie

MAX_COUPS = 10_000   # garde-fou contre une partie qui ne se terminerait jamais


def jouer_partie(seed: int, joueurs: list[Joueur]) -> list[int]:
    """Joue une partie complète. joueurs[p] contrôle la place p.

    Renvoie le classement : la liste des places, de la première à la dernière.
    """
    etat = nouvelle_partie(seed)
    for place, joueur in enumerate(joueurs):
        joueur.debut_partie(place, len(joueurs))

    for _ in range(MAX_COUPS):
        terminee, classement = fin_de_partie(etat)
        if terminee:
            return classement
        actif = joueur_actif(etat)
        actions = actions_legales(etat)
        action = joueurs[actif].choisir(etat, actif, actions)
        if action not in actions:
            raise ValueError(f"{joueurs[actif].nom()} a joué une action illégale : {action}")
        for place, joueur in enumerate(joueurs):
            joueur.observer(etat, actif, action)
        appliquer(etat, action)

    raise RuntimeError(f"partie trop longue, graine {seed}")


@dataclass
class Resultat:
    """Bilan d'un joueur sur un match."""
    nom: str
    parties: int
    somme_positions: int = 0   # 0 = premier, N - 1 = durak
    victoires: int = 0
    duraks: int = 0

    @property
    def position_moyenne(self) -> float:
        return self.somme_positions / self.parties

    @property
    def taux_victoire(self) -> float:
        return self.victoires / self.parties

    @property
    def taux_durak(self) -> float:
        return self.duraks / self.parties


def demi_intervalle(p: float, n: int) -> float:
    """Demi-largeur de l'intervalle de confiance à 95 % d'une proportion p mesurée sur n essais."""
    return 1.96 * math.sqrt(p * (1 - p) / n)


def match(joueurs: list[Joueur], n_donnes: int, seed_depart: int = 0,
          executeur: Executor | None = None) -> list[Resultat]:
    """Fait jouer les joueurs sur n_donnes donnes.

    Chaque donne est jouée autant de fois qu'il y a de joueurs, en décalant
    tout le monde d'une place à chaque fois : chacun occupe chaque place
    avec les mêmes cartes, ce qui supprime l'avantage de la donne et de la position.
    Les joueurs doivent être des objets distincts (deux instances, pas deux fois la même).

    Si un executeur est fourni, les donnes sont réparties entre plusieurs processus.
    """
    if executeur is None:
        return match_sequentiel(joueurs, n_donnes, seed_depart)

    # découpage en blocs de donnes consécutives, un peu plus nombreux que les
    # processus pour que tous les cœurs restent occupés jusqu'au bout
    n_blocs = min(n_donnes, 4 * nombre_coeurs())
    bornes = [seed_depart + n_donnes * i // n_blocs for i in range(n_blocs + 1)]
    taches = [executeur.submit(match_sequentiel, joueurs, fin - debut, debut)
              for debut, fin in zip(bornes, bornes[1:]) if fin > debut]
    return fusionner([tache.result() for tache in taches])


def match_sequentiel(joueurs: list[Joueur], n_donnes: int, seed_depart: int) -> list[Resultat]:
    """Le match joué entièrement dans le processus courant."""
    n = len(joueurs)
    if len({id(j) for j in joueurs}) != n:
        raise ValueError("chaque place doit avoir son propre objet joueur")

    resultats = [Resultat(j.nom(), parties=n_donnes * n) for j in joueurs]
    for seed in range(seed_depart, seed_depart + n_donnes):
        for r in range(n):
            places = joueurs[r:] + joueurs[:r]   # à la place p : le joueur d'origine (p + r) % n
            classement = jouer_partie(seed, places)
            for position, place in enumerate(classement):
                res = resultats[(place + r) % n]
                res.somme_positions += position
                res.victoires += position == 0
                res.duraks += position == n - 1
    return resultats


def fusionner(blocs: list[list[Resultat]]) -> list[Resultat]:
    """Additionne les résultats de plusieurs blocs de donnes, joueur par joueur."""
    total = [Resultat(res.nom, parties=0) for res in blocs[0]]
    for bloc in blocs:
        for t, res in zip(total, bloc):
            t.parties += res.parties
            t.somme_positions += res.somme_positions
            t.victoires += res.victoires
            t.duraks += res.duraks
    return total


def nombre_coeurs() -> int:
    return os.cpu_count() or 1


def nouvel_executeur(processus: int | None = None) -> ProcessPoolExecutor:
    """Un groupe de processus prêt à travailler. À utiliser avec « with ».

    Sous Windows, il ne doit être créé que dans le bloc if __name__ == "__main__".
    """
    return ProcessPoolExecutor(max_workers=processus or nombre_coeurs())


def afficher(resultats: list[Resultat]) -> None:
    for res in resultats:
        print(f"{res.nom:<20} victoires {res.taux_victoire:6.1%} "
              f"± {demi_intervalle(res.taux_victoire, res.parties):.1%}   "
              f"durak {res.taux_durak:6.1%}   position moyenne {res.position_moyenne:.3f}")


if __name__ == "__main__":
    joueurs = [JoueurPetit(), JoueurAleatoire(1)]

    debut = time.perf_counter()
    resultats = match(joueurs, n_donnes=2000)
    duree_seq = time.perf_counter() - debut
    print(f"Un seul cœur : {duree_seq:.1f} s")
    afficher(resultats)

    with nouvel_executeur() as executeur:
        debut = time.perf_counter()
        resultats = match(joueurs, n_donnes=2000, executeur=executeur)
        duree_par = time.perf_counter() - debut
    print(f"\n{nombre_coeurs()} cœurs : {duree_par:.1f} s  (accélération x{duree_seq / duree_par:.1f})")
    afficher(resultats)
