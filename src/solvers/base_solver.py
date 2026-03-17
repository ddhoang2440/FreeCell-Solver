from abc import ABC, abstractmethod
from typing import List, Optional, Set, Dict, Tuple
import time
import psutil
import os
from ..game_state import FreeCellState

class BaseSolver(ABC):
    def __init__(self, initial_state: FreeCellState):
        self.initial_state = initial_state
        self.expanded_nodes = 0
        self.search_time = 0
        self.memory_usage = 0
        self.solution = None
        self.solution_length = 0
        self.visited: Set[int] = set()
    
    @abstractmethod
    def solve(self) -> Optional[List[Tuple]]:
        pass
    
    def measure_performance(self):
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / 1024 / 1024
        
        start_time = time.time()
        solution = self.solve()
        end_time = time.time()
        
        end_memory = process.memory_info().rss / 1024 / 1024
        
        self.search_time = end_time - start_time
        self.memory_usage = end_memory - start_memory
        self.solution = solution
        self.solution_length = len(solution) if solution else 0
        
        return {
            'expanded_nodes': self.expanded_nodes,
            'search_time': self.search_time,
            'memory_usage': self.memory_usage,
            'solution_length': self.solution_length,
            'found': solution is not None
        }
    
    def reconstruct_path(self, came_from: Dict, current_state: FreeCellState) -> List[Tuple]:
        path = []
        while current_state in came_from:
            prev_state, action = came_from[current_state]
            path.append(action)
            current_state = prev_state
        path.reverse()
        return path