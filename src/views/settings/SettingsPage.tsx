import { useCallback, useEffect, useMemo, useState } from "react";
import { Check, CircleAlert, Laptop, Moon, Palette, RotateCcw, Settings2, Sun, Type } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { useAuth } from "@/context/auth/AuthContext";
import { useTheme, type Theme } from "@/context/shadcntheme/ThemeContext";
import { apiRequest } from "@/api/kairos-client";

type Accent = "teal" | "blue" | "green" | "amber" | "rose" | "neutral";
type FontScale = "small" | "default" | "large" | "xlarge";
type Density = "compact" | "comfortable" | "spacious";
type ThemeMode = Theme;

type Preferences = {
  accent_color: Accent;
  font_size: FontScale;
  interface_density: Density;
  theme_mode: ThemeMode;
  email_notifications_enabled: boolean;
  notification_preferences: Record<string, boolean>;
  updated_at?: string | null;
};

const defaults: Preferences = {
  accent_color: "teal",
  font_size: "default",
  interface_density: "comfortable",
  theme_mode: "system",
  email_notifications_enabled: true,
  notification_preferences: {},
};
const accents: Array<{ value: Accent; label: string; color: string; detail: string }> = [
  { value: "teal", label: "Kairos Teal", color: "#0f766e", detail: "Brand default" },
  { value: "blue", label: "Blue", color: "#2563eb", detail: "Cool and focused" },
  { value: "green", label: "Green", color: "#15803d", detail: "Natural and calm" },
  { value: "amber", label: "Amber", color: "#b45309", detail: "Warm highlight" },
  { value: "rose", label: "Rose", color: "#be123c", detail: "Soft contrast" },
  { value: "neutral", label: "Monochrome", color: "#525252", detail: "Neutral" },
];
const fontOptions: Array<{ value: FontScale; label: string; example: string }> = [
  { value: "small", label: "Small", example: "Compact text" },
  { value: "default", label: "Default", example: "Recommended" },
  { value: "large", label: "Large", example: "Larger reading" },
  { value: "xlarge", label: "Extra large", example: "Maximum text" },
];
const densityOptions: Array<{ value: Density; label: string; detail: string }> = [
  { value: "compact", label: "Compact", detail: "Less spacing, more content" },
  { value: "comfortable", label: "Comfortable", detail: "Balanced everyday layout" },
  { value: "spacious", label: "Spacious", detail: "More room between elements" },
];
const categories = [
  { key: "internship_updates", label: "Internship updates", description: "Placement and internship workflow changes" },
  { key: "work_log_reviews", label: "Work-log reviews", description: "Review results and requested revisions" },
  { key: "report_updates", label: "Reports and feedback", description: "Report review and mentor feedback" },
  { key: "recruitment_updates", label: "Recruitment updates", description: "Job applications and recruitment activity" },
  { key: "account_security", label: "Account and security", description: "Important account and security communication" },
];

