import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { get, put } from "../api";
import AttachmentsPanel from "../components/AttachmentsPanel";
import { Field, fmtDate, fmtDateTime, SelectInput } from "../components/Fields";
import { useSession } from "../session";
import type { AmCase, FieldResult, PmCase } from "../types";
import { REVIEW_STATUS } from "./ReconciliationPage";

interface CompareResponse {
  result: {
    am_number: string;
    pm_number: string;
    technical_index: number;
    coincidences: number;
    divergences: number;
    critical_divergences: number;
    missing: number;
    results: FieldResult[];
    algorithm_version: string;
    parameters: Record<string, unknown>;
    disclaimer: string;
  };
  am: AmCase;
  pm: PmCase;
  review: { status: string; notes: string | null; updated_at: string; technical_index: number; algorithm_version: string } | null;
}

const OUTCOME: Record<string, { label: string; cls: string }> = {
  COINCIDENTE: { label: "Coincidente", cls: "ok" },
  COMPATIVEL: { label: "Compatível", cls: "ok" },
  DIVERGENTE: { label: "Divergente", cls: "danger" },
  INCONCLUSIVO: { label: "Inconclusivo", cls: "warn" },
  SEM_DADOS: { label: "Não informado / sem dados", cls: "" },
  INFORMATIVO: { label: "Somente no PM", cls: "info" },
};

