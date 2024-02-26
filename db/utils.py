def norm_recipe(*recipe):
    return tuple(sorted(recipe))


def recalculate_depth_tree(con, cur):
    # Delete all recipes with Nothing as an input
    cur.execute("DELETE FROM recipes WHERE input1 = 'Nothing' OR input2 = 'Nothing'")

    # Set depth of all elements to NULL
    cur.execute("UPDATE elements SET depth = NULL")

    # Set depth of default elements to 0
    cur.execute(
        "UPDATE elements SET depth = 0 WHERE text IN ('Water', 'Fire', 'Wind', 'Earth')"
    )
    con.commit()

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

        # updates = 0

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

        # If no new elements were updated, break
        # if updates == 0:
        #     break
        con.commit()


def recalculate_yield(con, cur):
    # Set all counts to 0
    cur.execute("UPDATE elements SET yield = 0")
    cur.execute("UPDATE elements SET recipe_count = 0")

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
