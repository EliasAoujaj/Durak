"""Un moteur compact et rapide pour la recherche (minimax), à 2 joueurs.

Chaque carte est un bit d'un entier de 36 bits : bit (couleur - 1) * 9 + (valeur - 6).
Une main, l'ensemble des attaques ou des défenses est donc un simple entier :
- ajouter une carte : m | bit        - retirer : m & ~bit
- tester : m & bit                   - compter : m.bit_count()
Copier un état revient à copier quelques entiers, et un état est directement
une clé de dictionnaire. C'est bien plus rapide que des listes d'objets Carte.

Un état rapide est un tuple :
    (main0, main1, attaques, non_battues, defenses, pioche, attaquant, prend)
- attaques : toutes les cartes d'attaque sur la table ;
- non_battues : celles qui ne sont pas encore battues ;
- defenses : les cartes de défense sur la table ;
- pioche : tuple d'indices de cartes, la prochaine piochée en dernier (comme pop()).
Qui a battu quoi n'a plus d'importance pour la suite : seuls ces trois ensembles comptent.

Les règles sont EXACTEMENT celles de moteur.py ; test_rapide.py le vérifie en comparant
les deux moteurs coup par coup sur des centaines de parties.
"""

from cartes import Carte
from moteur import MAX_ATTAQUES, TAILLE_MAIN, EtatPartie, fin_de_partie
from solveur import GAGNE, NUL, PERDU, PROFONDEUR_MAX, BudgetDepasse, Solveur

# --- les cartes en bits ---

def indice(carte: Carte) -> int:
    return (carte.couleur.value - 1) * 9 + (carte.valeur - 6)


def masque(cartes) -> int:
    m = 0
    for c in cartes:
        m |= 1 << indice(c)
    return m


def bits(m: int):
    """Les bits à 1 de m, un par un (chacun sous forme d'entier à un seul bit)."""
    while m:
        bas = m & -m   # le bit à 1 le plus bas (astuce du complément à deux)
        yield bas
        m ^= bas


def sous_masques(m: int):
    """Tous les sous-ensembles non vides de m (même astuce que sous_groupes, en plus rapide)."""
    s = m
    while s:
        yield s
        s = (s - 1) & m


# VALEUR[k] : les 4 cartes de valeur k + 6 ; REPETE sert à étaler un ensemble de valeurs
REPETE = 1 | (1 << 9) | (1 << 18) | (1 << 27)
VALEUR = [REPETE << k for k in range(9)]
COULEUR = [0x1FF << (9 * c) for c in range(4)]

# BAT[a][i] : les cartes qui battent la carte i quand l'atout a l'indice a (couleur - 1)
BAT = []
for a in range(4):
    table = []
    for i in range(36):
        c, k = divmod(i, 9)
        plus_fortes = COULEUR[c] & ~((1 << (i + 1)) - 1)   # même couleur, valeur supérieure
        table.append(plus_fortes | (COULEUR[a] if c != a else 0))
    BAT.append(table)

