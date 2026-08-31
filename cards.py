# -*- coding: utf-8 -*-
"""Base de datos de cartas de Naranjonomía.

Implementa las tres barajas definidas en la especificación:
    * Mazo A (Naranjas)  - Proyectos creativos que generan PI e ingresos.
    * Mazo B (Verdes)    - Impulsores, IA, defensas y bufetes.
    * Mazo C (Rojas)     - Burocracia costarricense (CCSS, Hacienda, ACAM, ...).

Cada carta expone su efecto mediante una función pura sobre el estado del
`GameController` y el `Player`. Esto mantiene el código libre de estado global
y sencillo de portar a WebAssembly con pygbag.
"""
from __future__ import annotations

import random
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Optional, List


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------

class CardType(Enum):
    PROYECTO = 1     # Naranjas
    IMPULSOR = 2     # Verdes
    CONSECUENCIA = 3 # Rojas


@dataclass
class Card:
    id: str
    nombre: str
    tipo: CardType
    subtipo: str
    coste: int
    puntos_pi: int
    descripcion: str
    ingresos: int = 0
    # Efecto al ser jugada (proyectos/impulsores) o al ser revelada (consecuencias).
    efecto_func: Optional[Callable] = None
    # Bandera para el proyecto que se benefició de "Parque Biblioteca España" (G5).
    bonus_g5: int = 0
    # Rectángulo de colisión asignado por el renderer.
    rect: object = None


# ---------------------------------------------------------------------------
# Utilidades para modificar el estado del jugador
# ---------------------------------------------------------------------------

def _draw_from(deck: List[Card], jugador, ctrl) -> Optional[Card]:
    """Roba una carta del mazo indicado y la añade a la mano si hay hueco."""
    if not deck:
        return None
    carta = deck.pop()
    if len(jugador.mano) < 5:
        jugador.mano.append(carta)
    else:
        # Si la mano está llena, descartar automáticamente.
        ctrl.descarte_general.append(carta)
    return carta


# ---------------------------------------------------------------------------
# Efectos de Proyectos (Naranjas)
# ---------------------------------------------------------------------------

def efecto_O1(ctrl, jugador, oponente):
    """Ecosistema de Software y Apps: sin efecto inmediato adicional.
    El descuento de coste se resuelve en `coste_efectivo` cuando G1 está activo."""
    return


def efecto_O2(ctrl, jugador, oponente):
    """Desarrollo de Videojuegos: al completarse, roba 1 carta de Soporte (Verde) gratis."""
    _draw_from(ctrl.mazo_verde, jugador, ctrl)


def efecto_O3(ctrl, jugador, oponente):
    """Producción de Largometraje: oponente +3 MC ahora, tú +12 MC próximo turno."""
    oponente.mc += 3
    jugador.mc_extra_proximo_turno += 12


def efecto_O4(ctrl, jugador, oponente):
    """Álbum de Música: sin efecto inmediato; su +1 MC/proyecto se aplica en ingresos."""
    return


def efecto_O5(ctrl, jugador, oponente):
    """Ruta de Turismo Comunidad: inmunidad a R3 (marchamo) - flag pasivo del proyecto."""
    return


def efecto_O6(ctrl, jugador, oponente):
    """Complejo Gastronómico: prepara -5 MC al próximo proyecto de Artes Escénicas."""
    jugador.descuento_artes_escenicas = 5


def efecto_O7(ctrl, jugador, oponente):
    """Pasarela de Moda y Diseño: descarta 1 carta de tu mano y roba 2 del mazo mixto."""
    # Descarta automáticamente la carta más antigua (izquierda) para evitar sub-estados.
    if jugador.mano:
        descartada = jugador.mano.pop(0)
        ctrl.descarte_general.append(descartada)
    for _ in range(2):
        ctrl.robar_carta_general(jugador)


def efecto_O8(ctrl, jugador, oponente):
    """Teatro de Artes Escénicas: el oponente pagará 2 MC al inicio de su próximo turno."""
    oponente.debe_pagar_entradas = 2


# ---------------------------------------------------------------------------
# Efectos de Impulsores (Verdes)
# ---------------------------------------------------------------------------

def efecto_G1(ctrl, jugador, oponente):
    """Claude CoWork (IA avanzada): 50% descuento permanente en Software/Videojuegos/Diseño."""
    jugador.tiene_claude_cowork = True


