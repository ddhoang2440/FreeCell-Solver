import heapq
import time
from typing import List, Tuple, Optional, Dict
from backend.solvers.base_solver import BaseSolver
from backend.game_state import FreeCellState


class UCSSolver(BaseSolver):
    """
    Uniform Cost Search solver for FreeCell.

    Improvements over naive UCS:
    1. Differential move costs — foundation moves are free (cost 0), parking
       a card to a free cell is expensive (cost 5). This guides the frontier
       toward cheaper / better paths without requiring a heuristic.
    2. Move ordering — within the same cost bucket, moves are sorted by
       quality so the heap pops the most promising state first.
    3. Resource limits — configurable max_nodes and max_time stop the search
       before exhausting RAM on hard boards.
    4. SocketIO progress reporting — emits solver_progress events to the
       frontend at regular intervals so the UI stays responsive.
    """

    # ------------------------------------------------------------------ #
    #  Bảng chi phí cơ sở theo loại nước đi                              #
    # ------------------------------------------------------------------ #
    # Chi phí này là giá trị nền trước khi điều chỉnh theo ngữ cảnh.
    # Nước đưa bài lên foundation luôn miễn phí (ưu tiên tuyệt đối).
    # Các nước còn lại sẽ được cộng/trừ thêm dựa vào delta chất lượng state.
    _BASE_COST: Dict[str, int] = {
        'cascade_to_foundation':        0,   # Luôn có lợi — miễn phí
        'freecell_to_foundation':       0,   # Luôn có lợi — miễn phí
        'cascade_to_cascade_sequence':  2,   # Di nhóm — tiết kiệm tài nguyên
        'freecell_to_cascade':          2,   # Giải phóng ô tạm — tốt
        'cascade_to_cascade':           4,   # Di chuyển đơn — trung tính
        'cascade_to_freecell':          6,   # Ngốn ô tạm — tốn kém
    }

    # Thứ tự ưu tiên khi sắp xếp nước đi (giá trị nhỏ = thử trước)
    _MOVE_PRIORITY: Dict[str, int] = {
        'cascade_to_foundation':        0,
        'freecell_to_foundation':       0,
        'cascade_to_cascade_sequence':  1,
        'freecell_to_cascade':          2,
        'cascade_to_cascade':           3,
        'cascade_to_freecell':          4,
    }

    def __init__(self, initial_state: FreeCellState):
        super().__init__(initial_state)
        self.priority_queue: List = []
        self.cost_so_far: Dict[int, int] = {}

        # Progress-reporting bookkeeping (set by app.py after construction)
        self.socketio = None
        self.game_id = None
        self.start_time: float = 0.0
        self._last_progress_time: float = 0.0
        self._last_sent_nodes: int = 0

    # ------------------------------------------------------------------ #
    #  Cost & ordering helpers                                             #
    # ------------------------------------------------------------------ #
    def _state_quality(self, state: 'FreeCellState') -> float:
        """
        Đo chất lượng tổng thể của một state — giá trị càng cao càng tốt.

        Bốn thành phần:
          [A] Tiến độ foundation  : mỗi lá lên foundation = +10 điểm
          [B] Tài nguyên trống    : free cell trống = +3, cascade rỗng = +7
          [C] Bài bị kẹt         : mỗi lá blocked = -4 điểm (phạt)
          [D] Chuỗi có thứ tự     : mỗi lá liên tiếp đúng thứ tự ở cuối cột = +1
        """
        # [A] Tiến độ đưa bài lên foundation — quan trọng nhất
        foundation_score = sum(len(p) for p in state.foundations.values()) * 10

        # [B] Tài nguyên trống — càng nhiều chỗ trống, càng linh hoạt
        resource_score = (state.get_empty_free_cells() * 3 +
                          state.get_empty_cascades() * 7)

        # [C] Phạt bài bị kẹt — bài không thể di chuyển làm tắc nghẽn
        blocked_penalty = state.get_blocked_cards_count() * 4

        # [D] Thưởng cho chuỗi đã sắp xếp đúng thứ tự ở cuối mỗi cột
        sequence_bonus = 0
        for cascade in state.cascades:
            for i in range(len(cascade) - 1, 0, -1):
                if cascade[i].can_place_on(cascade[i - 1]):
                    sequence_bonus += 1
                else:
                    break

        return foundation_score + resource_score - blocked_penalty + sequence_bonus

    def _get_move_cost(self, move: Tuple,
                       state_before: 'FreeCellState',
                       state_after: 'FreeCellState') -> int:
        """
        Tính chi phí thực tế của một nước đi dựa vào ngữ cảnh state.

        Công thức:
            edge_cost = base_cost - (improvement // 2)
            trong đó improvement = quality(state_after) - quality(state_before)

        - Nước cải thiện state nhiều → improvement lớn → edge_cost nhỏ (thưởng)
        - Nước làm state xấu đi     → improvement âm  → edge_cost lớn (phạt)
        - Foundation moves           → luôn trả về 0 (ưu tiên tuyệt đối)
        - Non-foundation moves       → tối thiểu = 1 (đảm bảo g(n) tăng nghiêm ngặt)
        """
        # Foundation moves luôn miễn phí — ưu tiên tuyệt đối trong UCS
        if move[0] in ('cascade_to_foundation', 'freecell_to_foundation'):
            return 0

        base = self._BASE_COST.get(move[0], 4)

        # Tính delta chất lượng giữa state trước và sau khi thực hiện move
        q_before = self._state_quality(state_before)
        q_after  = self._state_quality(state_after)
        improvement = q_after - q_before   # Dương = state tốt hơn

        # Điều chỉnh: improvement chia 2 để tránh thưởng/phạt quá mạnh
        edge_cost = base - int(improvement // 2)

        # Đảm bảo min=1: g(n) luôn tăng theo độ sâu, không có zero-cost plateau
        return max(1, edge_cost)

    def _sort_moves(self, moves: List[Tuple], state: FreeCellState) -> List[Tuple]:
        """Sort moves by quality so better moves are pushed with lower tie-break counters."""
        def _key(move: Tuple) -> int:
            base = self._MOVE_PRIORITY.get(move[0], 5)
            # Extra reward: moving to non-empty cascade (avoids wasting empty slots)
            if move[0] in ('cascade_to_cascade', 'freecell_to_cascade',
                           'cascade_to_cascade_sequence'):
                if len(move) >= 3:
                    dest_idx = move[2]
                    if state.cascades[dest_idx]:   # non-empty destination
                        return base - 1            # slight preference
            return base

        return sorted(moves, key=_key)

    # ------------------------------------------------------------------ #
    #  SocketIO progress                                                   #
    # ------------------------------------------------------------------ #
    def _send_progress(self, current_state: FreeCellState, current_path: List):
        if not self.socketio:
            return

        now = time.time()
        time_diff = now - self._last_progress_time
        node_diff = self.expanded_nodes - self._last_sent_nodes

        # Throttle: emit at most once every 2 s OR every 10 000 nodes
        if time_diff < 2.0 and node_diff < 10_000:
            return

        foundation_cards = sum(len(p) for p in current_state.foundations.values())
        free_cells_used = sum(1 for c in current_state.free_cells if c is not None)
        elapsed = now - self.start_time if self.start_time else 1.0
        rate = self.expanded_nodes / elapsed if elapsed > 0 else 0.0
        progress = min(99.0, (foundation_cards / 52) * 100)

        try:
            self.socketio.emit('solver_progress', {
                'game_id': self.game_id,
                'solver': 'UCS',
                'progress': round(progress, 1),
                'nodes_explored': self.expanded_nodes,
                'current_depth': len(current_path),
                'foundation_cards': foundation_cards,
                'free_cells_used': free_cells_used,
                'exploration_rate': round(rate, 1),
                'queue_size': len(self.priority_queue),
            })
        except Exception:
            pass

        self._last_progress_time = now
        self._last_sent_nodes = self.expanded_nodes

    # ------------------------------------------------------------------ #
    #  Main search                                                         #
    # ------------------------------------------------------------------ #
    def solve(self, max_nodes: float = float('inf'), max_time: int = 86400) -> Optional[List[Tuple]]:
        """
        UCS search for a FreeCell solution.

        Args:
            max_nodes: Abort after expanding this many nodes (default: unlimited).
            max_time:  Abort after this many seconds (default: 24h — effectively unlimited).

        Returns:
            List of moves leading to a solved board, or None if no solution exists.
        """
        # --- Reset state ---------------------------------------------------
        self.priority_queue.clear()
        self.cost_so_far.clear()
        self.visited.clear()
        self.expanded_nodes = 0
        self.start_time = time.time()
        self._last_progress_time = self.start_time
        self._last_sent_nodes = 0

        initial_hash = hash(self.initial_state)
        self.cost_so_far[initial_hash] = 0

        # Heap entry: (cumulative_cost, tie_break_counter, state, path)
        counter = 0
        heapq.heappush(self.priority_queue, (0, counter, self.initial_state, []))

        print(f"[UCS] Starting search — no node/time limits (will run until solution found)")

        # --- Search loop ---------------------------------------------------
        while self.priority_queue and self.expanded_nodes < max_nodes:
            # Check wall-clock time limit
            now = time.time()
            if now - self.start_time > max_time:
                print(f"[UCS] Time limit reached after {self.expanded_nodes:,} nodes")
                return None

            current_cost, _, current_state, path = heapq.heappop(self.priority_queue)
            current_hash = hash(current_state)

            # Stale entry — a cheaper path was already found
            if current_cost > self.cost_so_far.get(current_hash, float('inf')):
                continue

            # Already fully explored via a shorter/equal path
            if current_hash in self.visited:
                continue

            self.visited.add(current_hash)
            self.expanded_nodes += 1

            # --- Periodic logging & progress --------------------------------
            if self.expanded_nodes % 5_000 == 0:
                elapsed = time.time() - self.start_time
                rate = self.expanded_nodes / elapsed if elapsed > 0 else 0
                print(
                    f"[UCS] Nodes: {self.expanded_nodes:,}, "
                    f"Rate: {rate:.0f} n/s, "
                    f"Queue: {len(self.priority_queue):,}, "
                    f"Cost: {current_cost}, "
                    f"Depth: {len(path)}"
                )
                self._send_progress(current_state, path)

            # --- Goal check -------------------------------------------------
            if current_state.is_goal():
                elapsed = time.time() - self.start_time
                print(
                    f"[UCS] Solution found! "
                    f"Nodes: {self.expanded_nodes:,}, "
                    f"Time: {elapsed:.2f}s, "
                    f"Path length: {len(path)}, "
                    f"Total cost: {current_cost}"
                )
                self.solution = path

                if self.socketio:
                    try:
                        self.socketio.emit('solver_progress', {
                            'game_id': self.game_id,
                            'solver': 'UCS',
                            'progress': 100,
                            'nodes_explored': self.expanded_nodes,
                            'time_taken': elapsed,
                            'solution_length': len(path),
                        })
                    except Exception:
                        pass

                return path

            # --- Expand node ------------------------------------------------
            moves = current_state.get_all_moves()
            moves = self._sort_moves(moves, current_state)

            for move in moves:
                new_state = current_state.apply_move(move)
                if new_state is None:
                    continue

                new_hash = hash(new_state)

                # Skip already-visited states
                if new_hash in self.visited:
                    continue

                # Tính edge weight theo ngữ cảnh: trước và sau khi apply move
                new_cost = current_cost + self._get_move_cost(move, current_state, new_state)

                # Only push if this is a strictly better (cheaper) path
                if new_cost < self.cost_so_far.get(new_hash, float('inf')):
                    self.cost_so_far[new_hash] = new_cost
                    counter += 1
                    new_path = path + [move]
                    heapq.heappush(
                        self.priority_queue,
                        (new_cost, counter, new_state, new_path)
                    )

        print(f"[UCS] Search exhausted — expanded {self.expanded_nodes:,} nodes, no solution found")
        return None