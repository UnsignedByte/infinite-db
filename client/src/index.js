import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import Root from './pages/Root';
import Element from './pages/Element';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';

const root = ReactDOM.createRoot(document.getElementById('root'));

const router = createBrowserRouter([
  {
    path: '/',
    element: <Root />
  },
  {
    path: '/element/:text',
    element: <Element />
  }
])

root.render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);