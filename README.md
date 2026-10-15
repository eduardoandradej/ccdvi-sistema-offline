# Sistema DVI Offline — CCDVI/SEPOL

Plataforma web de **apoio** à identificação de vítimas de desastres (DVI), que funciona inteiramente em rede local
(sem internet). A referência metodológica é o *INTERPOL DVI Guide 2023* e os formulários AM/PM 2023.

> **Uso demonstrativo, somente com DADOS FICTÍCIOS.** O sistema **não** é homologado pela INTERPOL, **não** realiza
> identificação e **não** substitui a análise pericial nem o Identification Board. A conformidade legal (LGPD), a
> segurança para produção e os procedimentos de identificação ainda dependem de avaliação institucional.

| Camada | Tecnologia |
|---|---|
| API | Python 3.12+, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic |
| Banco | PostgreSQL 16 |
| Interface | React 18 + TypeScript + Vite (pt-BR, sem CDN, fontes do sistema) |
| Comparação AM×PM | Motor próprio explicável + RapidFuzz (semelhança textual auxiliar) |
| Implantação | Podman + Quadlet/systemd, Nginx como proxy reverso |
| Testes | pytest (API, contra PostgreSQL real), Playwright (E2E), Ruff |

Situação detalhada do que funciona, do que foi testado e do que falta: **[docs/STATUS_IMPLEMENTACAO.md](docs/STATUS_IMPLEMENTACAO.md)**.

## Como funciona

```mermaid
flowchart LR
  subgraph LAN["Rede local da operação (sem internet)"]
    AM["Base Ante Mortem<br/>entrevistas e desaparecidos"]
    PM["Base Post Mortem<br/>registros e exames"]
    CMD["Base Principal<br/>reconciliação e coordenação"]
  end
  subgraph SRV["Servidor Linux (Podman)"]
    WEB["Nginx<br/>interface web"]
    API["API FastAPI<br/>permissões e auditoria"]
    DB[("PostgreSQL")]
    ST[("Anexos<br/>SHA-256")]
  end
  AM & PM & CMD --> WEB --> API
  API --> DB
  API --> ST
```

```mermaid
flowchart LR
  L[Login] --> O[Operação] --> B[Base] --> F[Função]
  F --> AMf["Ficha AM<br/>entrevistas, sinais, anexos"]
  F --> PMf["Ficha PM<br/>exames, pertences, custódia"]
  AMf & PMf --> R["Comparação AM × PM<br/>coincidências e divergências"]
  R --> H["Análise humana<br/>encaminhamento pericial"]
```

## Telas

Capturadas automaticamente pelos testes E2E (Playwright), com dados fictícios.

| Seleção de contexto | Ficha AM: sinais particulares |
|---|---|
| ![Seleção de operação, base e função](docs/screenshots/02-contexto.png) | ![Ficha AM com sinais](docs/screenshots/04-am-caracteristicas.png) |
| **Anexos com hash e versões** | **Ficha PM com fotografia** |
| ![Anexos AM](docs/screenshots/05-am-anexos.png) | ![Anexos PM](docs/screenshots/06-pm-anexos.png) |
| **Candidatos AM × PM** | **Comparação lado a lado** |
| ![Candidatos](docs/screenshots/07-reconciliacao-candidatos.png) | ![Comparação](docs/screenshots/08-comparacao-lado-a-lado.png) |
| **Divergência de lateralidade** | **Auditoria (somente consulta)** |
| ![Divergências](docs/screenshots/09-comparacao-divergencias.png) | ![Auditoria](docs/screenshots/11-auditoria.png) |

## Estrutura

```
backend/            API FastAPI (app/), migrações (alembic/), testes (tests/)
frontend/           Interface React/TS (src/), testes E2E Playwright (e2e/)
deploy/             Containerfiles, Nginx, unidades Quadlet, exemplo de configuração
scripts/            dev-up, podman-deploy, backup/restore, verificação de recursos externos
tests/amostras/     Arquivos sintéticos (marca d'água "TESTE — DADO FICTÍCIO") para upload manual
docs/               Etapa A, arquitetura, rastreabilidade, RBAC, instalação, status, OpenAPI, screenshots
```

## Início rápido (desenvolvimento em Ubuntu 24.04)

Guia completo, inclusive implantação com Podman: [docs/INSTALACAO.md](docs/INSTALACAO.md).

