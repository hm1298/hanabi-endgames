"""
This contains the basic logic for dealing with variants.
"""
# pylint: disable=invalid-name

import json
import requests


MAX_TIME = 12
VARIANT_URL = "https://raw.githubusercontent.com/Hanabi-Live/hanabi-live/main/packages/data/src/json/variants.json"
VARIANT_PATH = './data/assets/variants.json'


class VariantJSON(json.JSONEncoder):
    """Encodes JSON into a temporary object."""
    def default(self, o):
        return o.__dict__


class Variant:
    """Defines a class for variants."""
    # pylint: disable-next=redefined-builtin
    def __init__(self, id, name, suits, *args, **kwargs):
        self.id = id
        self.name = name
        self.suits = suits
        self.args = args
        self.kwargs = kwargs

    def get_max_score(self):
        """Returns the maximum possible score in this variant."""
        return 5 * len(self.suits)


def update_variants():
    """Pulls from github. To fold into io."""
    response = requests.get(VARIANT_URL, timeout=MAX_TIME).json()
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
