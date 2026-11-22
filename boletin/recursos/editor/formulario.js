/* ==========================================================================
   Formulario del boletín.
   Mantiene un objeto `datos` sincronizado con los campos y lo envía a Python
   (puente QWebChannel) cada vez que algo cambia, para refrescar la vista previa.
   ========================================================================== */
(function () {
  'use strict';

  var datos = null;          // estado completo del boletín
  var puente = null;         // objeto Python expuesto por QWebChannel
  var cargando = false;      // evita notificar cambios mientras se llena el formulario
  var temporizador = null;
  var editores = [];         // [{editor, leer(), escribir(html)}]
  var COLORES = ['#1a7224', '#215e9a', '#f29e05'];
  var MAX_IMAGEN = 1600;     // px del lado mayor; las fotos más grandes se reducen

  // ------------------------------------------------------------------ utilidades
  function $(sel, raiz) { return (raiz || document).querySelector(sel); }
  function $$(sel, raiz) { return Array.prototype.slice.call((raiz || document).querySelectorAll(sel)); }

  function leer(ruta) {
    return ruta.split('.').reduce(function (o, k) { return o == null ? undefined : o[k]; }, datos);
  }
  function escribir(ruta, valor) {
    var partes = ruta.split('.'), ultimo = partes.pop();
    var o = partes.reduce(function (x, k) { return x[k]; }, datos);
    o[ultimo] = valor;
  }

  function notificar() {
    if (cargando || !datos) return;
    clearTimeout(temporizador);
    temporizador = setTimeout(enviar, 350);
  }
  function enviar() {
    clearTimeout(temporizador);
    volcarEditores();
    var json = JSON.stringify(datos);
    window.__ultimo = json;
    if (puente) puente.cambio(json);
  }

  // Reduce una imagen grande y la devuelve como data-URI (JPEG, o PNG si tiene transparencia).
  function reducirImagen(archivo) {
    return new Promise(function (ok, error) {
      var lector = new FileReader();
      lector.onerror = error;
      lector.onload = function () {
        var img = new Image();
        img.onerror = function () { ok(lector.result); };
        img.onload = function () {
          var escala = Math.min(1, MAX_IMAGEN / Math.max(img.naturalWidth, img.naturalHeight));
          var pequena = archivo.size < 400 * 1024;
          if (escala === 1 && pequena) { ok(lector.result); return; }
          var c = document.createElement('canvas');
          c.width = Math.round(img.naturalWidth * escala);
          c.height = Math.round(img.naturalHeight * escala);
          c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
          var png = /png|gif|webp|svg/i.test(archivo.type);
          ok(png ? c.toDataURL('image/png') : c.toDataURL('image/jpeg', 0.88));
        };
        img.src = lector.result;
      };
      lector.readAsDataURL(archivo);
    });
  }

  function dataUriAArchivo(uri, nombre) {
    var partes = uri.split(','), tipo = /data:([^;]+)/.exec(partes[0])[1];
    var bin = atob(partes[1]), n = bin.length, bytes = new Uint8Array(n);
    while (n--) bytes[n] = bin.charCodeAt(n);
    return new File([bytes], nombre, { type: tipo });
  }

  // ------------------------------------------------------------------ editor de texto enriquecido
  function crearEditor(textarea, valor, alCambiar) {
    textarea.value = valor || '';
    var ed = SUNEDITOR.create(textarea, {
      lang: (window.SUNEDITOR_LANG || {}).es,
      width: '100%',
      height: 'auto',
      minHeight: '110px',
      maxHeight: '520px',
      defaultTag: 'p',
      fontSize: [9, 10, 11, 12, 14, 16, 18, 20, 24, 28],
      fontSizeUnit: 'pt',
      formats: ['p', 'h2', 'h3', 'h4', 'blockquote'],
      imageFileInput: true,
      imageUrlInput: false,
      imageWidth: '320px',
      imageResizing: true,
      imageHeightShow: false,
      tableCellControllerPosition: 'top',
      resizingBar: false,
      showPathLabel: false,
      plugins: window.pluginEmoji ? [window.pluginEmoji] : [],
      buttonList: [
        ['undo', 'redo'],
        ['formatBlock', 'fontSize'],
        ['bold', 'italic', 'underline', 'strike'],
        ['fontColor', 'hiliteColor', 'removeFormat'],
        ['emoji'],
        ['align', 'list', 'outdent', 'indent'],
        ['table', 'image', 'link', 'horizontalRule'],
        ['codeView']
      ]
    });
    ed.onChange = function (contenido) { alCambiar(contenido); notificar(); };
    ed.onImageUploadBefore = function (archivos, info, core, continuar) {
      Promise.all(Array.prototype.map.call(archivos, function (f) {
        return reducirImagen(f).then(function (uri) { return dataUriAArchivo(uri, f.name); });
      })).then(function (lista) { continuar(lista); }, function () { continuar(); });
    };
    var registro = {
      editor: ed,
      volcar: function () { alCambiar(ed.getContents(true)); }
    };
    editores.push(registro);
    return registro;
  }

  function destruirEditores(raiz) {
    editores = editores.filter(function (r) {
      var dentro = raiz.contains(r.editor.core.context.element.topArea);
      if (dentro) { try { r.editor.destroy(); } catch (e) { /* ya no existe */ } }
      return !dentro;
    });
  }

  function volcarEditores() {
    editores.forEach(function (r) { try { r.volcar(); } catch (e) { /* editor destruido */ } });
  }

  // ------------------------------------------------------------------ campos simples
  function enlazarCampos() {
    $$('[data-campo]').forEach(function (el) {
      var ruta = el.dataset.campo;
      var evento = (el.type === 'checkbox' || el.tagName === 'SELECT' || el.type === 'date') ? 'change' : 'input';
      el.addEventListener(evento, function () {
        var v = el.type === 'checkbox' ? el.checked : (el.type === 'number' ? Number(el.value) : el.value);
        escribir(ruta, v);
        if (ruta === 'semana.inicio') autocompletarFin();
        visibilidad();
        notificar();
      });
    });
  }

  // Al elegir el lunes, propone el viernes de esa semana.
  function autocompletarFin() {
    var ini = datos.semana.inicio;
    if (!ini) return;
    var f = new Date(ini + 'T12:00:00');
    f.setDate(f.getDate() + 4);
    datos.semana.fin = f.toISOString().slice(0, 10);
    $('[data-campo="semana.fin"]').value = datos.semana.fin;
  }

  function llenarCampos() {
    $$('[data-campo]').forEach(function (el) {
      var v = leer(el.dataset.campo);
      if (el.type === 'checkbox') el.checked = !!v;
      else el.value = v == null ? '' : v;
    });
    visibilidad();
  }

  function visibilidad() {
    $$('[data-visible-si-no]').forEach(function (el) {
      el.classList.toggle('oculto', !!leer(el.dataset.visibleSiNo));
    });
  }

  // ------------------------------------------------------------------ imágenes sueltas (mensaje y mapa)
  var destinoImagen = null;

  function pintarImagen(caja) {
    var uri = leer(caja.dataset.imagen), vista = $('.imagen-vista', caja);
    vista.style.backgroundImage = uri ? 'url("' + uri + '")' : '';
    vista.classList.toggle('llena', !!uri);
  }

  function enlazarImagenes() {
    var selector = $('#selector-imagen');
    $$('[data-imagen]').forEach(function (caja) {
      $('.elegir', caja).addEventListener('click', function () { destinoImagen = caja; selector.value = ''; selector.click(); });
      $('.quitar', caja).addEventListener('click', function () {
        escribir(caja.dataset.imagen, ''); pintarImagen(caja); notificar();
      });
    });
    selector.addEventListener('change', function () {
      if (!selector.files.length || !destinoImagen) return;
      var caja = destinoImagen;
      reducirImagen(selector.files[0]).then(function (uri) {
        escribir(caja.dataset.imagen, uri); pintarImagen(caja); notificar();
      });
    });
  }

  // ------------------------------------------------------------------ docentes
  function pintarDocentes() {
    var cuerpo = $('#docentes tbody');
    cuerpo.innerHTML = '';
    datos.acompanamiento.docentes.forEach(function (doc, i) {
      var tr = document.createElement('tr');
      tr.innerHTML = '<td><input type="text" class="nombre"></td>' +
                     '<td class="zona"><input type="text" class="z"></td>' +
                     '<td><button type="button" class="icono" title="Quitar">✕</button></td>';
      var nombre = $('.nombre', tr), zona = $('.z', tr);
      nombre.value = doc.nombre || ''; zona.value = doc.zona || '';
      nombre.addEventListener('input', function () { doc.nombre = nombre.value; notificar(); });
      zona.addEventListener('input', function () { doc.zona = zona.value; notificar(); });
      $('button', tr).addEventListener('click', function () {
        datos.acompanamiento.docentes.splice(i, 1); pintarDocentes(); notificar();
      });
      cuerpo.appendChild(tr);
    });
  }

  function enlazarDocentes() {
    $('#docente-nuevo').addEventListener('click', function () {
      datos.acompanamiento.docentes.push({ nombre: '', zona: '' });
      pintarDocentes();
      var filas = $$('#docentes .nombre'); filas[filas.length - 1].focus();
      notificar();
    });
    $('#zonas-limpiar').addEventListener('click', function () {
      datos.acompanamiento.docentes.forEach(function (d) { d.zona = ''; });
      pintarDocentes(); notificar();
    });
    $('#zonas-rotar').addEventListener('click', function () {
      var lista = datos.acompanamiento.docentes, zonas = lista.map(function (d) { return d.zona; });
      zonas.unshift(zonas.pop());
      lista.forEach(function (d, i) { d.zona = zonas[i]; });
      pintarDocentes(); notificar();
    });
  }

  // ------------------------------------------------------------------ días de la agenda
  function pintarDias() {
    var cont = $('#dias');
    destruirEditores(cont);
    cont.innerHTML = '';
    var visibles = 0;
    datos.agenda.dias.forEach(function (dia) {
      var t = document.createElement('div');
      t.className = 'tarjeta' + (dia.mostrar ? '' : ' apagada');
      t.style.setProperty('--c', COLORES[visibles % COLORES.length]);
      if (dia.mostrar) visibles++;
      t.innerHTML = '<div class="tarjeta-cab"><input type="text">' +
                    '<label class="interruptor"><input type="checkbox"> Incluir</label></div>' +
                    '<div class="tarjeta-cuerpo"><textarea></textarea></div>';
      var nombre = $('input[type=text]', t), check = $('input[type=checkbox]', t);
      nombre.value = dia.nombre; check.checked = !!dia.mostrar;
      nombre.addEventListener('input', function () { dia.nombre = nombre.value; notificar(); });
      check.addEventListener('change', function () {
        volcarEditores(); dia.mostrar = check.checked; pintarDias(); notificar();
      });
      cont.appendChild(t);
      crearEditor($('textarea', t), dia.html, function (html) { dia.html = html; });
    });
  }

  // ------------------------------------------------------------------ secciones extra
  function pintarExtras() {
    var cont = $('#extras');
    destruirEditores(cont);
    cont.innerHTML = '';
    datos.extras.forEach(function (extra, i) {
      var t = document.createElement('div');
      t.className = 'tarjeta';
      t.innerHTML = '<div class="tarjeta-cab"><input type="text" placeholder="Título de la sección">' +
                    '<label class="interruptor"><input type="checkbox"> Hoja nueva</label>' +
                    '<button type="button" class="icono" title="Eliminar sección">✕</button></div>' +
                    '<div class="tarjeta-cuerpo"><textarea></textarea></div>';
      var titulo = $('input[type=text]', t), salto = $('input[type=checkbox]', t);
      titulo.value = extra.titulo || ''; salto.checked = !!extra.salto;
      titulo.addEventListener('input', function () { extra.titulo = titulo.value; notificar(); });
      salto.addEventListener('change', function () { extra.salto = salto.checked; notificar(); });
      $('button', t).addEventListener('click', function () {
        volcarEditores(); datos.extras.splice(i, 1); pintarExtras(); notificar();
      });
      cont.appendChild(t);
      crearEditor($('textarea', t), extra.html, function (html) { extra.html = html; });
    });
  }

  // ------------------------------------------------------------------ carga completa
  var editoresFijos = {};

  function cargarDatos(nuevos) {
    cargando = true;
    datos = nuevos;
    llenarCampos();
    $$('[data-imagen]').forEach(pintarImagen);
    $$('textarea[data-rico]').forEach(function (ta) {
      var ruta = ta.dataset.rico;
      if (editoresFijos[ruta]) {
        editoresFijos[ruta].editor.setContents(leer(ruta) || '');
      } else {
        editoresFijos[ruta] = crearEditor(ta, leer(ruta), function (html) { escribir(ruta, html); });
      }
    });
    pintarDocentes();
    pintarDias();
    pintarExtras();
    // SunEditor dispara onChange al inicializarse: se ignora hasta el siguiente ciclo.
    setTimeout(function () { cargando = false; }, 200);
  }

  // ------------------------------------------------------------------ arranque
  function iniciar() {
    $$('#pestanas button').forEach(function (b) {
      b.addEventListener('click', function () {
        $$('#pestanas button').forEach(function (x) { x.classList.toggle('activa', x === b); });
        $$('.panel').forEach(function (p) { p.classList.toggle('activa', p.id === 'panel-' + b.dataset.panel); });
        window.scrollTo(0, 0);
      });
    });
    enlazarCampos();
    enlazarImagenes();
    enlazarDocentes();
    $('#extra-nuevo').addEventListener('click', function () {
      volcarEditores();
      datos.extras.push({ titulo: '', html: '', salto: false });
      pintarExtras(); notificar();
    });

    // API que usa la ventana principal (Python).
    window.boletin = {
      cargar: cargarDatos,
      recolectar: function () { volcarEditores(); return JSON.stringify(datos); }
    };

    if (window.qt && window.qt.webChannelTransport && window.QWebChannel) {
      new QWebChannel(qt.webChannelTransport, function (canal) {
        puente = canal.objects.puente;
        puente.cargar.connect(function (json) { cargarDatos(JSON.parse(json)); });
        puente.formularioListo();
      });
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
  else iniciar();
})();
