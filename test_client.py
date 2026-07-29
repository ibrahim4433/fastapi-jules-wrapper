import httpx
import asyncio
import json

async def test_proxy():
    url = "http://localhost:8000/v1/chat/completions"
    headers = {
        "Content-Type": "application/json"
    }
    
    # Standard OpenAI-style payload
    payload = {
        "model": "jules-proxy-model",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Write a very short poem about an API proxy."}
        ],
        "temperature": 0.7
    }

    print(f"Sending request to {url}...")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    # We use a long timeout because Jules might take a minute or two to process
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            print(f"\nStatus Code: {response.status_code}")
            
            if response.status_code == 200:
                print("\nRaw JSON Response:")
                response_json = response.json()
                print(json.dumps(response_json, indent=2))
                
                # Extract just the message content
                content = response_json['choices'][0]['message']['content']
                print("\nExtracted Assistant Message:")
                print("-" * 40)
                print(content)
                print("-" * 40)
            else:
                print(f"Error Response: {response.text}")
                
        except httpx.ConnectError:
            print("\nError: Could not connect to the server. Make sure the FastAPI app is running (uvicorn main:app --port 8000)")
        except httpx.ReadTimeout:
            print("\nError: The request timed out. Jules agent took too long to respond.")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    # Ensure the script is run in an async event loop
    asyncio.run(test_proxy())
