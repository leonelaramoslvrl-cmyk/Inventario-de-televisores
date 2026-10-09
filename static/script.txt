(function () {
  const state = { entries: [], editingId: null, dbAvailable: false };

  const $ = (id) => document.getElementById(id);
  const els = {
    room: $('fRoom'),
    micRoom: $('micRoom'),
    ubic: $('fUbic'),
    marca: $('fMarca'),
    instal: $('fInstal'),
    qr: $('fQr'),
    modelo: $('fModelo'),
    serial: $('fSerial'),
    qrPreview: $('qrPreview'),
    btnAdd: $('btnAdd'),
    btnCancelEdit: $('btnCancelEdit'),
    qrPhoto: $('fQrPhoto'),
    qrPhotoStatus: $('qrPhotoStatus'),
    btnOpenCamera: $('btnOpenCamera'),
    cameraOverlay: $('cameraOverlay'),
    cameraVideo: $('cameraVideo'),
    cameraStatus: $('cameraStatus'),
    btnCloseCamera: $('btnCloseCamera'),
    footerCount: $('footerCount'),
    btnExport: $('btnExport'),
    search: $('fSearch'),
    toast: $('toast'),
    banner: $('dbBanner'),
    perifSeg: $('perifSeg'),
    floorSearch: $('fFloorSearch'),
    btnOpenMenu: $('btnOpenMenu'),
    btnCloseMenu: $('btnCloseMenu'),
    floorDrawer: $('floorDrawer'),
    floorBackdrop: $('floorBackdrop'),
    floorList: $('floorList')
  };

  let perifValue = null;

  if (els.micRoom) {
    els.micRoom.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>';
  }

  function showToast(msg) {
    if (!els.toast) return;
    els.toast.textContent = msg;
    els.toast.classList.add('show');
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => els.toast.classList.remove('show'), 2400);
  }

  // ---------- Dictado por voz (Web Speech API) ----------
  const SpeechRecognitionImpl = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognitionImpl && els.micRoom && els.room) {
    const rec = new SpeechRecognitionImpl();
    rec.lang = 'es-ES';
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    let listening = false;

    rec.onresult = (e) => {
      const text = e.results[0][0].transcript;
      const digits = text.replace(/\D+/g, '');
      els.room.value = digits || text.trim();
      validate();
    };

    rec.onend = () => { listening = false; els.micRoom.classList.remove('listening'); };
    rec.onerror = () => { listening = false; els.micRoom.classList.remove('listening'); showToast('No se pudo escuchar. Intenta de nuevo.'); };

    els.micRoom.addEventListener('click', () => {
      if (listening) { rec.stop(); return; }
      try {
        rec.start();
        listening = true;
        els.micRoom.classList.add('listening');
      } catch (err) {
        showToast('El dictado no está disponible ahora mismo.');
      }
    });
  } else if (els.micRoom) {
    els.micRoom.style.display = 'none';
  }

  // ---------- Control Segmentado: Periféricos ----------
  if (els.perifSeg) {
    els.perifSeg.querySelectorAll('.segBtn').forEach(btn => {
      btn.addEventListener('click', () => {
        perifValue = btn.dataset.val;
        els.perifSeg.querySelectorAll('.segBtn').forEach(b => b.classList.toggle('active', b === btn));
      });
    });
  }

  // ---------- Lectura y procesamiento de QR ----------
  function parseQr(text) {
    const mn = text.match(/\bMN\s*:\s*([^\s]+)/i) || text.match(/\bMODEL\s*:\s*([^\s]+)/i);
    const sn = text.match(/\bSN\s*:\s*([^\s]+)/i) || text.match(/\bSERIAL\s*:\s*([^\s]+)/i);
    return {
      modelo: mn ? mn[1].trim() : '',
      serial: sn ? sn[1].trim() : ''
    };
  }

  function applyQrText(text) {
    if (els.qr) els.qr.value = text;
    updateQrPreviewFromText(text);
  }

  function updateQrPreviewFromText(text) {
    if (!els.qrPreview) return;
    if (!text.trim()) { 
      els.qrPreview.classList.remove('show', 'warn'); 
      return; 
    }
    const { modelo, serial } = parseQr(text);
    if (modelo && els.modelo) els.modelo.value = modelo;
    if (serial && els.serial) els.serial.value = serial;
    
    els.qrPreview.classList.add('show');
    if (modelo || serial) {
      els.qrPreview.classList.remove('warn');
      els.qrPreview.innerHTML = 'Detectado — Modelo: <b>' + (modelo || '—') + '</b> · Serial: <b>' + (serial || '—') + '</b>';
    } else {
      els.qrPreview.classList.add('warn');
      els.qrPreview.innerHTML = '<b>No encontré "MN" ni "SN"</b> en ese texto. Completa Modelo y Serial manualmente.';
    }
    validate();
  }

  if (els.qr) els.qr.addEventListener('input', () => updateQrPreviewFromText(els.qr.value));

  // ---------- Escáner de cámara en directo usando ZXing ----------
  let codeReader = null; 
  let isScanning = false;

  function setPhotoStatus(msg, warn) {
    if (!els.qrPhotoStatus) return;
    els.qrPhotoStatus.classList.add('show');
    els.qrPhotoStatus.classList.toggle('warn', !!warn);
    els.qrPhotoStatus.textContent = msg;
  }

  function stopCamera() {
    isScanning = false;
    if (codeReader) {
      try {
        codeReader.reset();
      } catch (e) {}
    }
    if (els.cameraVideo) {
      els.cameraVideo.srcObject = null;
    }
    if (els.cameraOverlay) {
      els.cameraOverlay.classList.remove('show');
    }
  }

  function openCamera() {
    if (typeof ZXing === 'undefined') {
      showToast('Cargando librería del escáner... Intenta en un segundo.');
      return;
    }

    if (!codeReader) {
      codeReader = new ZXing.BrowserMultiFormatReader();
    }

    if (els.cameraOverlay) els.cameraOverlay.classList.add('show');
    if (els.cameraStatus) els.cameraStatus.textContent = 'Buscando el código QR…';
    if (els.cameraVideo) els.cameraVideo.setAttribute('playsinline', 'true');

    isScanning = true;

    codeReader.decodeFromConstraints(
      { video: { facingMode: { ideal: 'environment' } } },
      els.cameraVideo,
      (result, err) => {
        if (!isScanning) return;
        
        if (result) {
          const decodedText = result.getText();
          applyQrText(decodedText);
          setPhotoStatus('Código QR leído con la cámara ✓', false);
          
          if (navigator.vibrate) {
            navigator.vibrate(200);
          }

          stopCamera();
          showToast('Código QR leído correctamente.');
        }
      }
    ).catch(err => {
      stopCamera();
      if (err && (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError')) {
        showToast('No se concedió permiso para usar la cámara.');
      } else if (err && err.name === 'NotFoundError') {
        showToast('No se encontró una cámara en este dispositivo.');
      } else {
        showToast('No se pudo abrir la cámara.');
      }
    });
  }

  if (els.btnOpenCamera) els.btnOpenCamera.addEventListener('click', openCamera);
  if (els.btnCloseCamera) els.btnCloseCamera.addEventListener('click', stopCamera);

  // ---------- Decodificación de archivos de imagen subidos (Fallback) ----------
  if (els.qrPhoto) {
    els.qrPhoto.addEventListener('change', async () => {
      const file = els.qrPhoto.files && els.qrPhoto.files[0];
      if (!file) return;

      if (typeof ZXing === 'undefined') {
        setPhotoStatus('Cargando librería del escáner...', true);
        return;
      }

      if (!codeReader) {
        codeReader = new ZXing.BrowserMultiFormatReader();
      }

      setPhotoStatus('Leyendo el código QR de la foto...', false);
      
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          const img = new Image();
          img.src = reader.result;
          img.onload = async () => {
            try {
              const result = await codeReader.decodeFromImageElement(img);
              if (result && result.getText()) {
                applyQrText(result.getText());
                setPhotoStatus('Código QR leído correctamente ✓', false);
              } else {
                setPhotoStatus('No pude leer un código QR en esa foto.', true);
              }
            } catch (e) {
              setPhotoStatus('No se encontró un código QR válido en la imagen.', true);
            }
          };
        } catch (err) {
          setPhotoStatus('Error al procesar la imagen.', true);
        }
      };
      reader.readAsDataURL(file);
    });
  }

  // ---------- Validación y auxiliares del formulario ----------
  function validate() {
    if (!els.room || !els.modelo || !els.serial || !els.btnAdd) return;
    const ok = els.room.value.trim() && els.modelo.value.trim() && els.serial.value.trim();
    els.btnAdd.disabled = !ok;
    const btnAnother = $('btnAddAnother');
    if (btnAnother) btnAnother.disabled = !ok;
  }

  [els.room, els.modelo, els.serial].forEach(el => {
    if (el) el.addEventListener('input', validate);
  });

  const NO_SERIAL_TEXT = 'No lo muestra';
  const btnSerialHidden = $('btnSerialHidden');

  function syncSerialHiddenBtn() {
    if (!btnSerialHidden || !els.serial) return;
    btnSerialHidden.classList.toggle('active', els.serial.value.trim() === NO_SERIAL_TEXT);
  }

  if (btnSerialHidden && els.serial) {
    btnSerialHidden.addEventListener('click', () => {
      els.serial.value = (els.serial.value.trim() === NO_SERIAL_TEXT) ? '' : NO_SERIAL_TEXT;
      syncSerialHiddenBtn();
      validate();
    });
    els.serial.addEventListener('input', syncSerialHiddenBtn);
  }

  function resetForm(keepRoom) {
    if (!keepRoom) {
      if (els.room) els.room.value = '';
      if (els.ubic) els.ubic.value = 'Habitación';
      if (els.marca) els.marca.value = 'Samsung';
      if (els.instal) els.instal.value = 'Base fija';
    }
    if (els.qr) els.qr.value = '';
    if (els.modelo) els.modelo.value = '';
    if (els.serial) els.serial.value = '';
    if (els.qrPreview) els.qrPreview.classList.remove('show', 'warn');
    if (els.qrPhoto) els.qrPhoto.value = '';
    if (els.qrPhotoStatus) {
      els.qrPhotoStatus.classList.remove('show', 'warn');
      els.qrPhotoStatus.textContent = '';
    }
    perifValue = null;
    if (els.perifSeg) els.perifSeg.querySelectorAll('.segBtn').forEach(b => b.classList.remove('active'));
    state.editingId = null;
    if (els.btnAdd) els.btnAdd.textContent = 'Agregar registro';
    if (els.btnCancelEdit) els.btnCancelEdit.style.display = 'none';
    const btnAnother = $('btnAddAnother');
    if (btnAnother) btnAnother.style.display = 'block';
    
    syncSerialHiddenBtn();
    validate();
    
    if (keepRoom && els.modelo) {
      els.modelo.focus({ preventScroll: true });
    }
  }

  // ---------- Clasificación por Torres y Pisos ----------
  const FLOOR_LABELS = ['Piso 1', 'Piso 2', 'Piso 3', 'Piso 4', 'Piso 5', 'Piso 6', 'Piso 7', 'Piso 8', 'Piso 9', 'Piso 10', 'Piso 11', 'Mezz 1', 'Mezz 2'];
  const TOWER_ORDER = ['Hotel', 'Suite', 'Otro'];

  function getTowerFloor(roomRaw) {
    const room = String(roomRaw).trim().toUpperCase();
    const n = parseInt(room, 10);
    if (isNaN(n) || !/^\d+$/.test(room)) return { tower: 'Otro', floor: 'Otro' };
    if (n >= 6051 && n <= 6069) return { tower: 'Suite', floor: 'Mezz 1' };
    if (n >= 6151 && n <= 6170) return { tower: 'Suite', floor: 'Mezz 2' };
    if (n >= 100 && n < 1200) {
      const floorNum = Math.floor(n / 100);
      const remainder = n % 100;
      if (floorNum >= 1 && floorNum <= 11) {
        return { tower: remainder <= 50 ? 'Hotel' : 'Suite', floor: 'Piso ' + floorNum };
      }
    }
    return { tower: 'Otro', floor: 'Otro' };
  }

  function floorKeyOf(room) {
    const { tower, floor } = getTowerFloor(room);
    return tower + '::' + floor;
  }

  function floorLabelOf(room) {
    const { tower, floor } = getTowerFloor(room);
    if (tower === 'Otro') return 'Otro';
    return 'Torre ' + tower + ' · ' + floor;
  }

  function openFloorMenu() {
    renderFloorList();
    if (els.floorDrawer) els.floorDrawer.classList.add('show');
    if (els.floorBackdrop) els.floorBackdrop.classList.add('show');
  }

  function closeFloorMenu() {
    if (els.floorDrawer) els.floorDrawer.classList.remove('show');
    if (els.floorBackdrop) els.floorBackdrop.classList.remove('show');
  }

  if (els.btnOpenMenu) els.btnOpenMenu.addEventListener('click', openFloorMenu);
  if (els.btnCloseMenu) els.btnCloseMenu.addEventListener('click', closeFloorMenu);
  if (els.floorBackdrop) els.floorBackdrop.addEventListener('click', closeFloorMenu);

  function renderFloorList() {
    const counts = {};
    state.entries.forEach(e => {
      const key = floorKeyOf(e.room);
      counts[key] = (counts[key] || 0) + 1;
    });

    if ($('allCount')) $('allCount').textContent = state.entries.length;
    const wrap = $('floorItemsWrap');
    if (!wrap) return;

    let html = '';
    TOWER_ORDER.forEach(tower => {
      if (tower === 'Otro') return;
      const floorsPresent = FLOOR_LABELS.filter(f => counts[tower + '::' + f]);
      if (!floorsPresent.length) return;
      html += '<div class="floorGroupLabel">Torre ' + tower + '</div>';
      html += floorsPresent.map(f => {
        const key = tower + '::' + f;
        return '<button type="button" class="floorItem" data-key="' + key + '">' +
          '<span>' + f + '</span><span class="n">' + counts[key] + '</span></button>';
      }).join('');
    });

    if (counts['Otro::Otro']) {
      html += '<div class="floorGroupLabel">Otros</div>';
      html += '<button type="button" class="floorItem" data-key="Otro::Otro">' +
        '<span>Sin piso identificado</span><span class="n">' + counts['Otro::Otro'] + '</span></button>';
    }

    wrap.innerHTML = html || '<div class="floorGroupLabel" style="padding-left:12px;">Aún no hay registros para agrupar.</div>';
    wrap.querySelectorAll('.floorItem').forEach(btn => {
      btn.addEventListener('click', () => {
        closeFloorMenu();
        openFloorPage(btn.dataset.key);
      });
    });
  }

  if ($('btnOpenAll')) {
    $('btnOpenAll').addEventListener('click', () => {
      closeFloorMenu();
      openAllPage();
    });
  }

  // ---------- Control de pantallas / vistas ----------
  const screenEls = { floorPage: $('floorPage'), detailPage: $('detailPage'), allPage: $('allPage') };
  let screenStack = [];

  function pushScreen(name) {
    if (!screenEls[name]) return;
    screenEls[name].classList.add('show');
    screenStack.push(name);
    history.pushState({ screen: name, depth: screenStack.length }, '');
  }

  function closeTopScreen() {
    const name = screenStack.pop();
    if (name && screenEls[name]) screenEls[name].classList.remove('show');
  }

  window.addEventListener('popstate', () => {
    if (screenStack.length) closeTopScreen();
  });

  function goBack() {
    if (screenStack.length) history.back();
  }

  function closeAllScreens() {
    const depth = screenStack.length;
    screenStack.forEach(name => {
      if (screenEls[name]) screenEls[name].classList.remove('show');
    });
    screenStack = [];
    if (depth) history.go(-depth);
  }

  if ($('btnBackFromFloor')) $('btnBackFromFloor').addEventListener('click', goBack);
  if ($('btnBackFromDetail')) $('btnBackFromDetail').addEventListener('click', goBack);
  if ($('btnBackFromAll')) $('btnBackFromAll').addEventListener('click', goBack);

  function normalizeText(v) {
    return String(v == null ? '' : v).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }

  function matchesQuery(e, rawQuery) {
    const q = normalizeText(rawQuery).trim();
    if (!q) return true;
    const haystack = normalizeText([e.room, e.ubicacion, e.marca, e.modelo, e.serial, e.instalacion].join(' '));
    // Todas las palabras escritas deben aparecer (ej. "351 samsung")
    return q.split(/\s+/).every(word => haystack.includes(word));
  }

  function openAllPage() {
    pushScreen('allPage');
    renderAllPage();
    if (els.search) els.search.focus({ preventScroll: true });
  }

  function renderAllPage() {
    const q = els.search ? els.search.value : '';
    const filtered = state.entries.filter(e => matchesQuery(e, q));

    if ($('allPageSub')) {
      $('allPageSub').textContent = state.entries.length + (state.entries.length === 1 ? ' registro' : ' registros');
    }

    const container = $('allPageList');
    if (container) {
      container.innerHTML = filtered.length
        ? tableHtml(filtered)
        : '<div class="empty">' + (state.entries.length ? 'Sin resultados para esa búsqueda.' : 'Todavía no hay registros. Agrega el primero arriba.') + '</div>';
      wireTableEvents(container);
    }
  }

  if (els.search) els.search.addEventListener('input', renderAllPage);

  let currentFloorKey = null;
  function renderFloorPageContent(key) {
    const [tower, floor] = key.split('::');
    const floorItems = state.entries.filter(e => floorKeyOf(e.room) === key);
    const q = els.floorSearch ? els.floorSearch.value : '';
    const items = floorItems.filter(e => matchesQuery(e, q));
    const countText = floorItems.length + (floorItems.length === 1 ? ' registro' : ' registros');
    
    if ($('floorPageTitle')) $('floorPageTitle').textContent = tower === 'Otro' ? 'Sin piso' : floor;
    if ($('floorPageSub')) $('floorPageSub').textContent = tower === 'Otro' ? countText : ('Torre ' + tower + ' · ' + countText);
    
    const container = $('floorPageList');
    if (container) {
      container.innerHTML = items.length
        ? tableHtml(items)
        : '<div class="empty">' + (floorItems.length ? 'Sin resultados para esa búsqueda.' : 'No hay registros en este piso todavía.') + '</div>';
      wireTableEvents(container);
    }
  }

  if (els.floorSearch) els.floorSearch.addEventListener('input', () => {
    if (currentFloorKey) renderFloorPageContent(currentFloorKey);
  });

  function openFloorPage(key) {
    currentFloorKey = key;
    if (els.floorSearch) els.floorSearch.value = '';
    renderFloorPageContent(key);
    pushScreen('floorPage');
  }

  function openDetailPage(id) {
    const e = state.entries.find(x => x.id === id);
    if (!e) return;
    
    if ($('detailRoomTitle')) $('detailRoomTitle').textContent = e.room;
    if ($('detailSub')) $('detailSub').textContent = floorLabelOf(e.room) + ' · ' + (e.ubicacion || '—');
    
    const container = $('detailContent');
    if (container) {
      container.innerHTML =
        '<div class="detailGrid">' +
          '<div><div class="k">Marca</div><div class="v">' + escapeHtml(e.marca || '—') + '</div></div>' +
          '<div><div class="k">Tipo de instalación</div><div class="v">' + escapeHtml(e.instalacion || '—') + '</div></div>' +
          '<div class="full"><div class="k">Modelo</div><div class="v">' + escapeHtml(e.modelo || '—') + '</div></div>' +
          '<div class="full"><div class="k">Serial</div><div class="v">' + escapeHtml(e.serial || '—') + '</div></div>' +
          '<div><div class="k">¿Reconoce periféricos?</div><div class="v">' + escapeHtml(e.perifericos || '—') + '</div></div>' +
          '<div><div class="k">Registrado</div><div class="v">' + escapeHtml(formatDateTime(e.createdAt)) + '</div></div>' +
        '</div>' +
        '<button type="button" class="detailEditBtn" id="btnEditFromDetail">Editar este registro</button>';
      
      const editBtn = $('btnEditFromDetail');
      if (editBtn) {
        editBtn.addEventListener('click', () => {
          closeAllScreens();
          editEntry(id);
        });
      }
    }
    pushScreen('detailPage');
  }

  // ---------- Renderizado de listas y tarjetas ----------
  let roomIndexMap = {};
  function refreshRoomIndexMap() {
    const byRoom = {};
    state.entries.forEach(e => { (byRoom[e.room] = byRoom[e.room] || []).push(e); });
    const map = {};
    Object.values(byRoom).forEach(list => {
      if (list.length <= 1) return;
      list.slice().sort((a, b) => (a.createdAt || 0) - (b.createdAt || 0)).forEach((e, i) => {
        map[e.id] = 'TV ' + (i + 1) + '/' + list.length;
      });
    });
    roomIndexMap = map;
  }

  function tableHtml(list) {
    const rows = list.map(e => {
      const perifClass = e.perifericos === 'Sí' ? 'si-perif' : (e.perifericos === 'No' ? 'no-perif' : '');
      const tvBadge = roomIndexMap[e.id] ? '<span class="tvBadge">' + roomIndexMap[e.id] + '</span>' : '';
      return '<tr class="' + perifClass + '" data-id="' + e.id + '">' +
        '<td class="roomCell mono">' + escapeHtml(e.room) + tvBadge + '</td>' +
        '<td>' + escapeHtml(e.ubicacion || '—') + '</td>' +
        '<td>' + escapeHtml(e.marca || '—') + '</td>' +
        '<td class="mono">' + escapeHtml(e.modelo || '—') + '</td>' +
        '<td class="mono">' + escapeHtml(e.serial || '—') + '</td>' +
        '<td>' + escapeHtml(e.perifericos || '—') + '</td>' +
        '<td>' + escapeHtml(e.instalacion || '—') + '</td>' +
        '<td>' + escapeHtml(formatDateTime(e.createdAt)) + '</td>' +
        '<td class="actionsCell">' +
          '<button type="button" class="iconBtn editBtn" title="Editar" aria-label="Editar"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg></button>' +
        '</td>' +
      '</tr>';
    }).join('');

    return '<div class="tableScroll"><table class="recordsTable">' +
      '<thead><tr>' +
        '<th>Hab.</th><th>Ubicación</th><th>Marca</th><th>Modelo</th><th>Serial</th>' +
        '<th>Periféricos</th><th>Instalación</th><th>Registrado</th><th></th>' +
      '</tr></thead>' +
      '<tbody>' + rows + '</tbody>' +
    '</table></div>';
  }

  function wireTableEvents(container) {
    container.querySelectorAll('tbody tr').forEach(row => {
      const id = row.dataset.id;
      const btnEdit = row.querySelector('.editBtn');
      if (btnEdit) {
        btnEdit.addEventListener('click', (ev) => { ev.stopPropagation(); editEntry(id); });
      }
      row.addEventListener('click', () => openDetailPage(id));
    });
  }

  function render() {
    refreshRoomIndexMap();
    if (els.footerCount) {
      els.footerCount.textContent = state.entries.length + (state.entries.length === 1 ? ' TV registrado' : ' TVs registrados');
    }
    if ($('allCount')) $('allCount').textContent = state.entries.length;

    if (screenStack.includes('allPage')) renderAllPage();
    if (screenStack.includes('floorPage') && currentFloorKey) {
      renderFloorPageContent(currentFloorKey);
    }
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  function formatDateTime(ts) {
    if (!ts) return '—';
    const d = new Date(ts);
    if (isNaN(d.getTime())) return '—';
    const datePart = d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
    const timePart = d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    return datePart + ' · ' + timePart;
  }

  function editEntry(id) {
    const e = state.entries.find(x => x.id === id);
    if (!e) return;
    state.editingId = id;
    if (els.room) els.room.value = e.room;
    if (els.ubic) els.ubic.value = e.ubicacion || 'Habitación';
    if (els.marca) els.marca.value = e.marca || 'Samsung';
    if (els.instal) els.instal.value = e.instalacion || 'Base fija';
    if (els.modelo) els.modelo.value = e.modelo || '';
    if (els.serial) els.serial.value = e.serial || '';
    if (els.qr) els.qr.value = '';
    if (els.qrPreview) els.qrPreview.classList.remove('show', 'warn');
    if (els.qrPhoto) els.qrPhoto.value = '';
    if (els.qrPhotoStatus) {
      els.qrPhotoStatus.classList.remove('show', 'warn');
      els.qrPhotoStatus.textContent = '';
    }
    
    perifValue = e.perifericos === 'Sí' ? 'si' : (e.perifericos === 'No' ? 'no' : null);
    if (els.perifSeg) els.perifSeg.querySelectorAll('.segBtn').forEach(b => b.classList.toggle('active', b.dataset.val === perifValue));
    
    if (els.btnAdd) els.btnAdd.textContent = 'Guardar cambios';
    if (els.btnCancelEdit) els.btnCancelEdit.style.display = 'block';
    
    const btnAnother = $('btnAddAnother');
    if (btnAnother) btnAnother.style.display = 'none';
    
    syncSerialHiddenBtn();
    validate();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  if (els.btnCancelEdit) els.btnCancelEdit.addEventListener('click', () => resetForm(false));

  // ---------- Sincronización con el Backend Flask ----------
  const API_BASE = '/api/tvs';
  const POLL_MS = 4000;
  let pollTimer = null;

  function entriesEqual(a, b) {
    if (a.length !== b.length) return false;
    return JSON.stringify(a) === JSON.stringify(b);
  }

  async function fetchEntries(silent) {
    try {
      const res = await fetch(API_BASE);
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      state.dbAvailable = true;
      if (els.banner) els.banner.classList.remove('show');
      if (!entriesEqual(data, state.entries)) {
        state.entries = data;
        render();
      }
    } catch (err) {
      state.dbAvailable = false;
      if (els.banner) {
        els.banner.textContent = 'No se pudo conectar con el servidor. Los cambios locales no se sincronizarán.';
        els.banner.classList.add('show');
      }
      if (!silent) showToast('No se pudo conectar con el servidor.');
    }
  }

  function initDb() {
    fetchEntries(true);
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => fetchEntries(true), POLL_MS);
  }
  initDb();

  async function addOrUpdateEntry(keepRoom) {
    if (!els.room || !els.ubic || !els.marca || !els.instal || !els.modelo || !els.serial) return;
    const data = {
      room: els.room.value.trim(),
      ubicacion: els.ubic.value,
      marca: els.marca.value.trim(),
      instalacion: els.instal.value,
      perifericos: perifValue === 'si' ? 'Sí' : (perifValue === 'no' ? 'No' : ''),
      modelo: els.modelo.value.trim(),
      serial: els.serial.value.trim()
    };
    if (!data.room || !data.modelo || !data.serial) return;

    try {
      if (state.editingId) {
        const res = await fetch(API_BASE + '/' + state.editingId, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const updated = await res.json();
        const idx = state.entries.findIndex(e => e.id === state.editingId);
        if (idx > -1) state.entries[idx] = updated; else state.entries.unshift(updated);
        showToast('Registro actualizado.');
      } else {
        const res = await fetch(API_BASE, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const created = await res.json();
        state.entries.unshift(created);
        showToast(keepRoom ? 'TV agregado. Listo para el siguiente de la habitación ' + data.room + '.' : 'TV agregado a la habitación ' + data.room + '.');
      }
      render();
    } catch (err) {
      showToast('No se pudo guardar. Verifica la conexión con el servidor.');
      return;
    }
    resetForm(keepRoom && !state.editingId);
  }

  if (els.btnAdd) els.btnAdd.addEventListener('click', () => addOrUpdateEntry(false));
  const btnAnother = $('btnAddAnother');
  if (btnAnother) {
    btnAnother.addEventListener('click', () => addOrUpdateEntry(true));
  }

  // ---------- Exportación a Excel ----------
  function downloadCsvFallback(headers, rows) {
    const esc = (v) => '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"';
    // BOM \ufeff para que Excel muestre bien tildes y ñ
    const csv = '\ufeff' + [headers].concat(rows).map(r => r.map(esc).join(',')).join('\r\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Inventario_TVs.csv';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function exportToExcel() {
    if (!state.entries.length) {
      showToast('Todavía no hay registros para exportar.');
      return;
    }
    try {
      const headers = ['Num. Hab.', 'Ubicación', 'Marca', 'Modelo', 'Serial', '¿Reconoce los periféricos?', 'Tipo de instalación', 'Fecha y hora de registro'];
      const rows = state.entries
        .slice()
        .sort((a, b) => (a.createdAt || 0) - (b.createdAt || 0))
        .map(e => [
          e.room,
          e.ubicacion || '',
          e.marca || '',
          e.modelo || '',
          e.serial || '',
          e.perifericos || '',
          e.instalacion || '',
          formatDateTime(e.createdAt)
        ]);

      if (typeof XLSX !== 'undefined') {
        const worksheet = XLSX.utils.aoa_to_sheet([headers].concat(rows));
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, 'Registros_TVs');
        XLSX.writeFile(workbook, 'Inventario_TVs.xlsx');
        showToast('Archivo Excel generado.');
      } else {
        // La librería de Excel se carga desde internet; si no cargó, se baja un CSV que Excel también abre.
        downloadCsvFallback(headers, rows);
        showToast('No cargó la librería de Excel. Se descargó un CSV que puedes abrir con Excel.');
      }
    } catch (err) {
      showToast('Error al intentar exportar.');
    }
  }

  if (els.btnExport) els.btnExport.addEventListener('click', exportToExcel);
  if ($('btnExportMenu')) {
    $('btnExportMenu').addEventListener('click', () => {
      closeFloorMenu();
      exportToExcel();
    });
  }
})();