import random
import sqlite3
from utils import norm_recipe, insert_combination, setup_logging, read_group
import argparse
import itertools
import numpy as np
from wordfreq import word_frequency
from wordfreq.tokens import lossy_tokenize
from os import path
import copy
import multiprocessing

# ANSI escape codes for color
red = "\033[1;31m"
green = "\033[1;32m"
yellow = "\033[1;33m"
blue = "\033[1;34m"
cyan = "\033[1;36m"
purple = "\033[1;35m"
reset = "\033[1;0m"


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
        "--sort",
        type=str,
        default="text ASC",
        help="The sort order for the elements",
    )

    parser.add_argument(
        "--algorithm",
        "-a",
        type=str,
        default="bfs",
        help="The algorithm to use to discover new elements",
    )

    parser.add_argument(
        "--batch",
        type=int,
        default=100,
        help="The number of elements batch for random algorithms",
    )

    parser.add_argument(
        "--search",
        "-s",
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

    parser.add_argument(
        "--groups",
        "-g",
        type=str,
        nargs="+",
        help="The groups to use for the search algorithm",
        default=[],
    )

    args = parser.parse_args()

    search = set.union(set(args.search), *[read_group(x) for x in args.groups])

    log = setup_logging()

    if args.batch < 1:
        log.error("Invalid arguments")
        exit(1)

    root = path.dirname(__file__)

    con = sqlite3.connect(path.join(root, "infinite_craft.db"), timeout=120)
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
        with multiprocessing.Pool(20) as pool:
            if args.algorithm == "bfs":
                idx = args.bfs_start
                while True:
                    # Get all elements with the current idx
                    delements = cur.execute(
                        f"SELECT text FROM elements WHERE {args.key} = ? ORDER BY {args.sort}",
                        (idx,),
                    ).fetchall()

                    # Get all elements with <= current idx
                    lelements = cur.execute(
                        f"SELECT text FROM elements WHERE {args.key} <= ? ORDER BY {args.sort}",
                        (idx,),
                    ).fetchall()

                    log.info(
                        f"Crawling {args.key} {idx}: {len(delements)} X {len(lelements)} = {len(delements) * len(lelements)} recipes to try"
                    )

                    idx += 1

                    count = 0

                    # Loop through all possible combinations of elements
                    for (a,) in delements:
                        batch = []
                        for (b,) in lelements:
                            count += 1

                            if count % 1000 == 0:
                                log.debug(
                                    f"Progress: {count}/{len(delements) * len(lelements)} ({count / (len(delements) * len(lelements)) * 100:.2f}%)"
                                )

                            if count % args.batch == 0:
                                insert_combination(log, pool, args, con, cur, batch)
                                batch = []

                            batch.append((a, b))
            elif args.algorithm == "random":
                while True:
                    a_s = cur.execute(
                        "SELECT text FROM elements ORDER BY RANDOM() LIMIT ?",
                        (args.batch,),
                    ).fetchall()

                    a_s = [x for x, in a_s]

                    insert_combination(
                        log,
                        pool,
                        args,
                        con,
                        cur,
                        itertools.combinations_with_replacement(a_s, 2),
                    )
            elif args.algorithm in ["max-yield", "min-uses", "max-freq"]:
                while True:
                    # Get all the elements in random order
                    elements = cur.execute(
                        "SELECT text FROM elements WHERE text <> 'Nothing' ORDER BY RANDOM()"
                    ).fetchall()
                    elements = [x for x, in elements]

                    nelements = len(elements)

                    if args.algorithm == "max-yield":
                        # Choose the element with the highest yield
                        _a = cur.execute(
                            """
                            SELECT text, yield, recipe_count FROM elements
                                WHERE text <> 'Nothing'
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
                                WHERE text <> 'Nothing'
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
                                WHERE text <> 'Nothing'
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

                        insert_combination(
                            log, pool, args, con, cur, [(a, b) for b in _b]
                        )

            elif args.algorithm == "search":
                # Starting pairs to search from
                search_exclude = set(args.search_exclude)

                if len(search) == 0:
                    log.error(
                        "No search elements provided. Use --search <element> <element> ..."
                    )
                    exit(1)

                search_new = set()
                search_missing = set()

                # Make sure the elements exist
                for element in search:
                    if (
                        cur.execute(
                            "SELECT COUNT(*) FROM elements WHERE text = ?", (element,)
                        ).fetchone()[0]
                        == 0
                    ):
                        log.info(f"{element} does not exist, adding to goals.")
                        search_missing.add(element)
                    else:
                        search_new.add(element)
                search = search_new
                initial_search = copy.deepcopy(search)

                queue = list(itertools.combinations_with_replacement(initial_search, 2))

                while len(queue) > 0:
                    # Filter out the recipes that have already been tried
                    # nqueue = []
                    # changed = True
                    # while changed:
                    #     changed = False
                    #     for a, b in queue:
                    #         sel = cur.execute(
                    #             "SELECT output FROM recipes WHERE input1 = ? AND input2 = ?",
                    #             norm_recipe(a, b),
                    #         ).fetchone()
                    #         if sel is not None:
                    #             if sel[0] in search_exclude:
                    #                 continue
                    #             search.add(sel[0])
                    #             changed = True
                    #             for x in search:
                    #                 nqueue.append((sel[0], x))
                    #         else:
                    #             nqueue.append((a, b))

                    #     queue = nqueue

                    log.info(f"Queue length: {len(queue)}")
                    batch = queue[: args.batch]
                    insert_combination(log, pool, args, con, cur, batch)

                    nqueue = queue[args.batch :]
                    reset_search = False

                    for a, b in batch:
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

                        if res in search_missing:
                            # We found an element that was missing
                            search_missing.remove(res)
                            initial_search.add(res)
                            log.info(f"Found missing element {res}, adding to search")
                            reset_search = True

                        search.add(res)

                        for x in search:
                            nqueue.append((res, x))

                    if reset_search:
                        log.info(
                            f"Resetting search with {len(initial_search)} initial elements"
                        )
                        queue = list(
                            itertools.combinations_with_replacement(initial_search, 2)
                        )
                    else:
                        queue = nqueue
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

                    insert_combination(
                        log,
                        pool,
                        args,
                        con,
                        cur,
                        [(a, b) for a in a_s for b in elements],
                    )

            elif args.algorithm == "find":
                # Remove the search elements from the search set

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
                    return np.linalg.norm(
                        [max(sim_single(x, y) for y in b) for x in a]
                    ) / (len(a) * len(b))

                batch = args.batch
                while True:
                    # Get every element
                    elements = cur.execute(
                        """
                        SELECT text FROM elements
                            WHERE text <> 'Nothing'
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

                    # Loop through all pairs of elements
                    any_found = insert_combination(
                        log,
                        pool,
                        args,
                        con,
                        cur,
                        itertools.combinations_with_replacement(a, 2),
                    )

                    if len(set(any_found) - search) == 0:
                        log.info("Search reached a dead end, increasing batch size")
                        batch += max(1, args.batch // 2)
            elif args.algorithm == "weighted-random":
                # Weighted by word commonality
                while True:
                    # Get every element
                    data = cur.execute(
                        """
                        SELECT text, depth, yield, recipe_count, freq FROM elements
                            WHERE text <> 'Nothing'
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
                    with open(path.join(root, "tmp.txt"), "w") as f:
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
                        elements, size=args.batch, p=probabilities, replace=False
                    ).tolist()

                    # Loop through all pairs of elements
                    insert_combination(
                        log,
                        pool,
                        args,
                        con,
                        cur,
                        itertools.combinations_with_replacement(a, 2),
                    )
            elif args.algorithm == "explore":
                # Get all elements
                elements = cur.execute(
                    f"""
                    SELECT text FROM elements
                        WHERE text <> 'Nothing'
                        ORDER BY {args.key}
                    """
                ).fetchall()

                elements = [x for x, in elements]

                search_new = set()

                # Make sure the elements exist
                for element in search:
                    if (
                        cur.execute(
                            "SELECT COUNT(*) FROM elements WHERE text = ?", (element,)
                        ).fetchone()[0]
                        == 0
                    ):
                        log.warn(f"Element {element} does not exist, skipping...")
                    else:
                        search_new.add(element)
                search = search_new

                batch = []
                count = 0
                for b in elements:
                    count += 1

                    if count % args.batch == 0:
                        insert_combination(log, pool, args, con, cur, batch)
                        batch = []
                    batch += [(a, b) for a in search]

    except KeyboardInterrupt:
        log.info("Exiting...")

        con.close()
        exit(0)


if __name__ == "__main__":
    main()
