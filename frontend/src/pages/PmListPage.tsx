import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { get, post } from "../api";
import { Field, fmtDate, fmtDateTime, SelectInput } from "../components/Fields";
import { useSession } from "../session";
import type { PmCase } from "../types";

type Row = Pick<PmCase, "id" | "pm_number" | "status" | "state_of_body" | "sex" | "age_min_years" | "age_max_years" | "recovery_date" | "updated_at">;

export default function PmListPage() {
  const { vocab, can, me } = useSession();
  const v = vocab!;
  const nav = useNavigate();
  const [params, setParams] = useSearchParams();
  const [rows, setRows] = useState<Row[]>([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [creating, setCreating] = useState(params.get("novo") === "1");
  const [form, setForm] = useState({ scene_ref: "", recovery_date: "", recovery_place: "", state_of_body: "" });
  const [error, setError] = useState<string | null>(null);
  const cc = me!.context!.operation.country_code;

  useEffect(() => {
    const p = new URLSearchParams();
    if (q) p.set("q", q);
    if (status) p.set("status", status);
    const t = setTimeout(() => get<Row[]>(`/api/pm?${p}`).then(setRows).catch((e) => setError(e.message)), 200);
    return () => clearTimeout(t);
  }, [q, status]);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const body = Object.fromEntries(Object.entries(form).map(([k, val]) => [k, val === "" ? null : val]));
      const c = await post<PmCase>("/api/pm", body);
      nav(`/pm/${c.id}`);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div>
      <div className="row between">
        <h1>Post Mortem — restos mortais não identificados</h1>
        {can("pm:write") && !creating && (
          <button onClick={() => { setCreating(true); setParams({}); }}>Recepção PM</button>
        )}
      </div>
      {creating && (
        <form className="card" onSubmit={create}>
          <h3>Recepção de novo registro PM</h3>
          <p className="small muted">
            Número atribuído pelo servidor conforme o Anexo 9: PM{cc}-NNNN[-CENA]. Cada corpo ou segmento recebe número
            próprio e exclusivo.
          </p>
          <div className="grid">
            <Field label="Referência de cena (ex.: A, B, HS)" code="Anexo 9">
              <input maxLength={6} value={form.scene_ref} onChange={(e) => setForm({ ...form, scene_ref: e.target.value.toUpperCase() })} />
            </Field>
            <Field label="Data de recuperação" code="EXT">
              <input type="date" value={form.recovery_date} onChange={(e) => setForm({ ...form, recovery_date: e.target.value })} />
            </Field>
            <Field label="Local de recuperação" code="EXT">
              <input value={form.recovery_place} onChange={(e) => setForm({ ...form, recovery_place: e.target.value })} />
            </Field>
            <Field label="Estado do corpo" code="402">
              <SelectInput value={form.state_of_body} options={v.state_of_body} onChange={(x) => setForm({ ...form, state_of_body: x ?? "" })} />
            </Field>
          </div>
          <div className="row">
            <button type="submit">Registrar PM</button>
            <button type="button" className="ghost" onClick={() => setCreating(false)}>
              Cancelar
            </button>
          </div>
        </form>
      )}
      {error && <div className="alert error">{error}</div>}
      <div className="row filters">
        <input placeholder="Buscar por número PM ou local…" value={q} onChange={(e) => setQ(e.target.value)} />
        <SelectInput value={status} options={v.case_status} empty="Todos os status" onChange={setStatus} />
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Nº PM</th>
            <th>Estado</th>
            <th>Sexo (535)</th>
            <th>Idade estimada</th>
            <th>Recuperação</th>
            <th>Status</th>
            <th>Atualizado</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>
                <Link to={`/pm/${r.id}`}>{r.pm_number}</Link>
              </td>
              <td>{r.state_of_body ? v.state_of_body[r.state_of_body] : "—"}</td>
              <td>{r.sex ? v.pm_sex[r.sex] : "—"}</td>
              <td>{r.age_min_years != null || r.age_max_years != null ? `${r.age_min_years ?? "?"}–${r.age_max_years ?? "?"}` : "—"}</td>
              <td>{fmtDate(r.recovery_date)}</td>
              <td>
                <span className={`tag ${r.status === "RASCUNHO" ? "" : "info"}`}>{v.case_status[r.status]}</span>
              </td>
              <td className="small">{fmtDateTime(r.updated_at)}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={7} className="muted">
                Nenhum registro.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
