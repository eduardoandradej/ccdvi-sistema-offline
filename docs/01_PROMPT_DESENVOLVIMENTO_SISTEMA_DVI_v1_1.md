# PROMPT PARA CLAUDE CODE — DESENVOLVIMENTO REAL DO SISTEMA DVI OFFLINE (v1.1)

Você atuará como arquiteto de software, desenvolvedor full-stack, engenheiro Linux/DevOps e responsável por testes. Seu objetivo não é produzir um mockup ou uma apresentação: **entregar um MVP funcional, com código-fonte, banco de dados, migrações, interface web, API, testes e instruções reproduzíveis de execução**, para uso exclusivamente demonstrativo com DADOS FICTÍCIOS, até avaliação e aprovação institucional.

## Contexto e objetivo

O projeto é uma plataforma autônoma de apoio à identificação de vítimas de desastres (DVI), no contexto de capacitação CCDVI/SEPOL/SSPTC/CEPF. Haverá três bases: (1) Comando e Reconciliação, (2) Ante Mortem (AM), com entrevistas de familiares e registros de pessoas desaparecidas, e (3) Post Mortem (PM), com registros de restos mortais e exames. A infraestrutura será Linux, rede Wi-Fi local e, futuramente, radioenlaces IP com VPN. A internet pode estar indisponível. Inicialmente desenvolva e prove o funcionamento em UMA instalação Linux com múltiplos perfis; depois prepare o projeto para três instâncias independentes.

Leia PRIMEIRO todos os documentos anexos: guia INTERPOL DVI 2023, formulários AM/PM e os anexos 4, 5, 6 e 9, além de requisitos institucionais e telas do SPT Web se fornecidos. Faça uma tabela de rastreabilidade entre campo/tela implementado e documento, seção, página e código original do formulário quando existente. Diferencie: (A) campos realmente encontrados nos documentos, (B) extensões propostas para o sistema e (C) campos do SPT Web confirmados pelos anexos. Não invente campos ou APIs do SPT Web; não alegue conformidade plena com a INTERPOL sem validação por especialistas. O DVI Guide e os formulários são REFERÊNCIA METODOLÓGICA, não licença para usar marcas ou sugerir homologação oficial.

## Stack obrigatória / preferencial (100% software livre)

- Ubuntu Server 24.04 LTS, x86_64, para o primeiro ambiente; projeto portátil para outros Linux.
- Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, Alembic, PostgreSQL.
- React + TypeScript + Vite, interface responsiva pt-BR, acessível e independente de CDN, fontes externas, mapas online ou APIs externas.
- Nginx como proxy reverso; Podman e Quadlet/systemd para implantação Linux. Ofereça também comando/script simples de desenvolvimento local. Não pressupor `podman-compose` instalado.
- Armazenamento de anexos em diretório privado, fora da pasta pública da aplicação, com metadados no PostgreSQL, hash SHA-256 e leitura autenticada. Usar alternativa aberta equivalente se justificar.
- RapidFuzz para comparação TEXTUAL auxiliar. Matching estruturado próprio em Python, testável e explicável. Não implantar reconhecimento facial nem identificação biométrica automática.
- pytest no backend, testes de API, testes básicos de UI/E2E com Playwright, Ruff, tipagem/validação e documentação OpenAPI.
- Restic ou scripts auditáveis para backups criptografados (sem chave embutida). Licenças de todas as dependências documentadas e compatíveis.

Evite Kubernetes, cloud, SaaS, microserviços desnecessários, modelos generativos online e qualquer dependência de internet em tempo de execução. Durante a preparação, download de dependências é permitido; forneça também procedimento de provisionamento e reinstalação em ambiente isolado, por pacotes/imagens/artefatos pré-baixados, com checksums e versões fixadas.


## REQUISITO CENTRAL DE UX — CONTEXTO DA OPERAÇÃO, BASE E PERFIL

**Implementar estas telas reais e integradas ao backend e banco de dados na ETAPA B; não criar apenas mockups.** O usuário deve ser orientado ao fluxo de trabalho de sua equipe, com separação clara entre fase DVI, base física e perfil de autorização. Base física NÃO é sinônimo de fase: uma pessoa com autorização pode operar mais de um módulo em uma base. A interface deve funcionar em português e sem internet, inclusive ícones, fontes e bibliotecas servidos localmente.

### Fluxo inicial obrigatório

