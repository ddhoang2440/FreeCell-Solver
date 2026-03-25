
import heapq
import time
from typing import List, Tuple, Optional, Dict
from backend.solvers.base_solver import BaseSolver
from backend.game_state import FreeCellState
from backend.card import Card, Rank, Suit

class AStarSolver(BaseSolver):
    def __init__(self, initial_state: FreeCellState):
        super().__init__(initial_state)
        self.priority_queue = []
        self.g_score: Dict[int, int] = {}
        self.f_score: Dict[int, int] = {}
        self.visited: Dict[int, int] = {}
        self.heuristic_cache: Dict[int, float] = {}
        self.move_cache = {}
        
        self.total_states = 0
        self.last_progress_time = 0
        self.progress_interval = 1.0
        self.best_heuristic = float('inf')
        self.start_heuristic = self._heuristic(initial_state)
        
        self.last_nodes_report = 0
        self.last_sent_nodes = 0

    def _get_moves_cached(self, state: FreeCellState) -> List[Tuple]:
        state_hash = hash(state)
        if state_hash not in self.move_cache:
            self.move_cache[state_hash] = state.get_all_moves()
        return self.move_cache[state_hash]
    
    def _get_move_cost(self, move: Tuple, state: FreeCellState) -> int:
        """All moves cost exactly 1 for admissibility"""
        return 1 
    
    def _sort_moves_by_priority(self, moves: List[Tuple], state: FreeCellState) -> List[Tuple]:
        """Heuristic ordering doesn't affect admissibility, only performance"""
        move_scores = []
        
        for move in moves:
            move_type = move[0]
            score = 0
            
            if move_type in ('cascade_to_foundation', 'freecell_to_foundation'):
                score = -100 
            elif move_type == 'cascade_to_cascade_sequence':
                score = -70
            elif move_type == 'cascade_to_cascade':
                if len(move) >= 3:
                    dest_idx = move[2]
                    if not state.cascades[dest_idx]:
                        score = -50
                    else:
                        score = -20
            elif move_type == 'freecell_to_cascade':
                if len(move) >= 3:
                    dest_idx = move[2]
                    if not state.cascades[dest_idx]:
                        score = -45
                    else:
                        score = -25
            elif move_type == 'cascade_to_freecell':
                score = 10
            elif move_type == 'freecell_to_freecell':
                score = 50
                
            move_scores.append((score, move))
        
        move_scores.sort(key=lambda x: x[0])
        return [move for _, move in move_scores]
    

    def _heuristic(self, state: FreeCellState) -> float:
        state_hash = hash(state)
        if state_hash in self.heuristic_cache:
            return self.heuristic_cache[state_hash]

        h = 0
        cards_not_in_foundation = 52 - sum(len(f) for f in state.foundations.values())
        h += cards_not_in_foundation

        for cascade in state.cascades:
            if not cascade:
                continue
                
            for i in range(len(cascade)):
                card = cascade[i]

                is_blocked = False
                for j in range(i + 1, len(cascade)):
 
                    if not cascade[j].can_place_on(cascade[j-1]):
                        is_blocked = True
                        break
                
                if is_blocked:
                    h += 1 

        empty_slots = sum(1 for c in state.free_cells if c is None)
        empty_slots += sum(1 for cas in state.cascades if not cas)
        
        h -= (empty_slots * 0.01) 

        res = max(0, float(h))
        self.heuristic_cache[state_hash] = res
        return res
    def _get_progress(self, current_heuristic: float) -> float:
        if self.start_heuristic <= 0:
            return 100.0
            
        improvement = self.start_heuristic - current_heuristic
        max_possible = self.start_heuristic
        progress = (improvement / max_possible) * 100
        
        return max(0, min(99, progress))
    def _send_progress(self, current_state: FreeCellState, current_path: List):
        current_time = time.time()

        time_diff = current_time - self.last_progress_time
        nodes_diff = self.expanded_nodes - self.last_sent_nodes if hasattr(self, 'last_sent_nodes') else 0
        
        if time_diff < 2 and nodes_diff < 10000:
            return  
        if not self.socketio:
            return
            
        current_heuristic = self._heuristic(current_state)
        progress = self._get_progress(current_heuristic)
        
        if current_heuristic < self.best_heuristic:
            self.best_heuristic = current_heuristic
        
        foundation_cards = 0
        for suit in current_state.foundations:
            foundation_cards += len(current_state.foundations[suit])
        
        free_cells_used = sum(1 for cell in current_state.free_cells if cell is not None)
        
        elapsed = current_time - self.start_time if self.start_time else 1
        rate = self.expanded_nodes / elapsed if elapsed > 0 else 0
        
        try:
            self.socketio.emit('solver_progress', {
                'game_id': self.game_id,
                'solver': 'A*',
                'progress': round(progress, 1),
                'nodes_explored': self.expanded_nodes,
                'current_depth': len(current_path),
                'best_heuristic': self.best_heuristic,
                'current_heuristic': current_heuristic,
                'foundation_cards': foundation_cards,
                'free_cells_used': free_cells_used,
                'exploration_rate': round(rate, 1),
                'estimated_remaining': self._estimate_remaining_time(rate, current_heuristic)
            })
            
            self.last_progress_time = current_time
            self.last_sent_nodes = self.expanded_nodes
            
        except Exception as e:
            pass
    
    def _estimate_remaining_time(self, rate: float, current_heuristic: float) -> str:
        if rate <= 0:
            return "calculating..."
            
        remaining_improvement = current_heuristic
        estimated_nodes = remaining_improvement * 100
        estimated_seconds = estimated_nodes / rate
        
        if estimated_seconds < 60:
            return f"~{int(estimated_seconds)}s"
        elif estimated_seconds < 3600:
            return f"~{int(estimated_seconds/60)}m"
        else:
            return f"~{int(estimated_seconds/3600)}h"
        
    def solve(self, max_nodes: int = 500000, max_time: int = 300) -> Optional[List[Tuple]]:
        self.priority_queue.clear()
        self.g_score.clear()
        self.f_score.clear()
        self.visited.clear()
        self.expanded_nodes = 0
        self.start_time = time.time()
        self.last_progress_time = self.start_time
        self.best_heuristic = float('inf')
        
        initial_hash = hash(self.initial_state)
        initial_h = self._heuristic(self.initial_state)
        self.start_heuristic = initial_h
        
        print(f"Starting A* search with initial heuristic: {initial_h}")
        print(f"Goal: Find optimal solution (minimizing moves)")
        
        self.g_score[initial_hash] = 0
        self.f_score[initial_hash] = initial_h
        
        heapq.heappush(self.priority_queue, (initial_h, 0, 0, self.initial_state, []))
        
        counter = 1
        
        while self.priority_queue and self.expanded_nodes < max_nodes:
            current_time = time.time()
            if current_time - self.start_time > max_time:
                print(f"Time limit reached after {self.expanded_nodes} nodes")
                return None
                
            current_f, current_g, depth, current_state, path = heapq.heappop(self.priority_queue)
            current_hash = hash(current_state)
            
            if self.expanded_nodes % 5000 == 0:
                elapsed = current_time - self.start_time
                rate = self.expanded_nodes / elapsed if elapsed > 0 else 0
                print(f"Nodes: {self.expanded_nodes}, Rate: {rate:.0f} n/s, "
                      f"Queue: {len(self.priority_queue)}, f: {current_f:.1f}, "
                      f"g: {current_g}, Depth: {len(path)}")
                self._send_progress(current_state, path)
            
            if current_g > self.g_score.get(current_hash, float('inf')):
                continue
            
            if current_hash in self.visited:
                if self.visited[current_hash] <= len(path):
                    continue
            
            self.visited[current_hash] = len(path)
            self.expanded_nodes += 1
            
            if current_state.is_goal():
                elapsed = time.time() - self.start_time
                print(f"✓ Optimal solution found!")
                print(f"  Nodes expanded: {self.expanded_nodes}")
                print(f"  Time: {elapsed:.2f}s")
                print(f"  Solution length: {len(path)} moves")
                print(f"  Rate: {self.expanded_nodes/elapsed:.0f} nodes/sec")
                self.solution = path
                
                if self.socketio:
                    self.socketio.emit('solver_progress', {
                        'game_id': self.game_id if hasattr(self, 'game_id') else None,
                        'solver': 'A*',
                        'progress': 100,
                        'nodes_explored': self.expanded_nodes,
                        'time_taken': elapsed,
                        'solution_length': len(path),
                        'optimal': True
                    })
                
                return path
            
            moves = self._get_moves_cached(current_state)
            moves = self._sort_moves_by_priority(moves, current_state)
            
            for move in moves:
                new_state = current_state.apply_move(move)
                if new_state is None or new_state is current_state:
                    continue
                    
                new_hash = hash(new_state)
                
                if new_hash in self.visited:
                    if self.visited[new_hash] <= len(path) + 1:
                        continue
                
                tentative_g = current_g + 1
                
                if new_hash not in self.g_score or tentative_g < self.g_score[new_hash]:
                    self.g_score[new_hash] = tentative_g
                    h_score = self._heuristic(new_state)
                    f_score = tentative_g + h_score
                    self.f_score[new_hash] = f_score
                    
                    new_path = path + [move]
                    heapq.heappush(self.priority_queue, (f_score, tentative_g, counter, new_state, new_path))
                    counter += 1
        
        print(f"Max nodes reached without solution: {self.expanded_nodes}")
        return None