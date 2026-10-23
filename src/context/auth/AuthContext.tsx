import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  clearAccessToken,
  getAccessToken,
  getCurrentAccount,
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
    if (!getAccessToken()) {
      setIsLoading(false);
      return () => { active = false; };
    }

    getCurrentAccount()
      .then((currentAccount) => {
        if (active) setAccount(currentAccount);
      })
      .catch(() => {
        clearAccessToken();
        if (active) setAccount(null);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => { active = false; };
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
