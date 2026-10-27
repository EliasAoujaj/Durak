"""Les stratégies de jeu. Chaque stratégie est une sous-classe de Joueur."""

import random

from cartes import Carte, Couleur, bat
from memoire import Memoire
from moteur import Action, EtatPartie, TypeAction, cartes_triees, defenseur, non_battues
from rapide import SolveurRapide
from solveur import BudgetDepasse, Solveur


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


class JoueurFinal(JoueurCompteur):
    """JoueurCompteur qui joue parfaitement la fin de partie.

    Tant que la pioche n'est pas vide, il joue comme JoueurCompteur. Ensuite, il
    reconstitue la main adverse grâce à sa mémoire et la résout avec le minimax.
    Si la recherche dépasse `budget` positions pour une décision, il se rabat
    sur son heuristique. Il ne tente même pas la recherche quand les deux mains
    réunies comptent plus de `max_cartes` cartes : elle serait presque toujours
    abandonnée, après avoir coûté beaucoup de temps.
    Ne fonctionne qu'à 2 joueurs (sinon : JoueurCompteur).

    `rapide` choisit le solveur en entiers (rapide.py) plutôt que le solveur d'origine.

    Les compteurs `resolus`, `abandons` et `ignorees` comptent les décisions prises
    par le minimax, celles où le budget a été dépassé, et celles jugées trop grosses.
    """

    def __init__(self, budget: int = 100_000, max_cartes: int = 16, rapide: bool = True,
                 **reglages):
        super().__init__(**reglages)
        self.budget = budget
        self.max_cartes = max_cartes
        # le solveur rapide (rapide.py) donne les mêmes résultats, en beaucoup plus vite
        self.classe_solveur = SolveurRapide if rapide else Solveur
        self.solveur = None
        self.resolus = 0
        self.abandons = 0
        self.ignorees = 0

    def nom(self) -> str:
        return "JoueurFinal" if self.classe_solveur is SolveurRapide else "JoueurFinal(lent)"

    def debut_partie(self, moi: int, nb_joueurs: int) -> None:
        super().debut_partie(moi, nb_joueurs)   # la mémoire de JoueurCompteur
        self.solveur = self.classe_solveur(moi, self.budget) if nb_joueurs == 2 else None

    def choisir(self, etat: EtatPartie, moi: int, actions: list[Action]) -> Action:
        preferee = super().choisir(etat, moi, actions)
        if etat.pioche or self.solveur is None or len(actions) == 1:
            return preferee
        if sum(len(main) for main in etat.mains) > self.max_cartes:   # tailles publiques
            self.ignorees += 1
            return preferee
        try:
            complet = self.reconstituer(etat, moi)
            action = self.solveur.meilleure_action(complet, actions, preferee)
        except BudgetDepasse:
            self.abandons += 1
            return preferee
        self.resolus += 1
        return action

    def reconstituer(self, etat: EtatPartie, moi: int) -> EtatPartie:
        """L'état complet tel que le joueur le connaît : sa main, et la main adverse
        déduite de la mémoire (sans jamais lire etat.mains de l'adversaire)."""
        adversaire = next(j for j in range(len(etat.mains)) if j != moi)
        main_adverse = self.memoire.inconnues(etat) | self.memoire.connues[adversaire]
        mains = [[], []]
        mains[moi] = list(etat.mains[moi])
        mains[adversaire] = cartes_triees(main_adverse)
        # contrôle : seule la taille de la main adverse est lue, et elle est publique
        assert len(mains[adversaire]) == len(etat.mains[adversaire]), "mémoire incohérente"
        return EtatPartie(mains=mains, pioche=[], atout=etat.atout, table=list(etat.table),
                          defausse=[], attaquant=etat.attaquant,   # défausse inutile ici
                          defenseur_prend=etat.defenseur_prend, classement=list(etat.classement))


