import { createContext, useContext, useMemo } from "react";

import { useAuth } from "../lib/auth";
import { themes, themeForPermissions, type Theme } from "./tokens";

const ThemeContext = createContext<Theme>(themes.management);

/**
 * The palette follows the signed-in member's capabilities, exactly like the
 * website: floor staff get the management theme, kitchen and cashier stations
 * get the high-contrast operations theme.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { me } = useAuth();
  const theme = useMemo(
    () => (me ? themeForPermissions(me.membership.permissions) : themes.management),
    [me]
  );
  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}

export function useTheme(): Theme {
  return useContext(ThemeContext);
}