function applyAccent(value: Accent) {
  const root = document.documentElement;
  const tokens: Record<Accent, { primary: string; foreground: string; ring: string; sidebar: string }> = {
    teal: { primary: "oklch(0.48 0.09 190)", foreground: "oklch(0.99 0.01 190)", ring: "oklch(0.56 0.11 190)", sidebar: "oklch(0.48 0.09 190)" },
    blue: { primary: "oklch(0.49 0.19 258)", foreground: "oklch(0.99 0 0)", ring: "oklch(0.58 0.18 258)", sidebar: "oklch(0.49 0.19 258)" },
    green: { primary: "oklch(0.48 0.13 150)", foreground: "oklch(0.99 0 0)", ring: "oklch(0.58 0.14 150)", sidebar: "oklch(0.48 0.13 150)" },
    amber: { primary: "oklch(0.57 0.14 65)", foreground: "oklch(0.99 0 0)", ring: "oklch(0.65 0.14 65)", sidebar: "oklch(0.57 0.14 65)" },
    rose: { primary: "oklch(0.5 0.18 15)", foreground: "oklch(0.99 0 0)", ring: "oklch(0.6 0.18 15)", sidebar: "oklch(0.5 0.18 15)" },
    neutral: { primary: "oklch(0.32 0 0)", foreground: "oklch(0.99 0 0)", ring: "oklch(0.48 0 0)", sidebar: "oklch(0.32 0 0)" },
  };
  const token = tokens[value];
  root.style.setProperty("--primary", token.primary);
  root.style.setProperty("--primary-foreground", token.foreground);
  root.style.setProperty("--ring", token.ring);
  root.style.setProperty("--sidebar-primary", token.sidebar);
  root.style.setProperty("--sidebar-primary-foreground", token.foreground);
  root.dataset.kairosAccent = value;
}
function applyTypography(value: FontScale) {
  const sizes: Record<FontScale, string> = { small: "14px", default: "16px", large: "18px", xlarge: "20px" };
  document.documentElement.style.setProperty("--kairos-font-size", sizes[value]);
  document.documentElement.dataset.kairosFontSize = value;
}
function applyDensity(value: Density) {
  const spacing: Record<Density, string> = { compact: "0.75", comfortable: "1", spacious: "1.25" };
  document.documentElement.style.setProperty("--kairos-density", spacing[value]);
  document.documentElement.dataset.kairosDensity = value;
}

