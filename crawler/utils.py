import requests
import time
import random
from urllib.parse import quote_plus
import json
import logging
import sys

# ANSI escape codes for color
red = "\033[1;31m"
green = "\033[1;32m"
yellow = "\033[1;33m"
blue = "\033[1;34m"
cyan = "\033[1;36m"
purple = "\033[1;35m"
reset = "\033[1;0m"


def norm_recipe(*recipe):
    return tuple(sorted(recipe))


def remove_nothings(con, cur):
    # Delete all recipes with Nothing as an input
    cur.execute("DELETE FROM recipes WHERE input1 = 'Nothing' OR input2 = 'Nothing'")

    con.commit()


def recalculate_depth_tree(con, cur):

    # Set depth of all elements to NULL
    cur.execute("UPDATE elements SET depth = NULL")

    # Set depth of default elements to 0
    cur.execute(
        "UPDATE elements SET depth = 0 WHERE text IN ('Water', 'Fire', 'Wind', 'Earth')"
    )

    # Loop through the elements and recipes to find the depth of each element

    depth = 0

    while True:
        # Filter all recipes using only elements with depth <= depth
        # and at least one element with depth == depth
        recipes = cur.execute(
            """
          SELECT DISTINCT output FROM recipes
            WHERE (
              (SELECT depth FROM elements WHERE text = input1) = ?
              OR
              (SELECT depth FROM elements WHERE text = input2) = ?
            )
            AND (SELECT depth FROM elements WHERE text = input1) <= ?
            AND (SELECT depth FROM elements WHERE text = input2) <= ?
            
          """,
            (depth, depth, depth, depth),
        ).fetchall()

        # If no recipes were found, break
        if len(recipes) == 0:
            break

        depth += 1

        # Update the depth of the output elements
        for recipe in recipes:
            # # count if this element was updated
            # updates += cur.execute(
            #     "SELECT COUNT(*) FROM elements WHERE depth > ? AND text = ?",
            #     (depth, recipe[0]),
            # ).fetchone()[0]

            cur.execute(
                "UPDATE elements SET depth = COALESCE(MIN(depth, ?), ?) WHERE text = ?",
                (depth, depth, recipe[0]),
            )
    con.commit()


def recalculate_shortest_path(con, cur):
    # Delete the shortest path table
    cur.execute("DROP TABLE IF EXISTS shortest_path")

    # Create the shortest path table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS shortest_path (
            output TEXT,
            input1 TEXT,
            input2 TEXT,
            PRIMARY KEY (output),
            FOREIGN KEY (input1) REFERENCES elements(text),
            FOREIGN KEY (input2) REFERENCES elements(text),
            FOREIGN KEY (output) REFERENCES elements(text)
        )
        """
    )

    # get the shortest path for each element
    res = cur.execute(
        """
        WITH depths AS
            (SELECT input1, e1.depth AS d1, input2, e2.depth AS d2, output, eo.depth AS do FROM recipes 
                JOIN elements AS e1 ON input1 = e1.text
                JOIN elements AS e2 ON input2 = e2.text
                JOIN elements AS eo ON output = eo.text
                WHERE e1.depth < eo.depth AND e2.depth < eo.depth)
        INSERT OR REPLACE INTO shortest_path (output, input1, input2)
        SELECT d1.output, d1.input1, d1.input2 FROM depths d1
            JOIN (
                SELECT output, MIN(d1 + d2) AS shortest FROM depths
                GROUP BY output
            ) shortest ON d1.output = shortest.output AND d1.d1 + d1.d2 = shortest.shortest
"""
    )

    con.commit()


#     cur.execute(
#         """
#         SELECT * FROM recipes
#             GROUP BY output
#             ORDER BY LENGTH(input1) + LENGTH(input2) ASC

# """
#     )


