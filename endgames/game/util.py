"""Methods for fetching initial positions and other utility."""

import itertools
import random
from endgames.game.variants import Variant, VARIANT_NAMES_DICT
from endgames.game.io import read_printout

def lookup_variant(variant_name):
    """Gives Variant object that has name variant_name.

    Args:
        variant_name (str): name of variant

    Returns:
        Variant: the variant
    """
    return VARIANT_NAMES_DICT[variant_name]

def lookup_hand_size(num_players):
    """Return the Hanab Live hand size given num_players.

    Args:
        num_players (int): the number of players in a hanabi game

    Returns:
        int: the number of cards in each player's hand
    """
    if num_players in (2, 3):
        return 5
    elif num_players == 6:
        return 3
    return 4

class Deck:
    """An ordered list of cards"""
    def __init__(self, variant=None):
        if variant is None:
            variant = lookup_variant("No Variant")
        elif isinstance(variant, str):
            variant = lookup_variant(variant)

        self.seed = None
        self.variant = variant
        self.deck = None  # to be overwritten
        self._init_deck(variant)

    def _init_deck(self, variant: Variant):
        """Initializes self.deck. Requires hanabi game logic.

        Args:
            variant (Variant): a Hanab Live game variant
        """
        deck = []
        for suit_index, suit in enumerate(variant.suits):
            for rank in variant.clue_ranks:
                card = Card(suit_index, rank)

                if variant.stack_size == 4 and rank == 5:
                    continue
                deck.append(card)
                if suit.one_of_each:
                    continue
                if variant.sudoku:
                    deck.append(card)
                elif rank == 1:
                    if variant.up_or_down or suit.reversed:
                        continue
                    deck.append(card)
                    deck.append(card)
                elif rank == variant.critical_rank:
                    continue
                elif rank == 5:
                    if suit.reversed:
                        deck.append(card)
                        deck.append(card)
                else:
                    deck.append(card)

        self.deck = deck

    def set_deck(self, deck):
        """Setter method for self.deck in case of unseeded deck.

        Args:
            deck (list): a list of strings representing cards
        """
        self.deck = []
        for word in deck:
            rank = 0
            for index, char in enumerate(word):
                if char in "12345":
                    rank = int(char)
                    word = word[:index] + word[index + 1:]
                    word.strip()
                    break
            suit = "Chromatic"
            for attempt in self.variant.suits:
                if attempt.abbreviation is not None and word.lower() == attempt.abbreviation.lower():
                    suit = attempt.name
                    break
                if attempt.id is not None and word.lower() == attempt.id.lower():
                    suit = attempt.name
                    break
                if word.lower() == attempt.name.lower():
                    suit = attempt.name
                    break
            suit_index = self.variant.suit_names.index(suit) + 1  # 1-indexed
            self.deck.append(Card(suit_index, rank))

    # TODO: use __repr__ instead? decide
    def print(self, cutoff=None):
        """Prints the deck.

        Renders cards as ordered pairs of numbers (a, b). So this is a
        suit-agnostic way of printing.

        Args:
            cutoff (int, optional): # cards to print. Defaults to None.
        """
        if cutoff is None:
            cutoff = len(self.deck)
        print(" ".join([str(card.interpret()) for card in self.deck[:cutoff]]))

    # TODO: implement Hanab Live shuffling method
    def shuffle(self, seed):
        """Shuffles deck according to a seed.

        Args:
            seed (str): a seed string as used on Hanab Live
            deck (list): a list of cards

        Returns:
            list: a copy of deck sorted by seed
        """
        self.seed = seed
        random.seed(seed)
        random.shuffle(self.deck)

    def check_for_infeasibility(self, num_players=2, hand_cap=None):
        """Checks if the deck is impossible to win.

        Returning True indicates that the deck is provably infeasible,
        i.e. impossible to win. Returning False indicates that the deck
        may or may not be possible to win. Currently, the checks cover
        all hand capacity losses and pace losses but not losses due to
        clue count or losses due to hand distribution (which may other-
        wise be viewed as a type of pace loss).

        In other words, the current checks solve a hanabi-like game in
        which there is 1 hand of sum(len(hand) for hand in hands) cards,
        the last card in the deck must be played last, and no more than
        len(hands) cards may be played after the final card is drawn.
        Additionally, the player has perfect information of the deck.

        Currently in the process of trying to make this slightly more
        capable of tackling different hanabi variants or game sizes.
        It still only works for 5 Suit (see _check_for_pace_loss()).

        Args:
            num_players (int): Number of players. Defaults to 2.
            hand_cap (int): Cumulative hand size of ALL players.

        Returns:
            bool: able to prove the deck is infeasible?
        """
        if hand_cap is None:
            hand_cap = num_players * lookup_hand_size(num_players)
        paths_through_deck = self._suitify()
        proved_infeasible = True
        for path in paths_through_deck:
            path = self._pathify(path)
            if self._check_for_capacity_loss(path, hand_cap):
                continue
            if self._check_for_pace_loss(path, num_players):
                continue
            proved_infeasible = False
            break
        return proved_infeasible

    def _suitify(self):
        locations = {}
        for loc, card in enumerate(self.deck):
            suit, rank = card.interpret()
            if suit not in locations:
                locations[suit] = {}
            if rank not in locations[suit]:
                locations[suit][rank] = []
            locations[suit][rank].append(loc)

        # pylint made this look gross
        for suit, ranks_to_locs in locations.items():
            for rank, locs in ranks_to_locs.items():
                if rank in (1, 5):
                    ranks_to_locs[rank] = [min(locs)]

        paths = []
        for ranks_to_locs in locations.values():
            paths += ranks_to_locs.values()
        return itertools.product(*paths)

    def _pathify(self, locs):
        path = [False] * 50
        for loc in locs:
            path[loc] = True
        return path

    def _check_for_pace_loss(self, path, num_final_plays):
        index = len(self.deck) - 1
        curr = path[index]
        # checks for BDR loss
        if curr and self.deck[index].interpret()[1] != 5:
            return True
        pace = num_final_plays
        stacks = [0, 0, 0, 0, 0]
        while pace < 25:  # 25 is max score
            pace += 1
            index -= 1
            curr = path[index]
            if curr:
                card = self.deck[index]
                suit, rank = card.interpret()
                suit -= 1  # 0-indexing
                stacks[suit] = max(stacks[suit], 6 - rank)
            if sum(stacks) > pace:
                return True
        return False

    def _check_for_capacity_loss(self, path, capacity):
        hand = set()
        stacks = [0, 0, 0, 0, 0]
        for index, curr in enumerate(path):
            if not curr:
                continue
            card = self.deck[index]
            suit, rank = card.interpret()
            suit -= 1  # 0-indexing
            if stacks[suit] == rank - 1:  # i.e., playable
                newly_playable = card.value + 1
                stacks[suit] += 1
                while newly_playable in hand:
                    hand.remove(newly_playable)
                    newly_playable += 1
                    stacks[suit] += 1
            else:
                hand.add(card.value)
                if len(hand) == capacity:
                    return True
        return False

# TODO: fix
class Card:
    """A card with suit and rank"""
    def __init__(self, suit_index, rank):
        self.value = (suit_index << 31) | rank
    def interpret(self):
        """Returns (suit index, rank)."""
        x = self.value >> 31
        y = self.value & 0x7FFFFFFF
        return x, y

def create_bespoke_deck(deck, variant=None):
    """Create deck from input. Assumes No Variant."""
    if variant is None:
        variant = "No Variant"
    result = Deck(variant)
    result.set_deck(deck)
    return result

if __name__ == "__main__":
    # VAR = "No Variant"
    # SEED = "p2v0scommendation-splintering-gondolas"
    # DECK = Deck(VAR)
    # DECK.shuffle(SEED)
    # DECK.print()
    # print(DECK.check_for_infeasibility())
    FILE = "assets/rama_hard_decks.txt"
    D_NO = 8
    for i, d in enumerate(read_printout(FILE)):
        DECK = create_bespoke_deck(d)
        print(DECK.check_for_infeasibility())
