# Status da implementação — v0.1.0 (Etapa A concluída, Etapa B entregue, Etapa C iniciada)

Atualizado em 15/10/2026.

Legenda:

- ✅ implementado e testado automaticamente
- 🟡 implementado, com teste parcial ou manual
- ⏳ pendente
- ⛔ bloqueado por falta de informação ou de ambiente

## Ambiente e versões verificadas

Os testes rodaram em um contêiner **Ubuntu 24.04.5 LTS** (x86_64), sem Podman, com:

- PostgreSQL 16.15
- Python 3.13.16
- Node 22.22.0
- Chromium (Playwright 1.56.1)

As versões das bibliotecas estão em [LICENSES.md](../LICENSES.md) e fixadas em `backend/pyproject.toml` e
`frontend/package-lock.json`. Os testes usaram serviços reais: PostgreSQL, API uvicorn e a interface servida pelo Vite
com proxy para a API. Não há *mocks*.

## Resultados dos testes executados (15/10/2026)

| Suíte | Comando | Resultado |
|---|---|---|
| API (pytest, PostgreSQL real `dvi_test`) | `cd backend && .venv/bin/pytest -v` | **38 passed**, 0 failed |
| Lint Python | `.venv/bin/ruff check .` | sem erros |
| Tipos e build do frontend | `cd frontend && npm run build` | sem erros |
| E2E (Playwright/Chromium + API + PostgreSQL) | `npx playwright test` | **5 passed**, 0 failed |
| Recursos externos no build | `scripts/check-offline-assets.sh` | OK, nenhum |
| Backup → restore em banco limpo | `scripts/test-backup-restore.sh` | OK: 9 anexos verificados por SHA-256; contagens de AM, PM, anexos, sinais, itens e revisões idênticas |
| API servindo o banco restaurado | instância separada (porta 8001), verificação e download de anexos | OK, executado manualmente |
| Construção das imagens de contêiner | `docker build -f deploy/Containerfile.backend .` | **não concluída**: Docker Hub retornou 429 e o proxy do ambiente não é confiável dentro do contêiner |

Os testes E2E cobrem:

1. AM completo: cadastro, entrevista, sinal, foto, PDF, extensão forjada recusada e persistência após recarregar.
2. PM: cadastro com foto, e acesso a AM negado (403).
3. Reconciliação: comparação lado a lado com justificativas, divergência de lateralidade e encaminhamento, sem botão
   de identificação.
4. Usuário multibase: troca de contexto e elevação de privilégio negada (403).
5. Coordenador, auditor e TIC: menus restritos, rota direta bloqueada e API com 403.

Os testes E2E também registram todos os hosts acessados pelo navegador e falham se houver qualquer chamada externa.

## Funcionalidades

| Item | Status | Evidência |
|---|---|---|
| Login/logout, Argon2id, sessão de servidor, limitação de tentativas | ✅ | `tests/test_auth_context.py` |
| Seleção de operação → base → função, validada no servidor e auditada | ✅ | testes de API + E2E "Contexto" |
| Painel contextual com menus por permissão e indicação da base de origem | ✅ | E2E, screenshots 03 e 07 |
| Status do servidor local (só o que é verificável) | 🟡 | consulta `/api/health` a cada 30 s |
| RBAC no servidor por usuário + operação + base + função | ✅ | ver [RBAC.md](RBAC.md) |
| Cadastro AM em 7 abas, salvamento parcial e controle de versão (409 em conflito) | ✅ | `test_am_pm.py`, E2E AM |
| Entrevistas múltiplas por caso e bloqueio de duplicidade (nome + data de nascimento) | ✅ | `test_entrevistas_sinais_e_itens`, `test_duplicidade_am_bloqueada` |
| Sinais (404), itens (300–350), implantes (515), grau de certeza, situação por categoria | ✅ | testes de API |
| Cadastro PM em 7 abas, numeração conforme Anexo 9 com cena, UUID, custódia somente-inclusão | ✅ | `test_cadastro_pm_numeracao_e_custodia`, E2E PM |
| Requisitos mínimos para "pronto para reconciliação" validados no servidor | ✅ | `test_pronto_para_reconciliacao_exige_campos_minimos` |
| Anexos JPEG/PNG/PDF validados pelo conteúdo, SHA-256, UUID, armazenamento privado | ✅ | `test_attachments.py` |
| Extensão forjada, tipo proibido, arquivo corrompido e excesso de tamanho recusados | ✅ | `test_extensao_forjada_e_tipos_proibidos_rejeitados`, `test_limite_de_tamanho`, E2E |
| Upload com barra de progresso, confirmação somente após resposta do servidor, miniatura, visualizador, download | ✅ | E2E AM e PM, screenshot 05 |
| Remoção de EXIF/GPS na visualização, com original preservado | ✅ | `test_exif_gps_removido_na_visualizacao` |
| Nova versão sem sobrescrever; retirada com justificativa sem apagar o arquivo | ✅ | `test_nova_versao_preserva_original_e_retirada_nao_apaga` |
| Persistência após reinício (dados e anexos) | ✅ | `test_persistencia_apos_reinicio`, `test_anexo_persiste_apos_reinicio`, E2E com recarga da página |
| Trilha de auditoria imutável (gatilho no PostgreSQL) e tela de consulta | ✅ | `test_auditoria_e_imutavel` |
| Histórico por registro com diferenças antes/depois | ✅ | `test_cadastro_am_parcial_e_edicao` |
| Motor de comparação explicável v0.1.0 com RapidFuzz auxiliar | ✅ | `test_matching.py` (cenários compatível, lateralidade, ausência, negativo, idade, implante) |
| Tela de candidatos, comparação lado a lado com anexos autorizados, registro da análise humana | ✅ | E2E "Reconciliação", screenshots 07–09 |
| Sem identificação positiva automática (status inexistente; API retorna 422) | ✅ | `test_api_candidatos_e_revisao` |
| Painel do coordenador (só agregados) | ✅ | `test_coordenador_ve_apenas_agregados` |
| Administração TIC: usuários, concessão e revogação de autorizações, saúde do serviço | ✅ | `test_revogacao_tem_efeito_imediato`, E2E "Perfis", screenshot 12 |
| Interface sem chamadas externas | ✅ | E2E verifica os hosts requisitados; `scripts/check-offline-assets.sh` |
| Backup e restore com verificação de hashes | ✅ | `scripts/test-backup-restore.sh` (resultado acima). A cifragem com GPG está implementada, mas não foi testada (não havia chave). |
| Containerfiles, Nginx, Quadlet, `podman-deploy.sh` | ⛔ | escritos, mas **não executados**: sem Podman no ambiente e o build pelo Docker foi bloqueado (limite de requisições do Docker Hub e proxy) |
| Relatório comparativo imprimível com aviso "DOCUMENTO DEMONSTRATIVO — NÃO É LAUDO OFICIAL" | 🟡 | impressão pelo navegador (`window.print`); sem PDF gerado no servidor |

