import heapq
import time
from typing import Dict, List, Optional, Tuple

from backend.game_state import FreeCellState
from backend.solvers.base_solver import BaseSolver


class UCSSolver(BaseSolver):
    """
    Uniform Cost Search cho FreeCell.

    Cost function: additive-only, không dùng state delta.
        foundation = 1, cascade/freecell_to_cascade = 2,
        cascade_to_freecell = 3 (+1 khi khan hiếm slot)

    Tối ưu state-space:
        [1] Auto-move     : foundation moves an toàn apply ngay, không branch
        [2] Canonical hash: sort free cells + normalize empty cascades
                            Dùng trực tiếp làm key — không qua tầng py_hash
                            trung gian để tránh collision
        [3] Move pruning  : no-undo, empty-cascade dedup, bỏ foundation_to_*

    Tối ưu bộ nhớ / tốc độ:
        [4] Heap lưu (cost, priority, depth, counter, canon_hash, last_move)
            — không lưu state object trong heap, tránh memory pressure
            và object comparison overhead
        [5] State lookup dict: canon_hash → state, tra cứu khi pop
        [6] Depth theo dõi trong heap tuple — tránh _get_depth() O(depth)
    """

    _BASE_COST: Dict[str, int] = {
        "cascade_to_foundation":        1,
        "freecell_to_foundation":       1,
        "freecell_to_cascade":          2,
        "cascade_to_cascade":           2,
        "cascade_to_cascade_sequence":  2,
        "cascade_to_freecell":          3,
    }

    _MOVE_PRIORITY: Dict[str, int] = {
        "cascade_to_foundation":        0,
        "freecell_to_foundation":       0,
        "freecell_to_cascade":          1,
        "cascade_to_cascade_sequence":  2,
        "cascade_to_cascade":           3,
        "cascade_to_freecell":          4,
    }

    def __init__(self, initial_state: FreeCellState):
        super().__init__(initial_state)

        # Heap entry: (g_cost, move_priority, depth, counter, canon_hash, last_move)
        # Không lưu state trong heap — tra cứu qua _state_by_hash
        self.priority_queue: List = []

        self.cost_so_far: Dict[int, int] = {}
        self.came_from: Dict[int, Tuple[Optional[int], Optional[object]]] = {}

        # [4] State lookup: canon_hash → FreeCellState
        # Lưu state mới nhất (cheapest) cho mỗi canonical hash
        self._state_by_hash: Dict[int, FreeCellState] = {}

        self.socketio = None
        self.game_id  = None
        self.start_time: float = 0.0
        self._last_progress_time: float = 0.0
        self._last_sent_nodes: int = 0
        self._initial_auto_moves: List[Tuple] = []

    # ------------------------------------------------------------------ #
    #  [2] Canonical hash — key duy nhất, không tầng trung gian           #
    # ------------------------------------------------------------------ #
    def _canonical_hash(self, state: FreeCellState) -> int:
        """
        Chuẩn hóa state để loại duplicate từ hoán vị:
          - Free cells     : sort theo string (None → '')
          - Empty cascades : chỉ đếm số lượng, không phân biệt vị trí
          - Non-empty cols : sort theo nội dung tuple
          - Foundation     : unique theo suit, không cần chuẩn hóa

        Trả về canonical hash dùng trực tiếp làm key cho cost_so_far,
        came_from, visited — không qua tầng py_hash trung gian,
        tránh hash collision giữa các FreeCellState khác nhau.
        """
        fc_key = tuple(sorted(
            (str(c) if c else "") for c in state.free_cells
        ))
        non_empty = sorted(
            tuple(str(c) for c in col)
            for col in state.cascades if col
        )
        empty_count = sum(1 for col in state.cascades if not col)
        fd_key = tuple(
            (suit.name if hasattr(suit, 'name') else str(suit), len(pile))
            for suit, pile in sorted(state.foundations.items(),
                                     key=lambda x: str(x[0]))
        )
        return hash((fc_key, tuple(non_empty), empty_count, fd_key))

    # ------------------------------------------------------------------ #
    #  [1] Auto-move                                                       #
    # ------------------------------------------------------------------ #
    def _apply_auto_moves(
        self, state: FreeCellState, path_moves: List[Tuple]
    ) -> Tuple[FreeCellState, List[Tuple]]:
        """
        Apply liên tiếp foundation moves an toàn — không tạo branch mới.
        foundation_vals được tính 1 lần rồi truyền vào safe() để tránh
        tính lại trong mỗi vòng lặp.
        """
        current = state
        moves   = list(path_moves)
        while True:
            auto = self._find_safe_foundation_move(current)
            if auto is None:
                break
            nxt = current.apply_move(auto)
            if nxt is None:
                break
            moves.append(auto)
            current = nxt
        return current, moves

    def _find_safe_foundation_move(self, state: FreeCellState) -> Optional[Tuple]:
        """
        Lá X an toàn lên foundation khi mọi lá (X-1) màu ngược đã lên foundation.
        fvals tính 1 lần cho cả hàm.
        """
        fvals = {suit: len(pile) for suit, pile in state.foundations.items()}

        def safe(card) -> bool:
            needed = card.rank.value - 1
            if needed == 0:
                return True
            opp = [s for s in state.foundations
                   if _suit_color(s) != _suit_color(card.suit)]
            return all(fvals.get(s, 0) >= needed for s in opp)

        for i, card in enumerate(state.free_cells):
            if card and fvals.get(card.suit, 0) == card.rank.value - 1 and safe(card):
                return ("freecell_to_foundation", i)

        for idx, col in enumerate(state.cascades):
            if not col:
                continue
            card = col[-1]
            if fvals.get(card.suit, 0) == card.rank.value - 1 and safe(card):
                return ("cascade_to_foundation", idx)

        return None

    # ------------------------------------------------------------------ #
    #  Cost function — additive only                                       #
    # ------------------------------------------------------------------ #
    def _get_move_cost(self, move: Tuple, state_before: FreeCellState) -> int:
        """
        Cost encode độ tốn kém thực của move — không dùng state delta.

        Penalty:
          cascade_to_freecell khi empty_free <= 1: +1 (khan hiếm tài nguyên)

        Không phạt move vào empty cascade ở đây vì canonical hash đã
        chuẩn hóa empty cascades — phạt ở cost tạo ra inconsistency
        giữa canonical state và edge cost thực tế.
        """
        mt   = move[0]
        cost = self._BASE_COST.get(mt, 2)

        if mt == "cascade_to_freecell":
            empty_free = sum(1 for c in state_before.free_cells if c is None)
            if empty_free <= 1:
                cost += 1

        return cost

    # ------------------------------------------------------------------ #
    #  [3] Move pruning                                                    #
    # ------------------------------------------------------------------ #
    def _prune_moves(
        self,
        moves: List[Tuple],
        state: FreeCellState,
        last_move: Optional[Tuple],
    ) -> List[Tuple]:
        """
        Rule 1 — No-undo  : không hoàn tác nước vừa đi.
        Rule 2 — Empty dedup: nhiều empty cascades tương đương → chỉ thử 1.
        Rule 3 — No empty src: không di chuyển từ cột rỗng.
        Rule 4 — No foundation_to_*: bỏ hoàn toàn, cực hiếm cần.
        """
        empty_cascades  = {i for i, col in enumerate(state.cascades) if not col}
        used_empty_dest: set = set()
        result = []

        for move in moves:
            mt = move[0]

            # Rule 4
            if mt.startswith("foundation_to"):
                continue

            # Rule 3
            if mt in ("cascade_to_cascade", "cascade_to_cascade_sequence"):
                if move[1] in empty_cascades:
                    continue

            # Rule 2
            if mt in ("cascade_to_cascade", "freecell_to_cascade",
                      "cascade_to_cascade_sequence"):
                dest = move[2] if len(move) > 2 else None
                if isinstance(dest, int) and dest in empty_cascades:
                    src = move[1]
                    if src in used_empty_dest:
                        continue
                    used_empty_dest.add(src)

            # Rule 1
            if last_move is not None and _is_reverse_move(move, last_move):
                continue

            result.append(move)

        return result

    def _sort_moves(self, moves: List[Tuple], state: FreeCellState) -> List[Tuple]:
        """Tie-breaking khi cost bằng nhau."""
        def _key(m: Tuple) -> Tuple[int, int]:
            base  = self._MOVE_PRIORITY.get(m[0], 99)
            bonus = 0
            if m[0] in ("cascade_to_cascade", "freecell_to_cascade",
                        "cascade_to_cascade_sequence") and len(m) >= 3:
                if isinstance(m[2], int) and state.cascades[m[2]]:
                    bonus = -1
            return (base, bonus)
        return sorted(moves, key=_key)

    # ------------------------------------------------------------------ #
    #  Path reconstruction                                                 #
    # ------------------------------------------------------------------ #
    def _reconstruct_path(self, goal_hash: int) -> List[Tuple]:
        segments, current = [], goal_hash
        while True:
            parent_hash, seg = self.came_from[current]
            if seg is None:
                break
            segments.append(seg)
            current = parent_hash
        segments.reverse()
        return [m for seg in segments for m in seg]

    # ------------------------------------------------------------------ #
    #  SocketIO progress                                                   #
    # ------------------------------------------------------------------ #
    def _send_progress(self, state: FreeCellState, depth: int):
        if not self.socketio:
            return
        now = time.time()
        if (now - self._last_progress_time < 2.0
                and self.expanded_nodes - self._last_sent_nodes < 10_000):
            return

        fc_cards = sum(len(p) for p in state.foundations.values())
        fc_used  = sum(1 for c in state.free_cells if c is not None)
        elapsed  = (now - self.start_time) or 1.0
        rate     = self.expanded_nodes / elapsed

        try:
            self.socketio.emit("solver_progress", {
                "game_id":          self.game_id,
                "solver":           "UCS",
                "progress":         round(min(99.0, fc_cards / 52 * 100), 1),
                "nodes_explored":   self.expanded_nodes,
                "current_depth":    depth,
                "foundation_cards": fc_cards,
                "free_cells_used":  fc_used,
                "exploration_rate": round(rate, 1),
                "queue_size":       len(self.priority_queue),
            })
        except Exception:
            pass

        self._last_progress_time = now
        self._last_sent_nodes    = self.expanded_nodes

    # ------------------------------------------------------------------ #
    #  Main search                                                         #
    # ------------------------------------------------------------------ #
    def solve(self, node_limit: int = 200000,
              max_time: int = 300) -> Optional[List[Tuple]]:
        """
        UCS chuẩn với:
          - Cost additive-only (range 1–4), không state delta
          - Canonical hash làm key duy nhất (không tầng py_hash trung gian)
          - State không lưu trong heap — tra qua _state_by_hash
          - Depth theo dõi trong heap tuple — O(1) thay vì O(depth)
        """
        self.priority_queue.clear()
        self.cost_so_far.clear()
        self.visited.clear()
        self.came_from.clear()
        self._state_by_hash.clear()
        self.expanded_nodes      = 0
        self.start_time          = time.time()
        self._last_progress_time = self.start_time
        self._last_sent_nodes    = 0

        # [1] Auto-move từ initial state
        initial_state, self._initial_auto_moves = self._apply_auto_moves(
            self.initial_state, []
        )
        if initial_state.is_goal():
            self.solution = self._initial_auto_moves
            return self._initial_auto_moves

        init_hash = self._canonical_hash(initial_state)
        self.cost_so_far[init_hash]    = 0
        self.came_from[init_hash]      = (None, None)
        self._state_by_hash[init_hash] = initial_state

        # [4] Heap: (g_cost, move_priority, depth, counter, canon_hash, last_move)
        # Không lưu state — tra qua _state_by_hash khi cần
        counter = 0
        heapq.heappush(self.priority_queue, (0, 0, 0, counter, init_hash, None))

        print("[UCS] Starting — cost 1–4, canonical key, hash-only heap")

        # Gửi progress ban đầu ngay khi bắt đầu
        self._send_progress(initial_state, 0)

        while self.priority_queue and self.expanded_nodes < node_limit:
            now = time.time()
            if now - self.start_time > max_time:
                print(f"[UCS] Time limit — {self.expanded_nodes:,} nodes")
                return None

            # [4] Pop hash, tra state từ dict — không compare state objects
            current_cost, _, current_depth, _, current_hash, last_move = \
                heapq.heappop(self.priority_queue)

            # Lazy deletion
            if current_cost > self.cost_so_far.get(current_hash, float("inf")):
                continue

            if current_hash in self.visited:
                continue
            self.visited.add(current_hash)
            self.expanded_nodes += 1

            # Tra state object từ dict
            current_state = self._state_by_hash[current_hash]

            if self.expanded_nodes % 1_000 == 0:
                elapsed = time.time() - self.start_time
                rate    = self.expanded_nodes / elapsed if elapsed > 0 else 0
                print(
                    f"[UCS] Nodes: {self.expanded_nodes:,}, "
                    f"Rate: {rate:.0f} n/s, "
                    f"Queue: {len(self.priority_queue):,}, "
                    f"Cost: {current_cost}, Depth: {current_depth}"
                )
                self._send_progress(current_state, current_depth)

            if current_state.is_goal():
                elapsed = time.time() - self.start_time
                path    = self._initial_auto_moves + self._reconstruct_path(
                    current_hash
                )
                print(
                    f"[UCS] Solution found! Nodes: {self.expanded_nodes:,}, "
                    f"Time: {elapsed:.2f}s, Moves: {len(path)}, "
                    f"Cost: {current_cost}, Depth: {current_depth}"
                )
                self.solution = path
                if self.socketio:
                    try:
                        self.socketio.emit("solver_progress", {
                            "game_id":         self.game_id,
                            "solver":          "UCS",
                            "progress":        100,
                            "nodes_explored":  self.expanded_nodes,
                            "time_taken":      elapsed,
                            "solution_length": len(path),
                        })
                    except Exception:
                        pass
                return path

            # Expand
            moves = current_state.get_all_moves()
            moves = self._sort_moves(moves, current_state)
            moves = self._prune_moves(moves, current_state, last_move)

            for priority_idx, move in enumerate(moves):
                new_state = current_state.apply_move(move)
                if new_state is None:
                    continue

                # [1] Auto-move
                new_state, auto_moves_after = self._apply_auto_moves(
                    new_state, [move]
                )

                # [2] Canonical hash — key duy nhất
                new_hash = self._canonical_hash(new_state)
                if new_hash in self.visited:
                    continue

                edge_cost = self._get_move_cost(move, current_state)
                new_cost  = current_cost + edge_cost

                if new_cost < self.cost_so_far.get(new_hash, float("inf")):
                    self.cost_so_far[new_hash]    = new_cost
                    self.came_from[new_hash]      = (current_hash, auto_moves_after)
                    self._state_by_hash[new_hash] = new_state  # cập nhật state mới nhất
                    counter += 1
                    # [4] Push hash, không push state object
                    heapq.heappush(
                        self.priority_queue,
                        (new_cost, priority_idx, current_depth + 1,
                         counter, new_hash, move)
                    )

        print(f"[UCS] Exhausted — {self.expanded_nodes:,} nodes, no solution")
        return None


# ------------------------------------------------------------------ #
#  Module-level helpers                                               #
# ------------------------------------------------------------------ #
def _suit_color(suit) -> str:
    name = suit.name.lower() if hasattr(suit, "name") else str(suit).lower()
    return "red" if name in ("hearts", "diamonds") else "black"


def _is_reverse_move(move: Tuple, last_move: Tuple) -> bool:
    mt, lmt = move[0], last_move[0]
    pairs = {
        ("cascade_to_freecell", "freecell_to_cascade"),
        ("freecell_to_cascade", "cascade_to_freecell"),
        ("cascade_to_cascade",  "cascade_to_cascade"),
    }
    if (mt, lmt) not in pairs:
        return False
    return (len(move) >= 3 and len(last_move) >= 3
            and move[1] == last_move[2] and move[2] == last_move[1])