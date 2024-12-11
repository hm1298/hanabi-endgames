"""
This contains the basic logic for dealing with suits.
"""

import json
import requests
import inflection
from endgames.game.io import *


MAX_TIME = 12
SUIT_URL = "https://raw.githubusercontent.com/Hanabi-Live/hanabi-live/main/packages/game/src/json/suits.json"
SUIT_PATH = './assets/suits.json'


class SuitJSON(json.JSONEncoder):
    """Encodes JSON into a temporary object."""
    def default(self, o):
        return o.__dict__


class Suit:
    """Defines a class for variants."""
    # pylint: disable-next=redefined-builtin
    def __init__(self, name, **kwargs):
        self.name = name
        self.abbreviation = None
        self.clue_colors = None
        self.display_name = None
        self.one_of_each = None
        self.pip = None
        self.prism = None
        self.reversed = None
        self.all_clue_colors = None
        self.all_clue_ranks = None
        self.no_clue_colors = None
        self.no_clue_ranks = None
        for key, value in kwargs.items():
            key = inflection.underscore(key)
            setattr(self, key, value)


def get_suit_list():
    """Returns list of Suit objects."""
    try:
        with open(SUIT_PATH, encoding="utf8") as json_file:
            json_list = json.load(json_file)
        suit_list = []
        for suit_data in json_list:
            suit_list.append(Suit(**suit_data))
        return suit_list
    except FileNotFoundError:
        update_suits()
        return get_suit_list()

def update_suits():
    """Pulls from github."""
    response = fetch_json(SUIT_URL)
    with open(SUIT_PATH, 'w', encoding="utf8") as json_file:
        json.dump(response, json_file)
    print("Updated suits.")

def find_suit(suit_name):
    """Returns Suit object with given suit_name."""

    correct_suit = None
    for suit in SUIT_LIST:
        if suit.name == suit_name:
            correct_suit = suit

    if not correct_suit:
        update_suits()
        return find_suit(suit_name)

    return correct_suit

SUIT_LIST = get_suit_list()
