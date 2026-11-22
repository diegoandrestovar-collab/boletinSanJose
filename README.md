# Boletín Institucional – I. E. San José (Oporapa, Huila)

Aplicación de escritorio en Python para diligenciar el boletín semanal con un formulario,
previsualizarlo separado en hojas tamaño oficio y exportarlo a PDF.

## Cómo funciona

1. **Formulario** (panel izquierdo): pestañas General, Mensaje, Información, Recomendaciones,
   Acompañamiento, Agenda y Extras. Los textos largos usan un editor enriquecido con negrita,
   colores, listas, **tablas** e **imágenes**.
2. **HTML**: con cada cambio, Python genera el HTML del boletín (`boletin/render.py` + plantilla Jinja2).
3. **Vista previa** (panel derecho): el HTML se reparte en hojas del tamaño elegido. Las tarjetas de
   los días crecen con el contenido; si una no cabe, continúa en la hoja siguiente
   (párrafo a párrafo, viñeta a viñeta o fila a fila en las tablas, repitiendo el encabezado).
4. **PDF**: se imprime exactamente lo que muestra la vista previa (texto real, no imagen).

## Instalación

Requiere Python 3.10 o superior.

**Windows:** doble clic en `ejecutar.bat` (la primera vez crea el entorno e instala lo necesario).

**Manual (Windows, Linux o macOS):**

```
python -m venv .venv
.venv\Scripts\activate          (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
python main.py
```

Para repartirlo sin instalar Python: `crear_ejecutable.bat` genera `dist\BoletinInstitucional\`.

## Uso

| Acción | Atajo |
|---|---|
| Nuevo / Abrir / Guardar (`.boletin`) | Ctrl+N / Ctrl+O / Ctrl+S |
| Exportar PDF | Ctrl+E |
| Acercar / Alejar / Ajustar al ancho | Ctrl++ / Ctrl+- / Ctrl+0 |
| Regenerar la vista previa | F5 |

- **Semana:** al elegir el lunes se propone el viernes y el texto de la franja verde se escribe solo.
- **Avance del periodo** y **semanas para la Prueba Saber** se calculan con las fechas
  (se pueden escribir a mano desmarcando la casilla).
- **Acompañamiento:** lista editable de docentes y zonas; «Rotar zonas» pasa cada zona al docente siguiente.
- **Agenda:** cada día se puede incluir u ocultar (el sábado viene oculto). Los colores se alternan
  verde, azul y naranja como en la plantilla.
- **Hoja:** Oficio 21,6 × 35,6 cm (el de la plantilla original), Oficio 21,6 × 33 cm o Carta.
- Si un bloque no cabe ni en una hoja completa (por ejemplo una imagen enorme), la vista previa lo
  marca con borde rojo punteado y la barra de estado lo avisa.

Sin abrir la ventana:

```
python main.py ejemplos/ejemplo.boletin --pdf boletin.pdf
python main.py ejemplos/ejemplo.boletin --html boletin.html
```

## Estructura

```
main.py                        punto de entrada (ventana o exportación por consola)
boletin/app.py                 ventana principal (PySide6 + QtWebEngine)
boletin/modelo.py              datos por defecto, docentes, cálculo de fechas
boletin/render.py              datos → HTML (Jinja2)
boletin/exportar.py            HTML → PDF
boletin/recursos/plantilla/    boletin.html.j2, boletin.css, paginar.js  ← diseño del documento
boletin/recursos/editor/       formulario (HTML/JS) y editor de texto SunEditor
boletin/recursos/img/          encabezados, pie, mapa e iconos tomados de la plantilla
```

Para cambiar colores, márgenes o tipografías edite `boletin.css`; para cambiar los textos fijos o la
lista de docentes por defecto, `modelo.py`.

Componentes de terceros incluidos: SunEditor (MIT) y la fuente Poppins (SIL OFL).
