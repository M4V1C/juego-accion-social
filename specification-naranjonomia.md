# Especificación Técnica de Desarrollo: Naranjonomía - El Reto de Emprender

Este documento sirve como especificación completa de diseño de software y base de conocimiento para modelos de agentes encargados de programar el videojuego en **Python + Pygame**. Contiene la arquitectura del sistema, la lógica detallada del ciclo de juego, las fórmulas matemáticas de posicionamiento de UI, y la base de datos estructurada con el mazo de cartas fundamentado en la teoría de la Economía Naranja y las regulaciones tributarias de Costa Rica.

---

## 1. Arquitectura de Software y Máquina de Estados

El videojuego se estructurará como un juego de cartas local por turnos (*Hotseat* o pantalla compartida) para **2 jugadores** (Jugador 1 vs. Jugador 2). La lógica visual y del juego se gobernará mediante una **Máquina de Estados de un solo hilo**, lo que evitará condiciones de carrera y simplificará la compilación a WebAssembly (WASM) mediante `pygbag`.

### Clase `GameController` (Gestor de Estados)
La máquina de estados debe gestionar los siguientes contextos:

```python
class GameState(Enum):
    MENU_PRINCIPAL = 1      # Pantalla de inicio con logo y selección de personajes
    INICIALIZACION = 2      # Reparto de cartas iniciales y asignación de recursos
    TURNO_PROXIMO = 3       # Configura variables para el nuevo jugador activo
    TURNO_ACCION = 4        # Jugador activo interactúa: puede jugar Verde/Naranja o "Pasar"
    REVELAR_CONSECUENCIA = 5 # Fase obligatoria: se roba y aplica un Evento de Burocracia (Rojo)
    EVALUAR_VICTORIA = 6    # Comprobación de condiciones de fin de partida
    FIN_DE_JUEGO = 7        # Pantalla final con el ganador y desglose del PIB generado
```

---

## 2. Sistema de Recursos e Interfaz Gráfica (UI)

El lienzo de pantalla se configurará en resolución estándar de **1280 x 720 píxeles** (relación de aspecto 16:9), óptima para renderizarse en navegadores web bajo compilación WASM.

### Recursos del Jugador
Cada instancia de la clase `Player` mantendrá el control de:
*   **Monedas Creativas (MC):** Reserva monetaria utilizada para financiar proyectos y pagar obligaciones. (Comienzan con **25 MC**).
*   **Puntos de Propiedad Intelectual (PI):** Puntos de victoria acumulados de los proyectos completados de forma exitosa.
*   **Proyectos Completados:** Lista de cartas de Proyecto (Naranja) activas.
*   **Efectos Activos (Modificadores):** Banderas booleanas o temporizadores (ej. `tiene_oficina_virtual = True` o `descuento_ia_activo = True`).
*   **Mano Actual:** Lista de cartas del jugador (máximo 5 cartas).

### Layout Visual de la Pantalla (Coordenadas en Píxeles)
Para evitar el uso de librerías GUI complejas, la pantalla se segmentará en tres secciones horizontales bien definidas, utilizando `pygame.Rect` estáticos para el control de clics:

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ AREA SUPERIOR: Información del Oponente (Jugador Inactivo)               │
│ [MC: XX] [PI: XX] [Proyectos: X/3] [Modificadores Activos]               │
├──────────────────────────────────────────────────────────────────────────┤
│ AREA CENTRAL: Tablero de Juego Activo                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐        │
│  │ Evento de Turno  │  │ Proyecto Activo  │  │ Botón "PASAR" o  │        │
│  │ (Carta Roja)     │  │ (Cartas Naranjas)│  │ "Lanzar Dado"    │        │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘        │
├──────────────────────────────────────────────────────────────────────────┤
│ AREA INFERIOR: Mano del Jugador Activo (Fila de Cartas)                 │
│  ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐                         │
│  │Carta│   │Carta│   │Carta│   │Carta│   │Carta│                         │
│  │  1  │   │  2  │   │  3  │   │  4  │   │  5  │                         │
│  └─────┘   └─────┘   └─────┘   └─────┘   └─────┘                         │
└──────────────────────────────────────────────────────────────────────────┘
```

#### Fórmulas de Grid de Cartas para el Renderizador
Las cartas se dibujarán como rectángulos interactivos de **140 px de ancho por 200 px de alto** (`CARD_WIDTH = 140`, `CARD_HEIGHT = 200`).
Para calcular la coordenada `X` de cada carta en la mano del jugador de forma dinámica para que queden centradas:

```python
# Centrado dinámico de N cartas en pantalla
total_cards_width = (num_cartas * CARD_WIDTH) + ((num_cartas - 1) * CARD_GAP)
start_x = (SCREEN_WIDTH - total_cards_width) // 2
card_y = 480  # Fijo en la zona inferior de la pantalla

