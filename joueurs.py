"""Les stratégies de jeu. Chaque stratégie est une sous-classe de Joueur."""

import random

from moteur import Action, EtatPartie


class Joueur:
    """Interface commune à toutes les stratégies.

    Un joueur ne doit utiliser que l'information à laquelle il a droit :
    sa propre main, la table, l'atout, la défausse, la taille de la pioche
    et le nombre de cartes des autres joueurs. Jamais leurs mains ni le
    contenu de la pioche.
    """

    def debut_partie(self, moi: int, nb_joueurs: int) -> None:
        """Appelée au début de chaque partie : sert à réinitialiser la mémoire du joueur."""
        pass

    def choisir(self, etat: EtatPartie, moi: int, actions: list[Action]) -> Action:
        """Renvoie l'action choisie parmi les actions légales."""
        raise NotImplementedError

    def observer(self, etat: EtatPartie, joueur: int, action: Action) -> None:
        """Appelée pour chaque coup joué par n'importe quel joueur, avant qu'il soit appliqué."""
        pass

    def nom(self) -> str:
        """Nom affiché dans les résultats : par défaut, le nom de la classe."""
        return type(self).__name__


class JoueurAleatoire(Joueur):
    """Choisit une action légale au hasard. Sert de référence et de test pour le moteur."""

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def choisir(self, etat: EtatPartie, moi: int, actions: list[Action]) -> Action:
        return self.rng.choice(actions)