def efecto_G2(ctrl, jugador, oponente):
    """Oficina Virtual Registrada: inmuniza contra R1 (Rechazo de CCSS)."""
    jugador.tiene_oficina_virtual = True


def efecto_G3(ctrl, jugador, oponente):
    """Alianza Público-Privada: revela 2 cartas del mazo naranja, elige 1, descarta la otra."""
    jugador.tiene_alianza_app = True  # también da mitigación pasiva para R7
    reveladas = []
    for _ in range(2):
        if ctrl.mazo_naranja:
            reveladas.append(ctrl.mazo_naranja.pop())
    if not reveladas:
        return
    # Delegar selección a la máquina de estados: el jugador clic-eará una.
    ctrl.iniciar_seleccion(reveladas)


def efecto_G4(ctrl, jugador, oponente):
    """Incubadora Ruta N: +2 MC pasivos a cada proyecto activo del jugador."""
    jugador.tiene_incubadora_ruta_n = True


def efecto_G5(ctrl, jugador, oponente):
    """Parque Biblioteca España: +4 MC/turno al proyecto activo más barato."""
    if not jugador.proyectos:
        # Sin proyectos: guarda pendiente para el próximo proyecto que juegue.
        jugador.g5_pendiente = True
        return
    mas_barato = min(jugador.proyectos, key=lambda c: c.coste)
    mas_barato.bonus_g5 = 4


def efecto_G6(ctrl, jugador, oponente):
    """Propiedad Intelectual Protegida: inmuniza contra R4 (ACAM)."""
    jugador.tiene_propiedad_intelectual = True


def efecto_G7(ctrl, jugador, oponente):
    """Abogado Corporativo (Bufete): cancela eventos tributarios > 10 MC (afecta R6, R7 alto)."""
    jugador.tiene_abogado = True


def efecto_G8(ctrl, jugador, oponente):
    """Educación Creativa Especializada: +1 PI inmediato."""
    jugador.pi += 1


# ---------------------------------------------------------------------------
# Efectos de Consecuencias (Rojas). Devuelven un texto para el log de UI.
# ---------------------------------------------------------------------------

def penalizacion_R1(ctrl, jugador, oponente):
    if jugador.tiene_oficina_virtual:
        return "Inmune: Oficina Virtual Registrada."
    if jugador.mc >= 10:
        jugador.mc -= 10
        return "Pagas 10 MC por alquilar una oficina ficticia."
    jugador.pierde_proximo_turno = True
    return "Sin fondos: pierdes el próximo turno."


def penalizacion_R2(ctrl, jugador, oponente):
    afectados = [p for p in jugador.proyectos
                 if p.subtipo in ("Soft Creativo", "Audiovisual", "Gastronomía")]
    coste = 5 * len(afectados)
    if coste == 0:
        return "Sin proyectos afectados por CCSS (26.33%)."
    jugador.mc -= coste
    return f"Pagas {coste} MC por Cargas Sociales (CCSS 26.33%) de {len(afectados)} proyecto(s)."


def penalizacion_R3(ctrl, jugador, oponente):
    if any(p.id == "O5" for p in jugador.proyectos):
        return "Inmune: Ruta de Turismo de Comunidad activa."
    jugador.mc -= 8
    return "Pagas 8 MC por Impuesto de Marchamo Vehicular."


def penalizacion_R4(ctrl, jugador, oponente):
    if jugador.tiene_propiedad_intelectual:
        return "Inmune: Propiedad Intelectual Protegida."
    jugador.mc -= 6
    return "Pagas 6 MC por Canon Musical ACAM."


def penalizacion_R5(ctrl, jugador, oponente):
    if any(p.id in ("O6", "O8") for p in jugador.proyectos):
        jugador.mc -= 10
        return "Pagas 10 MC en tasas del CFIA (Teatro / Complejo Gastronómico)."
    return "Sin proyecto Teatro ni Gastronómico. Sin coste."


def penalizacion_R6(ctrl, jugador, oponente):
    if jugador.tiene_abogado:
        return "Inmune: tu Bufete cancela el ajuste (>10 MC)."
    jugador.mc -= 12
    return "Pagas 12 MC por Ajuste Impositivo de Hacienda (IVA)."