# COUT[a][i] : pour ordonner les coups, comme solveur.ordonner (valeur, + 20 si atout)
COUT = [[i % 9 + 6 + (20 if i // 9 == a else 0) for i in range(36)] for a in range(4)]

# --- les coups ---

ATTAQUER, DEFENDRE, TRANSFERER, PRENDRE, PASSER = range(5)
PRIORITE = {TRANSFERER: 0, DEFENDRE: 1, ATTAQUER: 1, PASSER: 2, PRENDRE: 3}


def convertir(etat: EtatPartie) -> tuple:
    """L'état du moteur classique, traduit en état rapide."""
    return (masque(etat.mains[0]), masque(etat.mains[1]),
            masque(a for a, _ in etat.table),
            masque(a for a, d in etat.table if d is None),
            masque(d for _, d in etat.table if d is not None),
            tuple(indice(c) for c in etat.pioche),
            etat.attaquant, etat.defenseur_prend)


def coups(etat: tuple, a: int) -> tuple[int, list[tuple[int, int, int]]]:
    """Le joueur actif, et ses coups légaux : des triplets (type, cartes, cible).
    Mêmes règles que joueur_actif et actions_legales de moteur.py."""
    main0, main1, att, nb, dfs, pioche, attaquant, prend = etat
    mains = (main0, main1)
    defenseur = 1 - attaquant
    liste = []

    if nb and not prend:
        # --- le défenseur joue ---
        main = mains[defenseur]
        liste.append((PRENDRE, 0, 0))
        if nb == att:
            # aucune attaque battue : transferts avec les cartes de la valeur des attaques
            k = ((att & -att).bit_length() - 1) % 9
            n_att = att.bit_count()
            n_main_attaquant = mains[attaquant].bit_count()
            for s in sous_masques(main & VALEUR[k]):
                total = n_att + s.bit_count()
                if total <= n_main_attaquant and total <= MAX_ATTAQUES:
                    liste.append((TRANSFERER, s, 0))
        for cible in bits(nb):
            for carte in bits(main & BAT[a][cible.bit_length() - 1]):
                liste.append((DEFENDRE, carte, cible))
        return defenseur, liste

    # --- l'attaquant joue ---
    main = mains[attaquant]
    n_def = mains[defenseur].bit_count()
    if not att:
        for k in range(9):
            for s in sous_masques(main & VALEUR[k]):
                if s.bit_count() <= n_def:
                    liste.append((ATTAQUER, s, 0))
    else:
        liste.append((PASSER, 0, 0))
        if att.bit_count() < MAX_ATTAQUES and nb.bit_count() < n_def:
            m = att | dfs
            valeurs = (m | (m >> 9) | (m >> 18) | (m >> 27)) & 0x1FF   # valeurs présentes
            for carte in bits(main & (valeurs * REPETE)):
                liste.append((ATTAQUER, carte, 0))
    return attaquant, liste


def jouer(etat: tuple, coup: tuple[int, int, int]) -> tuple[tuple, int]:
    """Le nouvel état après le coup, et le gagnant (-1 si la partie continue).
    Mêmes règles que appliquer, fin_attaque et fin_de_partie de moteur.py."""
    main0, main1, att, nb, dfs, pioche, attaquant, prend = etat
    mains = [main0, main1]
    defenseur = 1 - attaquant
    type_coup, m, cible = coup

    if type_coup == ATTAQUER:
        mains[attaquant] &= ~m
        att |= m
        nb |= m
    elif type_coup == DEFENDRE:
        mains[defenseur] &= ~m
        nb &= ~cible
        dfs |= m
    elif type_coup == TRANSFERER:
        mains[defenseur] &= ~m
        att |= m
        nb |= m
        attaquant = defenseur
    elif type_coup == PRENDRE:
        prend = True
    else:  # PASSER : fin de l'attaque
        if prend:
            mains[defenseur] |= att | dfs   # le défenseur ramasse ; sinon tout part à la défausse
        for j in (attaquant, defenseur):   # on recomplète : l'attaquant d'abord
            while mains[j].bit_count() < TAILLE_MAIN and pioche:
                mains[j] |= 1 << pioche[-1]
                pioche = pioche[:-1]
        if not pioche:   # le premier à n'avoir plus de cartes gagne, l'attaquant d'abord
            for j in (attaquant, defenseur):
                if not mains[j]:
                    return etat, j
        if not prend:
            attaquant = defenseur
        att = nb = dfs = 0
        prend = False

    return (mains[0], mains[1], att, nb, dfs, pioche, attaquant, prend), -1


def cout_coup(coup: tuple[int, int, int], a: int) -> int:
    total = 0
    for carte in bits(coup[1]):
        total += COUT[a][carte.bit_length() - 1]
    return total


# --- le solveur ---

class SolveurRapide(Solveur):
    """Même minimax que Solveur (mêmes méthodes publiques, mêmes résultats), mais la
    recherche se fait sur les états rapides. Seul le point d'entrée _valeur change :
    il reçoit un état classique, le traduit, puis tout se passe en entiers."""

    def _valeur(self, etat: EtatPartie) -> int:
        terminee, classement = fin_de_partie(etat)
        if terminee:
            return GAGNE if classement[0] == self.moi else PERDU
        return self._valeur_rapide(convertir(etat), etat.atout.value - 1)

    def _valeur_rapide(self, etat: tuple, a: int) -> int:
        if etat in self.cache:
            return self.cache[etat]
        if etat in self.chemin:
            return NUL   # boucle

        self.noeuds += 1
        if self.noeuds > self.budget or len(self.chemin) > PROFONDEUR_MAX:
            raise BudgetDepasse

        self.chemin.add(etat)
        actif, liste = coups(etat, a)
        liste.sort(key=lambda coup: (PRIORITE[coup[0]], cout_coup(coup, a)))
        je_joue = actif == self.moi
        meilleure = PERDU - 1 if je_joue else GAGNE + 1
        for coup in liste:
            suivant, gagnant = jouer(etat, coup)
            if gagnant >= 0:
                v = GAGNE if gagnant == self.moi else PERDU
            else:
                v = self._valeur_rapide(suivant, a)
            if je_joue:
                meilleure = max(meilleure, v)
                if meilleure == GAGNE:
                    break
            else:
                meilleure = min(meilleure, v)
                if meilleure == PERDU:
                    break
        self.chemin.remove(etat)

        self.cache[etat] = meilleure
        return meilleure
