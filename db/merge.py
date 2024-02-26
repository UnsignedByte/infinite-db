import sqlite3
import json
from utils import recalculate_depth_tree, norm_recipe, recalculate_yield

con = sqlite3.connect("infinite_craft.db")
cur = con.cursor()

# Enable foreign keys
cur.execute("PRAGMA foreign_keys = ON")

cur.execute(
    """
      CREATE TABLE IF NOT EXISTS elements (
        text TEXT PRIMARY KEY,
        emoji TEXT,
        discovered BOOLEAN,
        depth INTEGER,
        yield INTEGER,
        recipe_count INTEGER
      )
    """
)

cur.execute(
    """ CREATE TABLE IF NOT EXISTS recipes (
          input1 TEXT,
          input2 TEXT,
          output TEXT,
          PRIMARY KEY (input1, input2),
          FOREIGN KEY (input1) REFERENCES elements(text),
          FOREIGN KEY (input2) REFERENCES elements(text),
          FOREIGN KEY (output) REFERENCES elements(text)
        )"""
)

# Load JSON data
with open("infinitecraft.json", "r") as f:
    data = json.load(f)

# Insert elements
for element in data["elements"]:
    cur.execute(
        "INSERT OR IGNORE INTO elements (text, emoji, discovered) VALUES (?, ?, ?)",
        (element["text"], element["emoji"], element["discovered"]),
    )

# Insert recipes
for output, recipes in data["recipes"].items():
    for recipe in recipes:
        r = norm_recipe(recipe[0]["text"], recipe[1]["text"])
        try:
            cur.execute(
                "INSERT OR IGNORE INTO recipes (input1, input2, output) VALUES (?, ?, ?)",
                (*r, output),
            )
        except sqlite3.IntegrityError as e:
            print(e)
            print(f"Invalid recipe: {r[0]} + {r[1]} = {output}")

recalculate_depth_tree(con, cur)
recalculate_yield(con, cur)
con.commit()

con.close()
