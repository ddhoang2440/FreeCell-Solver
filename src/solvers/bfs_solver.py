from collections import deque
from typing import List, Optional, Dict, Tuple
from .base_solver import BaseSolver
from ..game_state import FreeCellState

class BFSSolver(BaseSolver):
    def __init__(self, initial_state: FreeCellState):
        super().__init__(initial_state)
        self.name = "BFS"
    
    def solve(self) -> Optional[List[Tuple]]:
        if self.initial_state.is_goal():
            return []
        
        queue = deque()
        queue.append(self.initial_state)
        
        came_from: Dict[FreeCellState, Tuple[FreeCellState, Tuple]] = {}
        self.visited.add(hash(self.initial_state))
        
        while queue:
            current_state = queue.popleft()
            self.expanded_nodes += 1
            
            for move in current_state.get_all_moves():
                new_state = current_state.apply_move(move)
                state_hash = hash(new_state)
                
                if state_hash not in self.visited:
                    self.visited.add(state_hash)
                    came_from[new_state] = (current_state, move)
                    
                    if new_state.is_goal():
                        return self.reconstruct_path(came_from, new_state)
                    
                    queue.append(new_state)
        
        return None