export default function SettingsPage() {
  const { account } = useAuth();
  const { theme, setTheme } = useTheme();
  const [preferences, setPreferences] = useState<Preferences>(defaults);
  const [initialPreferences, setInitialPreferences] = useState<Preferences>(defaults);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [apiAvailable, setApiAvailable] = useState(true);

  const applyVisualPreferences = useCallback((next: Preferences) => {
    applyAccent(next.accent_color);
    applyTypography(next.font_size);
    applyDensity(next.interface_density);
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    apiRequest<Preferences>("/users/me/preferences")
      .then((loaded) => {
        if (!active) return;
        const merged = { ...defaults, ...loaded, notification_preferences: loaded.notification_preferences || {} };
        setPreferences(merged);
        setInitialPreferences(merged);
        setApiAvailable(true);
        applyVisualPreferences(merged);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setApiAvailable(false);
        setError(err instanceof Error ? err.message : "Could not load your saved preferences.");
        // Do not represent failed API loads as saved defaults. Use defaults only for this session.
        setPreferences(defaults);
        setInitialPreferences(defaults);
        applyVisualPreferences(defaults);
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [applyVisualPreferences]);

  useEffect(() => {
    setTheme(preferences.theme_mode);
  }, [preferences.theme_mode, setTheme]);

  const dirty = useMemo(() => JSON.stringify(preferences) !== JSON.stringify(initialPreferences), [preferences, initialPreferences]);

  const patchPreference = <K extends keyof Preferences>(key: K, value: Preferences[K]) => {
    setPreferences((current) => {
      const next = { ...current, [key]: value };
      applyVisualPreferences(next);
      if (key === "theme_mode") setTheme(value as ThemeMode);
      return next;
    });
    setNotice("");
  };

  const save = async (next = preferences) => {
    setSaving(true); setError(""); setNotice("");
    try {
      const saved = await apiRequest<Preferences>("/users/me/preferences", {
        method: "PATCH",
        body: JSON.stringify({
          accent_color: next.accent_color,
          font_size: next.font_size,
          interface_density: next.interface_density,
          theme_mode: next.theme_mode,
          email_notifications_enabled: next.email_notifications_enabled,
          notification_preferences: next.notification_preferences,
        }),
      });
      const merged = { ...defaults, ...saved, notification_preferences: saved.notification_preferences || {} };
      setPreferences(merged);
      setInitialPreferences(merged);
      setApiAvailable(true);
      applyVisualPreferences(merged);
      setTheme(merged.theme_mode);
      setNotice("Settings saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Settings could not be saved. Your saved preferences were not changed.");
      // Restore the most recently confirmed server values after a rejected save.
      setPreferences(initialPreferences);
      applyVisualPreferences(initialPreferences);
      setTheme(initialPreferences.theme_mode);
    } finally {
      setSaving(false);
    }
  };

  const reset = async () => {
    const next = { ...defaults, notification_preferences: {} };
    setPreferences(next);
    applyVisualPreferences(next);
    setTheme(next.theme_mode);
    await save(next);
  };

  const updateCategory = (key: string, checked: boolean) => {
    setPreferences((current) => ({ ...current, notification_preferences: { ...current.notification_preferences, [key]: checked } }));
    setNotice("");
  };

  if (loading) {
    return <main className="mx-auto w-full max-w-5xl space-y-6 py-4"><Skeleton className="h-10 w-64" /><Skeleton className="h-4 w-96 max-w-full" /><div className="grid gap-4 lg:grid-cols-2"><Skeleton className="h-64" /><Skeleton className="h-64" /><Skeleton className="h-72 lg:col-span-2" /></div></main>;
  }

  return (
    <main className="mx-auto w-full max-w-5xl space-y-6 py-3">
      <header className="space-y-1">
        <div className="flex items-center gap-2 text-sm text-muted-foreground"><Settings2 className="size-4" /> Personal preferences</div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Settings</h1>
        <p className="text-sm text-muted-foreground">Make Kairos work the way you do.</p>
      </header>

      {error && <Alert variant="destructive"><CircleAlert className="size-4" /><AlertTitle>Something needs attention</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
      {notice && <Alert><Check className="size-4" /><AlertTitle>Saved</AlertTitle><AlertDescription>{notice}</AlertDescription></Alert>}
      {!apiAvailable && <Alert><CircleAlert className="size-4" /><AlertTitle>Preferences service unavailable</AlertTitle><AlertDescription>Visual changes preview in this session, but they cannot be saved until the settings API is available.</AlertDescription></Alert>}

      <div className="grid gap-5">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2"><Palette className="size-5 text-primary" /><CardTitle>Appearance</CardTitle></div>
            <CardDescription>Choose the accent used by shared controls and active states.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <RadioGroup value={preferences.accent_color} onValueChange={(value) => patchPreference("accent_color", value as Accent)} className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {accents.map((accent) => (
                <label key={accent.value} htmlFor={`accent-${accent.value}`} className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors hover:bg-muted/50 ${preferences.accent_color === accent.value ? "border-primary bg-primary/5 ring-1 ring-primary/30" : "border-border"}`}>
                  <RadioGroupItem id={`accent-${accent.value}`} value={accent.value} />
                  <span className="size-7 shrink-0 rounded-full border border-black/10" style={{ backgroundColor: accent.color }} aria-hidden="true" />
                  <span className="min-w-0"><span className="block text-sm font-medium">{accent.label}</span><span className="block text-xs text-muted-foreground">{accent.detail}</span></span>
                  {preferences.accent_color === accent.value && <Check className="ml-auto size-4 shrink-0 text-primary" aria-label="Selected" />}
                </label>
              ))}
            </RadioGroup>
            <Separator />
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div><Label className="text-sm font-medium">Theme mode</Label><p className="text-xs text-muted-foreground">Light, dark, or follow your device.</p></div>
              <RadioGroup value={preferences.theme_mode} onValueChange={(value) => patchPreference("theme_mode", value as ThemeMode)} className="flex flex-wrap gap-2">
                {([{ value: "light", label: "Light", icon: Sun }, { value: "dark", label: "Dark", icon: Moon }, { value: "system", label: "System", icon: Laptop }] as const).map((option) => <label key={option.value} htmlFor={`theme-${option.value}`} className={`flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm ${preferences.theme_mode === option.value ? "border-primary bg-primary/5" : "border-border"}`}><RadioGroupItem id={`theme-${option.value}`} value={option.value} /><option.icon className="size-4" /><span>{option.label}</span></label>)}
              </RadioGroup>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2"><Type className="size-5 text-primary" /><CardTitle>Typography & accessibility</CardTitle></div>
            <CardDescription>Adjust text size independently from your browser zoom.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <RadioGroup value={preferences.font_size} onValueChange={(value) => patchPreference("font_size", value as FontScale)} className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {fontOptions.map((option) => <label key={option.value} htmlFor={`font-${option.value}`} className={`cursor-pointer rounded-lg border p-3 ${preferences.font_size === option.value ? "border-primary bg-primary/5" : "border-border"}`}><span className="flex items-center gap-2"><RadioGroupItem id={`font-${option.value}`} value={option.value} /><span className="font-medium">{option.label}</span></span><span className="mt-2 block text-xs text-muted-foreground">{option.example}</span></label>)}
            </RadioGroup>
            <Separator />
            <div className="space-y-3">
              <div><Label className="text-sm font-medium">Interface density</Label><p className="text-xs text-muted-foreground">Controls spacing and padding—not browser zoom.</p></div>
              <RadioGroup value={preferences.interface_density} onValueChange={(value) => patchPreference("interface_density", value as Density)} className="grid gap-3 sm:grid-cols-3">
                {densityOptions.map((option) => <label key={option.value} htmlFor={`density-${option.value}`} className={`cursor-pointer rounded-lg border p-3 ${preferences.interface_density === option.value ? "border-primary bg-primary/5" : "border-border"}`}><span className="flex items-center gap-2"><RadioGroupItem id={`density-${option.value}`} value={option.value} /><span className="font-medium text-sm">{option.label}</span></span><span className="mt-1.5 block text-xs text-muted-foreground">{option.detail}</span></label>)}
              </RadioGroup>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2"><Laptop className="size-5 text-primary" /><CardTitle>Notifications & email alerts</CardTitle></div>
            <CardDescription>Account email: {account?.email || "Unavailable"} · {account?.is_verified ? "Verified" : "Not verified"}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <CircleAlert className="size-4" />
              <AlertTitle>Delivery preferences aren't connected yet</AlertTitle>
              <AlertDescription>The current backend has transactional email for verification, password reset, and invitations, but no general notification queue or email-preference enforcement. These controls are shown as unavailable until that pipeline exists.</AlertDescription>
            </Alert>
            <div className="flex items-center justify-between gap-4 rounded-lg border p-4">
              <div><p className="font-medium text-sm">Optional email updates</p><p className="text-xs text-muted-foreground">Does not affect verification, password reset, or security-critical messages.</p></div>
              <Switch checked={preferences.email_notifications_enabled} onCheckedChange={(checked) => patchPreference("email_notifications_enabled", checked)} disabled aria-label="Optional email updates (not yet supported)" />
            </div>
            {categories.map((category) => (
              <div key={category.key} className="flex items-center justify-between gap-4 border-b pb-3 last:border-b-0">
                <div><p className="font-medium text-sm">{category.label}</p><p className="text-xs text-muted-foreground">{category.description} · Not yet supported by the delivery service</p></div>
                <Switch checked={Boolean(preferences.notification_preferences[category.key])} onCheckedChange={(checked) => updateCategory(category.key, checked)} disabled aria-label={category.label + " notifications (not yet supported)"} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Account & preferences</CardTitle><CardDescription>Personal settings apply to your Kairos account. They don't change institution or platform settings.</CardDescription></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between"><span className="text-sm font-medium">Signed in as</span><span className="text-sm text-muted-foreground break-all">{account?.full_name} · {account?.email}</span></div>
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between"><span className="text-sm font-medium">Email verification</span><Badge variant={account?.is_verified ? "secondary" : "outline"}>{account?.is_verified ? "Verified" : "Verification required"}</Badge></div>
            <Separator />
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-between">
              <Button type="button" variant="outline" onClick={() => void reset()} disabled={!apiAvailable || saving}><RotateCcw className="mr-2 size-4" />Reset preferences</Button>
              <Button type="button" onClick={() => void save()} disabled={!apiAvailable || saving || !dirty}>{saving ? "Saving…" : "Save preferences"}</Button>
            </div>
            <p className="text-xs text-muted-foreground">Appearance changes preview immediately. Save preferences to keep them across devices.</p>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
