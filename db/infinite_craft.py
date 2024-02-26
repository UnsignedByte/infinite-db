import requests
import json
import time
import random
import sqlite3
import logging
import sys
from utils import norm_recipe
import argparse
import datetime
from urllib.parse import quote_plus
import itertools
from queue import SimpleQueue
import numpy as np
from wordfreq import word_frequency
from wordfreq.preprocess import preprocess_text
from wordfreq.tokens import lossy_tokenize

# Set up logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
# SEt format for log messages
log_format = logging.Formatter("%(levelname)s:\t%(message)s")
# Set up a handler to write to the console
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setFormatter(log_format)
# Add the handler to the logger
log.addHandler(console_handler)

# ANSI escape codes for color
red = "\033[1;31m"
green = "\033[1;32m"
yellow = "\033[1;33m"
blue = "\033[1;34m"
cyan = "\033[1;36m"
purple = "\033[1;35m"
reset = "\033[1;0m"

# Color for warning, error, and info messages.
logging.addLevelName(
    logging.DEBUG, f"{blue}{logging.getLevelName(logging.DEBUG)}{reset}"
)
logging.addLevelName(
    logging.INFO, f"{green}{logging.getLevelName(logging.INFO)}{reset}"
)
logging.addLevelName(
    logging.WARNING, f"{yellow}{logging.getLevelName(logging.WARNING)}{reset}"
)
logging.addLevelName(
    logging.ERROR, f"{red}{logging.getLevelName(logging.ERROR)}{reset}"
)


def combine(a, b):
    s = requests.Session()
    s.headers.update(
        {
            "Referer": "https://neal.fun/infinite-craft/",
            "Origin": "https://neal.fun",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        }
    )
    for _ in range(10):
        try:
            # print(s.headers)
            r = s.get(
                f"https://neal.fun/api/infinite-craft/pair?first={quote_plus(a)}&second={quote_plus(b)}",
                timeout=10,
            )
            if r.status_code == 500:
                raise Exception("Internal Server Error")
            elif r.status_code == 429:
                raise TimeoutError("Rate Limited")
            elif r.status_code != 200:
                raise Exception(r.status_code)
            j = json.loads(r.content)
            if "emoji" not in j:
                print(a, b, j)
            return (j["result"], j["isNew"], j["emoji"])
        except TimeoutError as e:
            log.error(f"Failed to combine {a} and {b}: {e}")
            log.debug(f"Retrying in 1 Minute")
            time.sleep(60)
        except Exception as e:
            log.error(f"Failed to combine {a} and {b}: {e}")

    raise Exception("Failed to combine elements")


# Update the depth of a given element and propogate the change
def recursive_update_depth(cur, con, element, depth):
    # Get the old depth of the element
    # log.debug(f"Updating depth of {element} to {depth}")
    old_depth = cur.execute(
        "SELECT depth FROM elements WHERE text = ?", (element,)
    ).fetchone()[0]

    # If the old depth was smaller, return
    if old_depth <= depth:
        return

    # Update the depth of the element
    cur.execute("UPDATE elements SET depth = ? WHERE text = ?", (depth, element))

    # Find all recipes that use the element
    recipes = cur.execute(
        "SELECT * FROM recipes WHERE input1 = ? OR input2 = ?", (element, element)
    ).fetchall()

    # Propogate the change to the output elements
    for input1, input2, output in recipes:
        # Get the depth of the two input elements
        d1 = cur.execute(
            "SELECT depth FROM elements WHERE text = ?", (input1,)
        ).fetchone()[0]
        d2 = cur.execute(
            "SELECT depth FROM elements WHERE text = ?", (input2,)
        ).fetchone()[0]

        recursive_update_depth(cur, con, output, max(d1, d2) + 1)


