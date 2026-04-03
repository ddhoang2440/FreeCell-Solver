import sys
from test_parser import load_tests_config, create_state_from_json
from solvers.bfs_solver import BFSSolver
from solvers.dfs_solver import DFSSolver
from solvers.astar_solver import AStarSolver

def test_case(test_id):
    tests = load_tests_config()
    test_data = next((t for t in tests if t['id'] == test_id), None)
    if not test_data:
        print(f"Test {test_id} not found!")
        return

    state = create_state_from_json(test_data['state_data'])
    print(f"\n--- Testing {test_id} ---")
    print(f"Goal State: {state.is_goal()}")

    for name, solver_cls in [("BFS", BFSSolver), ("DFS", DFSSolver), ("A*", AStarSolver)]:
        solver = solver_cls(state)
        # BFS and DFS might need node_limit
        if name == "A*":
            solution = solver.solve(node_limit=1000)
        else:
            solution = solver.solve(node_limit=1000)
            
        found = solution is not None
        length = len(solution) if found else -1
        print(f"{name}: Found={found}, Length={length}")

if __name__ == "__main__":
    test_case("debug-is-goal")
    test_case("one-move-to-win")
