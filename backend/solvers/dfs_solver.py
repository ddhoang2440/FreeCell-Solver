from typing import List, Tuple, Optional
from backend.solvers.base_solver import BaseSolver
from backend.game_state import FreeCellState

class DFSSolver(BaseSolver):
    def __init__(self, initial_state: FreeCellState, max_depth: int = 100):
        super().__init__(initial_state)
        self.max_depth = max_depth
        self.stack = []
        
    def solve(self) -> Optional[List[Tuple]]:
        """DFS search for solution"""
        self.visited.clear()
        self.stack.clear()
        self.expanded_nodes = 0
        
        initial_hash = hash(self.initial_state)
        self.visited.add(initial_hash)
        self.stack.append((self.initial_state, []))  # (state, path)
        
        while self.stack:
            current_state, path = self.stack.pop()
            current_hash = hash(current_state)
            self.expanded_nodes += 1
            
            # Check goal
            if current_state.is_goal():
                self.solution = path
                return path
            
            # Check depth limit
            if len(path) >= self.max_depth:
                continue
            
            # Generate all possible moves
            moves = current_state.get_all_moves()
            # Try moves in reverse order for better DFS order
            for move in reversed(moves):
                new_state = current_state.apply_move(move)
                new_hash = hash(new_state)
                
                if new_hash not in self.visited:
                    self.visited.add(new_hash)
                    new_path = path + [move]
                    self.stack.append((new_state, new_path))
        
        return None  # No solution found