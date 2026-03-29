import os
import sys
import json
import csv
import time
import multiprocessing
from datetime import datetime

# Thêm đường dẫn project root vào sys.path để import dễ dàng
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
project_root = os.path.abspath(os.path.join(backend_dir, '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, backend_dir)

from backend.card import Card, Suit, Rank
from backend.game_state import FreeCellState
from backend.solvers.bfs_solver import BFSSolver
from backend.solvers.dfs_solver import DFSSolver
from backend.solvers.ucs_solver import UCSSolver
from backend.solvers.astar_solver import AStarSolver

def parse_card(s):
    if not s:
        return None
    suit_char = s[-1].upper()
    rank_str = s[:-1].upper()
    
    suit_map = {'S': Suit.SPADES, 'H': Suit.HEARTS, 'C': Suit.CLUBS, 'D': Suit.DIAMONDS}
    rank_map = {'A': Rank.ACE, '2': Rank.TWO, '3': Rank.THREE, '4': Rank.FOUR, 
                '5': Rank.FIVE, '6': Rank.SIX, '7': Rank.SEVEN, '8': Rank.EIGHT, 
                '9': Rank.NINE, '10': Rank.TEN, 'J': Rank.JACK, 'Q': Rank.QUEEN, 
                'K': Rank.KING}
                
    if suit_char not in suit_map or rank_str not in rank_map:
        raise ValueError(f"Khong the parse card: {s}")
        
    return Card(suit_map[suit_char], rank_map[rank_str])

def create_state_from_json(state_data):
    state = FreeCellState(seed=1) # Seed giả vì chúng ta sẽ overwrite dưới đây
    state.cascades = [[] for _ in range(8)]
    state.free_cells = [None] * 4
    state.foundations = {Suit.SPADES: [], Suit.HEARTS: [], Suit.CLUBS: [], Suit.DIAMONDS: []}
    
    # 1. Cascades
    for i, cascade in enumerate(state_data.get('cascades', [])):
        if i >= 8: break
        for card_str in cascade:
            state.cascades[i].append(parse_card(card_str))
            
    # 2. Free cells
    free_cells_data = state_data.get('free_cells', [])
    for i in range(4):
        if i < len(free_cells_data) and free_cells_data[i]:
            state.free_cells[i] = parse_card(free_cells_data[i])
            
    # 3. Foundations
    founds_data = state_data.get('foundations', {})
    suit_name_map = {'SPADES': Suit.SPADES, 'HEARTS': Suit.HEARTS, 'CLUBS': Suit.CLUBS, 'DIAMONDS': Suit.DIAMONDS}
    for suit_name, highest_rank in founds_data.items():
        suit = suit_name_map.get(suit_name.upper())
        if suit and highest_rank > 0:
            for val in range(1, highest_rank + 1):
                state.foundations[suit].append(Card(suit, Rank(val)))
                
    state._invalidate_cache()
    return state

def run_solver_worker(solver_class, state, queue):
    """Worker chạy trong process riêng biệt để có thể force kill nếu timeout"""
    try:
        solver = solver_class(state)
        result = solver.measure_performance()
        queue.put((True, result))
    except Exception as e:
        queue.put((False, str(e)))

def run_benchmark(timeout=60):
    fixtures_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'custom_tests.json')
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        
    with open(fixtures_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    test_cases = data.get('test_cases', [])
    if not test_cases:
        print("Khong tim thay test case nao trong file.")
        return

    solvers = {
        'BFS': BFSSolver,
        'DFS': DFSSolver,
        'UCS': UCSSolver,
        'A*': AStarSolver
    }
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file_path = os.path.join(results_dir, f'summary_{timestamp}.csv')
    json_file_path = os.path.join(results_dir, f'run_{timestamp}.json')
    
    all_results = []
    
    print("=" * 70)
    print("BAT DAU FREECELL SOLVER BENCHMARK")
    print(f"Tong so test case: {len(test_cases)}")
    print("=" * 70)

    for tc in test_cases:
        tc_id = tc.get('id', 'unknown')
        tc_cat = tc.get('category', 'unknown')
        print(f"\n======================================================================")
        print(f"Test Case: {tc_id} | Category: {tc_cat}")
        print(f"Desc: {tc.get('description', '')}")
        print(f"======================================================================")
        print(f"{'Solver':<8} | {'Time (s)':<10} | {'Mem (MB)':<10} | {'Nodes':<10} | {'Sol Len':<10}")
        print("-" * 70)
        
        state_data = tc.get('state_data', {})
        state = create_state_from_json(state_data)
        
        tc_results = []
        
        for solver_name, solver_class in solvers.items():
            queue = multiprocessing.Queue()
            process = multiprocessing.Process(
                target=run_solver_worker, 
                args=(solver_class, state, queue)
            )
            process.start()
            
            # Chờ để process thực thi hoặc báo timeout
            process.join(timeout)
            
            if process.is_alive():
                process.terminate()
                process.join()  # Clear process state
                print(f"{solver_name:<8} | {'[TIMEOUT] (> '+str(timeout)+'s)':<47}")
                res_dict = {
                    'solver': solver_name,
                    'status': 'Timeout',
                    'search_time': timeout,
                    'memory_usage': None,
                    'expanded_nodes': None,
                    'solution_length': None
                }
            else:
                if not queue.empty():
                    success, data = queue.get()
                    if success:
                        res = data
                        print(f"{solver_name:<8} | {res['search_time']:<10.3f} | {res['memory_usage']:<10.2f} | {res['expanded_nodes']:<10} | {res['solution_length']:<10}")
                        res_dict = {
                            'solver': solver_name,
                            'status': 'Finished',
                            'search_time': res['search_time'],
                            'memory_usage': res['memory_usage'],
                            'expanded_nodes': res['expanded_nodes'],
                            'solution_length': res['solution_length']
                        }
                    else:
                        print(f"{solver_name:<8} | [ERROR: {data}]")
                        res_dict = {
                            'solver': solver_name,
                            'status': 'Error',
                            'error': data
                        }
                else:
                    print(f"{solver_name:<8} | [UNKNOWN ERROR]")
                    res_dict = {
                        'solver': solver_name,
                        'status': 'Error',
                        'error': 'Queue empty'
                    }
            
            tc_results.append(res_dict)
            
        all_results.append({
            'test_case_id': tc_id,
            'category': tc_cat,
            'results': tc_results
        })

    # Ghi nhận log CSV
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Test_ID', 'Category', 'Solver', 'Status', 'Time(s)', 'Memory(MB)', 'Nodes', 'Solution_Length'])
        for tc_dict in all_results:
            for r in tc_dict['results']:
                writer.writerow([
                    tc_dict['test_case_id'], tc_dict['category'], r['solver'],
                    r['status'], r.get('search_time', ''), r.get('memory_usage', ''),
                    r.get('expanded_nodes', ''), r.get('solution_length', '')
                ])
                
    # Ghi file JSON
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump({'timestamp': timestamp, 'timeout_seconds': timeout, 'runs': all_results}, f, indent=2)

    print("=" * 70)
    print(f"Xuat bao cao CSV: {csv_file_path}")
    print(f"Xuat json log   : {json_file_path}")
    print("=" * 70)

if __name__ == '__main__':
    # Hạn chế cấp multiprocessing spawn trên Windows phải bọc trong main
    run_benchmark(timeout=60)
