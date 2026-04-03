import sys
import os
import json
import logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import uuid
import time
import threading
from typing import Dict, Any, Optional, Tuple, List
from game_state import FreeCellState
from card import Card, Suit, Rank
from solvers.bfs_solver import BFSSolver
from solvers.dfs_solver import DFSSolver
from solvers.ucs_solver import UCSSolver
from solvers.astar_solver import AStarSolver

from test_parser import create_state_from_json, load_tests_config

app = Flask(__name__)
app.config['SECRET_KEY'] = 'freecell-solver-secret-key'

CORS(app, supports_credentials=True)

socketio = SocketIO(app, cors_allowed_origins="*")

games: Dict[str, Dict[str, Any]] = {}
# solver_threads: Dict[str, Dict[str, Any]] = {}
active_solvers: Dict[str, Any] = {}

def save_games():
    """Lưu trạng thái các ván đấu vào file (Tránh mất khi restart server)"""
    try:
        # Nếu chưa muốn code phần lưu file, chỉ cần để pass
        # logger.info("Saving game sessions...")
        pass
    except Exception as e:
        logger.error(f"Failed to save games: {str(e)}")

def load_games():
    """Tải lại các ván đấu cũ khi khởi động server"""
    try:
        # Tương tự, nếu chưa cần hãy để pass
        pass
    except Exception as e:
        logger.error(f"Failed to load games: {str(e)}")

def card_to_dict(card: Optional[Card]) -> Optional[Dict]:
    """Convert Card object to dictionary"""
    if card is None:
        return None
    return {
        'suit': card.suit.name,
        'rank': card.rank.value,
        'display': str(card)
    }

def state_to_dict(state: FreeCellState) -> Dict:
    
    num_empty_free = state.get_empty_free_cells()
    num_empty_cascades = state.get_empty_cascades()
    
    max_to_filled = (1 + num_empty_free) * (2 ** num_empty_cascades)

    max_to_empty = (1 + num_empty_free) * (2 ** max(0, num_empty_cascades - 1))

    return {
        'cascades': [
            [card_to_dict(card) for card in cascade]
            for cascade in state.cascades
        ],
        'free_cells': [
            card_to_dict(cell) if cell else None for cell in state.free_cells
        ],
        'foundations': {
            suit.name: [card_to_dict(card) for card in pile]
            for suit, pile in state.foundations.items()
        },
        'move_history': [list(move) for move in state.move_history],
        
        'max_sequence_length': max_to_filled, 
        'max_sequence_to_empty': max_to_empty,
        
        'empty_free_cells': num_empty_free,
        'empty_cascades': num_empty_cascades,
        'seed': state.seed
    }
    
@app.route('/api/custom-tests', methods=['GET'])
def get_custom_tests():
    try:
        test_cases = load_tests_config()
        # Chỉ trả về metadata, giấu state_data cho nhẹ Payload
        metadata = []
        for tc in test_cases:
            metadata.append({
                'id': tc.get('id', 'unknown'),
                'category': tc.get('category', 'unknown'),
                'description': tc.get('description', '')
            })
        return jsonify({'success': True, 'tests': metadata})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/new-game', methods=['POST'])
def new_game():      
    try:
        data = request.get_json() or {}
        test_id = data.get('test_id')
        
        game_id = str(uuid.uuid4())
        
        if test_id:
            # Người dùng chọn Custom Test Map
            test_cases = load_tests_config()
            target_test = next((tc for tc in test_cases if tc.get('id') == test_id), None)
            
            if not target_test:
                return jsonify({'success': False, 'error': 'Cannot find test_id in custom_tests.json'}), 404
                
            state_data = target_test.get('state_data', {})
            state = create_state_from_json(state_data)
            origin_seed = target_test.get('origin_seed', test_id)
            seed_int = origin_seed
            state.seed = origin_seed
        else:
            # Người dùng chọn Random Microsoft Seed (giữ nguyên logic cũ)
            seed = data.get('seed', 1)
            seed_int = int(seed)
            state = FreeCellState(seed_int)
        
        games[game_id] = {
            'id': game_id,
            'state': state,
            'seed': seed_int,
            'test_id': test_id,
            'created_at': time.time(),
            'move_count': 0
        }
        
        print(f"Created new game: {game_id} with seed {seed_int}")
        
        return jsonify({
            'success': True,
            'game_id': game_id,
            'state': state_to_dict(state),
            'seed': seed_int
        })
        
    except ValueError as e:
        print(f"Error creating game: {e}")
        return jsonify({'success': False, 'error': 'Invalid seed'}), 400
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/game/<game_id>', methods=['GET'])
def get_game(game_id):
    if game_id not in games:
        return jsonify({'success': False, 'error': 'Game not found'}), 404
    
    game = games[game_id]
    return jsonify({
        'success': True,
        'state': state_to_dict(game['state']),
        'seed': game['seed']
    })