# Generar rectángulos de colisión para el gestor de eventos de mouse
for i, carta in enumerate(mano_jugador):
    x = start_x + i * (CARD_WIDTH + CARD_GAP)
    carta.rect = pygame.Rect(x, card_y, CARD_WIDTH, CARD_HEIGHT)
```

---

## 3. Flujo Lógico y Bucle del Juego (Pseudocódigo de Control)

Este algoritmo representa la estructura iterativa que el motor del juego ejecutará en cada fotograma. Debe utilizarse para estructurar la clase principal `App` de Pygame:

```python
import pygame
import sys

def main_game_loop():
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()
    
    # Inicialización de entidades del juego
    player1 = Player(nombre="Emprendedor 1", rol="Desarrollador de Software")
    player2 = Player(nombre="Emprendedor 2", rol="Cineasta e Industrias Culturales")
    controlador = GameController(player1, player2)
    
    while True:
        # 1. CAPTURA DE EVENTOS (INPUT)
        click_detectado = False
        pos_mouse = (0, 0)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Clic izquierdo
                    click_detectado = True
                    pos_mouse = event.pos

        # 2. ACTUALIZACIÓN DE LÓGICA SEGÚN ESTADO DE JUEGO
        if controlador.estado == GameState.MENU_PRINCIPAL:
            # Dibujar menú, esperar selección de personaje y clic en "Empezar"
            if click_detectado:
                evaluar_clics_menu(pos_mouse, controlador)
                
        elif controlador.estado == GameState.INICIALIZACION:
            # Crear y barajar mazos, repartir 4 cartas a cada uno, establecer MC iniciales
            controlador.inicializar_partida()
            controlador.estado = GameState.TURNO_PROXIMO
            
        elif controlador.estado == GameState.TURNO_PROXIMO:
            # Cambiar de jugador activo, reiniciar modificadores temporales de turno
            controlador.preparar_nuevo_turno()
            controlador.estado = GameState.TURNO_ACCION
            
        elif controlador.estado == GameState.TURNO_ACCION:
            # Esperar acción del jugador activo (clic en sus cartas o en botón "PASAR")
            if click_detectado:
                accion_realizada = procesar_clics_jugador(pos_mouse, controlador)
                if accion_realizada:
                    # Al jugar una carta, se evalúa su coste y se ejecuta su efecto
                    # Si el jugador pulsa "PASAR", se avanza a la fase de penalización/burocracia
                    controlador.estado = GameState.REVELAR_CONSECUENCIA
                    
        elif controlador.estado == GameState.REVELAR_CONSECUENCIA:
            # Se roba una carta del mazo Rojo (Burocracia de Costa Rica / Retos de Mercado)
            # Se muestra de forma emergente en pantalla y se le cobra la penalización al jugador
            if click_detectado and boton_aceptar_carta_roja.collidepoint(pos_mouse):
                controlador.aplicar_evento_rojo_y_descartar()
                controlador.estado = GameState.EVALUAR_VICTORIA
                
        elif controlador.estado == GameState.EVALUAR_VICTORIA:
            # Comprobar si el jugador activo tiene ya 3 Proyectos Naranjas completados
            # O si el oponente se quedó en bancarrota (MC <= 0)
            if controlador.comprobar_condiciones_victoria():
                controlador.estado = GameState.FIN_DE_JUEGO
            else:
                controlador.estado = GameState.TURNO_PROXIMO
                
        elif controlador.estado == GameState.FIN_DE_JUEGO:
            # Dibujar pantalla de victoria con análisis de "PI" y "PIB generado"
            if click_detectado and boton_reiniciar.collidepoint(pos_mouse):
                controlador.reiniciar_juego()

        # 3. RENDERIZADO (DIBUJADO EN PANTALLA)
        screen.fill(PALETA_COLORES["fondo_buttercream"])
        renderizar_elementos_segun_estado(screen, controlador)
        pygame.display.flip()
        clock.tick(30) # Límite de 30 FPS para ahorro de rendimiento