def recalculate_yield(con, cur):
    # Set all counts to 0
    cur.execute("UPDATE elements SET yield = 0")
    cur.execute("UPDATE elements SET recipe_count = 0")
    cur.execute("UPDATE elements SET freq = 0")

    # Loop through all the recipes
    recipes = cur.execute("SELECT * FROM recipes").fetchall()

    unique_products = {}

    for a, b, c in recipes:
        cur.execute(
            "UPDATE elements SET recipe_count = recipe_count + 1 WHERE text = ? OR text = ?",
            (a, b),
        )

        if c == "Nothing":
            continue

        if a not in unique_products:
            unique_products[a] = set()
        if b not in unique_products:
            unique_products[b] = set()

        unique_products[a].add(c)
        unique_products[b].add(c)

        if a != c and b != c:
            cur.execute(
                "UPDATE elements SET freq = freq + 1 WHERE text = ?",
                (c,),
            )

    for element, products in unique_products.items():
        cur.execute(
            "UPDATE elements SET yield = ? WHERE text = ?",
            (len(products), element),
        )

    con.commit()


headers = {
    "authority": "neal.fun",
    "method": "GET",
    "scheme": "https",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://neal.fun/infinite-craft/",
    "Origin": "https://neal.fun",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Sec-Ch-Ua-Platform": "Windows",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Microsoft Edge";v="122"',
}
s = requests.Session()
s.headers.update(headers)


def combine(log, a, b):
    for _ in range(10):
        try:
            # print(s.headers)
            r = s.get(
                f"https://neal.fun/api/infinite-craft/pair?first={quote_plus(a)}&second={quote_plus(b)}",
                timeout=10,
            )
            s.cookies.update(r.cookies)
            if r.status_code == 500:
                raise Exception("Internal Server Error")
            elif r.status_code == 429:
                raise TimeoutError("Rate Limited")
            elif r.status_code == 403:
                raise Exception("Forbidden")
            elif r.status_code != 200:
                raise Exception(r.status_code)
            j = json.loads(r.content)
            if "emoji" not in j:
                print(a, b, j)
            return (j["result"], j["isNew"], j["emoji"])
        except TimeoutError as e:
            log.error(f"Timed Out {a} and {b}: {e}")
            log.debug(f"Retrying in 1 Minute")
            time.sleep(60)
        except Exception as e:
            log.error(f"Failed to combine {a} and {b}: {e}")

    raise Exception("Failed to combine elements")


# Update the depth of a given element and propogate the change
def recursive_update_depth(cur, con, a, b, element):
    a, b = norm_recipe(a, b)
    # Get the depth of the two input elements
    d1 = cur.execute("SELECT depth FROM elements WHERE text = ?", (a,)).fetchone()[0]

    d2 = cur.execute("SELECT depth FROM elements WHERE text = ?", (b,)).fetchone()[0]

    depth = max(d1, d2) + 1

    # Get the old depth of the element
    old_depth = cur.execute(
        "SELECT depth FROM elements WHERE text = ?", (element,)
    ).fetchone()[0]

    # If the old depth was smaller, return
    if old_depth < depth:
        return
    elif old_depth == depth:
        # Here, we need to check if the shortest path has changed
        # Get the old shortest path
        s1, s2 = cur.execute(
            "SELECT input1, input2 FROM shortest_path WHERE output = ?", (element,)
        ).fetchone()

        # Get the depths of the old shortest path
        sd1 = cur.execute(
            "SELECT depth FROM elements WHERE text = ?", (s1,)
        ).fetchone()[0]
        sd2 = cur.execute(
            "SELECT depth FROM elements WHERE text = ?", (s2,)
        ).fetchone()[0]

        if d1 + d2 < sd1 + sd2:
            cur.execute(
                """
                INSERT OR REPLACE INTO shortest_path (output, input1, input2) VALUES (?, ?, ?)
                """,
                (element, a, b),
            )
    else:
        # Always update the shortest path as the depth has changed
        cur.execute(
            """
            INSERT OR REPLACE INTO shortest_path (output, input1, input2) VALUES (?, ?, ?)
            """,
            (element, a, b),
        )

    # Update the depth of the element
    cur.execute("UPDATE elements SET depth = ? WHERE text = ?", (depth, element))

    # Find all recipes that use the element
    recipes = cur.execute(
        "SELECT * FROM recipes WHERE input1 = ? OR input2 = ?", (element, element)
    ).fetchall()

    # Propogate the change to the output elements
    for input1, input2, output in recipes:
        recursive_update_depth(cur, con, input1, input2, output)


