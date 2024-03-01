import { useParams, useNavigate } from "react-router-dom";
import { TextStyle, ButtonStyle } from "../styles";
import { styled } from "styled-components";
import { COLORS } from "../styles";

const Button = styled.button`
  ${ButtonStyle}
  ${TextStyle}
  padding: 0.4em .5em;
  margin: 0.1em;
  border-radius: 0.3em;
  border: 0.2em solid ${(props) => props.theme.colors.neutral50};
  box-sizing: border-box;
  &:hover {
    background: linear-gradient(
      180deg,
      transparent,
      ${(props) => props.theme.colors.neutral25} 100%
    );
  }
`;

// UI for a single element
export default function Element({ element }) {
  const navigate = useNavigate();
  return (
    <Button
      onClick={(e) => {
        e.preventDefault();
        navigate(`/element/${encodeURIComponent(element.text)}`);
      }}
    >
      {element.emoji && (
        <span
          style={{
            "margin-right": "0.5em",
          }}
        >
          {element.emoji}
        </span>
      )}
      <span
        style={{
          color: element.discovered ? COLORS.primary100 : COLORS.neutral100,
        }}
      >
        {element.text}
      </span>
    </Button>
  );
}
