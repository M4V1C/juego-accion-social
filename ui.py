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
    AREA_SUPERIOR_H, AREA_CENTRAL_BOTTOM, AREA_INFERIOR_Y,
    LOG_BAND_Y, LOG_BAND_H, PROYECTOS_PARA_GANAR,
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
        elif estado == GameState.MANUAL:
            self._draw_menu(ctrl)
            self._draw_overlay_manual(ctrl)
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

        # Botones: Empezar (izquierda) y Manual (derecha).
        self._draw_button(ctrl.rect_empezar, "EMPEZAR", COLORS["azul_boton"])
        self._draw_button(ctrl.rect_manual,  "CÓMO JUGAR", COLORS["verde"])

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

        stats = (f"$ {oponente.mc}   |   "
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
                         (0, AREA_SUPERIOR_H, SCREEN_WIDTH, AREA_CENTRAL_BOTTOM - AREA_SUPERIOR_H))

        # Zona 1: panel de estado global persistente (ambos jugadores a la vez).
        self._draw_status_panel(ctrl)

        # Zona 2: proyectos activos del jugador activo.
        rect_proj = pygame.Rect(310, 105, 720, 285)
        pygame.draw.rect(self.screen, COLORS["blanco"], rect_proj, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["naranja"], rect_proj, 3, border_radius=8)
        etiqueta = self.font_sm.render(
            f"Proyectos activos de {ctrl.jugador_activo.nombre}",
            True, COLORS["naranja"])
        self.screen.blit(etiqueta, (rect_proj.x + 10, rect_proj.y + 6))
        # Mini cartas: tamaño dinámico para que las 5 ranuras quepan.
        slots = PROYECTOS_PARA_GANAR
        inner_w = rect_proj.w - 20
        slot_gap = 8
        slot_w = (inner_w - (slots - 1) * slot_gap) // slots
        slot_h = rect_proj.h - 50
        for i, p in enumerate(ctrl.jugador_activo.proyectos):
            r = pygame.Rect(
                rect_proj.x + 10 + i * (slot_w + slot_gap),
                rect_proj.y + 40, slot_w, slot_h)
            self._draw_card(p, r, mini=True)

        # Zona 3: información de turno / botón PASAR.
        rect_turno = pygame.Rect(1060, 105, 200, 285)
        pygame.draw.rect(self.screen, COLORS["blanco"], rect_turno, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["azul_texto"], rect_turno, 3, border_radius=8)
        etiqueta = self.font_sm.render("Turno actual", True, COLORS["azul_texto"])
        self.screen.blit(etiqueta, etiqueta.get_rect(center=(rect_turno.centerx, rect_turno.y + 18)))

        info = [
            ctrl.jugador_activo.nombre,
            ctrl.jugador_activo.rol,
            "",
            f"Dinero: ${ctrl.jugador_activo.mc}",
            f"Ingresos/turno: +${ctrl.jugador_activo.ingresos_totales()}",
            f"Proyectos: {len(ctrl.jugador_activo.proyectos)}/{PROYECTOS_PARA_GANAR}",
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

    # ---------------------- panel de estado global (izquierda del área central)
    def _draw_status_panel(self, ctrl: GameController) -> None:
        """Rectángulo persistente que muestra el estado de AMBOS jugadores.

        Se dibuja sobre el área central sin alterar los paneles de proyectos
        (rect_proj) ni de turno (rect_turno). Facilita la toma de decisiones
        al ver simultáneamente dinero, proyectos y modificadores rivales.
        """
        panel = pygame.Rect(10, 100, 280, 295)
        pygame.draw.rect(self.screen, COLORS["blanco"], panel, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["azul_texto"], panel, 3, border_radius=8)

        # Título.
        titulo = self.font_sm.render("ESTADO DE LA PARTIDA", True, COLORS["azul_texto"])
        self.screen.blit(titulo, titulo.get_rect(center=(panel.centerx, panel.y + 12)))

        # Dos mitades verticales, una por jugador.
        mid_y = panel.y + 30
        half_h = (panel.h - 44) // 2
        j1 = pygame.Rect(panel.x + 6, mid_y,             panel.w - 12, half_h)
        j2 = pygame.Rect(panel.x + 6, mid_y + half_h + 4, panel.w - 12, half_h)
        self._draw_status_half(j1, ctrl.player1, "JUGADOR 1",
                                activo=(ctrl.jugador_activo is ctrl.player1))
        self._draw_status_half(j2, ctrl.player2, "JUGADOR 2",
                                activo=(ctrl.jugador_activo is ctrl.player2))

        # Pie con contador del mazo rojo (info que antes vivía en rect_evento).
        info = f"Mazo Rojo: {len(ctrl.mazo_rojo)} · Descarte: {len(ctrl.descarte_rojo)}"
        surf = self.font_xs.render(info, True, COLORS["gris_medio"])
        self.screen.blit(surf, surf.get_rect(center=(panel.centerx, panel.bottom - 10)))

    def _draw_status_half(self, rect: pygame.Rect, jugador, etiqueta: str,
                          activo: bool) -> None:
        # Fondo destacado si es el jugador activo.
        color_fondo = COLORS["panel_activo"] if activo else COLORS["gris_claro"]
        pygame.draw.rect(self.screen, color_fondo, rect, border_radius=6)
        color_borde = COLORS["naranja"] if activo else COLORS["gris_medio"]
        pygame.draw.rect(self.screen, color_borde, rect, 2, border_radius=6)

        # Cabecera: etiqueta + marca de activo.
        cabecera = etiqueta + ("  ◀ EN TURNO" if activo else "")
        surf = self.font_sm.render(cabecera, True, color_borde)
        self.screen.blit(surf, (rect.x + 6, rect.y + 4))

        # Rol.
        surf = self.font_xs.render(jugador.rol, True, COLORS["gris_oscuro"])
        self.screen.blit(surf, (rect.x + 6, rect.y + 24))

        # Stats: Dinero · Proyectos · Mano.
        stats = (f"${jugador.mc}   "
                 f"Proy {len(jugador.proyectos)}/{PROYECTOS_PARA_GANAR}   "
                 f"Mano {len(jugador.mano)}")
        surf = self.font_sm.render(stats, True, COLORS["negro"])
        self.screen.blit(surf, (rect.x + 6, rect.y + 40))

        # Ingresos por turno.
        ing = f"Ingresos/turno: +${jugador.ingresos_totales()}"
        surf = self.font_xs.render(ing, True, COLORS["azul_texto"])
        self.screen.blit(surf, (rect.x + 6, rect.y + 62))

        # Fila de badges de proyectos activos (siempre visible para ambos jugadores).
        badge_y = rect.y + 80
        slots = PROYECTOS_PARA_GANAR
        badge_w = (rect.w - 12 - (slots - 1) * 4) // slots
        badge_h = min(rect.h - 82 - 4, 34)
        for i in range(slots):
            bx = rect.x + 6 + i * (badge_w + 4)
            slot_rect = pygame.Rect(bx, badge_y, badge_w, badge_h)
            if i < len(jugador.proyectos):
                p = jugador.proyectos[i]
                pygame.draw.rect(self.screen, COLORS["naranja_claro"], slot_rect, border_radius=4)
                pygame.draw.rect(self.screen, COLORS["naranja"], slot_rect, 2, border_radius=4)
                surf = self.font_xs.render(p.id, True, COLORS["negro"])
                self.screen.blit(surf, surf.get_rect(midtop=(slot_rect.centerx, slot_rect.y + 2)))
                ing_txt = f"+${p.ingresos}"
                surf = self.font_xs.render(ing_txt, True, COLORS["gris_oscuro"])
                self.screen.blit(surf, surf.get_rect(midbottom=(slot_rect.centerx, slot_rect.bottom - 2)))
            else:
                # Ranura vacía.
                pygame.draw.rect(self.screen, COLORS["blanco"], slot_rect, border_radius=4)
                pygame.draw.rect(self.screen, COLORS["gris_medio"], slot_rect, 1, border_radius=4)

    # ---------------------- overlays
    def _draw_overlay_manual(self, ctrl: GameController) -> None:
        """Ventana modal con el tutorial. Se dibuja sobre el menú principal."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        # Panel centrado.
        panel_w, panel_h = 940, 590
        panel = pygame.Rect((SCREEN_WIDTH - panel_w) // 2, 50, panel_w, panel_h)
        pygame.draw.rect(self.screen, COLORS["fondo_buttercream"], panel, border_radius=14)
        pygame.draw.rect(self.screen, COLORS["naranja"], panel, 4, border_radius=14)

        # Título del manual.
        titulo = self.font_lg.render("CÓMO JUGAR — NARANJONOMÍA", True, COLORS["naranja"])
        self.screen.blit(titulo, titulo.get_rect(center=(SCREEN_WIDTH // 2, panel.y + 30)))

        # Contenido: pares (encabezado, líneas) con dos columnas.
        secciones = [
            ("OBJETIVO",
             [f"Completa {PROYECTOS_PARA_GANAR} proyectos Naranjas activos, o",
              "provoca la bancarrota del oponente ($ ≤ 0)."]),
            ("RECURSOS",
             ["Dinero ($): financia todo y evita la bancarrota.",
              "Proyectos activos: cuentan hacia la victoria.",
              "Mano: máximo 5 cartas."]),
            ("TIPOS DE CARTAS",
             ["Naranjas · Proyectos que dan +$/turno.",
              "Verdes · Impulsores: descuentos, inmunidades, IA.",
              "Rojas · Burocracia CR (CCSS, Hacienda, ACAM…)."]),
            ("FASES DEL TURNO",
             ["1) Inicio: cobras ingresos y robas 1 carta.",
              "2) Acción: juegas UNA carta o pulsas PASAR.",
              "3) Consecuencia: revelas 1 carta Roja y pagas."]),
            ("CONSEJOS RÁPIDOS",
             ["Compra pronto G2, G6 o G7 para bloquear rojas.",
              "G1 (Claude CoWork) baja 50% coste Software/Diseño.",
              "O3 es caro pero suelta +$12 el turno siguiente."]),
            ("CONTROLES",
             ["Clic izquierdo sobre una carta de tu mano · jugarla.",
              "Clic en el botón PASAR · saltar acción.",
              "Esc · cerrar el juego."]),
        ]
        col_x = [panel.x + 30, panel.x + panel_w // 2 + 10]
        y_col = [panel.y + 80, panel.y + 80]
        for idx, (titulo_sec, lineas) in enumerate(secciones):
            col = idx % 2
            surf = self.font_md.render(titulo_sec, True, COLORS["azul_texto"])
            self.screen.blit(surf, (col_x[col], y_col[col]))
            y_col[col] += 28
            for ln in lineas:
                surf = self.font_sm.render(ln, True, COLORS["negro"])
                self.screen.blit(surf, (col_x[col] + 8, y_col[col]))
                y_col[col] += 22
            y_col[col] += 10

        # Botón cerrar.
        self._draw_button(ctrl.rect_cerrar_manual, "CERRAR", COLORS["azul_boton"])

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
        # Banda dedicada entre el área central y la mano, para no pisar cartas.
        band_rect = pygame.Rect(0, LOG_BAND_Y, SCREEN_WIDTH, LOG_BAND_H)
        pygame.draw.rect(self.screen, COLORS["gris_claro"], band_rect)
        pygame.draw.line(self.screen, COLORS["gris_medio"],
                         (0, LOG_BAND_Y), (SCREEN_WIDTH, LOG_BAND_Y), 1)
        pygame.draw.line(self.screen, COLORS["gris_medio"],
                         (0, LOG_BAND_Y + LOG_BAND_H),
                         (SCREEN_WIDTH, LOG_BAND_Y + LOG_BAND_H), 1)
        # Clip para garantizar que el texto del log NUNCA se pinte sobre la mano.
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(band_rect)
        try:
            etiqueta = self.font_xs.render("REGISTRO DE PARTIDA", True, COLORS["gris_oscuro"])
            self.screen.blit(etiqueta, (20, LOG_BAND_Y + 2))
            y0 = LOG_BAND_Y + 18
            for i, msg in enumerate(ctrl.log[-3:]):
                surf = self.font_xs.render(msg, True, COLORS["gris_oscuro"])
                self.screen.blit(surf, (20, y0 + i * 13))
        finally:
            self.screen.set_clip(previous_clip)

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

        infos = [
            f"Proyectos completados: {len(ganador.proyectos)} / {PROYECTOS_PARA_GANAR}",
            f"Dinero restante: ${ganador.mc}",
            f"Ingresos por turno finales: +${ganador.ingresos_totales()}",
        ]
        y = 240
        for txt in infos:
            surf = self.font_md.render(txt, True, COLORS["negro"])
            self.screen.blit(surf, surf.get_rect(center=(w // 2, y)))
            y += 40

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
            coste_txt = f"${carta.coste}"
            surf = self.font_sm.render(coste_txt, True, COLORS["negro"])
            self.screen.blit(surf, (rect.x + 6, rect.bottom - 22))

        # PI / Ingresos (esquina inferior der para proyectos).
        if carta.tipo == CardType.PROYECTO:
            info = f"+${carta.ingresos}/turno"
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
