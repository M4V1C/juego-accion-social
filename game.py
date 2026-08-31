# -*- coding: utf-8 -*-
"""Lógica principal del juego: `Player`, `GameState`, `GameController`.

Se implementa la Máquina de Estados de un solo hilo descrita en la
especificación (sección 1 y 3). No hay condiciones de carrera ni hilos
adicionales, lo que garantiza compatibilidad con la compilación a
WebAssembly mediante pygbag.
"""
from __future__ import annotations

import random
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional

import pygame

from cards import (
    Card, CardType,
    construir_mazo_naranja, construir_mazo_verde, construir_mazo_rojo,
)
from constants import (
    MC_INICIAL, HAND_MAX, INITIAL_HAND, PROYECTOS_PARA_GANAR,
    BTN_PASAR_RECT, BTN_ACEPTAR_RECT, BTN_REINICIAR_RECT, BTN_EMPEZAR_RECT,
    CARD_WIDTH, CARD_HEIGHT, CARD_GAP, HAND_Y, SCREEN_WIDTH,
)


# ---------------------------------------------------------------------------
# Estados de la Máquina de Juego (sección 1 de la especificación).
# ---------------------------------------------------------------------------

class GameState(Enum):
    MENU_PRINCIPAL       = 1
    INICIALIZACION       = 2
    TURNO_PROXIMO        = 3
    TURNO_ACCION         = 4
    REVELAR_CONSECUENCIA = 5
    EVALUAR_VICTORIA     = 6
    FIN_DE_JUEGO         = 7
    SELECCION_CARTA      = 8  # sub-estado auxiliar para efectos que requieren elegir carta


# ---------------------------------------------------------------------------
# Jugador
# ---------------------------------------------------------------------------

@dataclass
class Player:
    nombre: str
    rol: str
    mc: int = MC_INICIAL
    pi: int = 0
    proyectos: List[Card] = field(default_factory=list)
    mano: List[Card] = field(default_factory=list)

    # Modificadores permanentes (Impulsores Verdes).
    tiene_claude_cowork: bool = False        # G1
    tiene_oficina_virtual: bool = False      # G2
    tiene_alianza_app: bool = False          # G3 (residual, mitiga R7)
    tiene_incubadora_ruta_n: bool = False    # G4
    tiene_propiedad_intelectual: bool = False # G6
    tiene_abogado: bool = False              # G7

    # Efectos temporales.
    descuento_artes_escenicas: int = 0       # de O6 al próximo O8
    mc_extra_proximo_turno: int = 0          # de O3
    debe_pagar_entradas: int = 0             # a O8 del oponente
    pierde_proximo_turno: bool = False       # de R1 sin fondos
    g5_pendiente: bool = False               # G5 jugado sin proyectos aún

    def coste_efectivo(self, carta: Card) -> int:
        """Aplica descuentos permanentes/pendientes al coste de una carta."""
        coste = carta.coste
        if carta.tipo == CardType.PROYECTO:
            # G1: -50% en Soft Creativo (O1, O2) y Diseño (O7).
            if self.tiene_claude_cowork and carta.subtipo in ("Soft Creativo", "Diseño"):
                coste = coste // 2
            # O6 aplica -5 MC al próximo Artes Escénicas (O8).
            if self.descuento_artes_escenicas and carta.id == "O8":
                coste = max(0, coste - self.descuento_artes_escenicas)
        return coste

    def ingresos_totales(self) -> int:
        """Suma los ingresos pasivos de todos los proyectos activos."""
        total = 0
        tiene_O4 = any(p.id == "O4" for p in self.proyectos)
        for p in self.proyectos:
            base = p.ingresos
            if self.tiene_incubadora_ruta_n:
                base += 2
            # O4: +1 MC a cada uno de tus OTROS proyectos activos.
            if tiene_O4 and p.id != "O4":
                base += 1
            base += p.bonus_g5
            total += base
        return total


# ---------------------------------------------------------------------------
# Controlador del juego (máquina de estados + reglas).
# ---------------------------------------------------------------------------

