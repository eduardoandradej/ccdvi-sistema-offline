# Sistema DVI Offline — CCDVI/SEPOL

**Plataforma web de apoio à identificação de vítimas de desastres (DVI).** Funciona inteiramente na rede local de cada
base operacional, sem depender de internet. A referência metodológica é o *INTERPOL DVI Guide 2023* e seus formulários
Ante Mortem (AM) e Post Mortem (PM).

![Mapa estratégico de conectividade DVI](docs/imagens/01-mapa-estrategico-dvi.png)

> [!IMPORTANT]
> **Uso demonstrativo, somente com DADOS FICTÍCIOS.** O sistema não é homologado pela INTERPOL, não realiza
> identificação e não substitui a análise pericial nem o Identification Board. Conformidade com a LGPD, segurança
> para produção e procedimentos de identificação ainda dependem de avaliação institucional.

**Sumário:**
[Contexto operacional](#contexto-operacional) ·
[O que o sistema faz](#o-que-o-sistema-faz) ·
[Telas](#telas) ·
[Arquitetura do software](#arquitetura-do-software) ·
[Situação atual](#situação-atual) ·
[Preparar VM KVM](#preparação-da-vm-no-rocky-linux--kvm) ·
[Como executar](#como-executar) ·
[Testes](#testes) ·
[Documentação](#documentação)

---

## Contexto operacional

Uma operação DVI se organiza em **três bases**, e cada uma opera de forma autônoma, com servidor local, Wi-Fi para os
notebooks, nobreak e rádio:

| Base | Função | Uso no sistema |
|---|---|---|
| **Base Principal / Comando** | Coordenação, consolidação e reconciliação | Revisão de candidatos AM×PM, painel da operação, auditoria, TIC |
| **Base Ante Mortem (AM)** | Entrevistas com familiares, cadastro de desaparecidos | Fichas AM, entrevistas, sinais particulares, documentos e fotografias de referência |
| **Base Post Mortem (PM)** | Núcleo IML / perícia | Fichas PM, exames, pertences, cadeia de custódia, fotografias |

![Topologia: rede autônoma para três bases operacionais](docs/imagens/07-topologia-conectividade-dvi.png)

<details>
<summary><strong>Base Ante Mortem em detalhe</strong></summary>

![Base Ante Mortem](docs/imagens/04-base-ante-mortem.png)

</details>

### Infraestrutura de cada base

| Física | Lógica |
|---|---|
| ![Infraestrutura física da base DVI](docs/imagens/05-infraestrutura-fisica.png) | ![Infraestrutura lógica da base DVI](docs/imagens/06-infraestrutura-logica.png) |

> [!NOTE]
> As ilustrações mostram o **cenário-alvo**. Hoje o sistema roda e foi testado em **uma instalação** com múltiplos
> perfis e bases. A sincronização entre bases e a integração com sistemas oficiais estão planejadas, mas ainda **não
> foram implementadas** (ver [Situação atual](#situação-atual)).

---

## O que o sistema faz

- **Acesso por contexto.** O usuário entra, escolhe operação → base → função e vê apenas os módulos permitidos. O
  servidor confere a autorização em toda requisição; esconder botões na tela não basta.
- **Fichas AM e PM em abas.** Seguem os formulários INTERPOL 2023, com salvamento parcial e numeração conforme o
  Anexo 9 (ex.: `AM55-0001`, `PM55-0001-A`). Cada campo exibe o código do formulário de origem.
- **Fotografias e documentos.** Aceita JPEG, PNG e PDF, validados pelo conteúdo. O original é preservado com hash
  SHA-256, e as versões novas nunca sobrescrevem o anterior. A visualização remove dados de localização (GPS), e todo
  acesso é autenticado.
- **Comparação AM × PM.** Mostra os candidatos lado a lado e explica coincidências, divergências e informações
  ausentes. Ausência não conta como incompatibilidade. **Não existe identificação automática:** o sistema apenas
  encaminha os pares à análise pericial.
- **Auditoria.** Cada ação fica registrada em uma trilha que o próprio banco de dados impede de alterar ou apagar.

## Telas

Capturadas automaticamente pelos testes de ponta a ponta (Playwright), com dados fictícios.

| Seleção de operação, base e função | Ficha AM: sinais particulares |
|---|---|
| ![Seleção de contexto](docs/screenshots/02-contexto.png) | ![Ficha AM](docs/screenshots/04-am-caracteristicas.png) |
| **Anexos com hash e versões** | **Ficha PM com fotografia** |
| ![Anexos AM](docs/screenshots/05-am-anexos.png) | ![Anexos PM](docs/screenshots/06-pm-anexos.png) |
| **Candidatos AM × PM** | **Comparação lado a lado** |
| ![Candidatos](docs/screenshots/07-reconciliacao-candidatos.png) | ![Comparação](docs/screenshots/08-comparacao-lado-a-lado.png) |
| **Divergência de lateralidade** | **Trilha de auditoria** |
| ![Divergências](docs/screenshots/09-comparacao-divergencias.png) | ![Auditoria](docs/screenshots/11-auditoria.png) |

## Arquitetura do software

```mermaid
flowchart LR
  subgraph LAN["Rede local da base (sem internet)"]
    N["Notebooks e tablets"]
  end
  subgraph SRV["Servidor Linux — Podman/Quadlet"]
    WEB["Nginx<br/>interface web"]
    API["API FastAPI<br/>permissões e auditoria"]
    DB[("PostgreSQL 16")]
    ST[("Anexos<br/>originais + SHA-256")]
  end
  N --> WEB --> API
  API --> DB
  API --> ST
```

```mermaid
flowchart LR
  L[Login] --> O[Operação] --> B[Base] --> F[Função]
  F --> AMf["Ficha AM<br/>entrevistas, sinais, anexos"]
  F --> PMf["Ficha PM<br/>exames, pertences, custódia"]
  AMf & PMf --> R["Comparação AM × PM"]
  R --> H["Análise humana<br/>encaminhamento pericial"]
```

| Camada | Tecnologia |
|---|---|
| API | Python 3.12+, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic |
| Banco | PostgreSQL 16 |
| Interface | React 18 + TypeScript + Vite (pt-BR, sem CDN, fontes do sistema) |
| Comparação AM×PM | Motor próprio explicável + RapidFuzz (semelhança textual auxiliar) |
| Implantação | Podman + Quadlet/systemd, Nginx como proxy reverso |
| Testes | pytest (API, contra PostgreSQL real), Playwright (E2E), Ruff |

```
backend/            API FastAPI (app/), migrações (alembic/), testes (tests/)
frontend/           Interface React/TS (src/), testes E2E Playwright (e2e/)
deploy/             Containerfiles, Nginx, unidades Quadlet, exemplo de configuração
infra/kvm/          Autoinstall Ubuntu 24.04 LTS no KVM/Rocky Linux e runbook da VM
scripts/            dev-up, podman-deploy, backup/restore, verificação de recursos externos
tests/amostras/     Arquivos sintéticos (marca d'água "TESTE — DADO FICTÍCIO") para upload manual
docs/               Especificação, arquitetura, rastreabilidade, RBAC, instalação, status, imagens
```

## Situação atual

Versão **0.1.0**, primeiro MVP. Detalhamento completo em
[docs/STATUS_IMPLEMENTACAO.md](docs/STATUS_IMPLEMENTACAO.md).

| | |
|---|---|
| ✅ **Testado** | Login e contexto, fichas AM/PM, anexos, comparação e revisão, isolamento entre perfis, auditoria, backup/restore |
| 🧪 **Resultados** | 38 testes de API e 5 testes de navegador aprovados; backup restaurado com 9 anexos verificados por SHA-256 |
| ⏳ **Pendente** | Implantação Podman/Quadlet validada em servidor real, teste com a internet fisicamente desligada, exportação PDF/CSV, cadastro de operações pela interface |
| 🗺️ **Planejado** | Sincronização entre as três bases por pacotes cifrados; integração com sistemas oficiais (SPT Web) |

## Preparação da VM no Rocky Linux / KVM

Antes de instalar a aplicação, é possível provisionar um Ubuntu Server 24.04 LTS em KVM/QEMU sobre Rocky Linux,
por meio de **Autoinstall + NoCloud**, sem interação com as telas do instalador.

| Item do laboratório | Configuração |
|---|---|
| Hipervisor | Rocky Linux, QEMU/KVM e libvirt |
| VM | `ccdvi-ubuntu-lab` |
| Sistema convidado | Ubuntu Server 24.04.5 LTS |
| Recursos | 4 vCPUs, 16 GiB de RAM, disco de 80 GiB em qcow2 |
| Armazenamento | Pool `default`, em SSD (`/var/lib/libvirt/images`) |
| Rede | Bridge `br-ex`, conectada à LAN; IP inicialmente via DHCP |
| Acesso | Usuário administrativo `suporte` e OpenSSH |

- **[Runbook de criação da VM Ubuntu no KVM](infra/kvm/Runbook_Criacao_VM_Ubuntu_KVM_RockyLinux.md)** — preparação, execução, verificações e recuperação.
- **[Script de instalação automatizada](infra/kvm/instalar-ubuntu-ccdvi-kvm.sh)** — deve ser executado **no Rocky Linux hospedeiro**, com `sudo` disponível, e apenas ao criar uma VM nova.

O script solicita uma senha inicial no terminal e automatiza o restante do instalador. A VM criada não deve ser
reprovisionada por cima de outra já existente. O ambiente DVI permanece **demonstrativo**, com dados fictícios.
Não coloque senhas, discos `.qcow2`, imagens ISO NoCloud ou arquivos de configuração com credenciais no Git.

**Sequência de leitura:** runbook KVM → runbook Sistema DVI → runbook CCDVI Drive.
O Drive tem [repositório próprio](https://github.com/eduardoandradej/ccdvi-drive-offline).

## Como executar

Para instalação **nativa no Ubuntu 24.04 LTS** e operação via `systemd`, siga o
**[Runbook de Instalação e Operação do Sistema DVI](Runbook_Instalacao_Ubuntu_CCDVI_Sistema.txt)**.
A configuração ilustrada abaixo é apenas uma visão resumida; o runbook contém as etapas completas.

Guia da implantação alternativa com Podman/Quadlet e procedimentos offline:
[docs/INSTALACAO.md](docs/INSTALACAO.md).

```bash
# No Ubuntu já instalado: acessar o repositório
cd ~/ccdvi-sistema-offline

# Para a primeira instalação, seguir o runbook Sistema DVI antes de iniciar serviços.
# Após configurar o serviço ccdvi.service conforme o runbook:
sudo systemctl start ccdvi.service
sudo systemctl status ccdvi.service --no-pager

# Operação diária:
sudo systemctl stop ccdvi.service
sudo systemctl restart ccdvi.service
sudo journalctl -u ccdvi.service -f   # Ctrl+C fecha os logs, NÃO encerra o serviço

# Verificação da aplicação:
curl -fsS http://127.0.0.1:5173/api/health
```

| Endereço | Uso |
|---|---|
| `http://<IP-do-servidor>:5173` | Interface em desenvolvimento |
| `http://<IP-do-servidor>:8080` | Interface em produção (Nginx via Podman/Quadlet) |
| `http://127.0.0.1:8000/api/health` | Saúde da API |
| `http://127.0.0.1:8000/api/openapi.json` | Esquema OpenAPI (cópia em [docs/openapi.json](docs/openapi.json)) |

### Usuários de laboratório (fictícios)

Criados por `python -m app.seed`. A senha vem de `DVI_SEED_PASSWORD`; se a variável não for definida, o script gera
uma senha aleatória e a exibe uma única vez. Não há senha padrão no repositório.

| Usuário | Base | Função |
|---|---|---|
| `operador.am` | Base Ante Mortem | OPERADOR_AM |
| `operador.pm` | Base Post Mortem | OPERADOR_PM |
| `revisor` | Base Principal | REVISOR_RECONCILIACAO |
| `coordenador` | Base Principal | COORDENADOR |
| `admin.tic` | Base Principal | ADMIN_TIC |
| `auditor` | Base Principal | AUDITOR |
| `perito.multi` | Bases AM e PM | OPERADOR_AM e OPERADOR_PM |

Com `--demo-records`, o seed também cria registros fictícios para os cenários de demonstração. Entre eles, uma AM
com tatuagem de rosa no antebraço direito, um PM compatível, um PM com lateralidade oposta e casos com dados ausentes.

## Testes

```bash
# API: testes contra PostgreSQL real (banco dvi_test, recriado a cada execução)
cd backend
DVI_TEST_DATABASE_URL=postgresql+psycopg://dvi:SENHA@localhost:5432/dvi_test .venv/bin/pytest
.venv/bin/ruff check .

# Interface: tipos e build; garante que nenhum recurso externo é referenciado
cd ../frontend && npm run build && ../scripts/check-offline-assets.sh

# Backup -> restore em banco limpo, com verificação de SHA-256 dos anexos
SRC_URL=postgresql+psycopg://dvi:SENHA@localhost:5432/dvi SRC_STORAGE=backend/var/storage scripts/test-backup-restore.sh

# E2E (API e interface rodando, seed --demo-records aplicado)
npx vite preview --port 4173 &
DVI_E2E_PASSWORD=<senha do seed> npx playwright test
```

## Documentação

| Documento | Conteúdo |
|---|---|
| [ETAPA_A.md](docs/ETAPA_A.md) | Requisitos extraídos dos documentos INTERPOL, decisões e dúvidas em aberto |
| [ARQUITETURA.md](docs/ARQUITETURA.md) | Diagramas, modelo entidade-relacionamento, motor de comparação e segurança |
| [RASTREABILIDADE.md](docs/RASTREABILIDADE.md) | Cada campo/tela relacionado ao formulário ou anexo de origem |
| [RBAC.md](docs/RBAC.md) | Matriz de permissões e lista dos endpoints |
| [ESQUEMA_BANCO.md](docs/ESQUEMA_BANCO.md) | Tabelas, colunas, restrições e migrações |
| [Runbook KVM](infra/kvm/Runbook_Criacao_VM_Ubuntu_KVM_RockyLinux.md) | Provisionamento automático de VM Ubuntu no KVM/Rocky Linux |
| [Script KVM](infra/kvm/instalar-ubuntu-ccdvi-kvm.sh) | Criação de VM com Autoinstall/NoCloud |
| [Runbook Sistema DVI](Runbook_Instalacao_Ubuntu_CCDVI_Sistema.txt) | Instalação nativa e administração do `ccdvi.service` |
| [INSTALACAO.md](docs/INSTALACAO.md) | Instalação, Podman/Quadlet, backup/restore e operação sem internet |
| [STATUS_IMPLEMENTACAO.md](docs/STATUS_IMPLEMENTACAO.md) | Implementado, testado, pendente e bloqueado |
| [LICENSES.md](LICENSES.md) | Licenças das dependências |

Documentos de referência em `docs/`: especificação de desenvolvimento v1.1, fluxo de telas, *INTERPOL DVI Guide
2023*, formulários AM/PM e Anexos 4, 5, 6 e 9.
