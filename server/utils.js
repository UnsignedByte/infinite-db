function dbGet(db, query, params) {
  return new Promise((resolve, reject) => {
    db.get(query, params, (err, row) => {
      if (err) {
        reject(err);
        return;
      }
      resolve(row);
    });
  });
}

function getElements(db, elements, short = false) {
  const promises = elements.map((e) =>
    dbGet(
      db,
      `SELECT ${
        short ? "text, emoji, discovered" : "*"
      } FROM elements WHERE text = ?`,
      [e]
    )
  );

  return Promise.all(promises);
}

function elaborateRecipes(db, recipes) {
  const elements = new Set();
  recipes.forEach((r) => {
    elements.add(r.output);
    elements.add(r.input1);
    elements.add(r.input2);
  });

  return getElements(db, Array.from(elements), true).then((elems) => {
    const data = Object.fromEntries(elems.map((e) => [e.text, e]));

    return recipes.map((r) => ({
      ...r,
      input1: data[r.input1],
      input2: data[r.input2],
      output: data[r.output],
    }));
  });
}

async function find_path(res, db, target, paths = {}) {
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
      SELECT input1, input2 FROM shortest_path WHERE output = ?
      `,
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

        resolve(row);
      }
    );
  });

  paths[target] = {
    depth: target_depth,
    ...recipe,
  };

  if (!(recipe.input1 in paths)) {
    const p = await find_path(res, db, recipe.input1, paths);
    paths = { ...paths, ...p };
  }

  if (!(recipe.input2 in paths)) {
    const p = await find_path(res, db, recipe.input2, paths);
    paths = { ...paths, ...p };
  }

  return paths;
}

module.exports = {
  getElements,
  elaborateRecipes,
  find_path,
};
