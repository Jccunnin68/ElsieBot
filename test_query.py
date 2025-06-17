import requests
import json
import sys

def run_test_query(query: str):
    """
    Sends a test query to the running AI agent.
    """
    url = "http://localhost:8000/process"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "message": query,
        "context": {
            "channel_name": "test-channel",
            "username": "test-user"
        },
        "conversation_history": []
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Raise an exception for bad status codes
        
        response_data = response.json()
        print("✅ Query successful!")
        print(json.dumps(response_data, indent=2))
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending request: {e}")
        # Attempt to print the response text even on error
        if e.response is not None:
            print(f"   Response Text: {e.response.text}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query_text = " ".join(sys.argv[1:])
        run_test_query(query_text)
    else:
        print("Usage: python test_query.py <your query>") 