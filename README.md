# Jules API FastAPI Proxy

This project transforms Google's stateful, autonomous **Jules API** (a long-polling software engineering agent) into a high-throughput, stateless **OpenAI-compatible REST API** (`/v1/chat/completions`).

By acting as a proxy layer, this application allows you to use Jules as a standard Large Language Model (LLM) drop-in replacement for any tool, framework, or application that expects standard OpenAI JSON schemas.

## 🏗 Architectural Highlights

### 1. Repoless Execution & Jailbreaking
Jules is natively designed to clone GitHub repositories, generate PRs, and wait for human plan approval. This proxy tames that behavior by intentionally initiating a **repoless session** (omitting the `sourceContext` parameter). It injects a strict system "jailbreak" prompt that forces Jules to abandon its agentic tendencies and return raw JSON exclusively. 

### 2. Handling Eventual Consistency
Google's distributed infrastructure relies on eventual consistency. When a session is created via `POST /v1alpha/sessions`, it takes a moment to propagate to the `activities.list` datastore. This proxy is built to asynchronously catch the initial `404 Not Found` polling errors, gracefully back off, and retry until the session becomes available.

### 3. Stateless Chatbot Mechanics
Because Jules is operating in a repoless state without files to edit, he functions like a standard chatbot. The proxy intelligently detects the `agentMessaged` event in the activity log and immediately terminates the polling loop, extracting the text output and wrapping it in the standard OpenAI response schema.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- A valid Google API key with access to the Jules API (`jules.googleapis.com`)

### Installation

1. **Clone the repository and enter the directory:**
   ```bash
   git clone <repository_url>
   cd fastapi-jules-wrapper
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure your Environment:**
   Copy the example environment file and add your API key:
   ```bash
   cp .env.example .env
   # Edit .env and set JULES_API_KEY="your-api-key"
   export JULES_API_KEY="your-api-key"
   ```

---

## ⚡ Running the Proxy Server

Start the FastAPI application using Uvicorn. For production, you can increase the number of workers to handle more concurrent requests.

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

You should see the server start up successfully on `http://127.0.0.1:8000`.

---

## 🛠 Interacting with the API

You can interact with the proxy exactly as you would with the OpenAI API.

### Option 1: Using the Test Client
We have provided a built-in async Python test client to verify the connection and polling mechanics.

In a separate terminal, run:
```bash
python test_client.py
```
This will send a sample payload to the proxy, wait for Jules to process it, and print the raw JSON response along with the extracted text.

### Option 2: Using cURL
You can send a direct REST request to the proxy:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "jules-proxy-model",
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful assistant."
      },
      {
        "role": "user",
        "content": "Write a one sentence summary of what a proxy server does."
      }
    ],
    "temperature": 0.7
  }'
```

### Option 3: Integration with OpenAI SDKs
Because the API perfectly mimics the `/v1/chat/completions` schema, you can use the official OpenAI Python or Node.js SDKs by simply changing the `base_url`.

```python
from openai import OpenAI

client = OpenAI(
    api_key="dummy-key-not-needed",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="jules-proxy-model",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

## 📜 Logging and Debugging
If a request fails or times out, check the Uvicorn terminal output. The proxy logs the exact REST requests, `404` eventual-consistency retries, and the raw JSON of the `activities` array received from the Google API to help you debug.
