import { createRoot } from "react-dom/client";
import { useEffect, useMemo } from "react";

import { initializeOriginalHome } from "./original-home-behavior";
import { originalHomeMarkup } from "./original-home";
import "./styles.css";

function normalizedBase() {
  const base = import.meta.env.BASE_URL || "/";
  return base.endsWith("/") ? base : `${base}/`;
}

function applyInitialTheme() {
  const theme = new URLSearchParams(window.location.search).get("theme");
  document.body.dataset.theme = theme === "light" ? "light" : "dark";
}

function App() {
  const markup = useMemo(() => originalHomeMarkup.replaceAll("__LOOPX_BASE__", normalizedBase()), []);

  useEffect(() => {
    applyInitialTheme();
    initializeOriginalHome();
  }, []);

  return <div dangerouslySetInnerHTML={{ __html: markup }} />;
}

const root = document.getElementById("root");
if (!root) throw new Error("Root element not found");

createRoot(root).render(<App />);
