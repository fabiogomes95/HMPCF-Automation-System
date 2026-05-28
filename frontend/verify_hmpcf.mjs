import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();

const errors = [];
page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
page.on('pageerror', err => errors.push(err.message));

await page.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 15000 });
await page.waitForTimeout(1500);

await page.screenshot({ path: 'C:/tmp/recepcao_full.png', fullPage: true });

const checks = {
  headerH1: await page.locator('h1').textContent().catch(() => null),
  campoCPF: await page.locator('input[placeholder="000.000.000-00"]').isVisible().catch(() => false),
  campoCNS: await page.locator('input[placeholder="000 0000 0000 0000"]').isVisible().catch(() => false),
  campoNome: await page.locator('input[placeholder="Nome completo"]').isVisible().catch(() => false),
  btnAtendimento: await page.locator('button.btn-atendimento').isVisible().catch(() => false),
  btnImprimir: await page.locator('button.btn-imprimir').isVisible().catch(() => false),
  btnLimpar: await page.locator('button.btn-limpar').isVisible().catch(() => false),
  procedenciaSAMU: await page.locator('text=SAMU').first().isVisible().catch(() => false),
  procedenciaNORMAL: await page.locator('text=NORMAL').first().isVisible().catch(() => false),
  boletimPage: await page.locator('.page').isVisible().catch(() => false),
  headerContainer: await page.locator('.header-container').isVisible().catch(() => false),
  headerTextContent: await page.locator('.header-text').textContent().catch(() => null),
  dataAtendimento: await page.locator('label:has-text("DATA DE ATENDIMENTO")').isVisible().catch(() => false),
  classificacaoRisco: await page.locator('.section-title').first().textContent().catch(() => null),
  imgBrasao: await page.locator('img[alt="Brasão Extremoz"]').isVisible().catch(() => false),
};

console.log(JSON.stringify({ checks, errors }, null, 2));
await browser.close();
