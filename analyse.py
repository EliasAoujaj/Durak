"""Tire des leçons des joueurs experts : où l'heuristique se trompe-t-elle, et comment ?

Deux analyses :
1. Fin de partie (pioche vide) : le minimax donne la valeur EXACTE de chaque coup.
   On repère les décisions où le coup de l'heuristique (JoueurCompteur) perd une partie
   qui était gagnable : ce sont de vraies erreurs, prouvées.
2. Pioche presque vide (1 ou 2 cartes) : on repère les décisions où le PIMC choisit
   autrement que l'heuristique. Ce n'est plus une preuve, mais une tendance de l'expert.

Les erreurs sont regroupées par catégorie (« en défense, l'heuristique bat alors qu'il
fallait prendre »...), avec des statistiques et des exemples concrets. Le rapport
s'affiche et est enregistré dans rapport_analyse.txt.
"""

import time
from collections import Counter, defaultdict

from affichage import texte_action, texte_cartes
from arene import jouer_partie, nouvel_executeur
from joueurs import JoueurPetit, JoueurPimc, REGLAGES_RECHERCHE, contient_atout
from moteur import Action, EtatPartie, TypeAction, defenseur
from solveur import BudgetDepasse, ordonner

N_FIN = 2000        # donnes pour l'analyse de fin de partie (rapide : environ 1 à 2 minutes)
N_PIMC = 150        # donnes pour l'analyse du PIMC (lente : environ 10 minutes)
EXEMPLES = 3        # exemples affichés par catégorie
CATEGORIES = 12     # nombre de catégories affichées

NOMS = {TypeAction.ATTAQUER: "attaquer", TypeAction.DEFENDRE: "battre",
        TypeAction.TRANSFERER: "transférer", TypeAction.PRENDRE: "prendre",
        TypeAction.PASSER: "passer"}


class Analyste(JoueurPimc):
    """Joue comme JoueurPimc (ou JoueurFinal si avec_pimc est faux), et note chaque décision
    où il compare l'heuristique à l'expert."""

    def __init__(self, avec_pimc: bool, **reglages):
        super().__init__(**reglages)
        self.avec_pimc = avec_pimc
        self.journal: list[dict] = []

    def choisir(self, etat: EtatPartie, moi: int, actions: list[Action]) -> Action:
        # le choix de l'heuristique : JoueurPetit.choisir, avec le coût d'attaque du compteur
        preferee = JoueurPetit.choisir(self, etat, moi, actions)
        if self.solveur is None or len(actions) == 1:
            return preferee
        if not etat.pioche:
            return self.analyser_fin(etat, moi, actions, preferee)
        taille = sum(len(m) for m in etat.mains) + len(etat.pioche)
        if self.avec_pimc and len(etat.pioche) <= self.pioche_max and taille <= self.max_cartes_pimc:
            choix = self.choisir_pimc(etat, actions, preferee)
            self.noter("pimc", etat, moi, preferee, choix, perte=None)
            return choix
        return preferee

    def analyser_fin(self, etat, moi, actions, preferee) -> Action:
        if sum(len(m) for m in etat.mains) > self.max_cartes:
            return preferee
        complet = self.reconstituer(etat, moi)
        try:
            valeurs = self.solveur.valeurs(complet, actions)
        except BudgetDepasse:
            return preferee
        meilleure_valeur = max(valeurs)
        valeur_heuristique = valeurs[actions.index(preferee)]
        if valeur_heuristique == meilleure_valeur:
            choix = preferee
        else:
            # parmi les coups optimaux, le plus « naturel » (même ordre que le solveur)
            optimaux = [a for a, v in zip(actions, valeurs) if v == meilleure_valeur]
            choix = ordonner(optimaux, etat.atout)[0]
        self.noter("fin", etat, moi, preferee, choix, perte=meilleure_valeur - valeur_heuristique)
        return choix

    def noter(self, phase, etat, moi, heuristique, expert, perte) -> None:
        adversaire = 1 - moi
        if moi == defenseur(etat):
            role = "défense"
        elif not etat.table:
            role = "attaque initiale"
        else:
            role = "ajout ou passer"
        # en fin de partie, la main adverse est connue ; avant, seulement ses cartes connues
        main_adverse = (self.memoire.inconnues(etat) | self.memoire.connues[adversaire]
                        if not etat.pioche else self.memoire.connues[adversaire])
        differe = heuristique != expert
        entree = {
            "phase": phase, "role": role, "differe": differe, "perte": perte,
            "heuristique": NOMS[heuristique.type_action], "expert": NOMS[expert.type_action],
            "nuance": nuance(self, heuristique, expert, etat),
            "n_moi": len(etat.mains[moi]), "n_adv": len(etat.mains[adversaire]),
            "pioche": len(etat.pioche),
            "atouts_moi": sum(c.couleur == etat.atout for c in etat.mains[moi]),
            "heur_atout": contient_atout(heuristique, etat.atout),
            "expert_atout": contient_atout(expert, etat.atout),
        }
        if differe:
            table = "  ".join(f"{a}/{d if d else '—'}" for a, d in etat.table) or "(vide)"
            entree["exemple"] = (
                f"atout {etat.atout.name.lower()}, pioche {len(etat.pioche)} | "
                f"moi : {texte_cartes(etat.mains[moi])} | "
                f"adversaire ({len(etat.mains[adversaire])} cartes, connues : "
                f"{texte_cartes(main_adverse) or 'aucune'}) | table : {table}\n"
                f"        heuristique : {texte_action(heuristique)}   →   expert : {texte_action(expert)}")
        self.journal.append(entree)


