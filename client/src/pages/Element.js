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

function ElementDetails({ data }) {
  return (
    <div>
      <h2>Details for the element {data.text}</h2>
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
