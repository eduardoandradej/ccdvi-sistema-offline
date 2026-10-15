import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, get, post, put } from "../api";
import AttachmentsPanel from "../components/AttachmentsPanel";
import { Field, fmtDateTime, numOrNull, SelectInput, SpecSection, Tabs } from "../components/Fields";
import HistoryList from "../components/HistoryList";
import { EffectsEditor, MarksEditor } from "../components/ItemsEditors";
import { PM_SECTIONS } from "../formSpecs";
import { useSession } from "../session";
import type { PmCase } from "../types";

const MAIN_FIELDS = [
  "recovery_date", "recovery_place", "state_of_body", "sex", "sex_reason", "age_min_years", "age_max_years",
  "age_method", "height_min_cm", "height_max_cm", "weight_min_kg", "weight_max_kg", "build", "height_certainty",
  "category_status", "form_data", "status",
] as const;
type Draft = Pick<PmCase, (typeof MAIN_FIELDS)[number]>;

function toDraft(c: PmCase): Draft {
  return Object.fromEntries(MAIN_FIELDS.map((k) => [k, structuredClone(c[k])])) as Draft;
}

export function pmMissing(d: Draft, custody: number): string[] {
  const m: string[] = [];
  if (!d.state_of_body) m.push("Estado do corpo (402)");
  if (!d.sex) m.push("Sexo (535)");
  if (!d.recovery_date) m.push("Data de recuperação");
  if (custody < 1) m.push("Registro de recebimento na cadeia de custódia");
  return m;
}

