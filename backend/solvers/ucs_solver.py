import heapq
from typing import List, Tuple, Optional, Dict
from backend.solvers.base_solver import BaseSolver
from backend.game_state import FreeCellState

class UCSSolver(BaseSolver):
    def __init__(self, initial_state: FreeCellState):
        super().__init__(initial_state)
        self.priority_queue = []  # (cost, state, path)
        self.cost_so_far: Dict[int, int] = {}
        
    def _get_move_cost(self, move: Tuple) -> int:
        """Calculate cost of a move (all moves cost 1 in basic FreeCell)"""
        return 1
    
    def solve(self) -> Optional[List[Tuple]]:
        """UCS search for solution"""
        self.priority_queue.clear()
        self.cost_so_far.clear()
        self.visited.clear()
        self.expanded_nodes = 0
        
        initial_hash = hash(self.initial_state)
        heapq.heappush(self.priority_queue, (0, self.initial_state, []))
        self.cost_so_far[initial_hash] = 0
        
        while self.priority_queue:
            current_cost, current_state, path = heapq.heappop(self.priority_queue)
            current_hash = hash(current_state)
            
            # Skip if we've already found a better path
            if current_cost > self.cost_so_far.get(current_hash, float('inf')):
                continue
            
            self.visited.add(current_hash)
            self.expanded_nodes += 1
            
            # Check goal
            if current_state.is_goal():
                self.solution = path
                return path
            
            # Generate all possible moves
            for move in current_state.get_all_moves():
                new_state = current_state.apply_move(move)
                new_hash = hash(new_state)
                new_cost = current_cost + self._get_move_cost(move)
                
                # If this is a better path to new_state
                if new_hash not in self.cost_so_far or new_cost < self.cost_so_far[new_hash]:
                    self.cost_so_far[new_hash] = new_cost
                    new_path = path + [move]
                    heapq.heappush(self.priority_queue, (new_cost, new_state, new_path))
        
        return None  # No solution found