import { ReactNode } from "react";
import type { Dict } from "../types";

export interface FieldSpec {
  key: string;
  label: string;
  /** Código do campo no formulário INTERPOL 2023 ou "EXT" para extensão proposta pelo sistema. */
  code: string;
  type?: "text" | "textarea" | "select" | "date" | "number";
  options?: Dict;
  wide?: boolean;
}

export function Code({ code }: { code: string }) {
  if (!code) return null;
  const ext = code === "EXT";
  return (
    <span className={`code ${ext ? "ext" : ""}`} title={ext ? "Extensão proposta pelo sistema" : "Campo do formulário INTERPOL 2023"}>
      {ext ? "ext." : code}
    </span>
  );
}

export function Field({
  label,
  code,
  children,
  wide,
}: {
  label: string;
  code?: string;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <label className={`field ${wide ? "wide" : ""}`}>
      <span className="label">
        {label} {code && <Code code={code} />}
      </span>
      {children}
    </label>
  );
}

export function SelectInput({
  value,
  onChange,
  options,
  empty = "— não informado —",
  disabled,
}: {
  value: string | null | undefined;
  onChange: (v: string | null) => void;
  options: Dict;
  empty?: string;
  disabled?: boolean;
}) {
  return (
    <select value={value ?? ""} disabled={disabled} onChange={(e) => onChange(e.target.value || null)}>
      <option value="">{empty}</option>
      {Object.entries(options).map(([k, v]) => (
        <option key={k} value={k}>
          {v}
        </option>
      ))}
    </select>
  );
}

export const numOrNull = (v: string) => (v === "" ? null : Number(v));

/** Renderiza uma seção de form_data a partir de especificações rastreáveis. */
export function SpecSection({
  specs,
  values,
  onChange,
  disabled,
}: {
  specs: FieldSpec[];
  values: Record<string, unknown>;
  onChange: (key: string, value: unknown) => void;
  disabled?: boolean;
}) {
  return (
    <div className="grid">
      {specs.map((s) => {
        const v = values[s.key];
        let input: ReactNode;
        if (s.type === "textarea") {
          input = (
            <textarea disabled={disabled} rows={3} value={(v as string) ?? ""} onChange={(e) => onChange(s.key, e.target.value || null)} />
          );
        } else if (s.type === "select") {
          input = <SelectInput disabled={disabled} value={v as string} options={s.options ?? {}} onChange={(x) => onChange(s.key, x)} />;
        } else {
          input = (
            <input
              disabled={disabled}
              type={s.type === "date" ? "date" : s.type === "number" ? "number" : "text"}
              value={(v as string | number) ?? ""}
              onChange={(e) =>
                onChange(s.key, s.type === "number" ? numOrNull(e.target.value) : e.target.value || null)
              }
            />
          );
        }
        return (
          <Field key={s.key} label={s.label} code={s.code} wide={s.wide || s.type === "textarea"}>
            {input}
          </Field>
        );
      })}
    </div>
  );
}

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: { key: string; label: string; badge?: string | number }[];
  active: string;
  onChange: (k: string) => void;
}) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button
          key={t.key}
          role="tab"
          aria-selected={active === t.key}
          className={active === t.key ? "active" : ""}
          onClick={() => onChange(t.key)}
        >
          {t.label}
          {t.badge !== undefined && t.badge !== 0 && <span className="badge">{t.badge}</span>}
        </button>
      ))}
    </div>
  );
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("pt-BR");
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso.length === 10 ? iso + "T12:00" : iso).toLocaleDateString("pt-BR");
}
