import { useEffect, useState } from "react";

function readIsDark(): boolean {
  if (typeof document === "undefined") {
    return false;
  }
  return document.documentElement.classList.contains("dark");
}

function resolvePreferredDark(): boolean {
  try {
    const stored = localStorage.getItem("theme");
    if (stored === "dark") {
      return true;
    }
    if (stored === "light") {
      return false;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  } catch {
    return false;
  }
}

function applyTheme(isDark: boolean): void {
  document.documentElement.classList.toggle("dark", isDark);
}

export function useDarkMode(): [boolean, () => void] {
  const [isDark, setIsDark] = useState<boolean>(readIsDark);

  useEffect(() => {
    const dark = resolvePreferredDark();
    applyTheme(dark);
    setIsDark(dark);
  }, []);

  const toggle = () => {
    setIsDark((previous) => {
      const next = !previous;
      applyTheme(next);
      localStorage.setItem("theme", next ? "dark" : "light");
      return next;
    });
  };

  return [isDark, toggle];
}