```

---

## 4. Base de Datos del Mazo de Cartas (Diseño Semántico de Datos)

El mazo de cartas está estrictamente fundamentado en las características de la Economía Naranja (talento, creatividad, propiedad intelectual) y en los desafíos reales de Costa Rica (burocracia de la CCSS, impuestos de Hacienda, marchamos, y cánones privados como ACAM).

### Estructura de Datos Base para una Carta
Cada carta debe ser modelada como un objeto en Python derivado de la clase `Card`:

```python
class CardType(Enum):
    PROYECTO = 1     # Cartas Naranjas (Victoria y generación de ingresos)
    IMPULSOR = 2     # Cartas Verdes (Beneficios, reducciones de coste, IA avanzada)
    CONSECUENCIA = 3 # Cartas Rojas (Burocracia costarricense y multas)

class Card:
    def __init__(self, id, nombre, tipo, subtipo, coste, puntos_pi, descripcion, efecto_func):
        self.id = id                    # Identificador numérico único
        self.nombre = nombre            # Nombre de la carta
        self.tipo = tipo                # Instancia de CardType
        self.subtipo = subtipo          # Ej: "Software", "Artes", "Patrimonio", "Trámite"
        self.coste = coste              # Coste en Monedas Creativas (MC) para jugarse
        self.puntos_pi = puntos_pi      # Puntos de Propiedad Intelectual aportados al completarse
        self.descripcion = descripcion  # Texto descriptivo para la UI
        self.efecto_func = efecto_func  # Puntero a función lambda/método que ejecuta la lógica
        self.rect = None                # Asignado dinámicamente por la interfaz de Pygame
