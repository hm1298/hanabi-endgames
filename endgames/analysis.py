"""Analysis of multiple decks."""

# pylint: disable=C0301

import time
import pandas as pd
from tqdm import tqdm
from endgames.game.study import *  # pylint: disable=W0401,W0614
from endgames.game.util import create_hypo_url

def iterate_over_decks(num: int, variant_name: str="No Variant"):
    """Performs some execution on num decks.

    Args:
        num (int): number of decks to be generated
    """
    data, column_names = [], ["Seed", "Deck", "Infeasible", "Forced to Pace Zero", "Duration"]
    si = ShapeIdentifier()
    for seed in tqdm(range(1, num + 1)):
        seed = "egocentric" + str(seed)
        start = time.time()
        deck = Deck(variant_name)
        deck.shuffle(seed)
        inf, forced_pace_zero = deck.check_for_infeasibility(si)
        end = time.time()
        line = [seed, repr(deck), inf, forced_pace_zero, end - start]
        data.append(line)
    df = pd.DataFrame(data, columns=column_names)
    print((df["Infeasible"]).sum() / len(df["Infeasible"]))
    print(max(df["Duration"]), min(df["Duration"]))
    df.to_csv('egocentric_dark6_output.csv', index=False)

def print_urls(seeds):
    """Prints URLs of decks with seeds in list seeds."""
    result = []
    for seed in seeds:
        deck = Deck("No Variant")
        deck.shuffle(seed)
        result.append(create_hypo_url(deck))
        print(result[-1])
    return result

if __name__ == "__main__":
    iterate_over_decks(10 ** 6, "Black (6 Suits)")
    df1 = pd.read_csv("egocentric_dark6_output.csv")
    # df2 = pd.read_csv("dashing5_output.csv")
    # print("read")
    # d1 = df1.drop(columns=['Duration'])
    # d2 = df2.drop(columns=['Duration'])
    # print(sum(d1["Infeasible"]))
    # print(sum(d2["Infeasible"]))
    # difference = ~d1.eq(d2)
    # rows_with_differences = difference.any(axis=1)
    # differences = d2[rows_with_differences]
    # differences["URL"] = print_urls(differences["Seed"])
    # differences.to_csv("dashing4_5_differences.csv", index=False)
    print()
    print(df1.head())
    print("Percent infeasible:", (sum(df1["Infeasible"])) / len(df1["Infeasible"]))
    infeasible = df1[df1["Infeasible"]]
    feasible = df1[~df1["Infeasible"]]
    print("Avg feasible:", f"""{sum(feasible["Duration"]) / len(feasible["Duration"]):.6f}""", "seconds")
    print("Avg infeasible:", f"""{sum(infeasible["Duration"]) / len(infeasible["Duration"]):.6f}""", "seconds")
    print("Forced to pace zero:", f"""{100 * sum(feasible["Forced to Pace Zero"]) / len(feasible["Forced to Pace Zero"]):.3f}%""", "of 1p-winnable decks")
