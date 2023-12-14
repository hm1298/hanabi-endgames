"""Tools to anaylze Hanabi Games"""
class GameState:
    """
    Gamestate is a class to handle what an ongoing game of hanabi looks like on a specific turn.
    It is initialized with JSON data and the turn number, then
    contains methods to provide information about the game on that turn.
    """

    def __init__(self, data, turn):

        # Game/Seed/Variant info

        self.data = data
        self.deck = data["deck"]

        for i, card in enumerate(self.deck):
            card["order"] = i

        self.players = data["players"]
        self.actions = data["actions"]
        self.suit_count = 1 + max([card["suitIndex"] for card in self.deck])
        try:
            self.variant = data["options"]["variant"]
        except KeyError:
            self.variant = "No Variant"
        self.player_count = len(self.players)
        self.hand_size = _get_hand_size(self.data)

        # Turn-dependent game info

        self.clue_token_count = 8
        self.turn = 0
        self.discard_pile = []
        self.play_stacks = [[] for _ in range(self.suit_count)]
        self.score = 0
        self.hands = _get_starting_hands(
            self.deck, self.player_count, self.hand_size)
        self.current_player_index = 0
        self.strike_count = 0
        self.draw_pile_size = len(self.deck) - \
            self.player_count * self.hand_size

        # progress to current turn
        for i in range(turn):
            self.implement_action(self.actions[i])

    # Helper for plays, bombs, and discards

    def _remove_from_hand(self, player_index, order):

        found = False
        for i, card in enumerate(self.hands[player_index]):
            if card["order"] == order:
                found = True
                found_slot = i
                real_card = card
                break

        if not found:
            print(f'could not find card {order}!')
            return self.deck[order]

        remains = self.hands[player_index][:found_slot] + \
            self.hands[player_index][found_slot + 1:]
        self.hands[player_index] = remains
        return real_card

    def _draw_card(self):
        if self.draw_pile_size == 0:
            return
        card = self.deck[- self.draw_pile_size]
        self.hands[self.current_player_index] = [
            card] + self.hands[self.current_player_index]
        self.draw_pile_size -= 1

    def _get_type(self, action):
        i = action["type"]
        if i == 3:
            return "rank"
        if i == 2:
            return "color"
        if i == 1:
            return "discard"
        if i == 4 or i == 5:
            return "vtk"
        card = self.deck[action["target"]]
        if len(self.play_stacks[card["suitIndex"]]) == card["rank"] - 1:
            return "play"
        return "bomb"

    def _increment_clue_count(self):
        if self.variant[0:12] == "Clue starved":
            inc = 0.5
        else:
            inc = 1
        self.clue_token_count = min(8, self.clue_token_count + inc)


    def implement_action(self, action):
        """Increments the gamestate for when an action plays"""
        action_type = self._get_type(action)

        if action_type == "rank":
            self.clue_token_count -= 1

        elif action_type == "color":
            self.clue_token_count -= 1

        elif action_type == "discard":
            card = self._remove_from_hand(
                self.current_player_index, action["target"])
            self._increment_clue_count()
            self.discard_pile.append(card)
            self._draw_card()

        elif action_type == "play":
            card = self._remove_from_hand(
                self.current_player_index, action["target"])
            self.play_stacks[card["suitIndex"]].append(card)
            self._draw_card()
            self.score += 1

            if self.deck[action["target"]]["rank"] == 5:
                self._increment_clue_count()

        elif action_type == "bomb":
            card = self._remove_from_hand(
                self.current_player_index, action["target"])
            self.discard_pile.append(card)
            self.strike_count += 1
            self._draw_card()
        if action_type != "vtk":
            self.current_player_index = (
                self.current_player_index + 1) % self.player_count
            self.turn += 1


    def review_turn(self, turn_count):
        """Replays a state at a prior turn"""
        if turn_count >= len(self.actions) or turn_count < 0:
            return False

        return GameState(self.data, turn_count)

    # print

    def __repr__(self):
        hands_repr = []
        for hand in self.hands:
            hand_repr = []
            for card in hand:
                rank = card["rank"]
                suit = "RYGBKM"[card["suitIndex"]]
                hand_repr.append(suit + str(rank))
            hands_repr.append(hand_repr)

        return (
            f"turn: {self.turn}\n" +
            f"hands: {hands_repr}\n"
        )


def _get_hand_size(data):
    player_count = len(data["players"])
    if player_count < 4:
        hand_size = 5
    elif player_count < 6:
        hand_size = 4
    else:
        hand_size = 3

    if "options" in data:
        if "oneExtraCard" in data["options"]:
            hand_size += 1
        if "oneLessCard" in data["options"]:
            hand_size -= 1
    return hand_size


def _get_starting_hands(deck, player_count, hand_size):
    hands = []
    pile = iter(deck)
    for _ in range(player_count):
        hand = []
        for __ in range(hand_size):
            hand.append(next(pile))
        hands.append([card for card in reversed(hand)])
    return hands
