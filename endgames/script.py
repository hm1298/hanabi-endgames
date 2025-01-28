"""Quick script for "test as you go" development."""

from endgames.game.util import create_bespoke_deck, create_hypo_url
from endgames.game.io import read_printout

def main():
    """Does this do what I expect?"""
    raw_deck = read_printout("assets/rama_hard_decks.txt")[0]
    deck = create_bespoke_deck(raw_deck)
    print(create_hypo_url(deck))

if __name__ == "__main__":
    main()
