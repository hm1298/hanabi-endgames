"""Hanabi with infinite clues."""

from fractions import Fraction
from typing import Callable
import itertools

# TODO: consider using gmpy2 or quicktions for faster fractions

class Hanabi:
    """Generic base class for hanabi-like games.

    Everything you need to start a hanabi-like game, minus the details
    that might make it hanabi-like rather than exactly hanabi. Contains
    the deck, the stacks, the number of players, and the hand size of
    each player.
    """

    def __init__(self, deck, stacks, num_players, hand_sizes=None):
        self.is_successor = None  # a method
        self.is_successor: Callable

        self.deck = deck
        self.stacks = stacks
        self.num_players = num_players
        # TODO: abstract hand size (currently, it's hardcoded to 5)
        if hand_sizes is None:
            self.hands = [5] * num_players
        else:
            self.hands = hand_sizes

    def get_max_score(self):
        """Returns the maximum possible score--i.e., win condition."""
        return sum(self.stacks)

    def which_stack(self, card):
        """Returns the stack index if card can be played, else None."""
        if self.is_successor:
            return self.is_successor(self.stacks, card)
        return card[0] if self.stacks[card[0]] + 1 == card[1] else None

class Card(tuple):
    """Generic card class."""

    def __init__(self, suit_index, rank):
        self.suit_index = suit_index
        self.rank = rank
        super().__init__((suit_index, rank))

class Action():
    """Generic class for player actions."""

    def __init__(self, a_type, a_target, a_value):
        self.type = a_type
        self.target = a_target
        self.value = a_value

class InfiniteClueHanabi(Hanabi):
    """Class for infinite clue hanabi games."""

    def __init__(self, deck, stacks, player_hands):
        hand_sizes = [len(hand) for hand in player_hands]
        super().__init__(deck, stacks, len(player_hands), hand_sizes)

    def get_actions(self, gs):
        """Returns list of possible actions for player 1."""
        return list(range(len(gs[4]) + 1))

    def get_successors(self, gs, action, swap=True):
        """Returns dictionary of successor gamestates.

        (key, value) pairs have form (successor_state, probability)
        where successor_state is a gamestate that could result from
        this gamestate in 1 turn and probability is the probability of
        that gamestate occurring.
        """
        stacks = gs[0]
        trash = gs[1]
        deck = gs[2]
        trash1 = gs[3]
        hand1 = gs[4]
        trash2 = gs[5]
        hand2 = gs[6]
        actions = {}

        self.stacks = stacks

        # TODO: deal with empty deck
        deck_size = len(deck) + trash
        if deck_size <= 0:
            return 
        increment = 1 / (len(deck) + trash)
        deck_lookup = {}
        if trash:
            deck_lookup[(0, 1)] = trash * increment
        for i, card in enumerate(deck):
            new_deck = deck[:i] + deck[i+1:]  # expensive??
            deck_lookup[card] = [deck_lookup.get(card, 0) + increment, new_deck]

        # actions in player 1's hand
        increment = 1 / (len(hand1) + trash1)
        if trash1:
            for draw, result in deck_lookup.items():
                [prob, new_deck] = result
                if draw == (0, 1):
                    new_gs = (stacks,
                              trash - 1,
                              new_deck,
                              trash1,
                              hand1,
                              trash2,
                              hand2)
                else:
                    new_gs = (stacks,
                              trash,
                              new_deck,
                              trash1 - 1,
                              (*hand1, draw),
                              trash2,
                              hand2)
                actions[new_gs] = actions.get(new_gs, 0) + prob
        for i, card in enumerate(hand1):
            print(card)
            stack_index = self.which_stack(card)
            if stack_index is None:
                new_stacks = stacks
            else:
                print(stacks)
                new_stacks = stacks[:stack_index] + (stacks[stack_index] + 1,) + stacks[stack_index+1:]
                print(new_stacks, "yay")
            new_hand = hand1[:i] + hand1[i+1:]

            for draw, result in deck_lookup.items():
                [prob, new_deck] = result
                if draw == (0, 1):
                    new_gs = (new_stacks,
                              trash - 1,
                              new_deck,
                              trash1 + 1,
                              new_hand,
                              trash2,
                              hand2)
                else:
                    new_gs = (new_stacks,
                              trash,
                              new_deck,
                              trash1,
                              (*new_hand, draw),
                              trash2,
                              hand2)
                actions[new_gs] = actions.get(new_gs, 0) + prob


        # actions in player 2's hand
        if swap:
            swapped_gs = (stacks, trash, deck, trash2, hand2, trash1, hand1)
            other_actions = self.get_successors(swapped_gs, False)
            for key, value in other_actions.items():
                actions[key] = actions.get(key, 0) + value

        return actions

    def check_win_condition(self, gs):
        """Returns True if won."""
        return sum(gs[0]) == 25  # probably should change gamestate

    def check_loss_condition(self, gs):
        """Returns True if lost."""
        return gs[1] == -2

