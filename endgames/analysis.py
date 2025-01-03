"""Analysis of multiple decks."""

import time
import pandas as pd
from tqdm import tqdm
from endgames.game.util import *  # pylint: disable=W0401,W0614

def iterate_over_decks(num: int):
    """Performs some execution on num decks.

    Args:
        num (int): number of decks to be generated
    """
    data, column_names = [], ["Seed", "Deck", "Infeasible", "Duration"]
    si = ShapeIdentifier()
    for seed in tqdm(range(1, num + 1)):
        seed = "artichoke" + str(seed)
        start = time.time()
        deck = Deck("No Variant")
        deck.shuffle(seed)
        result = deck.check_for_infeasibility(si)
        end = time.time()
        line = [seed, repr(deck), result, end - start]
        data.append(line)
    df = pd.DataFrame(data, columns=column_names)
    print((df["Infeasible"]).sum() / len(df["Infeasible"]))
    print(max(df["Duration"]), min(df["Duration"]))
    df.to_csv('output.csv', index=False)

if __name__ == "__main__":
    iterate_over_decks(10 ** 6)
