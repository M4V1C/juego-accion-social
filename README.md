# Naranjonomía · El Reto de Emprender

Videojuego 2D de cartas por turnos, implementado en **Python + Pygame**, que sigue de forma estricta la especificación de diseño incluida en [specification-naranjonomia.md](specification-naranjonomia.md).

Está pensado para ejecutarse tanto en escritorio como en el navegador (WebAssembly) mediante **[pygbag](https://pygame-web.github.io/wiki/pygbag/)** y publicarse gratis en GitHub Pages.

Modo de juego: **Hotseat local** (2 jugadores compartiendo pantalla). No requiere red ni multijugador en línea.

---

## Estructura del proyecto

```
main.py            Punto de entrada asíncrono (compatible con pygbag)
constants.py       Dimensiones, paleta y reglas base
cards.py           Base de datos completa (24 plantillas · 2 copias c/u) y efectos
game.py            Player + Máquina de estados (GameController)
ui.py              Renderer con pygame.draw (sin assets externos)
requirements.txt   Dependencias mínimas
```

No hay imágenes, sonidos ni fuentes externas: el renderizado se hace con `pygame.draw` y `pygame.font.Font(None, ...)`. Esto mantiene el bundle final muy ligero.

---

## Ejecución local

1. Crear un entorno virtual e instalar dependencias:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Arrancar el juego:

   ```powershell
   python main.py
   ```

---

## Ejecución en el navegador con pygbag

1. Instalar pygbag (si no está ya en el entorno):

   ```powershell
   pip install pygbag
   ```

2. Servidor local de prueba:

   ```powershell
   pygbag main.py
   ```

   Abrir <http://localhost:8000> en un navegador con soporte WebAssembly (Chromium/Firefox modernos).

3. Build estático para GitHub Pages:

   ```powershell
   pygbag --build main.py
   ```

   Se genera la carpeta `build/web/` con todos los archivos estáticos.

---

## Publicación en GitHub Pages

1. Sube el repositorio a GitHub.
2. Ejecuta `pygbag --build main.py` para generar `build/web/`.
3. En GitHub, en **Settings → Pages**, publica desde la rama que aloja `build/web/` (por ejemplo `gh-pages`) o bien copia el contenido a la raíz de la rama `main` y sirve desde `/`.
4. Alternativa recomendada: workflow de GitHub Actions que ejecute pygbag en cada push y despliegue el resultado. Un ejemplo mínimo (`.github/workflows/deploy.yml`):

   ```yaml
   name: Deploy pygbag build
   on:
     push:
       branches: [main]
   jobs:
     build:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with: { python-version: "3.12" }
         - run: pip install pygame-ce pygbag
         - run: pygbag --build main.py
         - uses: peaceiris/actions-gh-pages@v4
           with:
             github_token: ${{ secrets.GITHUB_TOKEN }}
             publish_dir: ./build/web
   ```

---

## Reglas implementadas (resumen)

- **Recursos:** cada jugador comienza con **25 Monedas Creativas (MC)** y **0 PI**.
- **Mano:** máximo **5 cartas**; se reciben **4 iniciales** y se roba **1 al inicio de cada turno** (mezcla Naranja + Verde).
- **Máquina de estados:** `MENU_PRINCIPAL → INICIALIZACION → TURNO_PROXIMO → TURNO_ACCION → REVELAR_CONSECUENCIA → EVALUAR_VICTORIA → FIN_DE_JUEGO` (más un sub-estado `SELECCION_CARTA` para la Alianza Público-Privada).
- **Turno de acción:** el jugador activo puede **jugar 1 carta** o **pulsar PASAR**. En ambos casos se roba una carta Roja obligatoria al finalizar.
- **Mazos:** 2 copias de cada carta plantilla → **16 Naranjas + 16 Verdes + 16 Rojas**. El mazo Rojo se recicla desde el descarte al agotarse.
- **Victoria:**
  - Completar **3 proyectos Naranjas activos**, o
  - Que el oponente entre en **bancarrota (MC ≤ 0)**.
- **Pantalla final:** muestra PI, proyectos y **PIB Creativo Estimado** (multiplicador simbólico ×30 basado en el 3% del PIB global reportado por el BID) junto al mensaje pedagógico definido en la especificación.

Para el detalle de cada carta y su efecto teórico, consulta la sección 4 de [specification-naranjonomia.md](specification-naranjonomia.md).
