from collections import deque
from typing import List, Tuple, Optional, Dict
import time
from solvers.base_solver import BaseSolver
from game_state import FreeCellState

class BFSSolver(BaseSolver):
    def __init__(self, initial_state: FreeCellState, **kwargs):
        super().__init__(initial_state, **kwargs)
        self.queue: deque = deque()
        # Lưu mapping: state_hash -> (parent_hash, move_hợp_lệ_đưa_đến_đây)
        self.parent_map: Dict[int, Tuple[Optional[int], Optional[Tuple]]] = {}

    def _send_progress(self, current_state: FreeCellState, current_depth: int):
        socketio = getattr(self, 'socketio', None)
        if not socketio: return
            
        current_time = time.time()
        if not hasattr(self, 'last_progress_time'):
            self.last_progress_time = current_time
        elif current_time - self.last_progress_time < 0.5:
            return 
            
        self.last_progress_time = current_time
        foundation_cards = sum(len(f) for f in current_state.foundations.values())
        elapsed = current_time - self.start_time if self.start_time else 1
        rate = self.expanded_nodes / elapsed if elapsed > 0 else 0
        
        try:
            socketio.emit('solver_progress', {
                'game_id': getattr(self, 'game_id', None),
                'solver': 'BFS',
                'progress': round((foundation_cards / 52.0) * 100, 1),
                'nodes_explored': self.expanded_nodes,
                'current_depth': current_depth,
                'foundation_cards': foundation_cards,
                'free_cells_used': sum(1 for c in current_state.free_cells if c is not None),
                'exploration_rate': round(rate, 1),
                'estimated_remaining': 'calculating...',
            })
        except Exception: pass

    def solve(self, node_limit: int = 500000) -> Optional[List[Tuple]]:
        """BFS chuẩn - Tìm đường đi ngắn nhất dựa trên số quyết định của AI."""
        self.queue.clear()
        self.parent_map.clear()
        self.visited.clear()
        self.expanded_nodes = 0
        self.start_time = time.time()
        verbose = getattr(self, 'verbose', False)

        initial_hash = hash(self.initial_state)
        
        # Kiểm tra nếu bàn cờ đã thắng ngay từ đầu
        if self.initial_state.is_goal():
            return []
            
        # Trạng thái ban đầu: Không có cha, không có nước đi dẫn đến nó
        self.visited.add(initial_hash)
        self.queue.append(self.initial_state)
        self.parent_map[initial_hash] = (None, None)

        try:
            while self.queue:
                if getattr(self, 'cancelled', False): return None

                current_state = self.queue.popleft()
                self.expanded_nodes += 1
                
                if self.expanded_nodes > node_limit:
                    if verbose: print(f"[BFS] Node limit reached!")
                    return None

                # Lấy depth từ parent_map để log
                current_path_temp = self._reconstruct_path(hash(current_state))
                current_depth = len(current_path_temp)

                if self.expanded_nodes % 5000 == 0:
                    self._send_progress(current_state, current_depth)
                    if verbose:
                        print(f"Nodes: {self.expanded_nodes}, Queue: {len(self.queue)}, Depth: {current_depth}")

                # Duyệt tất cả các nước đi có thể
                for move in current_state.get_all_moves():
                    new_state = current_state.apply_move(move)
                    if new_state is None: continue
                    
                    # QUAN TRỌNG: Kích hoạt tự động dọn bài lên móng
                    if hasattr(new_state, 'auto_move_to_foundation'):
                        new_state.auto_move_to_foundation()
                    
                    new_hash = hash(new_state)
                    
                    if new_hash not in self.visited:
                        self.visited.add(new_hash)
                        self.parent_map[new_hash] = (hash(current_state), move)
                        
                        # Kiểm tra đích ngay khi sinh ra Node (Tối ưu cho BFS)
                        if new_state.is_goal():
                            self.solution = self._reconstruct_path(new_hash)
                            self._print_final_stats()
                            return self.solution

                        self.queue.append(new_state)

        finally:
            # Không xóa parent_map ở đây để đảm bảo reconstruct_path chạy được
            pass

        return None

    def _reconstruct_path(self, goal_hash: int) -> List[Tuple]:
        """Truy vết ngược từ đích về nguồn."""
        path = []
        curr = goal_hash
        while curr in self.parent_map:
            parent_hash, move = self.parent_map[curr]
            if move is None: break
            path.append(move)
            curr = parent_hash
        path.reverse()
        return path

    def _print_final_stats(self):
        elapsed = time.time() - self.start_time
        rate = self.expanded_nodes / elapsed if elapsed > 0 else 0
        print(f"\n✓ [BFS] Optimal solution found!")
        print(f"  Nodes expanded: {self.expanded_nodes}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Explicit Moves (AI Decisions): {len(self.solution)}")
        print(f"  Rate: {rate:.0f} nodes/sec\n")
