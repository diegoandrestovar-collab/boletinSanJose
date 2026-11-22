"""Boletín Institucional – I. E. San José (Oporapa, Huila).

Uso:
    python main.py                               abre la aplicación
    python main.py semana.boletin                abre un boletín guardado
    python main.py semana.boletin --pdf s.pdf    genera el PDF sin abrir la ventana
    python main.py semana.boletin --html s.html  genera el HTML autónomo sin abrir la ventana
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _preparar_entorno() -> None:
    # En Linux, ejecutando como administrador, Chromium exige desactivar su caja de arena.
    if sys.platform.startswith("linux") and hasattr(os, "geteuid") and os.geteuid() == 0:
        banderas = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
        if "--no-sandbox" not in banderas:
            os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (banderas + " --no-sandbox").strip()


def _sin_ventana(args) -> int:
    from boletin import modelo
    datos = modelo.normalizar(json.loads(Path(args.archivo).read_text(encoding="utf-8")))

    if args.html:
        from boletin.exportar import guardar_html
        guardar_html(datos, args.html)
        print(f"HTML generado: {args.html}")
    if not args.pdf:
        return 0

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from boletin.exportar import ExportadorPDF

    app = QApplication(sys.argv[:1])
    estado = {"codigo": 1}
    exportador = ExportadorPDF()

    def terminado(ok, mensaje, hojas, desbordes):
        if ok:
            print(f"PDF generado: {mensaje} ({hojas} hojas)")
            if desbordes:
                print(f"Aviso: {desbordes} bloque(s) no caben en una hoja.")
            estado["codigo"] = 0
        else:
            print(f"Error: {mensaje}", file=sys.stderr)
        app.quit()

    exportador.terminado.connect(terminado)
    exportador.exportar(datos, str(Path(args.pdf).resolve()))
    app.exec()
    return estado["codigo"]


def main() -> int:
    analizador = argparse.ArgumentParser(description="Editor del Boletín Institucional")
    analizador.add_argument("archivo", nargs="?", help="archivo .boletin")
    analizador.add_argument("--pdf", metavar="SALIDA", help="exporta a PDF y termina")
    analizador.add_argument("--html", metavar="SALIDA", help="exporta a HTML autónomo y termina")
    args = analizador.parse_args()

    _preparar_entorno()
    if args.pdf or args.html:
        if not args.archivo:
            analizador.error("indique el archivo .boletin que se va a exportar")
        return _sin_ventana(args)

    from boletin.app import ejecutar
    return ejecutar(args.archivo)


if __name__ == "__main__":
    sys.exit(main())
