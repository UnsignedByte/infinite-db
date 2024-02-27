import { useParams } from "react-router-dom";
import Nav from "./Nav";
import { useState, useEffect } from "react";
import "./Element.css";

function Similar({ text, similar }) {
  return (
    <div>
      <h2>Element {text} not found in the database.</h2>
      <p>Here are some similar elements:</p>
      <ul>
        {similar.map((s) => (
          <li key={s}>
            <a href={`/element/${encodeURIComponent(s)}`}>{s}</a>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RecipeTable({ text, type }) {
  const [recipes, setRecipes] = useState({
    recipes: [],
    count: 0,
  });

  const normalizeRecipes = (data) => {
    if (type === "input") {
      data.recipes = data.recipes.map((row) => {
        // order the inputs so that the searched term is first
        if (row.input2 === text) {
          return {
            input1: row.input2,
            input2: row.input1,
            output: row.output,
          };
        }
        return row;
      });
    }

    return data;
  };

  const concatRecipes = (data) => {
    data = normalizeRecipes(data);

    setRecipes({
      recipes: recipes.recipes.concat(data.recipes),
      count: data.count,
    });
  };

  const uriText = encodeURIComponent(text);

  useEffect(() => {
    // first reset the data
    setRecipes({
      recipes: [],
      count: 0,
    });
    fetch(`/api/recipes/${type}?text=${uriText}&limit=10`)
      .then((res) => res.json())
      .then((data) => setRecipes(normalizeRecipes(data)));
  }, [text]);

  const showMore = () => {
    fetch(
      `/api/recipes/${type}?text=${uriText}&offset=${recipes.recipes.length}&limit=10`
    )
      .then((res) => res.json())
      .then(concatRecipes);
  };

  const showAll = () => {
    fetch(
      `/api/recipes/${type}?text=${uriText}&offset=${recipes.recipes.length}&limit=0`
    )
      .then((res) => res.json())
      .then(concatRecipes);
  };

  return (
    <div className="RecipeTable">
      <table>
        <thead>
          <tr>
            <th className="input">Input 1</th>
            <th className="input">Input 2</th>
            <th className="output">Output</th>
          </tr>
        </thead>
        <tbody>
          {recipes.recipes.map((row, i) => (
            <tr key={i}>
              <td className="input">{row.input1}</td>
              <td className="input">{row.input2}</td>
              <td className="output">{row.output}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex">
        <div className="col">
          Showing {recipes.recipes.length} of {recipes.count} recipes.
        </div>
        <div className="col">
          <button onClick={showMore}>Show More</button>
        </div>
        <div className="col">
          <button onClick={showAll}>Show All</button>
        </div>
      </div>
    </div>
  );
}

function ElementDetails({ data }) {
  return (
    <div>
      <h2>
        Details for the element {data.emoji} {data.text}
      </h2>
      <p>First Discovered Here: {data.discovered ? "Yes" : "No"}</p>
      <p>Element Depth: {data.depth}</p>
      <p>
        This element has been used {data.recipe_count} times to create{" "}
        {data.yield} unique elements.
      </p>
      <p>
        This element can be created {data.freq} different ways, without using
        itself.
      </p>
      <div className="flex recipecolumns">
        <div className="col">
          <h3>Recipes Using {data.text}</h3>
          <RecipeTable text={data.text} type="input" />
        </div>

        <div className="col">
          <h3>Recipes Creating {data.text}</h3>
          <RecipeTable text={data.text} type="output" />
        </div>
      </div>
    </div>
  );
}

export default function Element() {
  const { text } = useParams();

  const [data, setData] = useState({});

  useEffect(() => {
    const parsedText = encodeURIComponent(text);
    fetch(`/api/element?text=${parsedText}`)
      .then((res) => {
        if (res.ok) {
          return res.json();
        } else if (res.status === 404) {
          // Get similar elements instead
          return fetch(`/api/similar?text=${parsedText}`).then((res) => {
            if (res.ok) {
              return res.json().then((j) => ({ similar: j }));
            }
          });
        } else {
          console.error("Error fetching element", res);
        }
      })
      .then((data) => {
        setData(data);
      });
  }, [text]);

  return (
    <div>
      <Nav />
      <div className="Element">
        {"similar" in data ? (
          <Similar text={text} similar={data.similar} />
        ) : "text" in data ? (
          <ElementDetails data={data} />
        ) : (
          <div>
            <h2>{text}</h2>
            <p>Loading...</p>
          </div>
        )}
      </div>
    </div>
  );
}
