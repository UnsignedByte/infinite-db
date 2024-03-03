const express = require("express");
const app = express();
const sqlite3 = require("sqlite3").verbose();
const path = require("path");
const fuzz = require("fuzzball");
const cors = require("cors");
const helmet = require("helmet");

const utils = require("./utils");

const port = process.env.PORT || 3001;

const root = path.join(__dirname, "../");

// Connect to the database in the crawler
const db = new sqlite3.Database(
  path.join(root, "crawler", "infinite_craft.db"),
  sqlite3.OPEN_READONLY,
  (err) => {
    if (err) {
      console.error(err.message);
    } else {
      console.log("Connected to the database");
    }
  }
);

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});

app.use(cors());

// Use static files from the build folder
app.use(express.static("client/build"));

// catch all other routes that are not the api and serve the index.html
app.get("*", (req, res) => {
  res.sendFile(path.join(root, "client/build", "index.html"));
});

app.get(
  "/api/stats",
  cors({
    origin: "same-origin",
  }),
  (req, res) => {
    db.get(
      ` SELECT 
        COUNT(*) AS count,
        SUM(CASE WHEN discovered = true THEN 1 ELSE 0 END) AS discovered,
        SUM(CASE WHEN recipe_count = 0 THEN 1 ELSE 0 END) AS unused
      FROM elements`,
      [],
      (err, row1) => {
        if (err) {
          res.status(500).json({ error: err.message });
          return;
        }

        db.get(`SELECT COUNT(*) AS recipes FROM recipes`, [], (err, row2) => {
          if (err) {
            res.status(500).json({ error: err.message });
            return;
          }

          res.status(200).json({ ...row1, ...row2 });
        });
      }
    );
  }
);

app.get(
  "/api/random",
  cors({
    origin: "same-origin",
  }),
  (req, res) => {
    db.get(
      `SELECT text FROM elements ORDER BY RANDOM() LIMIT 1`,
      [],
      (err, row) => {
        if (err) {
          res.status(500).json({ error: err.message });
          return;
        }

        if (!row) {
          res.status(404).json({ error: "Element not found" });
          return;
        }

        res.status(200).json(row);
      }
    );
  }
);

app.get(
  "/api/similar",
  cors({
    origin: "same-origin",
  }),
  (req, res) => {
    // error if text is not provided
    if (!req.query.text) {
      res.status(400).json({ error: "No text query provided" });
      return;
    }

    const term = decodeURIComponent(req.query.text); // Get the search term from the query parameter

    // First, check if the term is in the database
    db.all(`SELECT text FROM elements`, [], (err, rows) => {
      if (err) {
        res.status(500).json({ error: err.message });
        return;
      }

      // Create a list of all words
      const words = rows.map((row) => row.text);
      const limit = Number(req.query.limit || 100);

      // Use fuzzball to find the most similar word
      const similar = fuzz.extract(term, words, {
        scorer: fuzz.token_set_ratio,
        limit,
      });

      // sort by score and then alphabetically
      similar.sort((a, b) => {
        if (a[1] === b[1]) {
          return a[0].localeCompare(b[0]);
        }
        return b[1] - a[1];
      });

      utils
        .getElements(
          db,
          similar.map((s) => s[0]),
          true
        )
        .then((rows) => {
          res.status(200).json(rows);
        });
    });
  }
);

app.get(
  "/api/elements?",
  cors({
    origin: "same-origin",
  }),
  (req, res) => {
    // error if text is not provided
    if (!req.query.text) {
      res.status(400).json({ error: "No text query provided" });
      return;
    }

    const term = decodeURIComponent(req.query.text); // Get the search term from the query parameter

    // Get the term from the database
    utils
      .getElements(db, [term])
      .then((rows) => {
        if (!rows[0]) {
          res.status(404).json({ error: "Element not found" });
          return;
        }

        res.status(200).json(rows[0]);
      })
      .catch((err) => {
        res.status(500).json({ error: err.message });
      });
  }
);

app.post(
  "/api/elements?",
  cors({
    origin: "same-origin",
  }),
  (req, res) => {
    // get the post data
    req.body
      .json()
      .then((data) => getElements(db, data))
      .then((rows) => res.status(200).json(rows))
      .catch((err) => res.status(500).json({ error: err.message }));
  }
);

