import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { get } from "../api";
import type { CandidateSummary } from "../types";

export const REVIEW_STATUS: Record<string, string> = {
  SUGERIDO: "Sugerido",
  EM_ANALISE: "Em análise",
  INFORMACOES_COMPLEMENTARES: "Informações complementares necessárias",
  DESCARTADO: "Descartado",
  ENCAMINHADO_AVALIACAO_TECNICA: "Encaminhado à avaliação técnica",
};

interface Overview {
  algorithm_version: string;
  disclaimer: string;
  am_total: number;
  pm_total: number;
  rows: { am_case_id: string; am_number: string; name: string | null; status: string; candidates: number; top: CandidateSummary | null }[];
}

interface Candidates {
  algorithm_version: string;
  disclaimer: string;
  screened_out: number;
  screening_rule: string;
  candidates: CandidateSummary[];
}

export function CandidateBadges({ c }: { c: CandidateSummary }) {
  return (
    <span className="badges">
      <span className="tag ok">{c.coincidences} coincid./compat.</span>
      {c.divergences > 0 && <span className="tag warn">{c.divergences} diverg.</span>}
      {c.critical_divergences > 0 && <span className="tag danger">{c.critical_divergences} crítica(s)</span>}
      {c.missing > 0 && <span className="tag">{c.missing} sem dados</span>}
    </span>
  );
}

export default function ReconciliationPage() {
  const [params, setParams] = useSearchParams();
  const amId = params.get("am");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [cands, setCands] = useState<Candidates | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    get<Overview>("/api/matching/overview").then(setOverview).catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    if (!amId) return setCands(null);
    get<Candidates>(`/api/matching/candidates?am_case_id=${amId}&include_screened_out=${showAll}`)
      .then(setCands)
      .catch((e) => setError(e.message));
  }, [amId, showAll]);

  const am = overview?.rows.find((r) => r.am_case_id === amId);

  return (
    <div>
      <h1>Reconciliação AM × PM</h1>
      <div className="alert disclaimer">
        <strong>Instrumento de apoio.</strong> {overview?.disclaimer} Algoritmo v{overview?.algorithm_version}.
      </div>
      {error && <div className="alert error">{error}</div>}
      <div className="split">
        <div className="panel">
          <h3>
            Registros AM ({overview?.am_total ?? "…"}) · PM disponíveis: {overview?.pm_total ?? "…"}
          </h3>
          <table className="table selectable">
            <thead>
              <tr>
                <th>Nº AM</th>
                <th>Nome</th>
                <th>Melhor candidato para revisão</th>
              </tr>
            </thead>
            <tbody>
              {overview?.rows.map((r) => (
                <tr key={r.am_case_id} className={r.am_case_id === amId ? "selected" : ""} onClick={() => setParams({ am: r.am_case_id })}>
                  <td>{r.am_number}</td>
                  <td>{r.name ?? "—"}</td>
                  <td>
                    {r.top ? (
                      <>
                        {r.top.pm_number} <CandidateBadges c={r.top} />
                        {r.top.review_status && <span className="tag info">{REVIEW_STATUS[r.top.review_status]}</span>}
                      </>
                    ) : (
                      <span className="muted">nenhum</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="panel">
          {!cands && <p className="muted">Selecione um registro AM para ver os candidatos PM ordenados para revisão.</p>}
          {cands && am && (
            <>
              <h3>Candidatos PM para {am.am_number}</h3>
              <p className="small muted">
                {cands.screening_rule} Excluídos: {cands.screened_out}.{" "}
                <label className="check">
                  <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} /> mostrar
                  excluídos na triagem
                </label>
              </p>
              <table className="table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Nº PM</th>
                    <th>Resumo</th>
                    <th title="Índice técnico experimental — apenas ordenação, não é probabilidade">Índice técn.*</th>
                    <th>Revisão</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {cands.candidates.map((c, i) => (
                    <tr key={c.pm_case_id} className={c.critical_divergences ? "row-warn" : ""}>
                      <td>{i + 1}</td>
                      <td>{c.pm_number}</td>
                      <td>
                        <CandidateBadges c={c} />
                      </td>
                      <td>{c.technical_index}</td>
                      <td>{c.review_status ? REVIEW_STATUS[c.review_status] : <span className="muted">—</span>}</td>
                      <td>
                        <Link to={`/comparar?am=${c.am_case_id}&pm=${c.pm_case_id}`}>comparar lado a lado</Link>
                      </td>
                    </tr>
                  ))}
                  {cands.candidates.length === 0 && (
                    <tr>
                      <td colSpan={6} className="muted">
                        Nenhum candidato.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
              <p className="small muted">
                * Índice técnico experimental, não calibrado, usado só para ordenar a lista. Não representa probabilidade
                de identificação.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
