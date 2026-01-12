import requests
import json

# --- Configuration ---
BASE_URL = "http://localhost:8000"
ANALYZE_ENDPOINT = "/stream/analyze"
EVALUATE_ENDPOINT = "/stream/evaluate"

# --- Test Data ---
analyze_payload = {
    "resume_text": "Experienced Python developer with a background in machine learning and data science.",
    "jd_text": "Seeking a Senior Python Developer with expertise in building scalable machine learning models."
}

evaluate_payload = {
    "question": "Describe your experience with containerization technologies.",
    "user_answer": "I have extensive experience with Docker and Kubernetes, including creating Dockerfiles, managing container orchestration with Kubernetes, and deploying microservices-based applications.",
    "resume_text": "Experienced Python developer with a background in machine learning and data science. Proficient in Docker and Kubernetes.",
    "jd_text": "Seeking a Senior Python Developer with expertise in building scalable machine learning models. Experience with Docker and Kubernetes is required."
}

# --- Helper Function ---
def test_streaming_endpoint(endpoint, payload, description):
    """
    Tests a streaming endpoint by sending a POST request and printing the response chunks.
    """
    url = f"{BASE_URL}{endpoint}"
    print(f"--- Testing: {description} ---")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        with requests.post(url, json=payload, stream=True) as response:
            if response.status_code == 200:
                print("\n--- Streaming Response ---")
                for chunk in response.iter_content(chunk_size=None):
                    if chunk:
                        print(chunk.decode('utf-8'), end="", flush=True)
                print("\n--- End of Stream ---")
            else:
                print(f"\nError: Received status code {response.status_code}")
                print(f"Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"\nAn error occurred: {e}")
    print("\n" + "="*50 + "\n")

# --- Run Tests ---
if __name__ == "__main__":
    print("Starting CareerPilot Streaming API Tests...")
    print("="*50 + "\n")

    # Test the /stream/analyze endpoint
    test_streaming_endpoint(ANALYZE_ENDPOINT, analyze_payload, "Resume and JD Analysis")

    # Test the /stream/evaluate endpoint
    test_streaming_endpoint(EVALUATE_ENDPOINT, evaluate_payload, "User Answer Evaluation")