class JoueurPimc(JoueurFinal):
    """JoueurFinal qui raisonne aussi avant que la pioche soit vide, par PIMC
    (Perfect Information Monte Carlo).

    Quand la pioche a entre 1 et `pioche_max` cartes, à chaque décision :
    1. il tire `n_mondes` répartitions des cartes cachées compatibles avec sa mémoire ;
    2. dans chaque monde, il évalue chacun de ses coups : une simulation par l'heuristique
       (pour les deux camps) jusqu'à ce que la pioche soit vide, puis le minimax exact ;
    3. il joue le coup au meilleur total (à égalité, celui de l'heuristique).

    Il ne le fait que si les mains et la pioche réunies comptent au plus `max_cartes_pimc`
    cartes. Un monde dont une fin de partie dépasse `budget_monde` positions est ignoré.
    La pioche vide, il joue exactement comme JoueurFinal. Avant, comme JoueurCompteur.

    Compteurs : `pimc_decisions` (décisions prises par PIMC), `pimc_abandons` (aucun
    monde résolu : heuristique), `mondes_tentes` et `mondes_abandonnes`.
    """

    def __init__(self, n_mondes: int = 10, pioche_max: int = 4, max_cartes_pimc: int = 18,
                 budget_monde: int = 100_000, seed: int = 0, **reglages):
        super().__init__(**reglages)
        self.n_mondes = n_mondes
        self.pioche_max = pioche_max
        self.max_cartes_pimc = max_cartes_pimc
        self.budget_monde = budget_monde
        self.rng = random.Random(seed)
        # l'heuristique qui joue les simulations : JoueurPetit avec les mêmes réglages
        noms_petit = JoueurPetit().reglages().keys()
        self.politique = JoueurPetit(**{k: v for k, v in reglages.items() if k in noms_petit})
        self.pimc_decisions = 0
        self.pimc_abandons = 0
        self.mondes_tentes = 0
        self.mondes_abandonnes = 0

    def nom(self) -> str:
        return "JoueurPimc"

    def choisir(self, etat: EtatPartie, moi: int, actions: list[Action]) -> Action:
        # pioche vide : minimax exact de JoueurFinal ; sinon : l'heuristique du compteur
        preferee = super().choisir(etat, moi, actions)
        taille = sum(len(main) for main in etat.mains) + len(etat.pioche)   # tailles publiques
        if (not etat.pioche or len(etat.pioche) > self.pioche_max or self.solveur is None
                or len(actions) == 1 or taille > self.max_cartes_pimc):
            return preferee
        return self.choisir_pimc(etat, actions, preferee)

    def choisir_pimc(self, etat: EtatPartie, actions: list[Action], preferee: Action) -> Action:
        scores = [0] * len(actions)
        mondes_resolus = 0
        for _ in range(self.n_mondes):
            self.mondes_tentes += 1
            monde = self.memoire.tirer_monde(etat, self.rng)
            solveur = self.classe_solveur(self.memoire.moi, self.budget_monde)   # cache neuf par monde
            try:
                valeurs = solveur.valeurs_hybrides(monde, actions, self.politique)
            except BudgetDepasse:
                self.mondes_abandonnes += 1
                continue
            mondes_resolus += 1
            for i, v in enumerate(valeurs):
                scores[i] += v   # +1 par monde gagné, -1 par monde perdu

        if mondes_resolus == 0:
            self.pimc_abandons += 1
            return preferee
        self.pimc_decisions += 1
        meilleur_score = max(scores)
        if scores[actions.index(preferee)] == meilleur_score:
            return preferee   # à égalité, on garde le choix de l'heuristique
        return actions[scores.index(meilleur_score)]


REGLES_SAGE = ("ouverture_forte", "presque_vide", "prendre_avant_fin", "planification",
               "simples", "transfert")


