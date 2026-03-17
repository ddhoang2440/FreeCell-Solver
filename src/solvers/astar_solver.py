# import heapq
# import itertools
# from typing import List, Optional, Dict, Tuple
# from .base_solver import BaseSolver
# from ..game_state import FreeCellState

# class AStarSolver(BaseSolver):
#     def __init__(self, initial_state: FreeCellState):
#         super().__init__(initial_state)
#         self.name = "A*"
    
#     def heuristic(self, state: FreeCellState) -> float:
#         h = 0.0
        
#         # Cards not in foundation
#         cards_not_in_foundation = state.get_cards_not_in_foundation()
#         h += cards_not_in_foundation * 1.0
        
#         # Penalty for buried important cards
#         for cascade in state.cascades:
#             for i, card in enumerate(cascade):
#                 if card.rank.value <= 3:  # A, 2, 3
#                     depth = len(cascade) - i - 1
#                     h += depth * 0.5
        
#         # Bonus for empty spaces
#         empty_cells = state.get_empty_free_cells()
#         empty_cascades = state.get_empty_cascades()
#         h -= (empty_cells + empty_cascades) * 0.3
        
#         return max(0, h)
    
#     def cost_function(self, move: Tuple) -> int:
#         move_type = move[0]
#         if move_type in ['cascade_to_foundation', 'freecell_to_foundation']:
#             return 1
#         elif move_type in ['cascade_to_cascade']:
#             return 2
#         else:
#             return 3
    
#     def solve(self) -> Optional[List[Tuple]]:
#         if self.initial_state.is_goal():
#             return []
        
#         pq = []
#         initial_h = self.heuristic(self.initial_state)
#         counter = itertools.count()
#         heapq.heappush(pq, (initial_h, next(counter), self.initial_state))
#         # heapq.heappush(pq, (initial_h, self.initial_state))
        
#         g_score = {hash(self.initial_state): 0}
#         came_from: Dict[FreeCellState, Tuple[FreeCellState, Tuple]] = {}
        
#         while pq:
#             current_f, _,current_state = heapq.heappop(pq)
#             current_hash = hash(current_state)
            
#             if current_f > g_score.get(current_hash, float('inf')) + self.heuristic(current_state):
#                 continue
            
#             self.expanded_nodes += 1
            
#             if current_state.is_goal():
#                 return self.reconstruct_path(came_from, current_state)
            
#             for move in current_state.get_all_moves():
#                 new_state = current_state.apply_move(move)
#                 new_hash = hash(new_state)
                
#                 tentative_g = g_score[current_hash] + self.cost_function(move)
                
#                 if tentative_g < g_score.get(new_hash, float('inf')):
#                     g_score[new_hash] = tentative_g
#                     f_score = tentative_g + self.heuristic(new_state)
#                     came_from[new_state] = (current_state, move)
#                     heapq.heappush(pq, (f_score, next(counter),new_state))
        
#         return None
import heapq
import itertools
from typing import List, Optional, Dict, Tuple
from .base_solver import BaseSolver
from ..game_state import FreeCellState


class AStarSolver(BaseSolver):
    def __init__(self, initial_state: FreeCellState):
        super().__init__(initial_state)
        self.name = "A*"

    def heuristic(self, state: FreeCellState) -> float:
        h = 0.0

        cards_not_in_foundation = state.get_cards_not_in_foundation()
        h += cards_not_in_foundation * 1.0

        for cascade in state.cascades:
            for i, card in enumerate(cascade):
                if card.rank.value <= 3:
                    depth = len(cascade) - i - 1
                    h += depth * 0.5

        empty_cells = state.get_empty_free_cells()
        empty_cascades = state.get_empty_cascades()
        h -= (empty_cells + empty_cascades) * 0.3

        return max(0, h)

    def cost_function(self, move: Tuple) -> int:
        move_type = move[0]

        if move_type in ['cascade_to_foundation', 'freecell_to_foundation']:
            return 1
        elif move_type in ['cascade_to_cascade']:
            return 2
        else:
            return 3

    def solve(self) -> Optional[List[Tuple]]:

        if self.initial_state.is_goal():
            return []

        pq = []
        counter = itertools.count()

        initial_h = self.heuristic(self.initial_state)

        heapq.heappush(
            pq,
            (initial_h, next(counter), self.initial_state)
        )

        g_score: Dict[FreeCellState, float] = {
            self.initial_state: 0
        }

        came_from: Dict[
            FreeCellState,
            Tuple[FreeCellState, Tuple]
        ] = {}

        while pq:

            current_f, _, current_state = heapq.heappop(pq)

            if current_f > g_score.get(current_state, float('inf')) + self.heuristic(current_state):
                continue

            self.expanded_nodes += 1

            if current_state.is_goal():
                return self.reconstruct_path(came_from, current_state)

            for move in current_state.get_all_moves():

                new_state = current_state.apply_move(move)

                tentative_g = (
                    g_score[current_state]
                    + self.cost_function(move)
                )

                if tentative_g < g_score.get(new_state, float('inf')):

                    g_score[new_state] = tentative_g

                    f_score = tentative_g + self.heuristic(new_state)

                    came_from[new_state] = (
                        current_state,
                        move
                    )

                    heapq.heappush(
                        pq,
                        (f_score, next(counter), new_state)
                    )

        return None