app.get(
  "/api/recipes/:filter(input|output)",
  cors({
    origin: "same-origin",
  }),
  (req, res) => {
    if (!req.query.text) {
      res.status(400).json({ error: "No text query provided" });
      return;
    }

    const term = decodeURIComponent(req.query.text); // Get the search term from the query parameter
    const offset = Number(req.query.offset || 0);
    const limit = Number(req.query.limit || 10);

    const type = req.params.filter;

    const query =
      type === "input"
        ? [
            `SELECT * FROM recipes WHERE input1 = ? OR input2 = ? AND output <> "Nothing" ORDER BY output ASC`,
            [term, term],
          ]
        : [
            `SELECT * FROM recipes WHERE output = ? ORDER BY input1, input2 ASC`,
            [term],
          ];

    db.all(...query, (err, rows) => {
      if (err) {
        res.status(500).json({ error: err.message });
        return;
      }

      const l = rows.length;

      if (limit > 0) {
        rows = rows.slice(offset, offset + limit);
      } else {
        rows = rows.slice(offset);
      }

      utils
        .elaborateRecipes(db, rows)
        .then((rows) => res.status(200).json({ recipes: rows, count: l }));
    });
  }
);

app.get(
  "/api/path",
  cors({
    origin: "same-origin",
  }),
  (req, res) => {
    const find_path = async (target, paths = {}) => {
      if (target in paths) {
        return paths;
      }

      const target_depth = await new Promise((resolve, reject) => {
        db.get(
          "SELECT depth FROM elements WHERE text = ?",
          [target],
          (err, row) => {
            if (err) {
              res.status(500).json({ error: err.message });
              reject();
              return;
            }
            if (!row) {
              res.status(404).json({ error: "Element not found" });
              reject();
              return;
            }

            resolve(row.depth);
          }
        );
      });
      if (target_depth === 0) {
        return { [target]: { depth: 0 } };
      }

      const recipe = await new Promise((resolve, reject) => {
        // Find the recipe that creates the target element with the lowest sum depth of inputs
        // Include only recipes where the inputs have a depth < output depth
        // This is to ensure that recipes have no cycles
        db.get(
          `
          SELECT input1, input2
          FROM recipes
          WHERE output = ?
            AND (SELECT depth FROM elements WHERE text = input1) < ?
            AND (SELECT depth FROM elements WHERE text = input2) < ?
          ORDER BY (SELECT depth FROM elements WHERE text = input1) + (SELECT depth FROM elements WHERE text = input2)
          LIMIT 1
          `,
          [target, target_depth, target_depth],
          (err, row) => {
            if (err) {
              res.status(500).json({ error: err.message });
              reject();
              return;
            }
            if (!row) {
              res.status(404).json({ error: "Element not found" });
              reject();
              return;
            }

            resolve(row);
          }
        );
      });

      paths[target] = {
        depth: target_depth,
        ...recipe,
      };

      if (!(recipe.input1 in paths)) {
        const p = await find_path(recipe.input1, paths);
        paths = { ...paths, ...p };
      }

      if (!(recipe.input2 in paths)) {
        const p = await find_path(recipe.input2, paths);
        paths = { ...paths, ...p };
      }

      return paths;
    };

    if (!req.query.text) {
      res.status(400).json({ error: "No text query provided" });
      return;
    }

    const term = decodeURIComponent(req.query.text);

    find_path(term).then((paths) => {
      // Make it into a list and filter out depth 0 elements
      paths = Object.keys(paths)
        .map((key) => ({ output: key, ...paths[key] }))
        .filter((p) => p.depth > 0);

      // sort by depth
      paths.sort((a, b) => a.depth - b.depth);

      // Get all unique elements in the path
      utils
        .elaborateRecipes(db, paths)
        .then((rows) => res.status(200).json(rows));
    });
  }
);

app.get(
  "/api/sort",
  cors({
    origin: "same-origin",
  }),
  (req, res) => {
    const key = req.query.key || "depth";
    const descending = req.query.descending === "true";
    const offset = Number(req.query.offset || 0);
    const limit = Number(req.query.limit || 100);

    const boolDesc = (d) => (d ? "DESC" : "ASC");

    const keymap = {
      text: "text",
      length: "LENGTH(text)",
      depth: "depth",
      discovered: "discovered",
      recipe_count: "recipe_count",
      freq: "freq",
      yield: `CASE WHEN
          recipe_count = 0
          THEN 0
          ELSE CAST(yield as REAL) / recipe_count
        END ${boolDesc(descending)}, recipe_count`,
    };

    if (!(key in keymap)) {
      res.status(400).json({ error: "Invalid sort key" });
      return;
    }

    db.all(
      `SELECT * FROM elements ORDER BY ${keymap[key]} ${
        descending ? "DESC" : "ASC"
      }, text LIMIT ? OFFSET ?`,
      [limit, offset],
      (err, rows) => {
        if (err) {
          res.status(500).json({ error: err.message });
          return;
        }

        res.status(200).json(rows);
      }
    );
  }
);

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);

function shutdown() {
  console.log("Shutting down");
  db.close();
  process.exit(0);
}
