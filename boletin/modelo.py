"""Modelo de datos del boletín: valores por defecto, normalización y cálculos de fechas."""
from __future__ import annotations

import copy
import math
from datetime import date, datetime, timedelta

VERSION = 1

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

# Tamaños de hoja disponibles (milímetros). El primero es el de la plantilla original.
TAMANOS = {
    "oficio": {"etiqueta": "Oficio 21,6 × 35,6 cm (8,5 × 14 pulg.)", "ancho": 215.9, "alto": 355.6},
    "oficio33": {"etiqueta": "Oficio 21,6 × 33 cm (8,5 × 13 pulg.)", "ancho": 215.9, "alto": 330.2},
    "carta": {"etiqueta": "Carta 21,6 × 27,9 cm", "ancho": 215.9, "alto": 279.4},
}

# Paleta de cada día (se repite en el mismo orden que la plantilla: verde, azul, naranja).
COLORES_DIA = [
    {"fondo": "#e6f6e1", "titulo": "#124f1a", "tab": "#1a7224"},
    {"fondo": "#dbe8f6", "titulo": "#002060", "tab": "#215e9a"},
    {"fondo": "#feebb3", "titulo": "#f2810a", "tab": "#f29e05"},
]

DOCENTES = [
    "ADA UBIELLY VALENCIA CELIS", "ÁLVARO PEÑA CASTRO", "ALVENIS TRUJILLO COLLO",
    "AMÉLIDA PEÑARANDA AGUIRRE", "CAROLINA LÓPEZ VARGAS", "DIEGO ANDRÉS TOVAR CARDOZO",
    "HERMAN FERNANDO PEÑA RAMIREZ", "JAIME ANDRÉS ROBLES LUQUE", "JHON STEVEEN CUSCUE SILVA",
    "JHONNATHAN DANIEL BELTRAN GALINDO", "JOSÉ ROGER EMBUS SALAZAR", "JUAN CARLOS LOPEZ REYES",
    "JUAN CARLOS MEJÍA RODRÍGUEZ", "JUAN MANUEL BRAVO CABRERA", "LINA MARIA ÁNGEL GONZÁLEZ",
    "LINA MARITZA MONCAYO BETANCURT", "MARTHA GRILLO VARGAS", "NURY CONSTANZA PEÑA RAMIREZ",
    "OSCAR JAVIER ARCINIEGAS RAMIREZ", "PAOLA ANDREA CASTAÑEDA BERMEO", "ROBINSON TRUJILLO RODRÍGUEZ",
    "SHEYLA STEFANIA HENAO MORENO", "YEFRY ALEXANDER MARTÍNEZ", "YENIRETH CORTÉS CORTÉS",
    "YUBELY SANCHEZ ORTIZ",
]

RECOMENDACIONES = (
    "<ul>"
    "<li>La rotación por los diferentes salones implica el manejo disciplinario del tiempo, salir "
    "puntuales del salón y llegar en el menor tiempo posible a clase siguiente "
    "(<strong>menos de 3 minutos</strong>).</li>"
    "<li>No están autorizadas las compras en la tienda escolar en los espacios de rotación de clase, "
    "ni en lugares diferentes a ellas.</li>"
    "<li>Salidas al baño únicamente bajo autorización del docente de clase.</li>"
    "<li>En el espacio del descanso no está permitida la permanencia de estudiantes al interior de "
    "los salones de clase y la parte baja de la institución.</li>"
    "</ul>"
)

NOTAS_ACOMPANAMIENTO = (
    "<ul>"
    "<li>En los espacios del descanso en los que haya encuentros deportivos producto del campeonato "
    "intercursos, los docentes ubicados en las zonas 20 y 23 intercambiarán zonas de acompañamiento "
    "con los docentes Roger Embus y Nury Peña.</li>"
    "<li>Los estudiantes que requieran tomar medicamentos por razones de salud dentro de la "
    "institución educativa deberán tener la autorización por escrito de sus padres.</li>"
    "<li>En el espacio del descanso no está permitida la permanencia de estudiantes al interior de "
    "los salones de clase y la parte baja de la institución.</li>"
    "</ul>"
)


def _lunes_proximo(hoy: date | None = None) -> date:
    hoy = hoy or date.today()
    # Lunes de la semana en curso; si ya es fin de semana, el lunes siguiente.
    lunes = hoy - timedelta(days=hoy.weekday())
    if hoy.weekday() >= 5:
        lunes += timedelta(days=7)
    return lunes


def datos_nuevos() -> dict:
    """Boletín en blanco con los textos fijos de la plantilla."""
    lunes = _lunes_proximo()
    return {
        "version": VERSION,
        "pagina": {"tamano": "oficio"},
        "institucion": {
            "nombre": "Institución Educativa San José – Oporapa, Huila",
            "telefono": "(57) 3147791126",
            "direccion": "Calle 7 No. 9ª-34",
        },
        "semana": {
            "inicio": lunes.isoformat(),
            "fin": (lunes + timedelta(days=4)).isoformat(),
            "texto": "",
        },
        "mensaje": {
            "mostrar": True,
            "titulo": "Mensaje del Equipo Directivo",
            "html": "",
            "imagen": "",
        },
        "info": {
            "mostrar": True,
            "titulo": "Información Institucional",
            "periodo": "1",
            "inicio": "",
            "fin": "",
            "avance_auto": True,
            "avance": 0,
            "saber_mostrar": True,
            "saber_titulo": "Prueba Saber 11",
            "saber_fecha": "",
            "saber_auto": True,
            "saber_semanas": "",
        },
        "recomendaciones": {
            "mostrar": True,
            "titulo": "Recomendaciones",
            "html": RECOMENDACIONES,
        },
        "acompanamiento": {
            "mostrar": True,
            "salto": True,
            "titulo": "Acompañamiento",
            "mostrar_mapa": True,
            "mapa": "",
            "docentes": [{"nombre": n, "zona": ""} for n in DOCENTES],
            "notas_html": NOTAS_ACOMPANAMIENTO,
        },
        "agenda": {
            "salto": True,
            "titulo": "Agenda de la Semana",
            "mostrar_fechas": False,
            "dias": [
                {"nombre": "Lunes", "mostrar": True, "html": ""},
                {"nombre": "Martes", "mostrar": True, "html": ""},
                {"nombre": "Miércoles", "mostrar": True, "html": ""},
                {"nombre": "Jueves", "mostrar": True, "html": ""},
                {"nombre": "Viernes", "mostrar": True, "html": ""},
                {"nombre": "Sábado", "mostrar": False, "html": ""},
            ],
        },
        "extras": [],
    }


