import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Studio } from "./studio";
import "../styles/globals.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Studio />
  </StrictMode>,
);
