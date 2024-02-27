import "./Nav.css";
import { useState, useEffect } from "react";

export default function Nav() {
  const [stats, setStats] = useState({
    count: 0,
    recipes: 0,
  });

  useEffect(() => {
    console.log("Fetching stats");

    fetch("/api/stats")
      .then((res) => {
        console.log(res);
        return res.json();
      })
      .then((data) => setStats(data));
  }, []);

  return (
    <div className="Nav">
      <div className="col">
        <h1>Infinite Craft Database</h1>
        <h2>
          Currently crawling {stats.count} elements and
          <br />
          {stats.recipes} recipes from the game{" "}
          <a href="https://neal.fun/infinite-craft">Infinite Craft</a>
        </h2>
      </div>
      <div className="col">
        <input
          className="search"
          type="text"
          placeholder="Search for an item"
        />
      </div>
      <div className="col">
        <button className="button">Search</button>
      </div>
      <div className="col">
        <button className="button">Random</button>
      </div>
    </div>
  );
}
