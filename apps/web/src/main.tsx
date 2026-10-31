import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { BRAND_NAME } from "./lib/brand";
import "./styles/index.css";

// The static <title> is a placeholder; keep it aligned with VITE_BRAND_NAME.
document.title = BRAND_NAME;

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
