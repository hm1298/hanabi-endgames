"""Methods for fetching initial positions and other utility."""

from bisect import bisect
import itertools
import random
from collections import Counter
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

    def check_for_infeasibility(self):
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
        pf = PathFinder(self, 2, 5)
        return pf.check_for_infeasibility()

class PathFinder:
    """A multi-use solver for hanabi-like decks"""
    def __init__(self, deck: Deck, num_players=2, hand_size=None):
        self.deck = deck
        self.num_players = num_players
        if hand_size is None:
            hand_size = lookup_hand_size(num_players)
        self.hand_size = hand_size
        self.capacity = hand_size * num_players

    def check_for_infeasibility(self):
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
        suits_to_locs = self._split_into_suits()
        paths_through_deck = self._suitify(suits_to_locs)
        proved_infeasible = True
        for path in paths_through_deck:
            path = self._pathify(path)
            if self._check_for_capacity_loss(path, self.capacity):
                continue
            if self._check_for_pace_loss(path, self.num_players):
                continue
            proved_infeasible = False
            break
        return proved_infeasible

    def check_for_pace_loss(self):
        """Checks for pace loss with infinite hand size."""
        cards = set()
        locations = []
        for card in self.deck.deck:
            if card.value not in cards:
                cards.add(card.value)
                locations.append(card.value)
        path = self._pathify(locations)
        return self._check_for_pace_loss(path, self.num_players)

    def _split_into_suits(self):
        locations = {}  # suit to rank to deck indices
        for loc, card in enumerate(self.deck.deck):
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

        return locations

    def _suitify(self, locations):
        score_lb = [[0] * 50 for _ in range(5)]  # minimal score of an All or Nothing agent that must eventually play all cards and plays cards as the last copy of a playable card is drawn

        # pace calculation for each suit
        for suit, ranks_to_locs in locations.items():
            index = suit - 1
            locs = []
            for rank in range(1, 6):
                locs.append(max(ranks_to_locs[rank]))
                loc = max(locs)
                score_lb[index][loc] = rank

        for suit, ranks_to_locs in locations.items():
            paths = itertools.product(*ranks_to_locs.values())
            for path in paths:
                """validate in some way, should make 3 checks?
                DOES NOT CONTAIN:
                - a discard of a playable (...a...a...)
                - a save of an unplayable whose duplicate is later and also unplayable (...b...b...a...)
                - a save of a connector that is not needed to play for pace reasons (...b...a...b...c...)
                """
                # self._verify_suit_path(path)
                pass
        paths = []
        for ranks_to_locs in locations.values():
            paths += ranks_to_locs.values()
        return itertools.product(*paths)

    def _suit_pace_helper(self, scores):
        return scores

    #TODO: implement
    def _suit_checker(self):
        return "hi"

    def _pathify(self, locs):
        path = [False] * 50
        for loc in locs:
            path[loc] = True
        return path

    def _check_for_pace_loss(self, path, num_final_plays):
        index = len(self.deck.deck) - 1
        curr = path[index]
        pace = num_final_plays
        stacks = [0, 0, 0, 0, 0]
        # checks for BDR loss
        if curr:
            card = self.deck.deck[index]
            if card.interpret()[1] != 5:
                return True
            suit, rank = card.interpret()
            suit -= 1  # 0-indexing
            stacks[suit] = max(stacks[suit], 6 - rank)  # should be 1
        while pace < 25:  # 25 is max score
            pace += 1
            index -= 1
            curr = path[index]
            if curr:
                card = self.deck.deck[index]
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
            card = self.deck.deck[index]
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

class ShapeIdentifier:
    def __init__(self, cards, locations, first_one_plays=True,
                 playables_play=True, last_dupe_saved=True):
        self.cards = tuple(cards)
        self.counts = Counter(card.rank for card in self.cards)
        self.locations = locations
        self.valid_subsequences = {}
        self.first_one_plays = first_one_plays or playables_play
        self.playables_play = playables_play
        self.last_dupe_saved = last_dupe_saved

        self._index = 1
        self._path = []
        self._playable = [None, -1, None, None, None, None]

    def set_cards(self, cards):
        """Setter function for cards."""
        self.cards = tuple(cards)

        self._index = 1
        self._path = []
        self._playable = [None, -1, None, None, None, None]

    def identify(self, cards=None):
        """Identifies possible paths."""
        if cards is not None:
            self.set_cards(cards)
        if self.cards in self.valid_subsequences:
            return self.valid_subsequences[self.cards]

        # the meat of the program
        is_playable = [None, True, False, False, False, False]
        first_playable = [None, self.first_one_plays, False, False, False, False]  # only changes if we care to update first ones?
        last_unplayable = [None, False, False, False, False, False]  # needed?
        guaranteed_held = [None, False, False, False, False, False]
        occurrences = [None, 0, 0, 0, 0, 0]
        options = [None, [], [], [], [], []]
        for card in self.cards:
            rank = card.rank
            occurrences[rank] += 1
            if occurrences[rank] == 1:
                options[rank].append(card.location)
                if (is_playable[rank] and self.playables_play) or \
                    (rank == 1 and self.first_one_plays):
                    self._update_playables(rank, guaranteed_held, is_playable)
                    first_playable[rank] = True
            elif occurrences[rank] == self.counts[rank]:
                guaranteed_held[rank] = True
                if is_playable[rank] and first_playable[rank]:
                    continue
                ...

    """def identify2(self):
        rank, prepath = self._index, self._path
        start_index, end_index = 0, len(self.locations[rank])
        constraint1, constraint2 = True, True  # ...b...b...a... or ...a...a...
        while start_index != end_index and (constraint1 or constraint2):
            if self.locations[start_index] < self._playable_at[rank]:
                start_index += 1
            else:
                constraint1 = False
            if self.locations[end_index] > self._playable_at[rank]:
                end_index -= 1
            else:
                constraint2 = False
        if not constraint1:
            start_index -= 1
        if not constraint2:
            end_index += 1"""

    def identify3(self):
        self._index += 1
        rank = self._index
        if rank > len(self.locations):
            answer = self._path
            self._index -= 1
            self._path = self._path[-1]
            return answer
        locations = self.locations[rank]
        playable = self._playable[rank]

        attempt = locations[0]
        if attempt > playable:
            self._helper(attempt, attempt)

        attempt = locations[-1]
        if attempt < playable:
            self._helper(attempt, playable)

        left = bisect(locations, self._playable[rank])
        path1 = self._helper(locations[left], rank)
        self._index = rank
        self._path = self._path[:rank - 1]
        if self._index + 1 < len(self._playable):
            self._playable[rank + 1] = None
        path2 = self._helper(locations[left + 1], rank)

        return path1 + path2

    def _helper(self, location, playable):
        self._path.append(location)
        if self._index + 1 < len(self._playable):
            self._playable[self._index + 1] = playable
        return self.identify()

    def _update_playables(self, index, in_hand, is_playable):
        """Helper function for self.identify().

        Based on cards guaranteed to be held, updates each subsequent
        card to be playable. Mutates list is_playable.
        """
        index += 1
        is_playable[index] = True
        while in_hand[index] and index <= 5:
            index += 1
            is_playable[index] = True

# TODO: fix
class Card:
    """A card with suit and rank"""
    def __init__(self, suit_index, rank):
        self.value = (suit_index << 31) | rank
        self.suit = suit_index
        self.rank = rank
    def interpret(self):
        """Returns (suit index, rank)."""
        return self.suit, self.rank

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
        if i != D_NO:
            continue
        DECK = create_bespoke_deck(d)
        print(DECK.check_for_infeasibility())
