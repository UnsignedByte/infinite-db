const express = require("express");
const app = express();
const sqlite3 = require("sqlite3").verbose();
const path = require("path");
const fuzz = require("fuzzball");
const cors = require("cors");
const helmet = require("helmet");

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

app.use(
  cors({
    origin: "same-origin",
  })
);

// Use static files from the build folder
app.use(express.static("client/build"));

app.get("/api/stats", (req, res) => {
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
});

app.get("/api/random", (req, res) => {
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
});

app.get("/api/similar", (req, res) => {
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

    // Use fuzzball to find the most similar word
    const similar = fuzz
      .extract(term, words, {
        scorer: fuzz.token_set_ratio,
        limit: 10,
      })
      .map((item) => item[0]);

    res.status(200).json(similar);
  });
});

app.get("/api/element", (req, res) => {
  // error if text is not provided
  if (!req.query.text) {
    res.status(400).json({ error: "No text query provided" });
    return;
  }

  const term = decodeURIComponent(req.query.text); // Get the search term from the query parameter

  // Get the term from the database
  db.get(`SELECT * FROM elements WHERE text = ?`, [term], (err, row) => {
    if (err) {
      res.status(500).json({ error: err.message });
      return;
    }

    if (!row) {
      res.status(404).json({ error: "Element not found" });
      return;
    }

    res.status(200).json(row);
  });
});

app.get("/api/recipes/:filter(input|output)", (req, res) => {
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
          `SELECT * FROM recipes WHERE input1 = ? OR input2 = ? ORDER BY output ASC`,
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

    res.status(200).json({
      recipes: rows,
      count: l,
    });
  });
});

app.get("/api/path", (req, res) => {
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

    res.status(200).json(paths);
  });
});

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);

function shutdown() {
  console.log("Shutting down");
  db.close();
  process.exit(0);
}
