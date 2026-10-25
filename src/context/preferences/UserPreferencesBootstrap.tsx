import { useEffect } from "react";
import { apiRequest } from "@/api/kairos-client";
import { useTheme, type Theme } from "@/context/shadcntheme/ThemeContext";

type Accent = "teal" | "blue" | "green" | "amber" | "rose" | "neutral";
type Preferences = {
  accent_color: Accent;
  font_size: "small" | "default" | "large" | "xlarge";
  interface_density: "compact" | "comfortable" | "spacious";
  theme_mode: Theme;
};

const accentTokens: Record<Accent, { primary: string; foreground: string; ring: string; sidebar: string }> = {
  teal: { primary: "oklch(0.48 0.09 190)", foreground: "oklch(0.99 0.01 190)", ring: "oklch(0.56 0.11 190)", sidebar: "oklch(0.48 0.09 190)" },
  blue: { primary: "oklch(0.49 0.19 258)", foreground: "oklch(0.99 0 0)", ring: "oklch(0.58 0.18 258)", sidebar: "oklch(0.49 0.19 258)" },
  green: { primary: "oklch(0.48 0.13 150)", foreground: "oklch(0.99 0 0)", ring: "oklch(0.58 0.14 150)", sidebar: "oklch(0.48 0.13 150)" },
  amber: { primary: "oklch(0.46 0.13 65)", foreground: "oklch(0.99 0 0)", ring: "oklch(0.55 0.14 65)", sidebar: "oklch(0.46 0.13 65)" },
  rose: { primary: "oklch(0.5 0.18 15)", foreground: "oklch(0.99 0 0)", ring: "oklch(0.6 0.18 15)", sidebar: "oklch(0.5 0.18 15)" },
  neutral: { primary: "oklch(0.32 0 0)", foreground: "oklch(0.99 0 0)", ring: "oklch(0.48 0 0)", sidebar: "oklch(0.32 0 0)" },
};

function applyPreferences(preferences: Preferences) {
  const root = document.documentElement;
  const token = accentTokens[preferences.accent_color];
  root.style.setProperty("--primary", token.primary);
  root.style.setProperty("--primary-foreground", token.foreground);
  root.style.setProperty("--ring", token.ring);
  root.style.setProperty("--sidebar-primary", token.sidebar);
  root.style.setProperty("--sidebar-primary-foreground", token.foreground);
  root.dataset.kairosAccent = preferences.accent_color;
  root.dataset.kairosFontSize = preferences.font_size;
  root.dataset.kairosDensity = preferences.interface_density;
}

export default function UserPreferencesBootstrap() {
  const { setTheme } = useTheme();

  useEffect(() => {
    let active = true;
    apiRequest<Preferences>("/users/me/preferences")
      .then((preferences) => {
        if (!active) return;
        if (!preferences || !accentTokens[preferences.accent_color]) return;
        applyPreferences(preferences);
        setTheme(preferences.theme_mode);
        try {
          localStorage.setItem("kairos.preferences.cache", JSON.stringify(preferences));
        } catch {
          // Account preferences are stored on the server; this cache is only an optional bootstrap.
        }
      })
      .catch(() => {
        // Public and signed-out routes may not have an authenticated preferences endpoint.
      });
    return () => { active = false; };
  }, [setTheme]);

  return null;
}
