import { Suspense } from "react";
import { createRoot } from "react-dom/client";
import "./css/globals.css";
import App from "./App";
import Spinner from "./views/spinner/Spinner";
import { ThemeProvider } from "./context/shadcntheme/ThemeContext";
import { AuthProvider } from "./context/auth/AuthContext";

async function startApp() {
  // Keep demo mocks opt-in so they never intercept real Kairos API requests by default.
  if (import.meta.env.DEV && import.meta.env.VITE_USE_MOCKS === "true") {
    const { worker } = await import("./api/mocks/browser");
    await worker.start({ onUnhandledRequest: "bypass" });
  }

  createRoot(document.getElementById("root")!).render(
    <AuthProvider>
      <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
        <Suspense fallback={<Spinner />}>
          <App />
        </Suspense>
      </ThemeProvider>
    </AuthProvider>,
  );
}

void startApp();
