// Ejecutar con node --test tests/test_corte_ui.js (sin navegador ni servidor).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const src = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
const api = src.slice(src.indexOf('    async function api('), src.indexOf('    /* ── Professional SVG'));
const corte = src.slice(src.indexOf('    let corteEnProceso'), src.indexOf('    function showReceiptModal'));

function setup({ status = 200, values = {}, fetchImpl } = {}) {
  const inputs = { cFondo: { value: '1000' }, b500: { value: '1' }, b200: { value: '2' }, b50: { value: '1' } };
  for (const [key, value] of Object.entries(values)) inputs[key] = { value };
  const button = { disabled: false, textContent: '✓ Confirmar Corte' };
  const calls = [], messages = [];
  let closed = false;
  const context = {
    usuario: { id: 1 },
    document: { getElementById: id => id === 'confirmarCorteBtn' ? button : inputs[id] || { value: '0' } },
    closeModal: () => { closed = true; },
    toast: (...args) => messages.push(args),
    fetch: async (url, options) => {
      calls.push({ url, body: JSON.parse(options.body) });
      if (fetchImpl) return fetchImpl();
      return { ok: status === 200, status, json: async () => {
        if (status === 500) throw new SyntaxError('Not JSON');
        return status === 200 ? { resumen: { diferencia: 0 } }
          : { detail: [{ loc: ['body', 'efectivo_real'], msg: 'Invalid' }] };
      } };
    }
  };
  vm.createContext(context);
  vm.runInContext(api + corte, context);
  return { context, button, calls, messages, isClosed: () => closed };
}

test('envía -50 netos, conserva el fondo y muestra corte con diferencia cero', async () => {
  const s = setup();
  await s.context.doCorte();
  assert.equal(s.calls.length, 1);
  assert.equal(s.calls[0].body.efectivo_real, -50);
  assert.equal(s.calls[0].body.fondo_caja, 1000);
  assert.deepEqual(s.calls[0].body.desglose, { B500: 1, B200: 2, B50: 1 });
  assert.equal(s.isClosed(), true);
  assert.match(s.messages[0][1], /Dif: \+\$0\.00/);
});

test('rechaza conteos negativos, fraccionarios y fondos inválidos', async () => {
  for (const values of [{ b500: '-1' }, { m1: '0.5' }, { cFondo: '-1' }, { cFondo: 'Infinity' }, { b200: 'abc' }]) {
    const s = setup({ values });
    await s.context.doCorte();
    assert.equal(s.calls.length, 0);
    assert.equal(s.isClosed(), false);
    assert.equal(s.messages[0][0], '❌');
  }
});

test('muestra error 422 legible y mantiene el formulario para corregir', async () => {
  const s = setup({ status: 422 });
  await s.context.doCorte();
  assert.match(s.messages[0][1], /rechazó los datos/);
  assert.doesNotMatch(s.messages[0][1], /object Object/);
  assert.equal(s.isClosed(), false);
  assert.equal(s.button.disabled, false);
});

test('advierte de un posible corte guardado ante error 500 o fallo de red', async () => {
  for (const options of [{ status: 500 }, { fetchImpl: async () => { throw new TypeError('Failed to fetch'); } }]) {
    const s = setup(options);
    await s.context.doCorte();
    assert.match(s.messages[0][1], /podría haberse guardado/);
    assert.equal(s.isClosed(), false);
    assert.equal(s.button.disabled, false);
  }
});

test('bloquea envíos simultáneos mientras se guarda el corte', async () => {
  let resolve;
  const s = setup({ fetchImpl: () => new Promise(r => { resolve = r; }) });
  const first = s.context.doCorte();
  assert.equal(s.button.disabled, true);
  await s.context.doCorte();
  assert.equal(s.calls.length, 1);
  resolve({ ok: true, status: 200, json: async () => ({ resumen: { diferencia: 0 } }) });
  await first;
  assert.equal(s.button.disabled, false);
  assert.equal(s.isClosed(), true);
});
