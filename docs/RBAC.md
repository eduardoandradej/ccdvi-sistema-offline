# Matriz RBAC

Fonte única: `backend/app/rbac.py`. A permissão de cada requisição depende da **função ativa** da sessão. Essa função
só vale se existir uma autorização ativa para usuário + operação + base + função, verificada a cada requisição.
Todos os dados são filtrados pela operação ativa. A base define a origem dos registros e **não concede** permissão.

## Permissões por função

| Permissão | OPERADOR_AM | OPERADOR_PM | REVISOR_RECONCILIACAO | COORDENADOR | ADMIN_TIC | AUDITOR |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| am:read | ✔ | | ✔ | | | |
| am:write | ✔ | | | | | |
| pm:read | | ✔ | ✔ | | | |
| pm:write | | ✔ | | | | |
| att_am:read | ✔ | | ✔ | | | |
| att_am:write | ✔ | | | | | |
| att_pm:read | | ✔ | ✔ | | | |
| att_pm:write | | ✔ | | | | |
| match:read | | | ✔ | | | |
| match:review | | | ✔ | | | |
| dashboard:read (só agregados) | | | | ✔ | | |
| admin:users / admin:health | | | | | ✔ | |
| audit:read | | | | | | ✔ |

## Endpoints

| Método e rota | Exige |
|---|---|
| POST /api/auth/login | público (com limitação de tentativas) |
| GET /api/health | público, sem dados |
| GET /api/auth/me, PUT/DELETE /api/auth/context, POST /api/auth/logout, GET /api/vocab | sessão válida |
| GET /api/am, GET /api/am/{id}, GET /api/am/{id}/history | am:read |
| POST /api/am, PUT /api/am/{id}, POST/PUT …/interviews, POST/DELETE …/marks, POST/DELETE …/effects | am:write |
| GET /api/pm, GET /api/pm/{id}, GET /api/pm/{id}/history | pm:read |
| POST /api/pm, PUT /api/pm/{id}, POST …/custody, POST/DELETE …/marks, POST/DELETE …/effects | pm:write |
| GET /api/attachments, GET /api/attachments/{id}, /content, /thumbnail, /verify | att_am:read ou att_pm:read, conforme o registro dono do anexo |
| POST /api/attachments, PATCH /api/attachments/{id}, POST …/versions, POST …/withdraw | att_am:write ou att_pm:write |
| GET /api/matching/candidates, /overview, /compare, /reviews | match:read |
| PUT /api/matching/review | match:review |
| GET /api/dashboard | dashboard:read |
| GET /api/audit | audit:read |
| GET/POST /api/admin/users, GET /api/admin/bases, POST /api/admin/authorizations, POST …/revoke | admin:users (não pode conceder autorização a si mesmo) |
| GET /api/admin/health | admin:health |

Toda escrita exige o cabeçalho `X-DVI-Request: 1`, como proteção contra CSRF. Acessos negados a anexos e trocas de
contexto negadas ficam registrados na auditoria.

## Testes que comprovam o isolamento

Arquivos em `backend/tests/`:

- `test_auth_context.py`
  - `test_contexto_nao_autorizado_403_e_auditado`
  - `test_usuario_multibase_alterna_contexto`
  - `test_revogacao_tem_efeito_imediato`
  - `test_admin_tic_nao_acessa_conteudo_sensivel`
  - `test_coordenador_ve_apenas_agregados`
  - `test_escrita_exige_cabecalho_csrf`
- `test_am_pm.py`
  - `test_isolamento_am_pm`
  - `test_isolamento_por_operacao`
- `test_attachments.py`
  - `test_controle_de_acesso_aos_anexos`
- `test_matching.py`
  - `test_operadores_nao_registram_revisao`
- `frontend/e2e/fluxos.spec.ts`: testes de PM e de contexto feitos pelo navegador.
