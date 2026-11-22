"""Genera el HTML del boletín a partir de los datos del formulario."""
from __future__ import annotations

import base64
import math
import mimetypes
import re
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from . import modelo

RECURSOS = Path(__file__).resolve().parent / "recursos"

_env = Environment(
    loader=FileSystemLoader(str(RECURSOS / "plantilla")),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

_SCRIPT = re.compile(r"<\s*(script|iframe|object|embed)\b.*?<\s*/\s*\1\s*>", re.I | re.S)
_EVENTO = re.compile(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", re.I)
_VACIO = re.compile(r"^(\s|&nbsp;|<br\s*/?>|</?(p|div|span)[^>]*>)*$", re.I)


def limpiar(html: str | None) -> Markup:
    """Texto enriquecido del editor, sin scripts ni manejadores de eventos."""
    html = html or ""
    html = _SCRIPT.sub("", html)
    html = _EVENTO.sub("", html)
    return Markup(html)


def vacio(html: str | None) -> bool:
    return bool(_VACIO.match(html or ""))


@lru_cache(maxsize=64)
def _data_uri(ruta: str) -> str:
    p = Path(ruta)
    tipo = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    if p.suffix == ".woff2":
        tipo = "font/woff2"
    return f"data:{tipo};base64,{base64.b64encode(p.read_bytes()).decode('ascii')}"


def construir_contexto(datos: dict, incrustar: bool) -> dict:
    d = modelo.normalizar(datos)
    tam = modelo.TAMANOS[d["pagina"]["tamano"]]

    def recurso(rel: str) -> str:
        ruta = RECURSOS / rel
        return _data_uri(str(ruta)) if incrustar else ruta.as_uri()

    info, semana, agenda = d["info"], d["semana"], d["agenda"]

    docentes = [x for x in d["acompanamiento"]["docentes"] if (x.get("nombre") or "").strip()]
    mitad = math.ceil(len(docentes) / 2)

    dias = []
    for i, dia in enumerate(agenda["dias"]):
        if not dia.get("mostrar", True):
            continue
        dias.append({
            "titulo": modelo.titulo_dia(dia, i, agenda, semana),
            "html": limpiar(dia.get("html")),
            "vacio": vacio(dia.get("html")),
            "color": modelo.COLORES_DIA[len(dias) % len(modelo.COLORES_DIA)],
        })

    extras = [
        {"titulo": e.get("titulo") or "", "html": limpiar(e.get("html")), "salto": bool(e.get("salto"))}
        for e in d["extras"]
        if (e.get("titulo") or "").strip() or not vacio(e.get("html"))
    ]

    return {
        "d": d,
        "ancho": tam["ancho"],
        "alto": tam["alto"],
        "recurso": recurso,
        "css": Markup((RECURSOS / "plantilla" / "boletin.css").read_text(encoding="utf-8")),
        "js": Markup((RECURSOS / "plantilla" / "paginar.js").read_text(encoding="utf-8")),
        "texto_semana": modelo.texto_semana(semana),
        "mensaje_html": limpiar(d["mensaje"]["html"]),
        "avance": modelo.avance_periodo(info, semana),
        "finaliza": modelo.fecha_larga(modelo.a_fecha(info.get("fin"))),
        "saber": modelo.semanas_saber(info, semana),
        "recomendaciones_html": limpiar(d["recomendaciones"]["html"]),
        "mapa": d["acompanamiento"]["mapa"] or recurso("img/mapa.jpg"),
        "docentes_izq": docentes[:mitad],
        "docentes_der": docentes[mitad:],
        "notas_html": limpiar(d["acompanamiento"]["notas_html"]),
        "notas_vacias": vacio(d["acompanamiento"]["notas_html"]),
        "dias": dias,
        "extras": extras,
    }


def generar_html(datos: dict, incrustar: bool = False) -> str:
    """Devuelve el documento HTML completo.

    incrustar=False → las imágenes de la plantilla se enlazan desde la carpeta de recursos
                      (rápido, para la vista previa y el PDF).
    incrustar=True  → todo va embebido en base64: un único archivo .html portable.
    """
    return _env.get_template("boletin.html.j2").render(**construir_contexto(datos, incrustar))
