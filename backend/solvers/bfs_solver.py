from collections import deque
from typing import List, Tuple, Optional, Dict
from backend.solvers.base_solver import BaseSolver
from backend.game_state import FreeCellState

class BFSSolver(BaseSolver):
    def __init__(self, initial_state: FreeCellState):
        super().__init__(initial_state)
        self.queue = deque()
        self.parent: Dict[FreeCellState, Tuple[FreeCellState, Tuple]] = {}
        
    def solve(self) -> Optional[List[Tuple]]:
        """BFS search for solution"""
        self.queue.clear()
        self.parent.clear()
        self.visited.clear()
        self.expanded_nodes = 0
        
        initial_hash = hash(self.initial_state)
        self.visited.add(initial_hash)
        self.queue.append(self.initial_state)
        self.parent[initial_hash] = (None, None)
        
        while self.queue:
            current_state = self.queue.popleft()
            current_hash = hash(current_state)
            self.expanded_nodes += 1
            
            # Check goal
            if current_state.is_goal():
                return self._reconstruct_path(current_state)
            
            # Generate all possible moves
            for move in current_state.get_all_moves():
                new_state = current_state.apply_move(move)
                new_hash = hash(new_state)
                
                if new_hash not in self.visited:
                    self.visited.add(new_hash)
                    self.queue.append(new_state)
                    self.parent[new_hash] = (current_state, move)
        
        return None  # No solution found
    
    def _reconstruct_path(self, goal_state: FreeCellState) -> List[Tuple]:
        """Reconstruct solution path from parent pointers"""
        path = []
        current = goal_state
        current_hash = hash(current)
        
        while True:
            parent_info = self.parent.get(current_hash)
            if parent_info is None:
                break
            
            parent_state, move = parent_info
            if move is None:
                break
            
            path.append(move)
            current = parent_state
            current_hash = hash(current)
        
        path.reverse()
        self.solution = path
        return path