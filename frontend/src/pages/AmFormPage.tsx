import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, get, post, put } from "../api";
import AttachmentsPanel from "../components/AttachmentsPanel";
import { Field, fmtDate, fmtDateTime, numOrNull, SelectInput, SpecSection, Tabs } from "../components/Fields";
import HistoryList from "../components/HistoryList";
import { EffectsEditor, MarksEditor } from "../components/ItemsEditors";
import { AM_SECTIONS } from "../formSpecs";
import { useSession } from "../session";
import type { AmCase, Interview } from "../types";

const MAIN_FIELDS = [
  "family_name", "given_names", "sex", "date_of_birth", "age_years", "height_min_cm", "height_max_cm",
  "weight_min_kg", "weight_max_kg", "build", "height_certainty", "category_status", "form_data", "status",
] as const;
type Draft = Pick<AmCase, (typeof MAIN_FIELDS)[number]>;

function toDraft(c: AmCase): Draft {
  return Object.fromEntries(MAIN_FIELDS.map((k) => [k, structuredClone(c[k])])) as Draft;
}

export function amMissing(d: Draft, interviews: number): string[] {
  const m: string[] = [];
  if (!d.family_name) m.push("Sobrenome");
  if (!d.given_names) m.push("Nome(s)");
  if (!d.sex) m.push("Sexo");
  if (!d.date_of_birth && d.age_years == null) m.push("Data de nascimento ou idade");
  if (interviews < 1) m.push("Ao menos uma entrevista/fonte");
  return m;
}