1. **Login**: autenticação local; mostrar nome/cargo e status da rede somente quando o status for verificável.
2. **Selecionar operação/desastre**: por exemplo, `SIMULADO CCDVI 2026`, usando somente operações às quais a conta possui acesso; permitir buscar operação e distinguir treinamento de operação real.
3. **Selecionar base/posto**: Comando DVI, Ante Mortem (AM), Post Mortem (PM) ou outros postos cadastrados. Mostrar apenas bases autorizadas; a base é um local/unidade de trabalho configurável, nunca um papel de segurança.
4. **Selecionar função operacional**: caso o usuário tenha várias funções autorizadas, selecionar uma função ativa entre ADMIN_TIC, OPERADOR_AM, OPERADOR_PM, REVISOR_RECONCILIACAO, COORDENADOR, AUDITOR, usando rótulos pt-BR. Nunca permitir elevação de privilégio apenas por seleção no frontend.
5. **Abrir painel contextual** com nome da operação, base ativa, função, status da operação, menus autorizados, botão de troca de contexto e identificação da origem dos registros. Alterações de contexto devem ser validadas pelo backend e auditadas.

**Segurança**: ações de criar, ler, editar, anexar, exportar e revisar são conferidas servidor-side por usuário + operação + base + função + estágio do registro, em cada endpoint. Operador AM não deve editar PM e vice-versa, salvo autorização explícita. Coordenação e TIC não têm automaticamente permissão para acessar fotos, documentos pessoais e registros sensíveis. Um usuário pode ter mais de uma função/base sem precisar de múltiplas contas.

### Telas mínimas por função

| Contexto | Menus principais | Gravações efetivas |
|---|---|---|
| Base AM / entrevistador | Novo desaparecido, entrevistas, referências, anexos, consultar caso | Criar/editar registros AM e anexar referências |
| Base PM / perito | Recepção PM, características, exames, pertences, anexos, consultar caso | Criar/editar PM e registrar anexos/evidências |
| Comando / reconciliação | Revisão de fichas, candidatos AM×PM, discrepâncias, relatórios | Registrar análise humana, pendências e encaminhamentos |
| Coordenador | Situação da operação, pendências, qualidade, relatórios | Registrar aprovações permitidas e decisões administrativas |
| TIC | Saúde de serviços, usuários autorizados, backup/restore, conectividade | Administrar infraestrutura sem presumir acesso ao conteúdo sensível |
| Auditor | Histórico, trilha de ações, relatórios autorizados | Consulta de auditoria, sem alteração de conteúdo operacional |

Na primeira implementação, pelo menos as experiências OPERADOR_AM, OPERADOR_PM e REVISOR_RECONCILIACAO precisam estar totalmente operacionais. Os demais perfis podem ser entregues progressivamente, mas sem telas/menus fictícios aparentando funcionalidades concluídas.

### Formulários segmentados por abas

- **AM**: Identificação/cadastro do desaparecido; Entrevistas/fontes; Características/sinais particulares; Vestimentas/objetos informados; Dados médicos/odontológicos de referência; Fotos e documentos; Histórico/auditoria. Ao alternar abas não perder dados; permitir salvar rascunho e continuar, com progresso de campos obrigatórios e validações claras.
- **PM**: Recepção e identificadores; Características/achados; Exames (incluindo papiloscopia, odontologia e amostras conforme documentação disponível); Fotografias; Pertences/evidências; Cadeia de custódia; Histórico/auditoria. Respeitar distinção entre relato AM e observação PM, inclusive incertezas.
- **Reconciliação**: Busca/lista de possíveis pares AM×PM, comparação lado a lado, atributos coincidentes/divergentes/não informados, anexos autorizados e decisão de encaminhamento à avaliação especializada. Nenhum botão de identificação positiva automática.

A origem/etapa de cada campo precisa ser rastreável aos documentos oficiais anexados, e as extensões propostas devem ser identificadas como tal. Não reproduzir por suposição uma tela ou aba do SPT Web não fornecida.

### Anexos reais: identidade, fotografias e documentos

Implementar na primeira versão um **componente de anexação reutilizável** para AM e PM, com:

