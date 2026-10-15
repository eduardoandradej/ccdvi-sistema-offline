import { useEffect, useState } from "react";
import { get } from "../api";
import type { HistoryEntry } from "../types";
import { fmtDateTime } from "./Fields";

export default function HistoryList({ url, refreshKey }: { url: string; refreshKey?: unknown }) {
  const [rows, setRows] = useState<HistoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    get<HistoryEntry[]>(url).then(setRows).catch((e) => setError(e.message));
  }, [url, refreshKey]);
  if (error) return <div className="alert error">{error}</div>;
  return (
    <div>
      <h3>Histórico / auditoria</h3>
      <table className="table">
        <thead>
          <tr>
            <th>Data/hora</th>
            <th>Usuário</th>
            <th>Função</th>
            <th>Ação</th>
            <th>Detalhes</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td className="nowrap">{fmtDateTime(r.occurred_at)}</td>
              <td>{r.username}</td>
              <td>{r.role}</td>
              <td>
                {r.action}
                {r.outcome !== "SUCESSO" && <span className="tag danger">{r.outcome}</span>}
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
