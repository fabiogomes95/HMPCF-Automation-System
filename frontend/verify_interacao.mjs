import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
const errors = [];
page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
page.on('pageerror', err => errors.push(err.message));

await page.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 15000 });
await page.waitForTimeout(1000);

// Screenshot inicial
await page.screenshot({ path: 'verify_01_inicial.png' });

// Teste 1: digitar CPF inválido e ver erro
await page.locator('input[placeholder="000.000.000-00"]').fill('111.111.111-11');
await page.waitForTimeout(600);
const erroCpf = await page.locator('.texto-erro-inline').textContent().catch(() => null);

// Screenshot com CPF digitado
await page.screenshot({ path: 'verify_02_cpf.png' });

// Teste 2: clicar botão Registrar sem preencher nome → deve mostrar erro
await page.locator('button.btn-atendimento').click();
await page.waitForTimeout(500);
const msgErro = await page.locator('.recepcao-msg').textContent().catch(() => null);

// Screenshot com mensagem de erro
await page.screenshot({ path: 'verify_03_erro_validacao.png' });

// Teste 3: clicar Limpar
await page.locator('button.btn-limpar').click();
await page.waitForTimeout(300);
const cpfAposLimpar = await page.locator('input[placeholder="000.000.000-00"]').inputValue();

// Teste 4: clicar botão procedência SAMU
await page.locator('.btn-samu').click();
await page.waitForTimeout(300);
const samuAtivo = await page.locator('.btn-samu').getAttribute('class');

// Screenshot final
await page.screenshot({ path: 'verify_04_samu.png' });

// Teste 5: atd info preenchido automaticamente (data/hora)
const dataAtd = await page.locator('label:has-text("DATA DE ATENDIMENTO") + input').inputValue().catch(() => null);
const horaAtd = await page.locator('label:has-text("HORA") + input').first().inputValue().catch(() => null);

console.log(JSON.stringify({
  erroCpf,
  msgErro,
  cpfAposLimpar,
  samuAtivo,
  dataAtdPreenchida: !!dataAtd && dataAtd.length > 0,
  horaAtdPreenchida: !!horaAtd && horaAtd.length > 0,
  consoleErrors: errors
}, null, 2));

await browser.close();
