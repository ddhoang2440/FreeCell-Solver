from typing import List, Optional, Dict, Tuple
from .base_solver import BaseSolver
from ..game_state import FreeCellState

class DFSSolver(BaseSolver):
    def __init__(self, initial_state: FreeCellState, max_depth: int = 100):
        super().__init__(initial_state)
        self.name = "DFS"
        self.max_depth = max_depth
    
    def solve(self) -> Optional[List[Tuple]]:
        for depth in range(1, self.max_depth + 1):
            self.visited.clear()
            result = self.dls(self.initial_state, depth, {})
            if result is not None:
                return result
        return None
    
    def dls(self, state: FreeCellState, depth: int, came_from: Dict) -> Optional[List[Tuple]]:
        if state.is_goal():
            return []
        
        if depth == 0:
            return None
        
        self.expanded_nodes += 1
        state_hash = hash(state)
        self.visited.add(state_hash)
        
        for move in state.get_all_moves():
            new_state = state.apply_move(move)
            new_hash = hash(new_state)
            
            if new_hash not in self.visited:
                new_came_from = came_from.copy()
                new_came_from[new_state] = (state, move)
                
                result = self.dls(new_state, depth - 1, new_came_from)
                if result is not None:
                    return [move] + result
        
        return None