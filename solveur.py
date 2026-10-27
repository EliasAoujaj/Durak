"""Résolution exacte de la fin de partie à 2 joueurs, quand la pioche est vide.

La pioche vide, chaque joueur connaît la main de l'autre (grâce au comptage) :
le jeu devient à information parfaite et sans hasard. On peut alors explorer
tous les coups possibles jusqu'à la fin (minimax) et jouer parfaitement.
"""

from moteur import (Action, EtatPartie, TypeAction, actions_legales, appliquer, fin_de_partie,
                    joueur_actif)

GAGNE, NUL, PERDU = 1, 0, -1
PROFONDEUR_MAX = 500   # au-delà, on abandonne (et on évite la limite de récursion de Python)


class BudgetDepasse(Exception):
    """Levée quand la recherche est trop longue : le joueur se rabat sur son heuristique."""


def copier(etat: EtatPartie) -> EtatPartie:
    """Une copie indépendante de l'état, bien plus rapide que copy.deepcopy.

    Les cartes ne sont pas copiées : elles sont gelées, on peut les partager sans risque.
    Seules les listes, qui sont modifiées par appliquer, doivent être neuves.
    """
    return EtatPartie(
        mains=[list(main) for main in etat.mains],
        pioche=list(etat.pioche),
        atout=etat.atout,
        table=list(etat.table),
        defausse=list(etat.defausse),
        attaquant=etat.attaquant,
        defenseur_prend=etat.defenseur_prend,
        classement=list(etat.classement),
    )


PRIORITE = {TypeAction.TRANSFERER: 0, TypeAction.DEFENDRE: 1, TypeAction.ATTAQUER: 1,
            TypeAction.PASSER: 2, TypeAction.PRENDRE: 3}


def ordonner(actions: list[Action], atout) -> list[Action]:
    """Les coups dans l'ordre où il vaut mieux les examiner : les plus prometteurs d'abord
    (transférer, battre ou attaquer avec des petites cartes ; prendre en dernier).
    Bien ordonner ne change pas le résultat, mais déclenche les coupures bien plus tôt."""
    def cle(action: Action):
        cout = sum(c.valeur + (20 if c.couleur == atout else 0) for c in action.cartes_jouees)
        return (PRIORITE[action.type_action], cout)
    return sorted(actions, key=cle)


def cle_position(etat: EtatPartie) -> tuple:
    """Une clé de dictionnaire qui identifie la position.

    Elle ne retient que ce qui compte pour la suite de la partie : les mains,
    la table (sans ordre), qui attaque et si le défenseur a pris. La défausse
    n'influence plus rien, et l'atout ne change pas pendant une partie.
    """
    return (frozenset(etat.mains[0]), frozenset(etat.mains[1]), frozenset(etat.table),
            etat.attaquant, etat.defenseur_prend)


class Solveur:
    """Minimax avec mémoïsation, du point de vue du joueur `moi`.

    Une position vaut GAGNE si `moi` gagne en jouant parfaitement contre un adversaire
    parfait, PERDU s'il perd quoi qu'il fasse, NUL si la partie peut tourner en rond.

    Le cache garde les positions déjà résolues : on le conserve pendant toute une partie,
    car les décisions successives retombent sur les mêmes positions.

    Approximation : une position qui revient sur le chemin en cours (une boucle) est
    comptée nulle, et ce résultat est mis en cache. C'est exact dans presque tous les cas,
    mais pas garanti ; les boucles sont de toute façon très rares en fin de partie.
    """

    def __init__(self, moi: int, budget: int):
        self.moi = moi
        self.budget = budget      # nombre maximal de positions explorées par décision
        self.cache: dict[tuple, int] = {}
        self.noeuds = 0
        self.chemin: set[tuple] = set()

    def evaluer(self, etat: EtatPartie) -> int:
        """Valeur exacte de la position (lève BudgetDepasse si c'est trop long)."""
        self.noeuds = 0
        self.chemin = set()
        return self._valeur(copier(etat))

    def meilleure_action(self, etat: EtatPartie, actions: list[Action],
                         preferee: Action | None = None) -> Action:
        """L'action de plus grande valeur. À valeur égale, on garde `preferee`
        (le choix de l'heuristique), pour jouer naturellement quand tout se vaut."""
        self.noeuds = 0
        self.chemin = {cle_position(etat)}
        ordre = list(actions)
        if preferee in ordre:   # l'examiner en premier : souvent la bonne, et on s'arrête plus tôt
            ordre.remove(preferee)
            ordre.insert(0, preferee)

        meilleure, meilleure_valeur = ordre[0], PERDU - 1
        for action in ordre:
            suivant = copier(etat)
            appliquer(suivant, action)
            v = self._valeur(suivant)
            if v > meilleure_valeur:
                meilleure, meilleure_valeur = action, v
                if v == GAGNE:
                    break   # impossible de faire mieux
        return meilleure

    def _valeur(self, etat: EtatPartie) -> int:
        terminee, classement = fin_de_partie(etat)
        if terminee:
            return GAGNE if classement[0] == self.moi else PERDU

        cle = cle_position(etat)
        if cle in self.cache:
            return self.cache[cle]
        if cle in self.chemin:
            return NUL   # on est revenu à une position déjà sur le chemin : boucle

        self.noeuds += 1
        if self.noeuds > self.budget or len(self.chemin) > PROFONDEUR_MAX:
            raise BudgetDepasse

        self.chemin.add(cle)
        je_joue = joueur_actif(etat) == self.moi
        # je cherche le maximum de ma valeur, l'adversaire le minimum
        meilleure = PERDU - 1 if je_joue else GAGNE + 1
        for action in ordonner(actions_legales(etat), etat.atout):
            suivant = copier(etat)
            appliquer(suivant, action)
            v = self._valeur(suivant)
            if je_joue:
                meilleure = max(meilleure, v)
                if meilleure == GAGNE:
                    break   # coupure : j'ai trouvé un coup gagnant, inutile de chercher plus
            else:
                meilleure = min(meilleure, v)
                if meilleure == PERDU:
                    break   # coupure : l'adversaire a un coup qui me fait perdre
        self.chemin.remove(cle)

        self.cache[cle] = meilleure
        return meilleure
