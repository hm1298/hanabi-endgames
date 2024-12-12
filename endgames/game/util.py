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

def init_deck(variant: Variant):
    deck = []
    for suit_index, suit in enumerate(variant.suits):
        for rank in variant.clue_ranks:
            card = create_card(suit_index, rank)

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

    return deck

def get_deck(variant_name, seed):
    variant = lookup_variant(variant_name)
    deck = init_deck(variant)
    return shuffle_deck(seed, deck)

def print_deck(deck, cutoff=None):
    if cutoff is None:
        cutoff = len(deck)
    print(" ".join([str(interpret_card(card)) for card in deck[:cutoff]]))

# TODO: implement Hanab Live shuffling method
def shuffle_deck(seed, deck):
    """Shuffles deck according to a seed.

    Args:
        seed (str): a seed string as used on Hanab Live
        deck (list): a list of cards

    Returns:
        list: a copy of deck sorted by seed
    """
    result = deck[:]
    print(len(result))
    print(seed)
    random.seed(seed)
    random.shuffle(result)
    return result

def create_card(suit_index, rank):
    return (suit_index << 31) | rank

def interpret_card(n):
    x = n >> 31
    y = n & 0x7FFFFFFF
    return x, y

if __name__ == "__main__":
    VAR = "No Variant"
    SEED = "p2v0scommendation-splintering-gondolas"
    print_deck(get_deck(VAR, SEED))
