import React from "react";
import ReactDOM from "react-dom/client";
import Root from "./pages/Root";
import ElementPage from "./pages/ElementPage";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { COLORS } from "./styles";
import { ThemeProvider } from "styled-components";
import { createGlobalStyle } from "styled-components";

const root = ReactDOM.createRoot(document.getElementById("root"));

const router = createBrowserRouter([
  {
    path: "/",
    element: <Root />,
  },
  {
    path: "/element/:utext",
    element: <ElementPage />,
  },
]);

const GlobalStyle = createGlobalStyle`
  html, body, #root {
    width: 100%;
    height: 100%;
  }

  html {
    background-color: ${(props) => props.theme.colors.background};
    color: ${(props) => props.theme.colors.neutral100};
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  #root {
    padding-left: 2em;
    padding-right: 2em;
    padding-top: 1em;
    width: 100%;
    height: 100%;
    box-sizing: border-box;
  }
  
  h1 {
    font-size: 2em;
    margin-bottom: 0;
    margin-top: 0;
  }

  h2 {
    font-size: 1.3em;
    margin-bottom: 0;
    margin-top: 0;
  }

  h3 {
    font-size: 1.1em;
    font-weight: normal;
  }
  
  .flex {
    display: flex;
    align-items: center;
  }

  .wrap {
    flex-wrap: wrap;
  }
  
  .col {
    padding: 0.3em;
  }
  
  .left {
    text-align: left;
  }

  .right {
    text-align: right;
  }

  .center {
    text-align: center;
  }
  
  p {
    margin-left: 1em;
  }

  /* Custom scrollbar styles */
  ::-webkit-scrollbar {
    width: 0.5em;
    height: 0.5em;
    background-color: ${(props) => props.theme.colors.background};
  }

  ::-webkit-scrollbar-corner {
    background-color: ${(props) => props.theme.colors.background};
  }

  ::-webkit-scrollbar-track {
    background-color: ${(props) => props.theme.colors.background};
  }

  ::-webkit-scrollbar-thumb {
    background-color: ${(props) => props.theme.colors.primary50};
    border-radius: 0.2em;
  }

  ::-webkit-scrollbar-thumb:hover {
    background-color: ${(props) => props.theme.colors.primary75};
  }
    
`;

root.render(
  <ThemeProvider theme={{ colors: COLORS }}>
    <GlobalStyle />
    <React.StrictMode>
      <RouterProvider router={router} />
    </React.StrictMode>
  </ThemeProvider>
);
