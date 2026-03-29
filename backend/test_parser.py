import json
import os
from backend.card import Card, Suit, Rank
from backend.game_state import FreeCellState

def load_tests_config():
    """Loads custom tests json file"""
    import os
    # Trỏ đúng đến file custom_tests.json với đường dẫn tuyệt đối tĩnh để app API cũng load được
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'tests', 'fixtures', 'custom_tests.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f).get('test_cases', [])
    except Exception as e:
        print(f"Error loading custom_tests.json: {e}")
        return []

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
    # Khi dùng custom test, seed là chuỗi string "Custom: ID" thay vì số nguyên ngẫu nhiên
    return state
