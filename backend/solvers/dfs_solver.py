from typing import List, Set, Tuple, Optional
import time
from solvers.base_solver import BaseSolver
from game_state import FreeCellState

class DFSSolver(BaseSolver):
    def __init__(self, initial_state: FreeCellState,  **kwargs):
        super().__init__(initial_state, **kwargs)
        self.stack = []
        self.visited: Set[int] = set() 
    def _send_progress(self, current_state: FreeCellState, current_path: List):
        if not hasattr(self, 'socketio') or not self.socketio:
            return

        current_time = time.time()

        # Cập nhật WebUI nhiều nhất mỗi 0.5 giây để tránh lag
        # last_progress_time = 0 → emit ngay lần đầu
        last = getattr(self, 'last_progress_time', 0)
        if last > 0 and current_time - last < 0.5:
            return

        self.last_progress_time = current_time

        foundation_cards = sum(len(f) for f in current_state.foundations.values())
        progress = (foundation_cards / 52.0) * 100
        free_cells_used = sum(1 for cell in current_state.free_cells if cell is not None)

        elapsed = current_time - self.start_time if getattr(self, 'start_time', None) else 1
        rate = self.expanded_nodes / elapsed if elapsed > 0 else 0

        try:
            self.socketio.emit('solver_progress', {
                'game_id': getattr(self, 'game_id', None),
                'solver': 'DFS (Pure)',
                'progress': float(f"{progress:.1f}"),
                'nodes_explored': self.expanded_nodes,
                'current_depth': len(current_path),
                'foundation_cards': foundation_cards,
                'free_cells_used': free_cells_used,
                'exploration_rate': float(f"{rate:.1f}"),
                'estimated_remaining': "calculating..."
            })
        except Exception:
            pass

    def solve(self, node_limit: int = 200000, max_time: int = 300) -> Optional[List[Tuple]]:
        """Depth-First Search"""
        self.visited.clear()
        self.stack.clear()
        self.expanded_nodes = 0
        self.start_time = time.time()
        
        initial_hash = hash(self.initial_state)
        
        if self.initial_state.is_goal():
            self.solution = []
            return []
            
        self.visited.add(initial_hash)        
        self.stack.append((self.initial_state, []))  # (state, path)

        # Gửi progress ban đầu ngay khi bắt đầu
        self._send_progress(self.initial_state, [])

        while self.stack:
            if getattr(self, 'cancelled', False):
                if self.verbose:
                    print(f"[DFS] Search cancelled for game {getattr(self, 'game_id', 'unknown')}")
                return None
                
            current_time = time.time()
            if current_time - self.start_time > max_time:
                if self.verbose:
                    print(f"Time limit reached after {self.expanded_nodes} nodes explored")
                return None
                
            if self.expanded_nodes > node_limit:
                if self.verbose:
                    print(f"Max nodes reached: {self.expanded_nodes}")
                return None

            # 1. Lấy đỉnh tiếp theo trong stack (LIFO - Hậu vào tiên xuất)
            current_state, path = self.stack.pop()
            current_depth = len(path)
            self.expanded_nodes += 1
            
            if self.expanded_nodes % 1000 == 0:
                elapsed = current_time - self.start_time
                rate = self.expanded_nodes / elapsed if elapsed > 0 else 0
                if self.verbose:
                    print(f"[DFS] Nodes: {self.expanded_nodes}, Rate: {rate:.0f} n/s, Stack: {len(self.stack)}, Depth: {current_depth}")
                self._send_progress(current_state, path)

            moves = current_state.get_all_moves()
            for move in reversed(moves): 
                new_state = current_state.apply_move(move)
                if new_state is None:
                    continue

                if hasattr(new_state, 'auto_move_to_foundation'):
                    new_state.auto_move_to_foundation()
                
                new_hash = hash(new_state)
                new_depth = current_depth + 1
                
                # Nếu chưa thăm hoặc tìm được đường đi ngắn hơn tới trạng thái này
                if new_hash not in self.visited:
                    self.visited.add(new_hash)
                    new_path = path + [move]
                    
                    # KIỂM TRA ĐÍCH (Đã được gộp lại an toàn ở đây)
                    if new_state.is_goal():
                        self.solution = new_path
                        elapsed = time.time() - self.start_time
                        rate = self.expanded_nodes / elapsed if elapsed > 0 else 0
                        
                        # Luôn in thông số ra Terminal
                        print("\n✓ [DFS] Solution found!")
                        print(f"  Nodes expanded: {self.expanded_nodes}")
                        print(f"  Time: {elapsed:.2f}s")
                        print(f"  Solution length: {len(new_path)} moves")
                        print(f"  Rate: {rate:.0f} nodes/sec\n")
                        
                        return new_path
                        
                    self.stack.append((new_state, new_path))
                    
        return None
                    
