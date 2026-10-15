import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { ApiError, get } from "./api";
import type { Me, Vocab } from "./types";

interface SessionState {
  me: Me | null;
  vocab: Vocab | null;
  loading: boolean;
  refresh: () => Promise<Me | null>;
  can: (perm: string) => boolean;
}

const Ctx = createContext<SessionState | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [vocab, setVocab] = useState<Vocab | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const m = await get<Me>("/api/auth/me");
      setMe(m);
      if (!vocab) setVocab(await get<Vocab>("/api/vocab"));
      return m;
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setMe(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, [vocab]);

  useEffect(() => {
    refresh();
    const onUnauth = () => setMe(null);
    window.addEventListener("dvi:unauthorized", onUnauth);
    return () => window.removeEventListener("dvi:unauthorized", onUnauth);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const can = useCallback((perm: string) => !!me?.permissions.includes(perm), [me]);

  return <Ctx.Provider value={{ me, vocab, loading, refresh, can }}>{children}</Ctx.Provider>;
}

export function useSession(): SessionState {
  const s = useContext(Ctx);
  if (!s) throw new Error("SessionProvider ausente");
  return s;
}
