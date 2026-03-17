import copy
import random
from typing import List, Tuple, Optional, Dict
from .card import Card, Suit, Rank, microsoft_deal

class FreeCellState:
    def __init__(self, seed: int = 1):
        self.seed = seed
        self.cascades: List[List[Card]] = [[] for _ in range(8)]
        self.free_cells: List[Optional[Card]] = [None] * 4
        self.foundations: Dict[Suit, List[Card]] = {
            Suit.SPADES: [],
            Suit.HEARTS: [],
            Suit.CLUBS: [],
            Suit.DIAMONDS: []
        }
        self.move_history = []
        self._deal_cards(seed)
    
    def _deal_cards(self, seed: int):
        deck = microsoft_deal(seed)
        for i, card in enumerate(deck):
            col_index = i % 8
            self.cascades[col_index].append(card)
    
    # def __hash__(self): 
    #     state_str = ""
    #     for cascade in self.cascades:
    #         state_str += "|".join(str(card) for card in cascade) + ";"
    #     state_str += "|".join(str(cell) if cell else "None" for cell in self.free_cells) + ";"
    #     for suit, foundation in self.foundations.items():
    #         state_str += str(suit) + ":" + "".join(str(card) for card in foundation) + ";"
    #     return hash(state_str)
    def __hash__(self):
        cascades_tuple = tuple(tuple(str(card) for card in cascade) for cascade in self.cascades)
        freecells_tuple = tuple(str(c) if c else None for c in self.free_cells)

        foundations_tuple = tuple(
            (suit.value, tuple(str(card) for card in foundation))
            for suit, foundation in sorted(self.foundations.items(), key=lambda x: x[0].value)
        )

        return hash((cascades_tuple, freecells_tuple, foundations_tuple))
    def __eq__(self, other):
        if not isinstance(other, FreeCellState):
            return False

        return (
            self.cascades == other.cascades and
            self.free_cells == other.free_cells and
            self.foundations == other.foundations
        )
    
    def get_sequence_from_cascade(self, col, start_row):
        cascade:List[Card] = self.cascades[col] if hasattr(self, 'cascades') else self.current_state.cascades[col]
        
        if start_row >= len(cascade):
            return []
        
        sequence = [cascade[start_row]]
        
        for i in range(start_row + 1, len(cascade)):
            if cascade[i].can_place_on(cascade[i-1]):
                sequence.append(cascade[i])
            else:
                return [] 
                
        return sequence
    def get_all_moves(self) -> List[Tuple]:
        moves = []
        for i, cascade in enumerate(self.cascades):
            if cascade:
                for f_idx, cell in enumerate(self.free_cells):
                    if cell is None:
                        moves.append(('cascade_to_freecell', i, f_idx))
        
        for i, cell in enumerate(self.free_cells):
            if cell:
                for j, cascade in enumerate(self.cascades):
                    if not cascade or cell.can_place_on(cascade[-1]):
                        moves.append(('freecell_to_cascade', i, j))
        
        for i, src_cascade in enumerate(self.cascades):
            if not src_cascade:
                continue
            for j, dest_cascade in enumerate(self.cascades):
                if i == j:
                    continue
                if not dest_cascade or src_cascade[-1].can_place_on(dest_cascade[-1]):
                    moves.append(('cascade_to_cascade', i, j))
        
        for i, src_cell in enumerate(self.free_cells):
            if src_cell:
                for j, dest_cell in enumerate(self.free_cells):
                    if i != j and dest_cell is None:
                        moves.append(('freecell_to_freecell', i, j))
        
        for i, src_cascade in enumerate(self.cascades):
            if not src_cascade:
                continue
            
            for start_row in range(len(src_cascade)):
                sequence = self.get_sequence_from_cascade(i, start_row)
                
                if len(sequence) <= 1:
                    continue 
                
                empty_free_cells = self.get_empty_free_cells()
                empty_cascades = self.get_empty_cascades()
                max_length = empty_free_cells + 1
                if empty_cascades > 0:
                    max_length *= 2
                
                if len(sequence) > max_length:
                    sequence = sequence[:max_length]
                
                for j, dest_cascade in enumerate(self.cascades):
                    if i == j:
                        continue
                    
                    valid = False
                    if not dest_cascade:
                        valid = True
                    elif sequence[0].can_place_on(dest_cascade[-1]):
                        valid = True
                    
                    if valid:
                        moves.append(('cascade_to_cascade_sequence', i, j, len(sequence)))
                        print(f"Added sequence move: from {i} to {j}, length {len(sequence)}")
        
        for i, cascade in enumerate(self.cascades):
            if cascade:
                card = cascade[-1]
                if card.can_place_on_foundation(self.foundations[card.suit]):
                    moves.append(('cascade_to_foundation', i))
        
        for i, cell in enumerate(self.free_cells):
            if cell:
                if cell.can_place_on_foundation(self.foundations[cell.suit]):
                    moves.append(('freecell_to_foundation', i))
        
        return moves
    def apply_move(self, move: Tuple) -> 'FreeCellState':
        new_state = copy.deepcopy(self)
        move_type = move[0]
        
        if move_type == 'cascade_to_freecell':
            _, cascade_idx, free_cell_idx = move
            card = new_state.cascades[cascade_idx].pop()
            new_state.free_cells[free_cell_idx] = card
            
        elif move_type == 'freecell_to_cascade':
            _, free_cell_idx, cascade_idx = move
            card = new_state.free_cells[free_cell_idx]
            new_state.free_cells[free_cell_idx] = None
            new_state.cascades[cascade_idx].append(card)
            
        elif move_type == 'cascade_to_cascade':
            _, src_idx, dest_idx = move
            card = new_state.cascades[src_idx].pop()
            new_state.cascades[dest_idx].append(card)
            
        elif move_type == 'freecell_to_freecell':
            _, src_idx, dest_idx = move
            card = new_state.free_cells[src_idx]
            new_state.free_cells[src_idx] = None
            new_state.free_cells[dest_idx] = card
            
        elif move_type == 'cascade_to_foundation':
            _, cascade_idx = move
            card = new_state.cascades[cascade_idx].pop()
            new_state.foundations[card.suit].append(card)
            
        elif move_type == 'freecell_to_foundation':
            _, free_cell_idx = move
            card = new_state.free_cells[free_cell_idx]
            new_state.free_cells[free_cell_idx] = None
            new_state.foundations[card.suit].append(card)
        
        return new_state
    
    def is_goal(self) -> bool:
        return all(len(pile) == 13 for pile in self.foundations.values())
    
    def get_empty_free_cells(self) -> int:
        return self.free_cells.count(None)
    
    def get_empty_cascades(self) -> int:
        return sum(1 for c in self.cascades if not c)
    
    def get_cards_not_in_foundation(self) -> int:
        return 52 - sum(len(pile) for pile in self.foundations.values())