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

from backend.test_parser import create_state_from_json, load_tests_config

def run_solver_worker(solver_class, state, queue):
    """Worker chạy trong process riêng biệt để có thể force kill nếu timeout"""
    try:
        solver = solver_class(state)
        result = solver.measure_performance()
        queue.put((True, result))
    except Exception as e:
        queue.put((False, str(e)))

def run_benchmark(timeout=60):
    test_cases = load_tests_config()
    if not test_cases:
        print("Khong tim thay test case nao trong file.")
        return

    solvers = {
        'BFS': BFSSolver,
        'DFS': DFSSolver,
        'UCS': UCSSolver,
        'A*': AStarSolver
    }
    
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        
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
        print(f"{'Solver':<8} | {'Time (s)':<10} | {'Peak Mem (MB)':<14} | {'Nodes':<10} | {'Sol Len':<10}")
        print("-" * 74)
        
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
                        print(f"{solver_name:<8} | {res['search_time']:<10.3f} | {res['memory_usage']:<14.2f} | {res['expanded_nodes']:<10} | {res['solution_length']:<10}")
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
        writer.writerow(['Test_ID', 'Category', 'Solver', 'Status', 'Time(s)', 'Peak_Memory(MB)', 'Nodes', 'Solution_Length'])
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