- Tipos configuráveis: documento de identificação, fotografia de referência (AM), fotografia de achado/exame (PM), documento médico, odontológico, outro documento, registro de pertencente/objeto e material administrativo autorizado. Distinguir **documento do entrevistado** de **documento da pessoa desaparecida** e de **documento relacionado ao registro PM**; não confundi-los.
- Formatos iniciais JPEG/PNG/PDF (PDF multipágina); permitir vários anexos por caso e classificar com tipo, título/descrição, fonte/origem, usuário responsável, data/hora de obtenção e data/hora de ingestão, operação/base e vínculo ao registro. Metadados específicos de cadeia de custódia quando cabíveis.
- Upload funcional com barra de progresso, confirmação após persistência real, visualização em miniatura onde autorizado, visualizador ampliado/download autenticado, busca por tipo e indicação do vínculo. Visualizar não pode disponibilizar URL pública ou recursos CDN; autenticação em todos os endpoints.
- Preservação de original, SHA-256, armazenamento fora do webroot, validação de formato/conteúdo/tamanho, nomes saneados, recusa de tipos não permitidos, proteção contra upload abusivo; revisão de metadados e trilha de alterações. Evitar EXIF/geoexposição não autorizada nos previews e downloads.
- Status de anexação e integridade (enviado, armazenado, erro), sem sucesso falso. O arquivo continua acessível após reinício. Exclusão/revisão de evidência não pode eliminar original silenciosamente; definir política de retenção, substituição por versão e registro de custódia.
- Usar arquivos de **demonstração inteiramente sintéticos**, inclusive imagens genéricas e modelos de documentos contendo marca d'água de TESTE e nenhuma identidade real.

**Acesso local**: mesmo sem internet, os notebooks conectados à Wi-Fi/LAN abrem a aplicação hospedada no servidor Linux. Isso não significa funcionamento de cada notebook quando perde também a LAN. O modo PWA com rascunho no cliente desconectado é uma melhoria futura, deve ser especificado separadamente e não prometido como pronto.

### Testes de aceitação extras obrigatórios

12. Usuário AM autorizado faz login, escolhe operação/base AM, cadastra desaparecido, entrevista, características, adiciona fotografia de referência e PDF sintético de identificação; reinicia aplicação e confirma persistência e download autenticado.
13. Usuário PM autorizado acessa base PM, cadastra caso PM com fotos fictícias, pertences e observações; não consegue editar registros AM por endpoint nem manipular anexos AM restritos.
14. Um profissional com autorização para duas bases alterna o contexto corretamente; usuário sem autorização recebe 403 ao tentar trocar para base diferente por API; a interface não deve apenas esconder botões.
15. Anexos devem possuir tipo, origem, responsável, data, UUID, hash; tentativa de forjar extensão ou acesso por URL direta não autorizada deve falhar.
16. Painel Comando/Reconciliação lista registros AM/PM de uma operação, permite comparação lado a lado e apresenta os anexos conforme permissão; não registra identificação positiva automática.
17. Cadastro e anexos AM/PM funcionam exclusivamente na rede local; interface não faz chamadas externas durante uso. Testar isso explicitamente.

**Entregáveis adicionais**: documentação de fluxos (screenshots reais após implementação), matriz RBAC por endpoint, modelo de dados com entidades Usuário, Autorização, Operação, Base, Contexto, Caso AM, Entrevista, Registro PM, Anexo, Evidência, Evento de Auditoria e Comparação; demonstrar testes de isolamento por operação/base/função.


## MVP funcional mínimo: implementar, não apenas desenhar

**1. Acesso e operação**
- Login/logout, senhas com hash robusto, gestão de usuários habilitados, RBAC com papéis ADMIN_TIC, OPERADOR_AM, OPERADOR_PM, REVISOR, COORDENADOR e AUDITOR.
- Controle de acesso no backend por operação e por base; sem endpoints sensíveis abertos; sessão segura e tratamento de erros.
- Cadastro de operação/desastre e de base operativa; dashboard simples de contagem e status; registro de responsável e data/hora (com timezone coerente).
- Interface pt-BR, busca e filtros, formulários com validações, salvamento parcial/rascunho, confirmação de gravação real no banco e visualização após reiniciar o sistema.

**2. Ante Mortem (AM)**
- Cadastro de pessoa desaparecida e de entrevistado/fonte; vínculo de múltiplas entrevistas/documentos ao mesmo caso, evitando duplicação inadvertida.
- Formulário AM baseado em uma PRIMEIRA SELEÇÃO RASTREÁVEL de campos do formulário oficial 2023: identificação nominal, faixa etária e outras descrições disponíveis, características físicas, marcas/sinais (tatuagem, cicatriz, localização e lado), vestimentas, adornos/objetos, histórico médico/odontológico, anexos e observações.
- Para cada informação importante, armazenar origem/fonte, data, grau de certeza ou relato, sem converter relato familiar automaticamente em fato confirmado.

