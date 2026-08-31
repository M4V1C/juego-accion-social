# -*- coding: utf-8 -*-
"""Punto de entrada del juego Naranjonomía.

Ejecución local:
    python main.py

Compilación / despliegue web (WebAssembly con pygbag):
    pip install pygbag
    pygbag main.py                # arranca un servidor local en http://localhost:8000
    pygbag --build main.py        # genera la carpeta build/web para GitHub Pages

El bucle principal es asíncrono (`async def main`) y libera el hilo con
`await asyncio.sleep(0)` en cada frame, tal y como requiere pygbag para
poder ejecutar en el navegador.
"""
from __future__ import annotations

import asyncio
import sys

import pygame

from constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from game import GameController
from ui import Renderer


async def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Naranjonomía · El Reto de Emprender")
    clock = pygame.time.Clock()

    controlador = GameController()
    renderer = Renderer(screen)

    running = True
    while running:
        click_pos = None

        # 1) INPUT
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = event.pos
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        # 2) UPDATE (máquina de estados)
        controlador.update(click_pos)

        # 3) RENDER
        renderer.draw(controlador)
        pygame.display.flip()

        clock.tick(FPS)
        # Ceder control al event-loop del navegador (obligatorio para pygbag).
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
