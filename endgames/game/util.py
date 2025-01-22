"""Methods for fetching initial positions and other utility."""

from bisect import bisect
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
        if si is None:
            si = ShapeIdentifier()
        pf = PathFinder(self, si, 2, 5)
        return pf.check_for_infeasibility()

class PathFinder:
    """A multi-use solver for hanabi-like decks

    Attributes:
        deck (Deck): The deck of cards
        num_players (int): Number of players in the game (used for pace)
        hand_size (int): Number of cards each player can hold
        capacity (int): Total hand size of all players
    """
    def __init__(self, deck: Deck, si, num_players=2, hand_size=None):
        """Initializes the pathfinder based on game type

        Args:
            deck (Deck): The deck of cards
            num_players (int): Number of players
            hand_size (int): Hand size for each player
        """

        self.deck = deck
        self.si = si
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
        _, suit_to_ordering = self._split_into_suits()
        paths_through_deck = self._suitify2(suit_to_ordering)
        inf, paths = self.check_for_1p_inf(paths_through_deck)
        if len(paths) == 0:
            return inf, False
        # print(len(paths))
        return all(self._check_for_dist_loss(path) for path in paths), True

    def check_for_1p_inf(self, paths):
        """Checks for infeasibility in the 1-player case.

        Returns True/False if the infinite clue 2p case can be decided
        here, else returns pace 0 paths for a hand distribution check.
        """
        proved_infeasible = True
        found_pace_one = False
        dist_paths = []
        for path in paths:
            if isinstance(path[0], tuple):
                path = itertools.chain(*path)
            path = self._pathify(path)
            if self._check_for_capacity_loss(path, self.capacity):
                continue
            if self._check_for_pace_loss(path, self.num_players):
                continue
            if not self._check_for_pace_loss(path, 1):
                found_pace_one = True
                proved_infeasible = False
                break
            dist_paths.append(path)
        if found_pace_one:
            dist_paths = []
        return proved_infeasible, dist_paths

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
        """Splits the deck by suit into useful dictionaries.

        Returns:
        - locations (dict): Mapping of suit to rank to deck indices
        - suits (dict): Mapping of suit to list of Card instances
        """
        locations = {}  # suit to rank to deck indices
        suits = {}
        for loc, card in enumerate(self.deck.deck):
            suit, rank = card.interpret()
            if suit not in locations:
                locations[suit] = {}
                suits[suit] = []
            if rank not in locations[suit]:
                locations[suit][rank] = []
            locations[suit][rank].append(loc)
            suits[suit].append(card)

        for suit, ranks_to_locs in locations.items():
            for rank, locs in ranks_to_locs.items():
                if rank in (1, 5):
                    ranks_to_locs[rank] = [min(locs)]

        return locations, suits

    # currently being phased out
    def _suitify(self, locations):
        # minimal score of an All or Nothing agent that must eventually
        # play all cards and plays cards as the last copy of a playable
        # card is drawn
        score_lb = [[0] * 50 for _ in range(5)]

        # used to implement pace checks (...b...a...b...c...)
        # pace calculation for each suit
        for suit, ranks_to_locs in locations.items():
            index = suit - 1
            locs = []
            for rank in range(1, 6):
                locs.append(max(ranks_to_locs[rank]))
                loc = max(locs)
                score_lb[index][loc] = rank

        paths = []
        for ranks_to_locs in locations.values():
            paths += ranks_to_locs.values()
        return itertools.product(*paths)

    def _suitify2(self, orderings):
        """Generates possible paths through the deck.

        Utilizes precomputation on suit shape. Finds path for each
        suit then combines each suit path to get a full deck path.
        """
        paths = []
        for suit in orderings:
            paths.append(self.si.identify(orderings[suit]))
        return itertools.product(*paths)

    def _pathify(self, locs):
        """Converts a list of locations into a boolean path."""
        path = [False] * 50
        for loc in locs:
            path[loc] = True
        return path

    def _check_for_pace_loss(self, path, num_final_plays):
        """Checks if the path yields a pace loss."""
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
            stacks[suit] = max(stacks[suit], 6 - rank)  # should be 1
        while pace < 25:  # 25 is max score
            pace += 1
            index -= 1
            curr = path[index]
            if curr:
                card = self.deck.deck[index]
                suit, rank = card.interpret()
                stacks[suit] = max(stacks[suit], 6 - rank)
            if sum(stacks) > pace:
                return True
        return False

    def _check_for_capacity_loss(self, path, capacity):
        """Checks if the path yields a hand capacity loss."""
        hand = set()
        stacks = [0, 0, 0, 0, 0]
        for index, curr in enumerate(path):
            if not curr:
                continue
            card = self.deck.deck[index]
            suit, rank = card.interpret()
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

    def _check_for_dist_loss(self, path):
        """Checks if the path yields a hand distribution loss."""
        locations = self._get_pace_breakpoints(path)
        connectors, stacks = self._get_breakpoint_connectors(path, locations)
        # print("Connectors and stacks:", connectors, stacks)
        return self._solve_breakpoint(path, connectors, stacks)

    def _get_pace_breakpoints(self, path, value=0):
        """Returns locations at which pace must reach value."""
        index = len(self.deck.deck) - 1
        curr = path[index]
        pace = self.num_players
        stacks = [0, 0, 0, 0, 0]
        locations = []
        # checks for BDR loss
        if curr:
            card = self.deck.deck[index]
            suit, rank = card.interpret()
            stacks[suit] = max(stacks[suit], 6 - rank)  # should be 1
        while pace < 25:  # 25 is max score
            pace += 1
            index -= 1
            curr = path[index]
            if curr:
                card = self.deck.deck[index]
                suit, rank = card.interpret()
                stacks[suit] = max(stacks[suit], 6 - rank)
            if sum(stacks) == pace + value:
                locations.append(index)
        return locations

    def _get_breakpoint_connectors(self, path, locations):
        locs_to_entries = {loc: [] for loc in locations}
        locs_to_stacks = {loc: [] for loc in locations}
        hand = set()
        stacks = [0, 0, 0, 0, 0]
        prev, reached_pace_zero = (0, 0, 0, 0, 0), False
        for index, curr in enumerate(path):
            if not curr:
                continue
            card = self.deck.deck[index]
            suit, rank = card.interpret()

            if index == locations[-1]:
                locations.pop()
                curr = tuple(stacks)
                locs_to_stacks[index] = curr
                if reached_pace_zero:
                    diff = tuple(a - b for a, b in zip(curr, prev))
                    for suit_index, val in enumerate(diff):
                        if val > 0:
                            connector = (suit_index + 1, curr[suit_index])
                            locs_to_entries[index].append(connector)
                else:
                    locs_to_entries[index] = "anything"
                if len(locations) == 0:
                    break
                reached_pace_zero = True
                prev = curr

            if stacks[suit] == rank - 1:  # i.e., playable
                newly_playable = card.value + 1
                stacks[suit] += 1
                while newly_playable in hand:
                    hand.remove(newly_playable)
                    newly_playable += 1
                    stacks[suit] += 1
            else:
                hand.add(card.value)
        return locs_to_entries, locs_to_stacks

    def _solve_breakpoint(self, path, loc_to_cnct, loc_to_stack):
        """Basic algorithm is as follows:

        1. Partition cards into a few categories:
            (i) Must be held in hand 1.
            (ii) Must be held in hand 2.
            (iii) Could be held in either hand before pace 0.
            (iv) Drawn at pace 0.
        1b. For now, all cards drawn after starting hands and before
        pace 0 are assumed to be of type (iii).
        2. Separate as unique if the only possible 3-card ending is
        3-4-5 of the same suit. This is the only type of ending where
        the hand of the third to last play matters (with high clues).
        3. Use last pace 0 breakpoint to determine all possible 2-card
        endings. With the exception listed in #2, these are the only
        cards that matter for the hand distribution problem.
        3b. Return feasible if such a pair has both entries in (iii).
        4. For each unplayed card (at first pace 0 breakpoint), find
        the earliest turn and the latest turn it can play. Use this to
        determine which cards of type (iv) could be held in each hand.
        5. Iterate through the pairs from #3 to determine if there is
        a hand distribution that works, according to #4. Use a greedy
        approach (suit of earlier card plays > suit of later card
        plays > suits of other cards play) to determine if possible.
        For unique decks, go back and track the hand of the 3 if the
        4-5 pair is correctly distributed.

        Args:
            path (_type_): _description_
            loc_to_cnct (_type_): _description_
            loc_to_stack (_type_): _description_

        Returns:
            _type_: _description_
        """
        # ===== STEP ONE =====
        hand1 = [card.interpret() for index, card in enumerate(self.deck.deck[0:5]) if path[index]]
        hand2 = [card.interpret() for index, card in enumerate(self.deck.deck[5:10]) if path[index + 5]]
        pace0 = [card.interpret() for index, card in enumerate(self.deck.deck[min(loc_to_cnct):]) if path[index + min(loc_to_cnct)]]
        # print(pace0, "in", [card.interpret() if path[index] else None for index, card in enumerate(self.deck.deck)])


        # ===== STEP TWO =====
        # Checks if final pace 0 breakpoint is single suited
        # If single suited, then only a 3-4-5 ending is possible
        # So it becomes necessary to track who holds the 3
        unique = False
        if sum(rank != 5 for rank in loc_to_stack[max(loc_to_cnct)]) == 1:
            unique = True


        # ===== STEP THREE =====
        # Use last pace 0 breakpoint to find all possible endings
        location = max(loc_to_cnct)
        stacks = loc_to_stack[location]

        # First, consider each player holds a 5 on last turn
        suits = [index for index, value in enumerate(stacks) if value < 5]
        valid_assigns = []
        for i in suits:
            for j in suits:
                if i == j:
                    continue
                attempt = ((i, 5), (j, 5))
                # the following check could be retooled as a broader
                # "pre pace 0" check in the future. for now, it only
                # considers assignments impossible if the starting
                # hand cards prevent this ending assignment.
                if self._assign_helper(attempt, hand1, hand2):
                    continue
                valid_assigns.append(attempt)

        # Next, consider each player holds a matching 4 & 5 on last turn
        suits = [index for index, value in enumerate(stacks) if value < 4]
        for i in suits:
            attempt = ((i, 4), (i, 5))
            if self._assign_helper(attempt, hand1, hand2):
                continue
            valid_assigns.append(attempt)


        # Returns early (feasible) if there exists a pre pace 0 assignment
        for assign in valid_assigns:
            if assign[0] not in pace0 and assign[1] not in pace0:
                if unique:
                    continue
                return False


        # ===== STEP FOUR =====
        turns_playable = [None] * 26
        for suit, rank in pace0:
            index = 5 * suit + rank
            turns_playable[index] = []

        # Starting from the first pace 0 breakpoint, find earliest turns
        location = min(loc_to_cnct)
        stacks = loc_to_stack[location]
        hand = set()
        for i in range(location):  # recover the hand
            if path[i]:
                card = self.deck.deck[i]
                suit, rank = card.interpret()
                if stacks[suit] > rank:
                    hand.add(card.value)

        for draw_loc in range(location, len(self.deck.deck)):
            for suit, rank in enumerate(stacks):
                # clean up this value vs index stuff. also, where's Card?
                value, index = suit << 31 | rank, 5 * suit + rank
                if value in hand:
                    hand.remove(value)
                    stacks[suit] += 1
                    turns_playable[index].append(draw_loc)
            if path[draw_loc]:
                hand.add(self.deck.deck[draw_loc].value)

        # TODO: find latest turns. turns_playable currently a bunch of [x]'s
        # immediate implementation idea~ greedy approach each suit in turn


        # ===== STEP FIVE =====
        # TODO


        if len(valid_assigns) == 0:
            return True
        if unique:
            return False
        return len(valid_assigns) == 0

    def _assign_helper(self, t, h1, h2):
        return (t[0] in h1 and t[1] in h1) or (t[0] in h2 and t[1] in h2)

