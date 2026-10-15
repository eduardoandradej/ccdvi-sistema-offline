import { useMemo, useState } from "react";
import { post, put } from "../api";
import { useSession } from "../session";
import type { AuthorizationInfo } from "../types";

/** Fluxo: operação → base → função. Só aparecem opções autorizadas; o servidor revalida. */
export default function ContextPage() {
  const { me, refresh } = useSession();
  const auths = me!.authorizations;
  const [search, setSearch] = useState("");
  const [opId, setOpId] = useState<string | null>(null);
  const [baseId, setBaseId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const operations = useMemo(() => {
    const map = new Map<string, AuthorizationInfo["operation"]>();
    auths.forEach((a) => map.set(a.operation.id, a.operation));
    return [...map.values()].filter((o) =>
      `${o.name} ${o.code}`.toLowerCase().includes(search.trim().toLowerCase()),
    );
  }, [auths, search]);
  const bases = useMemo(() => {
    const map = new Map<string, AuthorizationInfo["base"]>();
    auths.filter((a) => a.operation.id === opId).forEach((a) => map.set(a.base.id, a.base));
    return [...map.values()];
  }, [auths, opId]);
  const roles = auths.filter((a) => a.operation.id === opId && a.base.id === baseId);

  const choose = async (a: AuthorizationInfo) => {
    setError(null);
    try {
      await put("/api/auth/context", { operation_id: a.operation.id, base_id: a.base.id, role: a.role });
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const logout = async () => {
    await post("/api/auth/logout");
    await refresh();
  };

  return (
    <div className="login-wrap">
      <div className="card context-card">
        <div className="row between">
          <div>
            <h1>Selecionar contexto de trabalho</h1>
            <p className="muted">
              {me!.full_name}
              {me!.job_title ? ` · ${me!.job_title}` : ""}
            </p>
          </div>
          <button className="ghost" onClick={logout}>
            Sair
          </button>
        </div>
        {auths.length === 0 && (
          <div className="alert">Sua conta não possui autorização ativa em nenhuma operação. Procure a TIC.</div>
        )}
        <section>
          <h2>1. Operação / desastre</h2>
          <input placeholder="Buscar operação…" value={search} onChange={(e) => setSearch(e.target.value)} />
          <div className="choices">
            {operations.map((o) => (
              <button
                key={o.id}
                className={`choice ${opId === o.id ? "selected" : ""}`}
                onClick={() => {
                  setOpId(o.id);
                  setBaseId(null);
                }}
              >
                <strong>{o.name}</strong>
                <span className={`tag ${o.kind === "REAL" ? "danger" : "info"}`}>
                  {o.kind === "REAL" ? "OPERAÇÃO REAL" : "TREINAMENTO"}
                </span>
                {o.disaster_place && <span className="small muted">{o.disaster_place}</span>}
              </button>
            ))}
          </div>
        </section>
        {opId && (
          <section>
            <h2>2. Base / posto</h2>
            <div className="choices">
              {bases.map((b) => (
                <button
                  key={b.id}
                  className={`choice ${baseId === b.id ? "selected" : ""}`}
                  onClick={() => setBaseId(b.id)}
                >
                  <strong>{b.name}</strong>
                  <span className="small muted">{b.code}</span>
                </button>
              ))}
            </div>
          </section>
        )}
        {baseId && (
          <section>
            <h2>3. Função operacional</h2>
            <div className="choices">
              {roles.map((a) => (
                <button key={a.role} className="choice" onClick={() => choose(a)}>
                  <strong>{a.role_label}</strong>
                  <span className="small muted">{a.role}</span>
                </button>
              ))}
            </div>
          </section>
        )}
        {error && <div className="alert error">{error}</div>}
      </div>
    </div>
  );
}