def insert_combination(args, con, cur, a: str, b: str, timer_start=None) -> bool:
    if args.skip_numeric and (is_numeric(a) or is_numeric(b)):
        return

    if timer_start is None:
        timer_start = datetime.datetime.now()
    if a == "Nothing" or b == "Nothing":
        return False
    # Sort the elements
    elems = norm_recipe(a, b)

    # If the recipe has already been tried, skip it
    if (
        cur.execute(
            "SELECT COUNT(*) FROM recipes WHERE input1 = ? AND input2 = ?",
            (*elems,),
        ).fetchone()[0]
        > 0
    ):
        return False
    try:
        result, is_new, emoji = combine(a, b)
    except Exception as e:
        log.error(f"Failed to combine {a} and {b}: {e}")

        return False

    # Insert the new recipe into the database
    cur.execute(
        "INSERT OR IGNORE INTO recipes VALUES (?, ?, ?)",
        (*elems, result),
    )

    new_element = (
        cur.execute(
            "SELECT COUNT(*) FROM elements WHERE text = ?", (result,)
        ).fetchone()[0]
        == 0
    )

    # Get the depth of the input elements
    d1 = cur.execute("SELECT depth FROM elements WHERE text = ?", (a,)).fetchone()[0]
    d2 = cur.execute("SELECT depth FROM elements WHERE text = ?", (b,)).fetchone()[0]

    # Calculate the depth of the new element
    depth = max(d1, d2) + 1

    # Add 1 recipe count to both input elements
    cur.execute(
        "UPDATE elements SET recipe_count = recipe_count + 1 WHERE text = ? OR text = ?",
        (a, b),
    )

    # if the element is new:
    if new_element:
        # Add 1 yield to both input elements
        cur.execute(
            "UPDATE elements SET yield = yield + 1 WHERE text = ? OR text = ?",
            (a, b),
        )

        log.info(
            f"{purple + 'First Discovery' if is_new else green + 'New Element'}\n\t{a} + {b} = {emoji} {result}{reset}"
        )
        # Insert the new element into the database
        cur.execute(
            "INSERT OR IGNORE INTO elements VALUES (?, ?, ?, ?, 0, 0, ?)",
            (result, emoji, is_new, depth, a != result and b != result),
        )
    else:
        if a != result and b != result:
            # Freq
            cur.execute(
                "UPDATE elements SET freq = freq + 1 WHERE text = ?",
                (result,),
            )

        # Check if this element has been created before by the left and right elements
        # If it hasn't, update the yield respectively

        if (
            cur.execute(
                """
            SELECT COUNT(*) FROM recipes WHERE output = ? AND (input1 = ? OR input2 = ?)
                    """,
                (result, a, a),
            ).fetchone()[0]
            == 1
        ):
            cur.execute(
                "UPDATE elements SET yield = yield + 1 WHERE text = ?",
                (a,),
            )
        if (
            cur.execute(
                """
            SELECT COUNT(*) FROM recipes WHERE output = ? AND (input1 = ? OR input2 = ?)
                    """,
                (result, b, b),
            ).fetchone()[0]
            == 1
        ):
            cur.execute(
                "UPDATE elements SET yield = yield + 1 WHERE text = ?",
                (b,),
            )

        log.debug(f"{cyan}{a} + {b} = {emoji} {result}{reset}")
        recursive_update_depth(cur, con, result, depth)

    con.commit()

    # Wait
    time.sleep(
        max(
            0.0,
            random.uniform(0.15, 0.25)
            - (datetime.datetime.now() - timer_start).total_seconds(),
        )
    )

    return result != "Nothing"


def is_numeric(s: str) -> bool:
    return any(c.isdigit() for c in s)


