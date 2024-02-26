import sqlite3
import argparse
import matplotlib.pyplot as plt
from os import path
import json
import os
import numpy as np
from fuzzywuzzy import process
from fuzzywuzzy import fuzz

# ANSI escape codes for color
red = "\033[1;31m"
green = "\033[1;32m"
yellow = "\033[1;33m"
blue = "\033[1;34m"
cyan = "\033[1;36m"
purple = "\033[1;35m"
reset = "\033[1;0m"

root = path.dirname(__file__)


# Greedily find a path to create the target element
def find_path(cur, target, paths={}) -> dict[str, None | tuple[str, str]]:
    if target in paths:
        return paths

    depth_result = cur.execute(
        "SELECT depth FROM elements WHERE text = ?", (target,)
    ).fetchone()

    if depth_result is None:
        print(f"{red}Element not found in database:{reset} {target}")
        return

    depth = depth_result[0]

    if depth == 0:
        return {target: None}

    # Find the recipe that creates the target element with the lowest sum depth of inputs
    # Include only recipes where the inputs have a depth < output depth
    # This is to ensure that recipes have no cycles
    recipe = cur.execute(
        """
        SELECT input1, input2
        FROM recipes
        WHERE output = ?
          AND (SELECT depth FROM elements WHERE text = input1) < ?
          AND (SELECT depth FROM elements WHERE text = input2) < ?
        ORDER BY (SELECT depth FROM elements WHERE text = input1) + (SELECT depth FROM elements WHERE text = input2)
        LIMIT 1
      """,
        (target, depth, depth),
    ).fetchone()

    paths[target] = recipe

    if recipe[0] not in paths:
        paths = {**paths, **find_path(cur, recipe[0], paths)}

    if recipe[1] not in paths:
        paths = {**paths, **find_path(cur, recipe[1], paths)}

    return paths


def summarize_elements(cur, element):
    # Check if the element exists
    if (
        cur.execute(
            "SELECT COUNT(*) FROM elements WHERE text = ?", (element,)
        ).fetchone()[0]
        == 0
    ):
        # Find similar elements
        similar = cur.execute("SELECT text FROM elements").fetchall()
        similar = [s for s, in similar]

        # Use fuzzy matching to find similar elements
        similar = process.extract(
            element, similar, limit=5, scorer=fuzz.token_set_ratio
        )
        print(similar)
        similar = [s for s, _ in similar]

        print(f"{red}Element not found in database:{reset} {element}")
        print(f"{yellow}Did you mean one of these?{reset}")
        for s in similar:
            print(f"\t{s}")
        return

    # Create a directory for the element
    element_path = path.join(root, "analysis", "elements", element)
    if not path.exists(element_path):
        os.makedirs(element_path, exist_ok=True)

    # Write a markdown file with summary information about this element
    with open(path.join(element_path, f"summary.md"), "w") as f:
        # Get the row for the element
        _, emoji, discovered, depth, y, r, frq = cur.execute(
            "SELECT * FROM elements WHERE text = ?", (element,)
        ).fetchone()

        f.write(f"# {emoji} {element}\n\n")

        print(
            f"{green}Summary written to {reset}{path.join(element_path, 'summary.md')}"
        )

        # -----------------------------------------------------------
        # Details
        # -----------------------------------------------------------

        f.write(f"## Details\n\n")

        f.write(f"**First Discovery:** {'Yes' if discovered else 'No'}\n\n")

        f.write(f"**Depth:** {depth}\n\n")
        f.write(
            f"This element has been used {r} times to create {y} unique elements\n\n"
        )
        f.write(
            f"This element has been created by {frq} recipes not including the element itself\n\n"
        )
        f.write(f"---\n\n")

        # -----------------------------------------------------------
        # Possible Path
        # -----------------------------------------------------------

        # Write the path to the file
        f.write(f"## Possible Path\n\n")

        # Find the path to create the element
        paths = find_path(cur, element)

        depths = []

        # Get the depths of the elements in the path
        for e in paths.keys():
            depth = cur.execute(
                "SELECT depth FROM elements WHERE text = ?", (e,)
            ).fetchone()[0]

            depths.append((e, depth))

        # Sort the elements by depth
        depths.sort(key=lambda x: x[1])

        # Get the length of the longest element name for padding
        max_length = max([len(e) for e, _ in depths])

        f.write(f"```\n")
        for e, d in depths:
            if paths[e] is not None:
                a, b = paths[e]
                f.write(
                    f"{a:{max_length}} + {b:{max_length}} = {e:{max_length}} (depth {d})\n"
                )

        f.write(f"```\n")

        # -----------------------------------------------------------
        # Recipes
        # -----------------------------------------------------------

        # Get the recipes making the element

        recipes = cur.execute(
            "SELECT * FROM recipes WHERE output = ? AND input1 <> ? AND input2 <> ?",
            (element, element, element),
        ).fetchall()
        f.write(f"## Recipes Creating {element}\n\n")

        # Create a table of recipes
        f.write(f"| Input 1 | Input 2 | Output |\n")
        f.write(f"| ------- | ------- | ------ |\n")
        for recipe in recipes:
            f.write(f"| {recipe[0]} | {recipe[1]} | {recipe[2]} |\n")

        f.write(f"---\n\n")

        # Get the recipes that use the element and have a non-empty output
        recipes = cur.execute(
            """
            SELECT * FROM recipes
              WHERE (input1 = ? OR input2 = ?) AND output NOT IN ('Nothing', ?)
              ORDER BY output
            """,
            (
                element,
                element,
                element,
            ),
        ).fetchall()
        if len(recipes) > 0:
            f.write(f"## Recipes Using {element}\n\n")

            # Create a table of recipes
            f.write(f"| Input 1 | Input 2 | Output |\n")
            f.write(f"| ------- | ------- | ------ |\n")
            for recipe in recipes:
                if recipe[0] == element:
                    f.write(f"| {recipe[0]} | {recipe[1]} | {recipe[2]} |\n")
                else:
                    f.write(f"| {recipe[1]} | {recipe[0]} | {recipe[2]} |\n")
        else:
            f.write(f"**No recipes using {element}**\n\n")


