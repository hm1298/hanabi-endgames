"""Methods for fetching initial positions and other utility."""

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

class Card:
    """A card with suit and rank"""
    def __init__(self, suit_index, rank):
        self.value = (suit_index << 31) | rank
    def interpret(self):
        x = self.value >> 31
        y = self.value & 0x7FFFFFFF
        return x, y

if __name__ == "__main__":
    VAR = "No Variant"
    SEED = "p2v0scommendation-splintering-gondolas"
    DECK = Deck(VAR)
    DECK.shuffle(SEED)
    DECK.print()