def penalizacion_R7(ctrl, jugador, oponente):
    coste = 7
    if jugador.tiene_alianza_app:
        coste = coste // 2  # mitigación 50%
    jugador.mc -= coste
    return f"Pagas {coste} MC por Impuesto de Construcción Municipal."


def penalizacion_R8(ctrl, jugador, oponente):
    if jugador.mc >= 5:
        jugador.mc -= 5
        return "Pagas 5 MC de Impuesto a Personas Jurídicas."
    # Sociedad disuelta: descartar 1 proyecto activo (el primero).
    if jugador.proyectos:
        descartado = jugador.proyectos.pop(0)
        ctrl.descarte_general.append(descartado)
        return f"Sin fondos: sociedad disuelta y descartas '{descartado.nombre}'."
    return "Sin fondos ni proyectos. Sin efecto adicional."


# ---------------------------------------------------------------------------
# Constructores de mazos (2 copias de cada carta para dar profundidad estratégica).
# ---------------------------------------------------------------------------

def construir_mazo_naranja() -> List[Card]:
    plantilla = [
        Card("O1", "Ecosistema de Software y Apps",   CardType.PROYECTO, "Soft Creativo",
             15, 1,
             "Sinergia Digital: si tienes Claude CoWork, su coste baja a 7 MC. +3 MC/turno.",
             ingresos=3, efecto_func=efecto_O1),
        Card("O2", "Desarrollo de Videojuegos",       CardType.PROYECTO, "Soft Creativo",
             20, 2,
             "PI Activa: al completarse, robas 1 Soporte (Verde) gratis. +5 MC/turno.",
             ingresos=5, efecto_func=efecto_O2),
        Card("O3", "Producción de Largometraje",      CardType.PROYECTO, "Audiovisual",
             25, 3,
             "Encadenamiento: oponente +3 MC ahora; tú +12 MC próximo turno. +8 MC/turno.",
             ingresos=8, efecto_func=efecto_O3),
        Card("O4", "Álbum de Música de Estudio",      CardType.PROYECTO, "Artes e Ind.",
             10, 1,
             "Derechos de PI: +1 MC de ingresos a cada uno de tus otros proyectos activos.",
             ingresos=2, efecto_func=efecto_O4),
        Card("O5", "Ruta de Turismo de Comunidad",    CardType.PROYECTO, "Patrimonio",
             12, 1,
             "Patrimonio Sostenible: inmune a Marchamo Vehicular (R3). +3 MC/turno.",
             ingresos=3, efecto_func=efecto_O5),
        Card("O6", "Complejo Gastronómico Local",     CardType.PROYECTO, "Gastronomía",
             15, 2,
             "Fusión Cultural: -5 MC al próximo proyecto de Artes Escénicas. +4 MC/turno.",
             ingresos=4, efecto_func=efecto_O6),
        Card("O7", "Pasarela de Moda y Diseño",       CardType.PROYECTO, "Diseño",
             10, 1,
             "Impacto Visual: descarta 1 carta y roba 2 del mazo. +2 MC/turno.",
             ingresos=2, efecto_func=efecto_O7),
        Card("O8", "Teatro de Artes Escénicas",       CardType.PROYECTO, "Artes",
             12, 2,
             "Punto de Encuentro: el oponente te paga 2 MC al inicio de su próximo turno. +3 MC/turno.",
             ingresos=3, efecto_func=efecto_O8),
    ]
    mazo = []
    for c in plantilla:
        mazo.append(_clone(c))
        mazo.append(_clone(c))
    random.shuffle(mazo)
    return mazo


