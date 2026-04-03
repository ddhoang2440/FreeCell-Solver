
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Set
import time
import tracemalloc
from game_state import FreeCellState

class BaseSolver(ABC):
    def __init__(self, initial_state: FreeCellState, **kwargs):
        self.initial_state = initial_state
        self.solution: List[Tuple] = []
        self.expanded_nodes = 0
        self.search_time = 0
        self.memory_usage = 0
        self.visited: Set = set()
        
        self.game_id = kwargs.get('game_id')
        self.socketio = kwargs.get('socketio')
        self.verbose = kwargs.get('verbose', False)
        self.cancelled = False 
        self.start_time = None
        
    @abstractmethod
    def solve(self) -> Optional[List[Tuple]]:
        pass
    
    def measure_performance(self, **kwargs) -> dict:
        tracemalloc.start()
        self.start_time = time.time()
        solution = self.solve(**kwargs)
        end_time = time.time()

        # Lấy peak memory (lượng bộ nhớ cao nhất trong suốt quá trình chạy)
        _, peak_traced = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        self.search_time = end_time - self.start_time
        self.memory_usage = peak_traced / 1024 / 1024  # Bytes -> MB

        return {
            'expanded_nodes': self.expanded_nodes,
            'search_time': self.search_time,
            'memory_usage': self.memory_usage,
            'solution_length': len(solution) if solution else 0,
            'found_solution': solution is not None
        }