def normalizar(datos: dict | None) -> dict:
    """Completa con valores por defecto cualquier campo que falte (archivos viejos o incompletos)."""
    base = datos_nuevos()
    if not isinstance(datos, dict):
        return base

    def mezclar(defecto, valor):
        if isinstance(defecto, dict) and isinstance(valor, dict):
            salida = {k: mezclar(v, valor[k]) if k in valor else copy.deepcopy(v) for k, v in defecto.items()}
            for k, v in valor.items():
                salida.setdefault(k, v)
            return salida
        if valor is None:
            return copy.deepcopy(defecto)
        return valor

    salida = mezclar(base, datos)
    if salida["pagina"].get("tamano") not in TAMANOS:
        salida["pagina"]["tamano"] = "oficio"
    for clave in ("docentes",):
        if not isinstance(salida["acompanamiento"].get(clave), list):
            salida["acompanamiento"][clave] = base["acompanamiento"][clave]
    if not isinstance(salida["agenda"].get("dias"), list):
        salida["agenda"]["dias"] = base["agenda"]["dias"]
    if not isinstance(salida.get("extras"), list):
        salida["extras"] = []
    salida["version"] = VERSION
    return salida


# --------------------------------------------------------------------------- fechas

def a_fecha(texto) -> date | None:
    if not texto:
        return None
    try:
        return datetime.strptime(str(texto)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def fecha_larga(f: date | None, con_anio: bool = False) -> str:
    if not f:
        return ""
    texto = f"{f.day} de {MESES[f.month - 1].capitalize()}"
    return f"{texto} de {f.year}" if con_anio else texto


def texto_semana(semana: dict) -> str:
    """«Semana del 16 al 20 de noviembre», contemplando semanas entre dos meses o dos años."""
    manual = (semana.get("texto") or "").strip()
    if manual:
        return manual
    ini, fin = a_fecha(semana.get("inicio")), a_fecha(semana.get("fin"))
    if not ini or not fin:
        return "Semana del # al # de MES"
    if ini.year != fin.year:
        return (f"Semana del {ini.day} de {MESES[ini.month - 1]} de {ini.year} "
                f"al {fin.day} de {MESES[fin.month - 1]} de {fin.year}")
    if ini.month != fin.month:
        return f"Semana del {ini.day} de {MESES[ini.month - 1]} al {fin.day} de {MESES[fin.month - 1]}"
    return f"Semana del {ini.day} al {fin.day} de {MESES[fin.month - 1]}"


def avance_periodo(info: dict, semana: dict) -> int:
    """Porcentaje del periodo transcurrido al cierre de la semana del boletín."""
    if not info.get("avance_auto", True):
        try:
            return max(0, min(100, round(float(info.get("avance") or 0))))
        except (TypeError, ValueError):
            return 0
    ini, fin = a_fecha(info.get("inicio")), a_fecha(info.get("fin"))
    ref = a_fecha(semana.get("fin")) or a_fecha(semana.get("inicio")) or date.today()
    if not ini or not fin or fin <= ini:
        try:
            return max(0, min(100, round(float(info.get("avance") or 0))))
        except (TypeError, ValueError):
            return 0
    return max(0, min(100, round((ref - ini).days * 100 / (fin - ini).days)))


def semanas_saber(info: dict, semana: dict) -> dict:
    """Devuelve las partes del texto «Quedan N semanas» para la tarjeta de la prueba."""
    if not info.get("saber_auto", True):
        valor = str(info.get("saber_semanas") or "#").strip() or "#"
    else:
        fecha = a_fecha(info.get("saber_fecha"))
        ref = a_fecha(semana.get("inicio")) or date.today()
        if not fecha:
            valor = "#"
        else:
            dias = (fecha - ref).days
            if dias < 0:
                return {"antes": "", "numero": "", "despues": "La prueba ya se presentó"}
            if dias < 7:
                return {"antes": "", "numero": "¡Es esta semana!", "despues": ""}
            valor = str(math.ceil(dias / 7))
    if valor == "1":
        return {"antes": "Queda", "numero": "1", "despues": "semana"}
    return {"antes": "Quedan", "numero": valor, "despues": "semanas"}


def titulo_dia(dia: dict, indice: int, agenda: dict, semana: dict) -> str:
    nombre = dia.get("nombre") or ""
    if agenda.get("mostrar_fechas"):
        ini = a_fecha(semana.get("inicio"))
        if ini:
            f = ini + timedelta(days=indice)
            return f"{nombre} {f.day} de {MESES[f.month - 1]}"
    return nombre
