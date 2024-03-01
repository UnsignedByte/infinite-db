import { useParams, useNavigate } from "react-router-dom";
import { TextStyle, ButtonStyle } from "../styles";
import { styled } from "styled-components";

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
export default function Element({ emoji, text }) {
  const navigate = useNavigate();
  return (
    <Button
      onClick={(e) => {
        e.preventDefault();
        navigate(`/element/${encodeURIComponent(text)}`);
      }}
    >
      {emoji && (
        <span
          style={{
            "margin-right": "0.5em",
          }}
        >
          {emoji}
        </span>
      )}
      <span>{text}</span>
    </Button>
  );
}
