import { useParams, useNavigate } from "react-router-dom";
import Nav from "./Nav";
import { useState, useEffect } from "react";
import "./ElementPage.css";
import Element from "./Element";
import { styled } from "styled-components";
import { TextStyle, ButtonStyle } from "../styles";
import ElementList from "./ElementList";

const Button = styled.button`
  ${ButtonStyle}
  ${TextStyle}
`;

function Similar({ text }) {
  const [similar, setSimilar] = useState([]);

  useEffect(() => {
    // Get similar elements instead
    fetch(`/api/similar?text=${encodeURIComponent(text)}&limit=100`).then(
      (res) => {
        if (res.ok) {
          res.json().then((j) => setSimilar(j));
        } else {
          console.error("Error fetching similar elements", res);
        }
      }
    );
  }, [text]);

  const showMore = () => {
    fetch(
      `/api/similar?text=${encodeURIComponent(text)}&limit=${
        similar.length + 100
      }`
    ).then((res) => {
      if (res.ok) {
        res.json().then((j) => setSimilar(j));
      } else {
        console.error("Error fetching similar elements", res);
      }
    });
  };

  return (
    <div className="Similar">
      <h2>
        Element {text} not found in the database. Here are some similar
        elements:
      </h2>
      <ElementList elements={similar} showMore={showMore} />
    </div>
  );
}

function RecipeTable({ text, type }) {
  const [recipes, setRecipes] = useState({
    recipes: [],
    count: 0,
  });

  const normalizeRecipes = (data) => {
    console.log(data);
    if (type === "input") {
      data.recipes = data.recipes.map((row) => {
        // order the inputs so that the searched term is first
        if (row.input2.text === text) {
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
  }, [uriText]);

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
      <table
        style={{
          padding: "0.5em",
          width: "100%",
        }}
      >
        <tbody>
          {recipes.recipes.map((row, i) => (
            <tr key={i}>
              <td className="left">
                <Element emoji={row.input1.emoji} text={row.input1.text} />
              </td>
              <td className="center">+</td>
              <td className="left">
                <Element emoji={row.input2.emoji} text={row.input2.text} />
              </td>
              <td className="center">=</td>
              <td className="right">
                <Element emoji={row.output.emoji} text={row.output.text} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div
        className="flex"
        style={{
          width: "100%",
        }}
      >
        <div
          className="col"
          style={{
            "flex-grow": "10",
          }}
        >
          Showing {recipes.recipes.length} of {recipes.count} recipes.
        </div>
        <div className="col">
          <Button onClick={showMore}>Show More</Button>
        </div>
        <div className="col">
          <Button onClick={showAll}>Show All</Button>
        </div>
      </div>
    </div>
  );
}

const TableTitle = styled.h3`
  width: 100%;
  text-align: center;
`;

function ElementDetails({ data }) {
  const [path, setPath] = useState([]);

  useEffect(() => {
    // first reset the data
    setPath([]);
    fetch(`/api/path?text=${encodeURIComponent(data.text)}`)
      .then((res) => res.json())
      .then((data) => setPath(data));
  }, [data.text]);
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
        This element has been created {data.freq} different ways without using
        itself.
      </p>

      <div
        className="flex wrap"
        style={{
          "justify-content": "space-evenly",
          "align-items": "first baseline",
          width: "100%",
        }}
      >
        <div className="col">
          <TableTitle>Example way to Make {data.text}</TableTitle>
          <div>
            <table>
              <thead>
                <tr>
                  <th className="left">Input 1</th>
                  <th />
                  <th className="left">Input 2</th>
                  <th />
                  <th className="left">Output</th>
                  <th className="right">Depth</th>
                </tr>
              </thead>
              <tbody>
                {path.map((row, i) => (
                  <tr key={i}>
                    <td className="left">
                      <Element
                        emoji={row.input1.emoji}
                        text={row.input1.text}
                      />
                    </td>
                    <td className="center">+</td>
                    <td className="left">
                      <Element
                        emoji={row.input2.emoji}
                        text={row.input2.text}
                      />
                    </td>
                    <td className="center">=</td>
                    <td className="left">
                      <Element
                        emoji={row.output.emoji}
                        text={row.output.text}
                      />
                    </td>
                    <td className="right">{row.depth}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="col">
          <TableTitle>Recipes Using {data.text}</TableTitle>
          <RecipeTable text={data.text} type="input" />
        </div>

        <div className="col">
          <TableTitle>Recipes Creating {data.text}</TableTitle>
          <RecipeTable text={data.text} type="output" />
        </div>
      </div>
    </div>
  );
}

export default function ElementPage() {
  const { text } = useParams();

  const [data, setData] = useState();

  useEffect(() => {
    const parsedText = encodeURIComponent(text);
    fetch(`/api/element?text=${parsedText}`)
      .then((res) => {
        if (res.ok) {
          return res.json();
        } else if (res.status === 404) {
          return {};
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
      <div className="ElementPage">
        {!data ? (
          <div>Loading...</div>
        ) : "text" in data ? (
          <ElementDetails data={data} />
        ) : (
          <Similar text={text} />
        )}
      </div>
    </div>
  );
}