def construir_mazo_verde() -> List[Card]:
    plantilla = [
        Card("G1", "Claude CoWork (IA avanzada)", CardType.IMPULSOR, "IA / Permanente", 5, 0,
             "La IA como Colaborador: -50% coste permanente en Software, Videojuegos y Diseño.",
             efecto_func=efecto_G1),
        Card("G2", "Oficina Virtual Registrada",  CardType.IMPULSOR, "Permanente", 4, 0,
             "Emprendimiento sin Cadenas: inmune a R1 (Rechazo de CCSS por dirección física).",
             efecto_func=efecto_G2),
        Card("G3", "Alianza Público-Privada",     CardType.IMPULSOR, "Inmediato", 3, 0,
             "Gobierno Ágil: revela 2 cartas Naranjas, quédate 1 y descarta la otra.",
             efecto_func=efecto_G3),
        Card("G4", "Incubadora Ruta N",           CardType.IMPULSOR, "Permanente", 6, 0,
             "Ecosistema Innovador: +2 MC pasivos a cada proyecto activo por turno.",
             efecto_func=efecto_G4),
        Card("G5", "Parque Biblioteca España",    CardType.IMPULSOR, "Social", 5, 0,
             "Valor Social: +4 MC/turno a tu proyecto activo más barato.",
             efecto_func=efecto_G5),
        Card("G6", "Propiedad Intelectual Protegida", CardType.IMPULSOR, "Defensivo", 3, 0,
             "Patente de Ideas: inmune al canon musical ACAM (R4).",
             efecto_func=efecto_G6),
        Card("G7", "Abogado Corporativo (Bufete)", CardType.IMPULSOR, "Defensivo", 4, 0,
             "Garantía Legal: cancela eventos tributarios que te obliguen a pagar > 10 MC.",
             efecto_func=efecto_G7),
        Card("G8", "Educación Creativa Especializada", CardType.IMPULSOR, "Inmediato", 3, 0,
             "Formación del Talento: +1 PI inmediato por especialización del personal.",
             efecto_func=efecto_G8),
    ]
    mazo = []
    for c in plantilla:
        mazo.append(_clone(c))
        mazo.append(_clone(c))
    random.shuffle(mazo)
    return mazo


def construir_mazo_rojo() -> List[Card]:
    plantilla = [
        Card("R1", "Rechazo de CCSS por Dirección Física", CardType.CONSECUENCIA, "CCSS", 0, 0,
             "La CCSS deniega tu inscripción patronal por operar 100% digital.",
             efecto_func=penalizacion_R1),
        Card("R2", "Cargas Sociales Patronales (26.33%)", CardType.CONSECUENCIA, "CCSS", 0, 0,
             "Planilla: CCSS Salud, IVM, INA, IMAS, Banco Popular, FODESAF (~26.33%).",
             efecto_func=penalizacion_R2),
        Card("R3", "Impuesto de Marchamo Vehicular", CardType.CONSECUENCIA, "Hacienda", 0, 0,
             "Marchamo: 58% propiedad + 25% SOA + cobros municipales.",
             efecto_func=penalizacion_R3),
        Card("R4", "Canon Privado por Música (ACAM)", CardType.CONSECUENCIA, "Canon", 0, 0,
             "ACAM te cobra por ambientación acústica en tu actividad creativa.",
             efecto_func=penalizacion_R4),
        Card("R5", "Registro y Timbres del CFIA", CardType.CONSECUENCIA, "Colegio", 0, 0,
             "Tasas y timbres obligatorios del Colegio Federal de Ingenieros y Arquitectos.",
             efecto_func=penalizacion_R5),
        Card("R6", "Ajuste Impositivo de Hacienda (IVA)", CardType.CONSECUENCIA, "Hacienda", 0, 0,
             "Declaración de IVA 13% mensual + renta trimestral en PDF redundante.",
             efecto_func=penalizacion_R6),
        Card("R7", "Impuesto de Construcción Municipal", CardType.CONSECUENCIA, "Municipal", 0, 0,
             "Inspección municipal: 1% sobre el valor de mejoras del local comercial.",
             efecto_func=penalizacion_R7),
        Card("R8", "Impuesto a las Personas Jurídicas", CardType.CONSECUENCIA, "Registro", 0, 0,
             "Impuesto anual para mantener tu SA / SRL activa en el Registro Nacional.",
             efecto_func=penalizacion_R8),
    ]
    mazo = []
    for c in plantilla:
        mazo.append(_clone(c))
        mazo.append(_clone(c))
    random.shuffle(mazo)
    return mazo


def _clone(card: Card) -> Card:
    """Devuelve una copia independiente de una carta plantilla."""
    return Card(
        id=card.id,
        nombre=card.nombre,
        tipo=card.tipo,
        subtipo=card.subtipo,
        coste=card.coste,
        puntos_pi=card.puntos_pi,
        descripcion=card.descripcion,
        ingresos=card.ingresos,
        efecto_func=card.efecto_func,
    )