```bash
# 1. Dependências do sistema
sudo apt install -y postgresql-16 python3.12-venv nodejs npm   # Node 22 recomendado

# 2. Banco (troque a senha)
sudo -u postgres psql -c "CREATE ROLE dvi LOGIN PASSWORD 'TROQUE_ESTA_SENHA';"
sudo -u postgres psql -c "CREATE DATABASE dvi OWNER dvi;"

# 3. Configuração
cp .env.example backend/.env          # ajuste DVI_DATABASE_URL e DVI_SEED_PASSWORD

# 4. Instala dependências, aplica migrações, cria dados fictícios e inicia API + interface
scripts/dev-up.sh
```

Acesso:

| Endereço | Uso |
|---|---|
| `http://<IP-do-servidor>:5173` | Interface em desenvolvimento (Vite, com proxy para a API) |
| `http://127.0.0.1:8000/api/health` | Saúde da API |
| `http://127.0.0.1:8000/api/openapi.json` | Esquema OpenAPI (cópia em [docs/openapi.json](docs/openapi.json)) |
| `http://<IP-do-servidor>:8080` | Interface em produção (Nginx via Podman/Quadlet) |

O Swagger UI fica desabilitado de propósito, porque carrega arquivos de CDN.

### Usuários de laboratório (fictícios)

São criados por `python -m app.seed`. A senha vem de `DVI_SEED_PASSWORD`; se a variável não for definida, o script gera
uma senha aleatória e a exibe uma única vez. Não existe senha padrão versionada.

| Usuário | Base | Função |
|---|---|---|
| `operador.am` | Base Ante Mortem | OPERADOR_AM |
| `operador.pm` | Base Post Mortem | OPERADOR_PM |
| `revisor` | Base Principal | REVISOR_RECONCILIACAO |
| `coordenador` | Base Principal | COORDENADOR |
| `admin.tic` | Base Principal | ADMIN_TIC |
| `auditor` | Base Principal | AUDITOR |
| `perito.multi` | Bases AM e PM | OPERADOR_AM e OPERADOR_PM |

Com `--demo-records`, o seed também cria registros fictícios para os cenários de demonstração 5, 6 e 7 do prompt:
uma AM com tatuagem de rosa no antebraço direito, um PM compatível, um PM com lateralidade oposta e casos com dados
ausentes.

## Testes

```bash
# API: 38 testes contra PostgreSQL real (banco dedicado dvi_test, recriado a cada execução)
cd backend
DVI_TEST_DATABASE_URL=postgresql+psycopg://dvi:SENHA@localhost:5432/dvi_test .venv/bin/pytest
.venv/bin/ruff check .

# Interface: verificação de tipos e build
cd ../frontend && npm run build
../scripts/check-offline-assets.sh        # garante que nenhum recurso externo é referenciado

# Backup -> restore em banco limpo, com verificação de SHA-256 dos anexos
SRC_URL=postgresql+psycopg://dvi:SENHA@localhost:5432/dvi SRC_STORAGE=backend/var/storage scripts/test-backup-restore.sh

# E2E (com API e interface rodando e seed --demo-records aplicado):
npx vite preview --port 4173 &            # serve dist/ com proxy para a API
DVI_E2E_PASSWORD=<senha do seed> npx playwright test
```

## Documentação

- [docs/ETAPA_A.md](docs/ETAPA_A.md): requisitos extraídos, decisões de arquitetura e dúvidas em aberto
- [docs/ARQUITETURA.md](docs/ARQUITETURA.md): diagrama lógico, modelo entidade-relacionamento e decisões de segurança
- [docs/RASTREABILIDADE.md](docs/RASTREABILIDADE.md): mapeamento entre campo/tela e o documento ou formulário de origem
- [docs/RBAC.md](docs/RBAC.md): matriz de permissões por endpoint (lista completa dos 50 endpoints)
- [docs/ESQUEMA_BANCO.md](docs/ESQUEMA_BANCO.md): tabelas, colunas, restrições e comandos de migração
- [docs/INSTALACAO.md](docs/INSTALACAO.md): instalação, implantação com Podman/Quadlet, backup/restore e teste sem internet
- [docs/STATUS_IMPLEMENTACAO.md](docs/STATUS_IMPLEMENTACAO.md): o que está implementado, testado, pendente e bloqueado
- [docs/screenshots/](docs/screenshots/): telas reais capturadas pelos testes E2E
- [LICENSES.md](LICENSES.md): licenças das dependências
