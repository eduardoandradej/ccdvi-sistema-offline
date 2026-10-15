import { useEffect, useState } from "react";
import { Navigate, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { del, get, post } from "./api";
import { useSession } from "./session";
import LoginPage from "./pages/LoginPage";
import ContextPage from "./pages/ContextPage";
import HomePage from "./pages/HomePage";
import AmListPage from "./pages/AmListPage";
import AmFormPage from "./pages/AmFormPage";
import PmListPage from "./pages/PmListPage";
import PmFormPage from "./pages/PmFormPage";
import ReconciliationPage from "./pages/ReconciliationPage";
import ComparePage from "./pages/ComparePage";
import DashboardPage from "./pages/DashboardPage";
import AuditPage from "./pages/AuditPage";
import AdminPage from "./pages/AdminPage";

function ServerStatus() {
  // Mostra apenas o que é verificável: se o servidor local responde.
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => {
    let alive = true;
    const check = () =>
      get("/api/health")
        .then(() => alive && setOk(true))
        .catch(() => alive && setOk(false));
    check();
    const t = setInterval(check, 30000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);
  if (ok === null) return null;
  return (
    <span className={`net ${ok ? "ok" : "bad"}`} title="Conexão com o servidor local da rede">
      {ok ? "Servidor local: conectado" : "Servidor local: sem resposta"}
    </span>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  const { me, can, refresh } = useSession();
  const nav = useNavigate();
  const ctx = me!.context!;
  const logout = async () => {
    await post("/api/auth/logout");
    await refresh();
    nav("/login");
  };
  const switchCtx = async () => {
    await del("/api/auth/context");
    await refresh();
    nav("/contexto");
  };
  return (
    <div className="shell">
      {ctx.operation.kind === "TREINAMENTO" && (
        <div className="training-banner">AMBIENTE DE TREINAMENTO — SOMENTE DADOS FICTÍCIOS</div>
      )}
      <header className="topbar">
        <div className="brand">
          <strong>DVI Offline</strong>
          <span className="muted">CCDVI/SEPOL</span>
        </div>
        <div className="ctx" data-testid="context-bar">
          <span className="pill">{ctx.operation.name}</span>
          <span className="pill">{ctx.base.name}</span>
          <span className="pill role">{ctx.role_label}</span>
        </div>
        <div className="user">
          <ServerStatus />
          <span>
            {me!.full_name}
            {me!.job_title && <span className="muted"> · {me!.job_title}</span>}
          </span>
          <button className="ghost" onClick={switchCtx}>
            Trocar contexto
          </button>
          <button className="ghost" onClick={logout}>
            Sair
          </button>
        </div>
      </header>
      <nav className="menu">
        <NavLink to="/" end>
          Início
        </NavLink>
        {can("am:read") && <NavLink to="/am">Ante Mortem</NavLink>}
        {can("pm:read") && <NavLink to="/pm">Post Mortem</NavLink>}
        {can("match:read") && <NavLink to="/reconciliacao">Reconciliação</NavLink>}
        {can("dashboard:read") && <NavLink to="/painel">Situação da operação</NavLink>}
        {can("audit:read") && <NavLink to="/auditoria">Auditoria</NavLink>}
        {(can("admin:users") || can("admin:health")) && <NavLink to="/admin">Administração TIC</NavLink>}
      </nav>
      <main className="content">{children}</main>
      <footer className="footer">
        Instrumento de apoio. Não realiza identificação. Referência metodológica: INTERPOL DVI Guide 2023 — sem
        homologação ou vínculo oficial.
      </footer>
    </div>
  );
}

function Guard({ perm, children }: { perm?: string; children: React.ReactNode }) {
  const { can } = useSession();
  if (perm && !can(perm)) return <div className="alert error">Sua função ativa não permite acessar esta tela.</div>;
  return <>{children}</>;
}

export default function App() {
  const { me, loading } = useSession();
  if (loading) return <div className="center muted">Carregando…</div>;
  if (!me) {
    return (
      <Routes>
        <Route path="*" element={<LoginPage />} />
      </Routes>
    );
  }
  if (!me.context) {
    return (
      <Routes>
        <Route path="*" element={<ContextPage />} />
      </Routes>
    );
  }
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/am" element={<Guard perm="am:read"><AmListPage /></Guard>} />
        <Route path="/am/:id" element={<Guard perm="am:read"><AmFormPage /></Guard>} />
        <Route path="/pm" element={<Guard perm="pm:read"><PmListPage /></Guard>} />
        <Route path="/pm/:id" element={<Guard perm="pm:read"><PmFormPage /></Guard>} />
        <Route path="/reconciliacao" element={<Guard perm="match:read"><ReconciliationPage /></Guard>} />
        <Route path="/comparar" element={<Guard perm="match:read"><ComparePage /></Guard>} />
        <Route path="/painel" element={<Guard perm="dashboard:read"><DashboardPage /></Guard>} />
        <Route path="/auditoria" element={<Guard perm="audit:read"><AuditPage /></Guard>} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/login" element={<Navigate to="/" />} />
        <Route path="/contexto" element={<Navigate to="/" />} />
        <Route path="*" element={<div className="alert">Página não encontrada.</div>} />
      </Routes>
    </Shell>
  );
}
