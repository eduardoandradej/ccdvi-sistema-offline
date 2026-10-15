import { FormEvent, useCallback, useEffect, useState } from "react";
import { get, post } from "../api";
import { Field, SelectInput } from "../components/Fields";
import { useSession } from "../session";

interface UserRow {
  id: string;
  username: string;
  full_name: string;
  job_title: string | null;
  active: boolean;
  authorizations: { id: string; base: string; role: string; active: boolean }[];
}

interface Health {
  database: { ok: boolean; version: string };
  storage: { path: string; free_bytes: number; total_bytes: number };
  max_upload_mb: number;
}

export default function AdminPage() {
  const { can, vocab } = useSession();
  const [health, setHealth] = useState<Health | null>(null);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [bases, setBases] = useState<Record<string, string>>({});
  const [nu, setNu] = useState({ username: "", full_name: "", job_title: "", password: "" });
  const [grant, setGrant] = useState({ user_id: "", base_id: "", role: "" });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const load = useCallback(async () => {
    if (can("admin:health")) setHealth(await get<Health>("/api/admin/health"));
    if (can("admin:users")) {
      setUsers(await get<UserRow[]>("/api/admin/users"));
      const b = await get<{ id: string; name: string }[]>("/api/admin/bases");
      setBases(Object.fromEntries(b.map((x) => [x.id, x.name])));
    }
  }, [can]);
  useEffect(() => {
    load().catch((e) => setMsg({ ok: false, text: e.message }));
  }, [load]);

  if (!can("admin:users") && !can("admin:health")) {
    return <div className="alert error">Sua função ativa não permite acessar esta tela.</div>;
  }
  const act = async (fn: () => Promise<unknown>, ok: string) => {
    setMsg(null);
    try {
      await fn();
      setMsg({ ok: true, text: ok });
      load();
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    }
  };
  const createUser = (e: FormEvent) => {
    e.preventDefault();
    act(() => post("/api/admin/users", { ...nu, job_title: nu.job_title || null }), "Usuário criado.").then(() =>
      setNu({ username: "", full_name: "", job_title: "", password: "" }),
    );
  };
  const doGrant = (e: FormEvent) => {
    e.preventDefault();
    act(() => post("/api/admin/authorizations", grant), "Autorização concedida.");
  };

  return (
    <div>
      <h1>Administração TIC</h1>
      <p className="small muted">Administração de infraestrutura e contas, sem acesso ao conteúdo sensível dos casos.</p>
      {msg && <div className={`alert ${msg.ok ? "success" : "error"}`}>{msg.text}</div>}
      {health && (
        <div className="stats">
          <div className="stat">
            <span className="muted">Banco de dados</span>
            <strong>{health.database.ok ? "OK" : "Falha"}</strong>
            <span className="small">{health.database.version.split(" on ")[0]}</span>
          </div>
          <div className="stat">
            <span className="muted">Armazenamento de anexos</span>
            <strong>{(health.storage.free_bytes / 1024 ** 3).toFixed(1)} GB livres</strong>
            <span className="small mono">{health.storage.path}</span>
          </div>
          <div className="stat">
            <span className="muted">Limite de upload</span>
            <strong>{health.max_upload_mb} MB</strong>
          </div>
        </div>
      )}
      {can("admin:users") && (
        <>
          <h3>Usuários e autorizações nesta operação</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Usuário</th>
                <th>Nome</th>
                <th>Autorizações</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.username}</td>
                  <td>
                    {u.full_name}
                    {u.job_title && <div className="small muted">{u.job_title}</div>}
                  </td>
                  <td>
                    {u.authorizations.map((a) => (
                      <div key={a.id} className="small">
                        {a.base} · {vocab!.roles[a.role]}{" "}
                        {a.active ? (
                          <button className="link danger" onClick={() => act(() => post(`/api/admin/authorizations/${a.id}/revoke`), "Autorização revogada.")}>
                            revogar
                          </button>
                        ) : (
                          <span className="tag">revogada</span>
                        )}
                      </div>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="split">
            <form className="card" onSubmit={createUser}>
              <h4>Novo usuário</h4>
              <Field label="Usuário (minúsculas)">
                <input value={nu.username} onChange={(e) => setNu({ ...nu, username: e.target.value })} />
              </Field>
              <Field label="Nome completo">
                <input value={nu.full_name} onChange={(e) => setNu({ ...nu, full_name: e.target.value })} />
              </Field>
              <Field label="Cargo">
                <input value={nu.job_title} onChange={(e) => setNu({ ...nu, job_title: e.target.value })} />
              </Field>
              <Field label="Senha inicial (mín. 10 caracteres)">
                <input type="password" value={nu.password} onChange={(e) => setNu({ ...nu, password: e.target.value })} />
              </Field>
              <button type="submit">Criar usuário</button>
            </form>
            <form className="card" onSubmit={doGrant}>
              <h4>Conceder autorização</h4>
              <Field label="Usuário">
                <SelectInput value={grant.user_id} options={Object.fromEntries(users.map((u) => [u.id, u.username]))} empty="— selecione —" onChange={(x) => setGrant({ ...grant, user_id: x ?? "" })} />
              </Field>
              <Field label="Base">
                <SelectInput value={grant.base_id} options={bases} empty="— selecione —" onChange={(x) => setGrant({ ...grant, base_id: x ?? "" })} />
              </Field>
              <Field label="Função">
                <SelectInput value={grant.role} options={vocab!.roles} empty="— selecione —" onChange={(x) => setGrant({ ...grant, role: x ?? "" })} />
              </Field>
              <button type="submit" disabled={!grant.user_id || !grant.base_id || !grant.role}>
                Conceder
              </button>
            </form>
          </div>
        </>
      )}
    </div>
  );
}