def main():
    # ARguments

    parser = argparse.ArgumentParser(description="Crawl to discover new elements")

    parser.add_argument(
        "--bfs-start",
        type=int,
        default=0,
        help="The value to start the bfs at",
    )

    parser.add_argument(
        "--key",
        type=str,
        default="depth",
        help="The key to use for the algorithm",
    )

    parser.add_argument(
        "--algorithm",
        type=str,
        default="bfs",
        help="The algorithm to use to discover new elements",
    )

    parser.add_argument(
        "--batch",
        type=int,
        default=10,
        help="The number of elements batch for random algorithms",
    )

    parser.add_argument(
        "--search",
        type=str,
        nargs="+",
        help="The elements to start the search from",
        default=[],
    )

    parser.add_argument(
        "--search-exclude",
        type=str,
        nargs="+",
        help="The elements to exclude from the search",
        default=[],
    )

    parser.add_argument(
        "--min-length",
        type=int,
        default=0,
        help="The minimum length of the elements",
    )

    parser.add_argument(
        "--max-depth",
        type=int,
        default=10,
        help="The maximum depth of the elements",
    )

    parser.add_argument(
        "--skip-numeric",
        action="store_true",
        help="Skip numeric elements (Elements with digits)",
    )

    parser.add_argument(
        "--only-word", action="store_true", help="Only use single word elements"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="glove-twitter-25",
        help="The word2vec model to use for the search algorithm",
    )

    parser.add_argument(
        "--invert",
        action="store_true",
        help="Invert the weights for the weighted random algorithm",
    )

    args = parser.parse_args()

    if args.batch < 1:
        log.error("Invalid arguments")
        exit(1)

    con = sqlite3.connect("infinite_craft.db")
    cur = con.cursor()

    # Insert default elements if they don't exist
    default = [
        ("Water", "💧"),
        ("Fire", "🔥"),
        ("Wind", "🌬️"),
        ("Earth", "🌍"),
    ]

    for element in default:
        cur.execute(
            "INSERT OR IGNORE INTO elements VALUES (?, ?, 0, 0, 0, 0, 0)",
            element,
        )

    log.info(f"Starting crawler with {args.algorithm} algorithm")

    try:
        if args.algorithm == "bfs":
            idx = args.bfs_start
            while True:
                # Get all elements with the current idx
                delements = cur.execute(
                    f"SELECT text FROM elements WHERE {args.key} = ?", (idx,)
                ).fetchall()

                # Get all elements with <= current idx
                lelements = cur.execute(
                    f"SELECT text FROM elements WHERE {args.key} <= ?", (idx,)
                ).fetchall()

                log.info(
                    f"Crawling {args.key} {idx}: {len(delements)} X {len(lelements)} = {len(delements) * len(lelements)} recipes to try"
                )

                idx += 1

                count = 0

                # Loop through all possible combinations of elements
                for (a,) in delements:
                    for (b,) in lelements:
                        count += 1

                        if count % 1000 == 0:
                            log.debug(
                                f"Progress: {count}/{len(delements) * len(lelements)} ({count / (len(delements) * len(lelements)) * 100:.2f}%)"
                            )

                        insert_combination(args, con, cur, a, b)
        elif args.algorithm == "random":
            while True:
                a_s = cur.execute(
                    "SELECT text FROM elements ORDER BY RANDOM() LIMIT ?",
                    (args.batch,),
                ).fetchall()
                b_s = cur.execute(
                    "SELECT text FROM elements ORDER BY RANDOM() LIMIT ?",
                    (args.batch,),
                ).fetchall()

                a_s = [x for x, in a_s]
                b_s = [x for x, in b_s]

                for a, b in zip(a_s, b_s):
                    insert_combination(args, con, cur, a, b)
        elif args.algorithm in ["max-yield", "min-uses", "max-freq"]:
            while True:
                t = datetime.datetime.now()
                # Get all the elements in random order
                elements = cur.execute(
                    'SELECT text FROM elements WHERE text <> "Nothing" ORDER BY RANDOM()'
                ).fetchall()
                elements = [x for x, in elements]

                nelements = len(elements)

                if args.algorithm == "max-yield":
                    # Choose the element with the highest yield
                    _a = cur.execute(
                        """
                        SELECT text, yield, recipe_count FROM elements
                            WHERE text <> "Nothing"
                                AND recipe_count < ?
                            ORDER BY (CAST(yield as REAL) / (recipe_count + 1)) DESC LIMIT ?
                        """,
                        (nelements, args.batch),
                    ).fetchall()
                elif args.algorithm == "min-uses":
                    # Get all the elements with the lowest recipe count
                    _a = cur.execute(
                        """
                        SELECT text, yield, recipe_count FROM elements
                            WHERE text <> "Nothing"
                                AND recipe_count < ?
                                AND recipe_count = (SELECT MIN(recipe_count) FROM elements WHERE recipe_count < ?)
                        """,
                        (
                            nelements,
                            nelements,
                        ),
                    ).fetchall()
                    log.info(
                        f"Pulled {len(_a)} elements with a recipe count of {_a[0][2]}"
                    )
                elif args.algorithm == "max-freq":
                    _a = cur.execute(
                        """
                        SELECT text, freq, recipe_count FROM elements
                            WHERE text <> "Nothing"
                                AND recipe_count < ?
                            ORDER BY freq DESC LIMIT ?
                        """,
                        (nelements, args.batch),
                    ).fetchall()

                for a, y, r in _a:
                    if args.algorithm == "max-yield":
                        log.debug(
                            f"Max Yield {y}/{r+1} = {y/(r+1):.2f} element {yellow}{a}{reset}"
                        )
                    elif args.algorithm == "min-uses":
                        log.debug(f"Min Uses {r} element {yellow}{a}{reset}")
                    elif args.algorithm == "max-freq":
                        log.debug(f"Max Freq {y} element {yellow}{a}{reset}")

                    _b = []
                    if r / nelements < 0.7:
                        # Decently high chance of choosing a random element that has not been tried
                        # Just choose a random element until it works

                        for _ in range(args.batch * 10):
                            bt = random.choice(elements)

                            if (
                                cur.execute(
                                    "SELECT COUNT(*) FROM recipes WHERE input1 = ? AND input2 = ?",
                                    norm_recipe(a, bt),
                                ).fetchone()[0]
                                == 0
                            ):
                                _b.append(bt)
                                if len(_b) == args.batch:
                                    break

                    else:
                        # Get all the recipes that use the element
                        recipes = cur.execute(
                            "SELECT input1, input2 FROM recipes WHERE input1 = ? OR input2 = ?",
                            (a, a),
                        ).fetchall()

                        # Get the other input for the recipe
                        other_elems = set(y if x == a else x for x, y in recipes)

                        elements = set(elements)

                        # Get the elements that are not in the recipes
                        other_elems = list(elements - other_elems)

                        if len(other_elems) < args.batch:
                            _b = other_elems
                        else:
                            # Choose a random element from the set
                            _b = random.sample(other_elems, args.batch)

                    for b in _b:
                        insert_combination(args, con, cur, a, b, t)
        elif args.algorithm == "search":
            # Starting pairs to search from
            queue = SimpleQueue()
            search = set(args.search)
            search_exclude = set(args.search_exclude)

            if len(search) == 0:
                log.error(
                    "No search elements provided. Use --search <element> <element> ..."
                )
                exit(1)

            # Make sure the elements exist
            for element in search:
                if (
                    cur.execute(
                        "SELECT COUNT(*) FROM elements WHERE text = ?", (element,)
                    ).fetchone()[0]
                    == 0
                ):
                    log.error(f"Element {element} does not exist")
                    exit(1)

            for x in itertools.combinations_with_replacement(search, 2):
                queue.put(x)

            while not queue.empty():
                a, b = queue.get()
                insert_combination(args, con, cur, a, b)

                # Get result if it exists and skip otherwise
                res = cur.execute(
                    "SELECT output FROM recipes WHERE input1 = ? AND input2 = ?",
                    norm_recipe(a, b),
                ).fetchone()

                if res is None:
                    continue

                res = res[0]

                if res in search or res in search_exclude or res == "Nothing":
                    continue

                search.add(res)

                for x in search:
                    queue.put((res, x))
        elif args.algorithm == "shortest":
            # Sort by shortest words
            while True:
                # Get all elements
                elements = cur.execute(
                    """
                    SELECT text FROM elements
                        WHERE text <> 'Nothing'
                            AND DEPTH <= ?
                        ORDER BY RANDOM() LIMIT ?
                    """,
                    (args.max_depth, args.batch),
                ).fetchall()
                elements = [x for x, in elements]
                # Get number of elements

                nelements = cur.execute(
                    "SELECT COUNT(*) FROM elements WHERE text <> 'Nothing'"
                ).fetchone()[0]

                # Filters out elements that have been fully explored
                a_s = cur.execute(
                    """
                    SELECT text FROM elements
                        WHERE recipe_count < ?
                            AND text <> 'Nothing'
                            AND LENGTH(text) >= ?
                            AND depth <= ?
                        ORDER BY LENGTH(text)
                    """,
                    (nelements, args.min_length, args.max_depth),
                ).fetchall()
                a_s = [x for x, in a_s]

                # Get all elements

                for a in a_s:
                    for b in elements:
                        insert_combination(args, con, cur, a, b)
        elif args.algorithm == "find":
            # Remove the search elements from the search set

            search = set(args.search)

            import gensim.downloader

            # Load the model
            model = gensim.downloader.load(args.model)

            def similarity(a, b):
                # Split the elements into words
                a = a.lower().split()
                b = b.lower().split()

                def sim_single(x, y):
                    try:
                        return model.similarity(x, y)
                    except KeyError:
                        return 0

                # Get the l2 norm similarity of all the pairs of words
                return np.linalg.norm([max(sim_single(x, y) for y in b) for x in a]) / (
                    len(a) * len(b)
                )

            batch = args.batch
            while True:
                # Get every element
                elements = cur.execute(
                    """
                    SELECT text FROM elements
                        WHERE text <> "Nothing"
                    """
                ).fetchall()
                elements = [x for x, in elements if x not in search]

                # Get the similarity of each element in the search to every other element
                a = [(e, max(similarity(e, b) for b in search)) for e in elements]
                # Sort the elements by similarity descending
                a.sort(key=lambda x: x[1], reverse=True)

                # Get the top batch elements
                a = a[:batch]
                a = [x for x, _ in a]

                log.debug(f"Searching for {", ".join(search)}")
                log.debug(f"Top {batch} elements: \n\t{", ".join(a)}")

                any_found = False

                # Loop through all pairs of elements
                for x, y in itertools.combinations_with_replacement(a, 2):
                    any_found = insert_combination(args, con, cur, x, y) or any_found

                if not any_found:
                    log.info("Search reached a dead end, increasing batch size")
                    batch += max(1, args.batch // 2)
        elif args.algorithm == "weighted-random":
            # Weighted by word commonality
            while True:
                # Get every element
                data = cur.execute(
                    """
                    SELECT text, depth, yield, recipe_count, freq FROM elements
                        WHERE text <> "Nothing"
                        ORDER BY depth ASC
                    """
                ).fetchall()

                l = ["depth", "yield", "recipe_count", "freq"]
                elements = [x[0] for x in data]

                log.debug(f"Weighting by {args.key}")

                if args.key == "commonality":
                    new_elements = []

                    normalized_words = set()
                    for element in elements:
                        normalized = tuple(lossy_tokenize(element, "en"))
                        if normalized in normalized_words:
                            continue
                        if args.only_word and len(normalized) > 1:
                            continue
                        normalized_words.add(normalized)
                        # Keep only one element per normalized word, ordered by depth
                        new_elements.append(element)

                    elements = new_elements

                    probabilities = [
                        word_frequency(x, "en", wordlist="large")
                        / max(1, len(lossy_tokenize(x, "en"))) ** 2
                        for x in elements
                    ]
                elif args.key in l:
                    if args.key == "yield":
                        probabilities = [(x[2] / (x[3] + 1)) ** 4 for x in data]
                    else:
                        index = l.index(args.key)
                        probabilities = [x[index + 1] for x in data]
                else:
                    log.error(f"Invalid key {args.key}")
                    exit(1)

                probabilities = np.array(probabilities)
                probabilities = probabilities / probabilities.sum()
                # Invert the probabilities if needed
                if args.invert:
                    probabilities = 1 / (probabilities + 1e-6 / len(probabilities))
                    probabilities = probabilities / probabilities.sum()

                # print words and probabilities sorted
                with open("tmp.txt", "w") as f:
                    f.write(
                        "\n".join(
                            f"{x}: {p:.4e}"
                            for x, p in sorted(
                                zip(elements, probabilities),
                                key=lambda x: x[1],
                                reverse=True,
                            )
                        )
                        + "\n"
                    )

                # choose random elements
                a = np.random.choice(
                    elements, size=args.batch, p=probabilities
                ).tolist()

                b = np.random.choice(
                    elements, size=args.batch, p=probabilities
                ).tolist()

                # Loop through all pairs of elements
                for x, y in zip(a, b):
                    insert_combination(args, con, cur, x, y)
        elif args.algorithm == "explore":
            # Get all elements
            elements = cur.execute(
                f"""
                SELECT text FROM elements
                    WHERE text <> "Nothing"
                    ORDER BY {args.key}
                """
            ).fetchall()

            elements = [x for x, in elements]

            search = set(args.search)

            # Make sure the elements exist
            for element in search:
                if (
                    cur.execute(
                        "SELECT COUNT(*) FROM elements WHERE text = ?", (element,)
                    ).fetchone()[0]
                    == 0
                ):
                    log.error(f"Element {element} does not exist")
                    exit(1)

            for x in elements:
                for y in search:
                    insert_combination(args, con, cur, y, x)

    except KeyboardInterrupt:
        log.info("Exiting...")

        con.close()
        exit(0)


if __name__ == "__main__":
    main()