@app.route('/api/game/<game_id>/move', methods=['POST'])
def make_move(game_id):
    if game_id not in games:
        return jsonify({'success': False, 'error': 'Game not found'}), 404
    
    data = request.get_json()
    move = data.get('move')
    if not move:
        return jsonify({'success': False, 'error': 'No move provided'}), 400
    
    game = games[game_id]
    state = game['state']
    move_tuple = tuple(move)
    
    try:
        new_state = state.apply_move(move_tuple)
        
        if new_state is None:
            return jsonify({
                'success': False, 
                'error': 'Nước đi không hợp lệ! (Kiểm tra quy tắc khác màu, giảm dần)',
                'state': state_to_dict(state) 
            }), 400
            
        # if hasattr(new_state, 'auto_move_to_foundation'):
        #     new_state.auto_move_to_foundation()
            
        games[game_id]['state'] = new_state
        games[game_id]['move_count'] += 1
        
        is_goal = new_state.is_goal()
        socketio.emit('state_update', {
            'game_id': game_id,
            'state': state_to_dict(new_state),
            'last_move': move
        })
        
        return jsonify({
            'success': True,
            'state': state_to_dict(new_state),
            'is_goal': is_goal
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
# @app.route('/api/game/<game_id>/move', methods=['POST'])
# def make_move(game_id):
#     if game_id not in games:
#         return jsonify({'success': False, 'error': 'Game not found'}), 404
    
#     data = request.get_json()
#     move = data.get('move')
    
#     if not move:
#         return jsonify({'success': False, 'error': 'No move provided'}), 400
    
#     game = games[game_id]
#     state = game['state']
    
#     move_tuple = tuple(move)
#     # all_moves = state.get_all_moves(True)
    
#     # # KIỂM TRA 1: Nước đi có nằm trong danh sách hợp lệ không?
#     # if move_tuple not in all_moves:
#     #     print(f"Từ chối: Nước đi {move_tuple} không có trong danh sách hợp lệ.")
#     #     print(f"Gợi ý: Do game_state chỉ cho phép ném bài vào ô trống ĐẦU TIÊN (first_empty_free).")
#     #     return jsonify({'success': False, 'error': 'Invalid move'}), 400
    
#     try:
#         new_state = state.apply_move(move_tuple)
        
#         # KIỂM TRA 2: Chặn lỗi văng (500) nếu apply_move trả về None
#         if new_state is None:
#             return jsonify({
#                 'success': True, 
#                 'state': state_to_dict(state), 
#                 'message': 'Move rejected by rules'
#             })
            
#         # Cập nhật thành công
#         games[game_id]['state'] = new_state
#         games[game_id]['move_count'] += 1
        
#         is_goal = new_state.is_goal()
        
#         socketio.emit('state_update', {
#             'game_id': game_id,
#             'state': state_to_dict(new_state),
#             'last_move': move
#         })
        
#         response = {
#             'success': True,
#             'state': state_to_dict(new_state),
#             'is_goal': is_goal
#         }
        
#         if is_goal:
#             response['message'] = 'Congratulations! You won!'
        
#         return jsonify(response)
        
#     except Exception as e:
#         # KIỂM TRA 3: Bắt tận tay nếu code bị sập ở đâu đó
#         import traceback
#         print("CRITICAL ERROR trong lúc di chuyển:")
#         traceback.print_exc()
#         return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/game/<game_id>/restart', methods=['POST'])
def restart_game(game_id):
    if game_id not in games:
        return jsonify({'success': False, 'error': 'Game not found'}), 404
    
    game = games[game_id]
    test_id = game.get('test_id')

    if test_id:
        test_cases = load_tests_config()
        target_test = next((tc for tc in test_cases if tc.get('id') == test_id), None)
        if not target_test:
            return jsonify({'success': False, 'error': 'Custom test not found'}), 404

        new_state = create_state_from_json(target_test.get('state_data', {}))
        new_state.seed = target_test.get('origin_seed', game['seed'])
    else:
        new_state = FreeCellState(game['seed'])

    games[game_id]['state'] = new_state
    games[game_id]['move_count'] = 0
    
    socketio.emit('state_update', {
        'game_id': game_id,
        'state': state_to_dict(new_state)
    })
    
    return jsonify({
        'success': True,
        'state': state_to_dict(new_state)
    })

@app.route('/api/game/<game_id>/undo', methods=['POST'])
def undo_move(game_id):
    if game_id not in games:
        return jsonify({'success': False, 'error': 'Game not found'}), 404
    
    game = games[game_id]
    state = game['state']
    
    if not state.move_history:
        return jsonify({'success': False, 'error': 'No moves to undo'}), 400
    
    last_move = state.move_history[-1]
    success = undo_move_in_state(state, last_move)
    if not success:
        return jsonify({'success': False, 'error': 'Undo failed'}), 500
    games[game_id]['move_count'] = len(state.move_history)
    
    socketio.emit('state_update', {
        'game_id': game_id,
        'state': state_to_dict(state)
    })
    
    return jsonify({
        'success': True,
        'state': state_to_dict(state),
        'undone_move': list(last_move)
    })
def undo_move_in_state(state, last_move):
    move_type = last_move[0]
    
    try:
        if move_type == 'cascade_to_freecell':
            _, cascade_idx, free_cell_idx, card_data = last_move
            state.free_cells[free_cell_idx] = None
            card = Card(Suit[card_data['suit']], Rank(card_data['rank']))
            state.cascades[cascade_idx].append(card)
            
        elif move_type == 'freecell_to_cascade':
            _, free_cell_idx, cascade_idx, card_data = last_move
            state.cascades[cascade_idx].pop()
            card = Card(Suit[card_data['suit']], Rank(card_data['rank']))
            state.free_cells[free_cell_idx] = card
            
        elif move_type == 'cascade_to_cascade':
            _, src_idx, dest_idx, card_data = last_move
            card = Card(Suit[card_data['suit']], Rank(card_data['rank']))
            state.cascades[dest_idx].pop()
            state.cascades[src_idx].append(card)
            
        elif move_type == 'freecell_to_freecell':
            _, src_idx, dest_idx, card_data = last_move
            card = Card(Suit[card_data['suit']], Rank(card_data['rank']))
            state.free_cells[dest_idx] = None
            state.free_cells[src_idx] = card
            
        elif move_type == 'cascade_to_foundation':
            _, cascade_idx, card_data = last_move
            card = Card(Suit[card_data['suit']], Rank(card_data['rank']))
            state.foundations[card.suit].pop()
            state.cascades[cascade_idx].append(card)
            
        elif move_type == 'freecell_to_foundation':
            _, free_cell_idx, card_data = last_move
            card = Card(Suit[card_data['suit']], Rank(card_data['rank']))
            state.foundations[card.suit].pop()
            state.free_cells[free_cell_idx] = card
            
        elif move_type == 'cascade_to_cascade_sequence':
            _, src_idx, dest_idx, length, sequence_data = last_move
            sequence = [Card(Suit[c['suit']], Rank(c['rank'])) for c in sequence_data]
            state.cascades[src_idx].extend(sequence)
            state.cascades[dest_idx] = state.cascades[dest_idx][:-length]
        
        state.move_history.pop()
        return True
        
    except Exception as e:
        print(f"Undo error: {e}")
        return False
    
@app.route('/api/game/<game_id>/apply_solver_move', methods=['POST'])
def apply_solver_move(game_id):
    """API chuyên dụng: Áp dụng 1 bước của AI và trả về các frames (bước nhỏ) để diễn hoạt"""
    if game_id not in games:
        return jsonify({'success': False, 'error': 'Game not found'}), 404

    try:
        data = request.get_json()
        move = data.get('move')
        if move is None:
            return jsonify({'success': False, 'error': 'No move provided'}), 400

        game = games[game_id]
        state = game['state']
        move_tuple = tuple(move)
        
        steps = [] # Chứa các trạng thái trung gian

        # 1. Áp dụng nước đi chính
        new_state = state.apply_move(move_tuple)
        
        if new_state is None:
            # Ghost Move: Nếu nước đi này AI tính nhưng thực tế đã xong rồi (do auto_move trước đó)
            return jsonify({'success': True, 'steps': [state_to_dict(state)]})

        steps.append(state_to_dict(new_state))
        
        # 2. Tự động dọn bài TỪNG LÁ MỘT để tạo hiệu ứng "bay"
        curr = new_state
        while True:
            # Lấy tất cả nước đi có thể, chỉ lọc lấy nước đi lên móng (Foundation)
            possible_moves = curr.get_all_moves()
            auto_moves = [m for m in possible_moves if m[0] in ['cascade_to_foundation', 'freecell_to_foundation']]
            
            safe_auto_move = None
            for am in auto_moves:
                # Kiểm tra an toàn: Đảm bảo không bị bốc nhầm bài khi cột trống (tránh IndexError)
                idx = am[1]
                card_to_check = None
                if am[0] == 'cascade_to_foundation' and curr.cascades[idx]:
                    card_to_check = curr.cascades[idx][-1]
                elif am[0] == 'freecell_to_foundation' and curr.free_cells[idx]:
                    card_to_check = curr.free_cells[idx]
                
                if card_to_check and curr._is_safe_to_foundation(card_to_check):
                    safe_auto_move = am
                    break
            
            if not safe_auto_move:
                break
                
            curr = curr.apply_move(safe_auto_move)
            steps.append(state_to_dict(curr)) # Lưu lại frame bài đang bay

        # Lưu trạng thái cuối cùng vào RAM server
        games[game_id]['state'] = curr
        games[game_id]['move_count'] += 1
        save_games()

        return jsonify({
            'success': True,
            'steps': steps, 
            'is_goal': curr.is_goal()
        })
        
    except Exception as e:
        logger.error(f"Error in apply_solver_move: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/game/<game_id>/solve', methods=['POST'])
def solve_game(game_id):
    if game_id not in games:
        return jsonify({'success': False, 'error': 'Game not found'}), 404
    
    data = request.get_json()
    solver_name = data.get('solver', 'A*')
    
    # --- DỪNG SOLVER CŨ NẾU ĐANG CHẠY CHO GAME NÀY ---
    if game_id in active_solvers:
        active_solvers[game_id].cancelled = True
        print(f"Cancelling previous {solver_name} for game {game_id}")
    # -----------------------------------------------

    game = games[game_id]
    state = game['state']

    def solve_in_background():
        try:
            # Khởi tạo solver tương ứng
            if solver_name == "BFS": solver = BFSSolver(state)
            elif solver_name == "DFS": solver = DFSSolver(state)
            elif solver_name == "UCS": solver = UCSSolver(state)
            else: solver = AStarSolver(state)

            solver.game_id = game_id 
            solver.socketio = socketio
            
            # ĐƯA VÀO DANH SÁCH ĐANG CHẠY
            active_solvers[game_id] = solver

            # Kiểm tra xem bàn cờ đã thắng chưa NGAY LẬP TỨC
            if state.is_goal():
                is_solved = True
                explicit_path = []
            else:
                results = solver.measure_performance(node_limit = 2000000)
                # Dựa vào kết quả trả về của solve() chứ không dùng bool(path) vì path có thể rỗng (nếu đã thắng)
                is_solved = results.get('found_solution', False)
                explicit_path = getattr(solver, 'solution', [])
            
            # 2. MÔ PHỎNG LẠI ĐỂ LẤY FULL ĐƯỜNG ĐI (Gồm cả Auto-moves)
            full_solution = []
            is_truly_won = False
            if is_solved:
                import copy
                replay_state = copy.deepcopy(solver.initial_state)

                # CHÚ Ý: Lấy độ dài lịch sử TRƯỚC KHI dọn móng để bao gồm các nước auto-move đầu tiên vào solution
                old_history_len = len(getattr(replay_state, 'move_history', []))

                if hasattr(replay_state, 'auto_move_to_foundation'):
                    replay_state.auto_move_to_foundation()
                for move in explicit_path:
                    if replay_state is None:
                        break
                        
                    next_state = replay_state.apply_move(move)
                    
                    if next_state is None:
                        # Nếu AI cố đưa bài lên móng nhưng báo lỗi, tức là hàm auto_move 
                        # ở vòng lặp trước đã nhanh tay dọn nó lên móng giùm rồi! -> Bỏ qua an toàn.
                        if move[0] in ['cascade_to_foundation', 'freecell_to_foundation']:
                            continue
                        else:
                            print(f"⚠️ Cảnh báo: Nước đi {move} thực sự không hợp lệ!")
                            break
                            
                    replay_state = next_state
                    
                    if hasattr(replay_state, 'auto_move_to_foundation'):
                        replay_state.auto_move_to_foundation()
                
                if hasattr(replay_state, 'auto_move_to_foundation'):
                     replay_state.auto_move_to_foundation()

                is_truly_won = replay_state.is_goal() if replay_state else False

                if is_truly_won:
                    raw_full_solution = replay_state.move_history[old_history_len:]               
                    for m in raw_full_solution:
                        m_list = list(m)
                        # Nếu phần tử cuối cùng là một dict (card_data) HOẶC list (sequence_data), hãy CHẶT BỎ NÓ
                        if len(m_list) > 0 and isinstance(m_list[-1], (dict, list)):
                            clean_move = m_list[:-1]
                        else:
                            clean_move = m_list
                            
                        full_solution.append(clean_move)

            nodes = getattr(solver, 'expanded_nodes', 0)
            time_tk = getattr(solver, 'search_time', 0.0)
            mem = getattr(solver, 'memory_usage', 0.0)
            
            socketio.emit('solver_complete', {
                'game_id': game_id,
                'solver': solver_name,
                'results': {
                    'nodes_explored': nodes,
                    'time_taken': time_tk,
                    'memory_used': mem,
                    'solution_length': len(full_solution) if is_truly_won else 0,
                    'solution_found': is_truly_won
                },
                'solution': full_solution if is_truly_won else None
            })
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"💥 Solver Crash: {error_msg}")
            traceback.print_exc()
            # 🟢 GỬI LỖI VỀ FRONTEND ĐỂ KHÔNG BỊ TREO UI
            socketio.emit('solver_error', {'game_id': game_id, 'error': error_msg})
        finally:
            # DỌN DẸP KHI KẾT THÚC
            if game_id in active_solvers and active_solvers[game_id] == solver:
                del active_solvers[game_id]

    thread = threading.Thread(target=solve_in_background)
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'message': f'Solver {solver_name} started'})

