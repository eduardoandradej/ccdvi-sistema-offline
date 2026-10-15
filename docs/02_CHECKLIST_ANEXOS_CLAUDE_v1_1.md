# Anexos para entregar ao Claude junto ao prompt

## Essenciais — primeira execução

1. `DVI_DVI Guide 2023.pdf` — Guia INTERPOL 2023 (já fornecido nesta conversa; reanexar no Claude).
2. Formulário INTERPOL AM de 2023 (PDF preenchível): https://www.interpol.int/en/content/download/5324/file/AMFormSet_en-GB.pdf
3. Formulário INTERPOL PM de 2023 (PDF preenchível): https://www.interpol.int/en/content/download/5325/file/PMFormSet_en-GB.pdf
4. Anexo 4 (PM): https://www.interpol.int/en/content/download/5752/file/DVI_DVI%20Guide%20Annexure%204.pdf
5. Anexo 5 (AM): https://www.interpol.int/en/content/download/5753/file/DVI_DVI%20Guide%20Annexure%205.pdf
6. Anexo 6 (Reconciliação): https://www.interpol.int/en/content/download/5754/file/DVI_DVI%20Guide%20Annexure%206.pdf
7. Anexo 9 (Numeração): https://www.interpol.int/en/content/download/5760/file/DVI_DVI%20Guide%20Annexure%209.pdf

Portal oficial que reúne os materiais: https://www.interpol.int/en/How-we-work/Forensics/Disaster-Victim-Identification-DVI

## Úteis depois — melhoram fidelidade institucional

- Prints anonimizados das telas/abas AM/PM e administrativas do SPT Web; lista de campos e obrigatoriedades, sem dados reais.
- Modelos fictícios de relatórios, laudos e ficha de cadastro, com autorização de uso.
- Documento de requisitos tecnológicos, padrões de sistemas e MVPs da DGTIC (se aplicável).
- Regras internas de usuários/perfis, identificadores, estados de fluxo, cadeia de custódia e aprovação.
- Pranchas da infraestrutura física/lógica DVI como referência **visual**, não como especificação funcional.
- Especificação/API ou formato de importação/exportação do SPT Web, se existir e houver autorização. Sem isso, pedir apenas exportação genérica e integração futura.

## NÃO anexar ao Claude público sem autorização explícita

- Fotografias reais de cadáveres, digitais, perfis de DNA, prontuários, CPFs e dados pessoais de familiares ou vítimas.
- Senhas, tokens, VPNs, topologias institucionais sensíveis, IPs reais ou credenciais de servidores.

Para o protótipo, pedir que o próprio Claude crie **dados e imagens sintéticos** e que mantenha tudo local. Confirmar previamente as políticas institucionais e de compartilhamento de dados da plataforma escolhida.

## Como iniciar

1. Preferencialmente usar **Claude Code** com permissão para ler/criar arquivos e executar testes em um repositório de projeto; no Claude web puro pode ser necessário transferir manualmente os arquivos para execução.
2. Criar uma pasta de projeto vazia e abrir o Claude Code nela.
3. Adicionar o prompt e os PDFs essenciais, com nomes claros; informar o diretório dos anexos.
4. Solicitar: `Execute a ETAPA A e comece a ETAPA B. Quero código real, testes executados e o sistema rodando localmente.`
5. Ao receber o resultado, exigir demonstração dos fluxos AM, PM, anexos e matching; revisar `docs/STATUS_IMPLEMENTACAO.md` antes de avançar.

## Observação

A documentação INTERPOL orienta coleta e reconciliação, mas um novo sistema NÃO se torna automaticamente homologado ou conforme apenas por usar esses formulários. Identificação formal continua com especialistas e autoridades responsáveis.

## Material extra para acertar as telas de perfis/bases e anexos

- Organização real dos perfis do CCDVI (apenas nomes de papéis e competências, sem dados pessoais): operadores AM, peritos PM, reconciliação, coordenação e TIC.
- Exemplos anonimizados das fichas de cadastro/entrevista que os usuários preencherão, incluindo campos e ordem das abas.
- Tipos de documentos aceitos em AM e PM e regras institucionais de retenção, sigilo, cadeia de custódia e classificação documental.
- Fluxo de autorização de acesso entre Comando, AM e PM; ninguém deve ganhar acesso só por clicar em uma base.
- Amostras **inteiramente sintéticas** para teste: documento de identificação fictício, imagem de referência genérica, PDF de prontuário fictício, foto genérica de vestimenta, descrição textual fictícia de tatuagem/cicatriz e registro PM simulado.

Não é necessário fornecer imagens de identidades verdadeiras, pessoas desaparecidas reais, fotografias cadavéricas ou dados confidenciais para o desenvolvimento do MVP.
