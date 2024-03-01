import { css } from "styled-components";

export const COLORS = {
  primary0: "#282c34",
  primary25: "#1e222a",
  primary50: "#2e3544",
  primary75: "#3b5998",
  primary100: "#61dafb",
  neutral0: "#000000",
  neutral25: "#404040",
  neutral50: "#6b6b6b",
  neutral75: "#888888",
  neutral100: "#ffffff",
  background: "#282c34",
};

export const TextStyle = css`
  color: ${(props) => props.theme.colors.neutral100};
  font-size: 0.9em;
  font-weight: normal;
`;

export const ButtonStyle = css`
  background-color: transparent;
  border: 2px solid ${(props) => props.theme.colors.primary75};
  border-radius: 0.3em;
  color: ${(props) => props.theme.colors.neutral100};
  cursor: pointer;
  &:hover {
    background: linear-gradient(
      180deg,
      transparent,
      ${(props) => props.theme.colors.primary50} 100%
    );
    scale: 1.03;
  }
`;

export const LinkStyle = css`
  background-color: transparent;
  border: none;
  color: ${(props) => props.theme.colors.primary100};
  cursor: pointer;
  font-size: 1em;
  padding: 0;
  &:hover {
    text-decoration: underline;
  }
`;

export const InputStyle = css`
  border: 2px solid ${(props) => props.theme.colors.primary75};
  background-color: ${(props) => props.theme.colors.primary50};
  color: ${(props) => props.theme.colors.neutral100};
  border-radius: 0.5em;
  padding: 0.4em;
`;
