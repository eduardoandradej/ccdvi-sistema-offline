import { FormEvent, useState } from "react";
import { del, post } from "../api";
import { useSession } from "../session";
import type { Dict, Effect, Mark } from "../types";
import { Code, Field, SelectInput } from "./Fields";

type Kind = "am" | "pm";

/** Campo 404 — sinais particulares por tipo e região anatômica (com lateralidade). */
export function MarksEditor({
  kind,
  caseId,
  marks,
  categoryStatus,
  onCategoryStatus,
  canWrite,
  onChanged,
}: {
  kind: Kind;
  caseId: string;
  marks: Mark[];
  categoryStatus: Dict;
  onCategoryStatus: (k: string, v: string | null) => void;
  canWrite: boolean;
  onChanged: () => void;
}) {
  const { vocab } = useSession();
  const v = vocab!;
  const certainties = kind === "am" ? v.certainty_am : v.certainty_pm;
  const empty = { mark_type: "", region: "", description: "", certainty: Object.keys(certainties)[0], source: "" };
  const [form, setForm] = useState(empty);
  const [error, setError] = useState<string | null>(null);

  const add = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await post(`/api/${kind}/${caseId}/marks`, {
        ...form,
        description: form.description || null,
        source: form.source || null,
      });
      setForm(empty);
      onChanged();
    } catch (err) {
      setError((err as Error).message);
    }
  };
  const remove = async (id: string) => {
    if (!confirm("Remover este sinal? A remoção fica registrada no histórico.")) return;
    await del(`/api/${kind}/${caseId}/marks/${id}`);
    onChanged();
  };

  return (
    <div>
      <h3>
        Sinais particulares <Code code="404" />
      </h3>
      <p className="small muted">
        {kind === "am"
          ? "Registre o que foi RELATADO pela fonte; o grau de certeza não converte relato em fato."
          : "Registre o que foi OBSERVADO no exame, indicando incertezas."}
      </p>
      <table className="table">
        <thead>
          <tr>
            <th>Tipo</th>
            <th>Região / lado</th>
            <th>Descrição</th>
            <th>Certeza</th>
            {canWrite && <th />}
          </tr>
        </thead>
        <tbody>
          {marks.length === 0 && (
            <tr>
              <td colSpan={5} className="muted">
                Nenhum sinal registrado.
              </td>
            </tr>
          )}
          {marks.map((m) => (
            <tr key={m.id}>
              <td>{v.mark_types[m.mark_type]}</td>
              <td>{v.regions[m.region]}</td>
              <td>
                {m.description}
                {m.source && <div className="small muted">Fonte: {m.source}</div>}
              </td>
              <td>{v.certainty_am[m.certainty] ?? v.certainty_pm[m.certainty]}</td>
              {canWrite && (
                <td>
                  <button className="link danger" onClick={() => remove(m.id)}>
                    remover
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      {canWrite && (
        <form className="inline-form" onSubmit={add}>
          <Field label="Tipo" code="404">
            <SelectInput value={form.mark_type} options={v.mark_types} empty="— selecione —" onChange={(x) => setForm({ ...form, mark_type: x ?? "" })} />
          </Field>
          <Field label="Região anatômica" code="404">
            <SelectInput value={form.region} options={v.regions} empty="— selecione —" onChange={(x) => setForm({ ...form, region: x ?? "" })} />
          </Field>
          <Field label="Descrição (motivo, forma, tamanho)" wide>
            <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </Field>
          <Field label="Certeza" code="EXT">
            <SelectInput value={form.certainty} options={certainties} empty="—" onChange={(x) => setForm({ ...form, certainty: x ?? "" })} />
          </Field>
          {kind === "am" && (
            <Field label="Fonte" code="EXT">
              <input value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} />
            </Field>
          )}
          <button type="submit" disabled={!form.mark_type || !form.region}>
            Adicionar sinal
          </button>
        </form>
      )}
      {error && <div className="alert error">{error}</div>}

      <h3>Situação por categoria (quando não há itens)</h3>
      <p className="small muted">
        Ausência de registro não é evidência negativa. Use “Negativo” somente quando verificado que a pessoa/corpo não
        possui o sinal.
      </p>
      <div className="grid">
        {Object.entries(v.mark_types).map(([code, label]) => (
          <Field key={code} label={label} code="EXT">
            <SelectInput
              disabled={!canWrite}
              value={categoryStatus[code]}
              options={v.category_status}
              onChange={(x) => onCategoryStatus(code, x)}
            />
          </Field>
        ))}
      </div>
    </div>
  );
}

/** Campos 300–350 (vestimentas, calçados, relógio, óculos, joias, documentos, objetos, eletrônicos) e 515. */
export function EffectsEditor({
  kind,
  caseId,
  effects,
  fields,
  canWrite,
  onChanged,
  title,
}: {
  kind: Kind;
  caseId: string;
  effects: Effect[];
  fields: string[];
  canWrite: boolean;
  onChanged: () => void;
  title: string;
}) {
  const { vocab } = useSession();
  const v = vocab!;
  const certainties = kind === "am" ? v.certainty_am : v.certainty_pm;
  const empty = {
    field_code: fields[0],
    item_code: "",
    type_style: "",
    colour: "",
    brand: "",
    material: "",
    size: "",
    inscription: "",
    where_worn: "",
    serial_number: "",
    description: "",
    certainty: Object.keys(certainties)[0],
  };
  const [form, setForm] = useState(empty);
  const [error, setError] = useState<string | null>(null);
  const shown = effects.filter((e) => fields.includes(e.field_code));
  const fieldOptions = Object.fromEntries(fields.map((f) => [f, `${f} — ${v.effect_fields[f]}`]));

  const add = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    const body = Object.fromEntries(Object.entries(form).map(([k, val]) => [k, val === "" ? null : val]));
    try {
      await post(`/api/${kind}/${caseId}/effects`, body);
      setForm({ ...empty, field_code: form.field_code });
      onChanged();
    } catch (err) {
      setError((err as Error).message);
    }
  };
  const remove = async (id: string) => {
    if (!confirm("Remover este item? A remoção fica registrada no histórico.")) return;
    await del(`/api/${kind}/${caseId}/effects/${id}`);
    onChanged();
  };
  const set = (k: keyof typeof empty) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  return (
    <div>
      <h3>{title}</h3>
      <table className="table">
        <thead>
          <tr>
            <th>Campo</th>
            <th>Item</th>
            <th>Detalhes</th>
            <th>Certeza</th>
            {canWrite && <th />}
          </tr>
        </thead>
        <tbody>
          {shown.length === 0 && (
            <tr>
              <td colSpan={5} className="muted">
                Nenhum item registrado.
              </td>
            </tr>
          )}
          {shown.map((e) => (
            <tr key={e.id}>
              <td>
                <Code code={e.field_code} /> {v.effect_fields[e.field_code]}
              </td>
              <td>{v.effect_items[e.field_code]?.[e.item_code]}</td>
              <td>
                {[e.type_style, e.colour && v.colours[e.colour], e.brand, e.material, e.size, e.inscription && `“${e.inscription}”`, e.where_worn, e.serial_number && `nº série ${e.serial_number}`, e.description]
                  .filter(Boolean)
                  .join(" · ")}
              </td>
              <td>{v.certainty_am[e.certainty] ?? v.certainty_pm[e.certainty]}</td>
              {canWrite && (
                <td>
                  <button className="link danger" onClick={() => remove(e.id)}>
                    remover
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      {canWrite && (
        <form className="inline-form" onSubmit={add}>
          <Field label="Campo">
            <SelectInput value={form.field_code} options={fieldOptions} empty="—" onChange={(x) => setForm({ ...form, field_code: x ?? fields[0], item_code: "" })} />
          </Field>
          <Field label="Item">
            <SelectInput value={form.item_code} options={v.effect_items[form.field_code] ?? {}} empty="— selecione —" onChange={(x) => setForm({ ...form, item_code: x ?? "" })} />
          </Field>
          <Field label="Tipo/estilo">
            <input value={form.type_style} onChange={set("type_style")} />
          </Field>
          <Field label="Cor principal">
            <SelectInput value={form.colour} options={v.colours} onChange={(x) => setForm({ ...form, colour: x ?? "" })} />
          </Field>
          <Field label="Marca/fabricante">
            <input value={form.brand} onChange={set("brand")} />
          </Field>
          <Field label="Material">
            <input value={form.material} onChange={set("material")} />
          </Field>
          <Field label="Tamanho">
            <input value={form.size} onChange={set("size")} />
          </Field>
          <Field label="Inscrição">
            <input value={form.inscription} onChange={set("inscription")} />
          </Field>
          <Field label="Onde usado">
            <input value={form.where_worn} onChange={set("where_worn")} />
          </Field>
          <Field label="Nº de série">
            <input value={form.serial_number} onChange={set("serial_number")} />
          </Field>
          <Field label="Certeza" code="EXT">
            <SelectInput value={form.certainty} options={certainties} empty="—" onChange={(x) => setForm({ ...form, certainty: x ?? "" })} />
          </Field>
          <button type="submit" disabled={!form.item_code}>
            Adicionar item
          </button>
        </form>
      )}
      {error && <div className="alert error">{error}</div>}
    </div>
  );
}
