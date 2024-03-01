import Element from "./Element";
import { TextStyle, ButtonStyle } from "../styles";
import { styled } from "styled-components";

const Button = styled.button`
  ${ButtonStyle}
  ${TextStyle}
`;
export default function ElementList({ elements, showMore }) {
  return (
    <div
      style={{
        "padding-bottom": "1em",
      }}
    >
      <div className="flex wrap">
        {elements.map((s) => (
          <div class="col">
            <Element emoji={s.emoji} text={s.text} />
          </div>
        ))}
      </div>
      <div
        style={{
          "text-align": "right",
        }}
      >
        <Button onClick={showMore}>Show More</Button>
      </div>
    </div>
  );
}