def is_numeric(s: str) -> bool:
    return any(c.isdigit() for c in s)


def async_insert_combination(log, a, b):
    try:
        result, is_new, emoji = combine(log, a, b)
    except Exception as e:
        log.error(f"Failed to combine {a} and {b}: {e}")

        return None

    return a, b, result, is_new, emoji


def insert_recipe(log, cur, con, a, b, result, emoji, is_new):
    a, b = norm_recipe(a, b)

    # Insert the new recipe into the database
    cur.execute(
        "INSERT OR IGNORE INTO recipes VALUES (?, ?, ?)",
        (a, b, result),
    )

    new_element = (
        cur.execute(
            "SELECT COUNT(*) FROM elements WHERE text = ?", (result,)
        ).fetchone()[0]
        == 0
    )

    # Add 1 recipe count to both input elements
    cur.execute(
        "UPDATE elements SET recipe_count = recipe_count + 1 WHERE text = ? OR text = ?",
        (a, b),
    )

    # if the element is new:
    if new_element:
        # Get the depth of the input elements
        d1 = cur.execute("SELECT depth FROM elements WHERE text = ?", (a,)).fetchone()[
            0
        ]
        d2 = cur.execute("SELECT depth FROM elements WHERE text = ?", (b,)).fetchone()[
            0
        ]

        # Calculate the depth of the new element
        depth = max(d1, d2) + 1

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

        # Insert this recipe as the shortest path
        cur.execute(
            "INSERT OR REPLACE INTO shortest_path (output, input1, input2) VALUES (?, ?, ?)",
            (result, a, b),
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
        if a != b and (
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
        recursive_update_depth(cur, con, a, b, result)

    con.commit()


def insert_combination(log, pool, args, con, cur, inputs):
    # Filter out numeric elements
    if args.skip_numeric:
        inputs = [(a, b) for a, b in inputs if not (is_numeric(a) or is_numeric(b))]

    # Filter out elements with Nothing as an input
    inputs = [(a, b) for a, b in inputs if a != "Nothing" and b != "Nothing"]

    # normalize
    inputs = [norm_recipe(a, b) for a, b in inputs]

    # Filter unique
    inputs = list(set(inputs))

    # Filter out recipes we have already tried
    inputs = [
        (a, b)
        for a, b in inputs
        if cur.execute(
            "SELECT COUNT(*) FROM recipes WHERE input1 = ? AND input2 = ?", (a, b)
        ).fetchone()[0]
        == 0
    ]

    log.info(f"Pushing new batch with {len(inputs)} items")

    results = []

    try:
        for a, b in inputs:
            results.append(
                pool.apply_async(
                    async_insert_combination,
                    args=(log, a, b),
                )
            )

            newres = []
            for r in results:
                if not r.ready():
                    newres.append(r)
                else:
                    res = r.get()
                    if res is not None:
                        a, b, result, is_new, emoji = res
                        insert_recipe(log, cur, con, a, b, result, emoji, is_new)

            results = newres

            # Wait
            time.sleep(
                max(
                    0.0,
                    random.uniform(0.1, 0.12),
                )
            )

        text_results = []

        for r in results:
            res = r.get()
            if res is not None:
                a, b, result, is_new, emoji = res
                text_results.append(result)
                insert_recipe(log, cur, con, a, b, result, emoji, is_new)
    except KeyboardInterrupt:
        log.error("Keyboard Interrupt")
        # Cancel all the tasks
        for r in results:
            r.cancel()
        raise

    return text_results


def setup_logging():
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

    return log
