"""
This contains the basic logic for dealing with suits.
"""

import json
import requests


MAX_TIME = 12
SUIT_URL = "https://raw.githubusercontent.com/Hanabi-Live/hanabi-live/main/packages/data/src/json/suits.json"
SUIT_PATH = './data/assets/suits.json'


class SuitJSON(json.JSONEncoder):
    """Encodes JSON into a temporary object."""
    def default(self, o):
        return o.__dict__


class Suit:
    """Defines a class for variants."""
    # pylint: disable-next=redefined-builtin
    def __init__(self, name, id, abbreviation):
        self.name = name
        self.id = id
        self.abbreviation = abbreviation


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
    response = requests.get(SUIT_URL, timeout=MAX_TIME).json()
    with open(SUIT_PATH, 'w', encoding="utf8") as json_file:
        json.dump(response, json_file)
    print("Updated suits.")

def find_suit(suit_id):
    """Returns Suit object with given suit_id."""

    correct_suit = None
    for suit in SUIT_LIST:
        if suit.id == suit_id:
            correct_suit = suit

    if not correct_suit:
        update_suits()
        return find_suit(suit_id)

    return correct_suit

SUIT_LIST = get_suit_list()

print(SUIT_LIST[10])