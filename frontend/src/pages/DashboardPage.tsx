import { useEffect, useState } from "react";
import { get } from "../api";
import { useSession } from "../session";
import { REVIEW_STATUS } from "./ReconciliationPage";

interface Dash {
  am_by_status: Record<string, number>;
  pm_by_status: Record<string, number>;
  attachments: number;
  reviews_by_status: Record<string, number>;
}

export default function DashboardPage() {
  const { vocab } = useSession();
  const [d, setD] = useState<Dash | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    get<Dash>("/api/dashboard").then(setD).catch((e) => setError(e.message));
  }, []);
  if (error) return <div className="alert error">{error}</div>;
  if (!d) return <div className="muted">Carregando…</div>;
  const sum = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + b, 0);
  const block = (title: string, o: Record<string, number>, labels: Record<string, string>) => (
    <div className="stat">
      <span className="muted">{title}</span>
      <strong>{sum(o)}</strong>
      <ul className="small">
        {Object.entries(o).map(([k, n]) => (
          <li key={k}>
            {labels[k] ?? k}: {n}
          </li>
        ))}
      </ul>
    </div>
  );
  return (
    <div>
      <h1>Situação da operação</h1>
      <p className="small muted">Somente dados agregados. Esta função não acessa fichas, fotos ou documentos.</p>
      <div className="stats">
        {block("Registros AM", d.am_by_status, vocab!.case_status)}
        {block("Registros PM", d.pm_by_status, vocab!.case_status)}
        {block("Análises de pares AM×PM", d.reviews_by_status, REVIEW_STATUS)}
        <div className="stat">
          <span className="muted">Anexos armazenados</span>
          <strong>{d.attachments}</strong>
        </div>
      </div>
    </div>
  );
}
