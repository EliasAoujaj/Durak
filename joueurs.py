"""Les stratégies de jeu. Chaque stratégie est une sous-classe de Joueur."""

import random

from cartes import Carte, Couleur
from memoire import Memoire
from moteur import Action, EtatPartie, TypeAction, defenseur, non_battues


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


def contient_atout(action: Action, atout: Couleur) -> bool:
    return any(c.couleur == atout for c in action.cartes_jouees)


def de_type(actions: list[Action], type_action: TypeAction) -> list[Action]:
    return [a for a in actions if a.type_action == type_action]


# Les meilleurs réglages trouvés par recherche.py (61 % contre la version de base)
REGLAGES_RECHERCHE = dict(bonus_atout=20, pioche_fin=4, bonus_fin=5,
                          seuil_ajout=30, seuil_transfert=10, seuil_defense=30)


class JoueurPetit(Joueur):
    """Heuristique prudente et réglable : dépenser les cartes faibles, garder les fortes.

    Le coût d'une carte est sa valeur (6 à 14), plus un bonus si c'est un atout.
    Les réglages par défaut reproduisent la première version de ce joueur.

    Réglages :
    - bonus_atout : surcoût d'un atout en début et milieu de partie ;
    - pioche_fin : quand la pioche a au plus ce nombre de cartes, on entre en fin
      de partie (-1 : seulement quand la pioche est vide) ;
    - bonus_fin : surcoût d'un atout en fin de partie ;
    - seuil_ajout : en cours d'attaque, on n'ajoute que des cartes de coût inférieur ou égal ;
    - seuil_transfert : on ne transfère qu'avec des cartes de coût moyen inférieur ou égal ;
    - seuil_defense : hors fin de partie, si la défense la moins chère coûte plus que ça,
      on préfère prendre pour garder ses cartes fortes.
    """

    def __init__(self, bonus_atout=20, pioche_fin=-1, bonus_fin=20,
                 seuil_ajout=15, seuil_transfert=15, seuil_defense=100):
        self.bonus_atout = bonus_atout
        self.pioche_fin = pioche_fin
        self.bonus_fin = bonus_fin
        self.seuil_ajout = seuil_ajout
        self.seuil_transfert = seuil_transfert
        self.seuil_defense = seuil_defense

    def reglages(self) -> dict:
        """Les réglages du joueur, sous forme de dictionnaire."""
        return dict(vars(self))

    def nom(self) -> str:
        if self.reglages() == JoueurPetit().reglages():
            return "JoueurPetit"
        return "JoueurPetit*"

    # --- outils ---

    def en_fin_de_partie(self, etat: EtatPartie) -> bool:
        # pioche vide : toujours la fin de partie, sinon deux joueurs qui refusent de
        # défendre peuvent se renvoyer les mêmes cartes indéfiniment
        return not etat.pioche or len(etat.pioche) <= self.pioche_fin

    def cout_carte(self, carte: Carte, etat: EtatPartie) -> int:
        """Ce qu'on perd en jouant cette carte."""
        if carte.couleur != etat.atout:
            return carte.valeur
        bonus = self.bonus_fin if self.en_fin_de_partie(etat) else self.bonus_atout
        return carte.valeur + bonus

    def cout_moyen(self, action: Action, etat: EtatPartie) -> float:
        """Coût moyen par carte jouée : une paire de 7 est aussi « bon marché » qu'un 7 seul."""
        cartes = action.cartes_jouees
        return sum(self.cout_carte(c, etat) for c in cartes) / len(cartes)

    # --- décisions ---

    def choisir(self, etat: EtatPartie, moi: int, actions: list[Action]) -> Action:
        if moi == defenseur(etat):
            choix = self.choisir_defense(etat, actions)
        else:
            choix = self.choisir_attaque(etat, actions)
        # choix par défaut si aucune règle ne s'applique (par exemple une action inconnue)
        return choix if choix is not None else actions[0]

    def cout_attaque(self, action: Action, etat: EtatPartie) -> float:
        """Coût d'une attaque. Les sous-classes peuvent le modifier sans toucher au reste."""
        return self.cout_moyen(action, etat)

    def choisir_attaque(self, etat: EtatPartie, actions: list[Action]) -> Action | None:
        cout = lambda a: self.cout_attaque(a, etat)
        attaques = de_type(actions, TypeAction.ATTAQUER)
        if not etat.table:
            # attaque initiale : la moins chère par carte, et à coût égal la plus grosse
            return min(attaques, key=lambda a: (cout(a), -len(a.cartes_jouees)), default=None)
        # ajout en cours d'attaque : seulement des cartes assez peu chères
        ajouts = [a for a in attaques if cout(a) <= self.seuil_ajout]
        if ajouts:
            return min(ajouts, key=cout)
        passer = de_type(actions, TypeAction.PASSER)
        return passer[0] if passer else None

    def choisir_defense(self, etat: EtatPartie, actions: list[Action]) -> Action | None:
        cout = lambda a: self.cout_moyen(a, etat)
        prendre = Action(TypeAction.PRENDRE)

        # 1. transférer avec des cartes assez peu chères : l'adversaire hérite du problème
        transferts = [a for a in de_type(actions, TypeAction.TRANSFERER)
                      if cout(a) <= self.seuil_transfert]
        if transferts:
            return min(transferts, key=cout)

        # 2. si une attaque ne peut pas être battue, inutile de dépenser des cartes : prendre
        defenses = de_type(actions, TypeAction.DEFENDRE)
        cibles_couvertes = {a.cible for a in defenses}
        if any(att not in cibles_couvertes for att in non_battues(etat)):
            return prendre

        # 3. battre avec la carte la moins chère, sauf si elle est trop précieuse
        meilleure = min(defenses, key=cout, default=None)
        if (meilleure is not None and not self.en_fin_de_partie(etat)
                and cout(meilleure) > self.seuil_defense):
            return prendre
        return meilleure


class JoueurCompteur(JoueurPetit):
    """JoueurPetit qui compte les cartes : il préfère attaquer avec des cartes
    que l'adversaire ne pourra probablement pas battre.

    Tant que la pioche n'est pas vide, le comptage ne s'applique pas aux atouts :
    sinon le joueur les gaspille en attaque, parce qu'ils sont souvent imbattables
    (les mesures montrent qu'il perd alors nettement contre JoueurPetit).

    bonus_imbattable : de combien baisse le coût d'une carte sûre d'être imbattable
    (le coût baisse proportionnellement à la probabilité). Les autres réglages
    sont ceux de JoueurPetit.
    """

    def __init__(self, bonus_imbattable: float = 10, **reglages):
        super().__init__(**reglages)
        self.bonus_imbattable = bonus_imbattable
        self.memoire = None

    def nom(self) -> str:
        return "JoueurCompteur"

    def debut_partie(self, moi: int, nb_joueurs: int) -> None:
        self.memoire = Memoire(moi, nb_joueurs)   # une mémoire neuve à chaque partie

    def observer(self, etat: EtatPartie, joueur: int, action: Action) -> None:
        self.memoire.mettre_a_jour(etat, joueur, action)

    def cout_attaque(self, action: Action, etat: EtatPartie) -> float:
        cout = self.cout_moyen(action, etat)
        if etat.pioche and contient_atout(action, etat.atout):
            return cout
        adversaire = defenseur(etat)
        probas = [self.memoire.proba_imbattable(etat, c, adversaire) for c in action.cartes_jouees]
        reduction = self.bonus_imbattable * sum(probas) / len(probas)
        return cout - reduction