## Critérios de aceite do prompt

| Critério | Situação |
|---|---|
| 1. Iniciar seguindo o manual | 🟡 os passos do `dev-up.sh` foram executados aqui; implantação Podman/Quadlet não testada |
| 2. Usuário de laboratório criado por script, sem segredo embutido | ✅ |
| 3. Criar operação, AM e PM pelo navegador | 🟡 AM e PM pelo navegador ✅. A operação é criada pelo seed; ainda não existe tela de cadastro de operação ⏳ |
| 4. Anexar, recuperar com autenticação e persistir após reinício | ✅ |
| 5. Cenário de tatuagem de rosa / floral, cicatriz e 1,75 × 1,74 m | ✅ (seed `--demo-records` e testes) |
| 6. Lado oposto e incompatibilidades geram alerta, sem correspondência automática | ✅ |
| 7. Ausência não é evidência negativa | ✅ |
| 8. Isolamento de papéis | ✅ |
| 9. Backup e restauração em ambiente limpo, com hashes | ✅ script automatizado |
| 10. Fluxo sem internet, só na LAN | 🟡 sem chamadas externas verificado; o teste com a WAN fisicamente desligada precisa ser feito no laboratório |
| 11. Relatório comparativo rotulado como apoio | 🟡 impressão pelo navegador |
| Testes extras 12–17 | 12 ✅, 13 ✅, 14 ✅, 15 ✅, 16 ✅, 17 🟡 (mesma situação do critério 10) |

## Pendências (próximas etapas)

- ⏳ Exportação de AM, PM e comparação em PDF gerado no servidor, mais CSV/JSON com esquema versionado (Etapa C).
- ⏳ Tela de cadastro e encerramento de operação e de bases; troca de senha pelo próprio usuário.
- ⏳ Odontograma (630), árvore genealógica (560) e perfis STR (825).
- ⏳ Parâmetros e pesos do motor de comparação configuráveis pela interface; hoje ficam no código, mas a versão e os
  parâmetros já são gravados em cada revisão.
- ⏳ Verificação independente por segundo revisor (Anexo 6, 6.3).
- ⏳ Adaptação dos scripts de backup para volumes Podman (`podman exec dvi-db pg_dump`).
- ⏳ Validação da implantação Podman/Quadlet no servidor Ubuntu 24.04 do laboratório.
- ⏳ Pacotes de exportação/importação entre bases (Etapa D, apenas proposta em [ARQUITETURA.md](ARQUITETURA.md)).
- ⛔ Campos e telas do SPT Web: aguardam material autorizado.
- ⛔ Regras institucionais de obrigatoriedade, retenção e custódia: aguardam o CCDVI (ver [ETAPA_A.md](ETAPA_A.md)).

## Limites conhecidos

- A limitação de tentativas de login fica na memória do processo; com vários *workers*, o limite vale por processo.
- As miniaturas são geradas a cada requisição (sem cache). Isso é adequado para volumes de laboratório.
- Os rótulos em português são traduções do projeto. Os critérios de pontuação do motor de comparação não foram calibrados.
