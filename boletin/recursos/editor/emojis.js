/* ==========================================================================
   Botón 😀 para el editor (complemento de SunEditor).
   Inserta emojis sin depender del selector del sistema operativo, que en
   macOS no siempre llega al navegador incrustado de la aplicación.
   Para agregar o quitar emojis, edite la lista GRUPOS.
   ========================================================================== */
(function () {
  'use strict';

  var GRUPOS = [
    ['Fechas y horas', '📅 🗓️ ⏰ ⏱️ ⌛ 🕐 🕗 🕛 📆 🔔'],
    ['Colegio', '🏫 📚 📖 ✏️ 📝 🖊️ 📏 📐 🎓 🧑‍🏫 👩‍🏫 👨‍🏫 🧑‍🎓 🎒 💻 🖥️ 🔬 🧪 🧮 🌎'],
    ['Avisos', '⚠️ ❗ ❓ ✅ ☑️ ❌ 🚫 📢 📣 💡 🔍 👁️ 👀 📌 📍 📎 🖇️ ⭐ 🌟 ✨'],
    ['Flechas', '➡️ ⬅️ ⬆️ ⬇️ ↗️ ↘️ ↩️ ↪️ 🔄 👉 👈 👆 👇 → ← ➜ ➤ ►'],
    ['Actividades', '⚽ 🏀 🏐 🏃 🎨 🎭 🎵 🎤 🎉 🎊 🎈 🏆 🥇 🎂 🎁 🙌 👏 🤝 ❤️ 💚 💙'],
    ['Vacaciones', '🏖️ 🌴 ☀️ 🌊 ✈️ 🧳 🚌 🏕️ ⛰️ 😎 🥳 🎄 🎅 🎆'],
    ['Comunidad', '👨‍👩‍👧 👪 🧒 👦 👧 🙋 💬 📞 ✉️ 🏠 🍎 🥪 🧃 🚸']
  ];

  var estilo = document.createElement('style');
  estilo.textContent =
    '.se-emoji-menu{width:316px;max-height:330px;overflow-y:auto;padding:6px 8px 8px;}' +
    '.se-emoji-menu h6{margin:8px 2px 4px;font:600 11px/1.2 system-ui,sans-serif;color:#5d6b7a;text-transform:uppercase;letter-spacing:.03em;}' +
    '.se-emoji-menu h6:first-child{margin-top:2px;}' +
    '.se-emoji-menu .se-emoji-grid{display:grid;grid-template-columns:repeat(8,1fr);gap:2px;}' +
    '.se-emoji-menu button{all:unset;cursor:pointer;text-align:center;font-size:21px;line-height:34px;height:34px;border-radius:6px;' +
    'font-family:"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif;}' +
    '.se-emoji-menu button:hover{background:#e8f0fa;}';
  document.head.appendChild(estilo);

  window.pluginEmoji = {
    name: 'emoji',
    display: 'submenu',
    title: 'Insertar emoji',
    buttonClass: '',
    innerHTML: '<span style="font-size:17px;line-height:1;font-family:\'Apple Color Emoji\',\'Segoe UI Emoji\',\'Noto Color Emoji\',sans-serif">😀</span>',

    add: function (core, botonDestino) {
      var menu = core.util.createElement('DIV');
      menu.className = 'se-submenu se-list-layer';
      var html = '<div class="se-list-inner se-emoji-menu">';
      GRUPOS.forEach(function (g) {
        html += '<h6>' + g[0] + '</h6><div class="se-emoji-grid">';
        g[1].split(/\s+/).filter(Boolean).forEach(function (e) {
          html += '<button type="button" data-emoji="' + e + '" title="' + e + '">' + e + '</button>';
        });
        html += '</div>';
      });
      menu.innerHTML = html + '</div>';
      // mousedown: evita que el editor pierda la posición del cursor al hacer clic en el menú.
      menu.addEventListener('mousedown', function (e) { e.preventDefault(); e.stopPropagation(); });
      menu.addEventListener('click', this.alElegir.bind(core));
      core.initMenuTarget(this.name, botonDestino, menu);
    },

    alElegir: function (e) {
      var b = e.target.closest('button[data-emoji]');
      if (!b) return;
      e.preventDefault();
      this.insertNode(document.createTextNode(b.getAttribute('data-emoji')), null, true);
      this.submenuOff();
      this.focus();
      // Avisa al formulario para que guarde el cambio y refresque la vista previa.
      if (typeof this.functions.onChange === 'function') {
        this.functions.onChange(this.functions.getContents(true), this);
      }
    }
  };
})();
