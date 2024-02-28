import "./Nav.css";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function Nav() {
  const [stats, setStats] = useState({
    count: "?",
    recipes: "?",
  });

  useEffect(() => {
    fetch("/api/stats")
      .then((res) => res.json())
      .then((data) => setStats(data));
  }, []);

  const [searchText, setSearchText] = useState("");
  const navigate = useNavigate();

  const handleSearch = () => {
    if (searchText.trim() !== "") {
      navigate(`/element/${encodeURIComponent(searchText)}`);
    }
  };

  const handleRandom = () => {
    fetch("/api/random")
      .then((res) => res.json())
      .then((data) => {
        navigate(`/element/${encodeURIComponent(data.text)}`);
      });
  };

  const handleKeyPress = (event) => {
    if (event.key === "Enter") {
      handleSearch();
    }
  };

  return (
    <div className="Nav flex">
      <div className="col">
        <h1>Infinite Craft Database</h1>
        <span>
          Currently contains {stats.count} elements and
          <br />
          {stats.recipes} recipes from the game{" "}
          <a href="https://neal.fun/infinite-craft">Infinite Craft</a>
        </span>
      </div>
      <div className="col">
        <input
          className="search"
          type="text"
          placeholder="Search for an item"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          onKeyPress={handleKeyPress}
        />
      </div>
      <div className="col">
        <button className="button" onClick={handleSearch}>
          Search
        </button>
      </div>
      <div className="col">
        <button className="button" onClick={handleRandom}>
          Random
        </button>
      </div>
    </div>
  );
}
