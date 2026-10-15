import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { get, post, upload } from "../api";
import { useSession } from "../session";
import type { Attachment } from "../types";
import { Field, fmtDateTime, SelectInput } from "./Fields";

const ACCEPT = ".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf";

function fmtSize(n: number) {
  return n > 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.ceil(n / 1024)} KB`;
}

/** Componente de anexação reutilizável para AM e PM. */
export default function AttachmentsPanel({
  kind,
  caseId,
  canWrite,
  onCount,
}: {
  kind: "AM" | "PM";
  caseId: string;
  canWrite: boolean;
  onCount?: (n: number) => void;
}) {
  const { vocab } = useSession();
  const v = vocab!;
  const types = Object.fromEntries(
    (kind === "AM" ? v.attachment_types_am : v.attachment_types_pm).map((t) => [t, v.attachment_types[t]]),
  );
  const subjects = kind === "AM" ? v.attachment_subjects_am : v.attachment_subjects_pm;
  const [items, setItems] = useState<Attachment[]>([]);
  const [showOld, setShowOld] = useState(false);
  const [filter, setFilter] = useState<string | null>(null);
  const [form, setForm] = useState({
    doc_type: "",
    subject: Object.keys(subjects)[0],
    title: "",
    description: "",
    source: "",
    evidence_ref: "",
    obtained_at: "",
  });
  const fileRef = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [viewer, setViewer] = useState<Attachment | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const q = new URLSearchParams({ [kind === "AM" ? "am_case_id" : "pm_case_id"]: caseId });
    if (showOld) q.set("include_superseded", "true");
    if (filter) q.set("doc_type", filter);
    try {
      const list = await get<Attachment[]>(`/api/attachments?${q}`);
      setItems(list);
      if (!filter && !showOld) onCount?.(list.length);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [kind, caseId, showOld, filter, onCount]);

  useEffect(() => {
    load();
  }, [load]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.set("record_kind", kind);
    fd.set("case_id", caseId);
    Object.entries(form).forEach(([k, val]) => {
      if (val) fd.set(k, k === "obtained_at" ? new Date(val).toISOString() : val);
    });
    fd.set("file", file);
    setMsg(null);
    setProgress(0);
    try {
      const att = await upload<Attachment>("/api/attachments", fd, setProgress);
      setMsg({ ok: true, text: `Arquivo armazenado e confirmado pelo servidor. SHA-256: ${att.sha256}` });
      setForm({ ...form, title: "", description: "", evidence_ref: "" });
      if (fileRef.current) fileRef.current.value = "";
      load();
    } catch (err) {
      setMsg({ ok: false, text: `Erro — arquivo NÃO armazenado: ${(err as Error).message}` });
    } finally {
      setProgress(null);
    }
  };

  const verify = async (a: Attachment) => {
    const r = await get<{ ok: boolean; sha256_atual: string | null }>(`/api/attachments/${a.id}/verify`);
    alert(r.ok ? `Integridade confirmada.\nSHA-256: ${r.sha256_atual}` : "FALHA DE INTEGRIDADE: o arquivo armazenado não corresponde ao hash registrado.");
  };
  const withdraw = async (a: Attachment) => {
    const reason = prompt("Motivo da retirada (o arquivo original será mantido):");
    if (!reason) return;
    try {
      await post(`/api/attachments/${a.id}/withdraw`, { reason });
      load();
    } catch (err) {
      alert((err as Error).message);
    }
  };
  const newVersion = (a: Attachment) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ACCEPT;
    input.onchange = async () => {
      const f = input.files?.[0];
      if (!f) return;
      const fd = new FormData();
      fd.set("file", f);
      try {
        await upload(`/api/attachments/${a.id}/versions`, fd);
        load();
      } catch (err) {
        alert((err as Error).message);
      }
    };
    input.click();
  };

  return (
    <div>
      <div className="row between">
        <h3>Fotos e documentos</h3>
        <div className="row">
          <SelectInput value={filter} options={types} empty="Todos os tipos" onChange={setFilter} />
          <label className="check">
            <input type="checkbox" checked={showOld} onChange={(e) => setShowOld(e.target.checked)} /> mostrar versões
            anteriores
          </label>
        </div>
      </div>
      {error && <div className="alert error">{error}</div>}
      <div className="attachments">
        {items.length === 0 && <p className="muted">Nenhum anexo.</p>}
        {items.map((a) => (
          <div key={a.id} className={`att ${a.status !== "ARMAZENADO" || a.superseded ? "dim" : ""}`} data-testid="attachment">
            <div className="thumb">
              {a.mime_type.startsWith("image/") ? (
                <img src={`/api/attachments/${a.id}/thumbnail`} alt={a.title} onClick={() => setViewer(a)} />
              ) : (
                <span className="pdf">PDF{a.page_count ? ` · ${a.page_count} p.` : ""}</span>
              )}
            </div>
            <div className="meta">
              <strong>{a.title}</strong>
              <span className="tag">{v.attachment_types[a.doc_type]}</span>
              <span className="tag info">{subjects[a.subject] ?? a.subject}</span>
              {a.version > 1 && <span className="tag">v{a.version}</span>}
              {a.superseded && <span className="tag">substituído</span>}
              {a.status === "RETIRADO" && <span className="tag danger">retirado: {a.withdrawn_reason}</span>}
              <div className="small muted">
                {a.original_filename} · {fmtSize(a.size_bytes)} · enviado em {fmtDateTime(a.uploaded_at)} por{" "}
                {a.uploaded_by_name}
                {a.source && ` · fonte: ${a.source}`}
                {a.obtained_at && ` · obtido em ${fmtDateTime(a.obtained_at)}`}
                {a.evidence_ref && ` · evidência ${a.evidence_ref}`}
              </div>
              <div className="small mono" title="SHA-256">
                SHA-256 {a.sha256.slice(0, 16)}… · UUID {a.id.slice(0, 8)}…
              </div>
              <div className="row small">
                <a href={`/api/attachments/${a.id}/content`} target="_blank" rel="noreferrer">
                  visualizar
                </a>
                <a href={`/api/attachments/${a.id}/content?download=true`}>baixar</a>
                <button className="link" onClick={() => verify(a)}>
                  verificar integridade
                </button>
                {canWrite && !a.superseded && a.status === "ARMAZENADO" && (
                  <>
                    <button className="link" onClick={() => newVersion(a)}>
                      nova versão
                    </button>
                    <button className="link danger" onClick={() => withdraw(a)}>
                      retirar
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {canWrite && (
        <form className="card upload" onSubmit={submit}>
          <h4>Anexar arquivo (JPEG, PNG ou PDF)</h4>
          <div className="grid">
            <Field label="Tipo de anexo">
              <SelectInput value={form.doc_type} options={types} empty="— selecione —" onChange={(x) => setForm({ ...form, doc_type: x ?? "" })} />
            </Field>
            <Field label="Refere-se a">
              <SelectInput value={form.subject} options={subjects} empty="—" onChange={(x) => setForm({ ...form, subject: x ?? "" })} />
            </Field>
            <Field label="Título">
              <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </Field>
            <Field label="Fonte/origem">
              <input value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} />
            </Field>
            <Field label="Data/hora de obtenção">
              <input type="datetime-local" value={form.obtained_at} onChange={(e) => setForm({ ...form, obtained_at: e.target.value })} />
            </Field>
            {kind === "PM" && (
              <Field label="Identificador de evidência">
                <input placeholder="ex.: PM55-0001-A-Evidence item 3" value={form.evidence_ref} onChange={(e) => setForm({ ...form, evidence_ref: e.target.value })} />
              </Field>
            )}
            <Field label="Descrição" wide>
              <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </Field>
            <Field label="Arquivo" wide>
              <input ref={fileRef} type="file" accept={ACCEPT} data-testid="file-input" />
            </Field>
          </div>
          {progress !== null && (
            <div className="progress">
              <div style={{ width: `${progress}%` }} />
              <span>{progress < 100 ? `Enviando ${progress}%` : "Gravando e verificando no servidor…"}</span>
            </div>
          )}
          <button type="submit" disabled={progress !== null || !form.doc_type || !form.title}>
            Enviar anexo
          </button>
          {msg && <div className={`alert ${msg.ok ? "success" : "error"}`}>{msg.text}</div>}
        </form>
      )}

      {viewer && (
        <div className="modal" onClick={() => setViewer(null)}>
          <div className="modal-body" onClick={(e) => e.stopPropagation()}>
            <div className="row between">
              <strong>{viewer.title}</strong>
              <button className="ghost" onClick={() => setViewer(null)}>
                fechar
              </button>
            </div>
            <img src={`/api/attachments/${viewer.id}/content`} alt={viewer.title} />
            <p className="small muted">Visualização sem metadados EXIF/GPS. Não utilizar como biometria facial.</p>
          </div>
        </div>
      )}
    </div>
  );
}
