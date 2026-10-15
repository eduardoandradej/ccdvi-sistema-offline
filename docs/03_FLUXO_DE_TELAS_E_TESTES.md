# Fluxo de telas e critério de uso — v1.1

```text
LOGIN
  ↓
SELEÇÃO DE OPERAÇÃO (ex.: SIMULADO CCDVI)
  ↓
SELEÇÃO DA BASE (COMANDO / AM / PM) [somente autorizadas]
  ↓
PERFIL ATIVO (conforme permissões reais da conta)
  ├── AM → Desaparecido → Entrevistas → Características → Fotos/Documentos → Salvar no banco local
  ├── PM → Registro PM → Exame → Características → Fotos/Documentos → Salvar no banco local
  ├── RECONCILIAÇÃO → Lista de candidatos → Comparação AM×PM → Encaminhamento pericial
  └── TIC/COORDENAÇÃO → Operação, rede, pendências, relatórios autorizados
```

## Cenário de demonstração

1. Entrar como OPERADOR_AM na operação SIMULADO CCDVI, Base AM.
2. Cadastrar pessoa fictícia e vincular entrevistado fictício.
3. Anexar PDF de identidade sintética, fotografia de referência genérica e documento odontológico fictício.
4. Salvar, sair, entrar novamente e recuperar os arquivos.
5. Entrar como OPERADOR_PM na mesma operação, Base PM.
6. Registrar caso PM fictício e adicionar fotografia genérica de vestimenta/objeto, sem dados ou imagens de cadáveres reais.
7. Entrar como REVISOR autorizado, abrir tela de comparação AM×PM, visualizar justificativas e divergências.
8. Repetir com internet desconectada, usando Wi-Fi da rede local.
9. Provar isolamento de acesso de usuário AM aos registros e anexos PM e vice-versa.

**Observação**: contexto de base não é permissão; o servidor deve verificar acesso a cada operação. Matching apenas recomenda casos para revisão e nunca autentica identidade automaticamente.