class ShapeOptions:
    """Options for ShapeIdentifier."""
    def __init__(self, bdrs=None, hand_capacity=None, playables_play=True):
        self.bdrs = bdrs
        self.hand_capacity = hand_capacity
        self.check_for_hand_dist = None
        self.playables_play = playables_play
        self.sh_ranks = None

        if bdrs is None:
            self.bdrs = set()
        if hand_capacity is None:
            self.check_for_hand_dist = False
        else:
            self.check_for_hand_dist = True

    def is_bdr(self, card):
        """Determines if card should be a BDR."""
        return card.rank in self.bdrs

    def add_bdr(self, card):
        """Adds a bdr to self.bdrs."""
        self.bdrs.add(card.rank)

    def hand_dist(self, cards):
        """Sets, typecasts, and returns self.sh_ranks."""
        self.sh_ranks = tuple(self.get_hand_dist_concerns(cards))
        return self.sh_ranks

    def get_hand_dist_concerns(self, cards):
        """Returns ranks of cards with hand dist concern."""
        result = []
        if not self.check_for_hand_dist:
            return result
        counts = [None, 0, 0, 0, 0, 0]
        for card in cards:
            if card.location >= self.hand_capacity:
                return result
            counts[card.rank] += 1
            if counts[card.rank] == 2:
                result.append(card.rank)
        return result

