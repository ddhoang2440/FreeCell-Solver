import heapq
import time
from typing import Dict, List, Optional, Tuple

from backend.game_state import FreeCellState
from backend.solvers.base_solver import BaseSolver


class UCSSolver(BaseSolver):
    """
    Uniform Cost Search cho FreeCell — phiên bản cuối.

    Thiết kế cost function:
    ───────────────────────
    Cost CHỈ encode "độ tốn kém thực" của move — không encode
    "state sau tốt/xấu hơn bao nhiêu". Lý do:

        cost -= delta_quality  →  cost âm/thấp giả tạo →
        UCS thấy path "rẻ" nhưng thực ra không dẫn đến goal →
        phải explore hàng trăm nghìn nodes sai hướng.

    Công thức: cost = BASE + penalty_cộng_thêm
    Không có phép trừ nào dựa vào trạng thái state.

    Cost range 1–4:
        foundation move  = 1   (ưu tiên tuyệt đối)
        normal cascade   = 2   (tiêu chuẩn)
        to freecell      = 3   (tốn tài nguyên tạm)
        to freecell khi tight = 4  (penalty khi gần hết slot)

    foundation_to_* bị prune hoàn toàn vì:
        - Cực hiếm khi cần trong FreeCell chuẩn
        - Chỉ tạo nhánh vô ích, tăng branching factor

    Các tối ưu state-space (không đổi thuật toán):
        [1] Auto-move     : foundation moves an toàn apply ngay, không branch
        [2] Canonical hash: sort free cells + normalize empty cascades
        [3] Move pruning  : no-undo, empty-cascade dedup, prune foundation_to
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
        self.priority_queue: List = []
        self.cost_so_far: Dict[int, int] = {}
        self.came_from: Dict[int, Tuple[Optional[int], Optional[object]]] = {}

        # Cache: python_hash(state) → (canonical_hash, empty_free_cells)
        # Tính 1 lần, dùng lại nhiều lần trong expand
        self._canon_cache: Dict[int, int] = {}
        self._free_cell_cache: Dict[int, int] = {}

        self.socketio = None
        self.game_id  = None
        self.start_time: float = 0.0
        self._last_progress_time: float = 0.0
        self._last_sent_nodes: int = 0
        self._initial_auto_moves: List[Tuple] = []

    # ------------------------------------------------------------------ #
    #  Canonical hash — tái lập, cache để không tính lại                  #
    # ------------------------------------------------------------------ #
    def _canonical_hash(self, state: FreeCellState) -> int:
        """
        Chuẩn hóa state để loại duplicate từ hoán vị:
          - Free cells: sort theo string (None → '')
          - Empty cascades: chỉ đếm số lượng, không phân biệt vị trí
          - Non-empty cascades: sort theo nội dung
          - Foundation: unique theo suit, không cần chuẩn hóa

        Cache theo python hash(state) để tránh tính lại.
        """
        py_hash = hash(state)
        if py_hash in self._canon_cache:
            return self._canon_cache[py_hash]

        fc_key = tuple(sorted(
            (str(c) if c else '') for c in state.free_cells
        ))
        non_empty = sorted(
            tuple(str(c) for c in col)
            for col in state.cascades if col
        )
        empty_count = sum(1 for col in state.cascades if not col)
        fd_key = tuple(
            (str(suit), len(pile))
            for suit, pile in sorted(state.foundations.items(),
                                     key=lambda x: str(x[0]))
        )
        result = hash((fc_key, tuple(non_empty), empty_count, fd_key))
        self._canon_cache[py_hash]    = result
        # Cache luôn empty_free_cells vì _get_move_cost cần
        self._free_cell_cache[py_hash] = state.get_empty_free_cells()
        return result

    def _get_empty_free_cells(self, state: FreeCellState) -> int:
        """Lấy từ cache, tránh gọi lại state.get_empty_free_cells()."""
        py_hash = hash(state)
        if py_hash not in self._free_cell_cache:
            self._canonical_hash(state)   # tính cache
        return self._free_cell_cache[py_hash]

    # ------------------------------------------------------------------ #
    #  [1] Auto-move                                                       #
    # ------------------------------------------------------------------ #
    def _apply_auto_moves(
        self, state: FreeCellState, path_moves: List[Tuple]
    ) -> Tuple[FreeCellState, List[Tuple]]:
        """
        Apply liên tiếp foundation moves an toàn — không tạo branch mới.
        Gộp vào edge hiện tại, không tốn thêm node expand.
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
        Đảm bảo X không cần làm bàn đạp cho cascade move nào sau này.
        """
        fvals = {suit: len(pile) for suit, pile in state.foundations.items()}

        def safe(card) -> bool:
            needed = card.rank.value - 1
            if needed == 0:
                return True
            opp = [s for s in state.foundations if _suit_color(s) != _suit_color(card.suit)]
            return all(fvals.get(s, 0) >= needed for s in opp)

        for i, card in enumerate(state.free_cells):
            if card and fvals.get(card.suit, 0) == card.rank.value - 1 and safe(card):
                return ('freecell_to_foundation', i)

        for idx, col in enumerate(state.cascades):
            if not col:
                continue
            card = col[-1]
            if fvals.get(card.suit, 0) == card.rank.value - 1 and safe(card):
                return ('cascade_to_foundation', idx)

        return None

    # ------------------------------------------------------------------ #
    #  Cost function — additive only, không dùng state delta              #
    # ------------------------------------------------------------------ #
    def _get_move_cost(self, move: Tuple, state_before: FreeCellState) -> int:
        """
        Cost chỉ encode độ tốn kém của move.
        Không compare state_before vs state_after — tránh cost âm giả tạo.

        Các penalty được cộng thêm:
          - cascade_to_freecell: tốn slot tạm (base=3)
          - cascade_to_freecell khi empty_free <= 1: khan hiếm tài nguyên (+1)
          - move vào empty cascade: dùng tài nguyên mạnh (+1)
        """
        mt   = move[0]
        cost = self._BASE_COST.get(mt, 2)

        if mt == "cascade_to_freecell":
            empty_free = self._get_empty_free_cells(state_before)
            if empty_free <= 1:
                cost += 1   # khan hiếm free cell → phạt thêm

        if mt in ("cascade_to_cascade", "freecell_to_cascade",
                  "cascade_to_cascade_sequence"):
            dest_idx = move[2] if len(move) > 2 else None
            if isinstance(dest_idx, int) and not state_before.cascades[dest_idx]:
                cost += 1   # dùng empty cascade → tài nguyên mạnh

        return cost   # guaranteed >= 1 vì _BASE_COST min = 1

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
        Rule 1: Không hoàn tác nước vừa đi (no-undo).
        Rule 2: Nhiều empty cascades tương đương → chỉ thử 1 đại diện.
        Rule 3: Không di chuyển từ cột rỗng.
        Rule 4: Bỏ hoàn toàn foundation_to_* — cực hiếm cần, chỉ tạo nhánh thừa.
        """
        empty_cascades  = {i for i, col in enumerate(state.cascades) if not col}
        used_empty_dest: set = set()
        result = []

        for move in moves:
            mt = move[0]

            # Rule 4: bỏ hoàn toàn foundation_to_*
            if mt.startswith("foundation_to"):
                continue

            # Rule 3: không di chuyển từ cột rỗng
            if mt in ("cascade_to_cascade", "cascade_to_cascade_sequence"):
                if move[1] in empty_cascades:
                    continue

            # Rule 2: empty cascade tương đương → chỉ 1 đại diện
            if mt in ("cascade_to_cascade", "freecell_to_cascade",
                      "cascade_to_cascade_sequence"):
                dest = move[2] if len(move) > 2 else None
                if isinstance(dest, int) and dest in empty_cascades:
                    src = move[1]
                    if src in used_empty_dest:
                        continue
                    used_empty_dest.add(src)

            # Rule 1: no-undo
            if last_move is not None and _is_reverse_move(move, last_move):
                continue

            result.append(move)

        return result

    def _sort_moves(self, moves: List[Tuple], state: FreeCellState) -> List[Tuple]:
        """Tie-breaking khi cost bằng nhau — không ảnh hưởng tính UCS."""
        def _key(m: Tuple) -> Tuple[int, int]:
            base = self._MOVE_PRIORITY.get(m[0], 99)
            bonus = 0
            if m[0] in ("cascade_to_cascade", "freecell_to_cascade",
                        "cascade_to_cascade_sequence") and len(m) >= 3:
                if isinstance(m[2], int) and state.cascades[m[2]]:
                    bonus = -1   # ưu tiên nhẹ move vào cột không rỗng
            return (base, bonus)
        return sorted(moves, key=_key)

    # ------------------------------------------------------------------ #
    #  Path reconstruction                                                 #
    # ------------------------------------------------------------------ #
    def _reconstruct_path(self, goal_hash: int) -> List[Tuple]:
        """Truy ngược came_from. Mỗi entry = [move_chính] + auto-moves."""
        segments, current = [], goal_hash
        while True:
            parent_hash, seg = self.came_from[current]
            if seg is None:
                break
            segments.append(seg)
            current = parent_hash
        segments.reverse()
        return [m for seg in segments for m in seg]

    def _get_depth(self, state_hash: int) -> int:
        depth, cur = 0, state_hash
        while True:
            parent, mv = self.came_from.get(cur, (None, None))
            if mv is None:
                return depth
            depth += 1
            cur = parent

    # ------------------------------------------------------------------ #
    #  SocketIO progress                                                   #
    # ------------------------------------------------------------------ #
    def _send_progress(self, state: FreeCellState, depth: int):
        if not self.socketio:
            return
        now = time.time()
        if now - self._last_progress_time < 2.0 \
                and self.expanded_nodes - self._last_sent_nodes < 10_000:
            return

        fc_cards  = sum(len(p) for p in state.foundations.values())
        fc_used   = sum(1 for c in state.free_cells if c is not None)
        elapsed   = now - self.start_time or 1.0
        rate      = self.expanded_nodes / elapsed

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
    def solve(self, max_nodes: float = float("inf"),
              max_time: int = 86400) -> Optional[List[Tuple]]:
        """
        UCS chuẩn với cost additive-only (range 1–4) và các tối ưu:
          [1] Auto-move foundation an toàn
          [2] Canonical hash — loại duplicate từ hoán vị
          [3] Move pruning — no-undo, empty dedup, bỏ foundation_to
        """
        self.priority_queue.clear()
        self.cost_so_far.clear()
        self.visited.clear()
        self.came_from.clear()
        self._canon_cache.clear()
        self._free_cell_cache.clear()
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
        self.cost_so_far[init_hash] = 0
        self.came_from[init_hash]   = (None, None)

        # Heap: (g_cost, move_priority_tiebreak, counter, state, last_move)
        counter = 0
        heapq.heappush(self.priority_queue, (0, 0, counter, initial_state, None))

        print("[UCS] Starting — additive cost 1–4, canonical hash, auto-move, pruning")

        while self.priority_queue and self.expanded_nodes < max_nodes:
            now = time.time()
            if now - self.start_time > max_time:
                print(f"[UCS] Time limit — {self.expanded_nodes:,} nodes")
                return None

            current_cost, _, _, current_state, last_move = heapq.heappop(
                self.priority_queue
            )
            current_hash = self._canonical_hash(current_state)

            # Lazy deletion: stale entry
            if current_cost > self.cost_so_far.get(current_hash, float("inf")):
                continue

            # Visited check khi POP — đúng lý thuyết UCS
            if current_hash in self.visited:
                continue
            self.visited.add(current_hash)
            self.expanded_nodes += 1

            if self.expanded_nodes % 5_000 == 0:
                depth   = self._get_depth(current_hash)
                elapsed = time.time() - self.start_time
                rate    = self.expanded_nodes / elapsed if elapsed > 0 else 0
                print(
                    f"[UCS] Nodes: {self.expanded_nodes:,}, "
                    f"Rate: {rate:.0f} n/s, "
                    f"Queue: {len(self.priority_queue):,}, "
                    f"Cost: {current_cost}, Depth: {depth}"
                )
                self._send_progress(current_state, depth)

            if current_state.is_goal():
                elapsed = time.time() - self.start_time
                path    = self._initial_auto_moves + self._reconstruct_path(current_hash)
                print(
                    f"[UCS] Solution found! Nodes: {self.expanded_nodes:,}, "
                    f"Time: {elapsed:.2f}s, Moves: {len(path)}, Cost: {current_cost}"
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

                # [1] Auto-move: gộp foundation moves bắt buộc vào cùng edge
                new_state, auto_moves_after = self._apply_auto_moves(
                    new_state, [move]
                )

                # [2] Canonical hash
                new_hash = self._canonical_hash(new_state)
                if new_hash in self.visited:
                    continue

                edge_cost = self._get_move_cost(move, current_state)
                new_cost  = current_cost + edge_cost

                if new_cost < self.cost_so_far.get(new_hash, float("inf")):
                    self.cost_so_far[new_hash] = new_cost
                    self.came_from[new_hash]   = (current_hash, auto_moves_after)
                    counter += 1
                    heapq.heappush(
                        self.priority_queue,
                        (new_cost, priority_idx, counter, new_state, move)
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
    """Kiểm tra move có hoàn tác trực tiếp last_move không."""
    mt, lmt = move[0], last_move[0]
    pairs = {
        ("cascade_to_freecell",  "freecell_to_cascade"),
        ("freecell_to_cascade",  "cascade_to_freecell"),
        ("cascade_to_cascade",   "cascade_to_cascade"),
    }
    if (mt, lmt) not in pairs:
        return False
    return (len(move) >= 3 and len(last_move) >= 3
            and move[1] == last_move[2] and move[2] == last_move[1])