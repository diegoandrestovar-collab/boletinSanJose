"""Exportación del boletín a PDF y HTML usando el motor Chromium de Qt (QtWebEngine)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from PySide6.QtCore import QMarginsF, QObject, QSizeF, QTimer, QUrl, Signal
from PySide6.QtGui import QPageLayout, QPageSize
from PySide6.QtWebEngineCore import QWebEnginePage

from . import modelo
from .render import generar_html

# Los resultados se piden como texto JSON: es la forma más fiable de traer datos desde JavaScript.
CONSULTA_LISTO = "window.boletinListo ? JSON.stringify([window.boletinPaginas, window.boletinDesbordes]) : ''"


def ejecutar_js(pagina: QWebEnginePage, codigo: str, respuesta=None) -> None:
    """runJavaScript en el mundo principal (0), con o sin función de respuesta."""
    if respuesta is None:
        pagina.runJavaScript(codigo, 0)
    else:
        pagina.runJavaScript(codigo, 0, respuesta)


def leer_listo(resultado) -> tuple[int, int] | None:
    """Convierte la respuesta de CONSULTA_LISTO en (hojas, desbordes); None si aún no termina."""
    if not resultado:
        return None
    try:
        hojas, desbordes = json.loads(resultado)
        return int(hojas), int(desbordes)
    except (TypeError, ValueError):
        return None


def diseno_pagina(datos: dict) -> QPageLayout:
    """Hoja del tamaño elegido, vertical y sin márgenes (los márgenes los pone la plantilla)."""
    tam = modelo.TAMANOS[modelo.normalizar(datos)["pagina"]["tamano"]]
    hoja = QPageSize(QSizeF(tam["ancho"], tam["alto"]), QPageSize.Unit.Millimeter, tam["etiqueta"],
                     QPageSize.SizeMatchPolicy.ExactMatch)
    return QPageLayout(hoja, QPageLayout.Orientation.Portrait, QMarginsF(0, 0, 0, 0),
                       QPageLayout.Unit.Millimeter)


def guardar_html(datos: dict, destino: str | Path) -> None:
    """HTML autónomo: plantilla, imágenes y fuentes van incrustadas en un solo archivo."""
    Path(destino).write_text(generar_html(datos, incrustar=True), encoding="utf-8")


class ExportadorPDF(QObject):
    """Carga el HTML en una página fuera de pantalla, espera la paginación y la imprime a PDF."""

    terminado = Signal(bool, str, int, int)   # éxito, ruta o mensaje de error, hojas, bloques desbordados

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pagina = QWebEnginePage(self)
        self._pagina.loadFinished.connect(self._cargado)
        self._pagina.pdfPrintingFinished.connect(self._impreso)
        self._carpeta = tempfile.TemporaryDirectory(prefix="boletin_pdf_")
        self._destino = ""
        self._diseno = None
        self._intentos = 0
        self._info = (0, 0)
        self.ocupado = False

    def exportar(self, datos: dict, destino: str | Path) -> None:
        if self.ocupado:
            return
        self.ocupado = True
        self._destino = str(destino)
        self._diseno = diseno_pagina(datos)
        self._intentos = 0
        origen = Path(self._carpeta.name) / "boletin.html"
        origen.write_text(generar_html(datos), encoding="utf-8")
        self._pagina.load(QUrl.fromLocalFile(str(origen)))

    def _cargado(self, ok: bool) -> None:
        if not self.ocupado:
            return
        if not ok:
            self._fin(False, "No se pudo cargar el documento HTML.")
            return
        self._esperar()

    def _esperar(self) -> None:
        ejecutar_js(self._pagina, CONSULTA_LISTO, self._revisar)

    def _revisar(self, resultado) -> None:
        info = leer_listo(resultado)
        if info:
            self._info = info
            # Un respiro para que Chromium termine de pintar imágenes y fuentes.
            QTimer.singleShot(150, lambda: self._pagina.printToPdf(self._destino, self._diseno))
            return
        self._intentos += 1
        if self._intentos > 150:
            self._fin(False, "La paginación del documento tardó demasiado.")
            return
        QTimer.singleShot(100, self._esperar)

    def _impreso(self, ruta: str, ok: bool) -> None:
        self._fin(ok, ruta if ok else "No se pudo escribir el PDF (¿está abierto en otro programa?).")

    def _fin(self, ok: bool, mensaje: str) -> None:
        self.ocupado = False
        self.terminado.emit(ok, mensaje, *self._info)
