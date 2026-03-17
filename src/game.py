import pygame
import threading
import time
import os
from typing import Optional, List, Tuple

from .constants import *
from .card import Card, Suit, Rank
from .game_state import FreeCellState
from .button import Button
from .solvers.bfs_solver import BFSSolver
from .solvers.dfs_solver import DFSSolver
from .solvers.ucs_solver import UCSSolver
from .solvers.astar_solver import AStarSolver

class FreeCellGame:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True
        font_path = os.path.join('assets','fonts', 'DejaVu Sans 400.ttf')
        if os.path.exists(font_path):
            self.large_font = pygame.font.Font(font_path, 36)
            self.small_font = pygame.font.Font(font_path, 20)
            self.font = pygame.font.Font(font_path, 24)
            self.big_font = pygame.font.Font(font_path, 48)
        else:
            # Fallback to default
            self.large_font = pygame.font.Font(None, 36)
            self.small_font = pygame.font.Font(None, 20)
            self.font = pygame.font.Font(None, 24)
            self.big_font = pygame.font.Font(None, 48)
     
        self.current_state = None
        self.selected_card = None
        self.selected_source = None
        self.selected_sequence = []
        self.solving = False
        
        self.dragging = False
        self.dragged_cards = [] 
        self.dragged_source = None 
        self.drag_start_pos = (0, 0) 
        self.drag_offset_x = 0  
        self.drag_offset_y = 0
        self.drag_source_col = -1 
        self.drag_source_row = -1
        self.drag_source_freecell = -1
        self.drag_positions = []
        
        self.buttons = []
        self.create_buttons()
        
        self.status_message = "Ready"
        self.seed_input = "1"
        self.input_active = False
        
        self.new_game()
    
    def create_buttons(self):
        self.buttons = []
        
        BUTTON_Y = 65 
        BUTTON_HEIGHT = 30
        
        self.buttons.append(Button(20, BUTTON_Y, 100, BUTTON_HEIGHT, "New Game", (52, 152, 219), (41, 128, 185)))
        self.buttons.append(Button(130, BUTTON_Y, 80, BUTTON_HEIGHT, "Restart", (241, 156, 18), (230, 126, 34)))
        self.buttons.append(Button(220, BUTTON_Y, 70, BUTTON_HEIGHT, "Undo", (149, 165, 166), (127, 140, 141)))
        
        self.seed_rect = pygame.Rect(360, BUTTON_Y, 100, BUTTON_HEIGHT)

        solver_buttons = [
            ("BFS", (155, 89, 182), (142, 68, 173)),
            ("DFS", (230, 126, 34), (211, 84, 0)),
            ("UCS", (26, 188, 156), (22, 160, 133)),
            ("A*", (231, 76, 60), (192, 57, 43))
        ]
        
        x_start = 460
        for i, (text, color, hover_color) in enumerate(solver_buttons):
            self.buttons.append(Button(x_start + i * 75, BUTTON_Y, 65, BUTTON_HEIGHT, text, color, hover_color))
    def new_game(self):
        try:
            seed = int(self.seed_input)
            self.current_state = FreeCellState(seed)
            self.selected_card = None
            self.selected_source = None
            self.selected_sequence = []
            self.dragging = False
            self.dragged_cards = []
            self.status_message = f"New game with seed {seed}"
        except ValueError:
            self.status_message = "Invalid seed number"
    
    def restart_game(self):
        if self.current_state:
            self.current_state = FreeCellState(self.current_state.seed)
            self.selected_card = None
            self.selected_source = None
            self.selected_sequence = []
            self.dragging = False
            self.dragged_cards = []
            self.status_message = "Game restarted"
    
    def undo_move(self):
        if self.current_state and self.current_state.move_history:
            self.current_state.move_history.pop()
            self.current_state = FreeCellState(self.current_state.seed)
            for move in self.current_state.move_history:
                self.current_state = self.current_state.apply_move(move)
            self.status_message = "Undo last move"
    
    def get_max_sequence_length(self):
        empty_free_cells = self.current_state.get_empty_free_cells()
        empty_cascades = self.current_state.get_empty_cascades()
        
        base = empty_free_cells + 1
        if empty_cascades > 0:
            return base * (2 ** empty_cascades)
        return base
    
    def get_sequence_from_cascade(self, col, start_row):
        cascade:List[Card] = self.current_state.cascades[col]
        
        if start_row >= len(cascade):
            return []
        sequence = [cascade[start_row]]
        
        for i in range(start_row + 1, len(cascade)):
            if cascade[i].can_place_on(cascade[i-1]):
                sequence.append(cascade[i])
            else:
                return [] 
                
        return sequence
    
    def get_card_rect_at_pos(self, location_type, index, card_index=None):
        if location_type == 'cascade':
            x = CASCADE_START_X + index * CASCADE_SPACING
            
            cascade = self.current_state.cascades[index]
            dynamic_offset_y = min(35, 500 // (max(1, len(cascade)) + 1))
            
            y = CASCADE_START_Y + (card_index if card_index is not None else 0) * dynamic_offset_y
            return pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
            
        elif location_type == 'freecell':
            x = FREE_CELL_START_X + index * (CARD_WIDTH + CARD_PADDING)
            y = FREE_CELL_START_Y
            return pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
            
        elif location_type == 'foundation':
            x = FOUNDATION_START_X + index * (CARD_WIDTH + CARD_PADDING)
            y = FOUNDATION_START_Y
            return pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
            
        return None
    
    def get_card_at_pos(self, pos):
        x, y = pos
        for i, (suit, pile) in enumerate(self.current_state.foundations.items()):
            found_x = FOUNDATION_START_X + i * (CARD_WIDTH + CARD_PADDING)
            found_rect = pygame.Rect(found_x, FOUNDATION_START_Y, CARD_WIDTH, CARD_HEIGHT)
            if found_rect.collidepoint(x, y):
                return ('foundation', suit, pile[-1] if pile else None)
        for i in range(4):
            cell_x = FREE_CELL_START_X + i * (CARD_WIDTH + CARD_PADDING)
            cell_rect = pygame.Rect(cell_x, FREE_CELL_START_Y, CARD_WIDTH, CARD_HEIGHT)
            if cell_rect.collidepoint(x, y):
                card = self.current_state.free_cells[i]
                return ('freecell', i, card) if card else ('freecell_empty', i)

        for i in range(8):
            cascade_x = CASCADE_START_X + i * CASCADE_SPACING
            cascade = self.current_state.cascades[i]
            
            dynamic_offset_y = min(35, 500 // (max(1, len(cascade)) + 1))
            
            for j in range(len(cascade) - 1, -1, -1):
                card_y = CASCADE_START_Y + j * dynamic_offset_y
                
                click_h = CARD_HEIGHT if j == len(cascade) - 1 else dynamic_offset_y
                
                card_rect = pygame.Rect(cascade_x, card_y, CARD_WIDTH, click_h)
                if card_rect.collidepoint(x, y):
                    return ('cascade', i, j, cascade[j])
            
            column_rect = pygame.Rect(cascade_x, CASCADE_START_Y, CARD_WIDTH, 500)
            if not cascade and column_rect.collidepoint(x, y):
                return ('cascade_empty', i)

        return None
    def start_drag(self, pos):
        """Bắt đầu kéo thả"""
        if self.solving:
            return
        
        clicked = self.get_card_at_pos(pos)
        if not clicked:
            return
        
        print(f"Start drag: {clicked}")
        
        if clicked[0] == 'cascade':
            _, col, row, card = clicked
            cascade = self.current_state.cascades[col]
            if row == len(cascade) - 1:
                self.dragged_cards = [card]
                self.dragged_source = ('cascade', col)
                self.drag_source_col = col
                self.drag_source_row = row
                self.drag_source_freecell = -1
                self.status_message = f"Dragging 1 card"
            else:
                sequence = self.get_sequence_from_cascade(col, row)
                if sequence:
                    max_allowed = self.get_max_sequence_length()
                    if len(sequence) <= max_allowed:
                        self.dragged_cards = sequence
                        self.dragged_source = ('cascade_sequence', col, row)
                        self.drag_source_col = col
                        self.drag_source_row = row
                        self.drag_source_freecell = -1
                        self.status_message = f"Dragging {len(sequence)} cards"
                    else:
                        self.status_message = f"Cannot drag {len(sequence)} cards! Max: {max_allowed}"
                        return
                else:
                    return
        
        elif clicked[0] == 'freecell':
            _, idx, card = clicked
            self.dragged_cards = [card]
            self.dragged_source = ('freecell', idx)
            self.drag_source_col = -1
            self.drag_source_row = -1
            self.drag_source_freecell = idx
            self.status_message = f"Dragging from freecell"
        
        else:
            return
        self.dragging = True
        self.drag_start_pos = pos
        self.drag_offset_x = pos[0] - self.get_card_rect_at_pos(clicked[0], 
                                                               clicked[1] if len(clicked) > 1 else 0,
                                                               clicked[2] if len(clicked) > 2 else 0).x
        self.drag_offset_y = pos[1] - self.get_card_rect_at_pos(clicked[0],
                                                               clicked[1] if len(clicked) > 1 else 0,
                                                               clicked[2] if len(clicked) > 2 else 0).y
        
        self.drag_positions = []
        for i, card in enumerate(self.dragged_cards):
            self.drag_positions.append((pos[0] - self.drag_offset_x, 
                                       pos[1] - self.drag_offset_y + i * 30))
    
    def update_drag(self, pos):
        if not self.dragging:
            return
        self.drag_positions = []
        for i in range(len(self.dragged_cards)):
            self.drag_positions.append((pos[0] - self.drag_offset_x, 
                                       pos[1] - self.drag_offset_y + i * 30))
    
    def end_drag(self, pos):
        if not self.dragging:
            return
        destination = self.find_drop_target(pos)
        
        if destination and self.dragged_cards:
            self.attempt_drag_move(destination)
        else:
            self.status_message = "Invalid drop target"

        self.dragging = False
        self.dragged_cards = []
        self.dragged_source = None
        self.drag_positions = []
    
    # def find_drop_target(self, pos):
    #         x, y = pos
            
    #         for i, (suit, pile) in enumerate(self.current_state.foundations.items()):
    #             foundation_x = FOUNDATION_START_X + i * (CARD_WIDTH + CARD_PADDING)
    #             foundation_rect = pygame.Rect(foundation_x, FOUNDATION_START_Y, CARD_WIDTH, CARD_HEIGHT)
    #             if foundation_rect.collidepoint(x, y):
    #                 return ('foundation', suit)
            
    #         for i in range(4):
    #             cell_x = FREE_CELL_START_X + i * (CARD_WIDTH + CARD_PADDING)
    #             cell_rect = pygame.Rect(cell_x, FREE_CELL_START_Y, CARD_WIDTH, CARD_HEIGHT)
    #             if cell_rect.collidepoint(x, y):
    #                 return ('freecell', i)
            
    #         for i in range(8):
    #             cascade_x = CASCADE_START_X + i * (CARD_WIDTH + CARD_PADDING)
    #             cascade = self.current_state.cascades[i]
    #             if cascade:
    #                 last_card_y = CASCADE_START_Y + (len(cascade) - 1) * 30
    #                 drop_rect = pygame.Rect(cascade_x, last_card_y, CARD_WIDTH, CARD_HEIGHT + 30)
    #             else:
    #                 drop_rect = pygame.Rect(cascade_x, CASCADE_START_Y, CARD_WIDTH, CARD_HEIGHT + 100)
                
    #             if drop_rect.collidepoint(x, y):
    #                 return ('cascade', i)
            
    #         return None
    
    def find_drop_target(self, pos):
        x, y = pos
        
        # 1. Kiểm tra Foundation (Các ô thu hoạch)
        for i, (suit, pile) in enumerate(self.current_state.foundations.items()):
            foundation_x = FOUNDATION_START_X + i * (CARD_WIDTH + CARD_PADDING)
            foundation_rect = pygame.Rect(foundation_x, FOUNDATION_START_Y, CARD_WIDTH, CARD_HEIGHT)
            if foundation_rect.collidepoint(x, y):
                return ('foundation', suit)
        
        # 2. Kiểm tra Free Cells (Các ô trống phía trên)
        for i in range(4):
            cell_x = FREE_CELL_START_X + i * (CARD_WIDTH + CARD_PADDING)
            cell_rect = pygame.Rect(cell_x, FREE_CELL_START_Y, CARD_WIDTH, CARD_HEIGHT)
            if cell_rect.collidepoint(x, y):
                return ('freecell', i)
        
        # 3. Kiểm tra Cascades (Các cột bài chính)
        for i in range(8):
            # SỬ DỤNG CASCADE_SPACING ĐỂ ĐỒNG BỘ VỚI VỊ TRÍ VẼ
            cascade_x = CASCADE_START_X + i * CASCADE_SPACING
            cascade = self.current_state.cascades[i]
            
            if cascade:
                # Tính toán vị trí lá bài cuối cùng
                last_card_y = CASCADE_START_Y + (len(cascade) - 1) * 30
                # TẠO VÙNG VA CHẠM RỘNG HƠN: 
                # Bao gồm từ đầu cột đến tận cùng phía dưới màn hình để dễ thả bài
                drop_rect = pygame.Rect(cascade_x, CASCADE_START_Y, CARD_WIDTH, SCREEN_HEIGHT - CASCADE_START_Y)
            else:
                # Nếu cột trống, cho phép bấm vào ô trống đó
                drop_rect = pygame.Rect(cascade_x, CASCADE_START_Y, CARD_WIDTH, CARD_HEIGHT + 100)
            
            if drop_rect.collidepoint(x, y):
                return ('cascade', i)
        
        return None
    def attempt_drag_move(self, destination):
        dest_type, dest_idx = destination[0], destination[1]
        
        if self.dragged_source[0] == 'cascade':
            source_col = self.dragged_source[1]
            
            if dest_type == 'cascade':
                move = ('cascade_to_cascade', source_col, dest_idx)
            elif dest_type == 'freecell':
                move = ('cascade_to_freecell', source_col, dest_idx)
            elif dest_type == 'foundation':
                move = ('cascade_to_foundation', source_col)
            else:
                return
        
        elif self.dragged_source[0] == 'cascade_sequence':
            source_col = self.dragged_source[1]
            seq_len = len(self.dragged_cards)
            
            if dest_type == 'cascade':
                dest_cascade = self.current_state.cascades[dest_idx]
                first_card = self.dragged_cards[0]
                
                if dest_cascade and not first_card.can_place_on(dest_cascade[-1]):
                    self.status_message = "Invalid sequence placement"
                    return
                
                empty_free = self.current_state.get_empty_free_cells()
                empty_casc = self.current_state.get_empty_cascades()
                if not dest_cascade:
                    empty_casc -= 1 
                
                max_allowed = (empty_free + 1) * (2 ** max(0, empty_casc))
                if seq_len > max_allowed:
                    self.status_message = f"Cannot move {seq_len} cards! Max: {max_allowed}"
                    return
                self.move_sequence(source_col, dest_idx, seq_len)
                return
            else:
                self.status_message = "Can only drop sequence to cascade"
                return
        
        elif self.dragged_source[0] == 'freecell':
            source_idx = self.dragged_source[1]
            
            if dest_type == 'cascade':
                move = ('freecell_to_cascade', source_idx, dest_idx)
            elif dest_type == 'freecell':
                move = ('freecell_to_freecell', source_idx, dest_idx)
            elif dest_type == 'foundation':
                move = ('freecell_to_foundation', source_idx)
            else:
                return
        else:
            return
        
        all_moves = self.current_state.get_all_moves()
        
        if move in all_moves:
            print(f"Valid move from drag! Applying {move}")
            self.current_state = self.current_state.apply_move(move)
            self.current_state.move_history.append(move)
            self.status_message = f"Moved {len(self.dragged_cards)} card(s)"
            
            if self.current_state.is_goal():
                self.status_message = "Congratulations! You won!"
        else:
            print(f"Invalid move from drag: {move}")
            self.status_message = "Invalid move!"
    
    def move_sequence(self, src_col, dest_col, length):
        src_cascade = self.current_state.cascades[src_col]
        start_row = len(src_cascade) - length
        
        sequence = src_cascade[start_row:]
        
        self.current_state.cascades[src_col] = src_cascade[:start_row]
        
        self.current_state.cascades[dest_col].extend(sequence)
        
        move = ('cascade_sequence', src_col, dest_col, length)
        self.current_state.move_history.append(move)
        
        self.status_message = f"Moved sequence of {length} cards"
    
    def draw(self):
        self.screen.fill(GREEN_TABLE)
        
        header_height = 105
        header_rect = pygame.Rect(0, 0, SCREEN_WIDTH, header_height)
        pygame.draw.rect(self.screen, (20, 60, 15), header_rect) 
        
        pygame.draw.line(self.screen, (255, 215, 0), (0, header_height), (SCREEN_WIDTH, header_height), 2)

        title_shadow = self.big_font.render("FREECELL SOLVER", True, (0, 0, 0))
        title = self.big_font.render("FREECELL SOLVER", True, (255, 215, 0))
        self.screen.blit(title_shadow, (22, 14))
        self.screen.blit(title, (20, 12))

        for button in self.buttons:
            button.draw(self.screen)
        
        if self.status_message:
            status_surface = self.font.render(self.status_message, True, WHITE)
            text_width = status_surface.get_width()
            text_height = status_surface.get_height()

            padding_x, padding_y = 20, 12
            popup_width = text_width + (padding_x * 2)
            popup_height = text_height + (padding_y * 2)
            
            popup_x = (SCREEN_WIDTH - popup_width) // 2
            popup_y = SCREEN_HEIGHT - popup_height - 50
            popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)

            shadow_rect = popup_rect.copy()
            shadow_rect.move_ip(3, 3)
            pygame.draw.rect(self.screen, (0, 0, 0, 100), shadow_rect, border_radius=10)

            pygame.draw.rect(self.screen, (40, 40, 40), popup_rect, border_radius=10)
            pygame.draw.rect(self.screen, (255, 215, 0), popup_rect, 2, border_radius=10)

            self.screen.blit(status_surface, (popup_x + padding_x, popup_y + padding_y))
        pygame.draw.rect(self.screen, WHITE, self.seed_rect, border_radius=5)
        seed_text = self.font.render(f"Seed: {self.seed_input}", True, BLACK)
        self.screen.blit(seed_text, (self.seed_rect.x + 5, self.seed_rect.y + 5))

        if not self.current_state:
            return

        for i in range(4):
            x = FREE_CELL_START_X + i * (CARD_WIDTH + CARD_PADDING)
            y = FREE_CELL_START_Y
            pygame.draw.rect(self.screen, (30, 90, 15), (x, y, CARD_WIDTH, CARD_HEIGHT), border_radius=8)
            pygame.draw.rect(self.screen, (50, 150, 30), (x, y, CARD_WIDTH, CARD_HEIGHT), 2, border_radius=8)
            
            cell = self.current_state.free_cells[i]
            if cell:
                cell.draw(self.screen, x, y, self.font)
        suit_symbols = {'hearts': '♥', 'diamonds': '♦', 'clubs': '♣', 'spades': '♠'}
        suit_colors = {'hearts': RED, 'diamonds': RED, 'clubs': BLACK, 'spades': BLACK}
        
        for i, (suit, pile) in enumerate(self.current_state.foundations.items()):
            x = FOUNDATION_START_X + i * (CARD_WIDTH + CARD_PADDING)
            y = FOUNDATION_START_Y
            
            pygame.draw.rect(self.screen, (30, 90, 15), (x, y, CARD_WIDTH, CARD_HEIGHT), border_radius=8)
            
            if not pile:
                s_name = suit.name.lower() if hasattr(suit, 'name') else str(suit).lower()
                sym_surf = self.large_font.render(suit_symbols.get(s_name, "?"), True, (40, 100, 25))
                self.screen.blit(sym_surf, sym_surf.get_rect(center=(x + CARD_WIDTH//2, y + CARD_HEIGHT//2)))
            else:
                pile[-1].draw(self.screen, x, y, self.font)

        for i, cascade in enumerate(self.current_state.cascades):
            x = CASCADE_START_X + i * CASCADE_SPACING
            
            col_label = self.small_font.render(f"COL {i+1}", True, (50, 150, 30))
            self.screen.blit(col_label, (x + CARD_WIDTH//2 - 20, CASCADE_START_Y - 25))

            for j, card in enumerate(cascade):
                offset_y = min(35, 500 // (len(cascade) + 1)) 
                y = CASCADE_START_Y + j * offset_y
                
                is_dragged = False
                if self.dragging and self.dragged_source:
                    if self.dragged_source[0] == 'cascade' and self.dragged_source[1] == i and j == len(cascade)-1:
                        is_dragged = True
                    elif self.dragged_source[0] == 'cascade_sequence' and self.dragged_source[1] == i and j >= self.drag_source_row:
                        is_dragged = True
                
                if not is_dragged:
                    card.draw(self.screen, x, y, self.font)

        if self.dragging and self.drag_positions:
            for card, pos in zip(self.dragged_cards, self.drag_positions):
                shadow_rect = pygame.Rect(pos[0] + 5, pos[1] + 5, CARD_WIDTH, CARD_HEIGHT)
                pygame.draw.rect(self.screen, (0, 0, 0, 50), shadow_rect, border_radius=8)
                card.draw(self.screen, pos[0], pos[1], self.font)
        if self.solving:
            solving_text = self.font.render("Solving... Please wait", True, (255, 215, 0))
            solving_rect = solving_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self.screen.blit(solving_text, solving_rect)
        pygame.display.flip()
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    button_clicked = False
                    for button in self.buttons:
                        if button.handle_event(event):
                            button_clicked = True
                            if button.text == "New Game":
                                self.new_game()
                            elif button.text == "Restart":
                                self.restart_game()
                            elif button.text == "Undo":
                                self.undo_move()
                            elif button.text in ["BFS", "DFS", "UCS", "A*"]:
                                self.run_solver(button.text)
                    
                    if self.seed_rect.collidepoint(event.pos):
                        self.input_active = True
                    else:
                        self.input_active = False
                    
                    if not button_clicked and not self.solving:
                        self.start_drag(event.pos)
            
            elif event.type == pygame.KEYDOWN:
                if self.input_active:
                    if event.key == pygame.K_RETURN:
                        self.input_active = False
                        if self.seed_input:
                            try:
                                seed = int(self.seed_input)
                                self.new_game(seed)
                            except ValueError:
                                self.status_message = "Invalid seed number!"
                                self.seed_input = ""
                    elif event.key == pygame.K_BACKSPACE:
                        self.seed_input = self.seed_input[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        self.input_active = False
                    else:
                        if event.unicode.isdigit():
                            self.seed_input += event.unicode
                else:
                    if event.key == pygame.K_n:
                        self.new_game()
                    elif event.key == pygame.K_r:
                        self.restart_game()
                    elif event.key == pygame.K_u:
                        self.undo_move()
                    elif event.key == pygame.K_1:
                        self.run_solver("BFS")
                    elif event.key == pygame.K_2:
                        self.run_solver("DFS")
                    elif event.key == pygame.K_3:
                        self.run_solver("UCS")
                    elif event.key == pygame.K_4:
                        self.run_solver("A*")
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and self.dragging:
                    self.end_drag(event.pos)
            
            elif event.type == pygame.MOUSEMOTION:
                for button in self.buttons:
                    button.handle_event(event)
                
                if self.dragging:
                    self.update_drag(event.pos)

    def run_solver(self, solver_name):
        if self.solving:
            return
        
        self.solving = True
        self.status_message = f"Running {solver_name} solver..."
        
        thread = threading.Thread(target=self._solve_game, args=(solver_name,))
        thread.daemon = True
        thread.start()
    
    def _solve_game(self, solver_name):
        try:
            if solver_name == "BFS":
                solver = BFSSolver(self.current_state)
            elif solver_name == "DFS":
                solver = DFSSolver(self.current_state)
            elif solver_name == "UCS":
                solver = UCSSolver(self.current_state)
            else:
                solver = AStarSolver(self.current_state)
            
            results = solver.measure_performance()
            
            if solver.solution:
                self.status_message = f"{solver_name} found solution with {len(solver.solution)} moves"
                self.show_solution_dialog(solver_name, results, solver.solution)
            else:
                self.status_message = f"{solver_name} could not find solution"
            
        except Exception as e:
            self.status_message = f"Error: {str(e)}"
            print(f"Error in solver: {e}")
        finally:
            self.solving = False
    
    def show_solution_dialog(self, solver_name, results, solution):
        lines = [
            f"{solver_name} Solution Found!",
            f"Expanded nodes: {results['expanded_nodes']}",
            f"Search time: {results['search_time']:.2f}s",
            f"Memory: {results['memory_usage']:.2f}MB",
            f"Solution length: {results['solution_length']}",
            "",
            "Replay solution? (Y/N)"
        ]
        
        dialog_surface = pygame.Surface((400, 250))
        dialog_surface.fill(WHITE)
        pygame.draw.rect(dialog_surface, BLACK, dialog_surface.get_rect(), 2)
        
        y_offset = 20
        for line in lines:
            text = self.font.render(line, True, BLACK)
            dialog_surface.blit(text, (20, y_offset))
            y_offset += 30
        
        self.screen.blit(dialog_surface, (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 125))
        pygame.display.flip()
        
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_y:
                        self.replay_solution(solution)
                        waiting = False
                    elif event.key == pygame.K_n:
                        waiting = False
    
    def replay_solution(self, solution):
        self.restart_game()
        
        def play_step(step):
            if step < len(solution):
                self.current_state = self.current_state.apply_move(solution[step])
                self.current_state.move_history.append(solution[step])
                self.draw()
                pygame.time.wait(500)
                if step + 1 < len(solution):
                    pygame.time.set_timer(pygame.USEREVENT, 500)
                    play_step(step + 1)
        
        play_step(0)
        self.status_message = "Replay finished!"
    
    def run(self):
        while self.running:
            self.handle_events()
            self.draw()
            self.clock.tick(FPS)