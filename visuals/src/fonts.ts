import { continueRender, delayRender, staticFile } from "remotion";

const GOOGLE_FONTS_CSS =
  "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Instrument+Serif:ital@0;1&display=swap";

let loaded = false;

export const loadFonts = () => {
  if (loaded) return;
  loaded = true;

  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = GOOGLE_FONTS_CSS;
  document.head.appendChild(link);
};
