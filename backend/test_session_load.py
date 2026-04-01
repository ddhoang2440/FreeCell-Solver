import sys
import os
import json
import logging

# Thêm đường dẫn để import game_state, v.v.
sys.path.append(os.getcwd())

from game_state import FreeCellState
from card import Card, Suit, Rank
from app import dict_to_state, SESSION_FILE

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_load():
    print(f"Testing load from: {SESSION_FILE}")
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Loaded {len(data)} games from JSON.")
            for gid, gdata in data.items():
                print(f"Processing game: {gid}")
                state_data = gdata.get('state')
                if state_data:
                    try:
                        state = dict_to_state(state_data)
                        print(f"  Successfully reconstructed state for {gid}")
                    except Exception as e:
                        print(f"  ❌ Error reconstructing state for {gid}: {e}")
                else:
                    print(f"  ⚠️ No state data for {gid}")
    else:
        print("SESSION_FILE not found.")

if __name__ == "__main__":
    test_load()