**3. Post Mortem (PM)**
- Registro individualizado de restos mortais, identificador DVI conforme Anexo 9 (configurável, com controle de unicidade), e UUID interno independente, único entre bases.
- Formulário PM inicial: exame descritivo, idade e estatura estimadas quando disponíveis, marcas/sinais e localização anatômica/lateralidade, vestimentas, pertences associados, status de necropapiloscopia/odontologia/DNA, anexos fotográficos, informações de custódia e observações.
- Não codificar uma correspondência presumida de PM com pessoa AM sem revisão formal; não fundir registros automaticamente.

**4. Documentos e fotografias**
- Upload autenticado de JPEG/PNG/PDF, tamanho máximo configurável, validação real do arquivo (não apenas extensão), armazenamento protegido, hash SHA-256, associação AM/PM, download autorizado, metadados, audit trail e bloqueio de acesso por URL pública.
- Registro de origem, autor, data, tipo, descrição, identificador de evidência e histórico. Nunca sobrescrever silenciosamente um anexo original; utilizar novas versões.

**5. Motor de CORRESPONDÊNCIA AM × PM (prioridade)**
- Tela comparativa AM lado a lado PM, com destaque para coincidências, divergências, ausências e incertezas; links de anexos autorizados.
- Comparar inicialmente atributos estruturados: idade/faixa estimada (com margem e incerteza), estatura quando confiável, tatuagens, cicatrizes, localizações e lados, vestimentas, joias e próteses/implantes. Usar normalização de vocabulário (ex.: tipos de marcas, regiões anatômicas, lateralidade), sem supor que palavras parecidas signifiquem mesma característica.
- RapidFuzz SOMENTE para semelhança textual auxiliar após normalização, nunca como evidência conclusiva. Diferenciar explicitamente `não informado`, `não observado`, `não examinável`, `negativo` e `desconhecido`; ausência NÃO deve virar incompatibilidade.
- Produzir lista ordenada de *candidatos para revisão humana*, com razões explicáveis por campo, indicadores de divergências e referência aos registros originais. Não apresentar score numérico como "probabilidade de identificação" sem calibração/validação pericial. Se utilizar pontuação interna para ordenação, rotular como índice técnico experimental e mostrar seus limites.
- Critérios e pesos de ordenação configuráveis/versão do algoritmo gravada no resultado; registrar data, parâmetros e autor da revisão. Impedir conclusão positiva por ação automatizada.
- Fluxo de revisão: sugerido -> em análise -> informações complementares necessárias / descartado / encaminhado à avaliação técnica. Identificação formal e laudo conclusivo FORA do MVP, salvo registro documental de decisão externa autorizada. Não utilizar rosto/fotografia como biometria; somente visualização comparativa manual.
- Gerar casos fictícios de teste, inclusive falsos positivos plausíveis, falsos negativos e divergências críticas. Demonstrar que o sistema não confirma identidade sozinho.

**6. Relatórios, auditoria e exportação**
- Exportar AM, PM e relatório de comparação para PDF com status "DOCUMENTO DEMONSTRATIVO — NÃO É LAUDO OFICIAL", mais CSV/JSON com esquema versionado.
- Trilha de auditoria pesquisável (autor, data, ação, objeto, antes/depois sem expor segredos), sem opção comum de apagar histórico. Definir regras de retenção e revisão de segurança.
- Uma rotina REAL de backup e restore testada. Scripts e documentação de teste.

**7. Operação sem internet e futura integração entre bases**
- A aplicação deve funcionar em LAN sem conectividade WAN; nenhuma chamada de frontend/backend para domínios externos. Fornecer teste reprodutível bloqueando saída à internet.
- Para primeira versão distribuída, preferir pacotes de exportação/importação autorizados, criptografados e autenticados, com manifesto, IDs únicos, hashes, versão de esquema, importação idempotente e detecção de conflitos encaminhados à revisão. Transferência via mídia removível autorizada deve ser possível, sem sincronizar diretamente bancos PostgreSQL em múltiplos writers.
- Sincronização automática entre bases e integração SPT Web são fases FUTURAS. Antes de alegar que funcionam, devem ter conectores reais, APIs/contratos aprovados, testes e tratamento de conflitos. Não criar um botão de "sincronizar" que apenas simule sucesso.

## Segurança, privacidade e operação responsável

Todos os dados de demonstração devem ser sintéticos. Não importar nomes, imagens cadavéricas, biometria ou documentos pessoais reais nos testes. Planejar criptografia de disco/backup, HTTPS interno com certificados institucionais, segregação de rede, rotação de segredos, logs, proteção de dados sensíveis, cadeia de custódia e aprovação pela DGTIC. Não alegar conformidade legal ou segurança para produção antes de auditoria, avaliação jurídica/LGPD e validação dos procedimentos de identificação.

