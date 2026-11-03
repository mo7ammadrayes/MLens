import type { Session } from "@supabase/supabase-js";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api/endpoints";
import type { User } from "../api/types";
import { supabase } from "../lib/supabase";

interface AuthContextValue {
  session: Session | null;
  /** Application user row from GET /users/me (created on first sign-in). */
  user: User | undefined;
  /** True until the initial session check finishes. */
  initializing: boolean;
  profileError: Error | undefined;
  /** Set after the user follows a password-reset email link. */
  passwordRecovery: boolean;
  clearPasswordRecovery: () => void;
  reloadProfile: () => void;
  setUser: (user: User) => void;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [user, setUser] = useState<User>();
  const [profileError, setProfileError] = useState<Error>();
  const [passwordRecovery, setPasswordRecovery] = useState(false);
  const [profileTick, setProfileTick] = useState(0);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setInitializing(false);
    });
    const { data } = supabase.auth.onAuthStateChange((event, next) => {
      setSession(next);
      if (event === "PASSWORD_RECOVERY") setPasswordRecovery(true);
      if (event === "SIGNED_OUT") setUser(undefined);
    });
    return () => data.subscription.unsubscribe();
  }, []);

  const userKey = session?.user.id;
  useEffect(() => {
    if (!userKey) return;
    let active = true;
    setProfileError(undefined);
    api.users
      .me()
      .then((me) => active && setUser(me))
      .catch((err: Error) => active && setProfileError(err));
    return () => {
      active = false;
    };
  }, [userKey, profileTick]);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    setUser(undefined);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        session,
        user,
        initializing,
        profileError,
        passwordRecovery,
        clearPasswordRecovery: () => setPasswordRecovery(false),
        reloadProfile: () => setProfileTick((t) => t + 1),
        setUser,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

// Pages only need the signed-in application user.
export function useUser() {
  return { user: useAuth().user };
}
