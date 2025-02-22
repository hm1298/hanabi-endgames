"""Infeasibility checks for hanabi-like games."""

from bisect import bisect
import itertools
from endgames.game.util import Deck, create_bespoke_deck, lookup_hand_size
from endgames.game.io import read_printout

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
        # might want to ensure _check_for_dist_loss() always returns a bool
        # OR fold out this all(...) expression for robustness/debugging
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
        path = [False] * len(self.deck.deck)
        for loc in locs:
            path[loc] = True
        return path

    def _check_for_pace_loss(self, path, num_final_plays):
        """Checks if the path yields a pace loss."""
        index = len(self.deck.deck) - 1
        curr = path[index]
        pace = num_final_plays
        stacks = [0] * len(self.deck.variant.suits)
        # checks for BDR loss
        if curr:
            card = self.deck.deck[index]
            if card.interpret()[1] != 5:
                return True
            suit, rank = card.interpret()
            stacks[suit] = max(stacks[suit], 6 - rank)  # should be 1
        while pace < 5 * len(self.deck.variant.suits):  # max score
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
        stacks = [0] * len(self.deck.variant.suits)
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
        stacks = [0] * len(self.deck.variant.suits)
        locations = []
        # checks for BDR loss
        if curr:
            card = self.deck.deck[index]
            suit, rank = card.interpret()
            stacks[suit] = max(stacks[suit], 6 - rank)  # should be 1
        while pace < 5 * len(self.deck.variant.suits):  # max score
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
        stacks = [0] * len(self.deck.variant.suits)
        prev, reached_pace_zero = tuple(stacks), False
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
        # region ===== STEP ONE =====
        location = min(loc_to_cnct)
        stacks = loc_to_stack[location]  # access only, no modifying
        hand1 = [card.interpret() for index, card \
                 in enumerate(self.deck.deck[0:5]) if path[index]]
        hand2 = [card.interpret() for index, card \
                 in enumerate(self.deck.deck[5:10]) if path[index + 5]]
        hand1 = [tup for tup in hand1 if stacks[tup[0]] < tup[1]]
        hand2 = [tup for tup in hand2 if stacks[tup[0]] < tup[1]]
        pace0 = [card.interpret() for index, card \
                 in enumerate(self.deck.deck[location:]) \
                    if path[index + location]]
        # endregion


        # region ===== STEP TWO =====
        # Checks if final pace 0 breakpoint is single suited
        # If single suited, then only a 3-4-5 ending is possible
        # So it becomes necessary to track who holds the 3
        unique = False
        if sum(rank != 5 for rank in loc_to_stack[max(loc_to_cnct)]) == 1:
            unique = True
        # endregion


        # region ===== STEP THREE =====
        # Use last pace 0 breakpoint to find all possible endings
        location = max(loc_to_cnct)
        stacks = loc_to_stack[location]  # access only, no modifying

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

        # Returns early (infeasible) if there are no valid assignments
        if len(valid_assigns) == 0:
            return True

        # Returns early (infeasible) if unique and bad 34/35 dist
        if unique:
            suit = valid_assigns[0][0][0]
            attempt = ((suit, 3), (suit, 4))
            if self._assign_helper(attempt, hand1, hand2):
                return True
            attempt = ((suit, 3), (suit, 5))
            if self._assign_helper(attempt, hand1, hand2, anti=True):
                return True

        # Returns early (feasible) if there exists a pre pace 0 assignment
        for assign in valid_assigns:
            if assign[0] not in pace0 and assign[1] not in pace0:
                if unique:
                    continue
                return False

        # endregion


        # region ===== STEP FOUR =====
        turns_playable = [None] * (5 * len(self.deck.variant.suits) + 1)
        location = min(loc_to_cnct)
        stacks = list(loc_to_stack[location])
        for suit in range(len(self.deck.variant.suits)):
            for rank in range(stacks[suit] + 1, 6):
                index = 5 * suit + rank
                turns_playable[index] = []
        hand = set()
        for i in range(location + 1):  # recover the hand
            if not path[i]:
                continue
            card = self.deck.deck[i]
            suit, rank = card.interpret()
            if rank > stacks[suit]:
                hand.add(card.value)
        _temp_hand = set(hand)


        # Starting from the first pace 0 breakpoint, find earliest turns
        for draw_loc in range(location + 1, len(path) + 2):
            for suit, rank in enumerate(stacks):
                rank += 1
                # clean up this value vs index stuff. also, where's Card?
                value, index = suit << 31 | rank, 5 * suit + rank
                if value in hand:
                    hand.remove(value)
                    stacks[suit] += 1
                    turns_playable[index].append(draw_loc)
            if draw_loc < len(path) and path[draw_loc]:
                hand.add(self.deck.deck[draw_loc].value)

        # Now finds latest turns greedily for cards of each suit in turn
        for chosen_suit in range(len(self.deck.variant.suits)):
            stacks = list(loc_to_stack[location])
            hand = set(_temp_hand)
            for draw_loc in range(location + 1, len(path) + 2):
                found, value, index = False, None, None
                for suit, rank in enumerate(stacks):
                    rank += 1
                    if suit == chosen_suit:
                        continue
                    value, index = suit << 31 | rank, 5 * suit + rank
                    if value in hand:
                        found = True
                        break
                if not found:
                    suit, rank = chosen_suit, stacks[chosen_suit] + 1
                    value, index = suit << 31 | rank, 5 * suit + rank
                    # could add check to ensure this card is playable
                    # but all paths passed to _solve_breakpoint() have
                    # satisfied pace checks already, meaning SOME card
                    # is playable (so this one, the last option, is)
                    turns_playable[index].append(draw_loc)
                hand.remove(value)
                stacks[suit] += 1
                if draw_loc < len(path) and path[draw_loc]:
                    hand.add(self.deck.deck[draw_loc].value)

        # data validation, i.e. built-in testing
        for index, entry in enumerate(turns_playable):
            try:
                assert(entry is None or len(entry) == 2)
                assert(entry is None or entry[1] >= entry[0])
            except AssertionError as e:
                print(index, entry, stacks)
                raise e
        # endregion


        # region ===== STEP FIVE =====
        precursors = [[] for _ in range(5 * len(self.deck.variant.suits) + 1)]
        successors = [[] for _ in range(5 * len(self.deck.variant.suits) + 1)]
        stacks = loc_to_stack[location]  # access only, no modifying
        for deck_loc, card in enumerate(self.deck.deck):
            if deck_loc < location:
                continue
            if not path[deck_loc]:
                continue
            for pre_index, interval in enumerate(turns_playable):
                if interval is None:
                    continue
                if interval[0] <= deck_loc <= interval[1]:
                    precursors[card.index].append(pre_index)
                    successors[pre_index].append(card.index)

        # checks if the pace 0 playable can possibly lead to a card
        # that can be played on the last turn
        dead_end = False
        connectors = [False] * (5 * len(self.deck.variant.suits) + 1)
        connectors[self.deck.deck[location].index] = True
        for deck_loc, card in enumerate(self.deck.deck):
            if deck_loc < location:
                continue
            if not path[deck_loc]:
                continue
            if connectors[card.index]:
                for index in successors[card.index]:
                    connectors[index] = True
        end = False
        for assign in valid_assigns:
            for i in range(2):
                suit, rank = assign[i]
                index = 5 * suit + rank
                if connectors[index]:
                    end = True
                    break
            if end:
                break
        dead_end = not end
        if dead_end:
            degrees_of_freedom = 5 * len(self.deck.variant.suits) - sum(stacks) - \
                (len(hand1) + len(hand2) + len(pace0))
            # if no relevant cards appear after starting hand and pre
            # pace 0, then players with no relevant cards in starting
            # hand may lose to hand distribution because of a dead end
            if degrees_of_freedom == 0:
                if len(hand1) == 0 or len(hand2) == 0:
                    return True

        # special consideration for unique decks
        if unique:
            suit = valid_assigns[0][0][0]
            index = 5 * suit + 3
            queue = list(precursors[index])  # do not mutate precursors
            already_queued = set(queue)
            good_dist = False
            if len(queue) == 0:
                good_dist = True
            while queue:
                index = queue.pop()

                # if this card cannot be held in the correct hand for
                # proper 345 distribution, then ignore and move on
                suit2, rank2 = divmod(index - 1, 5)
                rank2 += 1
                attempt = ((suit, 4), (suit2, rank2))
                if self._assign_helper(attempt, hand1, hand2):
                    continue
                attempt = ((suit, 5), (suit2, rank2))
                if self._assign_helper(attempt, hand1, hand2, anti=True):
                    continue

                # if this card can be held in either hand, conclude
                # we cannot prove infeasible, and move on
                if len(precursors[index]) == 0:
                    good_dist = True
                    break

                # otherwise, look at the card's precursors
                for pre_index in precursors[index]:
                    if pre_index in already_queued:
                        continue
                    already_queued.add(pre_index)
                    queue.append(pre_index)
            if not good_dist:
                return True
        # endregion


        return False

    def _assign_helper(self, t, h1, h2, anti=False):
        if not anti:
            return (t[0] in h1 and t[1] in h1) or (t[0] in h2 and t[1] in h2)
        return (t[0] in h1 and t[1] in h2) or (t[0] in h2 and t[1] in h1)

class ShapeOptions:
    """Options for ShapeIdentifier."""
    def __init__(self, bdrs=None, hand_capacity=10, playables_play=True):
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
    for no, d in enumerate(read_printout(FILE)):
        if no != D_NO:
            continue
        DECK = create_bespoke_deck(d)
        print(DECK.check_for_infeasibility())