## Estrutura esperada do repositório

Crie e mantenha algo semelhante a:

```
dvi-offline/
  backend/              # API, domínio, modelos, migrações, testes
  frontend/             # telas reais com chamadas à API
  deploy/               # Containerfiles, Quadlet, nginx, exemplos de config
  scripts/              # instalação, seed fictício, backup/restore, smoke tests
  docs/                 # arquitetura, dicionário de dados, rastreabilidade, manuais
  tests/                # cenários integrados, fixtures e testes e2e
  .env.example          # sem senhas reais
  README.md
  LICENSES.md
```

Inclua diagrama lógico simples (Mermaid ou SVG gerado de código), diagrama entidade-relacionamento, OpenAPI, `README.md` com versões verificadas, comandos passo a passo para Ubuntu 24.04 e URLs/portas de acesso. Documente os requisitos mínimos de máquina e os limites dos testes. Preferir scripts reexecutáveis, logs legíveis e ambientes isolados. Não codifique senhas padrão de produção nem segredos nos arquivos versionados.

## Plano de trabalho obrigatório

TRABALHE EM ENTREGAS REAIS, SEM TENTAR RESOLVER TUDO EM UMA ÚNICA RESPOSTA:

ETAPA A — Leia anexos, extraia requisitos rastreáveis, proponha arquitetura mínima, esquema de dados, telas e critérios de aceitação. Apresente decisões e dúvidas bloqueantes curtas, sem interromper por detalhes que possam ser assumidos e explicitados.

ETAPA B — ENTREGUE SISTEMA EXECUTÁVEL: projeto inicial, banco/migrações, API, autenticação, criação/edição/listagem AM e PM, upload/consulta de anexos, frontend integrado, seeds fictícios e testes. Rode efetivamente o ambiente e apresente provas verificáveis dos endpoints e telas, quando tiver acesso às ferramentas. Se não puder executar, informe com precisão o que não foi testado; nunca invente logs ou resultados.

ETAPA C — Implemente matching explicável AM/PM com revisão humana, relatórios, auditoria e casos de teste negativos; execute e reporte testes de segurança de acesso e regressão.

ETAPA D — Scripts de implantação Podman/Quadlet, backup/restore, operação sem internet e documentação do laboratório. Depois proponha, SEM alegar pronta, a evolução para 3 bases e pacotes de sincronização.

## Demonstração obrigatória e critérios de aceite

Ao final da ETAPA C, eu devo conseguir:
1. Iniciar a aplicação em Linux seguindo apenas o manual e os comandos fornecidos.
2. Entrar com um usuário de laboratório criado por script e alterável; nenhum segredo real embutido.
3. Criar uma operação, um registro AM e um PM pelo navegador.
4. Anexar fotografias fictícias e PDFs de teste, recuperá-los com autenticação, e confirmar persistência após reiniciar os serviços.
5. Criar um registro AM fictício com tatuagem de rosa no antebraço direito, cicatriz no joelho esquerdo, estatura aproximada de 1,75 m; criar PM com tatuagem floral no mesmo local, cicatriz correspondente, estatura estimada 1,74 m. Ver a sugestão de revisão com a explicação de cada semelhança e ressalvas.
6. Criar outro PM com tatuagem em lado diferente e outras incompatibilidades; ver o alerta de divergência e impedir correspondência declarada automaticamente.
7. Criar casos com campos ausentes; comprovar que ausência não é tratada como evidência negativa.
8. Confirmar isolamento de papéis (ex.: AM não edita PM, não autorizado não baixa anexo).
9. Fazer backup, recuperar em ambiente limpo e validar dados/anexos e hashes.
10. Repetir o fluxo com a internet desligada, somente na LAN, sem CDNs/serviços online.
11. Obter relatório comparativo claramente rotulado como instrumento de apoio, sem identidade positiva automática.

Condição de conclusão: não considero entregue um mockup, HTML estático, frontend com arrays em memória, CRUD falso, botões sem backend ou uma API sem telas navegáveis. Todos os recursos marcados como concluídos devem efetivamente existir e ser demonstráveis. Mantenha `docs/STATUS_IMPLEMENTACAO.md` com o que está implementado, testado, pendente e bloqueado.

**COMECE AGORA pela ETAPA A e depois implemente a ETAPA B no repositório. Ao terminar cada etapa, apresente arquivos criados/alterados, comandos utilizados, testes executados, seus resultados reais e próximos passos. Continue com as etapas seguintes conforme a capacidade de execução, sem substituir implementação por longas explicações.**
