"""Ce qu'un joueur sait de la partie, à partir de l'information publique uniquement."""

import random
from math import comb

from cartes import Carte, bat, nouveau_paquet
from moteur import Action, EtatPartie, TypeAction, cartes_triees, defenseur

PAQUET = frozenset(nouveau_paquet())


def cartes_sur_table(etat: EtatPartie) -> set[Carte]:
    return {carte for paire in etat.table for carte in paire if carte is not None}


class Memoire:
    """La mémoire d'un joueur : les cartes connues de la main de chaque adversaire.

    Elle se met à jour avec mettre_a_jour, à appeler pour chaque coup joué,
    AVANT qu'il soit appliqué (c'est ce que fait l'arène avec observer).
    """

    def __init__(self, moi: int, nb_joueurs: int):
        self.moi = moi
        self.connues: list[set[Carte]] = [set() for _ in range(nb_joueurs)]

    def mettre_a_jour(self, etat: EtatPartie, joueur: int, action: Action) -> None:
        if action.type_action in (TypeAction.ATTAQUER, TypeAction.DEFENDRE, TypeAction.TRANSFERER):
            # une carte jouée quitte la main de son joueur
            self.connues[joueur] -= action.cartes_jouees
        elif action.type_action == TypeAction.PASSER and etat.defenseur_prend:
            # fin d'une attaque où le défenseur a pris : il ramasse toute la table, sous nos yeux
            d = defenseur(etat)
            if d != self.moi:
                self.connues[d] |= cartes_sur_table(etat)

    def inconnues(self, etat: EtatPartie) -> set[Carte]:
        """Les cartes dont on ignore l'emplacement : mains adverses (partie cachée) et pioche."""
        visibles = set(etat.mains[self.moi]) | set(etat.defausse) | cartes_sur_table(etat)
        for j, cartes in enumerate(self.connues):
            if j != self.moi:
                visibles |= cartes
        return set(PAQUET) - visibles

    def cachees(self, etat: EtatPartie) -> set[Carte]:
        """Les inconnues qui peuvent être dans une main adverse.

        La carte du dessous de la pioche est visible : tant que la pioche n'est pas vide,
        on sait qu'elle n'est dans aucune main.
        """
        resultat = self.inconnues(etat)
        if etat.pioche:
            resultat.discard(etat.pioche[0])
        return resultat

    def nb_inconnues_en_main(self, etat: EtatPartie, joueur: int) -> int:
        """Combien de cartes de ce joueur nous sont inconnues (la taille d'une main est publique)."""
        return len(etat.mains[joueur]) - len(self.connues[joueur])

    def proba_imbattable(self, etat: EtatPartie, carte: Carte, adversaire: int) -> float:
        """Probabilité que l'adversaire n'ait aucune carte capable de battre `carte`.

        Ses cartes inconnues sont vues comme tirées au hasard parmi les cartes cachées :
        P = C(n - b, k) / C(n, k)   (loi hypergéométrique), avec
        n cartes cachées, dont b battent `carte`, et k cartes inconnues dans sa main.
        """
        if any(bat(carte, c, etat.atout) for c in self.connues[adversaire]):
            return 0.0
        cachees = self.cachees(etat)
        n = len(cachees)
        b = sum(bat(carte, c, etat.atout) for c in cachees)
        k = min(self.nb_inconnues_en_main(etat, adversaire), n)
        return comb(n - b, k) / comb(n, k)

    def tirer_monde(self, etat: EtatPartie, rng: random.Random) -> EtatPartie:
        """Un état complet tiré au hasard parmi ceux compatibles avec ce qu'on sait (2 joueurs).

        Les cartes cachées sont mélangées puis distribuées : d'abord de quoi compléter
        la main adverse (dont on connaît la taille et une partie des cartes), le reste
        forme la pioche, dans un ordre aléatoire, avec la carte du dessous à sa place.
        """
        assert len(etat.mains) == 2, "le tirage de mondes ne gère que 2 joueurs"
        adversaire = 1 - self.moi
        # tri avant mélange : l'ordre d'un set varie d'une exécution à l'autre,
        # on ne serait plus reproductible
        cachees = cartes_triees(self.cachees(etat))
        rng.shuffle(cachees)
        k = self.nb_inconnues_en_main(etat, adversaire)

        mains = [[], []]
        mains[self.moi] = list(etat.mains[self.moi])
        mains[adversaire] = cartes_triees(self.connues[adversaire]) + cachees[:k]
        # on pioche avec pop(), donc par la fin : la carte du dessous reste en position 0
        pioche = [etat.pioche[0]] + cachees[k:] if etat.pioche else []

        assert len(mains[adversaire]) == len(etat.mains[adversaire]), "mémoire incohérente"
        assert len(pioche) == len(etat.pioche), "mémoire incohérente"
        return EtatPartie(mains=mains, pioche=pioche, atout=etat.atout, table=list(etat.table),
                          defausse=[], attaquant=etat.attaquant,
                          defenseur_prend=etat.defenseur_prend, classement=list(etat.classement))
