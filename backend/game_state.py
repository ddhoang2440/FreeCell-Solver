import copy
from typing import List, Tuple, Optional, Dict
from card import Card, Suit, microsoft_deal

class FreeCellState:
    __slots__ = (
        'seed', 'cascades', 'free_cells', 'foundations', 
        'move_history', '_hash', '_cached_moves','_cached_moves_with_foundation',
        '_cached_empty_free_cells', '_cached_empty_cascades',
        '_cached_cards_not_in_foundation', '_cached_blocked_count'
    )
    
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
        self.move_history: List[Tuple] = []
        
        self._hash = None
        self._cached_moves = None
        self._cached_moves_with_foundation = None
        self._cached_empty_free_cells = None
        self._cached_empty_cascades = None
        self._cached_cards_not_in_foundation = None
        self._cached_blocked_count = None
        
        self._deal_cards(seed)
    
    def _deal_cards(self, seed: int):
        deck = microsoft_deal(seed)
        for i, card in enumerate(deck):
            col_index = i % 8
            self.cascades[col_index].append(card)
    
    def _invalidate_cache(self):
        self._hash = None
        self._cached_moves = None
        self._cached_moves_with_foundation = None
        self._cached_empty_free_cells = None
        self._cached_empty_cascades = None
        self._cached_cards_not_in_foundation = None
        self._cached_blocked_count = None
     
    def __hash__(self):
        if self._hash is None:
            cascades_tuple = tuple(
                tuple(card.id for card in cascade if card is not None) 
                for cascade in self.cascades
            )
            
            free_ids = []
            for cell in self.free_cells:
                if cell is not None:
                    free_ids.append(cell.id)
                else:
                    free_ids.append(-1)
            free_cells_tuple = tuple(sorted(free_ids))
            
            foundations_parts = []
            for suit in [Suit.SPADES, Suit.HEARTS, Suit.CLUBS, Suit.DIAMONDS]:
                pile = self.foundations.get(suit, [])
                last_rank = pile[-1].rank.value if pile else 0
                foundations_parts.append(last_rank)
            foundations_tuple = tuple(foundations_parts)
                
            self._hash = hash((cascades_tuple, free_cells_tuple, foundations_tuple))
            
        return self._hash
    
    def __eq__(self, other):
        if not isinstance(other, FreeCellState):
            return False
        if self._hash is not None and other._hash is not None:
            if self._hash != other._hash:
                return False
        return (
            self.cascades == other.cascades and
            self.free_cells == other.free_cells and
            self.foundations == other.foundations
        )
    
    def __lt__(self, other):
        if not isinstance(other, FreeCellState):
            return NotImplemented
        return hash(self) < hash(other)
    
    def get_sequence_from_cascade(self, col: int, start_row: int) -> List[Card]:
        cascade = self.cascades[col]
        
        if start_row >= len(cascade):
            return []
        
        sequence = [cascade[start_row]]
        
        for i in range(start_row + 1, len(cascade)):
            if cascade[i].can_place_on(cascade[i-1]):
                sequence.append(cascade[i])
            else:
                return []
        
        return sequence
    def auto_move_to_foundation(self):
        moved = True
        while moved:
            moved = False
            for i, cascade in enumerate(self.cascades):
                if cascade:
                    if self._is_safe_to_foundation(cascade[-1]):
                        card = cascade.pop()
                        self.foundations[card.suit].append(card)
                        self._invalidate_cache()
                        moved = True
            
            for i, card in enumerate(self.free_cells):
                if card:
                    if self._is_safe_to_foundation(card):
                        self.foundations[card.suit].append(card)
                        self.free_cells[i] = None
                        self._invalidate_cache()
                        moved = True

    def _is_safe_to_foundation(self, card: Card) -> bool:
        foundation_pile = self.foundations[card.suit]
        
        if not card.can_place_on_foundation(foundation_pile):
            return False
            
        if card.rank.value <= 2:
            return True
            
        opp_color_suits = [Suit.SPADES, Suit.CLUBS] if card.suit in [Suit.HEARTS, Suit.DIAMONDS] else [Suit.HEARTS, Suit.DIAMONDS]
        
        safe_rank = card.rank.value - 1
        for suit in opp_color_suits:
            if not self.foundations[suit] or self.foundations[suit][-1].rank.value < safe_rank:
                return False
                
        return True
    def get_max_sequence_length(self, dest_is_empty: bool) -> int:
        empty_free = self.get_empty_free_cells()
        empty_cascades = self.get_empty_cascades()
       
        usable_empty_cascades = empty_cascades - 1 if dest_is_empty else empty_cascades
        
        usable_empty_cascades = max(0, usable_empty_cascades)
        
        return (1 + empty_free) * (1 << usable_empty_cascades)
    def _compute_all_moves(self, include_foundation_moves: bool = False) -> List[Tuple]:
        moves = []

        empty_free = [i for i, c in enumerate(self.free_cells) if c is None]
        empty_casc = [i for i, c in enumerate(self.cascades) if not c]

        first_empty_free = empty_free[0] if empty_free else None
        first_empty_casc = empty_casc[0] if empty_casc else None

        for i, cascade in enumerate(self.cascades):
            if not cascade:
                continue
            card = cascade[-1]
            if card and card.can_place_on_foundation(self.foundations.get(card.suit, [])):
                moves.append(('cascade_to_foundation', i))

        for i, card in enumerate(self.free_cells):
            if card and card.can_place_on_foundation(self.foundations.get(card.suit, [])):
                moves.append(('freecell_to_foundation', i))

        for i, card in enumerate(self.free_cells):
            if not card:
                continue

            if first_empty_casc is not None:
                moves.append(('freecell_to_cascade', i, first_empty_casc))

            for j, dest in enumerate(self.cascades):
                if dest and card.can_place_on(dest[-1]):
                    moves.append(('freecell_to_cascade', i, j))

        if first_empty_free is not None:
            for i, cascade in enumerate(self.cascades):
                if cascade:
                    moves.append(('cascade_to_freecell', i, first_empty_free))

        for i, src in enumerate(self.cascades):
            if not src:
                continue

            card = src[-1]

            if first_empty_casc is not None and i != first_empty_casc:
                moves.append(('cascade_to_cascade', i, first_empty_casc))

            for j, dest in enumerate(self.cascades):
                if i == j or not dest:
                    continue
                if card.can_place_on(dest[-1]):
                    moves.append(('cascade_to_cascade', i, j))
        
        empty_free_count = len(empty_free)
        empty_casc_count = len(empty_casc)

        for i, src in enumerate(self.cascades):
            if len(src) < 2:
                continue
            valid_seq_in_src = [src[-1]]
            for k in range(len(src) - 2, -1, -1):
                if src[k+1].can_place_on(src[k]):
                    valid_seq_in_src.insert(0, src[k])
                else:
                    break
            
            max_seq_len = len(valid_seq_in_src)
            if max_seq_len < 2:
                continue

            for j, dest in enumerate(self.cascades):
                if i == j: continue
                
                is_dest_empty = not dest
                eff_empty_casc = empty_casc_count - 1 if is_dest_empty else empty_casc_count
                max_allowed = (1 + empty_free_count) * (1 << max(0, eff_empty_casc))

                for length in range(2, max_seq_len + 1):
                    if length > max_allowed:
                        break 
                    
                    sub_seq = valid_seq_in_src[-length:]
                    
                    if is_dest_empty:
                        if j == first_empty_casc:
                            moves.append(('cascade_to_cascade_sequence', i, j, length))
                    else:
                        if sub_seq[0].can_place_on(dest[-1]):
                            moves.append(('cascade_to_cascade_sequence', i, j, length))

        if include_foundation_moves:
            moves.extend(self._get_foundation_moves(empty_free, empty_casc))

        return moves

    def _get_foundation_moves(self, empty_free: List[int], empty_casc: List[int]) -> List[Tuple]:
        moves = []
        
        total_foundation_cards = sum(len(pile) for pile in self.foundations.values())
        if total_foundation_cards == 0:
            return moves
        
        for suit, pile in self.foundations.items():
            if not pile:
                continue
                
            card = pile[-1]
            
            # if card.rank.value <= 2:
            #     if not self._should_take_low_card(card):
            #         continue
            
            for free_idx in empty_free:
                moves.append(('foundation_to_freecell', suit.name, free_idx))
            
            for cascade_idx, cascade in enumerate(self.cascades):
                if not cascade:
                    # Đặt vào cascade trống
                    if cascade_idx in empty_casc:
                        moves.append(('foundation_to_cascade', suit.name, cascade_idx))
                elif card.can_place_on(cascade[-1]):
                    # if self._is_beneficial_placement(card, cascade[-1]):
                        moves.append(('foundation_to_cascade', suit.name, cascade_idx))
        
        return moves

    def _should_take_low_card(self, card: Card) -> bool:
        for suit, pile in self.foundations.items():
            if pile and pile[-1].rank.value == card.rank.value + 1:
                return True
        return False

    def _is_beneficial_placement(self, card_from_foundation: Card, dest_top_card: Card) -> bool:
        if card_from_foundation.rank.value == dest_top_card.rank.value - 1:
            return True
        return False

    def get_all_moves(self, include_foundation_moves: bool = False) -> List[Tuple]:
        if include_foundation_moves:
            if self._cached_moves_with_foundation is None:
                self._cached_moves_with_foundation = self._compute_all_moves(True)
            return self._cached_moves_with_foundation
        else:
            if self._cached_moves is None:
                self._cached_moves = self._compute_all_moves(False)
            return self._cached_moves


    # def _compute_all_moves(self) -> List[Tuple]:
    #     moves = []

    #     empty_free = [i for i, c in enumerate(self.free_cells) if c is None]
    #     empty_casc = [i for i, c in enumerate(self.cascades) if not c]

    #     first_empty_free = empty_free[0] if empty_free else None
    #     first_empty_casc = empty_casc[0] if empty_casc else None

    #     for i, cascade in enumerate(self.cascades):
    #         if not cascade:
    #             continue
    #         card = cascade[-1]
    #         if card and card.can_place_on_foundation(self.foundations.get(card.suit, [])):
    #             moves.append(('cascade_to_foundation', i))

    #     for i, card in enumerate(self.free_cells):
    #         if card and card.can_place_on_foundation(self.foundations.get(card.suit, [])):
    #             moves.append(('freecell_to_foundation', i))

    #     for i, card in enumerate(self.free_cells):
    #         if not card:
    #             continue

    #         if first_empty_casc is not None:
    #             moves.append(('freecell_to_cascade', i, first_empty_casc))

    #         for j, dest in enumerate(self.cascades):
    #             if dest and card.can_place_on(dest[-1]):
    #                 moves.append(('freecell_to_cascade', i, j))

    #     if first_empty_free is not None:
    #         for i, cascade in enumerate(self.cascades):
    #             if cascade:
    #                 moves.append(('cascade_to_freecell', i, first_empty_free))

    #     for i, src in enumerate(self.cascades):
    #         if not src:
    #             continue

    #         card = src[-1]

    #         if first_empty_casc is not None and i != first_empty_casc:
    #             moves.append(('cascade_to_cascade', i, first_empty_casc))

    #         for j, dest in enumerate(self.cascades):
    #             if i == j or not dest:
    #                 continue
    #             if card.can_place_on(dest[-1]):
    #                 moves.append(('cascade_to_cascade', i, j))
    #     empty_free_count = len(empty_free)
    #     empty_casc_count = len(empty_casc)

    #     for i, src in enumerate(self.cascades):
    #         if len(src) < 2:
    #             continue
    #         valid_seq_in_src = [src[-1]]
    #         for k in range(len(src) - 2, -1, -1):
    #             if src[k+1].can_place_on(src[k]):
    #                 valid_seq_in_src.insert(0, src[k])
    #             else:
    #                 break
            
    #         max_seq_len = len(valid_seq_in_src)
    #         if max_seq_len < 2:
    #             continue

    #         for j, dest in enumerate(self.cascades):
    #             if i == j: continue
                
    #             is_dest_empty = not dest
    #             eff_empty_casc = empty_casc_count - 1 if is_dest_empty else empty_casc_count
    #             max_allowed = (1 + empty_free_count) * (1 << max(0, eff_empty_casc))

    #             for length in range(2, max_seq_len + 1):
    #                 if length > max_allowed:
    #                     break 
                    
    #                 sub_seq = valid_seq_in_src[-length:]
                    
    #                 if is_dest_empty:
    #                     if j == first_empty_casc:
    #                         moves.append(('cascade_to_cascade_sequence', i, j, length))
    #                 else:
    #                     if sub_seq[0].can_place_on(dest[-1]):
    #                         moves.append(('cascade_to_cascade_sequence', i, j, length))

    #     return moves

    # def get_all_moves(self) -> List[Tuple]:
    #     if self._cached_moves is None:
    #         self._cached_moves = self._compute_all_moves()
    #     return self._cached_moves

    # def apply_move(self, move: Tuple) -> 'FreeCellState | None':
    #     new_state = FreeCellState.__new__(FreeCellState)

    #     new_state.cascades = [c[:] for c in self.cascades]
    #     new_state.free_cells = self.free_cells[:]
    #     new_state.foundations = {s: v[:] for s, v in self.foundations.items()}
    #     # new_state.move_history = self.move_history + [move]
    #     new_state.seed = self.seed

    #     new_state._invalidate_cache()
    #     detailed_move = None
    #     move_type = move[0]

    #     if move_type == 'cascade_to_freecell':
    #         _, c_idx, f_idx = move
    #         if not new_state.cascades[c_idx]:
    #             return None
    #         if new_state.free_cells[f_idx] is not None:
    #             return None

    #         card = new_state.cascades[c_idx].pop()
    #         new_state.free_cells[f_idx] = card
    #         card_data = {'suit': card.suit.name, 'rank': card.rank.value}
    #         detailed_move = (move_type, c_idx, f_idx,card_data)
    #         new_state.move_history = self.move_history + [detailed_move]

    #     elif move_type == 'freecell_to_cascade':
    #         _, f_idx, c_idx = move
    #         card = new_state.free_cells[f_idx]
    #         if card is None:
    #             return None

    #         dest = new_state.cascades[c_idx]
    #         if dest and not card.can_place_on(dest[-1]):
    #             return None

    #         new_state.free_cells[f_idx] = None
    #         dest.append(card)
    #         card_data = {'suit': card.suit.name, 'rank': card.rank.value}
    #         detailed_move = (move_type, c_idx, f_idx, card_data)
    #         new_state.move_history = self.move_history + [detailed_move]

    #     elif move_type == 'cascade_to_cascade':
    #         _, src, dst = move
    #         if not new_state.cascades[src]:
    #             return None

    #         card = new_state.cascades[src][-1]
    #         dest = new_state.cascades[dst]

    #         if dest and not card.can_place_on(dest[-1]):
    #             return None

    #         new_state.cascades[src].pop()
    #         dest.append(card)
    #         card_data = {'suit': card.suit.name, 'rank': card.rank.value}
    #         detailed_move = (move_type, src, dst, card_data)
    #         new_state.move_history = self.move_history + [detailed_move]

    #     elif move_type == 'cascade_to_foundation':
    #         _, idx = move
    #         if not new_state.cascades[idx]:
    #             return None

    #         card = new_state.cascades[idx][-1]
    #         foundation = new_state.foundations.get(card.suit, [])

    #         if not card.can_place_on_foundation(foundation):
    #             return None

    #         new_state.cascades[idx].pop()
    #         foundation.append(card)
    #         new_state.foundations[card.suit] = foundation
    #         card_data = {'suit': card.suit.name, 'rank': card.rank.value}
    #         detailed_move = (move_type, idx, card_data)
    #         new_state.move_history = self.move_history + [detailed_move]

    #     elif move_type == 'freecell_to_foundation':
    #         _, idx = move
    #         card = new_state.free_cells[idx]
    #         if card is None:
    #             return None

    #         foundation = new_state.foundations.get(card.suit, [])
    #         if not card.can_place_on_foundation(foundation):
    #             return None

    #         new_state.free_cells[idx] = None
    #         foundation.append(card)
    #         new_state.foundations[card.suit] = foundation
    #         card_data = {'suit': card.suit.name, 'rank': card.rank.value}
    #         detailed_move = (move_type, idx, card_data)
    #         new_state.move_history = self.move_history + [detailed_move]

    #     elif move_type == 'cascade_to_cascade_sequence':
    #         _, src, dst, length = move

    #         src_c = new_state.cascades[src]
    #         if length <= 0 or length > len(src_c):
    #             return None

    #         seq = src_c[-length:]
    #         if any(card is None for card in seq):
    #             return None

    #         dest = new_state.cascades[dst]
    #         if dest and not seq[0].can_place_on(dest[-1]):
    #             return None

    #         new_state.cascades[src] = src_c[:-length]
    #         dest.extend(seq)
    #         sequence_data = [{'suit': c.suit.name, 'rank': c.rank.value} for c in seq]
    #         detailed_move = (move_type, src, dst,length, sequence_data)
    #         new_state.move_history = self.move_history + [detailed_move]

    #     return new_state
    def apply_move(self, move: Tuple) -> 'FreeCellState | None':
        new_state = FreeCellState.__new__(FreeCellState)

        new_state.cascades = [c[:] for c in self.cascades]
        new_state.free_cells = self.free_cells[:]
        new_state.foundations = {s: v[:] for s, v in self.foundations.items()}
        new_state.seed = self.seed

        new_state._invalidate_cache()
        detailed_move = None
        move_type = move[0]

        if move_type == 'cascade_to_freecell':
            _, c_idx, f_idx = move
            if not new_state.cascades[c_idx]:
                return None
            if new_state.free_cells[f_idx] is not None:
                return None

            card = new_state.cascades[c_idx].pop()
            new_state.free_cells[f_idx] = card
            card_data = {'suit': card.suit.name, 'rank': card.rank.value}
            detailed_move = (move_type, c_idx, f_idx, card_data)
            new_state.move_history = self.move_history + [detailed_move] if hasattr(self, 'move_history') else [detailed_move]

        elif move_type == 'freecell_to_cascade':
            _, f_idx, c_idx = move
            card = new_state.free_cells[f_idx]
            if card is None:
                return None

            dest = new_state.cascades[c_idx]
            if dest and not card.can_place_on(dest[-1]):
                return None

            new_state.free_cells[f_idx] = None
            dest.append(card)
            card_data = {'suit': card.suit.name, 'rank': card.rank.value}
            detailed_move = (move_type, c_idx, f_idx, card_data)
            new_state.move_history = self.move_history + [detailed_move] if hasattr(self, 'move_history') else [detailed_move]

        elif move_type == 'cascade_to_cascade':
            _, src, dst = move
            if not new_state.cascades[src]:
                return None

            card = new_state.cascades[src][-1]
            dest = new_state.cascades[dst]

            if dest and not card.can_place_on(dest[-1]):
                return None

            new_state.cascades[src].pop()
            dest.append(card)
            card_data = {'suit': card.suit.name, 'rank': card.rank.value}
            detailed_move = (move_type, src, dst, card_data)
            new_state.move_history = self.move_history + [detailed_move] if hasattr(self, 'move_history') else [detailed_move]

        elif move_type == 'cascade_to_foundation':
            _, idx = move
            if not new_state.cascades[idx]:
                return None

            card = new_state.cascades[idx][-1]
            foundation = new_state.foundations.get(card.suit, [])

            if not card.can_place_on_foundation(foundation):
                return None

            new_state.cascades[idx].pop()
            foundation.append(card)
            new_state.foundations[card.suit] = foundation
            card_data = {'suit': card.suit.name, 'rank': card.rank.value}
            detailed_move = (move_type, idx, card_data)
            new_state.move_history = self.move_history + [detailed_move] if hasattr(self, 'move_history') else [detailed_move]

        elif move_type == 'freecell_to_foundation':
            _, idx = move
            card = new_state.free_cells[idx]
            if card is None:
                return None

            foundation = new_state.foundations.get(card.suit, [])
            if not card.can_place_on_foundation(foundation):
                return None

            new_state.free_cells[idx] = None
            foundation.append(card)
            new_state.foundations[card.suit] = foundation
            card_data = {'suit': card.suit.name, 'rank': card.rank.value}
            detailed_move = (move_type, idx, card_data)
            new_state.move_history = self.move_history + [detailed_move] if hasattr(self, 'move_history') else [detailed_move]

        elif move_type == 'cascade_to_cascade_sequence':
            _, src, dst, length = move

            src_c = new_state.cascades[src]
            if length <= 0 or length > len(src_c):
                return None

            seq = src_c[-length:]
            if any(card is None for card in seq):
                return None

            dest = new_state.cascades[dst]
            if dest and not seq[0].can_place_on(dest[-1]):
                return None

            new_state.cascades[src] = src_c[:-length]
            dest.extend(seq)
            sequence_data = [{'suit': c.suit.name, 'rank': c.rank.value} for c in seq]
            detailed_move = (move_type, src, dst, length, sequence_data)
            new_state.move_history = self.move_history + [detailed_move] if hasattr(self, 'move_history') else [detailed_move]

        elif move_type == 'foundation_to_freecell':
            _, suit_name, free_idx = move
            from card import Suit
            suit = Suit[suit_name]
            foundation_pile = new_state.foundations.get(suit, [])
            if not foundation_pile:
                return None
            print("hu")
            card = foundation_pile[-1]
            if new_state.free_cells[free_idx] is not None:
                return None
            print("lmao")
            foundation_pile.pop()
            new_state.free_cells[free_idx] = card
            card_data = {'suit': card.suit.name, 'rank': card.rank.value}
            detailed_move = ('foundation_to_freecell', suit.name, free_idx, card_data)
            new_state.move_history = self.move_history + [detailed_move] if hasattr(self, 'move_history') else [detailed_move]

        elif move_type == 'foundation_to_cascade':
            _, suit_name, cascade_idx = move
            from card import Suit
            suit = Suit[suit_name]
            foundation_pile = new_state.foundations.get(suit, [])
            if not foundation_pile:
                return None
            
            card = foundation_pile[-1] 
            dest = new_state.cascades[cascade_idx]
            if dest and not card.can_place_on(dest[-1]):
                return None
            
            foundation_pile.pop()
            dest.append(card)
            card_data = {'suit': card.suit.name, 'rank': card.rank.value}
            detailed_move = ('foundation_to_cascade', suit.name, cascade_idx, card_data)
            new_state.move_history = self.move_history + [detailed_move] if hasattr(self, 'move_history') else [detailed_move]
        return new_state

    def is_goal(self) -> bool:
        for pile in self.foundations.values():
            if len(pile) != 13:
                return False
        return True
    
    def get_empty_free_cells(self) -> int:
        if self._cached_empty_free_cells is None:
            count = 0
            for cell in self.free_cells:
                if cell is None:
                    count += 1
            self._cached_empty_free_cells = count
        return self._cached_empty_free_cells
    
    def get_empty_cascades(self) -> int:
        if self._cached_empty_cascades is None:
            count = 0
            for c in self.cascades:
                if len(c) == 0:
                    count += 1
            self._cached_empty_cascades = count
        return self._cached_empty_cascades
    
    def get_cards_not_in_foundation(self) -> int:
        if self._cached_cards_not_in_foundation is None:
            self._cached_cards_not_in_foundation = 52 - sum(len(pile) for pile in self.foundations.values())
        return self._cached_cards_not_in_foundation
    
    def get_blocked_cards_count(self) -> int:
        if self._cached_blocked_count is None:
            self._cached_blocked_count = self._count_blocked_cards()
        return self._cached_blocked_count
    
    def _count_blocked_cards(self) -> int:
        blocked = 0
        
        for cascade in self.cascades:
            if not cascade:
                continue
            
            for i in range(len(cascade) - 1, -1, -1):
                card = cascade[i]
                can_move = False
                
                if card.can_place_on_foundation(self.foundations[card.suit]):
                    can_move = True
                
                if not can_move and self.get_empty_free_cells() > 0:
                    can_move = True
                
                if not can_move:
                    for other_cascade in self.cascades:
                        if other_cascade is cascade:
                            continue
                        if not other_cascade or card.can_place_on(other_cascade[-1]):
                            can_move = True
                            break
                
                if not can_move:
                    blocked += (i + 1)
                    break
        
        return blocked