export default function ComparePage() {
  const [params] = useSearchParams();
  const amId = params.get("am")!;
  const pmId = params.get("pm")!;
  const { vocab, can, me } = useSession();
  const v = vocab!;
  const [data, setData] = useState<CompareResponse | null>(null);
  const [form, setForm] = useState({ status: "", notes: "" });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const load = useCallback(async () => {
    const d = await get<CompareResponse>(`/api/matching/compare?am_case_id=${amId}&pm_case_id=${pmId}`);
    setData(d);
    setForm({ status: d.review?.status ?? "", notes: d.review?.notes ?? "" });
  }, [amId, pmId]);

  useEffect(() => {
    load().catch((e) => setMsg({ ok: false, text: e.message }));
  }, [load]);

  if (!data) return <div className="muted">{msg?.text ?? "Carregando…"}</div>;
  const { result: r, am, pm } = data;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setMsg(null);
    try {
      await put("/api/matching/review", { am_case_id: am.id, pm_case_id: pm.id, status: form.status, notes: form.notes || null });
      setMsg({ ok: true, text: "Análise registrada (com versão do algoritmo, parâmetros e resultado no momento da revisão)." });
      load();
    } catch (err) {
      setMsg({ ok: false, text: (err as Error).message });
    }
  };

  return (
    <div className="compare">
      <div className="breadcrumbs no-print">
        <Link to={`/reconciliacao?am=${am.id}`}>Reconciliação</Link> / {am.am_number} × {pm.pm_number}
      </div>
      <div className="print-only print-header">
        <strong>DOCUMENTO DEMONSTRATIVO — NÃO É LAUDO OFICIAL</strong>
        <div>
          Relatório comparativo AM × PM gerado em {new Date().toLocaleString("pt-BR")} por {me!.full_name} ·{" "}
          {me!.context!.operation.name}
        </div>
      </div>
      <div className="row between">
        <h1>
          Comparação {am.am_number} × {pm.pm_number}
        </h1>
        <button className="ghost no-print" onClick={() => window.print()}>
          Imprimir relatório de apoio
        </button>
      </div>
      <div className="alert disclaimer">
        <strong>Não é identificação.</strong> {r.disclaimer} Algoritmo v{r.algorithm_version}. Identificadores primários
        (papiloscopia, odontologia e DNA) devem ser confrontados por especialistas; a decisão cabe ao Identification
        Board/autoridade competente.
      </div>

      <div className="split">
        <div className="panel am-side">
          <h3>AM · {am.am_number}</h3>
          <dl className="kv">
            <dt>Nome</dt>
            <dd>{[am.given_names, am.family_name].filter(Boolean).join(" ") || "—"}</dd>
            <dt>Sexo</dt>
            <dd>{am.sex ? v.am_sex[am.sex] : "—"}</dd>
            <dt>Nascimento / idade</dt>
            <dd>
              {fmtDate(am.date_of_birth)} {am.age_years != null && `· ${am.age_years} anos`}
            </dd>
            <dt>Estatura (relato)</dt>
            <dd>{am.height_min_cm ? `${am.height_min_cm}–${am.height_max_cm ?? am.height_min_cm} cm` : "—"}</dd>
            <dt>Entrevistas</dt>
            <dd>{am.interviews.length}</dd>
          </dl>
        </div>
        <div className="panel pm-side">
          <h3>PM · {pm.pm_number}</h3>
          <dl className="kv">
            <dt>Estado do corpo</dt>
            <dd>{pm.state_of_body ? v.state_of_body[pm.state_of_body] : "—"}</dd>
            <dt>Sexo (535)</dt>
            <dd>{pm.sex ? v.pm_sex[pm.sex] : "—"}</dd>
            <dt>Idade estimada (540)</dt>
            <dd>{pm.age_min_years != null ? `${pm.age_min_years}–${pm.age_max_years ?? "?"} anos` : "—"}</dd>
            <dt>Estatura estimada (408)</dt>
            <dd>{pm.height_min_cm ? `${pm.height_min_cm}–${pm.height_max_cm ?? pm.height_min_cm} cm` : "—"}</dd>
            <dt>Recuperação</dt>
            <dd>
              {fmtDate(pm.recovery_date)} {pm.recovery_place}
            </dd>
          </dl>
        </div>
      </div>

      <div className="summary-line">
        <span className="tag ok">{r.coincidences} coincidentes/compatíveis</span>
        <span className="tag danger">{r.divergences} divergentes</span>
        <span className="tag danger">{r.critical_divergences} divergências críticas</span>
        <span className="tag">{r.missing} sem dados</span>
        <span className="small muted">Índice técnico experimental (só ordenação): {r.technical_index}</span>
      </div>

      <table className="table compare-table">
        <thead>
          <tr>
            <th>Atributo</th>
            <th>Campo</th>
            <th>AM (relato)</th>
            <th>PM (observação)</th>
            <th>Resultado</th>
            <th>Explicação</th>
          </tr>
        </thead>
        <tbody>
          {r.results.map((f, i) => (
            <tr key={i} className={`outcome-${OUTCOME[f.outcome]?.cls}`}>
              <td>{f.attribute}</td>
              <td>
                <span className="code">{f.field_code}</span>
              </td>
              <td>{f.am_value ?? <span className="muted">não informado</span>}</td>
              <td>{f.pm_value ?? <span className="muted">não registrado</span>}</td>
              <td>
                <span className={`tag ${OUTCOME[f.outcome]?.cls}`}>{OUTCOME[f.outcome]?.label ?? f.outcome}</span>
                {f.critical && <span className="tag danger">crítica</span>}
              </td>
              <td className="small">{f.explanation}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="split no-print">
        <div className="panel">
          {can("att_am:read") ? (
            <AttachmentsPanel kind="AM" caseId={am.id} canWrite={false} />
          ) : (
            <p className="muted">Sem permissão para anexos AM.</p>
          )}
        </div>
        <div className="panel">
          {can("att_pm:read") ? (
            <AttachmentsPanel kind="PM" caseId={pm.id} canWrite={false} />
          ) : (
            <p className="muted">Sem permissão para anexos PM.</p>
          )}
        </div>
      </div>

      <div className="card">
        <h3>Análise humana do par</h3>
        {data.review && (
          <p className="small">
            Situação atual: <strong>{REVIEW_STATUS[data.review.status]}</strong> · atualizado em{" "}
            {fmtDateTime(data.review.updated_at)} · algoritmo v{data.review.algorithm_version}
            {data.review.notes && <> · “{data.review.notes}”</>}
          </p>
        )}
        {can("match:review") ? (
          <form onSubmit={submit} className="no-print">
            <div className="grid">
              <Field label="Encaminhamento">
                <SelectInput value={form.status} options={REVIEW_STATUS} empty="— selecione —" onChange={(x) => setForm({ ...form, status: x ?? "" })} />
              </Field>
              <Field label="Justificativa / pendências" wide>
                <textarea rows={3} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
              </Field>
            </div>
            <p className="small muted">
              Não existe opção de “identificação positiva”. A identificação formal ocorre fora deste sistema.
            </p>
            <button type="submit" disabled={!form.status}>
              Registrar análise
            </button>
          </form>
        ) : (
          <p className="muted">Sua função não permite registrar análise.</p>
        )}
        {msg && <div className={`alert ${msg.ok ? "success" : "error"}`}>{msg.text}</div>}
      </div>
    </div>
  );
}
