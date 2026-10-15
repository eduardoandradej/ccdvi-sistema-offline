import { expect, Page, test } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PASSWORD = process.env.DVI_E2E_PASSWORD ?? "demo-ccdvi-2026";
const HERE = path.dirname(fileURLToPath(import.meta.url));
const SAMPLES = path.resolve(HERE, "../../tests/amostras");
const SHOTS = path.resolve(HERE, "../../docs/screenshots");

/** Registra todos os hosts acessados pelo navegador para provar que não há chamadas externas. */
function trackHosts(page: Page): Set<string> {
  const hosts = new Set<string>();
  page.on("request", (r) => hosts.add(new URL(r.url()).host));
  return hosts;
}

function expectOnlyLocal(hosts: Set<string>, baseURL: string) {
  const local = new URL(baseURL).host;
  expect([...hosts].filter((h) => h !== local)).toEqual([]);
}

async function login(page: Page, user: string, base: string, role: string) {
  await page.goto("/");
  await page.getByLabel("Usuário").fill(user);
  await page.getByLabel("Senha").fill(PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.getByRole("button", { name: /SIMULADO CCDVI 2026/ }).click();
  await page.getByRole("button", { name: new RegExp(base) }).click();
  await page.getByRole("button", { name: new RegExp(role) }).click();
  await expect(page.getByTestId("context-bar")).toBeVisible();
}

test("AM: cadastro, entrevista, sinal, anexos e persistência após recarregar", async ({ page, baseURL }) => {
  const hosts = trackHosts(page);
  await page.goto("/");
  await page.screenshot({ path: `${SHOTS}/01-login.png` });
  await page.getByLabel("Usuário").fill("operador.am");
  await page.getByLabel("Senha").fill(PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.getByRole("button", { name: /SIMULADO CCDVI 2026/ }).click();
  await page.getByRole("button", { name: /Base Ante Mortem/ }).click();
  await page.screenshot({ path: `${SHOTS}/02-contexto.png` });
  await page.getByRole("button", { name: /Operador Ante Mortem/ }).click();
  await expect(page.getByTestId("context-bar")).toContainText("Base Ante Mortem");
  await page.screenshot({ path: `${SHOTS}/03-painel-am.png` });
  // menus de outras funções não aparecem
  await expect(page.getByRole("link", { name: "Post Mortem" })).toHaveCount(0);

  await page.getByRole("link", { name: "Ante Mortem" }).click();
  await page.getByRole("button", { name: "Novo desaparecido" }).click();
  const suffix = Date.now().toString().slice(-6);
  await page.getByLabel(/^Sobrenome/).fill(`E2E TESTE ${suffix}`);
  await page.getByLabel(/^Nome\(s\)/).fill("FICTÍCIO");
  await page.getByLabel(/^Sexo/).selectOption("M");
  await page.getByRole("button", { name: "Criar registro AM" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/AM55-\d{4}/);
  const caseUrl = page.url();

  await page.getByLabel(/^Data de nascimento/).fill("1980-07-15");
  await page.getByLabel(/^Ocupação/).fill("Professor (fictício)");
  await page.getByRole("button", { name: "Salvar rascunho" }).click();
  await expect(page.locator(".alert.success")).toContainText("Gravado no banco de dados");

  await page.getByRole("tab", { name: /Entrevistas/ }).click();
  await page.getByLabel(/^Nome do informante/).fill("IRMÃO FICTÍCIO");
  await page.getByLabel(/^Vínculo/).fill("Irmão");
  await page.getByRole("button", { name: "Adicionar entrevista" }).click();
  await expect(page.locator("table")).toContainText("IRMÃO FICTÍCIO");

  await page.getByRole("tab", { name: /Características/ }).click();
  await page.getByLabel(/^Estatura mín/).fill("175");
  await page.getByLabel(/^Estatura máx/).fill("178");
  await page.locator(".inline-form").getByLabel(/^Tipo/).selectOption("3");
  await page.locator(".inline-form").getByLabel(/^Região anatômica/).selectOption("32");
  await page.locator(".inline-form").getByLabel(/^Descrição/).fill("tatuagem de âncora (fictícia)");
  await page.getByRole("button", { name: "Adicionar sinal" }).click();
  await expect(page.locator("table").first()).toContainText("Antebraço direito");
  await page.getByRole("button", { name: "Salvar rascunho" }).click();
  await expect(page.locator(".alert.success")).toContainText("Gravado no banco de dados");
  await page.screenshot({ path: `${SHOTS}/04-am-caracteristicas.png`, fullPage: true });

  await page.getByRole("tab", { name: /Fotos e documentos/ }).click();
  const up = page.locator("form.upload");
  await up.getByLabel("Tipo de anexo").selectOption("FOTO_REFERENCIA_AM");
  await up.getByLabel("Título").fill("Fotografia de referência (fictícia)");
  await up.getByTestId("file-input").setInputFiles(`${SAMPLES}/foto_referencia_ficticia.jpg`);
  await up.getByRole("button", { name: "Enviar anexo" }).click();
  await expect(up.locator(".alert.success")).toContainText("armazenado e confirmado");
  await up.getByLabel("Tipo de anexo").selectOption("DOC_IDENTIFICACAO");
  await up.getByLabel("Título").fill("Documento de identidade (fictício)");
  await up.getByTestId("file-input").setInputFiles(`${SAMPLES}/documento_identidade_ficticio.pdf`);
  await up.getByRole("button", { name: "Enviar anexo" }).click();
  await expect(page.getByTestId("attachment")).toHaveCount(2);
  // extensão forjada é recusada pelo servidor
  await up.getByLabel("Tipo de anexo").selectOption("OUTRO");
  await up.getByLabel("Título").fill("Arquivo forjado");
  await up.getByTestId("file-input").setInputFiles({
    name: "forjado.pdf", mimeType: "application/pdf",
    buffer: Buffer.from("isto não é um PDF"),
  });
  await up.getByRole("button", { name: "Enviar anexo" }).click();
  await expect(up.locator(".alert.error")).toContainText("NÃO armazenado");
  await page.screenshot({ path: `${SHOTS}/05-am-anexos.png`, fullPage: true });

  // persistência: recarrega a página, confere dados e baixa o anexo com a sessão autenticada
  await page.goto(caseUrl);
  await expect(page.getByLabel(/^Ocupação/)).toHaveValue("Professor (fictício)");
  await page.getByRole("tab", { name: /Fotos e documentos/ }).click();
  await expect(page.getByTestId("attachment")).toHaveCount(2);
  const href = await page.getByRole("link", { name: "baixar" }).last().getAttribute("href");
  const res = await page.request.get(href!);
  expect(res.status()).toBe(200);
  expect(res.headers()["content-type"]).toBe("application/pdf");
  expectOnlyLocal(hosts, baseURL!);
});

test("PM: cadastro com foto; isolamento de AM por API", async ({ page, baseURL }) => {
  const hosts = trackHosts(page);
  await login(page, "operador.pm", "Base Post Mortem", "Operador/Perito Post Mortem");
  await expect(page.getByRole("link", { name: "Ante Mortem" })).toHaveCount(0);
  expect((await page.request.get("/api/am")).status()).toBe(403);

  await page.getByRole("link", { name: "Post Mortem" }).click();
  await page.getByRole("button", { name: "Recepção PM" }).click();
  await page.getByLabel(/^Referência de cena/).fill("C");
  await page.getByLabel(/^Estado do corpo/).selectOption("COMPLETO");
  await page.getByRole("button", { name: "Registrar PM" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/PM55-\d{4}-C/);
  await page.getByRole("tab", { name: /Fotografias e anexos/ }).click();
  const up = page.locator("form.upload");
  await up.getByLabel("Tipo de anexo").selectOption("REGISTRO_PERTENCE");
  await up.getByLabel("Título").fill("Vestimenta (fictícia)");
  await up.getByTestId("file-input").setInputFiles(`${SAMPLES}/foto_vestimenta_ficticia.png`);
  await up.getByRole("button", { name: "Enviar anexo" }).click();
  await expect(up.locator(".alert.success")).toContainText("armazenado e confirmado");
  await page.screenshot({ path: `${SHOTS}/06-pm-anexos.png`, fullPage: true });
  expectOnlyLocal(hosts, baseURL!);
});

test("Reconciliação: candidatos, comparação explicada e encaminhamento sem identificação automática", async ({ page, baseURL }) => {
  const hosts = trackHosts(page);
  await login(page, "revisor", "Base Principal", "Revisor de Reconciliação");
  await page.getByRole("link", { name: "Reconciliação" }).click();
  await page.getByRole("row", { name: /MARIA SILVA FICTÍCIA/ }).click();
  await expect(page.getByText(/Candidatos PM para AM55-0001/)).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/07-reconciliacao-candidatos.png`, fullPage: true });
  await page.getByRole("link", { name: "comparar lado a lado" }).first().click();
  await expect(page.locator(".alert.disclaimer")).toContainText("Não é identificação");
  await expect(page.locator(".compare-table")).toContainText("Antebraço direito");
  await expect(page.locator(".compare-table")).toContainText("FLORAL");
  await expect(page.getByRole("button", { name: /identifica/i })).toHaveCount(0);
  await page.getByLabel("Encaminhamento").selectOption("ENCAMINHADO_AVALIACAO_TECNICA");
  await page.getByLabel(/Justificativa/).fill("Solicitar confronto odontológico (teste E2E).");
  await page.getByRole("button", { name: "Registrar análise" }).click();
  await expect(page.locator(".alert.success")).toContainText("Análise registrada");
  await page.screenshot({ path: `${SHOTS}/08-comparacao-lado-a-lado.png`, fullPage: true });
  // par com divergência de lateralidade
  await page.goBack();
  await page.getByRole("row", { name: /MARIA SILVA FICTÍCIA/ }).click();
  await page.locator("tr.row-warn").getByRole("link", { name: "comparar lado a lado" }).first().click();
  await expect(page.locator(".compare-table")).toContainText("LADO OPOSTO");
  await page.screenshot({ path: `${SHOTS}/09-comparacao-divergencias.png`, fullPage: true });
  expectOnlyLocal(hosts, baseURL!);
});

test("Contexto: usuário multibase alterna; troca não autorizada é negada pelo servidor", async ({ page }) => {
  await login(page, "perito.multi", "Base Ante Mortem", "Operador Ante Mortem");
  expect((await page.request.get("/api/am")).status()).toBe(200);
  await page.getByRole("button", { name: "Trocar contexto" }).click();
  await page.getByRole("button", { name: /SIMULADO CCDVI 2026/ }).click();
  await page.getByRole("button", { name: /Base Post Mortem/ }).click();
  await page.getByRole("button", { name: /Operador\/Perito Post Mortem/ }).click();
  await expect(page.getByTestId("context-bar")).toContainText("Base Post Mortem");
  expect((await page.request.get("/api/pm")).status()).toBe(200);
  expect((await page.request.get("/api/am")).status()).toBe(403);
  const me = await (await page.request.get("/api/auth/me")).json();
  const cmd = me.authorizations.find((a: { base: { code: string } }) => a.base.code === "PM");
  const r = await page.request.put("/api/auth/context", {
    headers: { "X-DVI-Request": "1" },
    data: { operation_id: cmd.operation.id, base_id: cmd.base.id, role: "REVISOR_RECONCILIACAO" },
  });
  expect(r.status()).toBe(403);
});

test("Perfis sem acesso a conteúdo: coordenador, auditor e TIC", async ({ page }) => {
  // Coordenador: só agregados; rota AM direta é bloqueada na interface e na API
  await login(page, "coordenador", "Base Principal", "Coordenador");
  await expect(page.getByRole("link", { name: "Ante Mortem" })).toHaveCount(0);
  await page.locator("nav.menu").getByRole("link", { name: "Situação da operação" }).click();
  await expect(page.getByText("Registros AM")).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/10-coordenador-painel.png` });
  await page.goto("/am");
  await expect(page.getByText("não permite acessar esta tela")).toBeVisible();
  expect((await page.request.get("/api/am")).status()).toBe(403);
  expect((await page.request.get("/api/matching/overview")).status()).toBe(403);
  await page.getByRole("button", { name: "Sair" }).click();

  // Auditor: trilha de auditoria, inclusive tentativas negadas
  await login(page, "auditor", "Base Principal", "Auditor");
  await page.locator("nav.menu").getByRole("link", { name: "Auditoria" }).click();
  await page.getByPlaceholder("Ação (ex.: ANEXO_ENVIADO)").fill("TROCA_CONTEXTO");
  await expect(page.locator("table")).toContainText("NEGADO");
  await page.screenshot({ path: `${SHOTS}/11-auditoria.png` });
  expect((await page.request.get("/api/pm")).status()).toBe(403);
  await page.getByRole("button", { name: "Sair" }).click();

  // TIC: saúde e usuários, sem acesso a casos nem anexos
  await login(page, "admin.tic", "Base Principal", "Administrador TIC");
  await page.locator("nav.menu").getByRole("link", { name: "Administração TIC" }).click();
  await expect(page.getByText("Banco de dados")).toBeVisible();
  await expect(page.locator("table")).toContainText("operador.am");
  await page.screenshot({ path: `${SHOTS}/12-admin-tic.png`, fullPage: true });
  expect((await page.request.get("/api/am")).status()).toBe(403);
});
