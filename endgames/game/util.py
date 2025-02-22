"""Methods for fetching initial positions and other utility."""

import random
from endgames.game.variants import Variant, VARIANT_NAMES_DICT

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
    if num_players == 6:
        return 3
    return 4

class Deck:
    """A deck of cards for a Hanabi-like game

    This class handles the creation and low-level analysis of a deck
    of cards, with support for different variants and both seed-based
    and arbitrary deck orders.

    Attributes:
        seed (str): A string representing the seed used for shuffling.
            Plans to implement the Hanab Live shuffling algorithm (or
            at least gain consistency with Rama's approach)
        variant (Variant): The variant of the current game
        deck (list): A list of Card objects
    """
    def __init__(self, variant=None):
        """Initializes the deck based on the specified variant.

        When a variant is not chosen, the base suits of Hanab Live
        are instead used ("No Variant"). The deck is populated with
        cards but not ordered until a seed is chosen for shuffling
        or a preselected order is provided with set_deck().

        Args:
            variant (str): name of a Hanab Live variant
        """
        if variant is None:
            variant = lookup_variant("No Variant")
        elif isinstance(variant, str):
            variant = lookup_variant(variant)

        self.seed = None
        self.variant = variant
        self.deck = None  # overwritten by _init_deck()
        self._init_deck(variant)

    def _init_deck(self, variant: Variant):
        """Initializes self.deck. Requires hanabi game logic.

        Args:
            variant (Variant): a Hanab Live game variant
        """
        deck = []
        for suit_index, suit in enumerate(variant.suits):
            for rank in variant.clue_ranks:
                # intentionally do not set card location
                # only set card location when creating deck ordering

                if variant.stack_size == 4 and rank == 5:
                    continue
                deck.append(Card(suit_index, rank))
                if suit.one_of_each:
                    continue
                if variant.sudoku:
                    deck.append(Card(suit_index, rank))
                elif rank == 1:
                    if variant.up_or_down or suit.reversed:
                        continue
                    deck.append(Card(suit_index, rank))
                    deck.append(Card(suit_index, rank))
                elif rank == variant.critical_rank:
                    continue
                elif rank == 5:
                    if suit.reversed:
                        deck.append(Card(suit_index, rank))
                        deck.append(Card(suit_index, rank))
                else:
                    deck.append(Card(suit_index, rank))

        self.deck = deck

    def __repr__(self):
        """Formats as a string."""
        fmt = ""
        for card in self.deck:
            suit_index, rank = card.interpret()
            suit = self.variant.suits[suit_index]
            if suit.abbreviation is not None:
                fmt += suit.abbreviation.lower()
            else:
                fmt += suit.id.lower()
            fmt += str(rank) + " "
        return fmt[:-1]

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
                if attempt.abbreviation is not None and \
                    word.lower() == attempt.abbreviation.lower():
                    suit = attempt.name
                    break
                if attempt.id is not None and \
                    word.lower() == attempt.id.lower():
                    suit = attempt.name
                    break
                if word.lower() == attempt.name.lower():
                    suit = attempt.name
                    break
            suit_index = self.variant.suit_names.index(suit)
            self.deck.append(Card(suit_index, rank))
        self._set_card_locations()

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

    def shuffle(self, seed):
        """Shuffles deck according to a seed.

        Args:
            seed (str): a seed string as used on Hanab Live
            deck (list): a list of cards

        Returns:
            list: a copy of deck sorted by seed
        """
        local_random = random.Random()
        self.seed = seed
        local_random.seed(seed)
        local_random.shuffle(self.deck)
        self._set_card_locations()

    def _set_card_locations(self):
        """Assigns locations to each card in the deck.

        Helper function that should be called any time the deck is
        reordered and the attribute Card.location will be used at
        any point.
        """
        for location, card in enumerate(self.deck):
            card.set_location(location)

    def check_for_infeasibility(self, si=None):
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
        # lazy imports to permit this method to function as intended
        # may later refactor Deck at a higher level of abstraction
        # pylint: disable=C0415
        from endgames.game.study import PathFinder, ShapeIdentifier
        if si is None:
            si = ShapeIdentifier()
        pf = PathFinder(self, si, 2, 5)
        try:
            return pf.check_for_infeasibility()
        except BaseException as e:
            print("An error occurred on the following deck.")
            print(self)
            print(create_hypo_url(self))
            raise e

class Card:
    """A card with suit and rank

    Attributes:
        value (int): Encodes suit and rank
        suit (int): The suit index
        rank (int): The numerical rank of the card
        location (int): The card's location in a deck
    """
    def __init__(self, suit_index, rank):
        """
        Initializes the card with suit and rank.

        Args:
            suit_index (int): The suit index
            rank (int): The card's rank. If card does not have a
                numerical rank, then a number assignment must occur
                elsewhere
        """
        self.value = (suit_index << 31) | rank
        self.suit = suit_index
        self.rank = rank
        # assert self.suit != 5  # fixed an indexing error
        self.index = 5 * self.suit + self.rank
        self.location = None
    def interpret(self):
        """Returns (suit index, rank)"""
        return self.suit, self.rank
    def set_location(self, new_value):
        """Setter function for Card.location"""
        self.location = new_value

def create_bespoke_deck(deck, variant=None):
    """Create deck from input. Assumes No Variant."""
    if variant is None:
        variant = "No Variant"
    result = Deck(variant)
    result.set_deck(deck)
    return result

def create_hypo_url(deck, num_players=2):
    """Create URL for loading deck on Hanab Live.

    Translated from the https://hanab.live/ Github:
    https://github.com/Hanabi-Live/hanabi-live/blob/cfde8020cd110bc051aef79a41d8ee4e13680e99/packages/client/src/lobby/hypoCompress.ts

    Args:
        deck (Deck): deck for use in hypothetical

    Returns:
        str: hanab live url
    """
    prefix = "https://hanab.live/shared-replay-json/"
    base_62 = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    result = ""

    # First section: number of players, rank min, rank max, and deck
    result += str(num_players)
    result += "15"  # represents rank min & rank max
    result += "".join(base_62[card.index - 1] for card in deck.deck)
    result += ","

    # Second section: game actions
    # We only use a trivial action here; Alice plays/bombs slot 1
    result += "00ae"  # the two numbers describe available actions
    result += ","

    # Third section: variant number
    result += str(deck.variant.id)

    # Now add '-'s to the URL for readability (line breaks)
    result = "-".join(result[i:i+20] for i in range(0, len(result), 20))

    return prefix + result
