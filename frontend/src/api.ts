// Cliente HTTP da API. Sempre na mesma origem (sem CDN/serviços externos).

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function detailMessage(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      return d
        .map((e: { msg?: string; loc?: unknown[] }) => {
          const field = Array.isArray(e.loc) ? e.loc.filter((x) => x !== "body").join(".") : "";
          return `${field ? field + ": " : ""}${(e.msg ?? "").replace(/^Value error, /, "")}`;
        })
        .join("; ");
    }
  }
  if (status === 401) return "Sessão expirada. Entre novamente.";
  if (status === 403) return "Permissão insuficiente para esta ação.";
  return `Erro ${status}`;
}

export async function api<T = unknown>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: {
      "X-DVI-Request": "1",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && !path.startsWith("/api/auth/login")) {
      window.dispatchEvent(new Event("dvi:unauthorized"));
    }
    throw new ApiError(res.status, detailMessage(data, res.status));
  }
  return data as T;
}

export const get = <T,>(p: string) => api<T>("GET", p);
export const post = <T,>(p: string, b?: unknown) => api<T>("POST", p, b ?? {});
export const put = <T,>(p: string, b: unknown) => api<T>("PUT", p, b);
export const patch = <T,>(p: string, b: unknown) => api<T>("PATCH", p, b);
export const del = <T,>(p: string) => api<T>("DELETE", p);

/** Upload multipart com progresso real (XMLHttpRequest). Resolve apenas após resposta 201 do servidor. */
export function upload<T>(path: string, form: FormData, onProgress?: (pct: number) => void): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", path);
    xhr.withCredentials = true;
    xhr.setRequestHeader("X-DVI-Request", "1");
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      let data: unknown = null;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        /* resposta vazia */
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data as T);
      else reject(new ApiError(xhr.status, detailMessage(data, xhr.status)));
    };
    xhr.onerror = () => reject(new ApiError(0, "Falha de rede ao enviar o arquivo."));
    xhr.send(form);
  });
}