class ShapeIdentifier:
    """A suit-centric approach to deck infeasibility.

    Attributes:
        cards (tuple): tuple of Cards
        counts (Counter): Amount of each type of card
        locations (list): list of Card locations
        valid_subsequences (dict): Memoization of prior suit orderings
    """
    def __init__(self, options: ShapeOptions = None):
        """Initializes based on suit ordering and location info.

        Args:
            cards (list): list of cards in order of appearance in deck
            locations (list): list of list of possible deck locations
        """
        if options is None:
            options = ShapeOptions()
        self.options = options
        self.valid_subsequences = {}

        self._locations = None
        self._index = None
        self._path = None
        self._playable = None
        self._set_protected_attrs()

    def _set_protected_attrs(self):
        """Setter function for protected attributes."""
        self._locations = [None, [], [], [], [], []]
        self._index = 0
        self._path = []
        self._playable = [None, -1, None, None, None, None]

    def get_shape(self, cards):
        """Gets shape of cards. Sets self._locations."""
        self._set_protected_attrs()
        ordering = []
        is_first = [None, True, True, True, True, True]
        is_played = [True, False, False, False, False, False]
        for card in cards:
            if is_first[card.rank] and self.options.is_bdr(card):
                is_first[card.rank] = False
                continue
            if is_played[card.rank]:
                continue
            if is_played[card.rank - 1]:
                is_played[card.rank] = True
            ordering.append(card.rank)
            is_first[card.rank] = False
            self._locations[card.rank].append(card.location)
        ordering = tuple(ordering)
        # print(self._locations)
        # print(shape)
        dist = self.options.hand_dist(cards)
        return ordering, dist

    def identify(self, cards):
        """Checks if shape has been identified.

        It if hasn't, identifies it and adds to memory.
        """
        self.get_shape(cards)
        # TODO: bugfix, currently the locations stored in
        # self.valid_subsequences are ONLY accurate for the original
        # list of cards used to populate its shape's entry. Need to
        # use indices into shape[0] rather than the internal card
        # locations. However, this requires passing shape[0] to
        # identify_recurse() in some way or other, since currently it
        # only has access to the class attribute _locations.
        # if shape not in self.valid_subsequences:
            # self.valid_subsequences[shape] = tuple(self.identify_recurse())
        return tuple(self.identify_recurse())

    def identify_recurse(self):
        """Identifies playable paths.

        This is the core method. Works recursively to return a list of
        paths that satisfy certain extra constraints. Each path is a list
        of 5 locations constituting a legal order to play the suit.

        The key constraints are:
            - No discards of playables. So any subsequence of self.cards
            with pattern (...a...a...) only permits legal paths that use
            the first location of a.
            - No holding an earlier copy of a duplicate unplayable. So
            any subsequence of self.cards with pattern (...b...b...a...)
            where b must play before a, whose earliest location is shown,
            only permits legal paths that use the second location of b.

        Currently, no pace checks (and any would have to come after
        memoization) so the exact values in self._locations are not very
        important, just their ordering. We use self._locations instead of
        indices in self.cards simply because we have the info on hand and
        it is more accurate to the deck.

        Returns:
            list: possible paths for this suit ordering through the deck
        """
        self._index += 1
        rank = self._index
        if rank == len(self._locations):
            answer = tuple(self._path)
            self._index -= 1
            self._path = self._path[:-1]
            return [answer]
        locations = self._locations[rank]
        playable = self._playable[rank]

        if rank in self.options.sh_ranks:
            paths = []
            for loc in locations:
                paths += self._helper(loc, max(loc, playable))
                self._index = rank
                self._path = self._path[:rank - 1]
                self._playable = self._playable[:rank + 1] + \
                    [False] * (len(self._playable) - (rank + 1))
            return paths

        attempt = locations[0]
        if attempt > playable:
            return self._helper(attempt, attempt)

        attempt = locations[-1]
        if attempt < playable:
            return self._helper(attempt, playable)

        attempt = bisect(locations, self._playable[rank]) - 1
        path1 = self._helper(locations[attempt], self._playable[rank])
        self._index = rank
        self._path = self._path[:rank - 1]
        self._playable = self._playable[:rank + 1] + \
            [False] * (len(self._playable) - (rank + 1))
        path2 = self._helper(locations[attempt + 1], locations[attempt + 1])

        return path1 + path2

    def _helper(self, location, playable):
        """Helper method for ShapeIdentifier.identify().

        Updates the local attributes based on how far identify()
        is through checking possible paths on this deck.
        """
        self._path.append(location)
        if self._index + 1 < len(self._playable):
            self._playable[self._index + 1] = playable
        return self.identify_recurse()

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
        assert self.suit != 5  # fixed an indexing error
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

if __name__ == "__main__":
    VAR = "No Variant"
    SEED = "p2v0scommendation-splintering-gondolas"
    DECK = Deck(VAR)
    DECK.shuffle(SEED)
    DECK.print()
    print(DECK)
    # print(DECK.check_for_infeasibility())
    FILE = "assets/rama_hard_decks.txt"
    D_NO = 8
    for i, d in enumerate(read_printout(FILE)):
        if i != D_NO:
            continue
        DECK = create_bespoke_deck(d)
        print(DECK.check_for_infeasibility())
