# Rastreabilidade de campos e telas

Legenda de origem:

- **A**: campo encontrado nos documentos INTERPOL (formulário AM/PM 2023 ou guia/anexos).
- **B**: extensão proposta pelo sistema. Na interface aparece com o selo roxo "ext.".
- **C**: campo do SPT Web confirmado por anexo. **Nenhum até agora**, porque as telas e a especificação do SPT Web
  não foram fornecidas.

Na interface, cada campo exibe o código do formulário de origem (selo azul) ou o selo "ext.".
Arquivo de definição dos campos de formulário: `frontend/src/formSpecs.ts`. Vocabulários controlados:
`backend/app/vocab.py`.

## Ante Mortem (AMFormSet_en-GB.pdf, versão 2023)

| Aba / campo no sistema | Armazenamento | Origem | Referência |
|---|---|---|---|
| Nº AM | `am_cases.am_number` | A | Anexo 9, p. 87 ("AM Numbers") |
| Sobrenome, nome(s), sexo, data de nascimento, idade | colunas `am_cases` | A | cabeçalho de todas as páginas do AM (Family name, First/Middle name(s), DOB, Age, Male/Female/Other/Unknown) |
| Visto pela última vez, local, circunstâncias | `form_data.circumstances` | B | — |
| Órgão responsável, nº do procedimento | `form_data.admin` | A | AM 100 (p. 1) |
| Registro papiloscópico / fontes de impressões | `form_data.admin` | A | AM 120, 125 (p. 1) |
| Entrevistas (informante, vínculo, contato, endereço, data) | `am_interviews` | A | AM 105 "Information given by" (p. 1) |
| Ponto de contato | `am_interviews.is_point_of_contact` | A | AM 110 (p. 1) |
| Local da entrevista e observações | `am_interviews` | B | — |
| Dados nominais | `form_data.nominal` | A | AM 200, 205, 210, 215, 220, 225, 230, 235, 238, 240, 241, 243 (p. 2) |
| Vestimentas, calçados, relógio, óculos, joias, documentos, objetos, eletrônicos | `effects` (`field_code` 300–350) | A | AM 300, 305, 310, 315, 335, 340, 345, 350 (p. 3–5), com a lista de cores do formulário |
| Sinais particulares (tipo × região) | `physical_marks` | A | AM 404 (p. 6) |
| Estatura, peso, compleição | colunas `am_cases` | A | AM 408, 412, 416 (p. 6) |
| Cabelo, olhos, pelos faciais, orelhas, circuncisão, outras características | `form_data.body` | A | AM 420, 428, 436, 440, 472, 424–468 (p. 6–7) |
| Grau de certeza (relatado, documentado, incerto) | `certainty`, `height_certainty` | B | exigência do prompt: não converter relato em fato |
| Situação por categoria (não informado, negativo…) | `category_status` | B | exigência do prompt: ausência ≠ incompatibilidade |
| Histórico médico, médico de referência, próteses | `form_data.medical` | A | AM 500, 505, 520, 525 (p. 9) |
| Implantes com nº de série | `effects` (`field_code` 515) | A | AM 515 (p. 9) e DVI Guide cap. 6 (p. 16) |
| Referências de DNA (direta e de parentes) | `form_data.dna` | A | AM 555, 560 (p. 10a) |
| Odontologia (dentista, período, imagens, dados específicos, dentição) | `form_data.dental` | A | AM 600, 615, 635, 640, 645 (p. 12–13) |
| Informações complementares | `form_data.supporting` | A | AM 700 (p. 14) |
| Fotos e documentos | `attachments` | B | estrutura própria. O formulário prevê a coluna "b = Attachment". |
| Odontograma (630), árvore genealógica e perfil STR (810–825) | — | A | **não implementado nesta etapa** |

## Post Mortem (PMFormSet_en-GB.pdf, versão 2023)

| Aba / campo no sistema | Armazenamento | Origem | Referência |
|---|---|---|---|
| Nº PM com referência de cena | `pm_cases.pm_number`, `scene_ref` | A | Anexo 9, p. 85–86 |
| UUID interno | `pm_cases.id` | B | exigência do prompt |
| Data e local de recuperação, equipe, PMs relacionados | colunas e `form_data.reception` | B | inspirado no Disaster Victim Recovery Form (Anexo 9, p. 86), que não foi fornecido |
| Números de referência (AFIS, DNA, polícia) | `form_data.reception` | A | PM 185 (p. 1) |
| Checklist do necrotério (fotos, pertences, impressões, exames, odontologia, amostras) | `form_data.checklist` | A | PM 155, 160, 165, 170, 175, 180 (p. 1) |
| Estado do corpo | `pm_cases.state_of_body` | A | PM 402 (p. 5) |
| Sinais particulares | `physical_marks` | A | PM 404 (p. 5) |
| Estatura, peso, compleição | colunas | A | PM 408, 412, 416 (p. 5) |
| Descrição corporal | `form_data.body` | A | PM 420–472 (p. 5–6) |
| Necropapiloscopia | `form_data.fingerprint` | A | PM 484, 488, 492, 496 (p. 7) |
| Exame interno, outras informações | `form_data.pathology` | A | PM 510, 520, 525, 550 (p. 8–9) |
| Sexo e justificativa | `pm_cases.sex`, `sex_reason` | A | PM 535 (p. 9) |
| Idade estimada e método | `age_min_years`, `age_max_years`, `age_method` | A | PM 540 (p. 9) |
| Amostras de DNA | `form_data.dna` | A | PM 545 (p. 9) |
| Odontologia | `form_data.dental` | A | PM 610, 615, 625, 635, 645, 647 (p. 10–11) |
| Pertences e vestimentas | `effects` | A | PM 300–350 (p. 2–4) |
| Implantes | `effects` (515) | A | PM 515 (p. 8) |
| Cadeia de custódia | `custody_events` | B | exigência do prompt |
| Identificador de evidência em anexos | `attachments.evidence_ref` | A/B | formato sugerido no Anexo 9 (ex.: "PM44-0025-A-Evidence item 21") |

## Reconciliação

| Elemento | Origem | Referência |
|---|---|---|
| Triagem inicial por sexo | A | Anexo 6, 6.4 (p. 71) |
| Comparação explicável por atributo e lista de candidatos para revisão | B | o Anexo 6, 6.5 descreve listas de *key markers* |
| Sem identificação automática; decisão do Identification Board | A | Anexo 6, introdução e 6.7 (p. 70, 73) |
| Status de encaminhamento | B | inspirado no Anexo 6, 6.3 |
| Implante com nº de série como identificador forte | A | DVI Guide cap. 6 (p. 16) |
