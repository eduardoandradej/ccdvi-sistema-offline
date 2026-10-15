import { useEffect, useState } from "react";
import { get } from "../api";
import { fmtDateTime } from "../components/Fields";

interface Row {
  id: number;
  occurred_at: string;
  username: string | null;
  role: string | null;
  action: string;
  object_type: string | null;
  object_id: string | null;
  outcome: string;
  details: Record<string, unknown>;
  client_ip: string | null;
}

export default function AuditPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [filters, setFilters] = useState({ action: "", username: "", object_id: "" });
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const p = new URLSearchParams(Object.entries(filters).filter(([, v]) => v));
    const t = setTimeout(() => get<Row[]>(`/api/audit?${p}`).then(setRows).catch((e) => setError(e.message)), 250);
    return () => clearTimeout(t);
  }, [filters]);
  return (
    <div>
      <h1>Trilha de auditoria</h1>
      <p className="small muted">
        Registros somente-inclusão (o banco de dados bloqueia alteração e exclusão). Consulta sem alteração de conteúdo
        operacional.
      </p>
      <div className="row filters">
        <input placeholder="Ação (ex.: ANEXO_ENVIADO)" value={filters.action} onChange={(e) => setFilters({ ...filters, action: e.target.value.toUpperCase() })} />
        <input placeholder="Usuário" value={filters.username} onChange={(e) => setFilters({ ...filters, username: e.target.value })} />
        <input placeholder="ID do objeto" value={filters.object_id} onChange={(e) => setFilters({ ...filters, object_id: e.target.value })} />
      </div>
      {error && <div className="alert error">{error}</div>}
      <table className="table">
        <thead>
          <tr>
            <th>#</th>
            <th>Data/hora</th>
            <th>Usuário</th>
            <th>Função</th>
            <th>Ação</th>
            <th>Objeto</th>
            <th>Resultado</th>
            <th>Detalhes</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{r.id}</td>
              <td className="nowrap">{fmtDateTime(r.occurred_at)}</td>
              <td>{r.username ?? "—"}</td>
              <td>{r.role ?? "—"}</td>
              <td>{r.action}</td>
              <td className="small mono">
                {r.object_type} {r.object_id?.slice(0, 8)}
              </td>
              <td>
                <span className={`tag ${r.outcome === "SUCESSO" ? "ok" : "danger"}`}>{r.outcome}</span>
              </td>
              <td>
                <details>
                  <summary className="small">ver</summary>
                  <pre className="small">{JSON.stringify(r.details, null, 2)}</pre>
                </details>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
