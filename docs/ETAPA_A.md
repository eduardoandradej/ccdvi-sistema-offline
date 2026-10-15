# Etapa A — Requisitos, arquitetura e decisões

Documentos lidos: `01_PROMPT_DESENVOLVIMENTO_SISTEMA_DVI_v1_1.md`, `02_CHECKLIST_ANEXOS_CLAUDE_v1_1.md`,
`03_FLUXO_DE_TELAS_E_TESTES.md`, `DVI_DVI Guide 2023.pdf` (31 p., numeração interna até a p. 29/110),
`AMFormSet_en-GB.pdf` (16 p.), `PMFormSet_en-GB.pdf` (17 p.) e Anexos 4, 5, 6 e 9.

## 1. Requisitos extraídos dos documentos INTERPOL

| # | Requisito | Fonte |
|---|---|---|
| R1 | Os identificadores primários são papiloscopia, odontologia comparativa e DNA. Números de série de implantes também podem ser confiáveis. Os demais são secundários. | DVI Guide 2023, cap. 6 (p. 16) |
| R2 | Identificação por fotografia ou reconhecimento visual não é confiável como único meio. | DVI Guide 2023, cap. 6 (p. 16–17) |
| R3 | Nenhum software substitui a decisão. A identificação final cabe ao Identification Board. | Anexo 6, introdução, 6.4 e 6.7 (p. 70–73) |
| R4 | Triagem inicial por sexo e idade. Classificar por estatura ou ancestralidade costuma ser impraticável. | Anexo 6, 6.4 (p. 71) |
| R5 | Fluxo da reconciliação: recomendação → verificação independente → relatório ao Identification Board. | Anexo 6, 6.3 (p. 71) |
| R6 | Numeração `AM{código-país}-{NNNN}` e `PM{código-país}-{NNNN}[-cena]`, sem duplicidade e com cinco dígitos acima de 9.999. | Anexo 9 (p. 85–87) |
| R7 | Formulário AM (amarelo): campos 100–125 administrativos, 200–245 nominais, 300–350 objetos, 400–496 descrição corporal, 500–560 médico/DNA, 600–650 odontologia, 700 informações complementares e 800 apêndice. | AMFormSet 2023 |
| R8 | Formulário PM (rosa): campos 155–185 checklist do necrotério, 300–350, 402 estado do corpo, 404–496, 510–550 patologia/idade/sexo/DNA, 610–650 odontologia e 700. | PMFormSet 2023 |
| R9 | Campo 404: tipos (1 cicatriz, 2 piercing, 3 tatuagem, 4 mancha, 5 malformação, 6 amputação) × regiões 01–37 com lateralidade. | AM/PM 404 |
| R10 | Cores permitidas em vestimentas e objetos: lista fechada de 15 cores. | AM/PM 300–350 |

## 2. Decisões de arquitetura

| Decisão | Justificativa |
|---|---|
| Monólito modular (uma API e um banco) por instalação | Evita microserviços desnecessários. Cada base poderá ter sua própria instalação no futuro. |
| UUID em todas as entidades, mais a base de origem de cada registro | Permite consolidar no futuro, entre instalações independentes, por pacotes de exportação/importação sem colisões. |
| Sessão de servidor em cookie HttpOnly/SameSite=Strict, em vez de JWT | Revogação imediata. Permite abrir imagens e PDFs autenticados com `<img>` e links sem expor tokens em URL. |
| Contexto (operação, base e função) gravado na sessão e revalidado a cada requisição | Trocar de contexto no frontend nunca concede privilégio. Revogar uma autorização tem efeito imediato. |
| Campos comparáveis em colunas e tabelas próprias; o restante do formulário em JSONB por seção | Mantém o motor de comparação testável e permite ampliar o formulário sem migrar o esquema a cada campo. |
| Anexos fora do webroot, com nome por UUID, SHA-256 no banco, validação pelo conteúdo e versões que não sobrescrevem | Atende aos requisitos de integridade, custódia e de não sobrescrever silenciosamente. |
| Trilha de auditoria somente-inserção, garantida por gatilho no PostgreSQL | Nem a própria aplicação consegue alterar ou apagar o histórico. |
| O motor de comparação produz resultado por atributo, separando "sem dados" de "divergente" | Atende aos requisitos de explicabilidade e de que ausência não seja tratada como incompatibilidade. |

## 3. Premissas adotadas (sem bloquear o desenvolvimento)

1. O código de país padrão na numeração é **55** (Brasil), configurável por operação.
2. A base é uma unidade de trabalho cadastrada **por operação**.
3. Um registro AM ou PM só pode ser marcado como "pronto para reconciliação" quando cumpre requisitos mínimos.
   - AM: nome, sexo, data de nascimento ou idade, e ao menos uma entrevista.
   - PM: estado do corpo, sexo, data de recuperação e um evento de custódia.
   - Esses critérios são uma **proposta** e precisam ser validados pelo CCDVI.
4. O coordenador vê apenas dados agregados. ADMIN_TIC não acessa conteúdo de casos.
5. Os rótulos em português são tradução do projeto, não tradução oficial da INTERPOL.

## 4. Dúvidas para validação institucional (não bloqueantes)

1. Quais campos são obrigatórios em cada aba, segundo as regras internas do CCDVI e as telas do SPT Web? As telas do
   SPT Web **não foram fornecidas**, por isso nenhuma tela ou campo do SPT Web foi reproduzido.
2. Qual o tempo de retenção dos anexos e das versões substituídas? Quem pode autorizar a retirada de evidência?
3. A operação deve usar sempre o código de país 55, ou equipes estrangeiras usam o próprio código (Anexo 9)?
4. Qual o fluxo formal de encaminhamento ao Identification Board e o modelo de relatório?
5. Qual a política de senhas, quem é responsável por criar contas e se haverá integração futura com diretório institucional.

## 5. Critérios de aceitação mapeados

Os critérios 1 a 11 e os testes extras 12 a 17 do prompt estão relacionados, com a evidência de cada um, em
[STATUS_IMPLEMENTACAO.md](STATUS_IMPLEMENTACAO.md).
