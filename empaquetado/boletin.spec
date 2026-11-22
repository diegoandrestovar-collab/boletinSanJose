# -*- mode: python ; coding: utf-8 -*-
"""Configuración de PyInstaller para el Boletín Institucional.

Funciona igual en Windows, macOS y Linux, pero cada sistema compila su propia versión:
    pyinstaller --noconfirm empaquetado/boletin.spec

Resultado en dist/:
    Windows → dist/BoletinInstitucional/BoletinInstitucional.exe
    macOS   → dist/Boletín Institucional.app
    Linux   → dist/BoletinInstitucional/BoletinInstitucional
"""
import sys
from pathlib import Path

RAIZ = Path(SPECPATH).parent          # carpeta del proyecto (SPECPATH = carpeta de este archivo)
EMPAQUETADO = Path(SPECPATH)
NOMBRE = "BoletinInstitucional"
NOMBRE_VISIBLE = "Boletín Institucional"
VERSION = "1.0.0"

if sys.platform == "win32":
    ICONO = str(EMPAQUETADO / "icono.ico")
elif sys.platform == "darwin":
    ICONO = str(EMPAQUETADO / "icono.icns")
else:
    ICONO = None

a = Analysis(
    [str(RAIZ / "main.py")],
    pathex=[str(RAIZ)],
    # Plantilla, formulario, imágenes y fuentes viajan dentro del ejecutable.
    datas=[(str(RAIZ / "boletin" / "recursos"), "boletin/recursos")],
    hiddenimports=["PySide6.QtWebChannel", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets"],
    # Módulos que la aplicación no usa: se excluyen para que el paquete pese menos.
    excludes=[
        "tkinter", "unittest", "pydoc", "numpy", "PIL", "playwright",
        "PySide6.Qt3DAnimation", "PySide6.Qt3DCore", "PySide6.Qt3DExtras", "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic", "PySide6.Qt3DRender", "PySide6.QtBluetooth", "PySide6.QtCharts",
        "PySide6.QtDataVisualization", "PySide6.QtGraphs", "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets", "PySide6.QtNfc", "PySide6.QtQuick3D", "PySide6.QtRemoteObjects",
        "PySide6.QtScxml", "PySide6.QtSensors", "PySide6.QtSerialBus", "PySide6.QtSerialPort",
        "PySide6.QtSpatialAudio", "PySide6.QtSql", "PySide6.QtStateMachine", "PySide6.QtTest",
        "PySide6.QtTextToSpeech", "PySide6.QtHttpServer", "PySide6.QtDesigner", "PySide6.QtHelp",
        "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtSvgWidgets", "PySide6.QtUiTools",
    ],
    noarchive=False,
)

# ------------------------------------------------------------------ adelgazar el paquete
# Qt WebEngine arrastra muchos módulos de Qt (3D, gráficos, multimedia, QML…) que la aplicación
# no usa. Se quitan por nombre; los mismos nombres sirven en Windows (.dll), macOS (.framework)
# y Linux (.so). Lo que WebEngine sí necesita (Core, Gui, Widgets, Network, Qml, Quick,
# Positioning, WebChannel, PrintSupport, OpenGL, DBus…) no está en esta lista.
import re

MODULOS_SOBRANTES = {
    "3DAnimation", "3DCore", "3DExtras", "3DInput", "3DLogic", "3DRender", "3DQuick",
    "3DQuickAnimation", "3DQuickExtras", "3DQuickInput", "3DQuickLogic", "3DQuickRender",
    "3DQuickScene2D", "3DQuickScene3D", "5Compat", "Bluetooth", "Charts", "ChartsQml",
    "DataVisualization", "DataVisualizationQml", "Designer", "DesignerComponents", "Graphs",
    "Graphs2DImpl", "GraphsWidgets", "Grpc", "GrpcQuick", "Help", "HttpServer", "JsonRpc",
    "LanguageServer", "Location", "Multimedia", "MultimediaQuick", "MultimediaWidgets", "Nfc",
    "Pdf", "PdfQuick", "PdfWidgets", "PositioningQuick", "Protobuf", "ProtobufQuick",
    "QmlDesignSupport", "QmlLocalStorage", "QmlNetwork", "QmlXmlListModel", "Quick3D",
    "Quick3DAssetImport", "Quick3DAssetUtils", "Quick3DEffects", "Quick3DGlslParser",
    "Quick3DHelpers", "Quick3DHelpersImpl", "Quick3DIblBaker", "Quick3DParticleEffects",
    "Quick3DParticles", "Quick3DPhysics", "Quick3DPhysicsHelpers", "Quick3DRuntimeRender",
    "Quick3DSpatialAudio", "Quick3DUtils", "Quick3DXr", "QuickControls2",
    "QuickControls2Basic", "QuickControls2BasicStyleImpl", "QuickControls2FluentWinUI3",
    "QuickControls2FluentWinUI3StyleImpl", "QuickControls2Fusion",
    "QuickControls2FusionStyleImpl", "QuickControls2Imagine", "QuickControls2ImagineStyleImpl",
    "QuickControls2Impl", "QuickControls2Material", "QuickControls2MaterialStyleImpl",
    "QuickControls2Universal", "QuickControls2UniversalStyleImpl", "QuickControls2IOSStyleImpl",
    "QuickControls2MacOSStyleImpl", "QuickControls2WindowsStyleImpl", "QuickDialogs2",
    "QuickDialogs2QuickImpl", "QuickDialogs2Utils", "QuickEffects", "QuickLayouts",
    "QuickParticles", "QuickShapes", "QuickTemplates2", "QuickTest", "QuickTimeline",
    "QuickTimelineBlendTrees", "QuickVectorImage", "QuickVectorImageGenerator",
    "RemoteObjects", "RemoteObjectsQml", "Scxml", "ScxmlQml", "Sensors", "SensorsQuick",
    "SerialBus", "SerialPort", "ShaderTools", "SpatialAudio", "Sql", "StateMachine",
    "StateMachineQml", "Test", "TextToSpeech", "UiTools", "VirtualKeyboard",
    "VirtualKeyboardQml", "VirtualKeyboardSettings", "WebSockets", "WebView", "WebViewQuick",
    "Labs",  # todos los QtLabs*
}
_PARTE_QT = re.compile(r"^(?:lib)?Qt6?([A-Za-z0-9]+?)(?:\.framework|\.abi3\.so|\.pyd|\.pyi|\.dll"
                       r"|\.dylib|\.so(?:\.\d+)*)?$")
_IDIOMAS_WEB = re.compile(r"^(?:es|es-419|en-US)\.pak$")
_TRADUCCIONES = re.compile(r"^(?:qt|qtbase|qtwebengine)_es\.qm$")


def _sobra(destino: str) -> bool:
    partes = destino.replace("\\", "/").split("/")
    if "PySide6" not in partes:
        return False
    for parte in partes:
        m = _PARTE_QT.match(parte)
        if m and (m.group(1) in MODULOS_SOBRANTES or m.group(1).startswith("Labs")):
            return True
    nombre = partes[-1]
    if "qml" in partes:                               # módulos QML: WebEngineWidgets no los usa
        return True
    if "qtwebengine_locales" in partes:               # solo español e inglés
        return not _IDIOMAS_WEB.match(nombre)
    if "translations" in partes and nombre.endswith(".qm"):
        return not _TRADUCCIONES.match(nombre)
    return False


antes = len(a.binaries) + len(a.datas)
a.binaries = [x for x in a.binaries if not _sobra(x[0])]
a.datas = [x for x in a.datas if not _sobra(x[0])]
print(f"[boletin.spec] Archivos de Qt descartados: {antes - len(a.binaries) - len(a.datas)}")

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NOMBRE,
    console=False,               # sin ventana negra de consola
    icon=ICONO,
    upx=False,                   # UPX rompe las librerías de Qt WebEngine
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name=NOMBRE,
    upx=False,
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{NOMBRE_VISIBLE}.app",
        icon=ICONO,
        bundle_identifier="co.edu.iesanjose.oporapa.boletin",
        version=VERSION,
        info_plist={
            "CFBundleDisplayName": NOMBRE_VISIBLE,
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "12.0",
            "NSHumanReadableCopyright": "Institución Educativa San José – Oporapa, Huila",
            # Asocia los archivos .boletin con la aplicación.
            "CFBundleDocumentTypes": [{
                "CFBundleTypeName": "Boletín Institucional",
                "CFBundleTypeRole": "Editor",
                "LSHandlerRank": "Owner",
                "CFBundleTypeExtensions": ["boletin"],
                "CFBundleTypeIconFile": "icono.icns",
            }],
        },
    )
