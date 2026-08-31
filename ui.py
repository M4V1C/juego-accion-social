# -*- coding: utf-8 -*-
"""Renderer de Pygame para Naranjonomía.

Sólo utiliza primitivas de dibujo (`pygame.draw`) y `pygame.font.Font(None, ...)`.
No hay assets externos, lo que mantiene el peso mínimo para pygbag (WebAssembly).
"""
from __future__ import annotations

from typing import List, Optional

import pygame

from cards import Card, CardType
from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLORS,
    CARD_WIDTH, CARD_HEIGHT, CARD_GAP, HAND_Y,
    AREA_SUPERIOR_H, AREA_INFERIOR_Y, PROYECTOS_PARA_GANAR,
    PIB_MULTIPLICADOR,
)
from game import GameController, GameState, Player


# ---------------------------------------------------------------------------
# Utilidad: word-wrap para descripciones dinámicas dentro de una carta.
# ---------------------------------------------------------------------------

def _wrap_text(font: pygame.font.Font, text: str, max_w: int) -> List[str]:
    palabras = text.split()
    lineas: List[str] = []
    actual = ""
    for w in palabras:
        prueba = (actual + " " + w).strip()
        if font.size(prueba)[0] <= max_w:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = w
    if actual:
        lineas.append(actual)
    return lineas


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        # Fuentes por defecto (sin dependencia de archivos externos).
        self.font_xs = pygame.font.Font(None, 16)
        self.font_sm = pygame.font.Font(None, 20)
        self.font_md = pygame.font.Font(None, 26)
        self.font_lg = pygame.font.Font(None, 36)
        self.font_xl = pygame.font.Font(None, 56)

    # ------------------------------------------------------------------ entrada
    def draw(self, ctrl: GameController) -> None:
        self.screen.fill(COLORS["fondo_buttercream"])
        estado = ctrl.estado
        if estado == GameState.MENU_PRINCIPAL:
            self._draw_menu(ctrl)
        elif estado == GameState.FIN_DE_JUEGO:
            self._draw_end_screen(ctrl)
        else:
            self._draw_juego(ctrl)

    # -------------------------------------------------------------------- menú
    def _draw_menu(self, ctrl: GameController) -> None:
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT
        # Título.
        titulo = "NARANJONOMÍA"
        subtitulo = "El Reto de Emprender"
        surf_t = self.font_xl.render(titulo, True, COLORS["naranja"])
        surf_s = self.font_lg.render(subtitulo, True, COLORS["azul_texto"])
        self.screen.blit(surf_t, surf_t.get_rect(center=(w // 2, 130)))
        self.screen.blit(surf_s, surf_s.get_rect(center=(w // 2, 190)))

        # Bloque de personajes.
        pygame.draw.rect(self.screen, COLORS["naranja_claro"],
                         (w // 2 - 350, 260, 700, 220), border_radius=16)
        self._render_multiline(
            [
                "Jugador 1: Desarrollador de Software",
                "Jugador 2: Cineasta e Industrias Culturales",
                "",
                "Modo Hotseat local · 2 jugadores comparten pantalla",
                "Objetivo: completar 3 proyectos Naranjas sin quebrar por burocracia",
            ],
            self.font_md,
            COLORS["negro"],
            x=w // 2 - 320,
            y=280,
            line_h=32,
        )

        # Botón "Empezar".
        self._draw_button(ctrl.rect_empezar, "EMPEZAR", COLORS["azul_boton"])

        # Pie: notas culturales.
        pie = "Basado en la Economía Naranja del BID y la carga regulatoria de Costa Rica"
        surf = self.font_sm.render(pie, True, COLORS["gris_medio"])
        self.screen.blit(surf, surf.get_rect(center=(w // 2, h - 40)))

    # ------------------------------------------------------------------ partida
    def _draw_juego(self, ctrl: GameController) -> None:
        # Actualizar rectángulos dinámicos de la mano del jugador activo.
        self._layout_mano(ctrl.jugador_activo)

        self._draw_area_superior(ctrl)
        self._draw_area_central(ctrl)
        self._draw_area_inferior(ctrl)

        # Overlays.
        if ctrl.estado == GameState.REVELAR_CONSECUENCIA:
            self._draw_overlay_carta_roja(ctrl)
        elif ctrl.estado == GameState.SELECCION_CARTA:
            self._draw_overlay_seleccion(ctrl)

        # Log inferior.
        self._draw_log(ctrl)

    # ---------------------- áreas
    def _draw_area_superior(self, ctrl: GameController) -> None:
        oponente = ctrl.oponente
        pygame.draw.rect(self.screen, COLORS["panel_oponente"],
                         (0, 0, SCREEN_WIDTH, AREA_SUPERIOR_H))
        pygame.draw.line(self.screen, COLORS["gris_medio"],
                         (0, AREA_SUPERIOR_H), (SCREEN_WIDTH, AREA_SUPERIOR_H), 2)

        etiqueta = f"OPONENTE — {oponente.nombre} ({oponente.rol})"
        surf = self.font_sm.render(etiqueta, True, COLORS["negro"])
        self.screen.blit(surf, (20, 10))

        stats = (f"MC: {oponente.mc}   |   PI: {oponente.pi}   |   "
                 f"Proyectos: {len(oponente.proyectos)}/{PROYECTOS_PARA_GANAR}   |   "
                 f"Mano: {len(oponente.mano)}")
        surf = self.font_md.render(stats, True, COLORS["azul_texto"])
        self.screen.blit(surf, (20, 34))

        # Modificadores.
        modificadores = self._modificadores_texto(oponente)
        surf = self.font_xs.render(modificadores, True, COLORS["gris_oscuro"])
        self.screen.blit(surf, (20, 66))

    def _draw_area_central(self, ctrl: GameController) -> None:
        pygame.draw.rect(self.screen, COLORS["panel_activo"],
                         (0, AREA_SUPERIOR_H, SCREEN_WIDTH, AREA_INFERIOR_Y - AREA_SUPERIOR_H))

        # Zona 1: espacio para carta de evento (visible sólo en overlay).
        rect_evento = pygame.Rect(60, 120, 220, 300)
        pygame.draw.rect(self.screen, COLORS["blanco"], rect_evento, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["rojo"], rect_evento, 3, border_radius=8)
        etiqueta = self.font_sm.render("Evento de Turno", True, COLORS["rojo"])
        self.screen.blit(etiqueta, etiqueta.get_rect(center=(rect_evento.centerx, rect_evento.y + 16)))
        # Al no haber evento, mostrar contador del mazo rojo.
        info = f"Mazo Rojo: {len(ctrl.mazo_rojo)}   Descarte: {len(ctrl.descarte_rojo)}"
        surf = self.font_xs.render(info, True, COLORS["gris_medio"])
        self.screen.blit(surf, surf.get_rect(center=(rect_evento.centerx, rect_evento.bottom - 20)))

        # Zona 2: proyectos activos del jugador activo.
        rect_proj = pygame.Rect(310, 120, 720, 300)
        pygame.draw.rect(self.screen, COLORS["blanco"], rect_proj, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["naranja"], rect_proj, 3, border_radius=8)
        etiqueta = self.font_sm.render(
            f"Proyectos activos de {ctrl.jugador_activo.nombre}",
            True, COLORS["naranja"])
        self.screen.blit(etiqueta, (rect_proj.x + 10, rect_proj.y + 6))
        # Mini cartas de proyectos activos.
        for i, p in enumerate(ctrl.jugador_activo.proyectos):
            r = pygame.Rect(rect_proj.x + 20 + i * 230, rect_proj.y + 40, 210, 240)
            self._draw_card(p, r, mini=True)

        # Zona 3: información de turno / botón PASAR.
        rect_turno = pygame.Rect(1060, 120, 200, 300)
        pygame.draw.rect(self.screen, COLORS["blanco"], rect_turno, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["azul_texto"], rect_turno, 3, border_radius=8)
        etiqueta = self.font_sm.render("Turno actual", True, COLORS["azul_texto"])
        self.screen.blit(etiqueta, etiqueta.get_rect(center=(rect_turno.centerx, rect_turno.y + 18)))

        info = [
            ctrl.jugador_activo.nombre,
            ctrl.jugador_activo.rol,
            "",
            f"MC: {ctrl.jugador_activo.mc}",
            f"PI: {ctrl.jugador_activo.pi}",
            f"Ingresos/turno: {ctrl.jugador_activo.ingresos_totales()}",
        ]
        y = rect_turno.y + 55
        for linea in info:
            surf = self.font_sm.render(linea, True, COLORS["negro"])
            self.screen.blit(surf, surf.get_rect(center=(rect_turno.centerx, y)))
            y += 22

        # Botón PASAR (visible en fase de acción).
        if ctrl.estado == GameState.TURNO_ACCION:
            self._draw_button(ctrl.rect_pasar, "PASAR TURNO", COLORS["azul_boton"])

    def _draw_area_inferior(self, ctrl: GameController) -> None:
        pygame.draw.rect(self.screen, COLORS["gris_claro"],
                         (0, AREA_INFERIOR_Y, SCREEN_WIDTH, SCREEN_HEIGHT - AREA_INFERIOR_Y))
        etiqueta = f"MANO DE {ctrl.jugador_activo.nombre}  ·  clic para jugar"
        surf = self.font_sm.render(etiqueta, True, COLORS["negro"])
        self.screen.blit(surf, (20, AREA_INFERIOR_Y + 4))
        for carta in ctrl.jugador_activo.mano:
            if carta.rect is not None:
                self._draw_card(carta, carta.rect,
                                highlight=(ctrl.estado == GameState.TURNO_ACCION),
                                affordable=(ctrl.jugador_activo.mc >= ctrl.jugador_activo.coste_efectivo(carta)))

    # ---------------------- overlays
    def _draw_overlay_carta_roja(self, ctrl: GameController) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        carta = ctrl.carta_roja_actual
        if carta is None:
            # Sin carta: sólo mostrar botón continuar.
            self._draw_button(ctrl.rect_aceptar, "CONTINUAR", COLORS["rojo"])
            return

        w, h = 300, 380
        r = pygame.Rect((SCREEN_WIDTH - w) // 2, 120, w, h)
        self._draw_card(carta, r, big=True)

        # Texto explicativo.
        texto = "BUROCRACIA CR — Aplica al jugador activo"
        surf = self.font_sm.render(texto, True, COLORS["blanco"])
        self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, 90)))

        self._draw_button(ctrl.rect_aceptar, "ACEPTAR EVENTO", COLORS["rojo"])

    def _draw_overlay_seleccion(self, ctrl: GameController) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))
        texto = "Alianza Público-Privada · elige 1 carta para conservar"
        surf = self.font_md.render(texto, True, COLORS["blanco"])
        self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, 200)))
        for c in ctrl.seleccion_pendiente:
            if c.rect:
                self._draw_card(c, c.rect, highlight=True, affordable=True)

    # ---------------------- log
    def _draw_log(self, ctrl: GameController) -> None:
        x, y0 = 20, SCREEN_HEIGHT - 130
        for i, msg in enumerate(ctrl.log[-5:]):
            surf = self.font_xs.render(msg, True, COLORS["gris_oscuro"])
            self.screen.blit(surf, (x, y0 + i * 16))

    # ---------------------- final
    def _draw_end_screen(self, ctrl: GameController) -> None:
        w = SCREEN_WIDTH
        # Título.
        surf = self.font_xl.render("Fin de la Partida", True, COLORS["naranja"])
        self.screen.blit(surf, surf.get_rect(center=(w // 2, 90)))

        ganador = ctrl.ganador
        if ganador is None:
            surf = self.font_lg.render("Sin ganador definido.", True, COLORS["negro"])
            self.screen.blit(surf, surf.get_rect(center=(w // 2, 200)))
            self._draw_button(ctrl.rect_reiniciar, "REINICIAR", COLORS["azul_boton"])
            return

        surf = self.font_lg.render(
            f"Ganador: {ganador.nombre} ({ganador.rol})", True, COLORS["azul_texto"])
        self.screen.blit(surf, surf.get_rect(center=(w // 2, 160)))

        pib = ganador.pi * PIB_MULTIPLICADOR
        infos = [
            f"Puntos de Propiedad Intelectual (PI): {ganador.pi}",
            f"Proyectos completados: {len(ganador.proyectos)} / {PROYECTOS_PARA_GANAR}",
            f"Monedas Creativas restantes: {ganador.mc} MC",
            f"PIB Creativo Estimado: {pib} (multiplicador BID x{PIB_MULTIPLICADOR})",
        ]
        y = 220
        for txt in infos:
            surf = self.font_md.render(txt, True, COLORS["negro"])
            self.screen.blit(surf, surf.get_rect(center=(w // 2, y)))
            y += 34

        mensaje = ("¡Felicidades! Lograste surfear la burocracia institucional del siglo XX "
                   "y generar valor social a través del talento.")
        for linea in _wrap_text(self.font_md, mensaje, w - 200):
            surf = self.font_md.render(linea, True, COLORS["verde"])
            self.screen.blit(surf, surf.get_rect(center=(w // 2, y)))
            y += 30

        self._draw_button(ctrl.rect_reiniciar, "REINICIAR", COLORS["azul_boton"])

    # ---------------------- carta
    def _draw_card(self, carta: Card, rect: pygame.Rect,
                   highlight: bool = False, affordable: bool = True,
                   mini: bool = False, big: bool = False) -> None:
        color_borde, color_fondo = self._colores_por_tipo(carta.tipo)
        pygame.draw.rect(self.screen, color_fondo, rect, border_radius=10)
        borde_grosor = 4 if (highlight and affordable) else 2
        pygame.draw.rect(self.screen, color_borde, rect, borde_grosor, border_radius=10)

        # Ribbon superior con nombre.
        ribbon = pygame.Rect(rect.x, rect.y, rect.w, 34)
        pygame.draw.rect(self.screen, color_borde, ribbon, border_top_left_radius=10, border_top_right_radius=10)
        font_nombre = self.font_sm if not big else self.font_md
        # Ajustar nombre a 2 líneas si es necesario.
        lineas_nombre = _wrap_text(font_nombre, carta.nombre, rect.w - 10)[:2]
        for i, ln in enumerate(lineas_nombre):
            surf = font_nombre.render(ln, True, COLORS["blanco"])
            self.screen.blit(surf, surf.get_rect(center=(rect.centerx, rect.y + 12 + i * 14)))

        # Coste (esquina inferior izq).
        if carta.tipo != CardType.CONSECUENCIA:
            coste_txt = f"{carta.coste} MC"
            surf = self.font_sm.render(coste_txt, True, COLORS["negro"])
            self.screen.blit(surf, (rect.x + 6, rect.bottom - 22))

        # PI / Ingresos (esquina inferior der para proyectos).
        if carta.tipo == CardType.PROYECTO:
            info = f"PI:{carta.puntos_pi}  +{carta.ingresos}/t"
            surf = self.font_xs.render(info, True, COLORS["negro"])
            self.screen.blit(surf, (rect.right - surf.get_width() - 6, rect.bottom - 20))

        # Subtipo.
        if carta.subtipo:
            surf = self.font_xs.render(carta.subtipo, True, COLORS["gris_oscuro"])
            self.screen.blit(surf, (rect.x + 6, rect.y + 40))

        # Descripción.
        desc_y = rect.y + 62
        max_w = rect.w - 14
        font_desc = self.font_xs
        lineas = _wrap_text(font_desc, carta.descripcion, max_w)
        max_lineas = (rect.h - 90) // 14
        for ln in lineas[:max_lineas]:
            surf = font_desc.render(ln, True, COLORS["negro"])
            self.screen.blit(surf, (rect.x + 7, desc_y))
            desc_y += 14

        # Overlay de "no puedo pagar".
        if not affordable and carta.tipo != CardType.CONSECUENCIA:
            veil = pygame.Surface(rect.size, pygame.SRCALPHA)
            veil.fill((0, 0, 0, 90))
            self.screen.blit(veil, rect.topleft)

    # ---------------------- botones
    def _draw_button(self, rect: pygame.Rect, texto: str, color) -> None:
        mouse = pygame.mouse.get_pos()
        activo = rect.collidepoint(mouse)
        c = COLORS["azul_hover"] if (activo and color == COLORS["azul_boton"]) else color
        pygame.draw.rect(self.screen, c, rect, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["negro"], rect, 2, border_radius=10)
        surf = self.font_md.render(texto, True, COLORS["blanco"])
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    # ---------------------- helpers
    def _colores_por_tipo(self, tipo: CardType):
        if tipo == CardType.PROYECTO:
            return COLORS["naranja"], COLORS["naranja_claro"]
        if tipo == CardType.IMPULSOR:
            return COLORS["verde"], COLORS["verde_claro"]
        return COLORS["rojo"], COLORS["rojo_claro"]

    def _layout_mano(self, jugador: Player) -> None:
        cartas = jugador.mano
        n = len(cartas)
        if n == 0:
            return
        total_w = n * CARD_WIDTH + (n - 1) * CARD_GAP
        start_x = (SCREEN_WIDTH - total_w) // 2
        for i, c in enumerate(cartas):
            x = start_x + i * (CARD_WIDTH + CARD_GAP)
            c.rect = pygame.Rect(x, HAND_Y, CARD_WIDTH, CARD_HEIGHT)

    def _modificadores_texto(self, jugador: Player) -> str:
        activos = []
        if jugador.tiene_claude_cowork:      activos.append("Claude CoWork")
        if jugador.tiene_oficina_virtual:    activos.append("Oficina Virtual")
        if jugador.tiene_incubadora_ruta_n:  activos.append("Ruta N")
        if jugador.tiene_propiedad_intelectual: activos.append("PI Protegida")
        if jugador.tiene_abogado:            activos.append("Abogado")
        if jugador.tiene_alianza_app:        activos.append("Alianza APP")
        if not activos:
            return "Sin modificadores permanentes."
        return "Modificadores: " + " · ".join(activos)

    def _render_multiline(self, lineas, font, color, x, y, line_h):
        for i, ln in enumerate(lineas):
            surf = font.render(ln, True, color)
            self.screen.blit(surf, (x, y + i * line_h))
