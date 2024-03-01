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
      `SELECT ${short ? "text, emoji" : "*"} FROM elements WHERE text = ?`,
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
    const emojis = Object.fromEntries(elems.map((e) => [e.text, e.emoji]));

    return recipes.map((r) => ({
      ...r,
      input1: { text: r.input1, emoji: emojis[r.input1] },
      input2: { text: r.input2, emoji: emojis[r.input2] },
      output: { text: r.output, emoji: emojis[r.output] },
    }));
  });
}

module.exports = {
  getElements,
  elaborateRecipes,
};
