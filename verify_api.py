import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_endpoint(endpoint):
    print(f"Testing {endpoint}...")
    try:
        response = requests.get(f"{BASE_URL}/{endpoint}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2)[:500] + "...")
        else:
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_endpoint("dashboard/leaderboard")
    test_endpoint("dashboard/stats")
    test_endpoint("dashboard/wrapped")
