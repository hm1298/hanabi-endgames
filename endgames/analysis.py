"""Analysis of multiple decks."""

import time
import pandas as pd
from tqdm import tqdm
from endgames.game.study import *  # pylint: disable=W0401,W0614

def iterate_over_decks(num: int):
    """Performs some execution on num decks.

    Args:
        num (int): number of decks to be generated
    """
    data, column_names = [], ["Seed", "Deck", "Infeasible", "Forced to Pace Zero", "Duration"]
    si = ShapeIdentifier()
    for seed in tqdm(range(1, num + 1)):
        seed = "dashing" + str(seed)
        start = time.time()
        deck = Deck("No Variant")
        deck.shuffle(seed)
        inf, forced_pace_zero = deck.check_for_infeasibility(si)
        end = time.time()
        line = [seed, repr(deck), inf, forced_pace_zero, end - start]
        data.append(line)
    df = pd.DataFrame(data, columns=column_names)
    print((df["Infeasible"]).sum() / len(df["Infeasible"]))
    print(max(df["Duration"]), min(df["Duration"]))
    df.to_csv('dashing3_output.csv', index=False)

if __name__ == "__main__":
    iterate_over_decks(10 ** 6)
    df = pd.read_csv("dashing2_output.csv")
    df2 = pd.read_csv("dashing3_output.csv")
    print("read")
    d1 = df.drop(columns=['Duration'])
    d2 = df2.drop(columns=['Duration'])
    print(sum(d1["Infeasible"]))
    print(sum(d2["Infeasible"]))
    difference = ~d1.eq(d2)
    rows_with_differences = difference.any(axis=1)
    d2[rows_with_differences].to_csv("dashing2_3_differences.csv", index=False)
    print()
    print(df.head())
    print((df["Infeasible"]).sum() / len(df["Infeasible"]))
    print(max(df["Duration"]), min(df["Duration"]))
    print([type(x) for x in df["Infeasible"].unique()])
    print(max(df[df["Infeasible"]]["Duration"]))
    infeasible = df[df["Infeasible"]]
    feasible = df[~df["Infeasible"]]
    print("Avg feasible:", f"""{sum(feasible["Duration"]) / len(feasible["Duration"]):.6f}""", "seconds")
    print("Avg infeasible:", f"""{sum(infeasible["Duration"]) / len(infeasible["Duration"]):.6f}""", "seconds")
    print("Forced to pace zero:", f"""{100 * sum(feasible["Forced to Pace Zero"]) / len(feasible["Forced to Pace Zero"]):.3f}%""", "of 1p-winnable decks")