class JoueurSage(JoueurPetit):
    """Une heuristique qui applique les leçons tirées de l'analyse des experts.

    Elle n'utilise ni comptage ni minimax : seulement sa main, la table, l'atout,
    la taille de la pioche et le nombre de cartes de l'adversaire. Tout ce qu'elle
    fait, un joueur humain peut donc le faire de tête.

    Les règles (chacune peut être désactivée avec `sans`, pour mesurer son apport) :
    - les atouts gardent toujours leur valeur, même en fin de partie (pas de bonus réduit) ;
    - "ouverture_forte" : quand la pioche est presque vide, ouvrir avec une carte ordinaire
      forte (au plus `carte_forte_max`), pour obliger l'adversaire à entamer ses atouts ;
    - "presque_vide" : pioche vide et adversaire à `presque_vide` cartes ou moins : ouvrir
      avec sa carte la plus forte, pour l'obliger à prendre ;
    - "prendre_avant_fin" : pioche presque vide, prendre plutôt que se défendre avec un atout ;
    - "planification" : en défense, prévoir une carte pour CHAQUE attaque avant de répondre,
      en réservant les atouts à celles que seul un atout peut battre ;
    - "simples" : à coût égal, ouvrir avec une seule carte plutôt qu'avec une paire ;
    - "transfert" : transférer dès que c'est possible sans atout.
    Les ajouts en attaque n'utilisent jamais d'atout, et s'arrêtent plus tôt près de la fin.
    """

    def __init__(self, bonus_atout: int = 20, pioche_proche: int = 4, seuil_ajout: int = 12,
                 seuil_ajout_fin: int = 10, seuil_defense: int = 30, presque_vide: int = 2,
                 carte_forte_max: int = 13, sans: tuple = ()):
        super().__init__(bonus_atout=bonus_atout, seuil_ajout=seuil_ajout,
                         seuil_defense=seuil_defense)
        inconnues = set(sans) - set(REGLES_SAGE)
        assert not inconnues, f"règles inconnues : {inconnues}"
        self.pioche_proche = pioche_proche
        self.seuil_ajout_fin = seuil_ajout_fin
        self.presque_vide = presque_vide
        self.carte_forte_max = carte_forte_max
        self.sans = frozenset(sans)

    def nom(self) -> str:
        return "JoueurSage" + "".join(f" -{r}" for r in sorted(self.sans))

    def avec(self, regle: str) -> bool:
        return regle not in self.sans

    # --- outils ---

    def cout_carte(self, carte: Carte, etat: EtatPartie) -> int:
        """Un atout garde toujours son prix, même en fin de partie."""
        return carte.valeur + (self.bonus_atout if carte.couleur == etat.atout else 0)

    def phase(self, etat: EtatPartie) -> str:
        if not etat.pioche:
            return "fin"
        if len(etat.pioche) <= self.pioche_proche:
            return "proche"
        return "milieu"

    # --- attaque ---

    def choisir_attaque(self, etat: EtatPartie, actions: list[Action]) -> Action | None:
        cout = lambda a: self.cout_moyen(a, etat)
        phase = self.phase(etat)
        attaques = de_type(actions, TypeAction.ATTAQUER)

        if not etat.table:
            simples = [a for a in attaques if len(a.cartes_jouees) == 1]
            n_adversaire = len(etat.mains[defenseur(etat)])   # taille publique
            if (self.avec("presque_vide") and phase == "fin" and simples
                    and n_adversaire <= self.presque_vide):
                return max(simples, key=cout)   # la plus forte : il devra sans doute prendre
            if self.avec("ouverture_forte") and phase == "proche":
                fortes = [a for a in simples if not contient_atout(a, etat.atout)
                          and next(iter(a.cartes_jouees)).valeur <= self.carte_forte_max]
                if fortes:
                    return max(fortes, key=cout)
            # sinon : la moins chère (les atouts, toujours chers, ne sortent qu'en dernier)
            nb = (lambda a: len(a.cartes_jouees)) if self.avec("simples") else (lambda a: -len(a.cartes_jouees))
            return min(attaques, key=lambda a: (cout(a), nb(a)), default=None)

        # ajout en cours d'attaque : jamais d'atout, et moins généreux près de la fin
        seuil = self.seuil_ajout if phase == "milieu" else self.seuil_ajout_fin
        ajouts = [a for a in attaques if not contient_atout(a, etat.atout) and cout(a) <= seuil]
        if ajouts:
            return min(ajouts, key=cout)
        passer = de_type(actions, TypeAction.PASSER)
        return passer[0] if passer else None

    # --- défense ---

    def choisir_defense(self, etat: EtatPartie, actions: list[Action]) -> Action | None:
        cout = lambda a: self.cout_moyen(a, etat)
        prendre = Action(TypeAction.PRENDRE)
        phase = self.phase(etat)

        transferts = de_type(actions, TypeAction.TRANSFERER)
        if self.avec("transfert"):
            transferts = [a for a in transferts if not contient_atout(a, etat.atout)]
        else:
            transferts = [a for a in transferts if cout(a) <= 10]   # comme JoueurPetit réglé
        if transferts:
            return min(transferts, key=cout)

        main = etat.mains[defenseur(etat)]
        cibles = non_battues(etat)
        plan = (self.plan_defense(etat, main, cibles) if self.avec("planification")
                else self.plan_glouton(etat, main, cibles))
        if plan is None:
            return prendre   # impossible de tout battre : inutile de dépenser des cartes

        cartes = [carte for _, carte in plan]
        if phase != "fin":
            if (self.avec("prendre_avant_fin") and phase == "proche"
                    and any(c.couleur == etat.atout for c in cartes)):
                return prendre   # garder ses atouts pour la fin de partie
            if max(self.cout_carte(c, etat) for c in cartes) > self.seuil_defense:
                return prendre
        cible, carte = plan[0]
        return Action(TypeAction.DEFENDRE, frozenset({carte}), cible)

    def plan_defense(self, etat: EtatPartie, main: list[Carte],
                     cibles: list[Carte]) -> list[tuple[Carte, Carte]] | None:
        """La façon la moins coûteuse de battre TOUTES les attaques, une carte par attaque,
        ou None si c'est impossible. Recherche exhaustive avec élagage (séparation et
        évaluation) : les attaques les plus difficiles à battre sont traitées en premier."""
        candidats = {c: sorted((d for d in main if bat(c, d, etat.atout)),
                               key=lambda d: self.cout_carte(d, etat)) for c in cibles}
        ordre = sorted(cibles, key=lambda c: len(candidats[c]))
        meilleur = [None, float("inf")]   # [plan, coût]

        def chercher(i: int, utilisees: set, plan: list, total: int) -> None:
            if total >= meilleur[1]:
                return   # élagage : on ne fera pas mieux que le meilleur plan connu
            if i == len(ordre):
                meilleur[0], meilleur[1] = list(plan), total
                return
            cible = ordre[i]
            for carte in candidats[cible]:
                if carte not in utilisees:
                    utilisees.add(carte)
                    plan.append((cible, carte))
                    chercher(i + 1, utilisees, plan, total + self.cout_carte(carte, etat))
                    plan.pop()
                    utilisees.remove(carte)

        chercher(0, set(), [], 0)
        return meilleur[0]

    def plan_glouton(self, etat: EtatPartie, main: list[Carte],
                     cibles: list[Carte]) -> list[tuple[Carte, Carte]] | None:
        """Sans planification : chaque attaque prend la carte la moins chère qui reste."""
        plan, utilisees = [], set()
        for cible in cibles:
            possibles = [d for d in main if d not in utilisees and bat(cible, d, etat.atout)]
            if not possibles:
                return None
            carte = min(possibles, key=lambda d: self.cout_carte(d, etat))
            utilisees.add(carte)
            plan.append((cible, carte))
        return plan


