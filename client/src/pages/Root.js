import Nav from "./Nav";
import { PiSortAscending, PiSortDescending } from "react-icons/pi";
import { useState, useEffect } from "react";
import Select from "react-select";
import { styled } from "styled-components";
import { TextStyle, ButtonStyle } from "../styles";
import { COLORS } from "../styles";
import ElementList from "./ElementList";

export default function Root() {
  const [key, setKey] = useState("depth");
  const [ascending, setAscending] = useState(false);

  const options = [
    { value: "depth", label: "Depth" },
    { value: "text", label: "Alphabetically" },
    { value: "length", label: "Text Length" },
    { value: "recipe_count", label: "Number of Uses" },
    { value: "freq", label: "Ways Created" },
    { value: "yield", label: "Yield" },
  ];

  const IconButton = styled.button`
    ${ButtonStyle}
    ${TextStyle}
    border-radius: 0.4em;
    height: 100%;
    aspect-ratio: 1;
    font-size: 1.1em;
  `;

  const [elements, setElements] = useState([]);

  useEffect(() => {
    fetch(`/api/sort?key=${key}&descending=${ascending}&limit=500`)
      .then((res) => res.json())
      .then((data) => setElements(data));
  }, [key, ascending]);

  const showMore = () => {
    fetch(
      `/api/sort?key=${key}&descending=${ascending}&offset=${elements.length}&limit=500`
    )
      .then((res) => res.json())
      .then((data) => setElements(elements.concat(data)));
  };

  return (
    <div className="Root">
      <Nav />
      <div
        className="flex"
        style={{
          "justify-content": "flex-end",
          "padding-right": "1em",
          "align-items": "stretch",
        }}
      >
        <div className="col">
          <Select
            styles={{
              control: (styles, state) => ({
                ...styles,
                width: "11em",
                border: `2px solid ${COLORS.primary75}`,
                "background-color": "transparent",
                cursor: "pointer",
                "&:hover": { scale: "1.03" },
                "border-radius": "0.4em",
              }),
              option: (styles, state) => ({
                ...styles,
                "background-color": state.isFocused
                  ? COLORS.primary75
                  : state.isSelected
                  ? COLORS.primary50
                  : "transparent",
                color: "white",
                cursor: "pointer",
              }),
              singleValue: (styles, state) => ({
                ...styles,
                color: COLORS.neutral100,
              }),
              menu: (styles) => ({
                ...styles,
                "background-color": COLORS.primary25,
              }),
            }}
            options={options}
            defaultValue={options[0]}
            onChange={(selectedOption) => setKey(selectedOption.value)}
          />
        </div>
        <div className="col">
          <IconButton onClick={() => setAscending(!ascending)}>
            {ascending ? <PiSortAscending /> : <PiSortDescending />}
          </IconButton>
        </div>
      </div>
      <ElementList elements={elements} showMore={showMore} />
    </div>
  );
}
