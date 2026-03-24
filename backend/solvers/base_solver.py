
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Set
import time
import psutil
import os
from backend.game_state import FreeCellState

class BaseSolver(ABC):
    def __init__(self, initial_state: FreeCellState):
        self.initial_state = initial_state
        self.solution: List[Tuple] = []
        self.expanded_nodes = 0
        self.search_time = 0
        self.memory_usage = 0
        self.visited: Set = set()
        
        self.game_id = None
        self.start_time = None
        
    @abstractmethod
    def solve(self) -> Optional[List[Tuple]]:
        pass
    
    def measure_performance(self) -> dict:
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / 1024 / 1024 
        self.start_time = time.time()
        solution = self.solve()
        end_time = time.time()
        
        end_memory = process.memory_info().rss / 1024 / 1024 
        
        self.search_time = end_time - self.start_time
        self.memory_usage = end_memory - start_memory
        
        return {
            'expanded_nodes': self.expanded_nodes,
            'search_time': self.search_time,
            'memory_usage': self.memory_usage,
            'solution_length': len(solution) if solution else 0,
            'found_solution': solution is not None
        }