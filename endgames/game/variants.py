"""
This contains the basic logic for dealing with variants.
"""
# pylint: disable=invalid-name

import json
import inflection
from endgames.game.io import fetch_json
from endgames.game.suits import find_suit


MAX_TIME = 12
VARIANT_URL = "https://raw.githubusercontent.com/Hanabi-Live/hanabi-live/main/packages/game/src/json/variants.json"
VARIANT_PATH = './assets/variants.json'


class VariantJSON(json.JSONEncoder):
    """Encodes JSON into a temporary object."""
    def default(self, o):
        return o.__dict__


class Variant:
    """Defines a class for variants."""
    # pylint: disable-next=redefined-builtin
    def __init__(self, id, name, suits, **kwargs):
        self.name = name
        self.id = id
        self.suit_names = suits
        self.suits = []
        for suit in suits:
            if "Reversed" in suit:
                suit = suit[:-9]
            self.suits.append(find_suit(suit))

        self.clue_colors = None
        self.clue_ranks = [1, 2, 3, 4, 5]
        self.color_clues_touch_nothing = None
        self.rank_clues_touch_nothing = None
        self.special_rank = None
        self.special_all_clue_colors = None
        self.special_all_clue_ranks = None
        self.special_no_clue_colors = None
        self.special_no_clue_ranks = None
        self.special_deceptive = None
        self.odds_and_evens = None
        self.funnels = None
        self.chimneys = None
        self.up_or_down = None
        self.critical_fours = None
        self.sudoku = None
        self.critical_rank = None
        self.stack_size = None

        for key, value in kwargs.items():
            key = inflection.underscore(key)
            setattr(self, key, value)

    def get_max_score(self):
        """Returns the maximum possible score in this variant."""
        num_suits = len(self.suits)
        try:
            stack_size = self.stack_size
        except AttributeError:
            stack_size = None
        try:
            if stack_size is None and self.sudoku:
                stack_size = num_suits
        except AttributeError:
            stack_size = 5  # default value

        return stack_size * num_suits


def update_variants():
    """Pulls from github. To fold into io."""
    response = fetch_json(VARIANT_URL)
    with open(VARIANT_PATH, 'w', encoding="utf8") as json_file:
        json.dump(response, json_file)
    print("Updated variants.")

def get_variant_dict():
    """Returns list of Variant objects."""
    try:
        with open(VARIANT_PATH, encoding="utf8") as json_file:
            json_list = json.load(json_file)
        variant_dict = {}
        for variant_data in json_list:
            variant_dict[variant_data["id"]] = Variant(**variant_data)
        return variant_dict
    except FileNotFoundError:
        update_variants()
        return get_variant_dict()

def get_variant_names_dict():
    """Returns list of Variant objects."""
    try:
        with open(VARIANT_PATH, encoding="utf8") as json_file:
            json_list = json.load(json_file)
        variant_dict = {}
        for variant_data in json_list:
            variant_dict[variant_data["name"]] = Variant(**variant_data)
        return variant_dict
    except FileNotFoundError:
        update_variants()
        return get_variant_names_dict()

def find_variant(variant_id):
    """Returns Variant object with given variant_id."""

    if variant_id in VARIANT_DICT:
        correct_variant = VARIANT_DICT[variant_id]
    else:
        update_variants()
        # throws an Error if variant_id does not exist
        return VARIANT_DICT[variant_id]

    return correct_variant

def find_variant_from_name(variant_name):
    """Returns Variant object with given variant_name."""

    if variant_name in VARIANT_NAMES_DICT:
        correct_variant = VARIANT_NAMES_DICT[variant_name]
    else:
        update_variants()
        # throws an Error if variant_name does not exist
        return VARIANT_NAMES_DICT[variant_name]

    return correct_variant

VARIANT_DICT = get_variant_dict()
VARIANT_NAMES_DICT = get_variant_names_dict()