class Gamestate:
    """Class for managing gamestates in hanabi-like games."""

    def __init__(self, hanabi_game, **kwargs):
        self.game = hanabi_game
        for key, value in kwargs.items():
            setattr(self, key, value)


def gamestate_helper(gs):
    """Helper function for creating gamestates."""
    stacks = gs[0]
    bad_order = False
    i = 0
    for j in range(len(stacks)):  #pylint: disable=C0200
        if stacks[j] > stacks[i]:
            bad_order = True
            break
        i = j
    if bad_order:
        i += 1
        for j in range(len(stacks) - 1):
            if stacks[j] <= stacks[i]:
                break
        x = i + j
    # not really sure what i want to do with this any more

def pad(hand=None, trash_value=(0,1), size=5):
    """Returns a tuple of length size, padded with trash."""
    padding = (trash_value for _ in range(size))
    if hand:
        gen = itertools.chain(hand, padding)
        return tuple(next(gen) for _ in range(size))
    return tuple(padding)

def dp():
    """Dynamic programming on infinite clue hanabi"""
    hb = InfiniteClueHanabi(None, None, [])
    gs = ((5, 5, 5, 3, 3),
          0,  # trash count of cards in deck
          ((3, 4), (4, 4), (4, 5)),  # active cards in deck
          4,  # trash count of cards in first player's hand
          ((3, 5),),  # first player's active cards
          5,  # trash count of cards in second player's hand
          ())  # second player's active cards
    stack = [gs]
    lookup = {}

    # TODO: make this work. look at maxing return rather than avging
    while stack:
        curr = stack.pop()
        probs = hb.get_successors(curr, None)

        # try to solve the gamestate now, while checking if possible
        solved, ans, state = True, Fraction(), None
        gen = iter(probs.items())
        for state, prob in gen:
            if prob == 0:  # may be unnecessary
                continue
            if state not in lookup:
                if hb.check_win_condition(state):
                    lookup[state] = 1
                else:
                    solved = False
                    break
            ans += prob * lookup[state]

        # solve it
        if solved:
            lookup[curr] = ans
            continue

        # couldn't solve it--solve it later and solve subproblems now
        stack.append(curr)
        stack.append(state)
        for state, prob in gen:
            if prob == 0:
                continue
            if state not in lookup:
                stack.append(state)

    return lookup[gs]

if __name__ == "__main__":
    dp()
    gs = ((5, 5, 5, 3, 3),
          0,  # trash count of cards in deck
          ((3, 4), (4, 4), (4, 5)),  # active cards in deck
          4,  # trash count of cards in first player's hand
          ((3, 5),),  # first player's active cards
          5,  # trash count of cards in second player's hand
          ())  # second player's active cards
    print(gs)
    hb = InfiniteClueHanabi(None, None, [])
    print(hb.get_successors(gs, None))
