"""An original gamestate."""

class GameState:
    """
    GameState provides the basic tools for analyzing different
    positions in various hanabi-like games.

    This class intends to provide utility in varying use cases
    without sacrificing speed, so its core functionality is
    intentionally limited. Add bespoke methods in subclasses.
    """

    def __init__(self, data=None):
        # TODO: modify or remove None option
        if data is None:
            data = {
                "deck": list(range(40)),
                "stacks": [0] * 5,
                "hands": [list(range(5)), list(range(5))]
            }
        self.deck = data["deck"]
        self.stacks = data["stacks"]
        self.hands = data["hands"]
        self.num_players = len(data["hands"])

    def is_isomorphic(self, other):
        """Determines if two GameStates are isomorphic.

        Two GameStates x and y are isomorphic if there exists
        a mapping between suits phi such that:
            x = phi(y)
        This is equivalent to stripping away the value of suits,
        ordering the resulting list of sets of cards, and
        checking if they are equal. The internal logic of this
        check is contained in get_repr().

        Args:
            other (GameState): another GameState

        Returns:
            Boolean: whether self and other are isomorphic
        """
        return self.get_repr() == other.get_repr()

    def get_repr(self, padding=0):
        """Returns a deck representation with suit info removed.

        First, finds all cards in gamestate and groups aspects of
        their identity by suit in sets. Then, orders those sets.
        This satisfies the conditions for isomorphism SO LONG AS
        the hanabi-like game has a specific turn for a player. If
        the game does not, then it is necessary to check if a
        reordering of the players will yield equal representation;
        trying different values of padding in range(self.num_players)
        provides that option.

        Args:
            padding (int, optional): Starting player number. Defaults to 0.

        Returns:
            List: deck representation, a list of sets of suitless cards
        """
        # instantiation
        suit_to_set_cards = {}
        for card in self.stacks:
            suit_to_set_cards[get_suit(card)] = {get_rank(card)}

        # populate deck
        for card in self.deck:
            suit_to_set_cards[get_suit(card)].add(("deck", get_rank(card)))

        # populate hands
        i = padding
        for hand in self.hands:
            i = (i + 1) % self.num_players
            for card in hand:
                suit_to_set_cards[get_suit(card)].add(("hand " + str(i), get_rank(card)))

        result = list(suit_to_set_cards.values())
        result.sort()

        return result

# TODO: phase out, likely access directly for speed
def get_suit(card):
    return card.Suit
def get_rank(card):
    return card.Rank
