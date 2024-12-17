"""Tests. Run with 'pytest --durations=0' for times."""

import pytest
from endgames.game import io, util

TESTS = io.read_printout("assets/rama_old_decks.txt")
ANSWERS = io.read_printout("assets/rama_old_decks_ans.txt")

@pytest.mark.parametrize("raw_deck, answer", list(zip(TESTS, ANSWERS)))
def test_study(raw_deck, answer):
    """Verifies infeasibility checks on 31 test decks

    Args:
        raw_deck (list): list of strings representing cards
        answer (list): 1-element list of string "True" or "False"
    """
    deck = util.create_bespoke_deck(raw_deck)
    result = deck.check_for_infeasibility()
    assert result is True or result is False
    assert str(result) == answer[0]
