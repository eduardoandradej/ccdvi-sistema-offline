import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { get, post } from "../api";
import { Field, fmtDateTime, SelectInput } from "../components/Fields";
import { useSession } from "../session";
import type { AmCase } from "../types";

type Row = Pick<AmCase, "id" | "am_number" | "status" | "family_name" | "given_names" | "sex" | "age_years" | "date_of_birth" | "updated_at">;

export default function AmListPage() {
  const { vocab, can } = useSession();
  const v = vocab!;
  const nav = useNavigate();
  const [params, setParams] = useSearchParams();
  const [rows, setRows] = useState<Row[]>([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [creating, setCreating] = useState(params.get("novo") === "1");
  const [form, setForm] = useState({ family_name: "", given_names: "", sex: "" });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const p = new URLSearchParams();
    if (q) p.set("q", q);
    if (status) p.set("status", status);
    const t = setTimeout(() => get<Row[]>(`/api/am?${p}`).then(setRows).catch((e) => setError(e.message)), 200);
    return () => clearTimeout(t);
  }, [q, status]);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const c = await post<AmCase>("/api/am", {
        family_name: form.family_name || null,
        given_names: form.given_names || null,
        sex: form.sex || null,
      });
      nav(`/am/${c.id}`);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div>
      <div className="row between">
        <h1>Ante Mortem — pessoas desaparecidas</h1>
        {can("am:write") && !creating && (
          <button onClick={() => { setCreating(true); setParams({}); }}>Novo desaparecido</button>
        )}
      </div>
      {creating && (
        <form className="card" onSubmit={create}>
          <h3>Novo registro AM</h3>
          <p className="small muted">
            O número AM é atribuído pelo servidor conforme o Anexo 9 (ex.: AM55-0001). Os demais dados podem ser
            preenchidos depois (salvamento parcial).
          </p>
          <div className="grid">
            <Field label="Sobrenome" code="cab.">
              <input value={form.family_name} onChange={(e) => setForm({ ...form, family_name: e.target.value })} />
            </Field>
            <Field label="Nome(s)" code="cab.">
              <input value={form.given_names} onChange={(e) => setForm({ ...form, given_names: e.target.value })} />
            </Field>
            <Field label="Sexo" code="cab.">
              <SelectInput value={form.sex} options={v.am_sex} onChange={(x) => setForm({ ...form, sex: x ?? "" })} />
            </Field>
          </div>
          <div className="row">
            <button type="submit">Criar registro AM</button>
            <button type="button" className="ghost" onClick={() => setCreating(false)}>
              Cancelar
            </button>
          </div>
        </form>
      )}
      {error && <div className="alert error">{error}</div>}
      <div className="row filters">
        <input placeholder="Buscar por número AM ou nome…" value={q} onChange={(e) => setQ(e.target.value)} />
        <SelectInput value={status} options={v.case_status} empty="Todos os status" onChange={setStatus} />
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Nº AM</th>
            <th>Nome</th>
            <th>Sexo</th>
            <th>Idade / nasc.</th>
            <th>Status</th>
            <th>Atualizado</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>
                <Link to={`/am/${r.id}`}>{r.am_number}</Link>
              </td>
              <td>{[r.given_names, r.family_name].filter(Boolean).join(" ") || <span className="muted">—</span>}</td>
              <td>{r.sex ? v.am_sex[r.sex] : "—"}</td>
              <td>{r.age_years ?? (r.date_of_birth ? new Date(r.date_of_birth + "T12:00").toLocaleDateString("pt-BR") : "—")}</td>
              <td>
                <span className={`tag ${r.status === "RASCUNHO" ? "" : "info"}`}>{v.case_status[r.status]}</span>
              </td>
              <td className="small">{fmtDateTime(r.updated_at)}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={6} className="muted">
                Nenhum registro.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
