import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'freecell-solver-secret-key'

CORS(app, supports_credentials=True)

socketio = SocketIO(app, cors_allowed_origins="*")

games: Dict[str, Dict[str, Any]] = {}
solver_threads: Dict[str, Dict[str, Any]] = {}

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
@app.route('/api/new-game', methods=['POST'])
def new_game():      
    try:
        data = request.get_json() or {}
        seed = data.get('seed', 1)
        game_id = str(uuid.uuid4())
        
        seed_int = int(seed)
        state = FreeCellState(seed_int)
        
        games[game_id] = {
            'id': game_id,
            'state': state,
            'seed': seed_int,
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
    all_moves = state.get_all_moves(True)
    print("all moves",all_moves)
    if move_tuple not in all_moves:
        return jsonify({'success': False, 'error': 'Invalid move'}), 400
    
    new_state = state.apply_move(move_tuple)
    games[game_id]['state'] = new_state
    games[game_id]['move_count'] += 1
    
    is_goal = new_state.is_goal()
    
    socketio.emit('state_update', {
        'game_id': game_id,
        'state': state_to_dict(new_state),
        'last_move': move
    })
    
    response = {
        'success': True,
        'state': state_to_dict(new_state),
        'is_goal': is_goal
    }
    
    if is_goal:
        response['message'] = 'Congratulations! You won!'
    
    return jsonify(response)

@app.route('/api/game/<game_id>/restart', methods=['POST'])
def restart_game(game_id):
    if game_id not in games:
        return jsonify({'success': False, 'error': 'Game not found'}), 404
    
    game = games[game_id]
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
@app.route('/api/game/<game_id>/solve', methods=['POST'])
def solve_game(game_id):
    if game_id not in games:
        return jsonify({'success': False, 'error': 'Game not found'}), 404
    
    data = request.get_json()
    solver_name = data.get('solver', 'A*')
    
    game = games[game_id]
    state = game['state']

    thread_id = str(uuid.uuid4())
    
    def solve_in_background():
        try:
            print(f"Starting {solver_name} solver for game {game_id}")
            
            if solver_name == "BFS":
                solver = BFSSolver(state)
            elif solver_name == "DFS":
                solver = DFSSolver(state)
            elif solver_name == "UCS":
                solver = UCSSolver(state)
            else:
                solver = AStarSolver(state)
            solver.game_id = game_id 
            solver.socketio = socketio
            
            socketio.emit('solver_progress', {
                'game_id': game_id,
                'solver': solver_name,
                'progress': 0,
                'message': f'Starting {solver_name} search...'
            })
            
            results = solver.measure_performance()
            
            print(f"Solver {solver_name} completed for game {game_id}")
            
            socketio.emit('solver_complete', {
                'game_id': game_id,
                'solver': solver_name,
                'results': {
                    'nodes_explored': results['expanded_nodes'],
                    'time_taken': results['search_time'],
                    'memory_used': results['memory_usage'],
                    'solution_length': results['solution_length'],
                    'solution_found': results['found_solution']
                },
                'solution': [list(move) for move in solver.solution] if solver.solution else None
            })
        except Exception as e:
            print(f"Solver error: {e}")
            socketio.emit('solver_error', {
                'game_id': game_id,
                'error': str(e)
            })
        finally:
            if thread_id in solver_threads:
                del solver_threads[thread_id]
    
    thread = threading.Thread(target=solve_in_background)
    thread.daemon = True
    thread.start()
    
    solver_threads[thread_id] = {
        'thread': thread,
        'game_id': game_id,
        'solver': solver_name,
        'started_at': time.time()
    }
    
    return jsonify({
        'success': True,
        'message': f'Solver {solver_name} started'
    })
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