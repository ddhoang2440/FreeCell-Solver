import requests
import json

def test_stats():
    try:
        res = requests.get("http://localhost:5000/api/statistics")
        if res.status_code == 200:
            data = res.json()
            print("Statistics API Success!")
            print(f"Total Games in Overview: {data['overview']['total_games']}")
            print(f"Num Solvers in Stats: {len(data['statistics'])}")
            for s in data['statistics']:
                print(f"Solver: {s['solver']}")
                for c in s['categories']:
                    print(f"  Level: {c['name']} | Avg Time: {c['avg_time']} | Avg Memory: {c.get('avg_memory')} | Timeouts: {c.get('timeouts')}")
        else:
            print(f"Error: {res.status_code}")
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    test_stats()