```

---

### CATALOGO COMPLETO DE CARTAS (La Base de Datos del Motor)

#### A. Mazo de Proyectos (Cartas Naranjas - Industrias Creativas)
Estas cartas se juegan desde la mano pagando su coste en MC. Aportan puntos de Propiedad Intelectual (PI) para la victoria final y generan ingresos recurrentes en MC al final de cada turno.

| ID | Nombre del Proyecto | Subtipo | Coste (MC) | Puntos de PI | Ingresos por Turno (MC) | Efecto Teórico y Regla de Juego |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **O1** | **Ecosistema de Software y Apps** | Soft Creativo | 15 | 1 | +3 | **Sinergia Digital:** Si tienes activo el soporte *"Claude CoWork"*, el coste de este proyecto disminuye permanentemente a 7 MC. |
| **O2** | **Desarrollo de Videojuegos** | Soft Creativo | 20 | 2 | +5 | **Propiedad Intelectual Activa:** Al completarse, permite robar inmediatamente 1 carta de Soporte (Verde) gratis. |
| **O3** | **Producción de Largometraje** | Audiovisual | 25 | 3 | +8 | **Encadenamiento Productivo:** Al jugarla, el resto de los jugadores recibe 3 MC por impacto local (hoteles, transporte), pero tú ganas 12 MC en tu siguiente turno. |
| **O4** | **Álbum de Música de Estudio** | Artes e Ind. | 10 | 1 | +2 | **Derechos de Propiedad Intelectual:** Aumenta en +1 MC los ingresos de todos tus otros proyectos activos. |
| **O5** | **Ruta de Turismo de Comunidad** | Patrimonio/Turismo | 12 | 1 | +3 | **Patrimonio Sostenible:** Inmune a cualquier evento impositivo de vehículos (Marchamos o traspasos). |
| **O6** | **Complejo Gastronómico Local** | Gastronomía | 15 | 2 | +4 | **Fusión Cultural:** Al jugarla, reduce en 5 MC el coste del próximo proyecto de *"Artes Escénicas"* que decidas financiar. |
| **O7** | **Pasarela de Moda y Diseño** | Diseño/Moda | 10 | 1 | +2 | **Impacto Visual:** Te permite descartar una carta de tu mano para robar 2 cartas adicionales del mazo principal. |
| **O8** | **Teatro de Artes Escénicas** | Artes / Cultura | 12 | 2 | +3 | **Punto de Encuentro:** El oponente debe pagarte 2 MC en concepto de "entradas" al inicio de su próximo turno. |

---

#### B. Mazo de Soportes e Impulsores (Cartas Verdes - Innovación y Mitigación)
Se juegan desde la mano pagando su coste en MC. Aportan modificadores directos, defensas de bufete o reducciones de impuestos basadas en las mejores prácticas de la economía moderna.

| ID | Nombre de la Carta | Coste (MC) | Tipo de Modificador | Efecto Teórico y Regla de Juego |
| :---: | :--- | :---: | :--- | :--- |
| **G1** | **Claude CoWork (IA avanzada)** | 5 | Permanente (Jugador) | **La IA como Colaborador:** El jugador entra en modo de orquestación digital avanzada. Todos los proyectos de *Software, Videojuegos y Diseño* reducen su coste un **50%** de forma permanente. |
| **G2** | **Oficina Virtual Registrada** | 4 | Permanente (Jugador) | **Emprendimiento sin Cadenas:** Inmuniza de por vida al jugador contra las multas por carecer de oficinas físicas o no poseer recibo de servicios (Bloquea el evento *"Rechazo de CCSS"*). |
| **G3** | **Alianza Público-Privada (APP)** | 3 | Inmediato | **Gobierno Local Ágil:** Te permite robar y ver las 2 siguientes cartas del mazo de Proyectos (Naranja), quedarte con una en tu mano y descartar la otra. |
| **G4** | **Incubadora Ruta N (Medellín)**| 6 | Permanente (Jugador) | **Ecosistema Innovador:** El jugador se traslada mentalmente al complejo tecnológico y cultural Ruta N. Aumenta en **+2 MC** todos tus ingresos pasivos de proyectos por turno de por vida. |
| **G5** | **Parque Biblioteca España** | 5 | Inmediato / Social | **Valor Social y Cohesión:** Transforma tu entorno cultural. Aumenta los ingresos de tu proyecto más barato en **+4 MC** por turno. |
| **G6** | **Propiedad Intelectual Protegida** | 3 | Permanente (Defensivo) | **Patente de Ideas:** Inmuniza por completo al jugador contra los cánones de propiedad intelectual privados (Anula el cobro del evento *"ACAM"*). |
| **G7** | **Abogado Corporativo (Bufete)** | 4 | Permanente (Defensivo) | **Garantía Legal:** Cancela el efecto de cualquier evento tributario o de inspección de Hacienda que te obligue a pagar más de 10 MC. |
| **G8** | **Educación Creativa Especializada**| 3 | Inmediato | **Formación del Talento:** Aumenta permanentemente tus puntos de Propiedad Intelectual (PI) actuales en **+1 PI** gracias a la especialización del personal. |

---

#### C. Mazo de Obstáculos y Burocracia (Cartas Rojas - Carga Regulatoria)
Estas cartas se roban obligatoriamente de forma aleatoria al final de cada turno. Representan el caótico panorama institucional de Costa Rica (CCSS, Hacienda, Municipalidades, Cánones privados), actuando como "jefes" u obstáculos de la vida del emprendedor.

| ID | Trámite o Evento Impositivo | Causa Teórica (Basada en las Fuentes) | Penalización o Coste Financiero (MC) | Forma de Evitar / Mitigar |
| :---: | :--- | :--- | :---: | :--- |
| **R1** | **Rechazo de CCSS por Dirección Física** | La Caja Costarricense de Seguro Social te deniega la inscripción patronal por operar de forma 100% digital sin local tradicional o recibo de luz. | **Pierdes 1 Turno completo** o debes pagar **10 MC** para alquilar una oficina ficticia inútil. | Inmune si tienes activa la carta de soporte *"Oficina Virtual Registrada"*. |
| **R2** | **Cargas Sociales Patronales (26.33%)** | Pago obligatorio calculado sobre planilla: CCSS Salud (14.75%), Pensión IVM (4.75%), INA, IMAS, Banco Popular y FODESAF (5%). | Paga **5 MC** de manera inmediata por cada proyecto de software, cine, videojuego o gastronomía activo. | No aplicable a proyectos de *Turismo Comunitario* ni *Artes Escénicas*. |
| **R3** | **Impuesto de Marchamo Vehicular** | Se cobra el marchamo de tu vehículo de distribución con tasas altísimas: 58% de impuesto a la propiedad, 25% de SOA y cobros municipales varios. | Paga **8 MC** de forma inmediata a la caja del Estado. | Inmune si tienes activo el soporte *"Ruta de Turismo de Comunidad"*. |
| **R4** | **Canon Privado por Música (ACAM)** | La Asociación Costarricense de Autores Musicales te impone un cobro privado por utilizar ambientación acústica en tus actividades creativas o de servicios. | Pierdes **6 MC** de tu reserva de forma inmediata. | Inmune si posees la carta *"Propiedad Intelectual Protegida"*. |
| **R5** | **Registro y Timbres del CFIA** | Se te exige registrar los planos y pagar tasas y timbres obligatorios del Colegio Federal de Ingenieros y Arquitectos (~2% del valor del proyecto). | Paga **10 MC** para poder mantener activo tu proyecto de *Teatro o Complejo Gastronómico*. | Puedes elegir descartar uno de esos proyectos si decides no pagar la tasa. |
| **R6** | **Ajuste Impositivo de Hacienda (IVA)** | Declaración obligatoria de IVA del 13% mensual y renta trimestral. El sistema del Estado del siglo XX requiere un proceso engorroso. | Paga **12 MC** por problemas con el llenado digital de formularios redundantes en PDF. | Inmune si tienes la carta de soporte *"Abogado Corporativo (Bufete)"*. |
| **R7** | **Impuesto de Construcción Municipal (1%)**| La municipalidad te inspecciona y cobra un 1% sobre el valor del local comercial por mejoras físicas realizadas para tu negocio. | Paga **7 MC** de tasas e impuestos municipales de obras. | Puedes mitigar un **50%** del coste si tienes activa una *"Alianza Público-Privada (APP)"*. |
| **R8** | **Impuesto a las Personas Jurídicas** | Impuesto anual obligatorio para mantener tu sociedad mercantil (SA o SRL) activa en el Registro Nacional de Costa Rica. | Paga **5 MC** de manera inmediata. | Si no tienes fondos, la sociedad queda disuelta: descarta 1 proyecto activo. |

---

## 5. Criterios de Victoria y Fin de Partida

La partida finaliza de forma inmediata si se cumple una de las siguientes condiciones:

1.  **Líder en Propiedad Intelectual (PI):** El primer jugador que logre completar de manera exitosa **3 Proyectos Naranjas** en su zona de juego activa y tenga sus impuestos de la CCSS al día se consagra como el *«Orquestador del Ecosistema Creativo»* y gana la partida.
2.  **Bancarrota Institucional:** Si la reserva de Monedas Creativas (MC) de un jugador desciende a **0 o menos** al final de un turno debido a cobros de la CCSS o multas de Hacienda, queda eliminado de forma inmediata. Su oponente es declarado ganador por defecto, habiendo sobrevivido al "deporte extremo" de emprender en el país.

### Pantalla de Resultados y Concientización Cultural
La escena final de juego presentará un informe pedagógico basado en las fuentes oficiales para concientizar al estudiante:
*   Mostrará el total de **Puntos de Propiedad Intelectual (PI)** acumulados.
*   Calculará el **PIB Creativo Estimado:** Multiplicará los puntos de PI por un multiplicador que emula el dato del BID, donde la Economía Naranja aporta el **3% del PIB global** y genera millones de empleos directos.
*   Mensaje educativo final: *"¡Felicidades! Lograste surfear la burocracia institucional del siglo XX y generaste valor social a través del talento. La cultura de tu país vale mucho: ¡Aprovéchala!"*

---
**Nota para el Agente Programador:** Al inicializar el juego en Pygame, puedes implementar el renderizado de cartas usando `pygame.draw.rect()` de manera directa, pintando el fondo de la carta del color correspondiente a su tipo (Naranja = Proyectos, Verde = Soportes, Rojo = Burocracia) y utilizando `pygame.font` con ajuste de línea de palabras para la descripción de los efectos dinámicos. Esto mantendrá el juego con un peso mínimo de KB y compatible para su carga directa en navegadores web con `pygbag`.