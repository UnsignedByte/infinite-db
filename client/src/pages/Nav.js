import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { LinkStyle, ButtonStyle, InputStyle } from "../styles";
import { styled, css } from "styled-components";

const SearchStyle = css`
  padding: 1.2em;
  outline: none;
  border-radius: 0.8em;
  box-sizing: border-box;
  font-size: 1.1em;
  width: 100%;
`;

const Button = styled.button`
  ${ButtonStyle}
  ${SearchStyle}
`;

const SearchBar = styled.input`
  ${InputStyle}
  ${SearchStyle}
`;

const Link = styled.button`
  ${LinkStyle}
`;

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
          <Link onClick={() => window.open("https://neal.fun/infinite-craft/")}>
            Infinite Craft
          </Link>
        </span>
      </div>
      <div
        className="col"
        style={{
          "flex-grow": "10",
          "padding-left": "1.5em",
        }}
      >
        <SearchBar
          type="text"
          placeholder="Search for an item"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          onKeyPress={handleKeyPress}
        />
      </div>
      <div className="col">
        <Button onClick={handleSearch}>Search</Button>
      </div>
      <div className="col">
        <Button onClick={handleRandom}>Random</Button>
      </div>
      <div className="col">
        <Button onClick={() => navigate("/")}>Home</Button>
      </div>
    </div>
  );
}
