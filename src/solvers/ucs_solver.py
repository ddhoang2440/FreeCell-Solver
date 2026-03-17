import heapq
from typing import List, Optional, Dict, Tuple
from .base_solver import BaseSolver
from ..game_state import FreeCellState

class UCSSolver(BaseSolver):
    def __init__(self, initial_state: FreeCellState):
        super().__init__(initial_state)
        self.name = "UCS"
    
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
        heapq.heappush(pq, (0, self.initial_state))
        
        g_score = {hash(self.initial_state): 0}
        came_from: Dict[FreeCellState, Tuple[FreeCellState, Tuple]] = {}
        
        while pq:
            current_cost, current_state = heapq.heappop(pq)
            current_hash = hash(current_state)
            
            if current_cost > g_score.get(current_hash, float('inf')):
                continue
            
            self.expanded_nodes += 1
            
            if current_state.is_goal():
                return self.reconstruct_path(came_from, current_state)
            
            for move in current_state.get_all_moves():
                new_state = current_state.apply_move(move)
                new_hash = hash(new_state)
                
                new_cost = current_cost + self.cost_function(move)
                
                if new_cost < g_score.get(new_hash, float('inf')):
                    g_score[new_hash] = new_cost
                    came_from[new_state] = (current_state, move)
                    heapq.heappush(pq, (new_cost, new_state))
        
        return None