REGLES_AMELIORATION = ("planification", "transfert_libre", "pas_atout_ouverture_fin",
                       "presque_vide", "pas_atout_ajout_fin", "ouverture_forte", "simples")


class JoueurAmeliore(JoueurPetit):
    """JoueurPetit avec les réglages de la recherche, auquel on AJOUTE certaines leçons
    de l'analyse, choisies avec `avec`. Sans aucune règle, il joue exactement comme
    JoueurPetit(**REGLAGES_RECHERCHE) : chaque règle ne modifie que sa propre situation.

    Les règles :
    - "planification" : en défense, prévoir une carte pour chaque attaque avant de répondre ;
    - "transfert_libre" : transférer avec n'importe quelles cartes qui ne sont pas des atouts ;
    - "pas_atout_ouverture_fin" : pioche vide, ne pas ouvrir avec un atout si on peut l'éviter ;
    - "presque_vide" : pioche vide et adversaire à `presque_vide` cartes ou moins,
      ouvrir avec sa carte la plus forte ;
    - "pas_atout_ajout_fin" : près de la fin (pioche à `pioche_proche` cartes ou moins),
      ne jamais ajouter d'atout en attaque ;
    - "ouverture_forte" : près de la fin (pioche non vide), ouvrir avec la carte ordinaire
      la plus forte jusqu'à `carte_forte_max` ;
    - "simples" : à coût égal, ouvrir avec une seule carte plutôt qu'avec plusieurs.
    """

    plan_defense = JoueurSage.plan_defense   # même recherche du meilleur plan de défense

    def __init__(self, avec: tuple = (), pioche_proche: int = 4, presque_vide: int = 2,
                 carte_forte_max: int = 13, **reglages):
        super().__init__(**(reglages or REGLAGES_RECHERCHE))
        inconnues = set(avec) - set(REGLES_AMELIORATION)
        assert not inconnues, f"règles inconnues : {inconnues}"
        self.avec = frozenset(avec)
        self.pioche_proche = pioche_proche
        self.presque_vide = presque_vide
        self.carte_forte_max = carte_forte_max

    def nom(self) -> str:
        return "Ameliore[" + ", ".join(r for r in REGLES_AMELIORATION if r in self.avec) + "]"

    def phase(self, etat: EtatPartie) -> str:
        if not etat.pioche:
            return "fin"
        return "proche" if len(etat.pioche) <= self.pioche_proche else "milieu"

    def choisir_attaque(self, etat: EtatPartie, actions: list[Action]) -> Action | None:
        cout = lambda a: self.cout_attaque(a, etat)
        phase = self.phase(etat)
        attaques = de_type(actions, TypeAction.ATTAQUER)

        if not etat.table:
            simples = [a for a in attaques if len(a.cartes_jouees) == 1]
            n_adversaire = len(etat.mains[defenseur(etat)])   # taille publique
            if ("presque_vide" in self.avec and phase == "fin" and simples
                    and n_adversaire <= self.presque_vide):
                return max(simples, key=cout)
            if "ouverture_forte" in self.avec and phase == "proche":
                fortes = [a for a in simples if not contient_atout(a, etat.atout)
                          and next(iter(a.cartes_jouees)).valeur <= self.carte_forte_max]
                if fortes:
                    return max(fortes, key=cout)
            candidates = attaques
            if "pas_atout_ouverture_fin" in self.avec and phase == "fin":
                sans_atout = [a for a in attaques if not contient_atout(a, etat.atout)]
                candidates = sans_atout or attaques
            if "simples" in self.avec:
                cle = lambda a: (cout(a), len(a.cartes_jouees))
            else:
                cle = lambda a: (cout(a), -len(a.cartes_jouees))   # comme JoueurPetit
            return min(candidates, key=cle, default=None)

        ajouts = [a for a in attaques if cout(a) <= self.seuil_ajout]
        if "pas_atout_ajout_fin" in self.avec and phase != "milieu":
            ajouts = [a for a in ajouts if not contient_atout(a, etat.atout)]
        if ajouts:
            return min(ajouts, key=cout)
        passer = de_type(actions, TypeAction.PASSER)
        return passer[0] if passer else None

    def choisir_defense(self, etat: EtatPartie, actions: list[Action]) -> Action | None:
        if not ({"planification", "transfert_libre"} & self.avec):
            return super().choisir_defense(etat, actions)   # rien ne change en défense
        cout = lambda a: self.cout_moyen(a, etat)
        prendre = Action(TypeAction.PRENDRE)

        transferts = de_type(actions, TypeAction.TRANSFERER)
        if "transfert_libre" in self.avec:
            transferts = [a for a in transferts if not contient_atout(a, etat.atout)]
        else:
            transferts = [a for a in transferts if cout(a) <= self.seuil_transfert]
        if transferts:
            return min(transferts, key=cout)

        defenses = de_type(actions, TypeAction.DEFENDRE)
        cibles_couvertes = {a.cible for a in defenses}
        if any(att not in cibles_couvertes for att in non_battues(etat)):
            return prendre

        if "planification" in self.avec:
            plan = self.plan_defense(etat, etat.mains[defenseur(etat)], non_battues(etat))
            if plan is None:
                return prendre   # chaque attaque est battable seule, mais pas toutes ensemble
            cible, carte = plan[0]
            meilleure = Action(TypeAction.DEFENDRE, frozenset({carte}), cible)
        else:
            meilleure = min(defenses, key=cout, default=None)

        # même règle que JoueurPetit : hors fin de partie, une défense trop chère, on prend
        if (meilleure is not None and not self.en_fin_de_partie(etat)
                and cout(meilleure) > self.seuil_defense):
            return prendre
        return meilleure
