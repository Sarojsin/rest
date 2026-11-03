/* ThemeProvider.tsx - Tier-based theming system
   Supports Basic (default), Professional, and Enterprise tiers
   Integrates with backend JWT tenant claims for persistent theming */
import { createContext, useContext, ReactNode, useEffect, useState } from "react";

type ThemeName = "customer" | "professional" | "enterprise" | "basic";

type ThemeContextProps = {
  theme: ThemeName;
  setTheme: (theme: ThemeName) => void;
};

const ThemeContext = createContext<ThemeContextProps | undefined>(undefined);

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
  // Check for saved theme preference or tier from backend JWT
  const [theme, setTheme] = useState<ThemeName>("customer");

  // Initialize theme from localStorage or default
  useEffect(() => {
    const saved = localStorage.getItem("app-theme");
    if (saved && ["customer", "professional", "enterprise", "basic"].includes(saved)) {
      setTheme(saved as ThemeName);
    } else {
      // Try to detect from user tier (would come from backend JWT)
      // For now default to customer for public pages, professional for staff
      const path = window.location.pathname;
      if (path.startsWith("/staff") || path.startsWith("/api")) {
        setTheme("professional");
      } else {
        setTheme("customer");
      }
    }
  }, []);

  // Persist theme change
  useEffect(() => {
    localStorage.setItem("app-theme", theme);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
};

/* CSS class names for theme switching */
export const themeClasses = {
  customer: "data-theme=\"customer\"",
  professional: "data-theme=\"professional\"",
  enterprise: "data-theme=\"enterprise\"",
  basic: "data-theme=\"basic\"",
};