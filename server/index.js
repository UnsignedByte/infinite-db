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

app.use(cors());

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

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);

function shutdown() {
  console.log("Shutting down");
  db.close();
  process.exit(0);
}