class GameController:
    def __init__(self):
        self.player1 = Player("Emprendedor 1", "Desarrollador de Software")
        self.player2 = Player("Emprendedor 2", "Cineasta e Industrias Culturales")
        self.jugador_activo: Player = self.player1
        self.oponente: Player = self.player2

        self.mazo_naranja: List[Card] = []
        self.mazo_verde: List[Card] = []
        self.mazo_rojo: List[Card] = []
        self.descarte_general: List[Card] = []
        self.descarte_rojo: List[Card] = []

        # Estado inicial: menú.
        self.estado: GameState = GameState.MENU_PRINCIPAL

        # UI feedback: mensaje temporal a mostrar al usuario.
        self.log: List[str] = []
        self.mensaje_evento_rojo: str = ""
        self.carta_roja_actual: Optional[Card] = None
        self.ganador: Optional[Player] = None

        # Selección pendiente (efecto G3).
        self.seleccion_pendiente: List[Card] = []
        self.estado_previo_seleccion: Optional[GameState] = None

        # Rectángulos de botones.
        self.rect_pasar = pygame.Rect(*BTN_PASAR_RECT)
        self.rect_aceptar = pygame.Rect(*BTN_ACEPTAR_RECT)
        self.rect_reiniciar = pygame.Rect(*BTN_REINICIAR_RECT)
        self.rect_empezar = pygame.Rect(*BTN_EMPEZAR_RECT)

    # ------------------------------------------------------------------ ciclo
    def update(self, click_pos: Optional[tuple]) -> None:
        """Un tick de la Máquina de Estados. `click_pos` puede ser `None`."""
        estado = self.estado

        if estado == GameState.MENU_PRINCIPAL:
            if click_pos and self.rect_empezar.collidepoint(click_pos):
                self.estado = GameState.INICIALIZACION

        elif estado == GameState.INICIALIZACION:
            self.inicializar_partida()
            self.estado = GameState.TURNO_PROXIMO

        elif estado == GameState.TURNO_PROXIMO:
            self.preparar_nuevo_turno()
            # Si el jugador activo pierde el turno, pasar directamente al oponente.
            if self.jugador_activo.pierde_proximo_turno:
                self.jugador_activo.pierde_proximo_turno = False
                self.log_append(f"{self.jugador_activo.nombre} pierde su turno.")
                self._alternar_jugador()
                self.preparar_nuevo_turno()
            self.estado = GameState.TURNO_ACCION

        elif estado == GameState.TURNO_ACCION:
            if click_pos:
                if self.rect_pasar.collidepoint(click_pos):
                    self.log_append(f"{self.jugador_activo.nombre} decide PASAR.")
                    self.estado = GameState.REVELAR_CONSECUENCIA
                    self._preparar_carta_roja()
                else:
                    self._procesar_click_en_mano(click_pos)

        elif estado == GameState.SELECCION_CARTA:
            if click_pos:
                self._procesar_click_seleccion(click_pos)

        elif estado == GameState.REVELAR_CONSECUENCIA:
            if click_pos and self.rect_aceptar.collidepoint(click_pos):
                self._aplicar_carta_roja()
                self.estado = GameState.EVALUAR_VICTORIA

        elif estado == GameState.EVALUAR_VICTORIA:
            if self.comprobar_condiciones_victoria():
                self.estado = GameState.FIN_DE_JUEGO
            else:
                self._alternar_jugador()
                self.estado = GameState.TURNO_PROXIMO

        elif estado == GameState.FIN_DE_JUEGO:
            if click_pos and self.rect_reiniciar.collidepoint(click_pos):
                self.reiniciar_juego()

    # ------------------------------------------------------------ setup inicial
    def inicializar_partida(self) -> None:
        self.mazo_naranja = construir_mazo_naranja()
        self.mazo_verde = construir_mazo_verde()
        self.mazo_rojo = construir_mazo_rojo()
        self.descarte_general = []
        self.descarte_rojo = []

        for j in (self.player1, self.player2):
            for _ in range(INITIAL_HAND):
                self.robar_carta_general(j)

        self.jugador_activo = self.player1
        self.oponente = self.player2
        self.log_append("Partida iniciada. Turno de Jugador 1.")

    def preparar_nuevo_turno(self) -> None:
        """Actualiza jugador activo, aplica ingresos y roba 1 carta hasta el máximo."""
        j = self.jugador_activo
        # Cobro de entradas al Teatro (O8) del oponente.
        if j.debe_pagar_entradas > 0 and self.oponente.proyectos:
            monto = j.debe_pagar_entradas
            monto = min(monto, j.mc if j.mc > 0 else 0)
            j.mc -= j.debe_pagar_entradas
            self.oponente.mc += j.debe_pagar_entradas
            self.log_append(
                f"{j.nombre} paga {j.debe_pagar_entradas} MC de entradas al Teatro de {self.oponente.nombre}."
            )
            j.debe_pagar_entradas = 0

        # Ingresos pasivos por proyectos.
        ingresos = j.ingresos_totales()
        if ingresos:
            j.mc += ingresos
            self.log_append(f"{j.nombre} recibe {ingresos} MC de sus proyectos.")

        # Bonus diferido (Largometraje O3).
        if j.mc_extra_proximo_turno:
            j.mc += j.mc_extra_proximo_turno
            self.log_append(
                f"{j.nombre} recibe {j.mc_extra_proximo_turno} MC diferidos del Largometraje."
            )
            j.mc_extra_proximo_turno = 0

        # Robo de mantenimiento.
        self.robar_carta_general(j)

    def _alternar_jugador(self) -> None:
        self.jugador_activo, self.oponente = self.oponente, self.jugador_activo

    # ---------------------------------------------------------------- mazo I/O
    def robar_carta_general(self, jugador: Player) -> Optional[Card]:
        """Roba 1 carta aleatoria del combinado Naranja+Verde."""
        if len(jugador.mano) >= HAND_MAX:
            return None
        opciones = []
        if self.mazo_naranja:
            opciones.append("naranja")
        if self.mazo_verde:
            opciones.append("verde")
        if not opciones:
            return None
        eleccion = random.choice(opciones)
        carta = self.mazo_naranja.pop() if eleccion == "naranja" else self.mazo_verde.pop()
        jugador.mano.append(carta)
        return carta

    def _preparar_carta_roja(self) -> None:
        """Robar (con reciclaje de descarte) la siguiente carta de burocracia."""
        if not self.mazo_rojo and self.descarte_rojo:
            self.mazo_rojo = self.descarte_rojo
            random.shuffle(self.mazo_rojo)
            self.descarte_rojo = []
        if self.mazo_rojo:
            self.carta_roja_actual = self.mazo_rojo.pop()
        else:
            self.carta_roja_actual = None

    def _aplicar_carta_roja(self) -> None:
        carta = self.carta_roja_actual
        if carta is None:
            self.mensaje_evento_rojo = "Sin carta de burocracia."
            return
        msg = "" if carta.efecto_func is None else carta.efecto_func(self, self.jugador_activo, self.oponente)
        self.mensaje_evento_rojo = msg or ""
        self.log_append(f"[R] {carta.nombre}: {self.mensaje_evento_rojo}")
        self.descarte_rojo.append(carta)
        self.carta_roja_actual = None

    # ---------------------------------------------------------- jugar carta UI
    def _procesar_click_en_mano(self, pos: tuple) -> None:
        jugador = self.jugador_activo
        for carta in list(jugador.mano):
            if carta.rect is not None and carta.rect.collidepoint(pos):
                self._intentar_jugar_carta(carta)
                return

    def _intentar_jugar_carta(self, carta: Card) -> None:
        jugador = self.jugador_activo
        coste = jugador.coste_efectivo(carta)
        if jugador.mc < coste:
            self.log_append(f"Fondos insuficientes para {carta.nombre} (coste {coste} MC).")
            return
        # Limitación de 3 proyectos activos (relacionado con criterio de victoria).
        if carta.tipo == CardType.PROYECTO and len(jugador.proyectos) >= PROYECTOS_PARA_GANAR:
            self.log_append("Ya tienes el máximo de proyectos activos.")
            return

        jugador.mc -= coste
        jugador.mano.remove(carta)

        if carta.tipo == CardType.PROYECTO:
            jugador.proyectos.append(carta)
            jugador.pi += carta.puntos_pi
            # Aplicar G5 pendiente si es el primer proyecto.
            if jugador.g5_pendiente:
                carta.bonus_g5 = 4
                jugador.g5_pendiente = False
            # Consumir descuento de artes escénicas si aplica.
            if carta.id == "O8":
                jugador.descuento_artes_escenicas = 0

        # Ejecutar efecto de la carta.
        if carta.efecto_func is not None:
            carta.efecto_func(self, jugador, self.oponente)

        self.log_append(f"{jugador.nombre} juega '{carta.nombre}' (coste {coste} MC).")

        # Impulsores no van a la zona activa: van al descarte tras usarse.
        if carta.tipo == CardType.IMPULSOR:
            self.descarte_general.append(carta)

        # Si el efecto lanzó una selección, quedarse en SELECCION_CARTA.
        if self.estado == GameState.SELECCION_CARTA:
            return

        # Avanzar al evento de burocracia.
        self.estado = GameState.REVELAR_CONSECUENCIA
        self._preparar_carta_roja()

    # ------------------------------------------------------------ selección G3
    def iniciar_seleccion(self, cartas: List[Card]) -> None:
        self.seleccion_pendiente = cartas
        self.estado_previo_seleccion = self.estado
        self.estado = GameState.SELECCION_CARTA
        self._posicionar_cartas_seleccion()

    def _posicionar_cartas_seleccion(self) -> None:
        n = len(self.seleccion_pendiente)
        total_w = n * CARD_WIDTH + (n - 1) * CARD_GAP
        start_x = (SCREEN_WIDTH - total_w) // 2
        y = 240
        for i, c in enumerate(self.seleccion_pendiente):
            x = start_x + i * (CARD_WIDTH + CARD_GAP)
            c.rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)

    def _procesar_click_seleccion(self, pos: tuple) -> None:
        elegida: Optional[Card] = None
        for c in self.seleccion_pendiente:
            if c.rect and c.rect.collidepoint(pos):
                elegida = c
                break
        if elegida is None:
            return
        for c in self.seleccion_pendiente:
            if c is elegida:
                if len(self.jugador_activo.mano) < HAND_MAX:
                    self.jugador_activo.mano.append(c)
                else:
                    self.descarte_general.append(c)
                self.log_append(f"{self.jugador_activo.nombre} conserva '{c.nombre}'.")
            else:
                self.descarte_general.append(c)
                self.log_append(f"Descarta '{c.nombre}'.")
        self.seleccion_pendiente = []
        # Reanudar flujo: avanzar a evento de burocracia.
        self.estado = GameState.REVELAR_CONSECUENCIA
        self._preparar_carta_roja()

    # ---------------------------------------------------------------- victoria
    def comprobar_condiciones_victoria(self) -> bool:
        # Bancarrota del jugador activo o del oponente.
        for j in (self.player1, self.player2):
            if j.mc <= 0:
                self.ganador = self.player2 if j is self.player1 else self.player1
                self.log_append(f"{j.nombre} entra en bancarrota institucional.")
                return True
        # 3 proyectos Naranjas completados.
        for j in (self.player1, self.player2):
            if len(j.proyectos) >= PROYECTOS_PARA_GANAR:
                self.ganador = j
                self.log_append(f"{j.nombre} alcanza {PROYECTOS_PARA_GANAR} proyectos activos.")
                return True
        return False

    # ---------------------------------------------------------------- reinicio
    def reiniciar_juego(self) -> None:
        self.__init__()

    # -------------------------------------------------------------------- misc
    def log_append(self, msg: str) -> None:
        self.log.append(msg)
        if len(self.log) > 6:
            self.log.pop(0)
