import { FormEvent, useState } from "react";
import { post } from "../api";
import { useSession } from "../session";

export default function LoginPage() {
  const { refresh } = useSession();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await post("/api/auth/login", { username, password });
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <form className="card login" onSubmit={submit}>
        <h1>Sistema DVI Offline</h1>
        <p className="muted">CCDVI/SEPOL — apoio à identificação de vítimas de desastres</p>
        <label>
          Usuário
          <input autoFocus autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label>
          Senha
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <div className="alert error">{error}</div>}
        <button type="submit" disabled={busy || !username || !password}>
          {busy ? "Entrando…" : "Entrar"}
        </button>
        <p className="small muted">
          Uso demonstrativo com dados fictícios. Não é sistema homologado pela INTERPOL.
        </p>
      </form>
    </div>
  );
}
