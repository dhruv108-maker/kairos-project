import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  clearAccessToken,
  getAccessToken,
  getCurrentAccount,
  refreshSession,
  subscribeToSessionLogout,
  signIn,
  signOut,
  type KairosAccount,
} from "@/api/kairos-client";

interface AuthContextValue {
  account: KairosAccount | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<KairosAccount>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<KairosAccount | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const restore = async () => {
      try {
        // The HttpOnly refresh cookie survives reloads; recover an access token
        // when sessionStorage is empty or the previous access token has expired.
        if (!getAccessToken()) await refreshSession();
        if (!getAccessToken()) return;
        const currentAccount = await getCurrentAccount();
        if (active) setAccount(currentAccount);
      } catch {
        clearAccessToken();
        if (active) setAccount(null);
      } finally {
        if (active) setIsLoading(false);
      }
    };
    void restore();
    const unsubscribe = subscribeToSessionLogout(() => {
      if (active) setAccount(null);
    });
    return () => {
      active = false;
      unsubscribe();
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await signIn(email, password);
    setAccount(response.account);
    return response.account;
  }, []);

  const logout = useCallback(() => {
    signOut();
    setAccount(null);
  }, []);

  const value = useMemo(() => ({ account, isLoading, login, logout }), [account, isLoading, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}