def summarize(cur):
    num_elements = cur.execute("SELECT COUNT(*) FROM elements").fetchone()[0]
    num_recipes = cur.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
    num_discovered = cur.execute(
        "SELECT COUNT(*) FROM elements WHERE discovered = 1"
    ).fetchone()[0]
    num_unused = cur.execute(
        "SELECT COUNT(*) FROM elements WHERE recipe_count = 0"
    ).fetchone()[0]

    print(f"{purple}Database summary for {args.source}:{reset}")
    print(f"  {num_elements} elements")
    print(f"  {num_recipes} recipes")
    print(f"  {num_discovered} newly discovered elements")
    print(f"  {num_unused} elements with no uses")

    # Query the database for element counts by depth
    depth_counts = cur.execute(
        "SELECT depth, COUNT(*) FROM elements GROUP BY depth"
    ).fetchall()

    # Separate the depth and count values into separate lists
    depths = [row[0] for row in depth_counts]
    counts = [row[1] for row in depth_counts]

    # Create a bar graph
    plt.bar(depths, counts)
    plt.yscale("log")

    # Set labels and title
    plt.xlabel("Depth")
    plt.ylabel("Count")
    plt.title("Element Counts by Depth")

    # Save to analysis/element_counts.png
    plt.savefig(path.join(root, "analysis", "element_counts.png"))
    print(
        f"{green}Element counts by depth written to {reset}{path.join(root, 'analysis', 'element_counts.png')}"
    )
    print(f"{purple}Maximum depth:{reset} {max(depths)}")

    # Get all the yields and recipe counts
    yields_recipes = cur.execute("SELECT yield, recipe_count FROM elements").fetchall()

    # -----------------------------------------------------------
    # Yield percentage Distribution
    # -----------------------------------------------------------

    # Convert to percentages (add 1 to avoid division by 0)
    yields = [a / (b + 1) * 100 for a, b in yields_recipes]

    # Create a histogram of yields
    plt.clf()
    plt.hist(yields, bins=range(0, 101, 5))

    # Set labels and title
    plt.xlabel("Yield (Percentage)")
    plt.ylabel("Count")
    plt.title("Element Yield Distribution")

    # Save to analysis/yield_distribution.png
    plt.savefig(path.join(root, "analysis", "yield_distribution.png"))
    print(
        f"{green}Element yield distribution written to {reset}{path.join(root, 'analysis', 'yield_distribution.png')}"
    )

    # -----------------------------------------------------------
    # Recipe count Distribution
    # -----------------------------------------------------------

    # Create a histogram of recipe counts
    recipes = [b for _, b in yields_recipes]
    plt.clf()
    plt.hist(recipes, bins=np.linspace(0, max(recipes), 100))

    # Use log scale for x axis
    plt.yscale("log")

    # Set labels and title
    plt.xlabel("Number of Uses")
    plt.ylabel("Number of Elements")
    plt.title("Element Use Distribution")

    # Save to analysis/recipe_distribution.png
    plt.savefig(path.join(root, "analysis", "recipe_distribution.png"))
    print(
        f"{green}Element recipe distribution written to {reset}{path.join(root, 'analysis', 'recipe_distribution.png')}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze the infinite_craft database")

    parser.add_argument(
        "--source",
        help="The database file to analyze",
        type=str,
        default="infinite_craft.db",
    )

    parser.add_argument(
        "--summary",
        help="Print a summary of the database",
        action="store_true",
    )

    parser.add_argument(
        "--element",
        help="Calculate stats for a specific element",
        type=str,
        default=None,
    )

    parser.add_argument("--json", help="Output playable JSON", action="store_true")

    args = parser.parse_args()

    con = sqlite3.connect(args.source)
    cur = con.cursor()

    if args.json:
        # Only output elements
        elements = cur.execute("SELECT * FROM elements").fetchall()
        # sort by depth
        elements.sort(key=lambda x: x[3])
        elements = [
            {"text": e[0], "emoji": e[1], "discovered": bool(e[2])} for e in elements
        ]

        with open(path.join(root, "analysis", "elements.json"), "w") as f:
            json.dump({"elements": elements}, f, indent=2, ensure_ascii=False)
            print(
                f"{green}Elements written to {reset}{path.join(root, 'analysis', 'elements.json')}"
            )

    if args.summary:
        summarize(cur)

    if args.element is not None:
        summarize_elements(cur, args.element)

    con.close()
