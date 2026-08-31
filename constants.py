# -*- coding: utf-8 -*-
"""Constantes globales: dimensiones, colores, tamaños de UI.

Sigue el layout definido en specification-naranjonomia.md, sección 2.
"""

# Lienzo 1280x720 (16:9) para pygbag/WebAssembly.
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 30

# Dimensiones de carta indicadas en la especificación.
CARD_WIDTH = 140
CARD_HEIGHT = 200
CARD_GAP = 20
HAND_Y = 480  # fila inferior fija

# Áreas horizontales.
AREA_SUPERIOR_H = 90
AREA_INFERIOR_Y = 470

# Paleta ajustada al fondo "buttercream" y familia cromática Naranja/Verde/Rojo.
COLORS = {
    "fondo_buttercream":  (255, 245, 220),
    "naranja":            (255, 140,  40),
    "naranja_claro":      (255, 190, 120),
    "verde":              ( 60, 180,  90),
    "verde_claro":        (150, 220, 170),
    "rojo":               (220,  70,  70),
    "rojo_claro":         (240, 150, 150),
    "gris_oscuro":        ( 40,  40,  50),
    "gris_medio":         (110, 110, 120),
    "gris_claro":         (215, 215, 225),
    "blanco":             (255, 255, 255),
    "negro":              ( 20,  20,  30),
    "azul_boton":         ( 60, 100, 200),
    "azul_hover":         ( 90, 140, 230),
    "amarillo":           (255, 210,  60),
    "azul_texto":         ( 30,  60, 130),
    "panel_oponente":     (230, 220, 200),
    "panel_activo":       (250, 235, 200),
}

# Botones estáticos en pantalla (rectángulos).
BTN_PASAR_RECT       = (1050, 500, 200, 60)   # esquina inferior-derecha del área central
BTN_ACEPTAR_RECT     = (SCREEN_WIDTH // 2 - 90, 560, 180, 55)
BTN_REINICIAR_RECT   = (SCREEN_WIDTH // 2 - 110, 600, 220, 60)
BTN_EMPEZAR_RECT     = (SCREEN_WIDTH // 2 - 120, 550, 240, 70)

# Reglas económicas base.
MC_INICIAL = 25
HAND_MAX = 5
INITIAL_HAND = 4
PROYECTOS_PARA_GANAR = 3

# Multiplicador BID para el "PIB Creativo Estimado" en la pantalla final.
# La Economía Naranja aporta ~3% del PIB global, este multiplicador es simbólico.
PIB_MULTIPLICADOR = 30
