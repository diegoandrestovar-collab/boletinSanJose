/* ==========================================================================
   Paginación del boletín.
   Toma los bloques de #fuente y los reparte en hojas (.pagina) del tamaño
   configurado. Las tarjetas marcadas como .divisible crecen con su contenido
   y, si no caben, continúan en la hoja siguiente (párrafo a párrafo, viñeta
   a viñeta o fila a fila en las tablas).
   ========================================================================== */
(function () {
  'use strict';

  var fuente = document.getElementById('fuente');
  var paginas = document.getElementById('paginas');
  var area = null;
  var total = 0;

  function plantilla(id) {
    return document.getElementById(id).content.cloneNode(true);
  }

  function nuevaPagina() {
    total += 1;
    var p = document.createElement('div');
    p.className = 'pagina' + (total === 1 ? ' portada' : '');
    p.appendChild(plantilla(total === 1 ? 'tpl-portada' : 'tpl-encabezado'));
    area = document.createElement('div');
    area.className = 'area';
    p.appendChild(area);
    p.appendChild(plantilla('tpl-pie'));
    p.querySelector('.num').textContent = total;
    paginas.appendChild(p);
  }

  function desborda(el) {
    return el.getBoundingClientRect().bottom > area.getBoundingClientRect().bottom + 0.5;
  }

  // ¿El bloque es el primer contenido real de la hoja? (los títulos no cuentan)
  function esPrimero(b) {
    var x = b.previousElementSibling;
    while (x) {
      if (!x.hasAttribute('data-con-siguiente')) return false;
      x = x.previousElementSibling;
    }
    return true;
  }

  function tieneContenido(cuerpo) {
    for (var i = 0; i < cuerpo.childNodes.length; i++) {
      var n = cuerpo.childNodes[i];
      if (n.nodeType === 1 || (n.nodeType === 3 && n.textContent.trim())) return true;
    }
    return false;
  }

  // Envuelve en <p> el texto suelto para poder moverlo como un bloque.
  function normalizar(cuerpo) {
    Array.prototype.slice.call(cuerpo.childNodes).forEach(function (n) {
      if (n.nodeType === 3) {
        if (!n.textContent.trim()) { n.remove(); return; }
        var p = document.createElement('p');
        cuerpo.replaceChild(p, n);
        p.appendChild(n);
      } else if (n.nodeType !== 1) {
        n.remove();
      }
    });
  }

  // Intenta partir un elemento (lista, tabla o contenedor) que no cabe completo.
  // Devuelve la parte que debe pasar a la hoja siguiente, o null si no se pudo.
  function partir(el, bloque) {
    if (el.nodeType !== 1) return null;
    var tag = el.tagName, origen = null, clon, destino;
    if (tag === 'UL' || tag === 'OL') origen = el;
    else if (tag === 'TABLE') origen = el.tBodies[0];
    else if (tag === 'DIV' && !el.classList.contains('se-component')) origen = el;
    if (!origen || origen.children.length < 2) return null;

    clon = el.cloneNode(false);
    destino = clon;
    if (tag === 'TABLE') {
      Array.prototype.forEach.call(el.children, function (h) {
        if (h.tagName === 'COLGROUP' || h.tagName === 'THEAD') clon.appendChild(h.cloneNode(true));
      });
      destino = document.createElement('tbody');
      clon.appendChild(destino);
    }
    while (desborda(bloque) && origen.lastElementChild) {
      destino.insertBefore(origen.lastElementChild, destino.firstChild);
    }
    if (!origen.children.length) {            // no cupo ni el primer elemento: se deshace
      while (destino.firstChild) origen.appendChild(destino.firstChild);
      return null;
    }
    if (tag === 'OL') clon.start = (el.start || 1) + origen.children.length;
    return clon;
  }

  // Divide una tarjeta que no cabe. Devuelve false si conviene pasarla entera a otra hoja.
  function dividir(b) {
    var cuerpo = b.querySelector('.cuerpo');
    if (!cuerpo) return false;
    normalizar(cuerpo);

    var resto = [];
    while (desborda(b) && cuerpo.lastChild) {
      resto.unshift(cuerpo.lastChild);
      cuerpo.removeChild(cuerpo.lastChild);
    }
    if (!resto.length) return !desborda(b);

    // El primer elemento que no cupo quizá sí cabe en parte.
    var primero = resto[0];
    cuerpo.appendChild(primero);
    var parte = partir(primero, b);
    if (parte) resto[0] = parte; else cuerpo.removeChild(primero);

    if (!tieneContenido(cuerpo)) {
      if (!esPrimero(b)) {                    // se devuelve todo y se pasa la tarjeta completa
        resto.forEach(function (n) { cuerpo.appendChild(n); });
        return false;
      }
      cuerpo.appendChild(resto.shift());      // ni en una hoja vacía cabe: se deja y se avisa
      b.classList.add('desbordado');
    }
    if (!resto.length) return true;

    var cont = b.cloneNode(true);
    cont.removeAttribute('data-salto');
    cont.classList.remove('desbordado');
    var cuerpo2 = cont.querySelector('.cuerpo');
    cuerpo2.innerHTML = '';
    resto.forEach(function (n) { cuerpo2.appendChild(n); });
    var h3 = cont.querySelector('.dia-cab h3');
    if (h3 && !h3.querySelector('small')) h3.insertAdjacentHTML('beforeend', ' <small>(continuación)</small>');
    b.classList.add('cortado');

    nuevaPagina();
    area.appendChild(cont);
    if (desborda(cont)) dividir(cont);
    return true;
  }

  function colocar(b) {
    if (b.hasAttribute('data-salto') && area.children.length) nuevaPagina();
    area.appendChild(b);
    if (!desborda(b)) return;

    var divisible = b.classList.contains('divisible');
    if (divisible && dividir(b)) return;

    if (esPrimero(b)) { b.classList.add('desbordado'); return; }

    // Pasa a la hoja siguiente, llevándose el título de sección si quedaba solo al final.
    var previo = b.previousElementSibling;
    b.remove();
    var arrastre = (previo && previo.hasAttribute('data-con-siguiente')) ? previo : null;
    if (arrastre) arrastre.remove();
    nuevaPagina();
    if (arrastre) area.appendChild(arrastre);
    area.appendChild(b);
    if (desborda(b) && !(divisible && dividir(b))) b.classList.add('desbordado');
  }

  // Reduce la letra del rótulo de la semana si el texto es más largo que la franja verde.
  function ajustarSemana() {
    var caja = document.querySelector('.pagina .semana');
    if (!caja) return;
    var texto = caja.firstElementChild, pt = 14;
    while (texto.scrollWidth > caja.clientWidth && pt > 7) {
      pt -= 0.5;
      caja.style.fontSize = pt + 'pt';
    }
  }

  function paginar() {
    nuevaPagina();
    Array.prototype.slice.call(fuente.children).forEach(colocar);
    fuente.remove();
    ajustarSemana();
    document.documentElement.setAttribute('data-paginas', total);
    window.boletinDesbordes = document.querySelectorAll('.desbordado').length;
    window.boletinPaginas = total;
    window.boletinListo = true;
  }

  function esperarRecursos() {
    var imgs = Array.prototype.slice.call(document.images);
    // Las plantillas (<template>) no cargan sus imágenes hasta clonarse: se precargan aquí.
    document.querySelectorAll('template').forEach(function (t) {
      t.content.querySelectorAll('img').forEach(function (i) {
        var pre = new Image(); pre.src = i.src; imgs.push(pre);
      });
    });
    var esperas = imgs.map(function (img) {
      if (img.complete) return Promise.resolve();
      return new Promise(function (ok) { img.onload = img.onerror = ok; });
    });
    if (document.fonts && document.fonts.load) {
      esperas.push(document.fonts.load('800 14pt Poppins').catch(function () {}));
      esperas.push(document.fonts.ready);
    }
    var limite = new Promise(function (ok) { setTimeout(ok, 4000); });
    return Promise.race([Promise.all(esperas), limite]);
  }

  // #fuente está oculto: sus imágenes sí se descargan, y se miden ya dentro de la hoja.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { esperarRecursos().then(paginar); });
  } else {
    esperarRecursos().then(paginar);
  }
})();