export default function AmFormPage() {
  const { id } = useParams();
  const { vocab, can } = useSession();
  const v = vocab!;
  const canWrite = can("am:write");
  const [c, setC] = useState<AmCase | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [dirty, setDirty] = useState(false);
  const [tab, setTab] = useState("ident");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [attCount, setAttCount] = useState(0);
  const [histKey, setHistKey] = useState(0);

  const load = useCallback(
    async (resetDraft: boolean) => {
      const data = await get<AmCase>(`/api/am/${id}`);
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
  const setSection = (section: string) => (key: string, value: unknown) => {
    const fd = { ...draft.form_data, [section]: { ...(draft.form_data[section] ?? {}), [key]: value } };
    set("form_data", fd);
  };

  const save = async (status?: string) => {
    setMsg(null);
    try {
      const body = { ...draft, ...(status ? { status } : {}), expected_version: c.version };
      const saved = await put<AmCase>(`/api/am/${c.id}`, body);
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

  // Itens (sinais, objetos, entrevistas) são gravados imediatamente; atualiza só a versão e as listas.
  // O rascunho em edição é mantido; apenas a versão e as listas vêm do servidor.
  const onItemsChanged = () => load(false).catch((e) => setMsg({ ok: false, text: e.message }));

  const missing = amMissing(draft, c.interviews.length);
  const name = [c.given_names, c.family_name].filter(Boolean).join(" ") || "(sem nome)";
  const tabs = [
    { key: "ident", label: "Identificação" },
    { key: "interviews", label: "Entrevistas/fontes", badge: c.interviews.length },
    { key: "traits", label: "Características/sinais", badge: c.marks.length },
    { key: "effects", label: "Vestimentas/objetos", badge: c.effects.filter((e) => e.field_code !== "515").length },
    { key: "medical", label: "Médico/odontológico" },
    { key: "attachments", label: "Fotos e documentos", badge: attCount },
    { key: "history", label: "Histórico" },
  ];

  return (
    <div>
      <div className="breadcrumbs">
        <Link to="/am">Ante Mortem</Link> / {c.am_number}
      </div>
      <div className="case-header">
        <div>
          <h1>
            {c.am_number} <span className="muted">· {name}</span>
          </h1>
          <span className={`tag ${c.status === "RASCUNHO" ? "" : "info"}`}>{v.case_status[c.status]}</span>{" "}
          <span className="small muted">
            versão {c.version} · atualizado {fmtDateTime(c.updated_at)}
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
        {tab === "ident" && (
          <>
            <h3>Pessoa desaparecida</h3>
            <div className="grid">
              <Field label="Sobrenome" code="cab.">
                <input disabled={!canWrite} value={draft.family_name ?? ""} onChange={(e) => set("family_name", e.target.value || null)} />
              </Field>
              <Field label="Nome(s)" code="cab.">
                <input disabled={!canWrite} value={draft.given_names ?? ""} onChange={(e) => set("given_names", e.target.value || null)} />
              </Field>
              <Field label="Sexo" code="cab.">
                <SelectInput disabled={!canWrite} value={draft.sex} options={v.am_sex} onChange={(x) => set("sex", x)} />
              </Field>
              <Field label="Data de nascimento" code="cab.">
                <input disabled={!canWrite} type="date" value={draft.date_of_birth ?? ""} onChange={(e) => set("date_of_birth", e.target.value || null)} />
              </Field>
              <Field label="Idade (anos)" code="cab.">
                <input disabled={!canWrite} type="number" value={draft.age_years ?? ""} onChange={(e) => set("age_years", numOrNull(e.target.value))} />
              </Field>
            </div>
            {(["circumstances", "nominal", "admin"] as const).map((s) => (
              <section key={s}>
                <h3>{AM_SECTIONS[s].title}</h3>
                <SpecSection disabled={!canWrite} specs={AM_SECTIONS[s].specs} values={draft.form_data[s] ?? {}} onChange={setSection(s)} />
              </section>
            ))}
          </>
        )}
        {tab === "interviews" && <Interviews c={c} canWrite={canWrite} onChanged={onItemsChanged} />}
        {tab === "traits" && (
          <>
            <h3>Medidas e compleição (relato)</h3>
            <div className="grid">
              <Field label="Estatura mín. (cm)" code="408">
                <input disabled={!canWrite} type="number" value={draft.height_min_cm ?? ""} onChange={(e) => set("height_min_cm", numOrNull(e.target.value))} />
              </Field>
              <Field label="Estatura máx. (cm)" code="408">
                <input disabled={!canWrite} type="number" value={draft.height_max_cm ?? ""} onChange={(e) => set("height_max_cm", numOrNull(e.target.value))} />
              </Field>
              <Field label="Certeza da estatura" code="EXT">
                <SelectInput disabled={!canWrite} value={draft.height_certainty} options={v.certainty_am} onChange={(x) => set("height_certainty", x)} />
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
            <h3>{AM_SECTIONS.body.title}</h3>
            <SpecSection disabled={!canWrite} specs={AM_SECTIONS.body.specs} values={draft.form_data.body ?? {}} onChange={setSection("body")} />
            <MarksEditor
              kind="am"
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
        {tab === "effects" && (
          <EffectsEditor
            kind="am"
            caseId={c.id}
            effects={c.effects}
            fields={["300", "305", "310", "315", "335", "340", "345", "350"]}
            canWrite={canWrite}
            onChanged={onItemsChanged}
            title="Vestimentas e objetos informados (campos 300–350)"
          />
        )}
        {tab === "medical" && (
          <>
            {(["medical", "dental", "dna", "supporting"] as const).map((s) => (
              <section key={s}>
                <h3>{AM_SECTIONS[s].title}</h3>
                <SpecSection disabled={!canWrite} specs={AM_SECTIONS[s].specs} values={draft.form_data[s] ?? {}} onChange={setSection(s)} />
              </section>
            ))}
            <EffectsEditor kind="am" caseId={c.id} effects={c.effects} fields={["515"]} canWrite={canWrite} onChanged={onItemsChanged} title="Implantes (campo 515)" />
          </>
        )}
        {tab === "attachments" && <AttachmentsPanel kind="AM" caseId={c.id} canWrite={can("att_am:write")} onCount={setAttCount} />}
        {tab === "history" && <HistoryList url={`/api/am/${c.id}/history`} refreshKey={histKey} />}
      </div>
    </div>
  );
}

function Interviews({ c, canWrite, onChanged }: { c: AmCase; canWrite: boolean; onChanged: () => void }) {
  const empty = {
    informant_name: "", relationship_to_missing: "", contact: "", address: "", interview_date: "", location: "",
    is_point_of_contact: false, notes: "",
  };
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    const body = Object.fromEntries(Object.entries(form).map(([k, val]) => [k, val === "" ? null : val]));
    try {
      if (editing) await put(`/api/am/${c.id}/interviews/${editing}`, body);
      else await post(`/api/am/${c.id}/interviews`, body);
      setForm(empty);
      setEditing(null);
      onChanged();
    } catch (err) {
      setError((err as Error).message);
    }
  };
  const edit = (iv: Interview) => {
    setEditing(iv.id);
    setForm({
      informant_name: iv.informant_name, relationship_to_missing: iv.relationship_to_missing ?? "",
      contact: iv.contact ?? "", address: iv.address ?? "", interview_date: iv.interview_date ?? "",
      location: iv.location ?? "", is_point_of_contact: iv.is_point_of_contact, notes: iv.notes ?? "",
    });
  };
  const s = (k: keyof typeof empty) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  return (
    <div>
      <h3>
        Entrevistas e fontes de informação <span className="code">105/110</span>
      </h3>
      <p className="small muted">
        Vários entrevistados podem ser vinculados ao mesmo caso. Documentos do entrevistado devem ser anexados como
        “Entrevistado/fonte”, separados dos documentos da pessoa desaparecida.
      </p>
      <table className="table">
        <thead>
          <tr>
            <th>Data</th>
            <th>Informante</th>
            <th>Vínculo</th>
            <th>Contato</th>
            <th>Observações</th>
            {canWrite && <th />}
          </tr>
        </thead>
        <tbody>
          {c.interviews.length === 0 && (
            <tr>
              <td colSpan={6} className="muted">
                Nenhuma entrevista registrada.
              </td>
            </tr>
          )}
          {c.interviews.map((iv) => (
            <tr key={iv.id}>
              <td>{fmtDate(iv.interview_date)}</td>
              <td>
                {iv.informant_name}
                {iv.is_point_of_contact && <span className="tag info">ponto de contato</span>}
              </td>
              <td>{iv.relationship_to_missing}</td>
              <td>{iv.contact}</td>
              <td className="small">{iv.notes}</td>
              {canWrite && (
                <td>
                  <button className="link" onClick={() => edit(iv)}>
                    editar
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      {canWrite && (
        <form className="card" onSubmit={submit}>
          <h4>{editing ? "Editar entrevista" : "Nova entrevista"}</h4>
          <div className="grid">
            <Field label="Nome do informante" code="105">
              <input value={form.informant_name} onChange={s("informant_name")} />
            </Field>
            <Field label="Vínculo com o desaparecido" code="105">
              <input value={form.relationship_to_missing} onChange={s("relationship_to_missing")} />
            </Field>
            <Field label="Telefone/e-mail" code="105">
              <input value={form.contact} onChange={s("contact")} />
            </Field>
            <Field label="Data da entrevista" code="105">
              <input type="date" value={form.interview_date} onChange={s("interview_date")} />
            </Field>
            <Field label="Local" code="EXT">
              <input value={form.location} onChange={s("location")} />
            </Field>
            <Field label="Endereço" code="105" wide>
              <input value={form.address} onChange={s("address")} />
            </Field>
            <label className="check">
              <input type="checkbox" checked={form.is_point_of_contact} onChange={(e) => setForm({ ...form, is_point_of_contact: e.target.checked })} />{" "}
              Ponto de contato da família (110)
            </label>
            <Field label="Observações da entrevista" code="EXT" wide>
              <textarea rows={4} value={form.notes} onChange={s("notes")} />
            </Field>
          </div>
          <div className="row">
            <button type="submit" disabled={!form.informant_name}>
              {editing ? "Salvar entrevista" : "Adicionar entrevista"}
            </button>
            {editing && (
              <button type="button" className="ghost" onClick={() => { setEditing(null); setForm(empty); }}>
                Cancelar
              </button>
            )}
          </div>
          {error && <div className="alert error">{error}</div>}
        </form>
      )}
    </div>
  );
}