export default function PmFormPage() {
  const { id } = useParams();
  const { vocab, can } = useSession();
  const v = vocab!;
  const canWrite = can("pm:write");
  const [c, setC] = useState<PmCase | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [dirty, setDirty] = useState(false);
  const [tab, setTab] = useState("reception");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [attCount, setAttCount] = useState(0);
  const [histKey, setHistKey] = useState(0);

  const load = useCallback(
    async (resetDraft: boolean) => {
      const data = await get<PmCase>(`/api/pm/${id}`);
      setC(data);
      if (resetDraft) {
        setDraft(toDraft(data));
        setDirty(false);
      }
      setHistKey((k) => k + 1);
    },
    [id],
  );

  useEffect(() => {
    load(true).catch((e) => setMsg({ ok: false, text: e.message }));
  }, [load]);

  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {
      if (dirty) e.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  if (!c || !draft) return <div className="muted">{msg?.text ?? "Carregando…"}</div>;

  const set = <K extends keyof Draft>(k: K, value: Draft[K]) => {
    setDraft({ ...draft, [k]: value });
    setDirty(true);
  };
  const setSection = (section: string) => (key: string, value: unknown) =>
    set("form_data", { ...draft.form_data, [section]: { ...(draft.form_data[section] ?? {}), [key]: value } });

  const save = async (status?: string) => {
    setMsg(null);
    try {
      const saved = await put<PmCase>(`/api/pm/${c.id}`, { ...draft, ...(status ? { status } : {}), expected_version: c.version });
      setC(saved);
      setDraft(toDraft(saved));
      setDirty(false);
      setHistKey((k) => k + 1);
      setMsg({ ok: true, text: `Gravado no banco de dados em ${fmtDateTime(saved.updated_at)} (versão ${saved.version}).` });
    } catch (e) {
      const conflict = e instanceof ApiError && e.status === 409;
      setMsg({ ok: false, text: (conflict ? "Conflito de edição: " : "Não foi gravado: ") + (e as Error).message });
    }
  };
  const onItemsChanged = () => load(false).catch((e) => setMsg({ ok: false, text: e.message }));
  const missing = pmMissing(draft, c.custody.length);
  const section = (s: string) => (
    <section key={s}>
      <h3>{PM_SECTIONS[s].title}</h3>
      <SpecSection disabled={!canWrite} specs={PM_SECTIONS[s].specs} values={draft.form_data[s] ?? {}} onChange={setSection(s)} />
    </section>
  );

  const tabs = [
    { key: "reception", label: "Recepção e identificadores" },
    { key: "findings", label: "Características/achados", badge: c.marks.length },
    { key: "exams", label: "Exames" },
    { key: "attachments", label: "Fotografias e anexos", badge: attCount },
    { key: "effects", label: "Pertences/evidências", badge: c.effects.filter((e) => e.field_code !== "515").length },
    { key: "custody", label: "Cadeia de custódia", badge: c.custody.length },
    { key: "history", label: "Histórico" },
  ];

  return (
    <div>
      <div className="breadcrumbs">
        <Link to="/pm">Post Mortem</Link> / {c.pm_number}
      </div>
      <div className="case-header">
        <div>
          <h1>{c.pm_number}</h1>
          <span className={`tag ${c.status === "RASCUNHO" ? "" : "info"}`}>{v.case_status[c.status]}</span>{" "}
          <span className="small muted">
            versão {c.version} · atualizado {fmtDateTime(c.updated_at)} · UUID {c.id}
          </span>
        </div>
        {canWrite && (
          <div className="savebar">
            {dirty && <span className="tag warn">alterações não gravadas</span>}
            <button onClick={() => save()} disabled={!dirty}>
              Salvar rascunho
            </button>
          </div>
        )}
      </div>
      <div className={`progress-box ${missing.length ? "" : "done"}`}>
        {missing.length ? (
          <>
            <strong>Pendências para “pronto para reconciliação”:</strong> {missing.join(" · ")}
          </>
        ) : (
          <>
            <strong>Campos mínimos preenchidos.</strong>
            {canWrite && c.status === "RASCUNHO" && (
              <button className="small-btn" onClick={() => save("PRONTO_RECONCILIACAO")}>
                Marcar como pronto para reconciliação
              </button>
            )}
          </>
        )}
      </div>
      {msg && <div className={`alert ${msg.ok ? "success" : "error"}`}>{msg.text}</div>}
      <Tabs tabs={tabs} active={tab} onChange={setTab} />
      <div className="tab-body">
        {tab === "reception" && (
          <>
            <div className="grid">
              <Field label="Número PM" code="Anexo 9">
                <input disabled value={c.pm_number} />
              </Field>
              <Field label="Data de recuperação" code="EXT">
                <input disabled={!canWrite} type="date" value={draft.recovery_date ?? ""} onChange={(e) => set("recovery_date", e.target.value || null)} />
              </Field>
              <Field label="Local de recuperação" code="EXT">
                <input disabled={!canWrite} value={draft.recovery_place ?? ""} onChange={(e) => set("recovery_place", e.target.value || null)} />
              </Field>
              <Field label="Estado do corpo" code="402">
                <SelectInput disabled={!canWrite} value={draft.state_of_body} options={v.state_of_body} onChange={(x) => set("state_of_body", x)} />
              </Field>
            </div>
            {section("reception")}
            {section("checklist")}
          </>
        )}
        {tab === "findings" && (
          <>
            <h3>Perfil biológico (observação PM)</h3>
            <div className="grid">
              <Field label="Sexo" code="535">
                <SelectInput disabled={!canWrite} value={draft.sex} options={v.pm_sex} onChange={(x) => set("sex", x)} />
              </Field>
              <Field label="Justificativa (sexo)" code="535">
                <input disabled={!canWrite} value={draft.sex_reason ?? ""} onChange={(e) => set("sex_reason", e.target.value || null)} />
              </Field>
              <Field label="Idade estimada mín. (anos)" code="540">
                <input disabled={!canWrite} type="number" value={draft.age_min_years ?? ""} onChange={(e) => set("age_min_years", numOrNull(e.target.value))} />
              </Field>
              <Field label="Idade estimada máx. (anos)" code="540">
                <input disabled={!canWrite} type="number" value={draft.age_max_years ?? ""} onChange={(e) => set("age_max_years", numOrNull(e.target.value))} />
              </Field>
              <Field label="Método de estimativa etária" code="540">
                <input disabled={!canWrite} value={draft.age_method ?? ""} onChange={(e) => set("age_method", e.target.value || null)} />
              </Field>
              <Field label="Estatura mín. (cm)" code="408">
                <input disabled={!canWrite} type="number" value={draft.height_min_cm ?? ""} onChange={(e) => set("height_min_cm", numOrNull(e.target.value))} />
              </Field>
              <Field label="Estatura máx. (cm)" code="408">
                <input disabled={!canWrite} type="number" value={draft.height_max_cm ?? ""} onChange={(e) => set("height_max_cm", numOrNull(e.target.value))} />
              </Field>
              <Field label="Confiabilidade da estatura" code="EXT">
                <SelectInput disabled={!canWrite} value={draft.height_certainty} options={v.certainty_pm} onChange={(x) => set("height_certainty", x)} />
              </Field>
              <Field label="Peso mín. (kg)" code="412">
                <input disabled={!canWrite} type="number" value={draft.weight_min_kg ?? ""} onChange={(e) => set("weight_min_kg", numOrNull(e.target.value))} />
              </Field>
              <Field label="Peso máx. (kg)" code="412">
                <input disabled={!canWrite} type="number" value={draft.weight_max_kg ?? ""} onChange={(e) => set("weight_max_kg", numOrNull(e.target.value))} />
              </Field>
              <Field label="Compleição" code="416">
                <SelectInput disabled={!canWrite} value={draft.build} options={v.build} onChange={(x) => set("build", x)} />
              </Field>
            </div>
            {section("body")}
            <MarksEditor
              kind="pm"
              caseId={c.id}
              marks={c.marks}
              categoryStatus={draft.category_status}
              onCategoryStatus={(k, x) => {
                const cs = { ...draft.category_status };
                if (x) cs[k] = x;
                else delete cs[k];
                set("category_status", cs);
              }}
              canWrite={canWrite}
              onChanged={onItemsChanged}
            />
          </>
        )}
        {tab === "exams" && (
          <>
            {section("fingerprint")}
            {section("dental")}
            {section("dna")}
            {section("pathology")}
            <EffectsEditor kind="pm" caseId={c.id} effects={c.effects} fields={["515"]} canWrite={canWrite} onChanged={onItemsChanged} title="Implantes (campo 515)" />
            {section("supporting")}
          </>
        )}
        {tab === "attachments" && <AttachmentsPanel kind="PM" caseId={c.id} canWrite={can("att_pm:write")} onCount={setAttCount} />}
        {tab === "effects" && (
          <EffectsEditor
            kind="pm"
            caseId={c.id}
            effects={c.effects}
            fields={["300", "305", "310", "315", "335", "340", "345", "350"]}
            canWrite={canWrite}
            onChanged={onItemsChanged}
            title="Vestimentas e pertences associados (campos 300–350)"
          />
        )}
        {tab === "custody" && <CustodyTab c={c} canWrite={canWrite} onChanged={onItemsChanged} />}
        {tab === "history" && <HistoryList url={`/api/pm/${c.id}/history`} refreshKey={histKey} />}
      </div>
    </div>
  );
}

function CustodyTab({ c, canWrite, onChanged }: { c: PmCase; canWrite: boolean; onChanged: () => void }) {
  const { vocab } = useSession();
  const v = vocab!;
  const empty = { event_type: "", occurred_at: "", location: "", responsible: "", notes: "" };
  const [form, setForm] = useState(empty);
  const [error, setError] = useState<string | null>(null);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await post(`/api/pm/${c.id}/custody`, {
        ...form,
        occurred_at: new Date(form.occurred_at).toISOString(),
        location: form.location || null,
        notes: form.notes || null,
      });
      setForm(empty);
      onChanged();
    } catch (err) {
      setError((err as Error).message);
    }
  };
  return (
    <div>
      <h3>
        Cadeia de custódia <span className="code ext">ext.</span>
      </h3>
      <p className="small muted">Eventos são somente-inclusão. Correções devem ser feitas registrando novo evento.</p>
      <table className="table">
        <thead>
          <tr>
            <th>Data/hora</th>
            <th>Evento</th>
            <th>Local</th>
            <th>Responsável</th>
            <th>Observações</th>
          </tr>
        </thead>
        <tbody>
          {c.custody.length === 0 && (
            <tr>
              <td colSpan={5} className="muted">
                Nenhum evento.
              </td>
            </tr>
          )}
          {c.custody.map((ev) => (
            <tr key={ev.id}>
              <td className="nowrap">{fmtDateTime(ev.occurred_at)}</td>
              <td>{v.custody_events[ev.event_type]}</td>
              <td>{ev.location}</td>
              <td>{ev.responsible}</td>
              <td className="small">{ev.notes}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {canWrite && (
        <form className="card" onSubmit={submit}>
          <div className="grid">
            <Field label="Evento">
              <SelectInput value={form.event_type} options={v.custody_events} empty="— selecione —" onChange={(x) => setForm({ ...form, event_type: x ?? "" })} />
            </Field>
            <Field label="Data/hora">
              <input type="datetime-local" value={form.occurred_at} onChange={(e) => setForm({ ...form, occurred_at: e.target.value })} />
            </Field>
            <Field label="Local">
              <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
            </Field>
            <Field label="Responsável">
              <input value={form.responsible} onChange={(e) => setForm({ ...form, responsible: e.target.value })} />
            </Field>
            <Field label="Observações" wide>
              <input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </Field>
          </div>
          <button type="submit" disabled={!form.event_type || !form.occurred_at || !form.responsible}>
            Registrar evento
          </button>
          {error && <div className="alert error">{error}</div>}
        </form>
      )}
    </div>
  );
}
