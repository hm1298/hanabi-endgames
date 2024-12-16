"""Methods for fetching initial positions and other utility."""

from collections import Counter
import itertools
import random
from endgames.game.suits import update_suits
from endgames.game.variants import *

def lookup_variant(variant_name):
    """Gives Variant object that has name variant_name.

    Args:
        variant_name (str): name of variant

    Returns:
        Variant: the variant
    """
    return VARIANT_NAMES_DICT[variant_name]

class Deck:
    """An ordered list of cards"""
    def __init__(self, variant=None):
        if variant is None:
            variant = lookup_variant("No Variant")
        elif isinstance(variant, str):
            variant = lookup_variant(variant)

        self.seed = None
        self.variant = variant
        self._init_deck(variant)

    def _init_deck(self, variant: Variant):
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

    def print(self, cutoff=None):
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

    def check_for_infeasibility(self):
        paths_through_deck = self._suitify()
        proved_infeasible = True
        for path in paths_through_deck:
            print(path)
            path = self._pathify(path)
            if self._check_for_capacity_loss(path):
                continue
            if self._check_for_pace_loss(path):
                continue
            proved_infeasible = False
            break
        return proved_infeasible

    def _suitify(self):
        locations = {}
        for loc, card in enumerate(self.deck):
            rank, suit = card.interpret()
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

    def _check_for_pace_loss(self, path):
        index = len(self.deck) - 1
        curr = path[index]
        # checks for BDR loss
        if curr and self.deck[index].interpret()[1] != 5:
            return True
        pace = 2
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

    def _check_for_capacity_loss(self, path):
        path = path[::-1]
        hand = set()
        index = 0
        stacks = [0, 0, 0, 0, 0]
        while path:
            curr = path.pop()
            if not curr:
                continue
            card = self.deck[index]
            suit, rank = card.interpret()
            suit -= 1  # 0-indexing
            if stacks[suit] == rank + 1:  # i.e., playable
                newly_playable = card.value + 1
                stacks[suit] += 1
                while newly_playable in hand:
                    hand.remove(newly_playable)
                    newly_playable += 1
                    stacks[suit] += 1
            else:
                hand.add(card.value)
                if len(hand) == 10:  # max capacity
                    return True
        return False

class Card:
    """A card with suit and rank"""
    def __init__(self, suit_index, rank):
        self.value = (suit_index << 31) | rank
    def interpret(self):
        """Returns (suit index, rank)."""
        x = self.value >> 31
        y = self.value & 0x7FFFFFFF
        return x, y

if __name__ == "__main__":
    VAR = "No Variant"
    SEED = "p2v0scommendation-splintering-gondolas"
    DECK = Deck(VAR)
    DECK.shuffle(SEED)
    DECK.print()
    print(DECK.check_for_infeasibility())