@app.route('/api/game/<game_id>/valid-moves', methods=['GET'])
def get_valid_moves(game_id):
    if game_id not in games:
        return jsonify({'success': False, 'error': 'Game not found'}), 404
    
    game = games[game_id]
    moves = game['state'].get_all_moves()
    
    moves_list = []
    for move in moves:
        move_type = move[0]
        if move_type == 'cascade_to_cascade_sequence':
            moves_list.append({
                'type': move_type,
                'source': move[1],
                'destination': move[2],
                'length': move[3]
            })
        elif move_type in ['cascade_to_freecell', 'freecell_to_cascade', 
                          'cascade_to_cascade', 'freecell_to_freecell']:
            moves_list.append({
                'type': move_type,
                'source': move[1],
                'destination': move[2]
            })
        elif move_type in ['cascade_to_foundation', 'freecell_to_foundation']:
            moves_list.append({
                'type': move_type,
                'source': move[1]
            })
    
    return jsonify({
        'success': True,
        'moves': moves_list,
        'count': len(moves_list)
    })

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Aggregates all benchmark results from the tests/results/ directory."""
    # current_dir should be FreeCell-Solver/backend
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests', 'results')
    if not os.path.exists(results_dir):
        # Try parent dir just in case
        results_dir = os.path.join(os.getcwd(), 'backend', 'tests', 'results')
        if not os.path.exists(results_dir):
            return jsonify({'success': False, 'error': f'No results directory found at {results_dir}'}), 404

    all_data = []
    for filename in sorted(os.listdir(results_dir), reverse=True):
        if filename.startswith('run_') and filename.endswith('.json'):
            file_path = os.path.join(results_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_data.append(data)
                if len(all_data) >= 10: # Only look at last 10 runs for stats
                    break
            except Exception as e:
                print(f"Error reading {filename}: {e}")

    if not all_data:
        return jsonify({'success': False, 'error': 'No data found'}), 404

    try:
        # Aggregate stats
        stats = {} 
        recent_matches = []
        
        for run in all_data:
            run_timestamp = run.get('timestamp', 'Unknown')
            # Handle potential null for timeout_seconds
            timeout_val = run.get('timeout_seconds')
            if timeout_val is None:
                timeout_val = 60
                
            for t_case in run.get('runs', []):
                category = t_case.get('category', 'unknown')
                t_id = t_case.get('test_case_id', 'unknown')
                for res in t_case.get('results', []):
                    solver = res.get('solver', 'unknown')
                    status = res.get('status', 'unknown')
                    
                    # For History Table
                    s_time = res.get('search_time')
                    recent_matches.append({
                        'timestamp': run_timestamp,
                        'seed': t_id,
                        'solver': solver,
                        'status': status,
                        'category': category,
                        'solution_length': res.get('solution_length'),
                        'search_time': round(float(s_time), 3) if s_time is not None else None
                    })

                    if solver not in stats:
                        stats[solver] = {}
                    if category not in stats[solver]:
                        stats[solver][category] = {
                            'sum_time': 0.0, 
                            'sum_nodes': 0, 
                            'count': 0, 
                            'success_count': 0,
                            'sum_solution_length': 0,
                            'sum_memory': 0.0,
                        }
                    
                    s_cat = stats[solver][category]
                    s_cat['count'] += 1
                    if status == 'Finished':
                        s_cat['success_count'] += 1
                        s_cat['sum_time'] += float(res.get('search_time') or 0)
                        s_cat['sum_nodes'] += int(res.get('expanded_nodes') or 0)
                        s_cat['sum_solution_length'] += int(res.get('solution_length') or 0)
                        s_cat['sum_memory'] += float(res.get('memory_usage') or 0.0)
                    elif status == 'Timeout':
                        s_cat['sum_time'] += float(timeout_val)

        # Sort matches by timestamp descending, then by original order preserved from runs
        recent_matches.sort(key=lambda x: str(x.get('timestamp', '')), reverse=True)
        recent_matches = recent_matches[:100] # Increase limit to show more levels
        # Format for frontend
        formatted_stats = []
        for solver, categories in stats.items():
            solver_data = {'solver': solver, 'categories': []}
            for category, data in categories.items():
                avg_time = data['sum_time'] / data['count'] if data['count'] > 0 else 0
                # Chỉ tính trung bình các chỉ số trên các lần thành công (để tránh null/timeout làm lệch)
                avg_nodes = data['sum_nodes'] / data['success_count'] if data['success_count'] > 0 else 0
                avg_solution = data['sum_solution_length'] / data['success_count'] if data['success_count'] > 0 else 0
                avg_memory = data['sum_memory'] / data['success_count'] if data['success_count'] > 0 else 0
                
                success_rate = (data['success_count'] / data['count']) * 100 if data['count'] > 0 else 0
                
                solver_data['categories'].append({
                    'name': category,
                    'avg_time': round(float(avg_time), 3),
                    'avg_nodes': int(avg_nodes),
                    'avg_solution': round(float(avg_solution), 1),
                    'avg_memory': round(float(avg_memory), 2),
                    'success_rate': round(float(success_rate), 1),
                    'total_tests': data['count'],
                    'timeouts': data['count'] - data['success_count']
                })
            formatted_stats.append(solver_data)

        # Global overview
        total_games = sum(sum(c['total_tests'] for c in s['categories']) for s in formatted_stats)
        total_success = sum(sum(cat_raw['success_count'] for cat_raw in s_raw.values()) for s_raw in stats.values())
        win_rate = (total_success / total_games * 100) if total_games > 0 else 0
        total_sum_time = sum(sum(cat_raw['sum_time'] for cat_raw in s_raw.values()) for s_raw in stats.values())
        avg_solve_time = total_sum_time / total_games if total_games > 0 else 0

        return jsonify({
            'success': True,
            'statistics': formatted_stats,
            'overview': {
                'total_games': total_games,
                'win_rate': round(float(win_rate), 1),
                'avg_time': round(float(avg_solve_time), 2)
            },
            'recent_matches': recent_matches,
            'total_runs': len(all_data),
            'last_updated': all_data[0].get('timestamp') if all_data else None
        })
    except Exception as e:
        logger.error(f"Statistics aggregation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': f'Failed to aggregate statistics: {str(e)}'
        }), 500

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')

if __name__ == '__main__':
    print("=" * 50)
    print("Starting FreeCell Solver API Server...")
    print("=" * 50)
    print(f"Server running on http://localhost:5000")
    print(f"WebSocket available on ws://localhost:5000")
    print("=" * 50)
    
    socketio.run(app, 
                debug=True, 
                port=5000,
                host='localhost',
                allow_unsafe_werkzeug=True)
