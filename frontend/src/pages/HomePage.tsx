import { Link } from "react-router-dom";
import { useSession } from "../session";

interface Tile {
  perm: string;
  to: string;
  title: string;
  text: string;
}

const TILES: Tile[] = [
  { perm: "am:write", to: "/am?novo=1", title: "Novo desaparecido", text: "Abrir ficha AM e iniciar entrevista." },
  { perm: "am:read", to: "/am", title: "Consultar casos AM", text: "Fichas, entrevistas, características e anexos." },
  { perm: "pm:write", to: "/pm?novo=1", title: "Recepção PM", text: "Registrar novos restos mortais (numeração Anexo 9)." },
  { perm: "pm:read", to: "/pm", title: "Consultar casos PM", text: "Exames, achados, pertences, custódia e anexos." },
  { perm: "match:read", to: "/reconciliacao", title: "Candidatos AM×PM", text: "Comparação lado a lado e encaminhamento." },
  { perm: "dashboard:read", to: "/painel", title: "Situação da operação", text: "Contagens agregadas por status." },
  { perm: "audit:read", to: "/auditoria", title: "Trilha de auditoria", text: "Histórico de ações do sistema." },
  { perm: "admin:users", to: "/admin", title: "Usuários e saúde", text: "Contas, autorizações e serviços." },
];

export default function HomePage() {
  const { me, can } = useSession();
  const ctx = me!.context!;
  const tiles = TILES.filter((t) => can(t.perm));
  return (
    <div>
      <h1>Painel — {ctx.role_label}</h1>
      <p className="muted">
        {ctx.operation.name} · {ctx.base.name}
        {ctx.operation.disaster_nature ? ` · ${ctx.operation.disaster_nature}` : ""}
        {ctx.operation.disaster_date ? ` · ${new Date(ctx.operation.disaster_date + "T12:00").toLocaleDateString("pt-BR")}` : ""}
      </p>
      <p className="small muted">
        Registros criados neste contexto terão origem: <strong>{ctx.base.name}</strong>.
      </p>
      <div className="tiles">
        {tiles.map((t) => (
          <Link key={t.to} to={t.to} className="tile">
            <strong>{t.title}</strong>
            <span>{t.text}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
