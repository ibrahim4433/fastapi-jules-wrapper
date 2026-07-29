# Jules Stateless LLM Proxy

This project transforms the stateful Jules autonomous coding agent into a stateless, standard LLM API endpoint matching the OpenAI schema (`/v1/chat/completions`).

## Architectural Highlights

### Repoless Execution
By design, the Jules API is highly stateful and expects to work within GitHub repositories. To tame this behavior into a stateless text-in/text-out format, this proxy creates "repoless" sessions. It accomplishes this by intentionally omitting the `sourceContext` parameter when communicating with the Jules `/v1alpha/sessions` endpoint.
Additionally, `requirePlanApproval` is explicitly set to `false`, and `automationMode` is omitted, stripping the agent of its ability to stall for plan approval or attempt PR generation.

### Stateless API & Prompt Formatting
To mimic the standard API, the proxy intercepts the message array, flattens the history into a single string, and injects a "Jailbreak" pre-system prompt. This forces the model to ignore its agentic tendencies and return raw JSON exclusively. Finally, the proxy uses `httpx.AsyncClient` to asynchronously poll the `activities` endpoint for a terminal state and extracts the final text output.

## Run Instructions

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Environment Variables:**
   Copy `.env.example` to `.env` and configure your API key, or export it directly:
   ```bash
   export JULES_API_KEY="your-secure-restricted-key"
   ```

3. **Run the API server:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

You can now interact with the API as if it were a standard OpenAI endpoint at `http://localhost:8000/v1/chat/completions`.