def nuance(joueur, heuristique: Action, expert: Action, etat: EtatPartie) -> str:
    """Pour deux coups du même type : l'expert joue-t-il plus fort, plus faible, ou plus de cartes ?"""
    if heuristique == expert or heuristique.type_action != expert.type_action:
        return ""
    if not heuristique.cartes_jouees or not expert.cartes_jouees:
        return ""
    if len(expert.cartes_jouees) != len(heuristique.cartes_jouees):
        return "plus de cartes" if len(expert.cartes_jouees) > len(heuristique.cartes_jouees) else "moins de cartes"
    c_h = joueur.cout_moyen(heuristique, etat)
    c_e = joueur.cout_moyen(expert, etat)
    if c_e > c_h:
        return "carte plus forte"
    if c_e < c_h:
        return "carte plus faible"
    return "autre carte de même valeur"


def analyser_bloc(avec_pimc: bool, seed_depart: int, n_donnes: int) -> list[dict]:
    """Joue n_donnes parties entre deux analystes et renvoie leurs journaux."""
    journal = []
    for seed in range(seed_depart, seed_depart + n_donnes):
        joueurs = [Analyste(avec_pimc, **REGLAGES_RECHERCHE), Analyste(avec_pimc, **REGLAGES_RECHERCHE)]
        jouer_partie(seed, joueurs)
        for j in joueurs:
            journal.extend(j.journal)
    return journal


def lancer(executeur, avec_pimc: bool, n_donnes: int, seed_depart: int) -> list[dict]:
    taille = max(1, n_donnes // 64)
    taches = [executeur.submit(analyser_bloc, avec_pimc, s, min(taille, seed_depart + n_donnes - s))
              for s in range(seed_depart, seed_depart + n_donnes, taille)]
    journal = []
    for tache in taches:
        journal.extend(tache.result())
    return journal


# --- le rapport ---

def pourcent(a, b) -> str:
    return f"{a / b:6.1%}" if b else "   —  "


def rapport(journal: list[dict], titre: str, mot: str, ecrire) -> None:
    ecrire(f"\n{'=' * 78}\n{titre}\n{'=' * 78}")
    if not journal:
        ecrire("Aucune décision analysée.")
        return
    differences = [e for e in journal if e["differe"]]
    ecrire(f"Décisions analysées : {len(journal)}   dont {mot} : {len(differences)} "
           f"({pourcent(len(differences), len(journal)).strip()})")

    # par rôle
    ecrire(f"\nPar situation :")
    par_role = Counter(e["role"] for e in journal)
    for role, total in par_role.most_common():
        n = sum(1 for e in differences if e["role"] == role)
        ecrire(f"  {role:<18} {total:6} décisions   {mot} : {n:5} ({pourcent(n, total).strip()})")

    # par catégorie
    groupes = defaultdict(list)
    for e in differences:
        cle = (e["role"], e["heuristique"], e["expert"], e["nuance"])
        groupes[cle].append(e)
    ecrire(f"\nLes {CATEGORIES} cas les plus fréquents (heuristique → expert) :")
    for (role, h, x, nu), cas in sorted(groupes.items(), key=lambda g: -len(g[1]))[:CATEGORIES]:
        n = len(cas)
        moyenne = lambda cle: sum(e[cle] for e in cas) / n
        part = lambda cle: sum(e[cle] for e in cas) / n
        libelle = f"{h} → {x}" + (f" ({nu})" if nu else "")
        ecrire(f"\n• {role} : {libelle}   —   {n} cas, {pourcent(n, len(differences)).strip()} des {mot}")
        ecrire(f"    en moyenne : {moyenne('n_moi'):.1f} cartes en main contre {moyenne('n_adv'):.1f} "
               f"chez l'adversaire, {moyenne('atouts_moi'):.1f} atout(s) en main"
               + (f", pioche {moyenne('pioche'):.1f}" if cas[0]["phase"] == "pimc" else ""))
        ecrire(f"    l'heuristique joue un atout dans {part('heur_atout'):.0%} des cas, "
               f"l'expert dans {part('expert_atout'):.0%}")
        for e in cas[:EXEMPLES]:
            ecrire(f"    ex. {e['exemple']}")


if __name__ == "__main__":
    lignes = []

    def ecrire(texte: str) -> None:
        print(texte)
        lignes.append(texte)

    with nouvel_executeur() as executeur:
        debut = time.perf_counter()
        journal_fin = lancer(executeur, avec_pimc=False, n_donnes=N_FIN, seed_depart=0)
        ecrire(f"(analyse de fin de partie : {time.perf_counter() - debut:.0f} s)")
        rapport(journal_fin, "1. FIN DE PARTIE (pioche vide) : les erreurs prouvées de l'heuristique",
                "erreurs", ecrire)

        debut = time.perf_counter()
        journal_pimc = lancer(executeur, avec_pimc=True, n_donnes=N_PIMC, seed_depart=100_000)
        ecrire(f"\n(analyse du PIMC : {time.perf_counter() - debut:.0f} s)")
        rapport([e for e in journal_pimc if e["phase"] == "pimc"],
                "2. PIOCHE PRESQUE VIDE (1 ou 2 cartes) : là où le PIMC choisit autrement",
                "divergences", ecrire)

    with open("rapport_analyse.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")
    print("\nRapport enregistré dans rapport_analyse.txt")
