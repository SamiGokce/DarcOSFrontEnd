import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { CpuProvider } from "./context/CpuContext.jsx";
import "./index.css"; // ✅ global styling
import './assets/base.css';


ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <CpuProvider>
        <App />
      </CpuProvider>
    </BrowserRouter>
  </React.StrictMode>
);
