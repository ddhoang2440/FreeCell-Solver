import heapq
import time
from typing import Dict, List, Optional, Tuple

from backend.game_state import FreeCellState
from backend.solvers.base_solver import BaseSolver


class UCSSolver(BaseSolver):
    """
    Uniform Cost Search theo đúng kiểu Dijkstra trên đồ thị trạng thái hiện ra
    từ FreeCellState.get_all_moves(include_foundation_moves=True).

    Điểm quan trọng:
    - Goal chỉ được chấp nhận khi state goal được pop khỏi priority queue.

    Solver này vẫn cần một cost model vì bài toán không có edge weight đo đạc sẵn.
    Do đó UCS sẽ tối ưu theo "estimated move cost" được định nghĩa rõ ràng trong
    _get_move_cost(), thay vì theo số bước.
    """

    _BASE_COST: Dict[str, int] = {
        "cascade_to_foundation": 1,
        "freecell_to_foundation": 1,
        "freecell_to_cascade": 2,
        "cascade_to_cascade": 2,
        "cascade_to_cascade_sequence": 2,
        "cascade_to_freecell": 3,
        "foundation_to_cascade": 4,
        "foundation_to_freecell": 5,
    }

    _MOVE_PRIORITY: Dict[str, int] = {
        "cascade_to_foundation": 0,
        "freecell_to_foundation": 0,
        "freecell_to_cascade": 1,
        "cascade_to_cascade_sequence": 2,
        "cascade_to_cascade": 3,
        "cascade_to_freecell": 4,
        "foundation_to_cascade": 5,
        "foundation_to_freecell": 6,
    }

    def __init__(self, initial_state: FreeCellState):
        super().__init__(initial_state)
        self.priority_queue: List[Tuple[int, int, int, FreeCellState]] = []
        self.cost_so_far: Dict[FreeCellState, int] = {}
        self.came_from: Dict[
            FreeCellState, Tuple[Optional[FreeCellState], Optional[Tuple]]
        ] = {}
        self._feature_cache: Dict[FreeCellState, Tuple[int, int, int, int]] = {}

        self.socketio = None
        self.game_id = None
        self.start_time: float = 0.0
        self._last_progress_time: float = 0.0
        self._last_sent_nodes: int = 0

    def _get_features(self, state: FreeCellState) -> Tuple[int, int, int, int]:
        """
        Trả về tuple:
        (foundation_cards, empty_free_cells, empty_cascades, blocked_cards)
        """
        if state not in self._feature_cache:
            foundation_cards = sum(len(pile) for pile in state.foundations.values())
            self._feature_cache[state] = (
                foundation_cards,
                state.get_empty_free_cells(),
                state.get_empty_cascades(),
                state.get_blocked_cards_count(),
            )
        return self._feature_cache[state]

    def _get_sequence_length(self, move: Tuple) -> int:
        if move[0] == "cascade_to_cascade_sequence" and len(move) >= 4:
            return max(1, int(move[3]))
        return 1

    def _estimate_uncover_gain(self, state_before: FreeCellState,
                               move: Tuple) -> int:
        """
        Ước lượng lợi ích của việc "mở khóa" lá bên dưới ở source cascade.
        """
        move_type = move[0]
        if move_type not in ("cascade_to_freecell", "cascade_to_cascade",
                             "cascade_to_cascade_sequence"):
            return 0

        src_idx = move[1]
        src_col = state_before.cascades[src_idx]
        seq_len = self._get_sequence_length(move)

        if len(src_col) <= seq_len:
            return 0

        exposed_card = src_col[-seq_len - 1]
        gain = 0

        if exposed_card.can_place_on_foundation(
            state_before.foundations.get(exposed_card.suit, [])
        ):
            gain += 2

        if len(src_col) - seq_len == 0:
            gain += 1

        return gain

    def _resource_pressure_penalty(self, state_before: FreeCellState,
                                   state_after: FreeCellState) -> int:
        """
        Phạt mạnh hơn khi move tiêu tốn tài nguyên tạm trong lúc tài nguyên đang ít.
        """
        _, before_empty_free, before_empty_cascade, _ = self._get_features(
            state_before
        )
        _, after_empty_free, after_empty_cascade, _ = self._get_features(
            state_after
        )

        penalty = 0

        if after_empty_free < before_empty_free:
            penalty += 1
            if before_empty_free <= 1:
                penalty += 1

        if after_empty_cascade < before_empty_cascade:
            penalty += 1
            if before_empty_cascade <= 1:
                penalty += 2

        return penalty

    def _get_move_cost(self, move: Tuple, state_before: FreeCellState,
                       state_after: FreeCellState) -> int:
        """
        Cost ước tính cho một cạnh.

        Đây không phải heuristic cho UCS; đây là định nghĩa cost của chính bài toán.
        UCS vẫn chuẩn miễn là mọi edge cost đều không âm và search không cắt nhánh
        bằng heuristic.

        Mô hình cost:
        - Base cost theo loại move.
        - Reward nhỏ cho move tạo tiến triển trực tiếp:
          tăng foundation, giải phóng free cell / cascade, giảm blocked cards.
        - Penalty nhỏ cho move làm tiêu tốn tài nguyên tạm hoặc tăng blocked cards.
        """
        move_type = move[0]
        base = self._BASE_COST.get(move_type, 3)
        seq_len = self._get_sequence_length(move)

        (
            before_foundation,
            before_empty_free,
            before_empty_cascade,
            before_blocked,
        ) = self._get_features(state_before)
        (
            after_foundation,
            after_empty_free,
            after_empty_cascade,
            after_blocked,
        ) = self._get_features(state_after)

        cost = base

        if move_type == "cascade_to_cascade_sequence":
            # Sequence dài thường tiết kiệm thao tác hơn so với di chuyển từng lá,
            # nhưng vẫn không nên rẻ ngang một single move.
            cost += max(0, seq_len - 1) // 2

        if after_foundation > before_foundation:
            cost -= 2
        if after_empty_free > before_empty_free:
            cost -= 1
        if after_empty_cascade > before_empty_cascade:
            cost -= 1
        if after_blocked < before_blocked:
            cost -= 1

        if after_blocked > before_blocked:
            cost += 1

        cost += self._resource_pressure_penalty(state_before, state_after)
        cost -= self._estimate_uncover_gain(state_before, move)

        if move_type in ("foundation_to_cascade", "foundation_to_freecell"):
            # Kéo bài xuống foundation hợp lệ nhưng thường là bước "trả giá"
            # để sửa một quyết định trước đó, nên phạt rõ hơn.
            cost += 2

        if move_type == "cascade_to_freecell" and before_empty_free <= 1:
            cost += 1

        if move_type in ("cascade_to_cascade", "cascade_to_cascade_sequence"):
            dest_idx = move[2]
            if isinstance(dest_idx, int) and not state_before.cascades[dest_idx]:
                # Dùng cột trống rất mạnh, nên không để nó quá rẻ.
                cost += 1

        return max(1, cost)

    def _sort_moves(self, moves: List[Tuple], state: FreeCellState) -> List[Tuple]:
        """
        Chỉ dùng để tie-break ổn định khi cost bằng nhau, không thay đổi tính UCS.
        """
        def _key(move: Tuple) -> Tuple[int, int]:
            base = self._MOVE_PRIORITY.get(move[0], 99)
            dest_non_empty_bonus = 0
            if move[0] in (
                "cascade_to_cascade",
                "freecell_to_cascade",
                "cascade_to_cascade_sequence",
                "foundation_to_cascade",
            ) and len(move) >= 3:
                dest = move[2]
                if isinstance(dest, int) and state.cascades[dest]:
                    dest_non_empty_bonus = -1
            return (base, dest_non_empty_bonus)

        return sorted(moves, key=_key)

    def _reconstruct_path(self, goal_state: FreeCellState) -> List[Tuple]:
        path: List[Tuple] = []
        current = goal_state

        while True:
            parent_state, move = self.came_from[current]
            if move is None:
                break
            path.append(move)
            current = parent_state

        path.reverse()
        return path

    def _get_depth(self, state: FreeCellState) -> int:
        depth = 0
        current = state

        while True:
            parent_state, move = self.came_from.get(current, (None, None))
            if move is None:
                return depth
            depth += 1
            current = parent_state

    def _send_progress(self, current_state: FreeCellState, depth: int):
        if not self.socketio:
            return

        now = time.time()
        time_diff = now - self._last_progress_time
        node_diff = self.expanded_nodes - self._last_sent_nodes
        if time_diff < 2.0 and node_diff < 10_000:
            return

        foundation_cards = sum(len(p) for p in current_state.foundations.values())
        free_cells_used = sum(1 for c in current_state.free_cells if c is not None)
        elapsed = now - self.start_time if self.start_time else 1.0
        rate = self.expanded_nodes / elapsed if elapsed > 0 else 0.0
        progress = min(99.0, (foundation_cards / 52) * 100)

        try:
            self.socketio.emit("solver_progress", {
                "game_id": self.game_id,
                "solver": "UCS",
                "progress": round(progress, 1),
                "nodes_explored": self.expanded_nodes,
                "current_depth": depth,
                "foundation_cards": foundation_cards,
                "free_cells_used": free_cells_used,
                "exploration_rate": round(rate, 1),
                "queue_size": len(self.priority_queue),
            })
        except Exception:
            pass

        self._last_progress_time = now
        self._last_sent_nodes = self.expanded_nodes

    def solve(self, max_nodes: float = float("inf"),
              max_time: int = 86400) -> Optional[List[Tuple]]:
        self.priority_queue.clear()
        self.cost_so_far.clear()
        self.visited.clear()
        self.came_from.clear()
        self._feature_cache.clear()
        self.expanded_nodes = 0
        self.start_time = time.time()
        self._last_progress_time = self.start_time
        self._last_sent_nodes = 0

        initial_state = self.initial_state
        self.cost_so_far[initial_state] = 0
        self.came_from[initial_state] = (None, None)

        counter = 0
        heapq.heappush(self.priority_queue, (0, 0, counter, initial_state))

        print("[UCS] Starting standard UCS with explicit estimated edge costs")

        while self.priority_queue and self.expanded_nodes < max_nodes:
            now = time.time()
            if now - self.start_time > max_time:
                print(f"[UCS] Time limit - {self.expanded_nodes:,} nodes")
                return None

            current_cost, _, _, current_state = heapq.heappop(self.priority_queue)

            if current_cost > self.cost_so_far.get(current_state, float("inf")):
                continue

            if current_state in self.visited:
                continue

            self.visited.add(current_state)
            self.expanded_nodes += 1

            if self.expanded_nodes % 5_000 == 0:
                depth = self._get_depth(current_state)
                elapsed = time.time() - self.start_time
                rate = self.expanded_nodes / elapsed if elapsed > 0 else 0
                print(
                    f"[UCS] Nodes: {self.expanded_nodes:,}, "
                    f"Rate: {rate:.0f} n/s, "
                    f"Queue: {len(self.priority_queue):,}, "
                    f"Cost: {current_cost}, Depth: {depth}"
                )
                self._send_progress(current_state, depth)

            if current_state.is_goal():
                elapsed = time.time() - self.start_time
                path = self._reconstruct_path(current_state)
                print(
                    f"[UCS] Solution found! "
                    f"Nodes: {self.expanded_nodes:,}, "
                    f"Time: {elapsed:.2f}s, "
                    f"Moves: {len(path)}, Cost: {current_cost}"
                )
                self.solution = path

                if self.socketio:
                    try:
                        self.socketio.emit("solver_progress", {
                            "game_id": self.game_id,
                            "solver": "UCS",
                            "progress": 100,
                            "nodes_explored": self.expanded_nodes,
                            "time_taken": elapsed,
                            "solution_length": len(path),
                        })
                    except Exception:
                        pass

                return path

            moves = current_state.get_all_moves(include_foundation_moves=True)
            moves = self._sort_moves(moves, current_state)

            for priority_idx, move in enumerate(moves):
                new_state = current_state.apply_move(move)
                if new_state is None:
                    continue

                if new_state in self.visited:
                    continue

                edge_cost = self._get_move_cost(move, current_state, new_state)
                new_cost = current_cost + edge_cost

                if new_cost < self.cost_so_far.get(new_state, float("inf")):
                    self.cost_so_far[new_state] = new_cost
                    self.came_from[new_state] = (current_state, move)
                    counter += 1
                    heapq.heappush(
                        self.priority_queue,
                        (new_cost, priority_idx, counter, new_state),
                    )

        print(f"[UCS] Exhausted - {self.expanded_nodes:,} nodes, no solution")
        return None
