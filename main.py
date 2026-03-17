#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygame
import sys
from src.game import FreeCellGame
from src.constants import SCREEN_WIDTH, SCREEN_HEIGHT

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("FreeCell Solver - CSC14003")
    
    game = FreeCellGame(screen)
    game.run()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()