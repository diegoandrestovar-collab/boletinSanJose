"""Ventana principal: formulario a la izquierda, vista previa paginada a la derecha."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QFile, QIODevice, QObject, QSettings, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QAction, QColor, QDesktopServices, QKeySequence
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineScript, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (QApplication, QFileDialog, QLabel, QMainWindow, QMessageBox,
                               QSplitter, QStyle, QToolBar)

from . import modelo
from .exportar import CONSULTA_LISTO, ExportadorPDF, ejecutar_js, guardar_html, leer_listo
from .render import RECURSOS, generar_html

NOMBRE_APP = "Boletín Institucional"
FILTRO = "Boletín (*.boletin);;Todos los archivos (*)"
PX_POR_MM = 96 / 25.4


class Puente(QObject):
    """Canal de comunicación entre el formulario (JavaScript) y la ventana (Python)."""

    cargar = Signal(str)          # Python → formulario: JSON con todos los datos
    cambiado = Signal(str)        # uso interno: el formulario cambió
    listo = Signal()              # uso interno: el formulario terminó de cargar

    @Slot(str)
    def cambio(self, datos_json: str) -> None:
        self.cambiado.emit(datos_json)

    @Slot()
    def formularioListo(self) -> None:
        self.listo.emit()


class Ventana(QMainWindow):
    def __init__(self, ruta_inicial: str | None = None):
        super().__init__()
        self.datos = modelo.datos_nuevos()
        self.ruta: Path | None = None
        self._guardado = self._firma(self.datos)
        self._ajustar_ancho = True
        self._zoom = 1.0
        self._scroll = 0
        self._intentos = 0
        self._temporal = tempfile.TemporaryDirectory(prefix="boletin_vista_")
        self._html_vista = Path(self._temporal.name) / "vista.html"
        self._preferencias = QSettings("IE San José Oporapa", "BoletinInstitucional")
        self._ruta_inicial = ruta_inicial

        self.resize(1500, 900)
        self._crear_vistas()
        self._crear_acciones()
        self._titulo()

        self._refresco = QTimer(self, singleShot=True, interval=250)
        self._refresco.timeout.connect(self._refrescar_vista)
        self._exportador = ExportadorPDF(self)
        self._exportador.terminado.connect(self._pdf_terminado)

    # ------------------------------------------------------------------ construcción
    def _crear_vistas(self) -> None:
        self.formulario = QWebEngineView()
        self.vista = QWebEngineView()
        self.vista.page().setBackgroundColor(QColor("#5b6470"))
        self.vista.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        for v in (self.formulario, self.vista):
            ajustes = v.settings()
            ajustes.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            ajustes.setAttribute(QWebEngineSettings.WebAttribute.PrintElementBackgrounds, True)

        # Puente QWebChannel: se inyecta qwebchannel.js antes de que cargue el formulario.
        self.puente = Puente(self)
        canal = QWebChannel(self)
        canal.registerObject("puente", self.puente)
        self.formulario.page().setWebChannel(canal)
        archivo = QFile(":/qtwebchannel/qwebchannel.js")
        if archivo.open(QIODevice.OpenModeFlag.ReadOnly):
            guion = QWebEngineScript()
            guion.setName("qwebchannel")
            guion.setSourceCode(bytes(archivo.readAll()).decode("utf-8"))
            guion.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            guion.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            self.formulario.page().scripts().insert(guion)
            archivo.close()
        self.puente.listo.connect(self._formulario_listo)
        self.puente.cambiado.connect(self._formulario_cambio)
        self.formulario.load(QUrl.fromLocalFile(str(RECURSOS / "editor" / "formulario.html")))
        self.vista.loadFinished.connect(self._vista_cargada)

        divisor = QSplitter(Qt.Orientation.Horizontal)
        divisor.addWidget(self.formulario)
        divisor.addWidget(self.vista)
        divisor.setStretchFactor(0, 0)
        divisor.setStretchFactor(1, 1)
        divisor.setSizes([620, 880])
        divisor.splitterMoved.connect(lambda *_: self._aplicar_zoom())
        self.setCentralWidget(divisor)

        self.etiqueta_hojas = QLabel("")
        self.statusBar().addPermanentWidget(self.etiqueta_hojas)

    def _crear_acciones(self) -> None:
        estilo = self.style()
        barra = QToolBar("Principal")
        barra.setMovable(False)
        barra.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(barra)

        def accion(texto, icono, atajo, funcion, ayuda=""):
            a = QAction(estilo.standardIcon(icono) if icono else self.windowIcon(), texto, self)
            if atajo:
                a.setShortcut(QKeySequence(atajo))
            a.setToolTip(f"{ayuda or texto} ({atajo})" if atajo else (ayuda or texto))
            a.triggered.connect(funcion)
            barra.addAction(a)
            return a

        SP = QStyle.StandardPixmap
        accion("Nuevo", SP.SP_FileIcon, "Ctrl+N", self.nuevo, "Boletín nuevo con los textos de la plantilla")
        accion("Abrir", SP.SP_DialogOpenButton, "Ctrl+O", self.abrir)
        accion("Guardar", SP.SP_DialogSaveButton, "Ctrl+S", self.guardar)
        accion("Guardar como", None, "Ctrl+Shift+S", self.guardar_como)
        barra.addSeparator()
        accion("Exportar PDF", SP.SP_ArrowDown, "Ctrl+E", self.exportar_pdf, "Generar el PDF final")
        accion("Exportar HTML", None, "", self.exportar_html, "Guardar el HTML en un solo archivo")
        barra.addSeparator()
        accion("−", None, "Ctrl+-", lambda: self._cambiar_zoom(1 / 1.15), "Alejar")
        accion("+", None, "Ctrl++", lambda: self._cambiar_zoom(1.15), "Acercar")
        accion("Ajustar al ancho", None, "Ctrl+0", self._zoom_ancho)
        accion("Actualizar", SP.SP_BrowserReload, "F5", self._pedir_y_refrescar, "Regenerar la vista previa")

    # ------------------------------------------------------------------ formulario
    def _formulario_listo(self) -> None:
        if self._ruta_inicial:
            ruta, self._ruta_inicial = self._ruta_inicial, None
            if self._leer(Path(ruta)):
                return
        self._enviar_al_formulario()

    def _enviar_al_formulario(self) -> None:
        self.puente.cargar.emit(json.dumps(self.datos, ensure_ascii=False))
        self._refrescar_vista()

    def _formulario_cambio(self, datos_json: str) -> None:
        try:
            self.datos = modelo.normalizar(json.loads(datos_json))
        except json.JSONDecodeError:
            return
        self._titulo()
        self._refresco.start()

    def _recolectar(self, continuar) -> None:
        """Pide al formulario los datos al instante (sin esperar el retardo de escritura)."""
        def recibido(datos_json):
            if datos_json:
                try:
                    self.datos = modelo.normalizar(json.loads(datos_json))
                except json.JSONDecodeError:
                    pass
            continuar()
        ejecutar_js(self.formulario.page(), "window.boletin ? window.boletin.recolectar() : ''", recibido)

    def _pedir_y_refrescar(self) -> None:
        self._recolectar(self._refrescar_vista)

    # ------------------------------------------------------------------ vista previa
    def _refrescar_vista(self) -> None:
        self._refresco.stop()

        def con_scroll(y):
            try:
                self._scroll = float(y or 0)
            except (TypeError, ValueError):
                self._scroll = 0
            try:
                self._html_vista.write_text(generar_html(self.datos), encoding="utf-8")
            except Exception as error:  # la plantilla no debería fallar, pero mejor avisar que cerrar
                self.statusBar().showMessage(f"Error al generar el HTML: {error}", 10000)
                return
            self.vista.load(QUrl.fromLocalFile(str(self._html_vista)))

        ejecutar_js(self.vista.page(), "String(window.scrollY || 0)", con_scroll)

    def _vista_cargada(self, ok: bool) -> None:
        if not ok:
            return
        self._aplicar_zoom()
        self._intentos = 0
        self._esperar_paginacion()

    def _esperar_paginacion(self) -> None:
        def revisar(resultado):
            info = leer_listo(resultado)
            if info:
                hojas, desbordes = info
                ejecutar_js(self.vista.page(), f"window.scrollTo(0, {self._scroll})")
                texto = f"{hojas} hoja{'s' if hojas != 1 else ''} · {self._nombre_tamano()}"
                if desbordes:
                    texto += f" · ⚠ {desbordes} bloque(s) no caben en una hoja (borde rojo)"
                self.etiqueta_hojas.setText(texto)
                return
            self._intentos += 1
            if self._intentos < 100:
                QTimer.singleShot(60, self._esperar_paginacion)
        ejecutar_js(self.vista.page(), CONSULTA_LISTO, revisar)

    def _nombre_tamano(self) -> str:
        return modelo.TAMANOS[self.datos["pagina"]["tamano"]]["etiqueta"].split(" (")[0]

    def _aplicar_zoom(self) -> None:
        if self._ajustar_ancho:
            ancho_hoja = modelo.TAMANOS[self.datos["pagina"]["tamano"]]["ancho"] * PX_POR_MM + 56
            self._zoom = max(0.3, min(2.5, self.vista.width() / ancho_hoja))
        self.vista.setZoomFactor(self._zoom)

    def _cambiar_zoom(self, factor: float) -> None:
        self._ajustar_ancho = False
        self._zoom = max(0.3, min(3.0, self._zoom * factor))
        self._aplicar_zoom()

    def _zoom_ancho(self) -> None:
        self._ajustar_ancho = True
        self._aplicar_zoom()

    def resizeEvent(self, evento) -> None:
        super().resizeEvent(evento)
        QTimer.singleShot(0, self._aplicar_zoom)

    # ------------------------------------------------------------------ archivos
    @staticmethod
    def _firma(datos: dict) -> str:
        return json.dumps(datos, sort_keys=True, ensure_ascii=False)

    def _sucio(self) -> bool:
        return self._firma(self.datos) != self._guardado

    def _titulo(self) -> None:
        nombre = self.ruta.name if self.ruta else "Sin título"
        self.setWindowTitle(f"{'● ' if self._sucio() else ''}{nombre} – {NOMBRE_APP}")

    def _carpeta(self) -> str:
        return str(self._preferencias.value("carpeta", str(Path.home() / "Documents")))

    def _recordar(self, ruta: str) -> None:
        self._preferencias.setValue("carpeta", str(Path(ruta).parent))

    def _nombre_sugerido(self, extension: str) -> str:
        base = self.ruta.stem if self.ruta else f"Boletin_{self.datos['semana'].get('inicio') or 'semana'}"
        return str(Path(self._carpeta()) / f"{base}{extension}")

    def _confirmar_descartar(self) -> bool:
        if not self._sucio():
            return True
        r = QMessageBox.question(
            self, NOMBRE_APP, "Hay cambios sin guardar. ¿Desea guardarlos?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Save:
            return self._escribir(self.ruta) if self.ruta else self._guardar_como_ahora()
        return r == QMessageBox.StandardButton.Discard

    def nuevo(self) -> None:
        def seguir():
            if not self._confirmar_descartar():
                return
            self.datos = modelo.datos_nuevos()
            self.ruta = None
            self._guardado = self._firma(self.datos)
            self._titulo()
            self._enviar_al_formulario()
        self._recolectar(seguir)

    def abrir(self) -> None:
        def seguir():
            if not self._confirmar_descartar():
                return
            ruta, _ = QFileDialog.getOpenFileName(self, "Abrir boletín", self._carpeta(), FILTRO)
            if ruta:
                self._leer(Path(ruta))
        self._recolectar(seguir)

    def _leer(self, ruta: Path) -> bool:
        try:
            self.datos = modelo.normalizar(json.loads(ruta.read_text(encoding="utf-8")))
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, NOMBRE_APP, f"No se pudo abrir el archivo:\n{error}")
            return False
        self.ruta = ruta
        self._guardado = self._firma(self.datos)
        self._recordar(str(ruta))
        self._titulo()
        self._enviar_al_formulario()
        return True

    def guardar(self) -> None:
        self._recolectar(lambda: self._escribir(self.ruta) if self.ruta else self._guardar_como_ahora())

    def guardar_como(self) -> None:
        self._recolectar(self._guardar_como_ahora)

    def _guardar_como_ahora(self) -> bool:
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar boletín", self._nombre_sugerido(".boletin"), FILTRO)
        if not ruta:
            return False
        if not ruta.lower().endswith(".boletin"):
            ruta += ".boletin"
        return self._escribir(Path(ruta))

    def _escribir(self, ruta: Path) -> bool:
        try:
            ruta.write_text(json.dumps(self.datos, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError as error:
            QMessageBox.warning(self, NOMBRE_APP, f"No se pudo guardar:\n{error}")
            return False
        self.ruta = ruta
        self._guardado = self._firma(self.datos)
        self._recordar(str(ruta))
        self._titulo()
        self.statusBar().showMessage(f"Guardado en {ruta}", 5000)
        return True

    # ------------------------------------------------------------------ exportación
    def exportar_pdf(self) -> None:
        if self._exportador.ocupado:
            return

        def seguir():
            ruta, _ = QFileDialog.getSaveFileName(self, "Exportar PDF", self._nombre_sugerido(".pdf"), "PDF (*.pdf)")
            if not ruta:
                return
            if not ruta.lower().endswith(".pdf"):
                ruta += ".pdf"
            self._recordar(ruta)
            self.statusBar().showMessage("Generando PDF…")
            self._refrescar_vista()
            self._exportador.exportar(self.datos, ruta)
        self._recolectar(seguir)

    def _pdf_terminado(self, ok: bool, mensaje: str, hojas: int, desbordes: int) -> None:
        self.statusBar().clearMessage()
        if not ok:
            QMessageBox.warning(self, NOMBRE_APP, mensaje)
            return
        aviso = QMessageBox(self)
        aviso.setWindowTitle(NOMBRE_APP)
        aviso.setIcon(QMessageBox.Icon.Information)
        texto = f"PDF generado ({hojas} hoja{'s' if hojas != 1 else ''}):\n{mensaje}"
        if desbordes:
            texto += "\n\nAtención: hay contenido que no cabe en una hoja y quedó recortado."
        aviso.setText(texto)
        abrir = aviso.addButton("Abrir PDF", QMessageBox.ButtonRole.AcceptRole)
        aviso.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
        aviso.exec()
        if aviso.clickedButton() is abrir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(mensaje))

    def exportar_html(self) -> None:
        def seguir():
            ruta, _ = QFileDialog.getSaveFileName(self, "Exportar HTML", self._nombre_sugerido(".html"), "HTML (*.html)")
            if not ruta:
                return
            if not ruta.lower().endswith((".html", ".htm")):
                ruta += ".html"
            try:
                guardar_html(self.datos, ruta)
            except OSError as error:
                QMessageBox.warning(self, NOMBRE_APP, f"No se pudo guardar:\n{error}")
                return
            self._recordar(ruta)
            self.statusBar().showMessage(f"HTML guardado en {ruta}", 5000)
        self._recolectar(seguir)

    # ------------------------------------------------------------------ cierre
    def closeEvent(self, evento) -> None:
        if self._confirmar_descartar():
            evento.accept()
        else:
            evento.ignore()


def ejecutar(ruta: str | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(NOMBRE_APP)
    ventana = Ventana(ruta)
    ventana.showMaximized()
    return app.exec()
