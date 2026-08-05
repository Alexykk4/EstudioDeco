    /* ═══════════════════════════════════════════════
       ESTUDIO DECO POS v2 — Mesa-based system
       ═══════════════════════════════════════════════ */
    let tiendas = [], mesas = [], usuario = null, metodoPago = 'Efectivo';
    let currentView = 'mesas', selectedMesa = null, selectedOrden = null, currentOrden = null;
    let directCart = [];
    let currentProducts = [], currentTienda = null, searchFilter = "", categoryFilter = "";
    let porcionesEstacion = {}; // {NOMBRE_BEBIDA: {porciones, cuello_de_botella}}
    let allProductsGlobal = null; // caché de todos los productos de todas las tiendas
    let propinaPct = 10; // porcentaje activo (0 = monto personalizado)

    function togglePropina() {
      const on = document.getElementById('propinaCheck').checked;
      document.getElementById('propinaControls').classList.toggle('hidden', !on);
      renderOrder();
    }
    function setPropinaPct(btn, pct) {
      propinaPct = pct;
      document.querySelectorAll('.propina-opt').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const custom = document.getElementById('propinaCustom');
      if (pct === 0) { custom.classList.remove('hidden'); custom.focus(); }
      else { custom.classList.add('hidden'); custom.value = ''; }
      renderOrder();
    }
    function calcPropina(subtotal) {
      if (!document.getElementById('propinaCheck')?.checked) return 0;
      if (propinaPct > 0) return Math.round(subtotal * propinaPct) / 100;
      const v = parseFloat(document.getElementById('propinaCustom')?.value) || 0;
      return Math.max(0, v);
    }

    async function api(p, o = {}) {
      const r = await fetch(`/api${p}`, { headers: { 'Content-Type': 'application/json' }, ...o, body: o.body ? JSON.stringify(o.body) : undefined });
      if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Error') }
      return r.json();
    }

    /* ── Professional SVG icons (replaces emojis at render time) ── */
    const _ICON_PATHS = {
      check: '<path d="M5 13l4 4L19 7"/>',
      x: '<path d="M6 6l12 12M18 6L6 18"/>',
      warn: '<path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 001.7 3h16.9a2 2 0 001.7-3L12.7 3.9a2 2 0 00-3.4 0z"/>',
      cash: '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/><path d="M6 12h.01M18 12h.01"/>',
      card: '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/>',
      transfer: '<path d="M7 16V4M7 4L3 8M7 4l4 4M17 8v12M17 20l4-4M17 20l-4-4"/>',
      chart: '<path d="M4 19V5M4 19h16M8 16V10M12 16V7M16 16v-5"/>',
      calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
      list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
      eye: '<path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/>',
      users: '<path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>',
      bag: '<path d="M6 8h12l1 13H5L6 8z"/><path d="M9 8V6a3 3 0 016 0v2"/>',
      note: '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h6"/>',
      logout: '<path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/>',
      bank: '<path d="M3 21h18M3 10h18M5 10V21M9 10V21M15 10V21M19 10V21M12 3l9 7H3l9-7z"/>',
      cart: '<circle cx="9" cy="20" r="1"/><circle cx="17" cy="20" r="1"/><path d="M3 3h2l2.4 12.2a2 2 0 002 1.6h7.8a2 2 0 002-1.5L21 7H6"/>',
      table: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M3 16h18M9 4v16"/>',
      print: '<path d="M6 9V3h12v6"/><path d="M6 17H4a2 2 0 01-2-2v-4a2 2 0 012-2h16a2 2 0 012 2v4a2 2 0 01-2 2h-2"/><rect x="6" y="13" width="12" height="8"/>',
      edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4 12.5-12.5z"/>',
      trash: '<path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>',
      search: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
      money: '<circle cx="12" cy="12" r="9"/><path d="M12 7v10M9.5 9.5c.5-1 1.5-1.5 2.5-1.5s2 .6 2 1.75-1 1.5-2.5 2-2.5.9-2.5 2.25S10.5 16 12 16s2-.4 2.5-1.2"/>',
      spend: '<path d="M12 2v20M17 7H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>',
      settings: '<circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/>',
      phone: '<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M10 18h4"/>',
      mix: '<path d="M12 3v18M3 12h18M6 6l12 12M18 6L6 18"/>',
      package: '<path d="M16.5 9.4L7.5 4.2M21 16V8a2 2 0 00-1-1.7l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.7l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><path d="M3.3 7L12 12l8.7-5M12 22V12"/>',
      user: '<path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/>',
      moon: '<path d="M21 14.5A8.5 8.5 0 1110.5 3a7 7 0 0010.5 11.5z"/>',
      sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
      tag: '<path d="M20.6 13.4l-7.2 7.2a2 2 0 01-2.8 0L3 13V3h10l7.6 7.6a2 2 0 010 2.8z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
      key: '<path d="M21 2l-2 2m-7.6 7.6A5 5 0 1110 6.4L20 2l2 2-4.5 4.5"/>',
      coffee: '<path d="M17 8h1a4 4 0 010 8h-1M3 8h14v9a4 4 0 01-4 4H7a4 4 0 01-4-4V8z"/><path d="M6 2v2M10 2v2M14 2v2"/>',
      download: '<path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>',
      chevronL: '<path d="M15 18l-6-6 6-6"/>',
      chevronR: '<path d="M9 18l6-6-6-6"/>',
      store: '<path d="M3 9l1-5h16l1 5M3 9v11a1 1 0 001 1h16a1 1 0 001-1V9M3 9h18M8 21V13h8v8"/>',
      palette: '<path d="M12 2a10 10 0 00-1 19.9c.6 0 1-.4 1-1v-1.2a2 2 0 012-1.9h2.3A3.9 3.9 0 0022 12 10 10 0 0012 2z"/><circle cx="7.5" cy="10" r="1"/><circle cx="12" cy="7" r="1"/><circle cx="16.5" cy="10" r="1"/>',
      megaphone: '<path d="M3 11v2a2 2 0 002 2h2l5 4V5L7 9H5a2 2 0 00-2 2zM16 8.5a4 4 0 010 7"/>',
      pin: '<path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/>',
      plus: '<path d="M12 5v14M5 12h14"/>',
      home: '<path d="M3 10.5L12 3l9 7.5V20a1 1 0 01-1 1h-5v-6H9v6H4a1 1 0 01-1-1v-9.5z"/>',
      minus: '<path d="M5 12h14"/>',
    };
    const _EMOJI_ICON = {
      '✅': 'check', '✓': 'check', '❌': 'x', '✕': 'x', '⚠️': 'warn', '⚠': 'warn',
      '💵': 'cash', '💳': 'card', '📱': 'phone', '💸': 'spend', '💰': 'money', '🪙': 'money', '💲': 'money',
      '📊': 'chart', '📈': 'chart', '📉': 'chart', '🍩': 'chart',
      '📅': 'calendar', '📋': 'list', '📝': 'note', '📦': 'package',
      '👁': 'eye', '👁️': 'eye', '👥': 'users', '👤': 'user',
      '🏦': 'bank', '💼': 'bag', '🚪': 'logout', '🛒': 'cart', '🪑': 'table',
      '🖨': 'print', '🖨️': 'print', '✏️': 'edit', '✏': 'edit', '🗑️': 'trash', '🗑': 'trash',
      '🔍': 'search', '⚙️': 'settings', '⚙': 'settings', '⚖️': 'mix', '⚖': 'mix',
      '🛍️': 'bag', '🛍': 'bag', '🌙': 'moon', '☀️': 'sun', '☀': 'sun',
      '🏷️': 'tag', '🏷': 'tag', '🔑': 'key', '☕': 'coffee', '🏪': 'store',
      '🎨': 'palette', '📣': 'megaphone', '📍': 'pin', '🔥': 'chart', '⭐': 'chart',
      '➕': 'plus', '🏠': 'home', '↔️': 'transfer', '↔': 'transfer',
    };
    function icon(name, size = 16) {
      const d = _ICON_PATHS[name] || _ICON_PATHS.list;
      return `<svg class="ico" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
    }
    function demojify(html) {
      if (!html || typeof html !== 'string') return html;
      let out = html;
      for (const [em, name] of Object.entries(_EMOJI_ICON)) {
        if (out.includes(em)) out = out.split(em).join(icon(name));
      }
      return out;
    }
    function iconize(v, size = 16) {
      if (!v) return '';
      if (_ICON_PATHS[v]) return icon(v, size);
      if (_EMOJI_ICON[v]) return icon(_EMOJI_ICON[v], size);
      return demojify(String(v));
    }
    function fillIcons(root = document) {
      root.querySelectorAll('[data-icon]').forEach(el => {
        const name = el.getAttribute('data-icon');
        const size = +(el.getAttribute('data-size') || 16);
        el.innerHTML = icon(name, size);
      });
    }

    async function init() {
      tiendas = await api('/tiendas');
      fillIcons();
      await refreshMesas();
      renderTabs();
      api('/catalog').then(d => { allProductsGlobal = d; }).catch(() => { });
    }

    /* ── VIEWS ── */
    function switchView(v) {
      if (v === 'catalog' && (!usuario || usuario.perfil !== 'Administrador')) return toast('⚠️', 'Solo Administrador', 'var(--gold)');
      closePage();
      closeSidebar();
      currentView = v;
      document.querySelectorAll('.view-btn').forEach(b => b.classList.toggle('active', b.dataset.view === v));
      const mg = document.getElementById('mesasGrid'), pv = document.getElementById('productsView'),
        cv = document.getElementById('catalogView'), sv = document.getElementById('semanalView'),
        op = document.getElementById('orderPanel'), sb = document.getElementById('semanalSidebar');
      // Ocultar todo
      [mg, pv, cv, sv, op, sb].forEach(el => el?.classList.add('hidden'));

      if (v === 'mesas') {
        mg.classList.remove('hidden'); op.classList.remove('hidden');
        selectedMesa = null; selectedOrden = null; currentOrden = null; renderOrder();
        refreshMesas();
      } else if (v === 'directa') {
        pv.classList.remove('hidden'); op.classList.remove('hidden');
        selectedMesa = null; selectedOrden = null; currentOrden = null; directCart = [];
        document.getElementById('mesaBar').classList.add('hidden');
        renderOrder();
        if (tiendas.length) selectTab(tiendas[0]);
      } else if (v === 'catalog') {
        cv.classList.remove('hidden');
        loadCatalog();
      } else if (v === 'semanal') {
        sv.classList.remove('hidden'); sb.classList.remove('hidden');
        loadSemanal();
      }
    }

    /* ── RESUMEN SEMANAL ── */
    const TIENDA_COLORS = [
      '#9575CD', '#BA68C8', '#7986CB', '#4DB6AC', '#FFB74D', '#F06292', '#81C784', '#A1887F'
    ];
    const tiendaColorMap = {};
    function getTiendaColor(nombre) {
      if (!tiendaColorMap[nombre]) {
        const idx = Object.keys(tiendaColorMap).length % TIENDA_COLORS.length;
        tiendaColorMap[nombre] = TIENDA_COLORS[idx];
      }
      return tiendaColorMap[nombre];
    }

    const DIAS_ES = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
    const MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
    function formatFechaDia(fechaStr) {
      const [y, m, d] = fechaStr.split('-').map(Number);
      const dt = new Date(y, m - 1, d);
      const hoy = new Date(); hoy.setHours(0, 0, 0, 0);
      const esHoy = dt.getTime() === hoy.getTime();
      return { label: `${DIAS_ES[dt.getDay()]} ${d} ${MESES_ES[m - 1]}`, esHoy };
    }
    function $pesos(v) { return '$' + v.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

    async function loadSemanal() {
      document.getElementById('semanalKpis').innerHTML = `
    <div class="kpi-card"><div class="kpi-label">Cargando...</div><div class="kpi-val purple">⏳</div></div>`;
      document.getElementById('semanalBody').innerHTML = '';
      try {
        const [data, bal] = await Promise.all([api('/report/semanal'), api('/balance')]);
        // KPIs
        const gastosCaja = (data.total_gastos || 0) - (data.total_gastos_banco || 0);
        const gastosBanco = data.total_gastos_banco || 0;
        const efectivoSemana = (data.total_efectivo || 0) - gastosCaja;
        const tarjetaSemana = (data.total_tarjeta || 0) - gastosBanco;
        const totalIngresos = data.total_ingresos || 0;
        const balCaja = bal.en_caja || 0;
        const balBanco = bal.en_banco || 0;
        const saldoAntCaja = balCaja - efectivoSemana;
        const saldoAntBanco = balBanco - tarjetaSemana;
        document.getElementById('semanalKpis').innerHTML = `
      <div class="kpi-card">
        <div class="kpi-label">💰 Ventas Semana</div>
        <div class="kpi-val purple">${$pesos(data.total_ventas || 0)}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">💲 Ingresos Semana</div>
        <div class="kpi-val" style="color:#26A69A;">${$pesos(totalIngresos)}</div>
      </div>
`;

        // Render balance sidebar on the right (historical cumulative)
        const pagos = data.pagos_semana || [];
        const pagosHtml = pagos.length ? pagos.map(p => `
      <div class="balance-card-detail">
        <span>${p.tienda_nombre} ${p.es_interno ? '↔️' : '💸'}</span>
        <span style="color:${p.es_interno ? 'var(--sage)' : 'var(--red)'};">$${p.monto.toFixed(2)}</span>
      </div>`).join('') : '<div style="font-size:11px;color:var(--text-muted);padding:4px 0;">Sin pagos esta semana</div>';

        const balTotal = bal.total || 0;

        document.getElementById('semanalSidebar').innerHTML = `
      <div class="balance-card">
        <div class="balance-card-title">📋 Pagos de la Semana</div>
        ${pagosHtml}
      </div>
    `;

        const maxDia = Math.max(...data.dias.map(d => d.total_ventas), 1);
        const body = document.getElementById('semanalBody');
        body.innerHTML = '';

        data.dias.forEach(dia => {
          const { label, esHoy } = formatFechaDia(dia.fecha);
          const pct = (dia.total_ventas / maxDia * 100).toFixed(1);
          const tiendaChips = dia.por_tienda.length
            ? dia.por_tienda.map(t => `<span class="tienda-chip">
            <span class="tienda-chip-dot" style="background:${getTiendaColor(t.tienda)}"></span>
            ${t.tienda} <strong>${$pesos(t.total)}</strong>
          </span>`).join('')
            : '<span style="font-size:11px;color:var(--text-muted)">Sin ventas</span>';

          const gastosRow = dia.gastos > 0
            ? `<div class="semanal-gastos-row">💸 Gastos: ${$pesos(dia.gastos)}</div>` : '';

          const ingresosRow = dia.ingresos > 0
            ? `<div style="font-size:11px;color:var(--green-ok);font-weight:600;">💰 Ingresos: ${$pesos(dia.ingresos)}</div>` : '';

          const el = document.createElement('div');
          el.className = 'semanal-day';
          el.innerHTML = `
        <div class="semanal-day-header">
          <div class="semanal-date ${esHoy ? 'today' : ''}">${esHoy ? '📣 Hoy — ' : ''} ${label}</div>
          ${dia.num_ventas > 0 ? `<span class="semanal-ventas-badge">${dia.num_ventas} venta${dia.num_ventas > 1 ? 's' : ''}</span>` : ''}
          <div class="semanal-bar-wrap"><div class="semanal-bar" style="width:${pct}%"></div></div>
          <div class="semanal-total">${$pesos(dia.total_ventas)}</div>
        </div>
        <div class="semanal-tiendas">${tiendaChips}</div>
        ${ingresosRow}${gastosRow}`;
          body.appendChild(el);
          // Animate bar
          setTimeout(() => el.querySelector('.semanal-bar').style.width = pct + '%', 50);
        });
      } catch (e) {
        document.getElementById('semanalKpis').innerHTML = '';
        document.getElementById('semanalBody').innerHTML = `<div class="semanal-empty">❌ ${e.message}</div>`;
      }
    }

    /* ── MESAS ── */
    async function refreshMesas() {
      mesas = await api('/mesas');
      renderMesas();
    }

    function renderMesas() {
      const g = document.getElementById('mesasGrid');
      g.innerHTML = mesas.map(m => {
        const num_cuentas = (m.ordenes && m.ordenes.length) || 0;
        const ocu = num_cuentas > 0;

        let lbl = "Disponible";
        if (ocu) {
          if (num_cuentas === 1) {
            lbl = m.ordenes[0].nombre_cliente || "Ocupada";
          } else {
            lbl = `${num_cuentas} cuentas`;
          }
        }

        return `<div class="mesa-card ${ocu ? 'ocupada' : ''}" onclick="clickMesa(${m.id})">
      <div class="mesa-status"></div>
      <div class="mesa-num">${m.numero}</div>
      <div class="mesa-label">${lbl}</div>
      ${m.total_orden > 0 ? `<div class="mesa-total">$${m.total_orden.toFixed(2)}</div>` : ''}
      ${m.num_items > 0 ? `<div class="mesa-items-count">${m.num_items} artículo${m.num_items > 1 ? 's' : ''}</div>` : ''}
    </div>`;
      }).join('');
    }

    async function clickMesa(id) {
      const m = mesas.find(x => x.id === id);
      if (!m) return;

      const num_cuentas = (m.ordenes && m.ordenes.length) || 0;

      if (num_cuentas === 0) {
        if (!usuario) return showNipModal(() => clickMesa(id));
        const res = await api(`/mesas/${id}/abrir`, { method: 'POST', body: { usuario_id: usuario.id, nombre_cliente: "" } });
        await refreshMesas();
        openAccountView(id, res.orden_id);
      } else {
        // Si ya hay 1 o mas cuentas, SIEMPRE mostrar el mini modal
        showAccountsModal(m);
      }
    }

    function showAccountsModal(m) {
      const acts = m.ordenes.map(o => `
    <div style="display:flex;gap:8px;margin-bottom:8px;align-items:center;">
      <button class="btn btn-ghost" style="flex:1; justify-content:space-between; padding:14px; border-radius:10px" onclick="closeModal(); openAccountView(${m.id}, ${o.id})">
        <span style="font-weight:700">Cuenta: ${o.nombre_cliente || 'Sin nombre'}</span>
        <span>Entrar →</span>
      </button>
      <button onclick="cancelarCuentaDesdeModal(${o.id}, ${m.id})" title="Eliminar cuenta" style="padding:10px 12px;background:var(--red-light);color:var(--red);border:none;border-radius:10px;cursor:pointer;font-size:16px;flex-shrink:0;">🗑️</button>
    </div>`).join('');

      showModal(`<div class="modal-title">👥 Varias Cuentas</div><div class="modal-sub">Mesa ${m.numero}</div>
    <div style="max-height:300px; overflow-y:auto; margin-bottom:14px;">${acts}</div>
    <div class="modal-btns">
      <button class="btn btn-ghost" onclick="closeModal()">Cerrar</button>
      <button class="btn btn-sage" onclick="closeModal(); createNewAccountFromModal(${m.id})">+ Nueva Cuenta</button>
    </div>`);
    }

    async function cancelarCuentaDesdeModal(ordenId, mesaId) {
      if (!confirm('¿Eliminar esta cuenta? Se borrarán todos sus artículos.')) return;
      try {
        await api(`/ordenes/${ordenId}`, { method: 'DELETE' });
        await refreshMesas();
        const m = mesas.find(x => x.id === mesaId);
        closeModal();
        if (m && m.ordenes && m.ordenes.length > 0) {
          showAccountsModal(m);
        }
      } catch (e) { toast('❌', e.message, 'var(--red)'); }
    }

    async function createNewAccountFromModal(mesa_id) {
      if (!usuario) return showNipModal(() => createNewAccountFromModal(mesa_id));
      const res = await api(`/mesas/${mesa_id}/abrir`, { method: 'POST', body: { usuario_id: usuario.id, nombre_cliente: "" } });
      await refreshMesas();
      openAccountView(mesa_id, res.orden_id);
    }

    async function openAccountView(mesa_id, orden_id) {
      selectedMesa = mesas.find(x => x.id === mesa_id) || { id: mesa_id, numero: mesa_id };

      try {
        const todas = await api(`/mesas/${mesa_id}/ordenes`);
        currentOrden = todas.find(x => x.id === orden_id);
        selectedOrden = currentOrden;
      } catch { currentOrden = { items: [], total: 0, id: orden_id }; selectedOrden = currentOrden; }

      document.getElementById('mesasGrid').classList.add('hidden');
      const pv = document.getElementById('productsView');
      pv.classList.remove('hidden');
      document.getElementById('mesaBar').classList.remove('hidden');

      updateAccountLabels();
      document.getElementById('btnCancelarCuenta').classList.remove('hidden');
      renderOrder();
      if (tiendas.length) selectTab(tiendas[0]);
    }

    function updateAccountLabels() {
      if (!selectedMesa || !selectedOrden) return;
      const nom = selectedOrden.nombre_cliente;
      const label = nom ? `Mesa ${selectedMesa.numero} - ${nom}` : `Mesa ${selectedMesa.numero}`;
      document.getElementById('mesaBadge').textContent = label;
      document.getElementById('orderMesaInfo').textContent = label;
    }

    function backToMesas() {
      selectedMesa = null; selectedOrden = null; currentOrden = null;
      document.getElementById('productsView').classList.add('hidden');
      document.getElementById('mesasGrid').classList.remove('hidden');
      document.getElementById('orderMesaInfo').textContent = 'Selecciona una mesa';
      document.getElementById('btnCancelarCuenta').classList.add('hidden');
      renderOrder();
      refreshMesas();
    }

    async function renameMesa() {
      if (!selectedOrden) return;
      const curr = selectedOrden.nombre_cliente || "";
      showModal(`<div class="modal-title">🏷️ Nombre de Cuenta</div><div class="modal-sub">Mesa ${selectedMesa.numero}</div>
    <div class="field"><input type="text" id="mesaNombreIn" class="input" placeholder="Escribe el nombre del cliente..." value="${curr}" onkeydown="if(event.key==='Enter')doRenameMesa()"></div>
    <div class="modal-btns"><button class="btn btn-ghost" onclick="closeModal()">Cancelar</button><button class="btn btn-sage" onclick="doRenameMesa()">Guardar</button></div>`);
      setTimeout(() => document.getElementById('mesaNombreIn')?.focus(), 100);
    }

    async function doRenameMesa() {
      const n = document.getElementById('mesaNombreIn').value.trim();
      try {
        await api(`/ordenes/${selectedOrden.id}/nombre`, { method: 'PUT', body: { nombre: n } });
        selectedOrden.nombre_cliente = n;

        updateAccountLabels();
        closeModal();
        toast('✅', 'Nombre asignado');
      } catch (e) { toast('❌', e.message, 'var(--red)'); }
    }

    function confirmarCancelarCuenta() {
      if (!selectedOrden) return;
      showModal(`
    <div class="modal-title">🗑️ Cancelar Cuenta</div>
    <div class="modal-sub">¿Estás seguro de que quieres cancelar esta cuenta y eliminarla de la mesa permanentemente?</div>
    <div class="modal-btns" style="margin-top:20px;">
      <button class="btn btn-ghost" onclick="closeModal()">NO, volver</button>
      <button class="btn" style="background:var(--terracotta); color:white;" onclick="doCancelarCuenta()">SÍ, ELIMINAR</button>
    </div>
  `);
    }

    async function doCancelarCuenta() {
      if (!selectedOrden) return;
      if (!usuario) return showNipModal(() => doCancelarCuenta());
      try {
        await api(`/ordenes/${selectedOrden.id}`, { method: 'DELETE' });
        closeModal();
        toast('✅', 'Cuenta cancelada');
        backToMesas();
      } catch (e) {
        toast('❌', e.message, 'var(--red)');
      }
    }


    /* ── TABS ── */
    function renderTabs() {
      document.getElementById('tabsRow').innerHTML = tiendas.map(t =>
        `<button class="tab" data-id="${t.id}" onclick="selectTab(${JSON.stringify(t).replace(/"/g, '&quot;')})">${t.nombre}</button>`
      ).join('');
    }

    async function selectTab(t) {
      currentTienda = t;
      document.querySelectorAll('.tab').forEach(b => b.classList.toggle('active', +b.dataset.id === t.id));
      const sc = document.getElementById('productsScroll');
      const catDiv = document.getElementById('catFilters');
      document.getElementById('searchInput').value = "";
      searchFilter = "";
      document.getElementById('searchInput').value = "";
      searchFilter = "";
      categoryFilter = "";

      if (t.precio_abierto) {
        sc.innerHTML = `<div class="mack-center"><div class="mack-title">🛍️ Tienda Mack</div><div class="mack-sub">Precio abierto</div><button class="mack-btn" onclick="showMackModal()">＄ Agregar Venta</button></div>`;
        return;
      }
      const prods = await api(`/productos/${t.id}`);
      currentProducts = prods;
      // Si es Estación 304, cargar porciones del inventario de materia prima
      if (t.nombre.toLowerCase().includes('estaci')) {
        try {
          porcionesEstacion = await fetch('/api/estacion/porciones').then(r => r.json());
        } catch { porcionesEstacion = {}; }
      } else {
        porcionesEstacion = {};
      }

      if (!prods.length) { sc.innerHTML = `<div class="mack-center"><div class="mack-sub">Sin productos en ${t.nombre}</div></div>`; document.getElementById('catFilters').style.display = 'none'; return; }

      // Build dynamic category filters
      const uniqueCats = new Set();
      prods.forEach(p => {
        let cat = (p.categoria_producto || "Otros").trim();
        if (!cat) cat = "Otros";
        cat = cat.charAt(0).toUpperCase() + cat.slice(1);
        uniqueCats.add(cat);
      });

      let catHtml = `<button class="tab active" id="btnCatAll" onclick="setCategoryFilter('')">Todo</button>`;
      Array.from(uniqueCats).sort().forEach(cat => {
        catHtml += `<button class="tab" id="btnCat_${cat}" onclick="setCategoryFilter('${cat}')">${cat}</button>`;
      });

      const catFilters = document.getElementById('catFilters');
      catFilters.innerHTML = catHtml;
      catFilters.style.display = uniqueCats.size > 1 ? 'flex' : 'none'; // Only show if more than one category exists

      filterProducts();
    }

    function setCategoryFilter(k) {
      categoryFilter = k;

      // Update active states
      const catFilters = document.getElementById('catFilters');
      Array.from(catFilters.children).forEach(btn => {
        btn.classList.remove('active');
      });

      if (k === '') {
        document.getElementById('btnCatAll').classList.add('active');
      } else {
        const btn = document.getElementById('btnCat_' + k);
        if (btn) btn.classList.add('active');
      }

      filterProducts();
    }

    function filterProducts() {
      const sc = document.getElementById('productsScroll');
      searchFilter = document.getElementById('searchInput').value.toLowerCase().trim();

      // Con query: buscar en TODOS los productos de TODAS las tiendas
      if (searchFilter.length > 0) {
        const pool = allProductsGlobal || currentProducts;
        const resultados = pool.filter(p => p.nombre.toLowerCase().includes(searchFilter));
        if (!resultados.length) { sc.innerHTML = `<div class="mack-center"><div class="mack-sub">No se encontraron productos</div></div>`; return; }

        // Agrupar por tienda
        const byTienda = {};
        resultados.forEach(p => {
          const tn = p.tienda_nombre || (tiendas.find(t => t.id === p.tienda_id) || { nombre: 'Otra' }).nombre;
          if (!byTienda[tn]) byTienda[tn] = [];
          byTienda[tn].push(p);
        });

        let html = '';
        for (const [tiendaNombre, prods] of Object.entries(byTienda)) {
          const tiendaObj = tiendas.find(t => t.nombre === tiendaNombre) || { id: prods[0].tienda_id, nombre: tiendaNombre, precio_abierto: 0, es_barra: 0 };
          html += `<div style="padding:10px 10px 5px;font-weight:700;font-size:13px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.5px;">📍 ${tiendaNombre}</div>`;
          html += `<div class="products-grid" style="margin-bottom:12px;">${prods.map(p => renderProd(p, tiendaObj)).join('')}</div>`;
        }
        sc.innerHTML = html;
        return;
      }

      // Sin query: comportamiento normal (solo tienda activa + filtro de categoría)
      let prodFiltrados = currentProducts;
      if (categoryFilter !== "") {
        prodFiltrados = prodFiltrados.filter(p => p.categoria_producto === categoryFilter);
      }
      if (!prodFiltrados.length) { sc.innerHTML = `<div class="mack-center"><div class="mack-sub">No se encontraron productos</div></div>`; return; }

      const cats = {};
      prodFiltrados.forEach(p => {
        let cat = (p.categoria_producto || "Otros").trim();
        if (!cat) cat = "Otros";
        cat = cat.charAt(0).toUpperCase() + cat.slice(1);
        if (!cats[cat]) cats[cat] = [];
        cats[cat].push(p);
      });

      const colorsByCat = {
        "Bebidas": "var(--blue-light)",
        "Extras": "var(--rose-light)",
        "Roles": "var(--gold-light)",
        "Talleres": "var(--green-light)",
        "Productos": "var(--sage-light)"
      };

      let html = '';
      for (const [catName, prods] of Object.entries(cats)) {
        const bg = colorsByCat[catName] || "var(--bg-warm)";
        html += `<div style="padding:12px 10px 4px 10px; font-weight:700; font-size:13px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:.5px;">${catName}</div>`;
        html += `<div style="background:${bg}; padding:10px; border-radius:10px; margin-bottom:10px;">`;
        html += `<div class="products-grid">${prods.map(p => renderProd(p, currentTienda)).join('')}</div>`;
        html += `</div>`;
      }
      sc.innerHTML = html;
    }

    function renderProd(p, t) {
      const isAbierto = p.es_precio_abierto;
      const isBundle  = p.es_bundle;
      const esEstacion = t && t.nombre.toLowerCase().includes('estaci');

      // Para productos de Estación 304, usar porciones del inventario en vez de stock_local
      let efectivoStock = p.stock_local;
      let porcionInfo = null;
      if (esEstacion && Object.keys(porcionesEstacion).length) {
        const key = (p.receta_key || p.nombre).toUpperCase().trim();
        porcionInfo = porcionesEstacion[key] || null;
        if (porcionInfo) efectivoStock = porcionInfo.porciones;
      }

      const out = efectivoStock <= 0, low = !out && efectivoStock <= p.stock_minimo && p.stock_minimo > 0;
      let sc = 'stock-ok', st = esEstacion && porcionInfo ? `${efectivoStock} porc.` : `${efectivoStock}`;
      if (out) { sc = 'stock-out'; st = esEstacion && porcionInfo ? 'Sin insumos' : 'Agotado'; }
      else if (low) { sc = 'stock-low'; st = esEstacion && porcionInfo ? `⚠ ${efectivoStock} porc.` : `⚠ ${efectivoStock}`; }
      if (isAbierto) st = 'Abierto';
      if (isBundle) st = '📦 Paquete';
      const canAdd = !out || isAbierto || isBundle;
      return `<div class="prod-card ${!canAdd ? 'disabled' : ''}" onclick="${canAdd ? `prepareAddItem(${JSON.stringify(p).replace(/"/g, '&quot;')},${JSON.stringify(t).replace(/"/g, '&quot;')})` : ''}" ${isBundle ? 'style="border-color:var(--terracotta);background:var(--terracotta-light);"' : ''}>
    <div class="prod-name">${isBundle ? '📦 ' : ''} ${p.nombre}</div>
    <div class="prod-price">${isAbierto ? 'Monto Abierto' : '$' + p.precio.toFixed(2)}</div>
    <span class="stock-tag ${isBundle ? 'stock-low' : sc}">${st}</span>
    ${canAdd ? `<button class="prod-add" onclick="event.stopPropagation();prepareAddItem(${JSON.stringify(p).replace(/"/g, '&quot;')},${JSON.stringify(t).replace(/"/g, '&quot;')})">+ Agregar</button>` : ''}
  </div>`;
    }

    /* ── ADD ITEM ── */
    async function prepareAddItem(prod, tienda) {
      if (!usuario) return showNipModal(() => prepareAddItem(prod, tienda));

      if (prod.es_precio_abierto) {
        showModal(`<div class="modal-title">🛍️ ${prod.nombre}</div><div class="modal-sub">Monto variable requerido</div>
    <div class="field"><label>Descripción / Detalle</label><input type="text" id="paD" class="input" placeholder="Opcional: Detalle de venta" value="${prod.nombre}"></div>
    <div class="field"><label>Monto a cobrar</label><input type="number" id="paM" class="input" placeholder="0.00" step="0.01" onkeydown="if(event.key==='Enter')doAddItemAbierto(${prod.id}, ${tienda.id})"></div>
    <div class="modal-btns"><button class="btn btn-ghost" onclick="closeModal()">Cancelar</button><button class="btn btn-sage" onclick="doAddItemAbierto(${prod.id}, ${tienda.id})">Agregar</button></div>`);
        setTimeout(() => document.getElementById('paM')?.focus(), 100);
      } else if (prod.es_bundle) {
        let comps = [];
        try { comps = await api(`/bundle-components/${prod.id}`); } catch(e) {}
        const tieneComp304 = comps.some(c => c.tienda_id === 1);
        addItemFinal(prod, tienda, prod.nombre, prod.precio, false, tieneComp304);
      } else {
        addItemFinal(prod, tienda, prod.nombre, prod.precio, false, false);
      }
    }

    async function doAddItemAbierto(prodId, tiendaId) {
      let prod = currentProducts.find(p => p.id === prodId);
      let tienda = currentTienda;
      if (!prod) {
        // Product from a different tienda (found via global/inline search)
        prod = (allProductsGlobal || []).find(p => p.id === prodId);
        tienda = tiendas.find(t => t.id === tiendaId) || tienda;
      }
      if (!prod) return;
      const m = parseFloat(document.getElementById('paM').value);
      const d = document.getElementById('paD').value.trim() || prod.nombre;
      if (!m || m <= 0) return;
      closeModal();
      addItemFinal(prod, tienda, d, m, true);
    }

    async function addItemFinal(prod, tienda, nombre_hist, precio, abierto, tieneComp304 = false) {
      const cat = (prod.categoria_producto || "").trim().toLowerCase();
      const es304 = tienda.id === 1 || tieneComp304;
      if (es304 && cat !== "extras" && !abierto && !nombre_hist.includes("(Frío)") && !nombre_hist.includes("(Caliente)")) {
        nombre_hist += " (Frío)";
      }

      if (selectedOrden) {
        // Mesa mode: save to DB on specific order
        try {
          const res = await api(`/ordenes/${selectedOrden.id}/items`, {
            method: 'POST', body: {
              producto_id: prod.id, tienda_id: tienda.id, nombre: nombre_hist,
              cantidad: 1, precio_unitario: precio, es_precio_abierto: abierto
            }
          });
          // refresh order
          const todas = await api(`/mesas/${selectedMesa.id}/ordenes`);
          currentOrden = todas.find(x => x.id === selectedOrden.id);
          selectedOrden = currentOrden;
          renderOrder();
        } catch (e) { toast('❌', e.message, 'var(--red)'); return; }
      } else {
        // Direct sale mode
        if (abierto) {
          directCart.push({ producto_id: prod.id, tienda_id: tienda.id, nombre: nombre_hist, cantidad: 1, precio_unitario: precio, es_precio_abierto: true, categoria_producto: prod.categoria_producto });
        } else {
          directCart.push({ producto_id: prod.id, tienda_id: tienda.id, nombre: nombre_hist, cantidad: 1, precio_unitario: precio, es_precio_abierto: false, categoria_producto: prod.categoria_producto, tieneComp304 });
        }
        renderOrder();
      }
      if (!abierto && prod.stock_local <= prod.stock_minimo && prod.stock_local > 0) toast('⚠️', `Stock bajo: ${prod.nombre}`, 'var(--gold)');
    }

    /* ── ORDER RENDERING ── */
    function getOrderItems() {
      if (selectedOrden && currentOrden) return currentOrden.items || [];
      return directCart;
    }
    function getOrderSubtotal() {
      return getOrderItems().reduce((s, i) => s + i.cantidad * i.precio_unitario, 0);
    }
    function getOrderTotal() {
      const sub = getOrderSubtotal();
      return sub + calcPropina(sub);
    }

    function renderOrder() {
      const items = getOrderItems();
      const subtotal = getOrderSubtotal();
      const propina = calcPropina(subtotal);
      const total = subtotal + propina;
      const cnt = items.reduce((s, i) => s + i.cantidad, 0);
      document.getElementById('orderCount').textContent = cnt;
      document.getElementById('orderTotal').textContent = `$${total.toLocaleString('es-MX', { minimumFractionDigits: 2 })}`;
      document.getElementById('btnCobrar').disabled = items.length === 0;
      const badge = document.getElementById('cartFabBadge');
      if (badge) { badge.textContent = cnt; badge.style.display = cnt > 0 ? 'flex' : 'none'; }

      // Mostrar subtotal + propina si hay propina activa
      const showPropina = propina > 0;
      document.getElementById('subtotalRow').style.display = showPropina ? 'flex' : 'none';
      document.getElementById('propinaAmtRow').style.display = showPropina ? 'flex' : 'none';
      if (showPropina) {
        document.getElementById('subtotalAmt').textContent = `$${subtotal.toLocaleString('es-MX', { minimumFractionDigits: 2 })}`;
        document.getElementById('propinaAmt').textContent = `$${propina.toLocaleString('es-MX', { minimumFractionDigits: 2 })}`;
      }

      if (metodoPago === 'Mixto' && items.length > 0) {
        calcMixto('efectivo');
      }
      const c = document.getElementById('orderItems');
      if (!items.length) { c.innerHTML = `<div class="order-empty"><span class="order-empty-icon">📋</span><span>Sin artículos</span></div>`; return; }

      c.innerHTML = items.map((it, idx) => {
        const n = it.nombre_producto || it.nombre;
        const sub = (it.cantidad * it.precio_unitario).toFixed(2);
        const removeAction = selectedMesa ? `removeDbItem(${it.id})` : `removeCartItem(${idx})`;
        const pId = it.producto_id || 'null';
        const editAction = selectedMesa ? `showEditItemModalDb(${it.id}, '${n.replace(/'/g, "\\'")}', ${it.precio_unitario}, ${it.tienda_id}, ${pId})` : `showEditItemModalCart(${idx}, '${n.replace(/'/g, "\\'")}', ${it.precio_unitario}, ${pId})`;
        return `<div class="order-item">
      <div class="oi-info"><div class="oi-name">${n}</div><div class="oi-detail">x${it.cantidad} · $${it.precio_unitario.toFixed(2)}</div></div>
      <div class="oi-price" style="display:flex; align-items:center; gap:6px;">
        $${sub}
        <button class="oi-edit" onclick="${editAction}" style="background:none;border:none;cursor:pointer;font-size:12px;" title="Editar">✏️</button>
      </div>
      <button class="oi-remove" onclick="${removeAction}">✕</button>
    </div>`;
      }).join('');
    }
    async function removeDbItem(itemId) {
      await api(`/orden-items/${itemId}`, { method: 'DELETE' });
      const todas = await api(`/mesas/${selectedMesa.id}/ordenes`);
      currentOrden = todas.find(x => x.id === selectedOrden.id) || { items: [], total: 0 };
      selectedOrden = currentOrden;
      renderOrder();
    }
    function removeCartItem(idx) { directCart.splice(idx, 1); renderOrder(); }

    function limpiarOrden() {
      if (selectedMesa) { toast('ℹ️', 'Elimina artículos uno por uno'); return; }
      directCart = []; renderOrder();
    }

    window.allExtrasTienda1 = []; // Cache to avoid duplicate fetch

    function applyDiscount(inputId, priceInputId) {
      const dsc = parseFloat(document.getElementById(inputId)?.value) || 0;
      const orig = parseFloat(document.getElementById(inputId)?.dataset.orig) || 0;
      if (dsc < 0 || dsc > 100 || !orig) return;
      document.getElementById(priceInputId).value = (orig * (1 - dsc / 100)).toFixed(2);
    }

    async function showEditItemModalDb(id, nombre, precio, tienda_id, producto_id) {
      const cleanNombre = nombre.replace(" (Frío)", "").replace(" (Caliente)", "");
      const isC = nombre.includes("(Caliente)");

      const parts = cleanNombre.split(" - ");
      const baseNombre = parts[0].trim();
      const clienteNombre = parts.length > 1 ? parts.slice(1).join(" - ").trim() : "";

      // Try to find category
      let cat = "";
      if (producto_id && currentProducts.length) {
        const f = currentProducts.find(x => x.id === producto_id);
        if (f) cat = (f.categoria_producto || "").trim().toLowerCase();
      }

      let tempHtml = "";
      if (tienda_id === 1 && cat !== "extras") {
        tempHtml = `
    <div class="field"><label>Temperatura</label>
      <select id="edTemp" class="input">
        <option value=" (Frío)" ${!isC ? 'selected' : ''}>Frío (por defecto)</option>
        <option value=" (Caliente)" ${isC ? 'selected' : ''}>Caliente</option>
        <option value="">N/A (Omitir)</option>
      </select>
    </div>`;
      }

      let extrasHtml = "";
      if (tienda_id === 1) {
        if (window.allExtrasTienda1.length === 0) {
          try {
            // Fetch all products for tienda 1 to get extras
            const prods1 = await api('/productos/1');
            window.allExtrasTienda1 = prods1.filter(p => {
              const c = (p.categoria_producto || "").trim().toLowerCase();
              return (c === "extras" || c === "extra") && p.stock_local > 0;
            });
          } catch (e) { }
        }
        if (window.allExtrasTienda1.length > 0) {
          const opts = window.allExtrasTienda1.map(ex => `<option value="${ex.id}">${ex.nombre} (+$${ex.precio})</option>`).join('');
          extrasHtml = `
          <div class="field"><label>Agregar Extra</label>
            <select id="edExtra" class="input">
              <option value="">Ninguno</option>
              ${opts}
            </select>
          </div>`;
        }
      }

      const labelCliente = tienda_id === 1 ? 'Nombre en vaso / Cliente' : 'Nota / Cliente';
      showModal(`<div class="modal-title">✏️ Editar Artículo</div>
    <div class="field"><label>Descripción Base</label><input type="text" id="edN_base" class="input" value="${baseNombre}" readonly style="background:#f4f4f4; color:#888;"></div>
    <div class="field"><label>${labelCliente}</label><input type="text" id="edN_cliente" class="input" value="${clienteNombre}"></div>
    ${tempHtml}
    ${extrasHtml}
    <div class="field"><label>Precio Unitario</label><input type="number" id="edP" class="input" step="0.01" value="${precio}" onkeydown="if(event.key==='Enter')doEditItemDb(${id})"></div>
    <div class="field"><label>Descuento (%)</label><div style="display:flex;gap:8px;align-items:center;"><input type="number" id="edDsc" class="input" style="width:80px" min="0" max="100" step="1" value="0" data-orig="${precio}" oninput="applyDiscount('edDsc','edP')"><button type="button" class="btn btn-ghost btn-sm" onclick="applyDiscount('edDsc','edP')">Aplicar</button><span style="font-size:11px;color:var(--text-muted)">0% = sin descuento</span></div></div>
    <div class="modal-btns"><button class="btn btn-ghost" onclick="closeModal()">Cancelar</button><button class="btn btn-sage" onclick="doEditItemDb(${id})">Guardar</button></div>`);
      setTimeout(() => document.getElementById('edN_cliente')?.focus(), 100);
    }

    async function doEditItemDb(id) {
      const baseN = document.getElementById('edN_base').value.trim();
      const clienteN = document.getElementById('edN_cliente').value.trim();
      const n = baseN + (clienteN ? " - " + clienteN : "");
      const tempEl = document.getElementById('edTemp');
      const t = tempEl ? tempEl.value : "";
      const p = parseFloat(document.getElementById('edP').value);
      if (!n || isNaN(p) || p < 0) return;
      const finalName = n + t;

      const extEl = document.getElementById('edExtra');

      try {
        await api(`/orden-items/${id}`, { method: 'PUT', body: { nombre: finalName, precio_unitario: p } });

        // Add extra if selected
        if (extEl && extEl.value) {
          const extraId = parseInt(extEl.value);
          const extraProd = window.allExtrasTienda1.find(x => x.id === extraId);
          if (extraProd) {
            await api(`/ordenes/${selectedOrden.id}/items`, {
              method: 'POST', body: {
                producto_id: extraProd.id, tienda_id: 1, nombre: `+ ${extraProd.nombre}`,
                cantidad: 1, precio_unitario: extraProd.precio, es_precio_abierto: false
              }
            });
          }
        }

        closeModal();
        const todas = await api(`/mesas/${selectedMesa.id}/ordenes`);
        currentOrden = todas.find(x => x.id === selectedOrden.id) || { items: [], total: 0 };
        selectedOrden = currentOrden;
        renderOrder();
        toast('✅', 'Artículo actualizado');
      } catch (e) { toast('❌', e.message, 'var(--red)'); }
    }

    async function showEditItemModalCart(idx, nombre, precio, producto_id) {
      if (nombre === undefined) nombre = directCart[idx].nombre;
      if (precio === undefined) precio = directCart[idx].precio_unitario;
      if (producto_id === undefined) producto_id = directCart[idx].producto_id;
      const cleanNombre = nombre.replace(" (Frío)", "").replace(" (Caliente)", "");
      const isC = nombre.includes("(Caliente)");
      const tienda_id = directCart[idx].tienda_id;
      const tieneComp304 = directCart[idx].tieneComp304 || false;
      const es304 = tienda_id === 1 || tieneComp304;
      const cat = (directCart[idx].categoria_producto || "").trim().toLowerCase();

      const parts = cleanNombre.split(" - ");
      const baseNombre = parts[0].trim();
      const clienteNombre = parts.length > 1 ? parts.slice(1).join(" - ").trim() : "";

      let tempHtml = "";
      if (es304 && cat !== "extras") {
        tempHtml = `
    <div class="field"><label>Temperatura</label>
      <select id="edTemp" class="input">
        <option value=" (Frío)" ${!isC ? 'selected' : ''}>Frío (por defecto)</option>
        <option value=" (Caliente)" ${isC ? 'selected' : ''}>Caliente</option>
        <option value="">N/A (Omitir)</option>
      </select>
    </div>`;
      }

      let extrasHtml = "";
      if (es304) {
        if (window.allExtrasTienda1.length > 0) {
          const opts = window.allExtrasTienda1.map(ex => `<option value="${ex.id}">${ex.nombre} (+$${ex.precio})</option>`).join('');
          extrasHtml = `
          <div class="field"><label>Agregar Extra</label>
            <select id="edExtra" class="input">
              <option value="">Ninguno</option>
              ${opts}
            </select>
          </div>`;
        }
      }

      const labelClienteC = es304 ? 'Nombre en vaso / Cliente' : 'Nota / Cliente';
      showModal(`<div class="modal-title">✏️ Editar Artículo</div>
    <div class="field"><label>Descripción Base</label><input type="text" id="edN_base" class="input" value="${baseNombre}" readonly style="background:#f4f4f4; color:#888;"></div>
    <div class="field"><label>${labelClienteC}</label><input type="text" id="edN_cliente" class="input" value="${clienteNombre}"></div>
    ${tempHtml}
    ${extrasHtml}
    <div class="field"><label>Precio Unitario</label><input type="number" id="edP" class="input" step="0.01" value="${precio}" onkeydown="if(event.key==='Enter')doEditItemCart(${idx})"></div>
    <div class="field"><label>Descuento (%)</label><div style="display:flex;gap:8px;align-items:center;"><input type="number" id="edDsc" class="input" style="width:80px" min="0" max="100" step="1" value="0" data-orig="${precio}" oninput="applyDiscount('edDsc','edP')"><button type="button" class="btn btn-ghost btn-sm" onclick="applyDiscount('edDsc','edP')">Aplicar</button><span style="font-size:11px;color:var(--text-muted)">0% = sin descuento</span></div></div>
    <div class="modal-btns"><button class="btn btn-ghost" onclick="closeModal()">Cancelar</button><button class="btn btn-sage" onclick="doEditItemCart(${idx})">Guardar</button></div>`);
      setTimeout(() => document.getElementById('edN_cliente')?.focus(), 100);
    }

    function doEditItemCart(idx) {
      const baseN = document.getElementById('edN_base').value.trim();
      const clienteN = document.getElementById('edN_cliente').value.trim();
      const n = baseN + (clienteN ? " - " + clienteN : "");
      const tempEl = document.getElementById('edTemp');
      const t = tempEl ? tempEl.value : "";
      const p = parseFloat(document.getElementById('edP').value);
      const extEl = document.getElementById('edExtra');

      if (!n || isNaN(p) || p < 0) return;
      const finalName = n + t;

      directCart[idx].nombre = finalName;
      directCart[idx].precio_unitario = p;

      if (extEl && extEl.value) {
        const extraId = parseInt(extEl.value);
        const extraProd = window.allExtrasTienda1.find(x => x.id === extraId);
        if (extraProd) {
          directCart.push({
            producto_id: extraProd.id, tienda_id: 1, nombre: `+ ${extraProd.nombre}`,
            cantidad: 1, precio_unitario: extraProd.precio, es_precio_abierto: false,
            categoria_producto: "Extras"
          });
        }
      }

      closeModal();
      renderOrder();
      toast('✅', 'Artículo actualizado');
    }

    function selPay(el) {
      document.querySelectorAll('.pay-btn').forEach(b => b.classList.remove('active'));
      el.classList.add('active');
      metodoPago = el.dataset.m;
      if (metodoPago === 'Mixto') {
        document.getElementById('mixtoFields').classList.remove('hidden');
        calcMixto('efectivo');
      } else {
        document.getElementById('mixtoFields').classList.add('hidden');
      }
    }

    function calcEfectivo(valStr) {
      const total = getOrderTotal();
      if (!total) return;
      const ef = parseFloat(valStr) || 0;
      const lbl = document.getElementById('efectivoCambio');
      const d = ef - total;
      if (d >= 0) {
        lbl.textContent = `Cambio: $${d.toFixed(2)}`;
        lbl.style.color = "var(--green)";
      } else {
        lbl.textContent = `Faltan: $${Math.abs(d).toFixed(2)}`;
        lbl.style.color = "var(--red)";
      }
    }

    function calcMixto(source) {
      const total = getOrderTotal();
      if (!total) return;
      const efInput = document.getElementById('mixEfectivo');
      const tarInput = document.getElementById('mixTarjeta');

      if (source === 'efectivo') {
        let ef = parseFloat(efInput.value) || 0;
        if (ef > total) ef = total;
        tarInput.value = (total - ef).toFixed(2);
      } else {
        let tar = parseFloat(tarInput.value) || 0;
        if (tar > total) tar = total;
        efInput.value = (total - tar).toFixed(2);
      }
    }

    /* ── COBRAR ── */
    async function cobrar() {
      if (!usuario) return showNipModal(cobrar);
      const baseItems = getOrderItems();
      if (!baseItems.length) return;

      // Para efectivo → mostrar modal de cambio primero
      if (metodoPago === 'Efectivo') {
        showCashModal();
        return;
      }

      await _procesarCobro(0);
    }

    function showCashModal() {
      const total = getOrderTotal();
      showModal(`<div class="modal-body">
    <div class="modal-title">💵 Cobro en Efectivo</div>
    <div style="text-align:center;padding:16px 0 8px;">
      <div style="font-size:12px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;">Total a cobrar</div>
      <div style="font-size:52px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--sage-dark);">$${total.toLocaleString('es-MX', { minimumFractionDigits: 2 })}</div>
    </div>
    <div class="field">
      <label>Monto recibido del cliente</label>
      <input type="number" id="cashIn" class="input" style="font-size:28px;text-align:center;font-family:'JetBrains Mono',monospace;padding:14px;" placeholder="0.00" step="0.01" oninput="updateCashChange(${total})" onkeydown="if(event.key==='Enter')confirmarCobroCash(${total})">
    </div>
    <div id="cashChangeBox" style="text-align:center;padding:20px 0;display:none;">
      <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Cambio a entregar</div>
      <div id="cashChangeAmt" style="font-size:64px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--green-ok);line-height:1;"></div>
    </div>
    <div id="cashFaltaBox" style="text-align:center;padding:12px 0;display:none;">
      <div id="cashFaltaAmt" style="font-size:20px;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--red);"></div>
    </div>
  </div>
  <div class="modal-footer">
    <div class="modal-btns" style="margin-top:0">
      <button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
      <button id="btnConfirmCash" class="btn btn-sage" onclick="confirmarCobroCash(${total})" disabled style="font-size:15px;padding:11px 28px;">✓ Confirmar Cobro</button>
    </div>
  </div>`);
      const m = document.querySelector('#modals .modal'); if (m) { m.style.width = '440px'; m.style.maxWidth = '98vw'; }
      setTimeout(() => document.getElementById('cashIn')?.focus(), 80);
    }

    function updateCashChange(total) {
      const recibido = parseFloat(document.getElementById('cashIn')?.value) || 0;
      const cambio = recibido - total;
      const changeBox = document.getElementById('cashChangeBox');
      const faltaBox = document.getElementById('cashFaltaBox');
      const btn = document.getElementById('btnConfirmCash');
      if (recibido <= 0) {
        changeBox.style.display = 'none'; faltaBox.style.display = 'none'; btn.disabled = true; return;
      }
      if (cambio >= 0) {
        document.getElementById('cashChangeAmt').textContent = '$' + cambio.toLocaleString('es-MX', { minimumFractionDigits: 2 });
        changeBox.style.display = 'block'; faltaBox.style.display = 'none'; btn.disabled = false;
      } else {
        document.getElementById('cashFaltaAmt').textContent = 'Faltan $' + Math.abs(cambio).toLocaleString('es-MX', { minimumFractionDigits: 2 });
        faltaBox.style.display = 'block'; changeBox.style.display = 'none'; btn.disabled = true;
      }
    }

    async function confirmarCobroCash(total) {
      const recibido = parseFloat(document.getElementById('cashIn')?.value) || 0;
      if (recibido < total) return;
      closeModal();
      await _procesarCobro(recibido);
    }

    async function _procesarCobro(efectivo_recibido) {
      const baseItems = getOrderItems();
      const subtotal = getOrderSubtotal();
      const propinaMonto = calcPropina(subtotal);
      let itemsConPropina = [...baseItems];
      if (propinaMonto > 0) {
        const tiendaRef = baseItems[0]?.tienda_id || tiendas[0]?.id || 1;
        const etiqueta = propinaPct > 0 ? `Propina (${propinaPct}%)` : 'Propina';
        itemsConPropina.push({ producto_id: null, tienda_id: tiendaRef, nombre: etiqueta, cantidad: 1, precio_unitario: propinaMonto, es_precio_abierto: true });
      }

      let ef = 0.0, tar = 0.0;
      const total = getOrderTotal();
      if (metodoPago === 'Mixto') {
        ef = parseFloat(document.getElementById('mixEfectivo').value) || 0;
        tar = parseFloat(document.getElementById('mixTarjeta').value) || 0;
        if (Math.abs((ef + tar) - total) > 0.01) { toast('⚠️', 'La suma mixta no cuadra', 'var(--gold)'); return; }
      }

      try {
        let data;
        if (selectedOrden) {
          if (propinaMonto > 0) {
            const tiendaRef = baseItems[0]?.tienda_id || tiendas[0]?.id || 1;
            const etiqueta = propinaPct > 0 ? `Propina (${propinaPct}%)` : 'Propina';
            await api(`/ordenes/${selectedOrden.id}/items`, {
              method: 'POST', body: {
                tienda_id: tiendaRef, nombre: etiqueta, cantidad: 1,
                precio_unitario: propinaMonto, es_precio_abierto: true
              }
            });
          }
          data = await api(`/ordenes/${selectedOrden.id}/cerrar`, { method: 'POST', body: { usuario_id: usuario.id, metodo_pago: metodoPago, monto_efectivo: ef, monto_tarjeta: tar, efectivo_recibido } });
        } else {
          data = await api('/ventas', { method: 'POST', body: { usuario_id: usuario.id, metodo_pago: metodoPago, items: itemsConPropina, monto_efectivo: ef, monto_tarjeta: tar, efectivo_recibido } });
          directCart = [];
        }
        document.getElementById('propinaCheck').checked = false;
        document.getElementById('propinaControls').classList.add('hidden');
        showReceiptModal(data);
        renderOrder();
        if (selectedMesa) { backToMesas(); }
      } catch (e) { toast('❌', e.message, 'var(--red)'); }
    }

    /* ── MODALS ── */
    let _fpActive = false;
    let _fpRendered = false; // true after first render into fpBody

    function showModal(h) {
      h = demojify(h);
      if (_fpActive && !_fpRendered) {
        const body = document.getElementById('fpBody');
        if (body) {
          _fpRendered = true;
          body.innerHTML = h.trimStart().startsWith('<div class="modal-body">') ? h : `<div class="modal-simple" style="max-width:100%;box-shadow:none;border:none;padding:0;">${h}</div>`;
          return;
        }
      }
      const inner = h.trimStart().startsWith('<div class="modal-body">')
        ? h
        : `<div class="modal-simple">${h}</div>`;
      document.getElementById('modals').innerHTML = `<div class="modal-bg" onclick="if(event.target===this)closeModal()"><div class="modal">${inner}</div></div>`;
    }
    function closeModal() {
      document.getElementById('modals').innerHTML = '';
      // Si estamos en modo página, re-renderizar el contenido de la página
      if (_fpActive && document.getElementById('fpBody') && !document.getElementById('fpBody').innerHTML.trim()) {
        document.getElementById('fpBody').innerHTML = '<div style="padding:20px;color:var(--text-muted)">← Usa el botón Volver</div>';
      }
    }

    async function openPage(title, fn) {
      const fp = document.getElementById('fullpage');
      fp.innerHTML = demojify(`
    <div class="fp-header">
      <button class="fp-back" onclick="closePage()">←</button>
      <div class="fp-title">${title}</div>
    </div>
    <div class="fp-body" id="fpBody" style="display:flex;align-items:center;justify-content:center;">
      <span style="color:var(--text-muted);font-size:13px;">Cargando…</span>
    </div>`);
      fp.classList.remove('hidden');
      closeSidebar();
      _fpActive = true;
      _fpRendered = false;
      try { await fn(); } catch (e) { document.getElementById('fpBody').innerHTML = demojify(`<div style="padding:30px;color:var(--red);">❌ ${e.message}</div>`); }
      const fpBody = document.getElementById('fpBody');
      if (fpBody) fpBody.style.display = '';
    }

    function closePage() {
      _fpActive = false;
      _fpRendered = false;
      const fp = document.getElementById('fullpage');
      fp.classList.add('hidden');
      fp.innerHTML = '';
      // Re-enable closeModal for regular modals
      document.getElementById('modals').innerHTML = '';
    }

    function toggleSidebar() {
      const s = document.querySelector('.sidebar');
      const isOpen = s.classList.contains('sidebar-open');
      s.classList.toggle('sidebar-open');
      document.getElementById('sidebarOverlay').classList.toggle('active', !isOpen);
    }
    function closeSidebar() {
      document.querySelector('.sidebar').classList.remove('sidebar-open');
      document.getElementById('sidebarOverlay').classList.remove('active');
    }

    function toggleSidebarCollapse() {
      const sb = document.querySelector('.sidebar');
      const app = document.querySelector('.app');
      const collapsed = sb.classList.toggle('sb-collapsed');
      app.classList.toggle('sb-collapsed', collapsed);
      document.body.classList.toggle('sb-collapsed', collapsed);
      document.getElementById('fullpage').style.left = collapsed ? '52px' : 'var(--sb-w)';
      localStorage.setItem('sb-collapsed', collapsed ? '1' : '0');
    }

    // Restaurar estado del sidebar al cargar
    (function () {
      if (localStorage.getItem('sb-collapsed') === '1') {
        document.querySelector('.sidebar')?.classList.add('sb-collapsed');
        document.querySelector('.app')?.classList.add('sb-collapsed');
        document.body.classList.add('sb-collapsed');
        const fp = document.getElementById('fullpage');
        if (fp) fp.style.left = '52px';
      }
    })();

    function toggleCart() {
      document.getElementById('orderPanel').classList.toggle('cart-open');
    }

    function setBottomNav(id) {
      document.querySelectorAll('.bottom-nav-btn').forEach(b => b.classList.remove('active'));
      const el = document.getElementById('bn' + id.charAt(0).toUpperCase() + id.slice(1));
      if (el) el.classList.add('active');
    }

    let nipCb = null;
    function showNipModal(cb) {
      nipCb = cb || null;
      showModal(`<div class="modal-title">🔑 Ingresar</div><div class="modal-sub">NIP de 4 dígitos</div>
    <div class="field"><input type="password" id="nipIn" class="input input-nip" maxlength="4" placeholder="● ● ● ●" autofocus onkeydown="if(event.key==='Enter')doNip()"></div>
    <div class="modal-err" id="nipErr"></div>
    <div class="modal-btns"><button class="btn btn-ghost" onclick="closeModal()">Cancelar</button><button class="btn btn-sage" onclick="doNip()">Validar</button></div>`);
      setTimeout(() => document.getElementById('nipIn')?.focus(), 100);
    }
    async function doNip() {
      const v = document.getElementById('nipIn').value, e = document.getElementById('nipErr');
      if (v.length !== 4 || !/^\d+$/.test(v)) { e.textContent = 'NIP de 4 dígitos'; return; }
      try {
        usuario = await api('/auth', { method: 'POST', body: { nip: v } });
        document.getElementById('userName').textContent = `${usuario.nombre}`;
        document.getElementById('userPill').classList.add('active');
        document.getElementById('topUserName').textContent = `${usuario.nombre}`;
        document.getElementById('topUserPill').classList.add('active');
        document.getElementById('topDot').style.background = 'var(--green-ok)';
        if (usuario.perfil === 'Administrador') document.getElementById('navCatalog').classList.remove('hidden');
        closeModal(); toast('✅', `Hola, ${usuario.nombre}`);
        if (nipCb) { const c = nipCb; nipCb = null; if (_fpActive) _fpRendered = false; c(); }
      } catch { e.textContent = 'NIP incorrecto'; document.getElementById('nipIn').value = ''; document.getElementById('nipIn').focus(); }
    }

    function showMackModal() {
      showModal(`<div class="modal-title">🛍️ Venta Mack</div><div class="modal-sub">Precio abierto</div>
    <div class="field"><label>Descripción</label><input type="text" id="mkD" class="input" placeholder="Ej: Bolsa azul"></div>
    <div class="field"><label>Monto</label><input type="number" id="mkM" class="input" placeholder="0.00" step="0.01" onkeydown="if(event.key==='Enter')addMk()"></div>
    <div class="modal-btns"><button class="btn btn-ghost" onclick="closeModal()">Cancelar</button><button class="btn btn-sage" onclick="addMk()">Agregar</button></div>`);
      setTimeout(() => document.getElementById('mkD')?.focus(), 100);
    }
    async function addMk() {
      const m = parseFloat(document.getElementById('mkM').value), d = document.getElementById('mkD').value.trim() || 'Artículo Mack';
      if (!m || m <= 0) return;
      const t = tiendas.find(x => x.precio_abierto);
      if (selectedOrden && t) {
        await api(`/ordenes/${selectedOrden.id}/items`, { method: 'POST', body: { tienda_id: t.id, nombre: d, cantidad: 1, precio_unitario: m, es_precio_abierto: true } });
        const todas = await api(`/mesas/${selectedMesa.id}/ordenes`);
        currentOrden = todas.find(x => x.id === selectedOrden.id);
        selectedOrden = currentOrden;
      } else if (t) {
        directCart.push({ producto_id: null, tienda_id: t.id, nombre: d, cantidad: 1, precio_unitario: m, es_precio_abierto: true });
      }
      renderOrder(); closeModal();
    }

    async function showFondoModal() {
      if (!usuario) return showNipModal(showFondoModal);
      try {
        const res = await api('/fondo');
        if (res.fondo > 0) {
          showModal(`<div class="modal-simple"><div class="modal-title">🏦 Caja Abierta</div>
        <div style="text-align:center;padding:24px 0 12px;">
          <div style="font-size:48px;margin-bottom:8px;">✅</div>
          <div style="font-size:14px;color:var(--text-secondary);margin-bottom:6px;">La caja ya fue abierta hoy</div>
          <div style="font-size:28px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--sage-dark);">$${res.fondo.toFixed(2)}</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:8px;">Solo se puede abrir una vez al día</div>
        </div>
        <div class="modal-btns"><button class="btn btn-sage" onclick="closeModal()">Entendido</button></div></div>`);
          return;
        }
      } catch (e) { /* si falla el check, dejamos abrir */ }
      showModal(`<div class="modal-simple"><div class="modal-title">🏦 Abrir Caja</div><div class="modal-sub">Fondo de caja al inicio del turno</div>
    <div class="field"><label>Monto del fondo</label><input type="number" id="fM" class="input" placeholder="0.00" step="0.01" onkeydown="if(event.key==='Enter')doFondo()"></div>
    <div class="modal-btns"><button class="btn btn-ghost" onclick="closeModal()">Cancelar</button><button class="btn" style="background:#66BB6A;color:white;" onclick="doFondo()">Guardar Fondo</button></div></div>`);
      setTimeout(() => document.getElementById('fM')?.focus(), 100);
    }
    async function doFondo() {
      const m = parseFloat(document.getElementById('fM').value);
      if (isNaN(m) || m < 0) return;
      try {
        await api('/fondo', { method: 'POST', body: { monto: m } });
        closeModal(); toast('✅', `Fondo de caja: $${m.toFixed(2)}`, 'var(--green-ok)');
      } catch (e) {
        toast('⚠️', e.message || 'La caja ya fue abierta hoy', 'var(--gold)');
      }
    }

    function showIngresoModal() {
      if (!usuario) return showNipModal(showIngresoModal);
      const ingresoTiendas = tiendas.filter(t => t.nombre === 'Estudio Deco' || t.nombre === 'Estación 304');
      const ingOpts = ingresoTiendas.map(t => `<option value="${t.id}">${t.nombre}</option>`).join('');
      showModal(`<div class="modal-simple"><div class="modal-title">💰 Registrar Ingreso</div><div class="modal-sub">Pago recibido fuera de ventas</div>
    <div class="field"><label>Destino</label><select id="iT" class="input">${ingOpts}</select></div>
    <div class="field"><label>Concepto</label><input id="iC" class="input" placeholder="Ej: Anticipo taller, abono cliente"></div>
    <div class="field"><label>Monto</label><input type="number" id="iM" class="input" placeholder="0.00" step="0.01"></div>
    <div class="field"><label>Método de pago</label><select id="iP" class="input"><option value="Efectivo">💵 Efectivo</option><option value="Tarjeta">💳 Tarjeta / Transferencia</option></select></div>
    <div class="modal-btns"><button class="btn btn-ghost" onclick="closeModal()">Cancelar</button><button class="btn" style="background:#26A69A;color:white;" onclick="doIngreso()">Guardar Ingreso</button></div></div>`);
      setTimeout(() => document.getElementById('iC')?.focus(), 100);
    }
    async function doIngreso() {
      const tid = +document.getElementById('iT').value;
      const c = document.getElementById('iC').value.trim(), m = parseFloat(document.getElementById('iM').value), p = document.getElementById('iP').value;
      if (!c || !m || m <= 0) return;
      const estacionT = tiendas.find(t => t.nombre === 'Estación 304');
      if (estacionT && tid === estacionT.id) {
        const hoy = new Date().toISOString().split('T')[0];
        await api('/pagos-tienda', { method: 'POST', body: {
          tienda_id: tid, tienda_nombre: 'Estación 304',
          monto: m, metodo_pago: p, concepto: c,
          es_interno: true, semana_inicio: hoy, semana_fin: hoy
        }});
      } else {
        await api('/ingresos', { method: 'POST', body: { usuario_id: usuario.id, concepto: c, monto: m, metodo_pago: p } });
      }
      closeModal(); toast('✅', `Ingreso: $${m.toFixed(2)} (${p})`, 'var(--green-ok)');
    }

    function showGastoModal() {
      if (!usuario) return showNipModal(showGastoModal);
      const gastoTiendas = tiendas.filter(t => t.nombre === 'Estudio Deco' || t.nombre === 'Estación 304');
      const opts = gastoTiendas.map(t => `<option value="${t.id}">${t.nombre}</option>`).join('');
      showModal(`<div class="modal-simple"><div class="modal-title">💸 Registrar Gasto</div><div class="modal-sub">Salida de dinero</div>
    <div class="field"><label>Origen de los fondos</label><select id="gO" class="input"><option value="Caja">Caja Fuerte / Efectivo</option><option value="Banco">Cuenta de Banco / Transferencia</option></select></div>
    <div class="field"><label>Tienda</label><select id="gT" class="input">${opts}</select></div>
    <div class="field"><label>Concepto</label><input id="gC" class="input" placeholder="Ej: Compra de leche"></div>
    <div class="field"><label>Monto</label><input type="number" id="gM" class="input" placeholder="0.00" step="0.01"></div>
    <div class="modal-btns"><button class="btn btn-ghost" onclick="closeModal()">Cancelar</button><button class="btn btn-terracotta" onclick="doGasto()">Guardar</button></div></div>`);
    }
    async function doGasto() {
      const c = document.getElementById('gC').value.trim(), m = parseFloat(document.getElementById('gM').value), t = document.getElementById('gT').value, o = document.getElementById('gO').value;
      if (!c || !m || m <= 0) return;
      await api('/gastos', { method: 'POST', body: { usuario_id: usuario.id, tienda_id: t ? +t : null, concepto: c, monto: m, origen: o } });
      closeModal(); toast('✅', `Gasto: $${m.toFixed(2)} (${o})`);
      if (!document.getElementById('semanalView').classList.contains('hidden')) loadSemanal();
    }

    async function showCorteModal() {
      if (!usuario) return showNipModal(showCorteModal);
      if (usuario.perfil !== 'Administrador') { toast('⚠️', 'Solo Administrador', 'var(--gold)'); return; }
      const r = await api('/report/corte');
      const esp = r.efectivo_esperado;
      const comTar = parseFloat(((r.total_tarjeta || 0) * 0.04).toFixed(2));
      const tarNeta = parseFloat(((r.total_tarjeta || 0) - comTar).toFixed(2));
      const totalTransfer = r.total_transferencia || 0;
      const totalEsp = parseFloat((esp + tarNeta + totalTransfer).toFixed(2));
      const fondoApertura = r.fondo_apertura || 0;
      const desdeStr = r.desde ? r.desde.slice(11, 19) : '00:00:00';
      const sabroCard = '';

      // Conteo ventas por método
      const conteo = r.conteo_metodos || [];
      const conteoHtml = conteo.map(c => {
        const icon = c.metodo_pago === 'Efectivo' ? '💵' : c.metodo_pago === 'Tarjeta' ? '💳' : c.metodo_pago === 'Transferencia' ? '🏦' : '⚖️';
        return `<span style="background:var(--bg-warm);border:1px solid var(--border);border-radius:20px;padding:2px 10px;font-size:11px;white-space:nowrap;">${icon} ${c.metodo_pago} <strong>${c.n}</strong> · $${c.monto.toFixed(0)}</span>`;
      }).join('');

      // Charts data
      const segsPago = [
        { label: 'Efectivo', value: r.total_efectivo || 0, color: '#4CAF50' },
        { label: 'Tarjeta', value: r.total_tarjeta || 0, color: '#C9A84C' },
        { label: 'Transfer.', value: (r.metodos_pago || []).find(m => m.metodo_pago === 'Transferencia')?.monto || 0, color: '#26A69A' },
      ].filter(s => s.value > 0);
      const legendPago = segsPago.map(s => `<div style="display:flex;align-items:center;gap:5px;font-size:11px;"><span style="width:10px;height:10px;border-radius:50%;background:${s.color};display:inline-block;flex-shrink:0;"></span>${s.label}<br><strong style="font-size:12px;">$${s.value.toFixed(0)}</strong></div>`).join('');

      const TIENDA_COLORS = ['#7C9A7E', '#C4755A', '#C9A84C', '#26A69A', '#5C6BC0', '#EC407A', '#8D6E63'];
      const barsTienda = (r.ventas_por_tienda || []).map((t, i) => ({ label: t.tienda, value: t.neto ?? t.total, color: TIENDA_COLORS[i % TIENDA_COLORS.length] }));

      // Canceladas del día
      const canceladasBadge = r.num_canceladas > 0 ? `<span style="background:var(--red);color:white;border-radius:4px;padding:1px 7px;font-size:11px;margin-left:8px;">${r.num_canceladas} cancelada(s)</span>` : '';

      const BILLS = [1000, 500, 200, 100, 50, 20], COINS = [10, 5, 2, 1, 0.5];
      const bRows = BILLS.map(d => `<div class="denom-row"><span class="denom-label">$${d.toLocaleString()}</span><input type="number" id="b${d}" class="input denom-input" value="0" min="0" oninput="calcCorte(${esp})"><span class="denom-sub" id="bs${d}"></span></div>`).join('');
      const cRows = COINS.map(d => `<div class="denom-row"><span class="denom-label">$${d % 1 ? d : Math.trunc(d)}</span><input type="number" id="m${d}" class="input denom-input" value="0" min="0" oninput="calcCorte(${esp})"><span class="denom-sub" id="ms${d}"></span></div>`).join('');
      showModal(`<div class="modal-body">
    <div class="modal-title">📊 Corte de Caja</div>
    <div class="modal-sub">Turno desde ${desdeStr} · ${r.num_ventas} ticket${r.num_ventas !== 1 ? 's' : ''}${canceladasBadge}</div>
    ${conteoHtml ? `<div style="display:flex;flex-wrap:wrap;gap:5px;margin:6px 0 10px;">${conteoHtml}</div>` : ''}

    <!-- Tarjetas de totales -->
    <div class="resumen-grid" style="margin-bottom:10px;grid-template-columns:repeat(3,1fr);">
      <div class="res-card"><div class="res-label">💵 Efectivo</div><div class="res-val v">$${(r.total_efectivo || 0).toFixed(2)}</div></div>
      <div class="res-card">
        <div class="res-label">💳 Tarjeta (bruto)</div>
        <div class="res-val" style="color:var(--gold)">$${(r.total_tarjeta || 0).toFixed(2)}</div>
        ${comTar > 0 ? `<div style="font-size:10px;color:var(--red);margin-top:2px;">− $${comTar.toFixed(2)} comisión 4%</div>` : ''}
      </div>
      <div class="res-card"><div class="res-label">📦 Gastos</div><div class="res-val g">-$${r.total_gastos.toFixed(2)}</div></div>
    </div>
    <div class="resumen-grid" style="margin-bottom:12px;grid-template-columns:repeat(${totalTransfer > 0 ? 4 : 3},1fr);">
      <div class="res-card" style="background:var(--green-light);border:1px solid var(--sage);"><div class="res-label" style="color:var(--green-ok)">💵 Ef. en Caja</div><div class="res-val" style="color:var(--green-ok)">$${esp.toFixed(2)}</div></div>
      <div class="res-card" style="background:var(--gold-light);border:1px solid var(--gold);"><div class="res-label" style="color:var(--gold)">💳 Tarjeta Neta</div><div class="res-val" style="color:var(--gold)">$${tarNeta.toFixed(2)}</div></div>
      ${totalTransfer > 0 ? `<div class="res-card" style="background:#E0F2F1;border:1px solid #26A69A;"><div class="res-label" style="color:#00796B">🏦 Transferencia</div><div class="res-val" style="color:#00796B">$${totalTransfer.toFixed(2)}</div></div>` : ''}
      <div class="res-card" style="background:var(--sage-light);border:1px solid var(--sage);"><div class="res-label" style="color:var(--sage-dark)">TOTAL GENERAL</div><div class="res-val" style="color:var(--sage-dark)">$${totalEsp.toFixed(2)}</div></div>
    </div>

    <!-- Gráficas -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
      <div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:12px;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:8px;">Métodos de pago</div>
        <div style="display:flex;align-items:center;gap:10px;">
          ${svgDonut(segsPago, 100)}
          <div style="display:flex;flex-direction:column;gap:6px;">${legendPago}</div>
        </div>
      </div>
      <div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:12px;overflow:hidden;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:8px;">Ventas neto por tienda</div>
        ${barsTienda.length ? svgBarsH(barsTienda, 140, 20, 6) : '<span style="font-size:11px;color:var(--text-muted)">Sin datos</span>'}
      </div>
    </div>

    ${sabroCard}
    <div class="field"><label>🏦 Fondo de caja inicial</label><input type="number" id="cFondo" class="input" value="${fondoApertura}" min="0" placeholder="0.00" oninput="calcCorte(${esp})"></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">
      <div><div style="font-size:10px;font-weight:700;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">💵 Billetes</div>${bRows}</div>
      <div><div style="font-size:10px;font-weight:700;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">🪙 Monedas</div>${cRows}</div>
    </div>
    <div style="background:var(--bg);border-radius:var(--radius-sm);padding:10px 14px;font-size:12px;margin-bottom:14px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:3px;"><span style="color:var(--text-muted)">Total contado:</span><span id="cTotalCont" style="font-family:'JetBrains Mono',monospace;font-weight:700;">$0.00</span></div>
      <div style="display:flex;justify-content:space-between;margin-bottom:3px;"><span style="color:var(--text-muted)">Menos fondo de caja:</span><span id="cMenosFondo" style="font-family:'JetBrains Mono',monospace;">-$0.00</span></div>
      <div style="display:flex;justify-content:space-between;padding-top:6px;border-top:1px solid var(--border);margin-bottom:3px;"><span style="font-weight:700;">Efectivo real (ventas):</span><span id="cReal" style="font-family:'JetBrains Mono',monospace;font-weight:700;">$0.00</span></div>
      <div style="display:flex;justify-content:space-between;margin-bottom:3px;"><span style="color:var(--text-muted)">Esperado (sistema):</span><span style="font-family:'JetBrains Mono',monospace;color:var(--text-muted);">$${esp.toFixed(2)}</span></div>
      <div style="display:flex;justify-content:space-between;padding-top:6px;border-top:1px solid var(--border);"><span style="font-weight:700;">Diferencia:</span><span id="cDif" style="font-family:'JetBrains Mono',monospace;font-weight:700;">$0.00</span></div>
    </div>
  </div>
  <div class="modal-footer">
    <div class="modal-btns" style="margin-top:0">
      <button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
      <button class="btn" style="background:#4a5568;color:white;" onclick="printCorteDia()">🖨️ Imprimir Z</button>
      <button class="btn btn-sage" onclick="doCorte()">✓ Confirmar Corte</button>
    </div>
  </div>`);
      const m = document.querySelector('#modals .modal');
      if (m) { m.style.width = '760px'; m.style.maxWidth = '98vw'; }
    }
    async function printCorteDia() {
      try {
        await api('/cortes/imprimir', { method: 'POST', body: { usuario_id: usuario.id } });
        toast('✅', 'Imprimiendo corte de caja...');
      } catch (e) { toast('❌', e.message, 'var(--red)'); }
    }
    function calcCorte(esp) {
      const BILLS = [1000, 500, 200, 100, 50, 20], COINS = [10, 5, 2, 1, 0.5];
      let total = 0;
      BILLS.forEach(d => {
        const q = parseInt(document.getElementById('b' + d)?.value) || 0;
        const sub = d * q; total += sub;
        const el = document.getElementById('bs' + d);
        if (el) el.textContent = q > 0 ? '= $' + sub.toLocaleString() : '';
      });
      COINS.forEach(d => {
        const q = parseInt(document.getElementById('m' + d)?.value) || 0;
        const sub = d * q; total += sub;
        const el = document.getElementById('ms' + d);
        if (el) el.textContent = q > 0 ? '= $' + sub.toFixed(2) : '';
      });
      const fondo = parseFloat(document.getElementById('cFondo')?.value) || 0;
      const real = total - fondo, dif = real - esp;
      document.getElementById('cTotalCont').textContent = '$' + total.toFixed(2);
      document.getElementById('cMenosFondo').textContent = '-$' + fondo.toFixed(2);
      document.getElementById('cReal').textContent = '$' + real.toFixed(2);
      const el = document.getElementById('cDif');
      el.textContent = (dif >= 0 ? '+' : '') + ' $' + Math.abs(dif).toFixed(2);
      el.style.color = dif >= 0 ? 'var(--green-ok)' : 'var(--red)';
    }
    async function doCorte() {
      const BILLS = [1000, 500, 200, 100, 50, 20], COINS = [10, 5, 2, 1, 0.5];
      let total = 0; const desglose = {};
      BILLS.forEach(d => { const q = parseInt(document.getElementById('b' + d)?.value) || 0; if (q) desglose['B' + d] = q; total += d * q; });
      COINS.forEach(d => { const q = parseInt(document.getElementById('m' + d)?.value) || 0; if (q) desglose['M' + d] = q; total += d * q; });
      const fondo = parseFloat(document.getElementById('cFondo')?.value) || 0;
      const efectivo_real = total - fondo;
      const d = await api('/corte', { method: 'POST', body: { usuario_id: usuario.id, efectivo_real, fondo_caja: fondo, desglose } });
      closeModal(); const dif = d.resumen.diferencia; toast('✅', `Corte OK · Dif: ${dif >= 0 ? '+' : ''}$${dif.toFixed(2)}`);
    }

    function showReceiptModal(d) {
      showModal(`<div class="modal-title">✅ Venta Registrada</div>
    <div class="modal-sub">Folio: ${d.venta.folio} · ${d.impreso ? '🖨 Impreso' : '⚠ Sin impresora'} · Cajero: ${d.cajero}</div>
    <div style="background:var(--bg);border-radius:var(--radius-sm);padding:16px;text-align:center;margin-top:14px;">
      <div style="font-size:28px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--sage-dark);">$${d.venta.total.toLocaleString('es-MX', { minimumFractionDigits: 2 })}</div>
      <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">${d.venta.metodo_pago}</div>
    </div>
    <div class="modal-btns"><button class="btn btn-sage" onclick="closeModal()">Cerrar</button></div>`);
    }

    /* ── CATALOG (CRUD) ── */
    async function loadCatalog() {
      try {
        const prods = await api('/catalog');
        const tb = document.getElementById('catalogTbody');
        tb.innerHTML = prods.map(p => `<tr>
      <td>${p.tienda_nombre}</td>
      <td style="color:var(--text-muted);font-size:11px;">${p.categoria_producto || '-'}</td>
      <td style="font-weight:600">${p.nombre}</td>
      <td style="font-family:'JetBrains Mono',monospace;color:var(--sage)">$${p.precio.toFixed(2)}</td>
      <td style="font-family:'JetBrains Mono',monospace;color:var(--text-muted)">$${(p.costo || 0).toFixed(2)}</td>
      <td>${p.stock_local}</td>
      <td style="color:var(--text-muted)">${p.stock_minimo}</td>
      <td>${p.es_precio_abierto ? 'Sí' : (p.es_bundle ? '📦 Bundle' : 'No')}</td>
      <td>
        <div class="cat-actions">
          <button class="btn-icon btn-edit" onclick='showCatalogModal(${JSON.stringify(p).replace(/'/g, "&#39;")})'>✏️</button>
          ${p.es_bundle ? `<button class="btn-icon" style="background:var(--sage-light);color:var(--sage);" onclick="showBundleModal(${p.id},'${p.nombre.replace(/'/g, "\\'")}',${p.precio})" title="Gestionar componentes">📦</button>` : ''}
          <button class="btn-icon btn-del" onclick="deleteProduct(${p.id}, '${p.nombre.replace(/'/g, "\\'")}')">🗑️</button>
        </div>
      </td>
    </tr>`).join('');
      } catch (e) { toast('❌', e.message, 'var(--red)'); }
    }

    async function showCatalogModal(p = null) {
      const isPromo = p ? (tiendas.find(t => t.id === p.tienda_id)?.nombre === 'Promociones') : false;
      const opts = tiendas.map(t => `<option value="${t.id}" ${p && p.tienda_id === t.id ? 'selected' : ''}>${t.nombre}</option>`).join('');
      // Cargar recetas disponibles
      let recetasOpts = '<option value="">— Sin receta —</option>';
      try {
        const recetas = await fetch('/api/estacion/recetas').then(r => r.json());
        recetasOpts += recetas.map(r => `<option value="${r.nombre}" ${p && p.receta_key === r.nombre ? 'selected' : ''}>${r.nombre}</option>`).join('');
      } catch {}
      showModal(`<div class="modal-title">${p ? '✏️ Editar' : '📦 Nuevo'} Producto</div>
    <div class="resumen-grid" style="grid-template-columns:1fr 1fr; margin:0 0 10px 0;">
      <div class="field" style="margin:0"><label>Tienda</label><select id="catTienda" class="input" onchange="onCatTiendaChange()">${opts}</select></div>
      <div class="field" style="margin:0"><label>Categoría</label><select id="catCat" class="input"><option value="">Ninguna</option><option value="Bebidas" ${p && p.categoria_producto === 'Bebidas' ? 'selected' : ''}>Bebidas</option><option value="Extras" ${p && p.categoria_producto === 'Extras' ? 'selected' : ''}>Extras</option><option value="roles" ${p && p.categoria_producto === 'roles' ? 'selected' : ''}>Roles</option><option value="talleres" ${p && p.categoria_producto === 'talleres' ? 'selected' : ''}>Talleres</option><option value="productos" ${p && p.categoria_producto === 'productos' ? 'selected' : ''}>Productos</option></select></div>
    </div>
    <div class="field"><label>Nombre del paquete / producto</label><input type="text" id="catNombre" class="input" value="${p ? p.nombre : ''}"></div>
    <div class="field" id="catRecetaRow">
      <label>Receta de inventario</label>
      <select id="catReceta" class="input">${recetasOpts}</select>
      <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">Solo para Estación 304 — descuenta insumos al vender esta bebida</div>
    </div>
    <div class="resumen-grid" style="grid-template-columns:1fr 1fr; margin:0 0 10px 0;">
      <div class="field" style="margin:0"><label>Precio de Venta</label><input type="number" id="catPrecio" class="input" step="0.01" value="${p ? p.precio : ''}"></div>
      <div class="field" style="margin:0"><label>Costo (Inversión)</label><input type="number" id="catCosto" class="input" step="0.01" value="${p ? (p.costo || 0) : ''}"></div>
    </div>
    <div class="resumen-grid" style="grid-template-columns:1fr 1fr; margin:0 0 14px 0;">
      <div class="field" style="margin:0"><label>Stock Real</label><input type="number" id="catStock" class="input" value="${p ? p.stock_local : '0'}"></div>
      <div class="field" style="margin:0"><label>Min. Alerta</label><input type="number" id="catMin" class="input" value="${p ? p.stock_minimo : '5'}"></div>
    </div>
    <div class="field" style="display:flex;align-items:center;gap:8px;">
        <input type="checkbox" id="catAbierto" ${p && p.es_precio_abierto ? 'checked' : ''} style="width:16px;height:16px;accent-color:var(--sage);">
        <label for="catAbierto" style="margin:0;cursor:pointer;">Es producto de precio abierto (preguntar importe al vender)</label>
    </div>
    <div class="field" style="display:flex;align-items:center;gap:8px;">
        <input type="checkbox" id="catBundle" ${(p && p.es_bundle) || isPromo ? 'checked' : ''} onchange="onCatBundleChange()" style="width:16px;height:16px;accent-color:var(--terracotta);">
        <label for="catBundle" style="margin:0;cursor:pointer;">📦 Es paquete (incluye artículos de varias tiendas)</label>
    </div>
    <div id="bundleHint" style="display:${(p && p.es_bundle) || isPromo ? 'block' : 'none'};background:var(--terracotta-light);border-radius:var(--radius-sm);padding:10px 12px;font-size:12px;color:#7B3F00;margin-top:6px;">
      ${p && p.es_bundle ? `✅ Paquete guardado. <strong>Guarda primero</strong> cualquier cambio de nombre/precio y luego edita los artículos con el botón <strong>📦</strong> en la tabla.`
          : '⬆️ Guarda el paquete primero. Después podrás agregar los artículos que lo forman.'}
    </div>
    <div class="modal-btns"><button class="btn btn-ghost" onclick="closeModal()">Cancelar</button><button class="btn btn-sage" onclick="saveProduct(${p ? p.id : null})">Guardar</button></div>`);
    }

    function onCatTiendaChange() {
      const sel = document.getElementById('catTienda');
      const nombre = sel.options[sel.selectedIndex]?.text || '';
      if (nombre === 'Promociones') {
        document.getElementById('catBundle').checked = true;
        onCatBundleChange();
      }
    }
    function onCatBundleChange() {
      const checked = document.getElementById('catBundle').checked;
      const hint = document.getElementById('bundleHint');
      if (hint) hint.style.display = checked ? 'block' : 'none';
    }

    async function saveProduct(id) {
      const tid = parseInt(document.getElementById('catTienda').value);
      const n = document.getElementById('catNombre').value.trim();
      const p = parseFloat(document.getElementById('catPrecio').value);
      const c = parseFloat(document.getElementById('catCosto').value) || 0.0;
      const s = parseInt(document.getElementById('catStock').value) || 0;
      const m = parseInt(document.getElementById('catMin').value) || 0;
      const cat = document.getElementById('catCat').value;
      const ab = document.getElementById('catAbierto').checked;
      const isBundle = document.getElementById('catBundle').checked;
      const receta_key = document.getElementById('catReceta')?.value || '';

      if (!n || isNaN(p) || isNaN(tid)) return toast('⚠️', 'Llena los datos principales');

      try {
        const body = { tienda_id: tid, nombre: n, precio: p, costo: c, stock_local: s, stock_minimo: m, codigo: "", es_precio_abierto: ab, es_bundle: isBundle ? 1 : 0, categoria_producto: cat, receta_key };
        if (id) {
          await api(`/catalog/${id}`, { method: 'PUT', body });
          toast('✅', 'Producto actualizado');
        } else {
          await api('/catalog', { method: 'POST', body });
          toast('✅', 'Producto creado');
        }
        closeModal();
        loadCatalog();
      } catch (e) { toast('❌', e.message, 'var(--red)'); }
    }

    async function deleteProduct(id, nombre) {
      if (!confirm(`¿Seguro que deseas eliminar: ${nombre}? \n(Se ocultará del catálogo pero seguirá visible en reportes históricos)`)) return;
      try {
        await api(`/catalog/${id}`, { method: 'DELETE' });
        toast('✅', 'Producto eliminado');
        loadCatalog();
      } catch (e) { toast('❌', e.message, 'var(--red)'); }
    }

    function toast(ic, msg, bc) {
      document.querySelectorAll('.toast').forEach(t => t.remove());
      const t = document.createElement('div'); t.className = 'toast';
      if (bc) t.style.borderLeftColor = bc; t.style.borderLeft = `3px solid ${bc || 'var(--sage)'}`;
      t.innerHTML = `<span class="toast-ico">${iconize(ic, 16)}</span><span>${msg}</span>`;
      document.body.appendChild(t); setTimeout(() => t.remove(), 3500);
    }

    /* ── VENTAS DEL DÍA ── */
    async function showVentasHoyModal() {
      if (!usuario) return showNipModal(showVentasHoyModal);
      let ventas;
      try { ventas = await api('/ventas/hoy'); } catch (e) { toast('❌', e.message, 'var(--red)'); return; }

      let filtroMetodo = 'Todos';
      const metIcon = m => icon(m === 'Efectivo' ? 'cash' : m === 'Tarjeta' ? 'card' : m === 'Transferencia' ? 'transfer' : m === 'Mixto' ? 'mix' : 'phone', 14);

      function renderVentaCard(v, isCancelled) {
        const hora = v.created_at ? v.created_at.slice(11, 16) : '';
        const itemsHtml = (v.items || []).map(it => `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:3px 0;border-bottom:1px solid var(--border-light);">
        <div style="flex:1;min-width:0;">
          <span style="font-size:12px;${isCancelled ? 'text-decoration:line-through;color:var(--text-muted);' : ''}">${it.nombre_producto}</span>
          <span style="font-size:11px;color:var(--text-muted);margin-left:6px;">x${it.cantidad} · $${it.precio_unitario.toFixed(2)}</span>
        </div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:600;color:var(--text-muted);flex-shrink:0;">$${it.subtotal.toFixed(2)}</span>
      </div>`).join('');

        const comisionTar = (v.metodo_pago === 'Tarjeta' || v.metodo_pago === 'Mixto') && v.monto_tarjeta > 0
          ? parseFloat((v.monto_tarjeta * 0.04).toFixed(2)) : 0;
        let pagoInfo = `<span style="display:inline-flex;align-items:center;gap:4px;">${metIcon(v.metodo_pago)} ${v.metodo_pago}</span>`;
        if (v.metodo_pago === 'Mixto') pagoInfo = `<span style="display:inline-flex;align-items:center;gap:4px;">${icon('mix', 14)} Mixto: ${icon('cash', 13)} $${v.monto_efectivo.toFixed(2)} + ${icon('card', 13)} $${v.monto_tarjeta.toFixed(2)}</span>`;
        if (comisionTar > 0) pagoInfo += ` <span style="font-size:10px;color:var(--red);margin-left:4px;">−$${comisionTar.toFixed(2)} com.</span>`;

        const bgHead = isCancelled ? '#FFF3F3' : 'var(--bg-warm)';
        const borderColor = isCancelled ? 'var(--red)' : 'var(--border)';
        const totalColor = isCancelled ? 'var(--red)' : 'var(--sage-dark)';

        return `<div style="background:var(--surface);border:1px solid ${borderColor};border-radius:var(--radius-sm);margin-bottom:10px;overflow:hidden;${isCancelled ? 'opacity:0.75' : ''}">
      <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:${bgHead};">
        <div style="flex:1;min-width:0;">
          <span style="font-size:12px;font-weight:700;font-family:'JetBrains Mono',monospace;${isCancelled ? 'text-decoration:line-through;' : ''}">${v.folio}</span>
          ${isCancelled ? '<span style="font-size:10px;background:var(--red);color:white;border-radius:4px;padding:1px 6px;margin-left:6px;">CANCELADA</span>' : ''}
          <span style="font-size:11px;color:var(--text-muted);margin-left:8px;">${hora} · ${v.cajero_nombre}</span>
        </div>
        <span style="font-size:11px;color:var(--text-secondary);margin-right:6px;">${pagoInfo}</span>
        <span style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:15px;color:${totalColor};">$${v.total.toFixed(2)}</span>
        <button class="btn-icon" style="background:var(--sage-light);color:var(--sage);flex-shrink:0;" onclick="reimprimirTicket(${v.id})" title="Reimprimir ticket">${icon('print', 15)}</button>
        <button class="btn-icon" style="background:#FFF3E0;color:#E65100;flex-shrink:0;" onclick="reimprimirComanda(${v.id})" title="Reimprimir comanda">${icon('list', 15)}</button>
        ${!isCancelled && usuario.perfil === 'Administrador' ? `
        <button class="btn-icon btn-edit" onclick="showEditVentaModal(${v.id},'${v.folio}',${v.total},'${v.metodo_pago}',${v.monto_efectivo},${v.monto_tarjeta})" title="Corregir pago" style="flex-shrink:0;">${icon('edit', 15)}</button>
        <button class="btn-icon btn-del" onclick="confirmarAnularVenta(${v.id},'${v.folio}')" title="Anular venta" style="flex-shrink:0;">${icon('trash', 15)}</button>` : ''}
      </div>
      <div style="padding:8px 14px 10px;">${itemsHtml || '<span style="font-size:11px;color:var(--text-muted)">Sin artículos</span>'}</div>
    </div>`;
      }

      function renderVentasHoy() {
        const match = v => filtroMetodo === 'Todos' || v.metodo_pago === filtroMetodo;
        const todasActivas = ventas.filter(v => !v.cancelada);
        const activas = todasActivas.filter(match);
        const canceladas = ventas.filter(v => v.cancelada && match(v));
        // KPIs always reflect the full day; only the list follows the chip filter
        const totalDia = todasActivas.reduce((s, v) => s + v.total, 0);
        const totalEf = todasActivas.filter(v => v.metodo_pago === 'Efectivo').reduce((s, v) => s + v.total, 0);
        const totalTar = todasActivas.filter(v => v.metodo_pago === 'Tarjeta').reduce((s, v) => s + v.total, 0);
        const totalTrn = todasActivas.filter(v => v.metodo_pago === 'Transferencia').reduce((s, v) => s + v.total, 0);

        const chip = (id, labelHtml) => {
          const on = filtroMetodo === id;
          return `<button onclick="window._ventasHoyFiltro('${id}')" style="padding:6px 14px;border-radius:20px;cursor:pointer;font-size:12px;font-weight:600;display:inline-flex;align-items:center;gap:5px;${on ? 'background:var(--sage-dark);color:#fff;border:none;' : 'background:var(--bg-warm);color:var(--text-secondary);border:1px solid var(--border);'}">${labelHtml}</button>`;
        };

        const rows = activas.length
          ? activas.map(v => renderVentaCard(v, false)).join('')
          : '<div style="padding:30px;text-align:center;color:var(--text-muted);">Sin ventas con este filtro</div>';

        const canceladasHtml = canceladas.length
          ? `<div style="margin-top:16px;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--red);letter-spacing:.5px;margin-bottom:8px;display:flex;align-items:center;gap:6px;">${icon('trash', 13)} Ventas Canceladas (${canceladas.length})</div>
        ${canceladas.map(v => renderVentaCard(v, true)).join('')}
       </div>` : '';

        showModal(`<div class="modal-body">
    <div class="modal-title" style="display:flex;align-items:center;gap:8px;">${icon('list', 20)} Ventas de Hoy</div>
    <div class="modal-sub">${activas.length} venta${activas.length !== 1 ? 's' : ''}${canceladas.length ? ` · ${canceladas.length} cancelada${canceladas.length !== 1 ? 's' : ''}` : ''}</div>
    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;">
      ${chip('Todos', 'Todos')}
      ${chip('Efectivo', icon('cash', 13) + ' Efectivo')}
      ${chip('Tarjeta', icon('card', 13) + ' Tarjeta')}
      ${chip('Transferencia', icon('transfer', 13) + ' Transferencia')}
    </div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px;">
      <div class="res-card"><div class="res-label">Total</div><div class="res-val" style="color:var(--sage-dark);font-size:15px;">$${totalDia.toFixed(2)}</div></div>
      <div class="res-card"><div class="res-label" style="display:flex;align-items:center;gap:4px;">${icon('cash', 12)} Efectivo</div><div class="res-val v" style="font-size:15px;">$${totalEf.toFixed(2)}</div></div>
      <div class="res-card"><div class="res-label" style="display:flex;align-items:center;gap:4px;">${icon('card', 12)} Tarjeta</div><div class="res-val" style="color:var(--gold);font-size:15px;">$${totalTar.toFixed(2)}</div></div>
      <div class="res-card"><div class="res-label" style="display:flex;align-items:center;gap:4px;">${icon('transfer', 12)} Transfer.</div><div class="res-val" style="color:var(--blue);font-size:15px;">$${totalTrn.toFixed(2)}</div></div>
    </div>
    <div style="max-height:480px;overflow-y:auto;">${rows}${canceladasHtml}</div>
  </div>
  <div class="modal-footer"><div class="modal-btns" style="margin-top:0"><button class="btn btn-ghost" onclick="closeModal()">Cerrar</button></div></div>`);
        const m = document.querySelector('#modals .modal'); if (m) { m.style.width = '720px'; m.style.maxWidth = '98vw'; }
      }

      window._ventasHoyFiltro = (f) => { filtroMetodo = f; renderVentasHoy(); };
      renderVentasHoy();
    }

    async function reimprimirTicket(vid) {
      try {
        const r = await api(`/ventas/${vid}/reimprimir`, { method: 'POST' });
        toast(r.impreso ? '✅' : '⚠️', r.impreso ? 'Ticket reimpreso' : 'Sin impresora', r.impreso ? 'var(--green-ok)' : 'var(--gold)');
      } catch (e) { toast('❌', e.message, 'var(--red)'); }
    }

    async function reimprimirComanda(vid) {
      try {
        const r = await api(`/ventas/${vid}/reimprimir_comanda`, { method: 'POST' });
        if (r.msg) toast('⚠️', r.msg, 'var(--gold)');
        else toast(r.impreso ? '✅' : '⚠️', r.impreso ? 'Comanda reimpresa' : 'Sin impresora', r.impreso ? 'var(--green-ok)' : 'var(--gold)');
      } catch (e) { toast('❌', e.message, 'var(--red)'); }
    }

    function showAjusteBalanceModal(cajaActual, bancoActual) {
      if (usuario?.perfil !== 'Administrador') { toast('⚠️', 'Solo Administrador', 'var(--gold)'); return; }
      showModal(`<div class="modal-title">✏️ Ajustar Balance</div>
    <div class="modal-sub">Ingresa el monto real que tienes ahora mismo. El sistema calculará la diferencia automáticamente.</div>
    <div style="display:flex;flex-direction:column;gap:14px;margin-top:18px;">
      <div>
        <label class="input-label">💵 Efectivo en Caja</label>
        <input id="ajusteCaja" type="number" class="input" step="0.01" value="${cajaActual.toFixed(2)}" placeholder="0.00">
      </div>
      <div>
        <label class="input-label">🏦 Monto en Banco / Tarjeta</label>
        <input id="ajusteBanco" type="number" class="input" step="0.01" value="${bancoActual.toFixed(2)}" placeholder="0.00">
      </div>
    </div>
    <div class="modal-btns" style="margin-top:20px;">
      <button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-sage" onclick="doAjusteBalance()">Guardar Ajuste</button>
    </div>`);
    }

    async function doAjusteBalance() {
      const caja = parseFloat(document.getElementById('ajusteCaja')?.value) || 0;
      const banco = parseFloat(document.getElementById('ajusteBanco')?.value) || 0;
      try {
        await api('/balance/ajustar', { method: 'POST', body: { caja, banco } });
        toast('✅', 'Balance ajustado', 'var(--green-ok)');
        closeModal();
        loadSemanal();
      } catch (e) { toast('❌', e.message, 'var(--red)'); }
    }

    function showEditVentaModal(vid, folio, total, metodo, montoEf, montoTar) {
      if (usuario.perfil !== 'Administrador') { toast('⚠️', 'Solo Administrador', 'var(--gold)'); return; }
      showModal(`<div class="modal-title">✏️ Corregir Venta</div>
    <div class="modal-sub">Folio: ${folio} · Total: $${total.toFixed(2)}</div>
    <div class="field"><label>Método de Pago</label>
      <select id="cvMetodo" class="input" onchange="updateCvAmounts(${total})">
        <option value="Efectivo" ${metodo === 'Efectivo' ? 'selected' : ''}>💵 Efectivo</option>
        <option value="Tarjeta" ${metodo === 'Tarjeta' ? 'selected' : ''}>💳 Tarjeta</option>
        <option value="Transferencia" ${metodo === 'Transferencia' ? 'selected' : ''}>📱 Transferencia</option>
        <option value="Mixto" ${metodo === 'Mixto' ? 'selected' : ''}>⚖️ Mixto</option>
      </select>
    </div>
    <div id="cvAmounts">
      <div class="field"><label>Monto Efectivo</label><input type="number" id="cvEf" class="input" step="0.01" value="${montoEf}"></div>
      <div class="field"><label>Monto Tarjeta / Transfer.</label><input type="number" id="cvTar" class="input" step="0.01" value="${montoTar}"></div>
    </div>
    <div class="modal-btns">
      <button class="btn btn-ghost" onclick="showVentasHoyModal()">← Volver</button>
      <button class="btn btn-sage" onclick="doCorregirVenta(${vid}, ${total})">Guardar</button>
    </div>`);
      updateCvAmounts(total);
    }

    function updateCvAmounts(total) {
      const m = document.getElementById('cvMetodo')?.value;
      const ef = document.getElementById('cvEf');
      const tar = document.getElementById('cvTar');
      if (!ef || !tar) return;
      if (m === 'Efectivo') { ef.value = total.toFixed(2); tar.value = '0.00'; }
      else if (m === 'Tarjeta' || m === 'Transferencia') { ef.value = '0.00'; tar.value = total.toFixed(2); }
    }

    async function doCorregirVenta(vid, total) {
      const metodo = document.getElementById('cvMetodo').value;
      const ef = parseFloat(document.getElementById('cvEf').value) || 0;
      const tar = parseFloat(document.getElementById('cvTar').value) || 0;
      try {
        await api(`/ventas/${vid}`, { method: 'PUT', body: { metodo_pago: metodo, monto_efectivo: ef, monto_tarjeta: tar } });
        toast('✅', 'Venta corregida'); showVentasHoyModal();
      } catch (e) { toast('❌', e.message, 'var(--red)'); }
    }

    function confirmarAnularVenta(vid, folio) {
      showModal(`<div class="modal-title">🗑️ Anular Venta</div>
    <div class="modal-sub">¿Anular el folio <strong>${folio}</strong>? Se repondrá el stock y se eliminará el registro.</div>
    <div class="modal-btns" style="margin-top:20px;">
      <button class="btn btn-ghost" onclick="showVentasHoyModal()">Cancelar</button>
      <button class="btn" style="background:var(--red);color:white;" onclick="doAnularVenta(${vid})">Sí, Anular</button>
    </div>`);
    }

    async function doAnularVenta(vid) {
      try {
        await api(`/ventas/${vid}`, { method: 'DELETE' });
        toast('✅', 'Venta anulada'); closeModal();
      } catch (e) { toast('❌', e.message, 'var(--red)'); }
    }

    /* ── BUNDLE / PAQUETES ── */
    let _bcAllProds = [];

    async function showBundleModal(bid, nombre, precioBundle) {
      let comps;
      try { comps = await api(`/bundle-components/${bid}`); } catch (e) { toast('❌', e.message, 'var(--red)'); return; }

      const sumaAsignada = comps.reduce((s, c) => s + c.cantidad * c.precio_asignado, 0);
      const diff = precioBundle - sumaAsignada;
      const diffColor = Math.abs(diff) < 0.01 ? 'var(--green-ok)' : 'var(--red)';

      const filas = comps.length ? comps.map(c => `
    <div style="display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid var(--border-light);">
      <div style="flex:1;min-width:0;">
        <div style="font-size:13px;font-weight:600;">${c.nombre}</div>
        <div style="font-size:11px;color:var(--text-muted);">${c.tienda_nombre} · x${c.cantidad} · precio asignado: $${c.precio_asignado.toFixed(2)}</div>
      </div>
      <button class="btn-icon btn-del" onclick="removeBundleComp(${c.id},${bid},'${nombre.replace(/'/g, "\\'")}',${precioBundle})" title="Quitar">✕</button>
    </div>`).join('')
        : '<div style="padding:12px 0;color:var(--text-muted);font-size:13px;">Sin componentes aún</div>';

      // Cache de productos no-bundle para filtrado dinámico
      _bcAllProds = (allProductsGlobal || []).filter(p => !p.es_bundle);

      // Tiendas únicas
      const tiendas = [...new Map(_bcAllProds.map(p => [p.tienda_id, p.tienda_nombre])).entries()];
      const tiendaOpts = tiendas.map(([id, nom]) => `<option value="${id}">${nom}</option>`).join('');

      showModal(`<div class="modal-body">
    <div class="modal-title">📦 ${nombre}</div>
    <div class="modal-sub">Precio del paquete: <strong>$${precioBundle.toFixed(2)}</strong> · Asignado a tiendas: <span style="color:${diffColor};font-weight:700;">$${sumaAsignada.toFixed(2)}</span>${Math.abs(diff) > 0.01 ? ` · <span style="color:var(--red);">Diferencia: $${diff.toFixed(2)}</span>` : ' ✓'}</div>
    <div style="max-height:220px;overflow-y:auto;margin-bottom:14px;">${filas}</div>
    <div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:14px;">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:8px;">+ Agregar componente</div>
      <div style="display:flex;gap:8px;margin-bottom:8px;">
        <div class="field" style="margin:0;flex:1;"><label>Tienda</label>
          <select id="bcTienda" class="input" onchange="filterBcTienda()">
            <option value="">— Elige tienda —</option>${tiendaOpts}
          </select>
        </div>
        <div class="field" style="margin:0;flex:2;"><label>Artículo</label>
          <select id="bcProd" class="input" onchange="autoBcPrecio()" disabled>
            <option value="">— Elige tienda primero —</option>
          </select>
        </div>
      </div>
      <div style="display:flex;gap:8px;">
        <div class="field" style="margin:0;flex:1;"><label>Cantidad</label><input type="number" id="bcQty" class="input" value="1" min="1" step="1"></div>
        <div class="field" style="margin:0;flex:1;"><label>Precio asignado ($)</label><input type="number" id="bcPrecio" class="input" step="0.01" placeholder="0.00"></div>
      </div>
      <button class="btn btn-sage" style="width:100%;margin-top:10px;justify-content:center;" onclick="addBundleComp(${bid},'${nombre.replace(/'/g, "\\'")}',${precioBundle})">+ Agregar</button>
    </div>
  </div>
  <div class="modal-footer"><div class="modal-btns" style="margin-top:0">
    <button class="btn btn-ghost" onclick="closeModal()">Cerrar</button>
  </div></div>`);
      const m = document.querySelector('#modals .modal'); if (m) { m.style.width = '560px'; m.style.maxWidth = '98vw'; }
    }

    function filterBcTienda() {
      const tiendaId = parseInt(document.getElementById('bcTienda').value);
      const prodSel = document.getElementById('bcProd');
      document.getElementById('bcPrecio').value = '';
      if (!tiendaId) { prodSel.innerHTML = '<option value="">— Elige tienda primero —</option>'; prodSel.disabled = true; return; }
      const opts = _bcAllProds.filter(p => p.tienda_id === tiendaId)
        .map(p => `<option value="${p.id}" data-precio="${p.precio}">${p.nombre} — $${p.precio.toFixed(2)}</option>`).join('');
      prodSel.innerHTML = `<option value="">— Selecciona artículo —</option>${opts}`;
      prodSel.disabled = false;
    }

    function autoBcPrecio() {
      const sel = document.getElementById('bcProd');
      const opt = sel.options[sel.selectedIndex];
      if (opt && opt.dataset.precio) document.getElementById('bcPrecio').value = parseFloat(opt.dataset.precio).toFixed(2);
    }

    async function addBundleComp(bid, nombre, precioBundle) {
      const cid = parseInt(document.getElementById('bcProd').value);
      const qty = parseInt(document.getElementById('bcQty').value) || 1;
      const precio = parseFloat(document.getElementById('bcPrecio').value);
      if (!cid || !precio || precio <= 0) return toast('⚠️', 'Selecciona producto y precio', 'var(--gold)');
      try {
        await api(`/bundle-components/${bid}`, { method: 'POST', body: { componente_id: cid, cantidad: qty, precio_asignado: precio } });
        showBundleModal(bid, nombre, precioBundle);
      } catch (e) { toast('❌', e.message, 'var(--red)'); }
    }

    async function removeBundleComp(cid, bid, nombre, precioBundle) {
      try {
        await api(`/bundle-components/${cid}`, { method: 'DELETE' });
        showBundleModal(bid, nombre, precioBundle);
      } catch (e) { toast('❌', e.message, 'var(--red)'); }
    }

    /* ── BUSCADOR GLOBAL ── */
    async function showGlobalSearch() {
      let allProds;
      try { allProds = await api('/catalog'); } catch (e) { toast('❌', e.message, 'var(--red)'); return; }
      showModal(`<div class="modal-body">
    <div class="modal-title">🔍 Buscar Producto</div>
    <div class="modal-sub">Busca en todas las tiendas · ${selectedOrden ? 'Agregará a la orden actual' : 'Venta directa'}</div>
    <div class="field"><input type="text" id="gsInput" class="input" placeholder="Escribe el nombre del producto..." autofocus></div>
    <div id="gsResults" style="max-height:380px;overflow-y:auto;"></div>
  </div>
  <div class="modal-footer"><div class="modal-btns" style="margin-top:0"><button class="btn btn-ghost" onclick="closeModal()">Cerrar</button></div></div>`);
      const m = document.querySelector('#modals .modal'); if (m) { m.style.width = '580px'; m.style.maxWidth = '98vw'; }
      const inp = document.getElementById('gsInput');
      const results = document.getElementById('gsResults');
      function render() {
        const q = (inp.value || '').toLowerCase().trim();
        const filt = q ? allProds.filter(p => p.nombre.toLowerCase().includes(q) || (p.tienda_nombre || '').toLowerCase().includes(q)) : allProds.slice(0, 40);
        if (!filt.length) { results.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted)">Sin resultados</div>'; return; }
        results.innerHTML = filt.map(p => `
      <div style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:var(--radius-sm);cursor:pointer;border-bottom:1px solid var(--border-light);"
        onmouseover="this.style.background='var(--bg)'" onmouseout="this.style.background=''"
        onclick="pickGlobal(${p.id},${JSON.stringify(p.nombre).replace(/"/g, '&quot;')},${p.precio},${p.tienda_id},${p.es_precio_abierto ? 1 : 0})">
        <div style="flex:1">
          <div style="font-size:13px;font-weight:600;">${p.nombre}</div>
          <div style="font-size:11px;color:var(--text-muted);">${p.tienda_nombre}${p.stock_local <= 0 ? ' · ⚠ Sin stock' : ''}</div>
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:600;color:var(--sage);">${p.es_precio_abierto ? 'Abierto' : '$' + p.precio.toFixed(2)}</div>
      </div>`).join('');
      }
      inp.addEventListener('input', render);
      render();
      setTimeout(() => inp?.focus(), 80);
    }

    async function pickGlobal(prodId, nombre, precio, tiendaId, esAbierto) {
      if (!usuario) return showNipModal(() => pickGlobal(prodId, nombre, precio, tiendaId, esAbierto));
      const tienda = tiendas.find(t => t.id === tiendaId) || { id: tiendaId, nombre: '', precio_abierto: 0 };
      if (esAbierto) {
        closeModal();
        showModal(`<div class="modal-title">🛍️ ${nombre}</div><div class="modal-sub">Monto variable</div>
      <div class="field"><label>Descripción</label><input type="text" id="gsD" class="input" value="${nombre}"></div>
      <div class="field"><label>Monto</label><input type="number" id="gsM" class="input" placeholder="0.00" step="0.01" onkeydown="if(event.key==='Enter')doPickGsAbierto(${prodId},${tiendaId})"></div>
      <div class="modal-btns"><button class="btn btn-ghost" onclick="closeModal()">Cancelar</button><button class="btn btn-sage" onclick="doPickGsAbierto(${prodId},${tiendaId})">Agregar</button></div>`);
        setTimeout(() => document.getElementById('gsM')?.focus(), 80);
        return;
      }
      closeModal();
      const prod = { id: prodId, nombre, precio, es_precio_abierto: false, stock_local: 99, stock_minimo: 0, categoria_producto: '' };
      await addItemFinal(prod, tienda, nombre, precio, false);
    }

    async function doPickGsAbierto(prodId, tiendaId) {
      const m = parseFloat(document.getElementById('gsM').value); const d = document.getElementById('gsD').value.trim();
      if (!m || m <= 0) return;
      closeModal();
      const tienda = tiendas.find(t => t.id === tiendaId) || { id: tiendaId };
      const prod = { id: prodId, nombre: d, precio: m, es_precio_abierto: true, stock_local: 99, stock_minimo: 0, categoria_producto: '' };
      await addItemFinal(prod, tienda, d, m, true);
    }

    /* ── PRE-CORTE (vista previa sin confirmar) ── */
    async function showPreCorteModal() {
      if (!usuario) return showNipModal(showPreCorteModal);
      let r;
      try { r = await api('/report/corte'); } catch (e) { toast('❌', e.message, 'var(--red)'); return; }
      const desdeStr = r.desde ? r.desde.slice(11, 19) : '00:00:00';
      const _comTar = parseFloat(((r.total_tarjeta || 0) * 0.04).toFixed(2));
      const _tarNeta = parseFloat(((r.total_tarjeta || 0) - _comTar).toFixed(2));
      const _espEf = r.efectivo_esperado || 0;
      const _totalEsp = parseFloat((_espEf + _tarNeta).toFixed(2));
      const tiendaRows = r.ventas_por_tienda.map(t => `
    <div style="display:flex;align-items:center;gap:6px;font-size:12px;padding:5px 0;border-bottom:1px solid var(--border-light);">
      <span style="color:var(--text-secondary);flex:1;">${t.tienda}</span>
      ${t.comision > 0 ? `<span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--red);">-$${t.comision.toFixed(2)}</span>` : ''}
      <span style="font-family:'JetBrains Mono',monospace;font-weight:700;color:var(--sage-dark);">$${(t.neto ?? t.total).toFixed(2)}</span>
    </div>`).join('');
      const gastosRows = r.gastos_detalle.map(g => `
    <div style="display:flex;justify-content:space-between;font-size:12px;padding:3px 0;border-bottom:1px solid var(--border-light);">
      <span style="color:var(--text-muted)">${g.concepto}</span>
      <span style="font-family:'JetBrains Mono',monospace;color:var(--red);">-$${g.monto.toFixed(2)}</span>
    </div>`).join('');
      const ingRows = (r.ingresos_detalle || []).map(i => `
    <div style="display:flex;justify-content:space-between;font-size:12px;padding:3px 0;border-bottom:1px solid var(--border-light);">
      <span style="color:var(--text-muted)">${i.concepto} <span style="opacity:.6">(${i.metodo_pago})</span></span>
      <span style="font-family:'JetBrains Mono',monospace;color:var(--green-ok);">+$${i.monto.toFixed(2)}</span>
    </div>`).join('');
      showModal(`<div class="modal-body">
    <div class="modal-title">👁 Pre-Corte</div>
    <div class="modal-sub">Turno desde ${desdeStr} · ${r.num_ventas} ticket${r.num_ventas !== 1 ? 's' : ''} · Sin confirmar</div>
    <div class="resumen-grid" style="margin-bottom:10px;grid-template-columns:repeat(3,1fr);">
      <div class="res-card"><div class="res-label">💵 Efectivo</div><div class="res-val v">$${(r.total_efectivo || 0).toFixed(2)}</div></div>
      <div class="res-card">
        <div class="res-label">💳 Tarjeta (bruto)</div>
        <div class="res-val" style="color:var(--gold)">$${(r.total_tarjeta || 0).toFixed(2)}</div>
        ${_comTar > 0 ? `<div style="font-size:10px;color:var(--red);margin-top:2px;">− $${_comTar.toFixed(2)} comisión 4%</div>` : ''}
      </div>
      <div class="res-card"><div class="res-label">📦 Gastos</div><div class="res-val g">-$${(r.total_gastos || 0).toFixed(2)}</div></div>
    </div>
    <div class="resumen-grid" style="margin-bottom:14px;grid-template-columns:repeat(3,1fr);">
      <div class="res-card" style="background:var(--green-light);border:1px solid var(--sage);"><div class="res-label" style="color:var(--green-ok)">💵 Ef. en Caja</div><div class="res-val" style="color:var(--green-ok)">$${_espEf.toFixed(2)}</div></div>
      <div class="res-card" style="background:var(--gold-light);border:1px solid var(--gold);"><div class="res-label" style="color:var(--gold)">💳 Tarjeta Neta</div><div class="res-val" style="color:var(--gold)">$${_tarNeta.toFixed(2)}</div></div>
      <div class="res-card" style="background:var(--sage-light);border:1px solid var(--sage);"><div class="res-label" style="color:var(--sage-dark)">TOTAL GENERAL</div><div class="res-val" style="color:var(--sage-dark)">$${_totalEsp.toFixed(2)}</div></div>
    </div>
    ${tiendaRows ? `<div style="margin-bottom:10px"><div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:4px;">Ventas por tienda <span style="font-weight:400;opacity:.7">(neto tras comisión tarjeta)</span></div>${tiendaRows}</div>` : ''}
    ${gastosRows ? `<div style="margin-bottom:10px"><div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:6px;">Gastos del turno</div>${gastosRows}</div>` : ''}
    ${ingRows ? `<div style="margin-bottom:10px"><div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:6px;">Ingresos registrados</div>${ingRows}</div>` : ''}
  </div>
  <div class="modal-footer">
    <div class="modal-btns" style="margin-top:0">
      <button class="btn btn-ghost" onclick="closeModal()">Cerrar</button>
      ${usuario.perfil === 'Administrador' ? `<button class="btn btn-gold" onclick="closeModal();showCorteModal()">📊 Ir a Corte</button>` : ''}
    </div>
  </div>`);
      const m = document.querySelector('#modals .modal'); if (m) { m.style.width = '560px'; m.style.maxWidth = '98vw'; }
    }

    /* ── SVG CHART HELPERS ── */
    let _gc = 0;
    function _glowFilter(blur = 2.5) {
      const id = 'gf' + (++_gc);
      return { id, def: `<defs><filter id="${id}" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur in="SourceGraphic" stdDeviation="${blur}" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>` };
    }
    function _tc() {
      const d = document.documentElement.getAttribute('data-theme') === 'dark';
      return {
        label:  d ? '#9e8cc5' : '#555',
        val:    d ? '#ede7f6' : '#333',
        axis:   d ? '#7e6baa' : '#666',
        valSm:  d ? '#b39ddb' : '#444',
        tick:   d ? '#6b5b8a' : '#888',
        muted:  d ? '#5a4a78' : '#aaa',
        track:  d ? '#2a2040' : '#f0f0f0',
        center: d ? '#1a1628' : 'white',
        zero:   d ? '#3a2d56' : '#ddd',
      };
    }

    function svgDonut(segments, size = 130) {
      const total = segments.reduce((s, x) => s + x.value, 0);
      const tc = _tc();
      if (!total) return `<svg width="${size}" height="${size}"><circle cx="${size / 2}" cy="${size / 2}" r="${size * 0.35}" fill="none" stroke="${tc.track}" stroke-width="${size * 0.18}"/><text x="${size / 2}" y="${size / 2 + 4}" text-anchor="middle" font-size="11" fill="${tc.muted}">Sin datos</text></svg>`;
      const r = size * 0.35, cx = size / 2, cy = size / 2, circ = 2 * Math.PI * r;
      const { id, def } = _glowFilter(3);
      let offset = 0, arcs = '';
      for (const seg of segments) {
        if (!seg.value) continue;
        const dash = (seg.value / total) * circ;
        arcs += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${seg.color}" stroke-width="${size * 0.19}" stroke-dasharray="${dash} ${circ - dash}" stroke-dashoffset="${-offset}" transform="rotate(-90 ${cx} ${cy})" opacity="0.92" filter="url(#${id})"/>`;
        offset += dash;
      }
      return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">${def}<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${tc.track}" stroke-width="${size * 0.19}"/>${arcs}<circle cx="${cx}" cy="${cy}" r="${r * 0.56}" fill="${tc.center}"/></svg>`;
    }

    function svgBarsH(items, barMaxW = 170, barH = 22, gap = 7) {
      if (!items.length) return '';
      const tc = _tc();
      const max = Math.max(...items.map(i => i.value), 1), labelW = 92, valueW = 72;
      const W = labelW + barMaxW + valueW, H = items.length * (barH + gap);
      const { id, def } = _glowFilter(2.5);
      const bars = items.map((item, i) => {
        const y = i * (barH + gap), w = Math.max(3, (item.value / max) * barMaxW);
        const lbl = item.label.length > 13 ? item.label.slice(0, 12) + '…' : item.label;
        const val = '$' + (item.value || 0).toLocaleString('es-MX', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
        return `<text x="${labelW - 5}" y="${y + barH * 0.72}" text-anchor="end" font-size="11" fill="${tc.label}">${lbl}</text><rect x="${labelW}" y="${y + 2}" width="${w}" height="${barH - 4}" rx="5" fill="${item.color || '#7C9A7E'}" opacity="0.85" filter="url(#${id})"/><text x="${labelW + w + 5}" y="${y + barH * 0.72}" font-size="11" font-weight="700" fill="${tc.val}">${val}</text>`;
      }).join('');
      return `<svg width="${W}" height="${H}" style="display:block;overflow:visible">${def}${bars}</svg>`;
    }

    function svgBarsV(items, maxH = 90, barW = 32, gap = 8) {
      if (!items.length) return '';
      const tc = _tc();
      const maxVal = Math.max(...items.map(i => i.value), 1);
      const W = items.length * (barW + gap), H = maxH + 28;
      const { id, def } = _glowFilter(2.5);
      const bars = items.map((item, i) => {
        const x = i * (barW + gap), bh = Math.max(2, (item.value / maxVal) * maxH), y = maxH - bh;
        const lbl = item.label.length > 3 ? item.label.slice(0, 3) : item.label;
        const val = item.value > 0 ? '$' + (item.value / 1000).toFixed(1) + 'k' : '';
        return `<rect x="${x}" y="${y}" width="${barW}" height="${bh}" rx="5" fill="${item.color || '#7C9A7E'}" opacity="0.85" filter="url(#${id})"/><text x="${x + barW / 2}" y="${maxH + 13}" text-anchor="middle" font-size="10" fill="${tc.axis}">${lbl}</text>${item.value > 0 ? `<text x="${x + barW / 2}" y="${y - 3}" text-anchor="middle" font-size="9" font-weight="700" fill="${tc.valSm}">${val}</text>` : ''}`;
      }).join('');
      return `<svg width="${W}" height="${H}" style="display:block;overflow:visible">${def}${bars}</svg>`;
    }

    /* ── ESTADÍSTICAS ── */
    async function showEstadisticasModal() {
      if (!usuario) return showNipModal(() => showEstadisticasModal());
      let data, bal;
      try { [data, bal] = await Promise.all([api('/estadisticas'), api('/balance')]); } catch (e) { toast('❌', e.message, 'var(--red)'); return; }
      const _balCaja = bal?.en_caja || 0, _balBanco = bal?.en_banco || 0, _balTotal = bal?.total || 0;

      const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
      const fmtMes = m => { const [y, mn] = m.split('-'); return MESES[+mn - 1] + "'" + y.slice(2); };

      // Grouped bar chart (2 series)
      function svgGrouped(items, s1, s2, maxH = 110, bW = 12, gap = 10) {
        if (!items.length) return '';
        const tc = _tc();
        const maxV = Math.max(...items.flatMap(it => [it[s1.k] || 0, it[s2.k] || 0]), 1);
        const gW = bW * 2 + 3 + gap, W = items.length * gW, H = maxH + 28;
        const { id, def } = _glowFilter(2.5);
        const bars = items.map((it, i) => {
          const gx = i * gW;
          const h1 = Math.max(2, (it[s1.k] || 0) / maxV * maxH), h2 = Math.max(2, (it[s2.k] || 0) / maxV * maxH);
          return `<rect x="${gx}" y="${maxH - h1}" width="${bW}" height="${h1}" rx="3" fill="${s1.c}" opacity="0.85" filter="url(#${id})"/>
              <rect x="${gx + bW + 3}" y="${maxH - h2}" width="${bW}" height="${h2}" rx="3" fill="${s2.c}" opacity="0.85" filter="url(#${id})"/>
              <text x="${gx + bW}" y="${maxH + 13}" text-anchor="middle" font-size="8" fill="${tc.tick}">${it.label}</text>`;
        }).join('');
        return `<svg width="${W}" height="${H}" style="display:block;overflow:visible">${def}${bars}</svg>`;
      }

      // Line/area chart (single or multi series) — escala adaptativa por día
      function svgLineArea(items, series, maxH = 110) {
        if (!items.length) return `<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px;">Sin datos aún</div>`;
        const tc = _tc();
        // Escala: ancho por punto decrece conforme hay más días (mín 7px, máx 28px)
        const ptW = Math.max(7, Math.min(28, Math.floor(560 / items.length)));
        const W = items.length === 1 ? 200 : items.length * ptW + 20;
        const H = maxH + 28;
        const allV = items.flatMap(it => series.map(s => it[s.k] || 0));
        const maxV = Math.max(...allV, 1), minV = Math.min(...allV, 0);
        const range = maxV - minV || 1;
        const xStep = items.length === 1 ? 0 : (W - 20) / (items.length - 1);
        const { id, def } = _glowFilter(2);
        const labelEvery = Math.ceil(items.length / 8);
        const paths = series.map(s => {
          const pts = items.map((it, i) => [10 + i * xStep, maxH - ((it[s.k] - minV) / range) * maxH]);
          if (pts.length === 1) {
            const [px, py] = pts[0];
            return `<circle cx="${px}" cy="${py}" r="5" fill="${s.c}" filter="url(#${id})"/>
              <text x="${px}" y="${py - 10}" text-anchor="middle" font-size="9" fill="${s.c}" font-weight="700">$${((items[0][s.k] || 0) / 1000).toFixed(1)}k</text>`;
          }
          const d = pts.map((p, i) => (i === 0 ? 'M' : 'L') + p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' ');
          const area = `M${pts[0][0]},${maxH} ` + pts.map(p => `L${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ') + ` L${pts[pts.length-1][0]},${maxH} Z`;
          const dots = pts.map((p, i) => {
            const showDot = ptW >= 10;
            const showLbl = i % labelEvery === 0;
            return `${showDot ? `<circle cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="2.5" fill="${s.c}" filter="url(#${id})"/>` : ''}
              ${showLbl ? `<text x="${p[0].toFixed(1)}" y="${(p[1]-7).toFixed(1)}" text-anchor="middle" font-size="7" fill="${s.c}" font-weight="700">$${((items[i][s.k]||0)/1000).toFixed(0)}k</text>` : ''}`;
          }).join('');
          return `<path d="${area}" fill="${s.c}" opacity="0.12"/>
              <path d="${d}" fill="none" stroke="${s.c}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" filter="url(#${id})"/>
              ${dots}`;
        }).join('');
        const zy = minV < 0 ? maxH - (0 - minV) / range * maxH : null;
        const zeroline = zy !== null ? `<line x1="10" y1="${zy.toFixed(1)}" x2="${W-10}" y2="${zy.toFixed(1)}" stroke="${tc.zero}" stroke-width="1" stroke-dasharray="4,3"/>` : '';
        const xlabels = items.map((it, i) => i % labelEvery === 0 ? `<text x="${(10+i*xStep).toFixed(1)}" y="${H-4}" text-anchor="middle" font-size="7" fill="${tc.muted}">${it.label}</text>` : '').join('');
        return `<svg width="${W}" height="${H}" style="display:block;overflow:visible;min-width:${W}px">${def}${zeroline}${paths}${xlabels}</svg>`;
      }

      function renderContent(tab) {
        const rows = tab === 'mes' ? data.por_mes : data.por_año;
        const lk = tab === 'mes' ? 'mes' : 'año';
        const fmt = l => tab === 'mes' ? fmtMes(l) : l;
        if (!rows.length) return '<div style="padding:40px;text-align:center;color:var(--text-muted);">Sin datos registrados</div>';

        const items = rows.map(r => ({ ...r, label: fmt(r[lk]), balance: r.ventas + r.ingresos - r.gastos - (r.pagos || 0) }));
        let acc = 0; const accItems = items.map(r => ({ ...r, acumulado: (acc += r.balance) }));

        // Datos diarios del año en curso para gráficas de línea
        const diasItems = (data.por_dia || []);
        let efAcc2 = 0, tarAcc2 = 0;
        const diasBalAcc = diasItems.map(r => ({ label: r.label, caja: (efAcc2 += r.efectivo || 0), banco: (tarAcc2 += r.tarjeta || 0) }));

        const totV = rows.reduce((s, r) => s + r.ventas, 0), totG = rows.reduce((s, r) => s + r.gastos, 0),
          totI = rows.reduce((s, r) => s + r.ingresos, 0), totP = rows.reduce((s, r) => s + (r.pagos || 0), 0);
        const fmt$ = v => '$' + v.toLocaleString('es-MX', { minimumFractionDigits: 0 });

        const kpis = `<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px;">
      <div style="background:var(--green-light);border-radius:var(--radius-sm);padding:9px 12px;text-align:center;border:1px solid var(--border-light);">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--green-ok);margin-bottom:2px;">Ventas</div>
        <div style="font-size:16px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--green-ok);">${fmt$(totV)}</div>
      </div>
      <div style="background:var(--blue-light);border-radius:var(--radius-sm);padding:9px 12px;text-align:center;border:1px solid var(--border-light);">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--blue);margin-bottom:2px;">Ingresos</div>
        <div style="font-size:16px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--blue);">${fmt$(totI)}</div>
      </div>
      <div style="background:var(--red-light);border-radius:var(--radius-sm);padding:9px 12px;text-align:center;border:1px solid var(--border-light);">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--red);margin-bottom:2px;">Gastos</div>
        <div style="font-size:16px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--red);">${fmt$(totG)}</div>
      </div>
      <div style="background:var(--terracotta-light,#FFF3E0);border-radius:var(--radius-sm);padding:9px 12px;text-align:center;border:1px solid var(--border-light);">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--terracotta,#E65100);margin-bottom:2px;">Pagos Tiendas</div>
        <div style="font-size:16px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--terracotta,#E65100);">${fmt$(totP)}</div>
      </div>
    </div>`;

        const bW = tab === 'mes' ? 20 : 36, gp = tab === 'mes' ? 6 : 16;
        const chart1 = `<div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:10px;margin-bottom:7px;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:6px;">📊 Ventas por ${tab}</div>
      <div style="overflow-x:auto;">${svgBarsV(items.map(r => ({ label: r.label, value: r.ventas, color: '#7C9A7E' })), 90, bW, gp)}</div>
    </div>`;

        const chart2 = `<div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:10px;margin-bottom:7px;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:4px;">📉 Ventas vs Gastos (barras)</div>
      <div style="display:flex;gap:12px;margin-bottom:6px;font-size:10px;">
        <span style="display:flex;align-items:center;gap:4px;"><span style="width:8px;height:8px;border-radius:2px;background:#7C9A7E;display:inline-block;"></span>Ventas</span>
        <span style="display:flex;align-items:center;gap:4px;"><span style="width:8px;height:8px;border-radius:2px;background:#EF9A9A;display:inline-block;"></span>Gastos</span>
      </div>
      <div style="overflow-x:auto;">${svgGrouped(items, { k: 'ventas', c: '#7C9A7E' }, { k: 'gastos', c: '#EF9A9A' }, 90, tab === 'mes' ? 13 : 28, tab === 'mes' ? 7 : 16)}</div>
    </div>`;

        // Gráfica ventas por tienda
        const TCOLORS = ['#7C9A7E', '#C4755A', '#C9A84C', '#26A69A', '#5C6BC0', '#EC407A', '#8D6E63', '#546E7A'];
        const tiendas = data.tiendas || [];
        const tiendaSeries = tiendas.map((t, i) => ({ k: t, c: TCOLORS[i % TCOLORS.length] }));
        const tiendaItems = items.map(r => {
          const obj = { label: r.label };
          tiendas.forEach(t => { obj[t] = r.por_tienda?.[t] || 0; });
          return obj;
        });

        // Multi-bar chart for N tiendas
        function svgMultiN(its, series, maxH = 120) {
          if (!its.length || !series.length) return '';
          const bW = 10, pad = 2, gp = 8;
          const gW = series.length * (bW + pad) + gp;
          const W = its.length * gW, H = maxH + 28;
          const maxV = Math.max(...its.flatMap(it => series.map(s => it[s.k] || 0)), 1);
          const { id, def } = _glowFilter(2.5);
          const bars = its.map((it, gi) => {
            const gx = gi * gW;
            const bs = series.map((s, si) => {
              const v = it[s.k] || 0, h = Math.max(2, v / maxV * maxH), y = maxH - h;
              return `<rect x="${gx + si * (bW + pad)}" y="${y}" width="${bW}" height="${h}" rx="2" fill="${s.c}" opacity="0.85" filter="url(#${id})"/>`;
            }).join('');
            return bs + `<text x="${gx + series.length * (bW + pad) / 2}" y="${maxH + 13}" text-anchor="middle" font-size="8" fill="${_tc().tick}">${it.label}</text>`;
          }).join('');
          return `<svg width="${W}" height="${H}" style="display:block;overflow:visible">${def}${bars}</svg>`;
        }

        const chart5 = `<div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:10px;margin-bottom:7px;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:4px;">💵 Efectivo vs 💳 Tarjeta (diario)</div>
      <div style="display:flex;gap:12px;margin-bottom:6px;font-size:10px;">
        <span style="display:flex;align-items:center;gap:4px;"><span style="width:8px;height:8px;border-radius:2px;background:#4CAF50;display:inline-block;"></span>Efectivo</span>
        <span style="display:flex;align-items:center;gap:4px;"><span style="width:8px;height:8px;border-radius:2px;background:#C9A84C;display:inline-block;"></span>Tarjeta</span>
      </div>
      <div style="overflow-x:auto;">${svgLineArea(diasItems, [{ k: 'efectivo', c: '#4CAF50' }, { k: 'tarjeta', c: '#C9A84C' }], 90)}</div>
    </div>`;

        const chart3 = tiendas.length ? `<div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:10px;margin-bottom:7px;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:4px;">🏪 Ventas por tienda</div>
      <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:6px;font-size:10px;">
        ${tiendaSeries.map(s => `<span style="display:flex;align-items:center;gap:4px;"><span style="width:8px;height:8px;border-radius:2px;background:${s.c};display:inline-block;"></span>${s.k}</span>`).join('')}
      </div>
      <div style="overflow-x:auto;">${svgMultiN(tiendaItems, tiendaSeries, 90)}</div>
    </div>` : '';

        const chart4 = `<div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:10px;margin-bottom:7px;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:6px;">🍩 Distribución total</div>
      <div style="display:flex;align-items:center;gap:16px;justify-content:center;">
        ${svgDonut([{ label: 'Ventas', value: totV, color: '#7C9A7E' }, { label: 'Ingresos', value: totI, color: '#64B5F6' }, { label: 'Gastos', value: totG, color: '#EF9A9A' }, { label: 'Pagos', value: totP, color: '#E65100' }].filter(s => s.value > 0), 90)}
        <div style="display:flex;flex-direction:column;gap:6px;">
          ${[{ label: 'Ventas', v: totV, c: '#7C9A7E' }, { label: 'Ingresos', v: totI, c: '#64B5F6' }, { label: 'Gastos', v: totG, c: '#EF9A9A' }, { label: 'Pagos', v: totP, c: '#E65100' }].map(s => `<div style="display:flex;align-items:center;gap:5px;font-size:11px;"><span style="width:9px;height:9px;border-radius:2px;background:${s.c};display:inline-block;"></span>${s.label}: <strong>${fmt$(s.v)}</strong></div>`).join('')}
        </div>
      </div>
    </div>`;

        const chart6 = `<div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:10px;margin-bottom:7px;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:4px;">📈 Ventas vs Gastos (diario)</div>
      <div style="display:flex;gap:12px;margin-bottom:6px;font-size:10px;">
        <span style="display:flex;align-items:center;gap:4px;"><span style="width:8px;height:8px;border-radius:2px;background:#7C9A7E;display:inline-block;"></span>Ventas</span>
        <span style="display:flex;align-items:center;gap:4px;"><span style="width:8px;height:8px;border-radius:2px;background:#EF9A9A;display:inline-block;"></span>Gastos</span>
      </div>
      <div style="overflow-x:auto;">${svgLineArea(diasItems, [{ k: 'ventas', c: '#7C9A7E' }, { k: 'gastos', c: '#EF9A9A' }], 90)}</div>
    </div>`;

        // Balance acumulado diario caja vs banco
        const chart7 = `<div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:10px;margin-bottom:7px;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:4px;">💰 Balance Acumulado · Caja vs Banco</div>
      <div style="display:flex;gap:12px;margin-bottom:6px;font-size:10px;">
        <span style="display:flex;align-items:center;gap:4px;"><span style="width:8px;height:8px;border-radius:2px;background:#4CAF50;display:inline-block;"></span>Caja</span>
        <span style="display:flex;align-items:center;gap:4px;"><span style="width:8px;height:8px;border-radius:2px;background:#90CAF9;display:inline-block;"></span>Banco</span>
      </div>
      <div style="overflow-x:auto;">${svgLineArea(diasBalAcc, [{ k: 'caja', c: '#4CAF50' }, { k: 'banco', c: '#90CAF9' }], 100)}</div>
    </div>`;

        const table = `<div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:6px;">Detalle</div>
    <div style="overflow-x:auto;border-radius:var(--radius-sm);border:1px solid var(--border);">
      <table style="width:100%;border-collapse:collapse;font-size:12px;">
        <thead><tr style="background:var(--bg-warm);font-size:10px;text-transform:uppercase;color:var(--text-secondary);">
          <th style="padding:7px 10px;text-align:left;">${tab === 'mes' ? 'Mes' : 'Año'}</th>
          <th style="padding:7px 10px;text-align:right;">Ventas</th>
          <th style="padding:7px 10px;text-align:right;"># Tickets</th>
          <th style="padding:7px 10px;text-align:right;">Ingresos</th>
          <th style="padding:7px 10px;text-align:right;color:var(--red);">Gastos</th>
          <th style="padding:7px 10px;text-align:right;color:var(--terracotta,#E65100);">Pagos</th>
          <th style="padding:7px 10px;text-align:right;">Balance</th>
        </tr></thead>
        <tbody>${rows.map((r, i) => {
          const b = r.ventas + r.ingresos - r.gastos - (r.pagos || 0);
          return `<tr style="border-top:1px solid var(--border-light);${i % 2 === 1 ? 'background:var(--bg-warm);' : ''}">
            <td style="padding:7px 10px;font-weight:600;">${fmt(r[lk])}</td>
            <td style="padding:7px 10px;text-align:right;font-family:'JetBrains Mono',monospace;">${fmt$(r.ventas)}</td>
            <td style="padding:7px 10px;text-align:right;color:var(--text-secondary);">${r.num_ventas}</td>
            <td style="padding:7px 10px;text-align:right;font-family:'JetBrains Mono',monospace;color:#2E7D32;">${fmt$(r.ingresos)}</td>
            <td style="padding:7px 10px;text-align:right;font-family:'JetBrains Mono',monospace;color:var(--red);">${fmt$(r.gastos)}</td>
            <td style="padding:7px 10px;text-align:right;font-family:'JetBrains Mono',monospace;color:var(--terracotta,#E65100);">${fmt$(r.pagos || 0)}</td>
            <td style="padding:7px 10px;text-align:right;font-family:'JetBrains Mono',monospace;font-weight:800;color:${b >= 0 ? 'var(--sage-dark)' : 'var(--red)'}">${fmt$(b)}</td>
          </tr>`;
        }).join('')}</tbody>
      </table>
    </div>`;

        return kpis + chart7 + chart5 + chart6 + chart1 + chart2 + chart3 + chart4 + table;
      }

      const balanceHtml = `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px;">
      <div style="background:var(--surface);border:2px solid var(--sage);border-radius:var(--radius-sm);padding:14px;display:flex;flex-direction:column;gap:6px;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);">📊 Balance Actual</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:800;color:${_balTotal >= 0 ? 'var(--sage-dark)' : 'var(--red)'};">${$pesos(_balTotal)}</div>
        <button style="align-self:flex-start;font-size:11px;padding:3px 10px;border-radius:6px;border:1px solid var(--border);background:var(--bg);color:var(--text-secondary);cursor:pointer;" onclick="showAjusteBalanceModal(${_balCaja},${_balBanco})">✏️ Ajustar</button>
      </div>
      <div style="background:var(--green-light);border:2px solid var(--sage);border-radius:var(--radius-sm);padding:14px;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--green-ok);margin-bottom:6px;">💵 Efectivo en Caja</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:800;color:${_balCaja >= 0 ? 'var(--green-ok)' : 'var(--red)'};">${$pesos(_balCaja)}</div>
      </div>
      <div style="background:var(--gold-light);border:2px solid var(--gold);border-radius:var(--radius-sm);padding:14px;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--gold);margin-bottom:6px;">🏦 Tarjeta / Banco</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:800;color:var(--gold);">${$pesos(_balBanco)}</div>
      </div>
    </div>`;

      // ── Helpers de periodo ──
      const _fmtISO = d => d.toISOString().slice(0, 10);
      const _hoyISO = () => _fmtISO(new Date());
      function _periodoPreset(preset, year, month) {
        const hoy = new Date(); hoy.setHours(12, 0, 0, 0);
        if (preset === '7d') {
          const d = new Date(hoy); d.setDate(hoy.getDate() - 6);
          return { desde: _fmtISO(d), hasta: _fmtISO(hoy) };
        }
        if (preset === '30d') {
          const d = new Date(hoy); d.setDate(hoy.getDate() - 29);
          return { desde: _fmtISO(d), hasta: _fmtISO(hoy) };
        }
        if (preset === 'mes') {
          const y = year || hoy.getFullYear(), m = month || (hoy.getMonth() + 1);
          const desde = `${y}-${String(m).padStart(2, '0')}-01`;
          const hasta = _fmtISO(new Date(y, m, 0));
          return { desde, hasta };
        }
        return null;
      }
      function _presetBtn(active, label, onclick) {
        const on = active
          ? 'background:var(--sage-dark);color:#fff;border:none;'
          : 'background:var(--surface);color:var(--text-secondary);border:1px solid var(--border);';
        return `<button onclick="${onclick}" style="padding:4px 12px;border-radius:16px;cursor:pointer;font-size:11px;font-weight:600;${on}">${label}</button>`;
      }
      function _periodoFiltroHtml(idPrefix, preset, desde, hasta, onPreset, onApply, includeAll) {
        return `<div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:12px;margin-bottom:14px;">
          <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:8px;">Periodo de ventas</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;">
            ${_presetBtn(preset === 'mes', 'Este mes', onPreset + "('mes')")}
            ${_presetBtn(preset === '7d', 'Últimos 7 días', onPreset + "('7d')")}
            ${_presetBtn(preset === '30d', 'Últimos 30 días', onPreset + "('30d')")}
            ${_presetBtn(preset === 'custom', 'Personalizado', onPreset + "('custom')")}
            ${includeAll ? _presetBtn(preset === 'all', 'Todo el historial', onPreset + "('all')") : ''}
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:end;">
            <div style="flex:1;min-width:130px;">
              <label style="font-size:10px;color:var(--text-muted);display:block;margin-bottom:3px;">Desde</label>
              <input type="date" id="${idPrefix}Desde" value="${desde || ''}" class="input" style="padding:6px 8px;font-size:12px;">
            </div>
            <div style="flex:1;min-width:130px;">
              <label style="font-size:10px;color:var(--text-muted);display:block;margin-bottom:3px;">Hasta</label>
              <input type="date" id="${idPrefix}Hasta" value="${hasta || ''}" class="input" style="padding:6px 8px;font-size:12px;">
            </div>
            <button class="btn btn-sage btn-sm" onclick="${onApply}" style="white-space:nowrap;">Aplicar</button>
          </div>
        </div>`;
      }

      // ── Estadísticas SOLO Estudio Deco (excluye Estación 304) ──
      let estudioData = null;
      let estudioPreset = 'all';
      let estudioDesde = '';
      let estudioHasta = '';

      async function loadEstudio() {
        let url = '/estadisticas/estudio';
        if (estudioPreset !== 'all' && estudioDesde && estudioHasta) {
          url += `?desde=${estudioDesde}&hasta=${estudioHasta}`;
        }
        estudioData = await api(url);
      }

      function renderEstudio() {
        const d = estudioData;
        if (!d) return '<div style="padding:40px;text-align:center;color:var(--text-muted);">Cargando…</div>';
        const fmt$ = v => '$' + (v || 0).toLocaleString('es-MX', { minimumFractionDigits: 0 });

        function barList(items, labelKey, valueKey, color, subKey) {
          if (!items || !items.length) return '<div style="padding:16px;text-align:center;color:var(--text-muted);font-size:12px;">Sin datos</div>';
          const maxV = Math.max(...items.map(it => it[valueKey] || 0), 1);
          return items.map((it, i) => {
            const pct = Math.max(3, (it[valueKey] || 0) / maxV * 100);
            const sub = subKey != null ? `<span style="color:var(--text-muted);font-weight:500;">${it[subKey]} u.</span>` : '';
            return `<div style="margin-bottom:8px;">
              <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;">
                <span style="font-weight:600;color:var(--text);">${i + 1}. ${it[labelKey]}</span>
                <span style="display:flex;gap:8px;align-items:center;"><span style="font-family:'JetBrains Mono',monospace;font-weight:700;color:${color};">${fmt$(it[valueKey])}</span>${sub}</span>
              </div>
              <div style="height:8px;background:var(--bg-warm);border-radius:5px;overflow:hidden;"><div style="height:100%;width:${pct}%;background:${color};border-radius:5px;"></div></div>
            </div>`;
          }).join('');
        }

        const periodoLabel = estudioPreset === 'all'
          ? 'Histórico completo'
          : `${estudioDesde || '—'} → ${estudioHasta || '—'}`;

        const filtro = _periodoFiltroHtml(
          'est',
          estudioPreset,
          estudioDesde,
          estudioHasta,
          'window._estudioPreset',
          'window._estudioApply()',
          true
        );

        const r = d.resumen || {};
        const kpis = `<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px;">
          <div style="background:var(--green-light);border-radius:var(--radius-sm);padding:9px 12px;text-align:center;border:1px solid var(--border-light);">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--green-ok);margin-bottom:2px;">Vendido</div>
            <div style="font-size:16px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--green-ok);">${fmt$(r.total)}</div>
          </div>
          <div style="background:var(--blue-light);border-radius:var(--radius-sm);padding:9px 12px;text-align:center;border:1px solid var(--border-light);">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--blue);margin-bottom:2px;">Tickets</div>
            <div style="font-size:16px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--blue);">${r.num_ventas || 0}</div>
          </div>
          <div style="background:var(--rose-light,#F8E4FF);border-radius:var(--radius-sm);padding:9px 12px;text-align:center;border:1px solid var(--border-light);">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--rose,#CE93D8);margin-bottom:2px;">Unidades</div>
            <div style="font-size:16px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--rose,#CE93D8);">${r.unidades || 0}</div>
          </div>
          <div style="background:var(--gold-light);border-radius:var(--radius-sm);padding:9px 12px;text-align:center;border:1px solid var(--border-light);">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--gold);margin-bottom:2px;">Ticket prom.</div>
            <div style="font-size:16px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--gold);">${fmt$(r.ticket_promedio)}</div>
          </div>
        </div>
        <div style="font-size:11px;color:var(--text-muted);margin-bottom:12px;">Periodo: <strong style="color:var(--text-secondary);">${periodoLabel}</strong></div>`;

        const card = (titulo, contenido) => `<div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:12px;margin-bottom:10px;">
          <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:10px;">${titulo}</div>
          ${contenido}
        </div>`;

        const talleres = card('🎨 Talleres que más venden', barList(d.ranking_talleres, 'producto', 'total', '#7E57C2', 'cantidad'));
        const dias = card('📅 Días que más venden', barList(d.ranking_dias_semana, 'dia', 'total', '#26A69A', 'num_ventas'));
        const tiendasCard = card('🏪 Tiendas (excluye Estación 304)', barList(d.ranking_tiendas, 'tienda', 'total', '#5C6BC0', 'cantidad'));
        const productos = card('⭐ Top productos', barList(d.ranking_productos, 'producto', 'total', '#C4755A', 'cantidad'));

        const topDiasRows = (d.top_dias || []).map((t, i) => `<tr style="border-top:1px solid var(--border-light);${i % 2 === 1 ? 'background:var(--bg-warm);' : ''}">
            <td style="padding:6px 10px;font-weight:600;">${i + 1}. ${t.fecha}</td>
            <td style="padding:6px 10px;text-align:right;color:var(--text-secondary);">${t.num_ventas} tickets</td>
            <td style="padding:6px 10px;text-align:right;font-family:'JetBrains Mono',monospace;font-weight:700;color:var(--sage-dark);">${fmt$(t.total)}</td>
          </tr>`).join('');
        const topDias = card('🔥 Mejores fechas', `<div style="overflow-x:auto;border-radius:var(--radius-sm);border:1px solid var(--border);">
          <table style="width:100%;border-collapse:collapse;font-size:12px;">${topDiasRows || '<tr><td style="padding:16px;text-align:center;color:var(--text-muted);">Sin datos</td></tr>'}</table>
        </div>`);

        return filtro + kpis + talleres + dias + tiendasCard + productos + topDias;
      }

      // ── Calendario de ventas ──
      let calYear = new Date().getFullYear();
      let calMonth = new Date().getMonth() + 1;
      let calDays = [];
      let calSelected = null;
      let calVentas = null;
      let calPreset = 'mes';
      let calDesde = _periodoPreset('mes', calYear, calMonth).desde;
      let calHasta = _periodoPreset('mes', calYear, calMonth).hasta;
      let calTienda = '';
      let calPeriodoData = null;
      let calTiendaTab = 0;
      const MESES_CAL = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
      const CAL_TCOLORS = ['#7C9A7E', '#C4755A', '#C9A84C', '#26A69A', '#5C6BC0', '#EC407A', '#8D6E63', '#546E7A'];
      const PAGO_COLORS = { 'Efectivo': '#4CAF50', 'Tarjeta': '#C9A84C', 'Transferencia': '#26A69A', 'Mixto': '#5C6BC0' };

      async function loadCalendario() {
        let url = `/ventas/calendario?anio=${calYear}&mes=${calMonth}`;
        if (calTienda) url += `&tienda=${encodeURIComponent(calTienda)}`;
        calDays = await api(url);
      }

      async function loadCalPeriodo() {
        if (!calDesde || !calHasta) { calPeriodoData = null; return; }
        let url = `/estadisticas/periodo?desde=${calDesde}&hasta=${calHasta}`;
        if (calTienda) url += `&tienda=${encodeURIComponent(calTienda)}`;
        calPeriodoData = await api(url);
        const names = Object.keys(calPeriodoData?.detalle_por_tienda || {});
        if (calTiendaTab >= names.length) calTiendaTab = 0;
      }

      async function selectCalDay(fecha) {
        calSelected = fecha;
        calVentas = await api(`/ventas?fecha=${fecha}`);
        renderModal('calendario');
      }

      function renderCalPeriodoStats() {
        const d = calPeriodoData;
        if (!d) return '<div style="padding:16px;text-align:center;color:var(--text-muted);font-size:12px;">Selecciona un periodo para ver estadísticas</div>';
        const fmt$ = v => '$' + (v || 0).toLocaleString('es-MX', { minimumFractionDigits: 0 });
        const r = d.resumen || {};
        const mejor = r.mejor_dia;

        const kpis = `<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px;">
          <div style="background:var(--green-light);border-radius:var(--radius-sm);padding:9px 12px;text-align:center;border:1px solid var(--border-light);">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--green-ok);margin-bottom:2px;">Total periodo</div>
            <div style="font-size:16px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--green-ok);">${fmt$(r.total)}</div>
          </div>
          <div style="background:var(--blue-light);border-radius:var(--radius-sm);padding:9px 12px;text-align:center;border:1px solid var(--border-light);">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--blue);margin-bottom:2px;">Tickets</div>
            <div style="font-size:16px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--blue);">${r.num_ventas || 0}</div>
          </div>
          <div style="background:var(--gold-light);border-radius:var(--radius-sm);padding:9px 12px;text-align:center;border:1px solid var(--border-light);">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--gold);margin-bottom:2px;">Ticket prom.</div>
            <div style="font-size:16px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--gold);">${fmt$(r.ticket_promedio)}</div>
          </div>
          <div style="background:var(--sage-light);border-radius:var(--radius-sm);padding:9px 12px;text-align:center;border:1px solid var(--border-light);">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--sage-dark);margin-bottom:2px;">Día más fuerte</div>
            <div style="font-size:13px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--sage-dark);">${mejor ? fmt$(mejor.total) : '—'}</div>
            <div style="font-size:9px;color:var(--text-muted);">${mejor ? mejor.fecha : ''}</div>
          </div>
        </div>`;

        const diasItems = (d.ranking_dias_semana || []).map(x => ({
          label: x.label || x.dia.slice(0, 3),
          value: x.total,
          color: '#26A69A',
        }));
        const chartDias = `<div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:12px;">
          <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:8px;">Días más fuertes</div>
          <div style="overflow-x:auto;">${svgBarsV(diasItems, 90, 36, 8)}</div>
        </div>`;

        const diarioItems = (d.diario || []).map(x => ({ label: x.label, total: x.total }));
        const chartDiario = `<div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:12px;">
          <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:8px;">Ventas diarias del periodo</div>
          <div style="overflow-x:auto;">${svgLineArea(diarioItems, [{ k: 'total', c: '#7C9A7E' }], 90)}</div>
        </div>`;

        const tiendaBars = (d.ventas_por_tienda || []).map((t, i) => ({
          label: t.tienda,
          value: t.total,
          color: CAL_TCOLORS[i % CAL_TCOLORS.length],
        }));
        const chartTiendas = `<div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:12px;">
          <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:8px;">Cuánto vendió cada tienda</div>
          <div style="overflow-x:auto;">${tiendaBars.length ? svgBarsH(tiendaBars, 180, 22, 7) : '<div style="color:var(--text-muted);font-size:12px;">Sin ventas</div>'}</div>
        </div>`;

        const pagoSegs = (d.metodos_pago || []).map(p => ({
          label: p.metodo,
          value: p.total,
          color: PAGO_COLORS[p.metodo] || '#8D6E63',
        }));
        const pagoLegend = pagoSegs.map(s => `<div style="display:flex;align-items:center;gap:5px;font-size:11px;"><span style="width:9px;height:9px;border-radius:2px;background:${s.color};display:inline-block;"></span>${s.label}: <strong>${fmt$(s.value)}</strong></div>`).join('');
        const chartPago = `<div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:12px;">
          <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:8px;">Métodos de pago</div>
          <div style="display:flex;align-items:center;gap:14px;justify-content:center;">
            ${svgDonut(pagoSegs, 100)}
            <div style="display:flex;flex-direction:column;gap:5px;">${pagoLegend || '<span style="color:var(--text-muted);font-size:12px;">Sin datos</span>'}</div>
          </div>
        </div>`;

        // Qué vendió cada tienda
        const detalle = d.detalle_por_tienda || {};
        const nombres = Object.keys(detalle);
        let detalleHtml = '';
        if (!nombres.length) {
          detalleHtml = '<div style="padding:16px;text-align:center;color:var(--text-muted);font-size:12px;">Sin productos en este periodo</div>';
        } else {
          const tabs = nombres.map((n, i) => {
            const on = i === calTiendaTab;
            return `<button onclick="window._calTiendaTab(${i})" style="font-size:11px;padding:4px 12px;border-radius:20px;border:1px solid var(--border);background:${on ? 'var(--sage-dark)' : 'var(--surface)'};color:${on ? '#fff' : 'var(--text-secondary)'};cursor:pointer;font-weight:600;">${n}</button>`;
          }).join('');
          const items = detalle[nombres[calTiendaTab]] || [];
          const totalT = items.reduce((s, x) => s + x.total, 0);
          const rows = items.map(p => `<tr style="border-top:1px solid var(--border-light);">
            <td style="padding:5px 8px;font-size:12px;">${p.producto}</td>
            <td style="padding:5px 8px;font-size:12px;text-align:right;color:var(--text-secondary);">${p.cantidad}</td>
            <td style="padding:5px 8px;font-size:12px;text-align:right;font-family:'JetBrains Mono',monospace;font-weight:700;">$${p.total.toFixed(2)}</td>
          </tr>`).join('');
          detalleHtml = `
            <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;">${tabs}</div>
            <div style="overflow-x:auto;border-radius:var(--radius-sm);border:1px solid var(--border);">
              <table style="width:100%;border-collapse:collapse;">
                <thead><tr style="background:var(--bg-warm);font-size:10px;text-transform:uppercase;color:var(--text-secondary);">
                  <th style="padding:6px 8px;text-align:left;">Producto</th>
                  <th style="padding:6px 8px;text-align:right;">Cant.</th>
                  <th style="padding:6px 8px;text-align:right;">Total</th>
                </tr></thead>
                <tbody>${rows}</tbody>
                <tfoot><tr style="background:var(--sage-light);">
                  <td colspan="2" style="padding:6px 8px;font-size:12px;font-weight:700;">TOTAL ${nombres[calTiendaTab]}</td>
                  <td style="padding:6px 8px;font-size:14px;font-weight:800;text-align:right;font-family:'JetBrains Mono',monospace;color:var(--sage-dark);">${fmt$(totalT)}</td>
                </tr></tfoot>
              </table>
            </div>`;
        }

        const topRows = (d.top_dias || []).slice(0, 5).map((t, i) => `<tr style="border-top:1px solid var(--border-light);">
          <td style="padding:5px 8px;font-size:12px;font-weight:600;">${i + 1}. ${t.fecha}</td>
          <td style="padding:5px 8px;font-size:12px;text-align:right;color:var(--text-secondary);">${t.num_ventas} tickets</td>
          <td style="padding:5px 8px;font-size:12px;text-align:right;font-family:'JetBrains Mono',monospace;font-weight:700;color:var(--sage-dark);">${fmt$(t.total)}</td>
        </tr>`).join('');

        return `
          <div style="margin-top:18px;padding-top:16px;border-top:1px solid var(--border);">
            <div style="font-size:12px;font-weight:800;color:var(--text);margin-bottom:4px;">Estadísticas del periodo</div>
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:12px;">${d.desde} → ${d.hasta}${d.tienda ? ' · ' + d.tienda : ' · Todas las tiendas'}</div>
            ${kpis}
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;margin-bottom:10px;">
              ${chartDias}${chartDiario}
            </div>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;margin-bottom:12px;">
              ${chartTiendas}${chartPago}
            </div>
            <div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:12px;margin-bottom:10px;">
              <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:10px;">Qué vendió cada tienda</div>
              ${detalleHtml}
            </div>
            <div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:12px;">
              <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:8px;">Top fechas del periodo</div>
              <div style="overflow-x:auto;border-radius:var(--radius-sm);border:1px solid var(--border);">
                <table style="width:100%;border-collapse:collapse;font-size:12px;">
                  ${topRows || '<tr><td style="padding:14px;text-align:center;color:var(--text-muted);">Sin datos</td></tr>'}
                </table>
              </div>
            </div>
          </div>`;
      }

      function renderCalendario() {
        const byFecha = {};
        calDays.forEach(d => { byFecha[d.fecha] = d; });
        const first = new Date(calYear, calMonth - 1, 1);
        const startDow = (first.getDay() + 6) % 7;
        const daysInMonth = new Date(calYear, calMonth, 0).getDate();
        const cells = [];
        for (let i = 0; i < startDow; i++) cells.push('<div></div>');
        for (let day = 1; day <= daysInMonth; day++) {
          const fecha = `${calYear}-${String(calMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
          const info = byFecha[fecha];
          const selected = calSelected === fecha;
          const has = !!info;
          const inPeriod = calDesde && calHasta && fecha >= calDesde && fecha <= calHasta;
          cells.push(`<button onclick="window._calSelect('${fecha}')" style="padding:8px 4px;border-radius:10px;border:1px solid ${selected ? 'var(--sage)' : inPeriod && has ? 'var(--sage)' : 'var(--border)'};background:${selected ? 'var(--sage-light)' : has ? 'var(--surface)' : 'var(--bg-warm)'};cursor:pointer;text-align:left;min-height:64px;opacity:${inPeriod || !calDesde ? 1 : 0.45};">
            <div style="font-size:12px;font-weight:700;color:var(--text);">${day}</div>
            ${has ? `<div style="font-size:10px;color:var(--sage-dark);font-family:'JetBrains Mono',monospace;margin-top:4px;">$${info.total.toLocaleString('es-MX', { maximumFractionDigits: 0 })}</div>
            <div style="font-size:9px;color:var(--text-muted);">${info.num_ventas} venta${info.num_ventas !== 1 ? 's' : ''}</div>` : '<div style="font-size:9px;color:var(--text-muted);margin-top:6px;">—</div>'}
          </button>`);
        }

        let detalle = '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:13px;">Selecciona un día para ver las ventas</div>';
        if (calSelected && calVentas) {
          let activas = calVentas.filter(v => !v.cancelada);
          if (calTienda) {
            activas = activas.filter(v => (v.items || []).some(it => (it.tienda_nombre || '') === calTienda));
          }
          const total = activas.reduce((s, v) => {
            if (!calTienda) return s + v.total;
            return s + (v.items || []).filter(it => it.tienda_nombre === calTienda).reduce((a, it) => a + (it.subtotal || 0), 0);
          }, 0);
          const ef = activas.filter(v => v.metodo_pago === 'Efectivo').reduce((s, v) => s + v.total, 0);
          const tar = activas.filter(v => v.metodo_pago === 'Tarjeta').reduce((s, v) => s + v.total, 0);
          const trn = activas.filter(v => v.metodo_pago === 'Transferencia').reduce((s, v) => s + v.total, 0);
          const lista = activas.length ? activas.map(v => {
            const hora = (v.created_at || '').slice(11, 16);
            const itemsTxt = (v.items || [])
              .filter(it => !calTienda || it.tienda_nombre === calTienda)
              .map(it => `${it.cantidad}× ${it.nombre_producto}`)
              .join(', ');
            return `<div style="padding:8px 0;border-bottom:1px solid var(--border-light);font-size:12px;">
              <div style="display:flex;justify-content:space-between;gap:8px;">
                <span><strong>${v.folio}</strong> · ${hora} · ${v.metodo_pago}</span>
                <span style="font-family:'JetBrains Mono',monospace;font-weight:700;">$${v.total.toFixed(2)}</span>
              </div>
              ${itemsTxt ? `<div style="font-size:10px;color:var(--text-muted);margin-top:3px;">${itemsTxt}</div>` : ''}
            </div>`;
          }).join('') : '<div style="padding:16px;text-align:center;color:var(--text-muted);">Sin ventas este día</div>';

          detalle = `
            <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap;">
              <div style="font-weight:700;font-size:14px;">${calSelected}</div>
              <div style="display:flex;gap:8px;">
                <a class="btn btn-sage btn-sm" href="/api/report/ventas-dia.pdf?fecha=${calSelected}" target="_blank" style="text-decoration:none;display:inline-flex;align-items:center;gap:5px;">${icon('download', 13)} PDF</a>
                <a class="btn btn-ghost btn-sm" href="/api/report/ventas-dia.csv?fecha=${calSelected}" target="_blank" style="text-decoration:none;display:inline-flex;align-items:center;gap:5px;">${icon('download', 13)} CSV</a>
              </div>
            </div>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px;">
              <div class="res-card"><div class="res-label">Total</div><div class="res-val" style="font-size:14px;color:var(--sage-dark);">$${total.toFixed(2)}</div></div>
              <div class="res-card"><div class="res-label">${icon('cash', 11)} Efectivo</div><div class="res-val v" style="font-size:14px;">$${ef.toFixed(2)}</div></div>
              <div class="res-card"><div class="res-label">${icon('card', 11)} Tarjeta</div><div class="res-val" style="font-size:14px;color:var(--gold);">$${tar.toFixed(2)}</div></div>
              <div class="res-card"><div class="res-label">${icon('transfer', 11)} Transfer.</div><div class="res-val" style="font-size:14px;color:var(--blue);">$${trn.toFixed(2)}</div></div>
            </div>
            <div style="max-height:260px;overflow-y:auto;">${lista}</div>`;
        }

        const tiendaOpts = ['<option value="">Todas las tiendas</option>']
          .concat((calPeriodoData?.tiendas || (window._allTiendas || tiendas || []).map(t => t.nombre)).map(n => {
            const name = typeof n === 'string' ? n : n;
            return `<option value="${name.replace(/"/g, '&quot;')}" ${calTienda === name ? 'selected' : ''}>${name}</option>`;
          }));

        const filtro = `
          ${_periodoFiltroHtml('cal', calPreset, calDesde, calHasta, 'window._calPreset', 'window._calApply()', false)}
          <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:end;margin-bottom:14px;">
            <div style="flex:1;min-width:180px;">
              <label style="font-size:10px;color:var(--text-muted);display:block;margin-bottom:3px;">Filtrar por tienda</label>
              <select id="calTiendaSel" class="input" style="padding:6px 8px;font-size:12px;" onchange="window._calTiendaChange(this.value)">
                ${tiendaOpts.join('')}
              </select>
            </div>
          </div>`;

        return `
          ${filtro}
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
            <button class="btn btn-ghost btn-sm" onclick="window._calNav(-1)">${icon('chevronL', 14)}</button>
            <div style="font-weight:700;font-size:15px;display:flex;align-items:center;gap:8px;">${icon('calendar', 16)} ${MESES_CAL[calMonth - 1]} ${calYear}</div>
            <button class="btn btn-ghost btn-sm" onclick="window._calNav(1)">${icon('chevronR', 14)}</button>
          </div>
          <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:6px;margin-bottom:8px;font-size:10px;font-weight:700;color:var(--text-muted);text-align:center;">
            <div>Lun</div><div>Mar</div><div>Mié</div><div>Jue</div><div>Vie</div><div>Sáb</div><div>Dom</div>
          </div>
          <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:6px;margin-bottom:16px;">${cells.join('')}</div>
          <div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:12px;">${detalle}</div>
          ${renderCalPeriodoStats()}`;
      }

      function renderModal(tab) {
        const bs = t => t === tab ? 'background:var(--sage-dark);color:#fff;border:none;' : 'background:var(--bg-warm);color:var(--text-secondary);border:1px solid var(--border);';
        let contenido = '';
        if (tab === 'estudio') contenido = renderEstudio();
        else if (tab === 'calendario') contenido = renderCalendario();
        else contenido = renderContent(tab);
        const subtitulo = tab === 'estudio' ? 'Solo Estudio Deco · excluye Estación 304 · filtro por periodo'
          : tab === 'calendario' ? 'Ventas por día · filtros · gráficas del periodo'
          : 'Análisis histórico de ventas, ingresos y gastos';
        showModal(`<div class="modal-body">
      <div class="modal-title">📈 Estadísticas</div>
      <div class="modal-sub">${subtitulo}</div>
      ${tab === 'estudio' || tab === 'calendario' ? '' : balanceHtml}
      <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;">
        <button onclick="window._statsTab('mes')" style="padding:5px 16px;border-radius:20px;cursor:pointer;font-size:12px;font-weight:600;${bs('mes')}">Por mes</button>
        <button onclick="window._statsTab('año')" style="padding:5px 16px;border-radius:20px;cursor:pointer;font-size:12px;font-weight:600;${bs('año')}">Por año</button>
        <button onclick="window._statsTab('calendario')" style="padding:5px 16px;border-radius:20px;cursor:pointer;font-size:12px;font-weight:600;${bs('calendario')}">📅 Calendario</button>
        <button onclick="window._statsTab('estudio')" style="padding:5px 16px;border-radius:20px;cursor:pointer;font-size:12px;font-weight:600;${bs('estudio')}">🎨 Estudio Deco</button>
      </div>
      ${contenido}
      <div style="padding-top:12px;margin-top:4px;"><button class="btn btn-ghost" onclick="closeModal()">Cerrar</button></div>
    </div>`);
        const m = document.querySelector('#modals .modal'); if (m) { m.style.width = '960px'; m.style.maxWidth = '99vw'; }
      }

      window._calNav = async (delta) => {
        calMonth += delta;
        if (calMonth < 1) { calMonth = 12; calYear--; }
        if (calMonth > 12) { calMonth = 1; calYear++; }
        calSelected = null; calVentas = null;
        if (calPreset === 'mes') {
          const p = _periodoPreset('mes', calYear, calMonth);
          calDesde = p.desde; calHasta = p.hasta;
        }
        try {
          await Promise.all([loadCalendario(), loadCalPeriodo()]);
          renderModal('calendario');
        } catch (e) { toast('❌', e.message, 'var(--red)'); }
      };
      window._calSelect = async (fecha) => {
        try { await selectCalDay(fecha); }
        catch (e) { toast('❌', e.message, 'var(--red)'); }
      };
      window._calPreset = async (preset) => {
        calPreset = preset;
        if (preset !== 'custom') {
          if (preset === 'mes') {
            const hoy = new Date();
            calYear = hoy.getFullYear();
            calMonth = hoy.getMonth() + 1;
          }
          const p = _periodoPreset(preset, calYear, calMonth);
          calDesde = p.desde; calHasta = p.hasta;
        }
        calSelected = null; calVentas = null; calTiendaTab = 0;
        try {
          await Promise.all([loadCalendario(), loadCalPeriodo()]);
          renderModal('calendario');
        } catch (e) { toast('❌', e.message, 'var(--red)'); }
      };
      window._calApply = async () => {
        const d = document.getElementById('calDesde')?.value;
        const h = document.getElementById('calHasta')?.value;
        if (!d || !h) { toast('⚠️', 'Selecciona desde y hasta', 'var(--gold)'); return; }
        if (d > h) { toast('⚠️', 'La fecha desde no puede ser mayor que hasta', 'var(--gold)'); return; }
        calDesde = d; calHasta = h; calPreset = 'custom';
        calYear = +d.slice(0, 4); calMonth = +d.slice(5, 7);
        calSelected = null; calVentas = null; calTiendaTab = 0;
        try {
          await Promise.all([loadCalendario(), loadCalPeriodo()]);
          renderModal('calendario');
        } catch (e) { toast('❌', e.message, 'var(--red)'); }
      };
      window._calTiendaChange = async (val) => {
        calTienda = val || '';
        calTiendaTab = 0;
        try {
          await Promise.all([loadCalendario(), loadCalPeriodo()]);
          if (calSelected) calVentas = await api(`/ventas?fecha=${calSelected}`);
          renderModal('calendario');
        } catch (e) { toast('❌', e.message, 'var(--red)'); }
      };
      window._calTiendaTab = (idx) => {
        calTiendaTab = idx;
        renderModal('calendario');
      };

      window._estudioPreset = async (preset) => {
        estudioPreset = preset;
        if (preset === 'all') {
          estudioDesde = ''; estudioHasta = '';
        } else if (preset === 'custom') {
          if (!estudioDesde || !estudioHasta) {
            const p = _periodoPreset('mes');
            estudioDesde = p.desde; estudioHasta = p.hasta;
          }
        } else {
          const p = _periodoPreset(preset);
          estudioDesde = p.desde; estudioHasta = p.hasta;
        }
        try {
          await loadEstudio();
          renderModal('estudio');
        } catch (e) { toast('❌', e.message, 'var(--red)'); }
      };
      window._estudioApply = async () => {
        const d = document.getElementById('estDesde')?.value;
        const h = document.getElementById('estHasta')?.value;
        if (!d || !h) { toast('⚠️', 'Selecciona desde y hasta', 'var(--gold)'); return; }
        if (d > h) { toast('⚠️', 'La fecha desde no puede ser mayor que hasta', 'var(--gold)'); return; }
        estudioDesde = d; estudioHasta = h; estudioPreset = 'custom';
        try {
          await loadEstudio();
          renderModal('estudio');
        } catch (e) { toast('❌', e.message, 'var(--red)'); }
      };

      window._statsTab = async (tab) => {
        if (tab === 'estudio') {
          try { await loadEstudio(); }
          catch (e) { toast('❌', e.message, 'var(--red)'); return; }
        }
        if (tab === 'calendario') {
          try { await Promise.all([loadCalendario(), loadCalPeriodo()]); }
          catch (e) { toast('❌', e.message, 'var(--red)'); return; }
        }
        renderModal(tab);
      };
      renderModal('mes');
    }

    /* ── CORTE SEMANAL ── */
    let _semanaOffset = 0;
    async function showCorteSemanalModal(offset) {
      if (offset !== undefined) _semanaOffset = offset;
      if (!usuario) return showNipModal(() => showCorteSemanalModal());
      if (usuario.perfil !== 'Administrador') { toast('⚠️', 'Solo Administrador', 'var(--gold)'); return; }
      if (_fpActive) _fpRendered = false;

      // Calcular rango de la semana (Lunes a Domingo)
      const hoy = new Date(); hoy.setHours(12, 0, 0, 0);
      const lunes = new Date(hoy); lunes.setDate(hoy.getDate() - hoy.getDay() + 1 + _semanaOffset * 7);
      const domingo = new Date(lunes); domingo.setDate(lunes.getDate() + 6);
      const fmt = d => d.toISOString().slice(0, 10);
      const desde = fmt(lunes), hasta = fmt(domingo);
      const fmtLabel = d => d.toLocaleDateString('es-MX', { day: 'numeric', month: 'short' });

      let r;
      try { r = await api(`/report/semanal?desde=${desde}&hasta=${hasta}`); }
      catch (e) { toast('❌', e.message, 'var(--red)'); return; }

      const DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
      const TIENDA_COLORS = ['#7C9A7E', '#C4755A', '#C9A84C', '#26A69A', '#5C6BC0', '#EC407A', '#8D6E63'];

      // Donut métodos de pago
      const segsPago = [
        { label: 'Efectivo', value: r.total_efectivo, color: '#4CAF50' },
        { label: 'Tarjeta', value: r.total_tarjeta, color: '#C9A84C' },
        { label: 'Transfer.', value: r.total_transferencia || 0, color: '#26A69A' },
      ].filter(s => s.value > 0);

      // Barras verticales por día (lunes-domingo)
      const diasMap = {};
      (r.diario || []).forEach(d => { diasMap[d.fecha] = d; });
      const barsDia = [];
      for (let i = 0; i < 7; i++) {
        const d = new Date(lunes); d.setDate(lunes.getDate() + i);
        const key = fmt(d);
        barsDia.push({ label: DIAS_SEMANA[i], value: diasMap[key]?.total || 0, color: d <= hoy ? '#7C9A7E' : '#ddd' });
      }

      // Check which tiendas have already been paid this week
      const pagosHechos = r.pagos_semana || [];
      const tiendaYaPagada = (tid) => pagosHechos.some(p => p.tienda_id === tid);

      // Find tienda IDs from the global tiendas array
      const findTiendaId = (nombre) => {
        const t = (window._allTiendas || tiendas || []).find(x => x.nombre.toLowerCase().includes(nombre.toLowerCase()));
        return t ? t.id : null;
      };

      // Tabla por tienda with PAGAR button
      const tiendaRows = (r.ventas_por_tienda || []).map((t, i) => {
        const tid = findTiendaId(t.tienda);
        const esEstudio = t.tienda.toLowerCase().includes('estudio');
        const esPromo = t.tienda.toLowerCase().includes('promoci');
        const esEstacion = t.tienda.toLowerCase().includes('estaci');
        const esSabro = t.tienda.toLowerCase().includes('sabro');
        const yaPagada = tid && tiendaYaPagada(tid);

        // Sabrodulce: pago = sumatoria de costos de la tabla ventas por tienda
        const sabroDetalle = esSabro ? Object.entries(r.detalle_por_tienda || {}).find(([k]) => k.toLowerCase().includes('sabro')) : null;
        const sabroCostoTotal = sabroDetalle ? sabroDetalle[1].reduce((s, x) => s + x.costo_total, 0) : 0;
        let montoSugerido = esSabro ? (sabroCostoTotal || t.total) : t.neto;

        let pagarBtn = '';
        if (!esEstudio && !esPromo && tid) {
          if (yaPagada) {
            const pagoPrev = pagosHechos.find(p => p.tienda_id === tid);
            pagarBtn = `<span style="font-size:10px;color:var(--green-ok);font-weight:700;">✅ Pagado $${pagoPrev.monto.toFixed(2)}</span>
              <button class="btn-pagar" style="font-size:10px;padding:3px 8px;margin-left:4px;opacity:.7;" onclick="showPagoTiendaModal(${tid},'${t.tienda.replace(/'/g, "\\\'")}',${montoSugerido.toFixed(2)},${esEstacion ? 'true' : 'false'},'${desde}','${hasta}')">+ Pago</button>`;
          } else {
            pagarBtn = `<button class="btn-pagar" onclick="showPagoTiendaModal(${tid},'${t.tienda.replace(/'/g, "\\\'")}',${montoSugerido.toFixed(2)},${esEstacion ? 'true' : 'false'},'${desde}','${hasta}')">💰 PAGAR</button>`;
          }
        }

        return `<tr>
      <td style="padding:7px 10px;font-size:12px;display:flex;align-items:center;gap:6px;">
        <span style="width:10px;height:10px;border-radius:50%;background:${TIENDA_COLORS[i % TIENDA_COLORS.length]};flex-shrink:0;display:inline-block;"></span>
        ${t.tienda}
      </td>
      <td style="padding:7px 10px;font-family:'JetBrains Mono',monospace;font-size:12px;text-align:right;">$${t.total.toFixed(2)}</td>
      <td style="padding:7px 10px;font-family:'JetBrains Mono',monospace;font-size:12px;text-align:right;color:var(--red);">${t.comision > 0 ? '-$' + t.comision.toFixed(2) : '-'}</td>
      <td style="padding:7px 10px;font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:800;text-align:right;color:var(--sage-dark);">$${montoSugerido.toFixed(2)}</td>
      <td style="padding:7px 10px;text-align:center;">${pagarBtn}</td>
    </tr>`;
      }).join('');

      const sabroCard = '';

      const legend = segsPago.map(s => `<div style="display:flex;align-items:center;gap:5px;font-size:11px;"><span style="width:10px;height:10px;border-radius:50%;background:${s.color};display:inline-block;"></span>${s.label}: <strong>$${s.value.toFixed(0)}</strong></div>`).join('');

      // Balance cards for the modal
      const balEstudio = r.balance_estudio_deco || 0;
      const balEstacion = r.balance_estacion_304 || 0;

      showModal(`<div class="modal-body">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
      <button class="btn btn-ghost" style="padding:4px 10px;font-size:18px;line-height:1;" onclick="showCorteSemanalModal(${_semanaOffset - 1})">‹</button>
      <div style="flex:1;text-align:center;">
        <div class="modal-title" style="margin:0;">📅 Corte Semanal</div>
        <div class="modal-sub" style="margin:0;">${fmtLabel(lunes)} – ${fmtLabel(domingo)} · ${r.num_ventas} ticket${r.num_ventas !== 1 ? 's' : ''}${r.num_canceladas ? ' · ' + r.num_canceladas + ' cancelada(s)' : ''}</div>
      </div>
      <button class="btn btn-ghost" style="padding:4px 10px;font-size:18px;line-height:1;" onclick="showCorteSemanalModal(${_semanaOffset + 1})" ${_semanaOffset >= 0 ? 'disabled' : ''}>›</button>
    </div>

    <!-- Tarjetas resumen -->
    <div class="resumen-grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:12px;">
      <div class="res-card"><div class="res-label">Total Semana</div><div class="res-val" style="color:var(--sage-dark);">$${r.total_ventas.toFixed(0)}</div></div>
      <div class="res-card"><div class="res-label">💵 Efectivo</div><div class="res-val v">$${r.total_efectivo.toFixed(0)}</div></div>
      <div class="res-card"><div class="res-label">💳 Tarjeta</div><div class="res-val" style="color:var(--gold);">$${r.total_tarjeta.toFixed(0)}</div></div>
      <div class="res-card"><div class="res-label">📦 Gastos</div><div class="res-val g">-$${r.total_gastos.toFixed(0)}</div></div>
    </div>

    <!-- Balance cards -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px;">
      <div style="background:var(--sage-light);border-radius:var(--radius-sm);padding:14px;border-left:4px solid var(--sage);">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--sage-dark);margin-bottom:4px;">🏠 Balance Estudio Deco</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:800;color:${balEstudio >= 0 ? 'var(--sage-dark)' : 'var(--red)'};">${$pesos(balEstudio)}</div>
      </div>
      <div style="background:var(--terracotta-light);border-radius:var(--radius-sm);padding:14px;border-left:4px solid var(--terracotta);">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--terracotta);margin-bottom:4px;">☕ Balance Estación 304</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:800;color:var(--terracotta);">${$pesos(balEstacion)}</div>
      </div>
    </div>

    <!-- Gráfica semanal -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;align-items:start;">
      <div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:12px;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:8px;">Ventas por día</div>
        <div style="overflow-x:auto;">${svgBarsV(barsDia, 80, 28, 6)}</div>
      </div>
      <div style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:12px;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:6px;">Métodos de pago</div>
        <div style="display:flex;align-items:center;gap:10px;">
          ${svgDonut(segsPago, 90)}
          <div style="display:flex;flex-direction:column;gap:5px;">${legend}</div>
        </div>
      </div>
    </div>

    <!-- Ventas por tienda (artículos) -->
    <div style="margin-bottom:16px;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:8px;">Ventas por tienda</div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;" id="semanal-tienda-tabs">
        ${Object.keys(r.detalle_por_tienda || {}).map((nombre, i) => `
          <button onclick="semanalSelectTienda('${nombre.replace(/'/g, "\\'")}')" id="stab-${i}"
            style="font-size:11px;padding:4px 12px;border-radius:20px;border:1px solid var(--border);background:${i === 0 ? 'var(--sage-dark)' : 'var(--bg-warm)'};color:${i === 0 ? '#fff' : 'var(--text-secondary)'};cursor:pointer;font-weight:600;">
            ${nombre}
          </button>`).join('')}
      </div>
      <div id="semanal-tienda-detalle" style="background:var(--bg-warm);border-radius:var(--radius-sm);padding:10px 14px;">
        ${(() => {
          const tiendas = Object.keys(r.detalle_por_tienda || {});
          if (!tiendas.length) return '<div style="color:var(--text-muted);font-size:12px;">Sin datos</div>';
          return tiendas.map((nombre, i) => {
            const items = r.detalle_por_tienda[nombre];
            const totalTienda = items.reduce((s, x) => s + x.total, 0);
            const costoTienda = items.reduce((s, x) => s + x.costo_total, 0);
            return `<div id="stienda-${i}" style="display:${i === 0 ? 'block' : 'none'}">
              <table style="width:100%;border-collapse:collapse;">
                <thead><tr style="font-size:10px;text-transform:uppercase;color:var(--text-secondary);">
                  <th style="padding:4px 8px;text-align:left;font-weight:700;">Producto</th>
                  <th style="padding:4px 8px;text-align:right;font-weight:700;">Cant.</th>
                  <th style="padding:4px 8px;text-align:right;font-weight:700;">Costo</th>
                  <th style="padding:4px 8px;text-align:right;font-weight:700;">Total</th>
                </tr></thead>
                <tbody>
                  ${items.map(p => `<tr style="border-top:1px solid var(--border-light);">
                    <td style="padding:5px 8px;font-size:12px;">${p.producto}</td>
                    <td style="padding:5px 8px;font-size:12px;text-align:right;color:var(--text-secondary);">${p.cantidad}</td>
                    <td style="padding:5px 8px;font-size:12px;text-align:right;font-family:'JetBrains Mono',monospace;color:var(--text-secondary);">$${p.costo_total.toFixed(2)}</td>
                    <td style="padding:5px 8px;font-size:12px;text-align:right;font-family:'JetBrains Mono',monospace;font-weight:700;">$${p.total.toFixed(2)}</td>
                  </tr>`).join('')}
                </tbody>
                <tfoot><tr style="background:var(--sage-light);">
                  <td colspan="2" style="padding:6px 8px;font-size:12px;font-weight:700;">TOTAL SEMANA</td>
                  <td style="padding:6px 8px;font-size:12px;font-weight:700;text-align:right;font-family:'JetBrains Mono',monospace;color:var(--text-secondary);">$${costoTienda.toFixed(2)}</td>
                  <td style="padding:6px 8px;font-size:14px;font-weight:800;text-align:right;font-family:'JetBrains Mono',monospace;color:var(--sage-dark);">$${totalTienda.toFixed(2)}</td>
                </tr></tfoot>
              </table>
            </div>`;
          }).join('');
        })()}
      </div>
    </div>

    <!-- Tabla por tienda -->
    <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--text-secondary);margin-bottom:6px;">Pago por tienda (neto tras comisión)</div>
    <div style="overflow-x:auto;border-radius:var(--radius-sm);border:1px solid var(--border);margin-bottom:2px;">
      <table style="width:100%;border-collapse:collapse;">
        <thead><tr style="background:var(--bg-warm);font-size:10px;text-transform:uppercase;color:var(--text-secondary);">
          <th style="padding:6px 10px;text-align:left;font-weight:700;">Tienda</th>
          <th style="padding:6px 10px;text-align:right;font-weight:700;">Bruto</th>
          <th style="padding:6px 10px;text-align:right;font-weight:700;">Comisión</th>
          <th style="padding:6px 10px;text-align:right;font-weight:700;">A PAGAR</th>
          <th style="padding:6px 10px;text-align:center;font-weight:700;">Acción</th>
        </tr></thead>
        <tbody>${tiendaRows || '<tr><td colspan="5" style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px;">Sin ventas en este período</td></tr>'}</tbody>
        ${r.ventas_por_tienda?.length ? `<tfoot><tr style="background:var(--sage-light);">
          <td style="padding:7px 10px;font-size:12px;font-weight:700;">TOTAL</td>
          <td style="padding:7px 10px;font-family:'JetBrains Mono',monospace;font-size:12px;text-align:right;font-weight:700;">$${r.total_ventas.toFixed(2)}</td>
          <td style="padding:7px 10px;font-family:'JetBrains Mono',monospace;font-size:12px;text-align:right;color:var(--red);font-weight:700;">-$${(r.ventas_por_tienda.reduce((s, t) => s + t.comision, 0)).toFixed(2)}</td>
          <td style="padding:7px 10px;font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:800;text-align:right;color:var(--sage-dark);">$${(r.ventas_por_tienda.reduce((s, t) => s + t.neto, 0)).toFixed(2)}</td>
          <td></td>
        </tr></tfoot>`: ''}
      </table>
    </div>
    ${sabroCard}
  </div>
  <div class="modal-footer"><div class="modal-btns" style="margin-top:0">
    <button class="btn btn-ghost" onclick="closeModal()">Cerrar</button>
  </div></div>`);
      const m = document.querySelector('#modals .modal'); if (m) { m.style.width = '800px'; m.style.maxWidth = '98vw'; }
    }

    /* ── SELECTOR TIENDA SEMANAL ── */
    function semanalSelectTienda(nombre) {
      const tabs = document.querySelectorAll('#semanal-tienda-tabs button');
      const panels = document.querySelectorAll('[id^="stienda-"]');
      const tiendas = Array.from(tabs).map(b => b.textContent.trim());
      const idx = tiendas.indexOf(nombre);
      tabs.forEach((b, i) => {
        b.style.background = i === idx ? 'var(--sage-dark)' : 'var(--bg-warm)';
        b.style.color = i === idx ? '#fff' : 'var(--text-secondary)';
      });
      panels.forEach((p, i) => { p.style.display = i === idx ? 'block' : 'none'; });
    }

    /* ── PAGO A TIENDA ── */
    function showPagoTiendaModal(tiendaId, tiendaNombre, montoSugerido, esInterno, desde, hasta) {
      showModal(`<div class="modal-simple">
    <div class="modal-title">💰 Pagar a ${tiendaNombre}</div>
    <div class="modal-sub">Registrar pago semanal</div>
    <div class="field"><label>Monto a pagar</label>
      <input type="number" id="ptMonto" class="input" value="${montoSugerido.toFixed(2)}" step="0.01" min="0" style="font-size:20px;font-weight:700;font-family:'JetBrains Mono',monospace;text-align:center;">
    </div>
    <div class="field"><label>Método de pago</label>
      <select id="ptMetodo" class="input">
        <option value="Efectivo">💵 Efectivo (Caja Fuerte)</option>
        <option value="Tarjeta">💳 Tarjeta / Transferencia (Banco)</option>
      </select>
    </div>
    <div class="modal-btns">
      <button class="btn btn-ghost" onclick="closeModal(); showCorteSemanalModal()">← Volver</button>
      <button class="btn" style="background:linear-gradient(135deg,#4CAF50,#2E7D32);color:white;" onclick="doPagoTienda(${tiendaId},'${tiendaNombre.replace(/'/g, "\\'")}',${esInterno ? 'true' : 'false'},'${desde}','${hasta}')">✓ Confirmar Pago</button>
    </div>
  </div>`);
      setTimeout(() => document.getElementById('ptMonto')?.select(), 100);
    }

    async function doPagoTienda(tiendaId, tiendaNombre, esInterno, desde, hasta) {
      const monto = parseFloat(document.getElementById('ptMonto').value);
      const metodo = document.getElementById('ptMetodo').value;
      if (!monto || monto <= 0) { toast('⚠️', 'Ingresa un monto válido', 'var(--gold)'); return; }
      // Deshabilitar botón para evitar doble pago
      const btn = document.querySelector('#modals .btn[onclick*="doPagoTienda"]');
      if (btn) { btn.disabled = true; btn.textContent = 'Procesando...'; }
      try {
        await api('/pagos-tienda', {
          method: 'POST', body: {
            usuario_id: usuario.id,
            tienda_id: tiendaId,
            tienda_nombre: tiendaNombre,
            monto: monto,
            metodo_pago: metodo,
            concepto: `Pago semanal ${desde} a ${hasta}`,
            es_interno: esInterno,
            semana_inicio: desde,
            semana_fin: hasta
          }
        });
        // Cerrar modal y refrescar
        document.getElementById('modals').innerHTML = '';
        toast('✅', `Pago de $${monto.toFixed(2)} a ${tiendaNombre} registrado`, 'var(--green-ok)');
        showCorteSemanalModal();
      } catch (e) {
        if (btn) { btn.disabled = false; btn.textContent = '✓ Confirmar Pago'; }
        toast('❌', e.message, 'var(--red)');
      }
    }


    init();

    /* ── NÓMINAS ── */
    async function showNominasPage() {
      if (!usuario) return showNipModal(() => openPage('👥 Nóminas', showNominasPage));
      let nominas = [];
      try { const _r = await api('/nominas'); nominas = Array.isArray(_r) ? _r : (_r.items ?? []); } catch (e) { }

      const metIcon = m => m === 'Efectivo' ? '💵' : '💳';
      const rows = nominas.length ? nominas.map(n => `
    <div style="display:flex;align-items:center;gap:12px;padding:12px 14px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);margin-bottom:8px;">
      <div style="width:38px;height:38px;border-radius:50%;background:var(--sage-light);display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;">👤</div>
      <div style="flex:1;min-width:0;">
        <div style="font-weight:700;font-size:13px;">${n.nombre_empleado}</div>
        <div style="font-size:11px;color:var(--text-muted);">${n.concepto} · ${n.created_at?.slice(0, 16) || ''} · ${n.cajero || ''}</div>
      </div>
      <div style="text-align:right;flex-shrink:0;">
        <div style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:15px;color:var(--sage-dark);">$${n.monto.toLocaleString('es-MX', { minimumFractionDigits: 2 })}</div>
        <div style="font-size:11px;color:var(--text-muted);">${metIcon(n.metodo_pago)} ${n.metodo_pago}</div>
      </div>
    </div>`).join('') : '<div style="padding:40px;text-align:center;color:var(--text-muted);">Sin nóminas registradas</div>';

      const totalMes = nominas.filter(n => n.created_at?.slice(0, 7) === new Date().toISOString().slice(0, 7)).reduce((s, n) => s + n.monto, 0);

      showModal(`<div class="modal-body">
    <div class="modal-title">👥 Nóminas</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;">
      <div class="res-card"><div class="res-label">Total este mes</div><div class="res-val" style="color:var(--sage-dark);">$${totalMes.toLocaleString('es-MX', { minimumFractionDigits: 2 })}</div></div>
      <div class="res-card"><div class="res-label">Registros totales</div><div class="res-val">${nominas.length}</div></div>
    </div>
    <button class="btn btn-sage" style="width:100%;margin-bottom:14px;" onclick="showRegistrarNominaModal()">+ Registrar Pago</button>
    <div style="max-height:500px;overflow-y:auto;">${rows}</div>
  </div>`);
    }

    function showRegistrarNominaModal() {
      // Abre encima como modal normal (saliendo del modo fp temporalmente)
      const wasFp = _fpActive;
      _fpActive = false;
      showModal(`<div class="modal-title">💸 Registrar Pago de Nómina</div>
    <div style="display:flex;flex-direction:column;gap:12px;margin-top:16px;">
      <div>
        <label class="input-label">👤 Nombre del empleado</label>
        <input id="nomEmpleado" type="text" class="input" placeholder="Nombre completo" autofocus>
      </div>
      <div>
        <label class="input-label">📝 Concepto</label>
        <input id="nomConcepto" type="text" class="input" placeholder="Ej: Quincena, Semana, Bono…" value="Nómina">
      </div>
      <div>
        <label class="input-label">💰 Monto</label>
        <input id="nomMonto" type="number" class="input" placeholder="0.00" step="0.01" min="0">
      </div>
      <div>
        <label class="input-label">💳 Método de pago</label>
        <div style="display:flex;gap:8px;">
          <button id="nomBtnEf" class="pay-btn active" onclick="nomSetMetodo('Efectivo')" style="flex:1">💵 Efectivo</button>
          <button id="nomBtnTar" class="pay-btn" onclick="nomSetMetodo('Tarjeta')" style="flex:1">💳 Tarjeta</button>
        </div>
      </div>
    </div>
    <div class="modal-btns" style="margin-top:20px;">
      <button class="btn btn-ghost" onclick="closeModal();${wasFp ? '_fpActive=true;' : ''}" >Cancelar</button>
      <button class="btn btn-sage" onclick="doRegistrarNomina(${wasFp})">Registrar y Enviar PDF</button>
    </div>`);
      window._nomMetodo = 'Efectivo';
    }

    function nomSetMetodo(m) {
      window._nomMetodo = m;
      document.getElementById('nomBtnEf').classList.toggle('active', m === 'Efectivo');
      document.getElementById('nomBtnTar').classList.toggle('active', m === 'Tarjeta');
    }

    async function doRegistrarNomina(wasFp = false) {
      const nombre = document.getElementById('nomEmpleado')?.value?.trim();
      const concepto = document.getElementById('nomConcepto')?.value?.trim() || 'Nómina';
      const monto = parseFloat(document.getElementById('nomMonto')?.value);
      if (!nombre) { toast('⚠️', 'Ingresa el nombre del empleado', 'var(--gold)'); return; }
      if (!monto || monto <= 0) { toast('⚠️', 'Ingresa un monto válido', 'var(--gold)'); return; }
      try {
        await api('/nominas', {
          method: 'POST', body: {
            nombre_empleado: nombre, concepto, monto,
            metodo_pago: window._nomMetodo || 'Efectivo',
            usuario_id: usuario?.id
          }
        });
        toast('✅', 'Nómina registrada y correo enviado', 'var(--green-ok)');
        document.getElementById('modals').innerHTML = '';
        if (wasFp) { _fpActive = true; _fpRendered = false; showNominasPage(); }
      } catch (e) { toast('❌', e.message, 'var(--red)'); }
    }

    /* ── MOVIMIENTOS (Gastos e Ingresos) ── */
    async function showMovimientosPage() {
      if (!usuario) return showNipModal(() => showMovimientosPage());
      const esAdmin = usuario.perfil === 'Administrador';
      const [_gastosResp, _ingresosResp] = await Promise.all([api('/gastos'), api('/ingresos')]);
      const gastos = Array.isArray(_gastosResp) ? _gastosResp : (_gastosResp.items ?? []);
      const ingresos = Array.isArray(_ingresosResp) ? _ingresosResp : (_ingresosResp.items ?? []);

      const ingresoTiendas = tiendas.filter(t => t.nombre === 'Estudio Deco' || t.nombre === 'Estación 304');
      const ingOpts = ingresoTiendas.map(t => `<option value="${t.id}">${t.nombre}</option>`).join('');
      const gastoTiendas = tiendas.filter(t => t.nombre === 'Estudio Deco' || t.nombre === 'Estación 304');
      const gasOpts = gastoTiendas.map(t => `<option value="${t.id}">${t.nombre}</option>`).join('');

      const th = `padding:8px 10px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--text-secondary);border-bottom:2px solid var(--border);`;
      const tbl = `width:100%;border-collapse:collapse;font-size:13px;`;

      const filaG = g => {
        const f = (g.created_at||'').substring(0,16);
        return `<tr style="border-bottom:1px solid var(--border-light);">
          <td style="padding:8px 10px;font-size:12px;color:var(--text-muted);">${f}</td>
          <td style="padding:8px 10px;">${g.concepto}</td>
          <td style="padding:8px 10px;font-size:12px;color:var(--text-secondary);">${g.tienda} · ${g.origen}</td>
          <td style="padding:8px 10px;font-family:'JetBrains Mono',monospace;font-weight:700;color:var(--red);text-align:right;">-$${g.monto.toFixed(2)}</td>
          ${esAdmin ? `<td style="padding:8px 6px;text-align:center;"><button onclick="anularGasto(${g.id})" style="padding:3px 9px;font-size:11px;background:var(--red-light);color:var(--red);border:none;border-radius:6px;cursor:pointer;font-weight:600;">Anular</button></td>` : '<td></td>'}
        </tr>`;
      };
      const filaI = i => {
        const f = (i.created_at||'').substring(0,16);
        return `<tr style="border-bottom:1px solid var(--border-light);">
          <td style="padding:8px 10px;font-size:12px;color:var(--text-muted);">${f}</td>
          <td style="padding:8px 10px;">${i.concepto}</td>
          <td style="padding:8px 10px;font-size:12px;color:var(--text-secondary);">${i.metodo_pago}</td>
          <td style="padding:8px 10px;font-family:'JetBrains Mono',monospace;font-weight:700;color:var(--green-ok);text-align:right;">+$${i.monto.toFixed(2)}</td>
          ${esAdmin ? `<td style="padding:8px 6px;text-align:center;"><button onclick="anularIngreso(${i.id})" style="padding:3px 9px;font-size:11px;background:var(--red-light);color:var(--red);border:none;border-radius:6px;cursor:pointer;font-weight:600;">Anular</button></td>` : '<td></td>'}
        </tr>`;
      };

      showModal(`<div class="modal-body">
        <div style="padding:18px 20px 0;"><div class="modal-title" style="margin:0;">💼 Gastos e Ingresos</div></div>
        <div style="padding:14px 20px;display:flex;flex-direction:column;gap:20px;overflow-y:auto;max-height:80vh;">

          <!-- FORMULARIOS -->
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <!-- Nuevo Gasto -->
            <div style="background:var(--red-light);border-radius:var(--radius-sm);padding:14px;display:flex;flex-direction:column;gap:8px;">
              <div style="font-size:13px;font-weight:700;color:var(--red);">💸 Nuevo Gasto</div>
              <select id="mv_gOrigen" class="input" style="font-size:13px;padding:7px 10px;"><option value="Caja">Caja / Efectivo</option><option value="Banco">Banco / Transferencia</option></select>
              <select id="mv_gTienda" class="input" style="font-size:13px;padding:7px 10px;">${gasOpts}</select>
              <input id="mv_gConcepto" class="input" placeholder="Concepto" style="font-size:13px;padding:7px 10px;">
              <input id="mv_gMonto" type="number" class="input" placeholder="Monto" step="0.01" style="font-size:13px;padding:7px 10px;">
              <button onclick="mvGuardarGasto()" style="padding:8px;background:var(--red);color:#fff;border:none;border-radius:var(--radius-sm);font-size:13px;font-weight:600;cursor:pointer;">Guardar Gasto</button>
            </div>
            <!-- Nuevo Ingreso -->
            <div style="background:var(--green-light);border-radius:var(--radius-sm);padding:14px;display:flex;flex-direction:column;gap:8px;">
              <div style="font-size:13px;font-weight:700;color:var(--green-ok);">💰 Nuevo Ingreso</div>
              <select id="mv_iDestino" class="input" style="font-size:13px;padding:7px 10px;">${ingOpts}</select>
              <select id="mv_iMetodo" class="input" style="font-size:13px;padding:7px 10px;"><option value="Efectivo">Efectivo</option><option value="Tarjeta">Tarjeta / Transferencia</option></select>
              <input id="mv_iConcepto" class="input" placeholder="Concepto" style="font-size:13px;padding:7px 10px;">
              <input id="mv_iMonto" type="number" class="input" placeholder="Monto" step="0.01" style="font-size:13px;padding:7px 10px;">
              <button onclick="mvGuardarIngreso()" style="padding:8px;background:var(--green-ok);color:#fff;border:none;border-radius:var(--radius-sm);font-size:13px;font-weight:600;cursor:pointer;">Guardar Ingreso</button>
            </div>
          </div>

          <!-- GASTOS -->
          <div>
            <div style="font-size:13px;font-weight:700;color:var(--red);margin-bottom:8px;">💸 Historial de Gastos (${gastos.length})</div>
            ${gastos.length === 0 ? '<div style="color:var(--text-muted);font-size:13px;">Sin gastos</div>' :
            `<div style="overflow-x:auto;border-radius:var(--radius-sm);border:1px solid var(--border);">
              <table style="${tbl}"><thead><tr>
                <th style="${th}">Fecha</th><th style="${th}">Concepto</th><th style="${th}">Tienda · Origen</th>
                <th style="${th};text-align:right;">Monto</th><th style="${th}"></th>
              </tr></thead><tbody>${gastos.map(filaG).join('')}</tbody></table>
            </div>`}
          </div>

          <!-- INGRESOS -->
          <div>
            <div style="font-size:13px;font-weight:700;color:var(--green-ok);margin-bottom:8px;">💰 Historial de Ingresos (${ingresos.length})</div>
            ${ingresos.length === 0 ? '<div style="color:var(--text-muted);font-size:13px;">Sin ingresos</div>' :
            `<div style="overflow-x:auto;border-radius:var(--radius-sm);border:1px solid var(--border);">
              <table style="${tbl}"><thead><tr>
                <th style="${th}">Fecha</th><th style="${th}">Concepto</th><th style="${th}">Método</th>
                <th style="${th};text-align:right;">Monto</th><th style="${th}"></th>
              </tr></thead><tbody>${ingresos.map(filaI).join('')}</tbody></table>
            </div>`}
          </div>

        </div>
      </div>`);
    }

    async function mvGuardarGasto() {
      const origen = document.getElementById('mv_gOrigen').value;
      const tienda_id = +document.getElementById('mv_gTienda').value;
      const concepto = document.getElementById('mv_gConcepto').value.trim();
      const monto = parseFloat(document.getElementById('mv_gMonto').value);
      if (!concepto || !monto || monto <= 0) { toast('⚠️', 'Completa concepto y monto', 'var(--gold)'); return; }
      await api('/gastos', { method: 'POST', body: { usuario_id: usuario.id, tienda_id, concepto, monto, origen } });
      toast('✅', `Gasto $${monto.toFixed(2)} registrado`, 'var(--green-ok)');
      _fpRendered = false; showMovimientosPage();
    }

    async function mvGuardarIngreso() {
      const tid = +document.getElementById('mv_iDestino').value;
      const metodo_pago = document.getElementById('mv_iMetodo').value;
      const concepto = document.getElementById('mv_iConcepto').value.trim();
      const monto = parseFloat(document.getElementById('mv_iMonto').value);
      if (!concepto || !monto || monto <= 0) { toast('⚠️', 'Completa concepto y monto', 'var(--gold)'); return; }
      const estacionT = tiendas.find(t => t.nombre === 'Estación 304');
      if (estacionT && tid === estacionT.id) {
        const hoy = new Date().toISOString().split('T')[0];
        await api('/pagos-tienda', { method: 'POST', body: { tienda_id: tid, tienda_nombre: 'Estación 304', monto, metodo_pago, concepto, es_interno: true, semana_inicio: hoy, semana_fin: hoy }});
      } else {
        await api('/ingresos', { method: 'POST', body: { usuario_id: usuario.id, concepto, monto, metodo_pago } });
      }
      toast('✅', `Ingreso $${monto.toFixed(2)} registrado`, 'var(--green-ok)');
      _fpRendered = false; showMovimientosPage();
    }

    async function anularGasto(id) {
      if (!confirm('¿Anular este gasto? Se eliminará del sistema.')) return;
      await api(`/gastos/${id}`, { method: 'DELETE' });
      toast('✅', 'Gasto anulado', 'var(--green-ok)');
      _fpRendered = false; showMovimientosPage();
    }

    async function anularIngreso(id) {
      if (!confirm('¿Anular este ingreso? Se eliminará del sistema.')) return;
      await api(`/ingresos/${id}`, { method: 'DELETE' });
      toast('✅', 'Ingreso anulado', 'var(--green-ok)');
      _fpRendered = false; showMovimientosPage();
    }

    function toggleTheme() {
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      const next = isDark ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      ['themeToggle','themeToggleE'].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.textContent = next === 'dark' ? '☀️' : '🌙';
      });
    }

    function initTheme() {
      const saved = localStorage.getItem('theme') || 'light';
      document.documentElement.setAttribute('data-theme', saved);
      ['themeToggle','themeToggleE'].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.textContent = saved === 'dark' ? '☀️' : '🌙';
      });
    }

    // ── LOGIN / SESSION ──────────────────────────────────────────────
    let _currentRole = null;

    function showLogin() {
      const ls = document.getElementById('loginScreen');
      ls.style.display = 'flex';
      ls.style.alignItems = 'center';
      ls.style.justifyContent = 'center';
      document.getElementById('decoApp').style.display = 'none';
      document.getElementById('estacionApp').style.display = 'none';
      document.getElementById('themeToggle').style.display = 'none';
      setTimeout(() => document.getElementById('loginUser').focus(), 100);
    }

    function showDecoApp() {
      document.getElementById('loginScreen').style.display = 'none';
      document.getElementById('decoApp').style.display = 'block';
      document.getElementById('estacionApp').style.display = 'none';
      document.getElementById('themeToggle').style.display = 'flex';
    }

    function showEstacionApp() {
      document.getElementById('loginScreen').style.display = 'none';
      document.getElementById('decoApp').style.display = 'none';
      document.getElementById('estacionApp').style.display = 'block';
      document.getElementById('themeToggle').style.display = 'none';
      loadEstacionData();
    }

    async function doLogin() {
      const username = document.getElementById('loginUser').value.trim();
      const password = document.getElementById('loginPass').value;
      const errEl = document.getElementById('loginError');
      errEl.style.display = 'none';
      if (!username || !password) { errEl.textContent = 'Ingresa usuario y contraseña'; errEl.style.display = 'block'; return; }
      try {
        const res = await fetch('/api/login', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({username, password}) });
        if (!res.ok) { const e = await res.json(); errEl.textContent = e.detail || 'Credenciales incorrectas'; errEl.style.display = 'block'; return; }
        const data = await res.json();
        sessionStorage.setItem('session', JSON.stringify({username: data.username, role: data.role}));
        _currentRole = data.role;
        if (data.role === 'deco') showDecoApp();
        else showEstacionApp();
      } catch(e) { errEl.textContent = 'Error de conexión'; errEl.style.display = 'block'; }
    }

    function doLogout() {
      sessionStorage.removeItem('session');
      _currentRole = null;
      document.getElementById('loginUser').value = '';
      document.getElementById('loginPass').value = '';
      showLogin();
    }

    function initSession() {
      const raw = sessionStorage.getItem('session');
      if (!raw) { showLogin(); return; }
      try {
        const s = JSON.parse(raw);
        _currentRole = s.role;
        if (s.role === 'deco') showDecoApp();
        else if (s.role === 'estacion') showEstacionApp();
        else showLogin();
      } catch { showLogin(); }
    }

    // ── ESTACIÓN 304 ADMIN ───────────────────────────────────────────
    async function loadEstacionData() {
      try {
        const [bal, movs] = await Promise.all([
          fetch('/api/estacion/balance').then(r => r.json()),
          fetch('/api/estacion/movimientos').then(r => r.json()),
        ]);
        document.getElementById('estBalanceNum').textContent = '$' + bal.balance.toLocaleString('es-MX', {minimumFractionDigits:2, maximumFractionDigits:2});
        document.getElementById('estIngresosNum').textContent = '$' + bal.total_ingresos.toLocaleString('es-MX', {minimumFractionDigits:2, maximumFractionDigits:2});
        document.getElementById('estGastosNum').textContent = '$' + bal.total_gastos.toLocaleString('es-MX', {minimumFractionDigits:2, maximumFractionDigits:2});
        const el = document.getElementById('estMovimientos');
        if (!movs.length) { el.innerHTML = '<div style="color:var(--text-muted);font-size:13px;text-align:center;padding:20px;">Sin movimientos aún</div>'; return; }
        el.innerHTML = movs.map(m => {
          const isIng = m.tipo === 'ingreso';
          const sign = isIng ? '+' : '-';
          const color = isIng ? 'var(--green-ok)' : 'var(--red)';
          const bg = isIng ? 'var(--green-light)' : 'var(--red-light)';
          const icon = isIng ? '↓' : '↑';
          const fecha = m.created_at ? m.created_at.substring(0,16).replace('T',' ') : '';
          return `<div style="display:flex;align-items:center;gap:12px;padding:12px 14px;background:var(--bg);border-radius:var(--radius-sm);border:1px solid var(--border);">
            <div style="width:32px;height:32px;border-radius:50%;background:${bg};color:${color};display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;flex-shrink:0;">${icon}</div>
            <div style="flex:1;min-width:0;">
              <div style="font-size:14px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${m.concepto}</div>
              <div style="font-size:11px;color:var(--text-muted);">${fecha} · ${m.metodo_pago}</div>
            </div>
            <div style="font-size:16px;font-weight:700;color:${color};flex-shrink:0;">${sign}$${m.monto.toLocaleString('es-MX',{minimumFractionDigits:2,maximumFractionDigits:2})}</div>
          </div>`;
        }).join('');
      } catch(e) { console.error('loadEstacionData', e); }
    }

    async function registrarGastoEstacion() {
      const concepto = document.getElementById('estGastoConcepto').value.trim();
      const monto = parseFloat(document.getElementById('estGastoMonto').value);
      const metodo_pago = document.getElementById('estGastoMetodo').value;
      if (!concepto) { toast('⚠️', 'Ingresa el concepto del gasto', 'var(--gold)'); return; }
      if (!monto || monto <= 0) { toast('⚠️', 'Ingresa un monto válido', 'var(--gold)'); return; }
      try {
        const res = await fetch('/api/estacion/gasto', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({concepto, monto, metodo_pago}) });
        if (!res.ok) throw new Error('Error al registrar');
        document.getElementById('estGastoConcepto').value = '';
        document.getElementById('estGastoMonto').value = '';
        toast('✅', 'Gasto registrado', 'var(--green-ok)');
        loadEstacionData();
      } catch(e) { toast('❌', e.message, 'var(--red)'); }
    }

    // ── TABS ESTACIÓN ──────────────────────────────────────────────
    function estSwitchTab(tab) {
      ['finanzas', 'inventario'].forEach(t => {
        const btn  = document.getElementById(`estTab-${t}`);
        const pane = document.getElementById(`estPane-${t}`);
        const active = t === tab;
        btn.style.borderBottomColor  = active ? 'var(--sage)' : 'transparent';
        btn.style.color              = active ? 'var(--sage)' : 'var(--text-secondary)';
        pane.style.display           = active ? 'flex'        : 'none';
      });
      if (tab === 'inventario') loadInventarioEstacion();
    }

    // ── INVENTARIO ESTACIÓN 304 ────────────────────────────────────
    async function loadInventarioEstacion() {
      try {
        const [porciones, ingredientes, recetas] = await Promise.all([
          fetch('/api/estacion/porciones').then(r => r.json()),
          fetch('/api/estacion/inventario').then(r => r.json()),
          fetch('/api/estacion/recetas').then(r => r.json()),
        ]);
        renderPorcionesEstacion(porciones);
        renderIngredientesEstacion(ingredientes);
        // Poblar el selector de venta manual con recetas de BD
        const sel = document.getElementById('estBebidaSel');
        if (sel) {
          sel.innerHTML = '<option value="">Seleccionar bebida…</option>' +
            recetas.map(r => `<option value="${r.nombre}">${r.nombre}</option>`).join('');
        }
      } catch(e) { console.error('loadInventarioEstacion', e); }
      loadRecetasEstacion();
    }

    function renderPorcionesEstacion(porciones) {
      const el = document.getElementById('estPorciones');
      if (!el) return;
      const entries = Object.entries(porciones).sort((a,b) => b[1].porciones - a[1].porciones);
      el.innerHTML = entries.map(([bebida, info]) => {
        const n = info.porciones;
        const color = n === 0 ? 'var(--red)' : n <= 2 ? 'var(--gold)' : 'var(--green-ok)';
        const bg    = n === 0 ? 'var(--red-light)' : n <= 2 ? '#fff8e1' : 'var(--bg-warm)';
        const cuello = info.faltantes?.length
          ? `Sin: ${info.faltantes.join(', ')}`
          : (info.cuello_de_botella ? `Límite: ${info.cuello_de_botella}` : '');
        return `<div style="background:${bg};border-radius:var(--radius-sm);padding:10px 12px;display:flex;flex-direction:column;gap:2px;">
          <div style="font-size:11px;font-weight:700;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${bebida}</div>
          <div style="font-size:22px;font-weight:800;color:${color};">${n}</div>
          ${cuello ? `<div style="font-size:10px;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${cuello}">${cuello}</div>` : ''}
        </div>`;
      }).join('');
    }

    function renderIngredientesEstacion(ingredientes) {
      const el = document.getElementById('estIngredientes');
      if (!el) return;
      el.innerHTML = ingredientes.map(ing => {
        const bajo    = ing.stock_minimo > 0 && ing.stock_actual <= ing.stock_minimo;
        const agotado = ing.stock_actual <= 0;
        const bgColor  = agotado ? 'var(--red-light)' : bajo ? '#fff8e1' : 'var(--bg-warm)';
        const numColor = agotado ? 'var(--red)' : bajo ? 'var(--gold)' : 'var(--text)';
        const unidad   = ing.unidad === 'unidad' ? 'uds' : ing.unidad;
        const costo    = ing.costo_unitario > 0 ? `$${ing.costo_unitario.toFixed(2)}/${unidad}` : '';
        const nomEsc   = ing.nombre.replace(/'/g,"\\'");
        return `<div style="display:flex;align-items:center;gap:8px;padding:10px 12px;background:${bgColor};border-radius:var(--radius-sm);">
          <div onclick="estEditarIngrediente(${ing.id},'${nomEsc}',${ing.stock_actual},${ing.stock_minimo},'${ing.unidad}')"
            style="flex:1;cursor:pointer;display:flex;flex-direction:column;gap:1px;">
            <div style="font-size:13px;font-weight:600;color:var(--text);">${ing.nombre}</div>
            ${costo ? `<div style="font-size:11px;color:var(--text-muted);">CPP: ${costo}</div>` : ''}
          </div>
          <div style="font-size:13px;font-weight:700;color:${numColor};white-space:nowrap;">${ing.stock_actual.toFixed(0)} ${unidad}</div>
          ${agotado ? '<div style="font-size:10px;font-weight:700;color:var(--red);background:var(--red-light);padding:2px 6px;border-radius:4px;">AGOTADO</div>' : bajo ? '<div style="font-size:10px;font-weight:700;color:var(--gold);background:#fff8e1;padding:2px 6px;border-radius:4px;">BAJO</div>' : ''}
          <button onclick="estModalCompra(${ing.id},'${nomEsc}','${ing.unidad}')" title="Registrar compra"
            style="padding:6px 10px;background:var(--sage);color:#fff;border:none;border-radius:var(--radius-sm);font-size:13px;cursor:pointer;flex-shrink:0;">🛒</button>
        </div>`;
      }).join('');
    }

    // ── RECETAS ──────────────────────────────────────────────────────
    async function loadRecetasEstacion() {
      const el = document.getElementById('estRecetasList');
      if (!el) return;
      try {
        const recetas = await fetch('/api/estacion/recetas').then(r => r.json());
        if (!recetas.length) {
          el.innerHTML = '<div style="color:var(--text-muted);font-size:13px;">Sin recetas.</div>';
          return;
        }
        el.innerHTML = recetas.map(r => `
          <div style="display:flex;align-items:center;gap:8px;padding:10px 12px;background:var(--bg-warm);border-radius:var(--radius-sm);">
            <div style="flex:1;">
              <div style="font-size:13px;font-weight:600;color:var(--text);">${r.nombre}</div>
              <div style="font-size:11px;color:var(--text-muted);">${r.num_ingredientes} ingrediente${r.num_ingredientes !== 1 ? 's' : ''}</div>
            </div>
            <button onclick="estEditarReceta(${r.id}, '${r.nombre.replace(/'/g,"&#39;")}')" title="Editar" style="padding:6px 10px;background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-sm);cursor:pointer;font-size:13px;">✏️</button>
            <button onclick="estEliminarReceta(${r.id}, '${r.nombre.replace(/'/g,"&#39;")}')" title="Eliminar" style="padding:6px 10px;background:var(--red-light);color:var(--red);border:none;border-radius:var(--radius-sm);cursor:pointer;font-size:13px;">🗑️</button>
          </div>`).join('');
      } catch(e) { el.innerHTML = '<div style="color:var(--red);font-size:13px;">Error al cargar recetas.</div>'; }
    }

    function estNuevaReceta() {
      showModal(`
        <div class="modal-title">📋 Nueva Receta</div>
        <div class="modal-simple" style="display:flex;flex-direction:column;gap:12px;margin-top:12px;">
          <div class="field">
            <label>Nombre de la receta</label>
            <input id="recNombre" type="text" class="input" placeholder="Ej. LATTE ESPECIAL" style="width:100%;">
          </div>
        </div>
        <div class="modal-btns" style="margin-top:16px;">
          <button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
          <button class="btn btn-sage" onclick="estGuardarNombreReceta(null)">Crear</button>
        </div>`);
    }

    async function estEditarReceta(id, nombre) {
      let detalle;
      try {
        detalle = await fetch(`/api/estacion/recetas/${id}`).then(r => r.json());
      } catch(e) { toast('❌', 'Error al cargar receta', 'var(--red)'); return; }

      let ings = [];
      try {
        ings = await fetch('/api/estacion/inventario').then(r => r.json());
      } catch(e) {}

      const ingOpts = ings.map(i => `<option value="${i.id}">${i.nombre} (${i.unidad === 'unidad' ? 'uds' : i.unidad})</option>`).join('');
      const ingRows = detalle.ingredientes.map(i => `
        <tr>
          <td style="padding:6px 8px;">${i.ingrediente_nombre}</td>
          <td style="padding:6px 8px;">${i.cantidad} ${i.unidad === 'unidad' ? 'uds' : i.unidad}</td>
          <td style="padding:6px 8px;text-align:right;">
            <button onclick="estQuitarIngReceta(${id}, ${i.ingrediente_id})" style="padding:3px 8px;background:var(--red-light);color:var(--red);border:none;border-radius:4px;cursor:pointer;font-size:12px;">✕</button>
          </td>
        </tr>`).join('') || '<tr><td colspan="3" style="padding:8px;color:var(--text-muted);font-size:12px;">Sin ingredientes</td></tr>';

      showModal(`
        <div class="modal-title">✏️ Editar Receta</div>
        <div class="modal-simple" style="display:flex;flex-direction:column;gap:14px;margin-top:12px;">
          <div style="display:flex;gap:8px;align-items:flex-end;">
            <div class="field" style="flex:1;margin:0;">
              <label>Nombre</label>
              <input id="recNombre" type="text" class="input" value="${detalle.nombre}" style="width:100%;">
            </div>
            <button class="btn btn-sage" style="white-space:nowrap;" onclick="estGuardarNombreReceta(${id})">Guardar nombre</button>
          </div>
          <div>
            <div style="font-size:13px;font-weight:600;color:var(--text);margin-bottom:6px;">Ingredientes</div>
            <table style="width:100%;border-collapse:collapse;font-size:13px;" id="recIngTable">
              <thead><tr style="background:var(--bg-warm);">
                <th style="padding:6px 8px;text-align:left;font-weight:600;color:var(--text-secondary);">Ingrediente</th>
                <th style="padding:6px 8px;text-align:left;font-weight:600;color:var(--text-secondary);">Cantidad</th>
                <th></th>
              </tr></thead>
              <tbody id="recIngBody">${ingRows}</tbody>
            </table>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;padding:10px;background:var(--bg-warm);border-radius:var(--radius-sm);">
            <div class="field" style="flex:2;min-width:140px;margin:0;">
              <label>Ingrediente</label>
              <select id="recIngSel" class="input">${ingOpts}</select>
            </div>
            <div class="field" style="flex:1;min-width:80px;margin:0;">
              <label>Cantidad</label>
              <input id="recIngCant" type="number" min="0.01" step="0.01" class="input" placeholder="g / uds">
            </div>
            <button class="btn btn-sage" style="white-space:nowrap;" onclick="estAgregarIngReceta(${id})">Agregar</button>
          </div>
        </div>
        <div class="modal-btns" style="margin-top:16px;">
          <button class="btn btn-ghost" onclick="closeModal()">Cerrar</button>
        </div>`);
    }

    async function estGuardarNombreReceta(id) {
      const nombre = (document.getElementById('recNombre')?.value || '').trim();
      if (!nombre) { toast('⚠️', 'Ingresa un nombre', 'var(--gold)'); return; }
      try {
        if (id) {
          const res = await fetch(`/api/estacion/recetas/${id}`, {
            method: 'PUT', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ nombre })
          });
          if (!res.ok) { const d = await res.json(); throw new Error(d.detail || 'Error'); }
          toast('✅', 'Nombre actualizado', 'var(--green-ok)');
        } else {
          const res = await fetch('/api/estacion/recetas', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ nombre })
          });
          if (!res.ok) { const d = await res.json(); throw new Error(d.detail || 'Error'); }
          const nueva = await res.json();
          closeModal();
          toast('✅', 'Receta creada', 'var(--green-ok)');
          estEditarReceta(nueva.id, nueva.nombre);
        }
        loadRecetasEstacion();
      } catch(e) { toast('❌', e.message, 'var(--red)'); }
    }

    async function estAgregarIngReceta(recetaId) {
      const ingrediente_id = parseInt(document.getElementById('recIngSel')?.value);
      const cantidad = parseFloat(document.getElementById('recIngCant')?.value);
      if (!ingrediente_id || !cantidad || cantidad <= 0) {
        toast('⚠️', 'Selecciona un ingrediente y cantidad válida', 'var(--gold)'); return;
      }
      try {
        const res = await fetch(`/api/estacion/recetas/${recetaId}/ingredientes`, {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ ingrediente_id, cantidad })
        });
        if (!res.ok) { const d = await res.json(); throw new Error(d.detail || 'Error'); }
        toast('✅', 'Ingrediente agregado', 'var(--green-ok)');
        estEditarReceta(recetaId, '');
        loadRecetasEstacion();
      } catch(e) { toast('❌', e.message, 'var(--red)'); }
    }

    async function estQuitarIngReceta(recetaId, ingredienteId) {
      try {
        await fetch(`/api/estacion/recetas/${recetaId}/ingredientes/${ingredienteId}`, { method: 'DELETE' });
        toast('✅', 'Ingrediente eliminado', 'var(--green-ok)');
        estEditarReceta(recetaId, '');
        loadRecetasEstacion();
      } catch(e) { toast('❌', e.message, 'var(--red)'); }
    }

    async function estEliminarReceta(id, nombre) {
      if (!confirm(`¿Eliminar la receta "${nombre}"? Esta acción no se puede deshacer.`)) return;
      try {
        await fetch(`/api/estacion/recetas/${id}`, { method: 'DELETE' });
        toast('✅', `Receta "${nombre}" eliminada`, 'var(--green-ok)');
        loadRecetasEstacion();
      } catch(e) { toast('❌', e.message, 'var(--red)'); }
    }

    function estEditarIngrediente(id, nombre, stockActual, stockMinimo, unidad) {
      const u = unidad === 'unidad' ? 'unidades' : 'g/ml';
      showModal(`
        <div class="modal-title">📦 ${nombre}</div>
        <div class="modal-sub">Stock actual: ${stockActual.toFixed(0)} ${u}</div>
        <div class="modal-simple" style="margin-top:14px;display:flex;flex-direction:column;gap:12px;">
          <div class="field">
            <label>Reponer (sumar al stock)</label>
            <input id="invRestockAmt" type="number" min="0" step="1" placeholder="Cantidad a agregar"
              class="input" style="width:100%;">
          </div>
          <div class="field">
            <label>Ajustar stock exacto (inventario físico)</label>
            <input id="invAjusteAmt" type="number" min="0" step="1" placeholder="Nuevo total"
              class="input" style="width:100%;" value="${stockActual}">
          </div>
          <div class="field">
            <label>Stock mínimo de alerta</label>
            <input id="invMinimoAmt" type="number" min="0" step="1" placeholder="0"
              class="input" style="width:100%;" value="${stockMinimo}">
          </div>
        </div>
        <div class="modal-btns" style="margin-top:16px;">
          <button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
          <button class="btn btn-sage" onclick="estGuardarIngrediente(${id})">Guardar</button>
        </div>`);
    }

    async function estGuardarIngrediente(id) {
      const restock = parseFloat(document.getElementById('invRestockAmt').value) || 0;
      const ajuste  = parseFloat(document.getElementById('invAjusteAmt').value);
      const minimo  = parseFloat(document.getElementById('invMinimoAmt').value) || 0;
      try {
        const promises = [];
        if (restock > 0) {
          promises.push(fetch(`/api/estacion/inventario/${id}/restock`, {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ cantidad: restock })
          }));
        } else {
          promises.push(fetch(`/api/estacion/inventario/${id}`, {
            method: 'PUT', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ nuevo_stock: ajuste })
          }));
        }
        promises.push(fetch(`/api/estacion/inventario/${id}/minimo`, {
          method: 'PUT', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ stock_minimo: minimo })
        }));
        await Promise.all(promises);
        closeModal();
        toast('✅', 'Stock actualizado', 'var(--green-ok)');
        loadInventarioEstacion();
      } catch(e) { toast('❌', e.message, 'var(--red)'); }
    }

    async function estRegistrarVentaBebida() {
      const sel = document.getElementById('estBebidaSel');
      const bebida = sel?.value;
      if (!bebida) { toast('⚠️', 'Selecciona una bebida', 'var(--gold)'); return; }
      try {
        const res = await fetch('/api/estacion/bebida-vendida', {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ nombre_bebida: bebida })
        });
        const d = await res.json();
        sel.value = '';
        if (d.warning) {
          toast('⚠️', d.warning, 'var(--gold)');
        } else {
          toast('✅', `${bebida} descontada`, 'var(--green-ok)');
        }
        loadInventarioEstacion();
      } catch(e) { toast('❌', e.message, 'var(--red)'); }
    }

    function estReponerTodo() {
      showModal(`
        <div class="modal-title">📦 Ingreso masivo de stock</div>
        <div class="modal-sub">Introduce las cantidades que ingresan por ingrediente</div>
        <div class="modal-simple" style="max-height:55vh;overflow-y:auto;margin-top:14px;" id="masivoCont">
          <div style="color:var(--text-muted);font-size:13px;">Cargando...</div>
        </div>
        <div class="modal-btns" style="margin-top:16px;">
          <button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
          <button class="btn btn-sage" onclick="estGuardarMasivo()">Guardar todo</button>
        </div>`);
      fetch('/api/estacion/inventario').then(r => r.json()).then(ings => {
        document.getElementById('masivoCont').innerHTML = ings.map(ing => {
          const u = ing.unidad === 'unidad' ? 'uds' : 'g';
          return `<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <label style="flex:1;font-size:13px;font-weight:600;">${ing.nombre} <span style="font-weight:400;color:var(--text-muted);">(${ing.stock_actual.toFixed(0)} ${u})</span></label>
            <input data-id="${ing.id}" type="number" min="0" step="1" placeholder="+0"
              style="width:80px;padding:8px;border:1.5px solid var(--border);border-radius:var(--radius-sm);background:var(--bg);color:var(--text);font-size:13px;text-align:right;">
          </div>`;
        }).join('');
      });
    }

    // ── NUEVO INGREDIENTE ──────────────────────────────────────────
    function estNuevoIngrediente() {
      showModal(`
        <div class="modal-title">➕ Nuevo ingrediente</div>
        <div class="modal-simple" style="margin-top:14px;display:flex;flex-direction:column;gap:12px;">
          <div class="field">
            <label>Nombre</label>
            <input id="nuevoIngNombre" type="text" placeholder="ej. Canela, Polvo de cacao…"
              class="input" style="width:100%;" autofocus>
          </div>
          <div class="field">
            <label>Unidad de medida</label>
            <select id="nuevoIngUnidad" class="input" style="width:100%;">
              <option value="g">Gramos / ml</option>
              <option value="unidad">Unidades (piezas)</option>
            </select>
          </div>
          <div style="display:flex;gap:10px;">
            <div class="field" style="flex:1;">
              <label>Stock inicial (opcional)</label>
              <input id="nuevoIngStock" type="number" min="0" step="1" placeholder="0"
                class="input" style="width:100%;">
            </div>
            <div class="field" style="flex:1;">
              <label>Stock mínimo de alerta</label>
              <input id="nuevoIngMinimo" type="number" min="0" step="1" placeholder="0"
                class="input" style="width:100%;">
            </div>
          </div>
        </div>
        <div class="modal-btns" style="margin-top:16px;">
          <button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
          <button class="btn btn-sage" onclick="estGuardarNuevoIngrediente()">Crear</button>
        </div>`);
    }

    async function estGuardarNuevoIngrediente() {
      const nombre  = document.getElementById('nuevoIngNombre').value.trim();
      const unidad  = document.getElementById('nuevoIngUnidad').value;
      const stock   = parseFloat(document.getElementById('nuevoIngStock').value) || 0;
      const minimo  = parseFloat(document.getElementById('nuevoIngMinimo').value) || 0;
      if (!nombre) { toast('⚠️', 'Escribe un nombre', 'var(--gold)'); return; }
      try {
        const res = await fetch('/api/estacion/inventario', {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ nombre, unidad, stock_inicial: stock, stock_minimo: minimo })
        });
        if (!res.ok) { const d = await res.json(); throw new Error(d.detail || 'Error'); }
        closeModal();
        toast('✅', `"${nombre}" agregado al inventario`, 'var(--green-ok)');
        loadInventarioEstacion();
      } catch(e) { toast('❌', e.message, 'var(--red)'); }
    }

    // ── COMPRAS DE INSUMOS ─────────────────────────────────────────
    function estModalCompra(id, nombre, unidad) {
      const u = unidad === 'unidad' ? 'unidades' : 'g/ml';
      showModal(`
        <div class="modal-title">🛒 Registrar compra</div>
        <div class="modal-sub">${nombre}</div>
        <div class="modal-simple" style="margin-top:14px;display:flex;flex-direction:column;gap:12px;">
          <div class="field">
            <label>Cantidad comprada (${u})</label>
            <input id="compraCantidad" type="number" min="0.01" step="1" placeholder="ej. 1000"
              class="input" style="width:100%;" autofocus>
          </div>
          <div class="field">
            <label>Costo total de la compra ($)</label>
            <input id="compraCosto" type="number" min="0" step="0.01" placeholder="ej. 85.00"
              class="input" style="width:100%;">
          </div>
          <div id="compraCppPreview" style="font-size:12px;color:var(--text-muted);min-height:16px;"></div>
          <div class="field">
            <label>Nota (opcional)</label>
            <input id="compraNota" type="text" placeholder="ej. Lala 1L, Walmart"
              class="input" style="width:100%;">
          </div>
        </div>
        <div class="modal-btns" style="margin-top:16px;">
          <button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
          <button class="btn btn-sage" onclick="estGuardarCompra(${id})">Guardar compra</button>
        </div>`);

      // Preview de costo unitario en tiempo real
      const preview = () => {
        const cant  = parseFloat(document.getElementById('compraCantidad')?.value) || 0;
        const costo = parseFloat(document.getElementById('compraCosto')?.value) || 0;
        const el    = document.getElementById('compraCppPreview');
        if (el && cant > 0 && costo > 0)
          el.textContent = `Costo unitario: $${(costo/cant).toFixed(4)}/${u}`;
        else if (el) el.textContent = '';
      };
      setTimeout(() => {
        document.getElementById('compraCantidad')?.addEventListener('input', preview);
        document.getElementById('compraCosto')?.addEventListener('input', preview);
      }, 50);
    }

    async function estGuardarCompra(id) {
      const cantidad   = parseFloat(document.getElementById('compraCantidad').value);
      const costo      = parseFloat(document.getElementById('compraCosto').value);
      const nota       = document.getElementById('compraNota').value.trim();
      if (!cantidad || cantidad <= 0) { toast('⚠️', 'Ingresa la cantidad', 'var(--gold)'); return; }
      if (isNaN(costo) || costo < 0)  { toast('⚠️', 'Ingresa el costo', 'var(--gold)'); return; }
      try {
        const res = await fetch('/api/estacion/compras', {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ ingrediente_id: id, cantidad, costo_total: costo, nota })
        });
        if (!res.ok) { const d = await res.json(); throw new Error(d.detail || 'Error'); }
        closeModal();
        toast('✅', 'Compra registrada', 'var(--green-ok)');
        loadInventarioEstacion();
      } catch(e) { toast('❌', e.message, 'var(--red)'); }
    }

    async function estVerHistorialCompras(ingId = null) {
      const url = ingId ? `/api/estacion/compras/${ingId}` : '/api/estacion/compras';
      try {
        const entradas = await fetch(url).then(r => r.json());
        const filas = entradas.length
          ? entradas.map(e => {
              const u = e.unidad === 'unidad' ? 'uds' : e.unidad;
              const fecha = e.created_at?.slice(0,16).replace('T',' ') || e.created_at;
              return `<div style="display:grid;grid-template-columns:1fr auto auto;gap:6px 12px;padding:10px 0;border-bottom:1px solid var(--border);align-items:start;">
                <div>
                  <div style="font-size:13px;font-weight:600;">${e.ingrediente}</div>
                  ${e.nota ? `<div style="font-size:11px;color:var(--text-muted);">${e.nota}</div>` : ''}
                  <div style="font-size:11px;color:var(--text-muted);">${fecha}</div>
                </div>
                <div style="text-align:right;font-size:13px;font-weight:600;white-space:nowrap;">+${e.cantidad.toFixed(0)} ${u}</div>
                <div style="text-align:right;font-size:13px;white-space:nowrap;">
                  <div style="font-weight:700;color:var(--sage);">$${e.costo_total.toFixed(2)}</div>
                  <div style="font-size:11px;color:var(--text-muted);">$${e.costo_unitario.toFixed(4)}/${u}</div>
                </div>
              </div>`;
            }).join('')
          : '<div style="color:var(--text-muted);font-size:13px;text-align:center;padding:20px;">Sin compras registradas</div>';

        showModal(`
          <div class="modal-title">📋 Historial de compras</div>
          <div style="max-height:60vh;overflow-y:auto;margin-top:12px;">${filas}</div>
          <div class="modal-btns" style="margin-top:14px;">
            <button class="btn btn-ghost" onclick="closeModal()">Cerrar</button>
          </div>`);
      } catch(e) { toast('❌', e.message, 'var(--red)'); }
    }

    async function estGuardarMasivo() {
      const inputs = document.querySelectorAll('#masivoCont input[data-id]');
      const ops = [];
      inputs.forEach(inp => {
        const v = parseFloat(inp.value) || 0;
        if (v > 0) ops.push({ id: parseInt(inp.dataset.id), cantidad: v });
      });
      if (!ops.length) { closeModal(); return; }
      try {
        await Promise.all(ops.map(op =>
          fetch(`/api/estacion/inventario/${op.id}/restock`, {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ cantidad: op.cantidad })
          })
        ));
        closeModal();
        toast('✅', `${ops.length} ingrediente(s) reabastecido(s)`, 'var(--green-ok)');
        loadInventarioEstacion();
      } catch(e) { toast('❌', e.message, 'var(--red)'); }
    }

    initTheme();
    initSession();

    /* ── Notas Flotantes (ventanas) ── */
    let _notesTimeout = {};
    let _noteZ = 1002;
    const NOTE_MIN_W = 200;
    const NOTE_MIN_H = 120;
    const NOTE_DEFAULT_W = 260;
    const NOTE_DEFAULT_H = 180;

    function notePreviewLabel(texto) {
      const t = (texto || '').replace(/\s+/g, ' ').trim();
      if (!t) return 'Nota';
      return t.length > 24 ? t.slice(0, 24) + '…' : t;
    }

    function rgbToHex(color) {
      if (!color) return '#fef3c7';
      if (color.startsWith('#')) {
        if (color.length === 4) {
          return '#' + [...color.slice(1)].map(c => c + c).join('');
        }
        return color.slice(0, 7);
      }
      const m = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
      if (!m) return '#fef3c7';
      return '#' + [m[1], m[2], m[3]].map(n => (+n).toString(16).padStart(2, '0')).join('');
    }

    function noteTintParts(color) {
      const hex = rgbToHex(color);
      return {
        hex,
        r: parseInt(hex.slice(1, 3), 16),
        g: parseInt(hex.slice(3, 5), 16),
        b: parseInt(hex.slice(5, 7), 16),
      };
    }

    const NOTE_GLASS_ALPHA = 0.58;

    function ensureNotesGlassStyles() {
      if (document.getElementById('notes-glass-runtime')) return;
      const s = document.createElement('style');
      s.id = 'notes-glass-runtime';
      s.textContent = `
.floating-note{
  background:transparent!important;
  background-color:transparent!important;
}
.floating-note .note-glass{
  position:absolute!important;
  inset:0!important;
  border-radius:inherit!important;
  pointer-events:none!important;
  z-index:0!important;
}
.floating-note>:not(.note-glass):not(.note-resize){position:relative;z-index:1}
.floating-note>.note-resize{position:absolute!important;right:0!important;bottom:0!important;left:auto!important;top:auto!important;z-index:6!important}
.note-color-btn.active{outline:2px solid rgba(40,30,60,.55);outline-offset:1px;transform:scale(1.12)}
`;
      document.head.appendChild(s);
    }

    function applyNoteColor(el, color) {
      ensureNotesGlassStyles();
      const { hex, r, g, b } = noteTintParts(color);
      el.dataset.noteColor = hex;
      const rgba = `rgba(${r}, ${g}, ${b}, ${NOTE_GLASS_ALPHA})`;
      el.style.setProperty('background', 'transparent', 'important');
      el.style.setProperty('background-color', 'transparent', 'important');
      let glass = el.querySelector('.note-glass');
      if (!glass) {
        glass = document.createElement('div');
        glass.className = 'note-glass';
        el.insertBefore(glass, el.firstChild);
      }
      glass.style.setProperty('background', `linear-gradient(165deg, rgba(255,255,255,0.28), rgba(255,255,255,0.05)), ${rgba}`, 'important');
      glass.style.setProperty('background-color', rgba, 'important');
      glass.style.setProperty('backdrop-filter', 'blur(36px) saturate(170%)', 'important');
      glass.style.setProperty('-webkit-backdrop-filter', 'blur(36px) saturate(170%)', 'important');
      el.querySelectorAll('.note-color-btn').forEach(btn => {
        btn.classList.toggle('active', (btn.dataset.color || '').toLowerCase() === hex.toLowerCase());
      });
    }

    function focusNoteWindow(id) {
      document.querySelectorAll('.floating-note.note-active').forEach(n => n.classList.remove('note-active'));
      const el = document.getElementById(`note-${id}`);
      if (!el) return;
      el.style.zIndex = String(++_noteZ);
      el.classList.add('note-active');
    }

    function refreshNotesTaskbar() {
      const bar = document.getElementById('notesTaskbar');
      if (!bar) return;
      bar.innerHTML = '';
      document.querySelectorAll('.floating-note.minimized').forEach(el => {
        const id = el.dataset.noteId;
        const ta = el.querySelector('textarea');
        const color = el.dataset.noteColor || '#fef3c7';
        const { r, g, b } = noteTintParts(color);
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'note-chip';
        chip.style.setProperty('background-color', `rgba(${r}, ${g}, ${b}, 0.55)`, 'important');
        chip.style.setProperty('backdrop-filter', 'blur(20px) saturate(160%)', 'important');
        chip.style.setProperty('-webkit-backdrop-filter', 'blur(20px) saturate(160%)', 'important');
        chip.title = 'Restaurar nota';
        const dot = document.createElement('span');
        dot.className = 'note-chip-dot';
        dot.style.background = `rgb(${r}, ${g}, ${b})`;
        const label = document.createElement('span');
        label.className = 'note-chip-label';
        label.textContent = notePreviewLabel(ta?.value || '');
        chip.append(dot, label);
        chip.onclick = () => restoreNote(+id);
        bar.appendChild(chip);
      });
    }

    async function loadNotes() {
      ensureNotesGlassStyles();
      try {
        const res = await fetch('/api/notas');
        if (!res.ok) return;
        const data = await res.json();
        document.querySelectorAll('.floating-note').forEach(n => n.remove());
        const bar = document.getElementById('notesTaskbar');
        if (bar) bar.innerHTML = '';
        data.forEach(note => renderNote(note));
        refreshNotesTaskbar();
      } catch (e) { console.error('Error loading notes:', e); }
    }

    async function createNote() {
      try {
        const body = {
          texto: '',
          pos_x: Math.max(20, window.innerWidth / 2 - NOTE_DEFAULT_W / 2),
          pos_y: Math.max(20, window.innerHeight / 2 - NOTE_DEFAULT_H / 2),
          color: '#fef3c7',
          width: NOTE_DEFAULT_W,
          height: NOTE_DEFAULT_H,
          minimizada: 0,
        };
        const res = await fetch('/api/notas', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        if (!res.ok) return;
        const { id } = await res.json();
        renderNote({ id, ...body });
        focusNoteWindow(id);
        const ta = document.querySelector(`#note-${id} textarea`);
        if (ta) ta.focus();
      } catch (e) { console.error('Error creating note:', e); }
    }

    function renderNote(note) {
      const el = document.createElement('div');
      el.className = 'floating-note';
      el.id = `note-${note.id}`;
      el.dataset.noteId = String(note.id);
      const w = Math.max(NOTE_MIN_W, Number(note.width) || NOTE_DEFAULT_W);
      const h = Math.max(NOTE_MIN_H, Number(note.height) || NOTE_DEFAULT_H);
      el.style.left = `${note.pos_x ?? 100}px`;
      el.style.top = `${note.pos_y ?? 100}px`;
      el.style.width = `${w}px`;
      el.style.height = `${h}px`;
      if (note.minimizada) el.classList.add('minimized');

      const colors = ['#fef3c7', '#dcfce7', '#dbeafe', '#fce7f3', '#f3f4f6'];
      const colorBtns = colors.map(c =>
        `<button type="button" class="note-color-btn" data-color="${c}" style="background:${c};" title="Color"></button>`
      ).join('');

      el.innerHTML = `
        <div class="note-glass" aria-hidden="true"></div>
        <div class="note-header">
          <div class="note-colors">${colorBtns}</div>
          <div class="note-win-btns">
            <button type="button" class="note-win-btn note-min-btn" title="Minimizar">${icon('minus', 13)}</button>
            <button type="button" class="note-win-btn note-del-btn" title="Cerrar">${icon('x', 13)}</button>
          </div>
        </div>
        <textarea class="note-textarea" placeholder="Escribe una nota..."></textarea>
        <div class="note-resize" title="Redimensionar"></div>
      `;
      el.querySelector('textarea').value = note.texto || '';
      applyNoteColor(el, note.color || '#fef3c7');

      const header = el.querySelector('.note-header');
      header.addEventListener('mousedown', e => startDrag(e, note.id));
      header.addEventListener('touchstart', e => startDrag(e, note.id), { passive: false });

      el.querySelectorAll('.note-color-btn').forEach(btn => {
        btn.addEventListener('mousedown', e => e.stopPropagation());
        btn.addEventListener('click', e => {
          e.preventDefault();
          e.stopPropagation();
          changeNoteColor(note.id, btn.dataset.color);
        });
      });
      el.querySelector('.note-min-btn').addEventListener('mousedown', e => e.stopPropagation());
      el.querySelector('.note-min-btn').addEventListener('click', e => {
        e.preventDefault(); e.stopPropagation(); minimizeNote(note.id);
      });
      el.querySelector('.note-del-btn').addEventListener('mousedown', e => e.stopPropagation());
      el.querySelector('.note-del-btn').addEventListener('click', e => {
        e.preventDefault(); e.stopPropagation(); deleteNote(note.id);
      });
      const resize = el.querySelector('.note-resize');
      resize.addEventListener('mousedown', e => startResize(e, note.id));
      resize.addEventListener('touchstart', e => startResize(e, note.id), { passive: false });

      const ta = el.querySelector('textarea');
      ta.addEventListener('input', () => handleNoteInput(note.id, ta));
      ta.addEventListener('focus', () => focusNoteWindow(note.id));

      el.addEventListener('mousedown', () => focusNoteWindow(note.id));
      document.body.appendChild(el);
    }

    function removeEmojis(text) {
      return text.replace(/[\p{Emoji_Presentation}\p{Extended_Pictographic}]/gu, '');
    }

    function handleNoteInput(id, textarea) {
      const orig = textarea.value;
      const clean = removeEmojis(orig);
      if (orig !== clean) textarea.value = clean;
      debounceUpdateNote(id);
      const el = document.getElementById(`note-${id}`);
      if (el?.classList.contains('minimized')) refreshNotesTaskbar();
    }

    function changeNoteColor(id, color) {
      const el = document.getElementById(`note-${id}`);
      if (!el) return;
      applyNoteColor(el, color);
      debounceUpdateNote(id);
      refreshNotesTaskbar();
    }

    function minimizeNote(id) {
      const el = document.getElementById(`note-${id}`);
      if (!el || el.classList.contains('minimized')) return;
      el.classList.add('minimized');
      el.classList.remove('note-active');
      refreshNotesTaskbar();
      debounceUpdateNote(id);
    }

    function restoreNote(id) {
      const el = document.getElementById(`note-${id}`);
      if (!el) return;
      el.classList.remove('minimized');
      focusNoteWindow(id);
      refreshNotesTaskbar();
      debounceUpdateNote(id);
      const ta = el.querySelector('textarea');
      if (ta) ta.focus();
    }

    async function deleteNote(id) {
      document.getElementById(`note-${id}`)?.remove();
      refreshNotesTaskbar();
      try {
        await fetch(`/api/notas/${id}`, { method: 'DELETE' });
      } catch (e) { console.error('Error deleting note:', e); }
    }

    function debounceUpdateNote(id) {
      if (_notesTimeout[id]) clearTimeout(_notesTimeout[id]);
      _notesTimeout[id] = setTimeout(() => updateNote(id), 500);
    }

    async function updateNote(id) {
      const el = document.getElementById(`note-${id}`);
      if (!el) return;
      const texto = el.querySelector('textarea')?.value || '';
      const pos_x = parseFloat(el.style.left) || 0;
      const pos_y = parseFloat(el.style.top) || 0;
      const color = el.dataset.noteColor || rgbToHex(el.style.backgroundColor || '#fef3c7');
      const width = parseFloat(el.style.width) || NOTE_DEFAULT_W;
      const height = parseFloat(el.style.height) || NOTE_DEFAULT_H;
      const minimizada = el.classList.contains('minimized') ? 1 : 0;

      try {
        await fetch(`/api/notas/${id}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ texto, pos_x, pos_y, color, width, height, minimizada })
        });
      } catch (e) { console.error('Error updating note:', e); }
    }

    let _dragNoteId = null;
    let _dragOffsetX = 0;
    let _dragOffsetY = 0;
    let _resizeNoteId = null;
    let _resizeStartX = 0;
    let _resizeStartY = 0;
    let _resizeStartW = 0;
    let _resizeStartH = 0;

    function startDrag(e, id) {
      if (e.target.closest('button') || e.target.closest('.note-resize')) return;
      e.preventDefault();
      _resizeNoteId = null;
      focusNoteWindow(id);
      _dragNoteId = id;
      const el = document.getElementById(`note-${id}`);
      const rect = el.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      _dragOffsetX = clientX - rect.left;
      _dragOffsetY = clientY - rect.top;
    }

    function startResize(e, id) {
      e.preventDefault();
      e.stopPropagation();
      _dragNoteId = null;
      focusNoteWindow(id);
      _resizeNoteId = id;
      const el = document.getElementById(`note-${id}`);
      _resizeStartX = e.touches ? e.touches[0].clientX : e.clientX;
      _resizeStartY = e.touches ? e.touches[0].clientY : e.clientY;
      _resizeStartW = el.offsetWidth;
      _resizeStartH = el.offsetHeight;
    }

    function onDragMove(e) {
      if (_resizeNoteId) {
        const el = document.getElementById(`note-${_resizeNoteId}`);
        if (!el) return;
        if (e.cancelable) e.preventDefault();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        const left = parseFloat(el.style.left) || 0;
        const top = parseFloat(el.style.top) || 0;
        let w = _resizeStartW + (clientX - _resizeStartX);
        let h = _resizeStartH + (clientY - _resizeStartY);
        w = Math.max(NOTE_MIN_W, Math.min(window.innerWidth - left, w));
        h = Math.max(NOTE_MIN_H, Math.min(window.innerHeight - top, h));
        el.style.width = `${w}px`;
        el.style.height = `${h}px`;
        return;
      }
      if (!_dragNoteId) return;
      const el = document.getElementById(`note-${_dragNoteId}`);
      if (!el) return;
      if (e.cancelable) e.preventDefault();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;

      let x = clientX - _dragOffsetX;
      let y = clientY - _dragOffsetY;

      x = Math.max(0, Math.min(window.innerWidth - el.offsetWidth, x));
      y = Math.max(0, Math.min(window.innerHeight - el.offsetHeight, y));

      el.style.left = `${x}px`;
      el.style.top = `${y}px`;
    }

    function onDragEnd() {
      if (_resizeNoteId) {
        debounceUpdateNote(_resizeNoteId);
        _resizeNoteId = null;
        return;
      }
      if (_dragNoteId) {
        debounceUpdateNote(_dragNoteId);
        _dragNoteId = null;
      }
    }

    document.addEventListener('mousemove', onDragMove);
    document.addEventListener('mouseup', onDragEnd);
    document.addEventListener('touchmove', onDragMove, { passive: false });
    document.addEventListener('touchend', onDragEnd);

    window.changeNoteColor = changeNoteColor;
    window.minimizeNote = minimizeNote;
    window.restoreNote = restoreNote;
    window.deleteNote = deleteNote;
    window.createNote = createNote;
    window.startDrag = startDrag;
    window.startResize = startResize;

    window.addEventListener('load', loadNotes);
