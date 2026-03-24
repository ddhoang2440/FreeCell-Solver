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
    #  Move cost table                                                     #
    # ------------------------------------------------------------------ #
    _MOVE_COST: Dict[str, int] = {
        'cascade_to_foundation':        0,   # Always beneficial — free
        'freecell_to_foundation':       0,   # Always beneficial — free
        'cascade_to_cascade_sequence':  1,   # Moving a group is efficient
        'freecell_to_cascade':          2,   # Frees a free-cell slot
        'cascade_to_cascade':           3,   # Neutral single-card move
        'cascade_to_freecell':          5,   # Consumes a free-cell slot
    }

    # Move ordering priority (lower = explored first via sort)
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
    def _get_move_cost(self, move: Tuple) -> int:
        return self._MOVE_COST.get(move[0], 3)

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
    def solve(self, max_nodes: int = 150_000, max_time: int = 60) -> Optional[List[Tuple]]:
        """
        UCS search for a FreeCell solution.

        Args:
            max_nodes: Abort after expanding this many nodes (default 150 000).
            max_time:  Abort after this many seconds (default 60).

        Returns:
            List of moves leading to a solved board, or None if not found
            within the resource limits.
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

        print(f"[UCS] Starting search — limits: {max_nodes:,} nodes / {max_time}s")

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

                new_cost = current_cost + self._get_move_cost(move)

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