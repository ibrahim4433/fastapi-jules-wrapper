import os
import json
import asyncio
import logging
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx

# Configure logging for production observability
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Core Jules API Configuration
JULES_API_BASE = "https://jules.googleapis.com/v1alpha"
JULES_API_KEY = os.environ.get("JULES_API_KEY")

if not JULES_API_KEY:
   logger.warning("JULES_API_KEY environment variable is not set. API calls will fail.")

# ==========================================
# Pydantic Models for OpenAI API Mimicry
# ==========================================

class Message(BaseModel):
   role: str
   content: str

class ChatCompletionRequest(BaseModel):
   model: str = Field(default="jules-proxy-model")
   messages: List[Message]
   temperature: Optional[float] = 1.0

class MessageResponse(BaseModel):
   role: str = "assistant"
   content: str

class Choice(BaseModel):
   index: int = 0
   message: MessageResponse
   finish_reason: str = "stop"

class ChatCompletionResponse(BaseModel):
   id: str
   object: str = "chat.completion"
   created: int
   model: str
   choices: List[Choice]

# ==========================================
# FastAPI Application Initialization
# ==========================================

app = FastAPI(
   title="Jules Stateless LLM Proxy",
   description="Transforms the stateful Jules Agent into a stateless OpenAI-compatible REST API.",
   version="1.0.0"
)

# Global Exception Handler for clean error propagation
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
   logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
   return JSONResponse(
       status_code=500,
       content={"error": {"message": "Internal Proxy Error", "type": "server_error", "details": str(exc)}}
   )

# ==========================================
# Core Orchestration Logic
# ==========================================

async def initiate_jules_session(client: httpx.AsyncClient, prompt_payload: str) -> str:
   """
   Initiates a repoless Jules session.
   Omitting 'sourceContext' forces the agent into an empty, dummy environment.
   """
   url = f"{JULES_API_BASE}/sessions"
   headers = {
       "Content-Type": "application/json",
       "x-goog-api-key": JULES_API_KEY
   }
   
   # Payload specifically omits automationMode and sets requirePlanApproval to False
   data = {
       "prompt": prompt_payload,
       "requirePlanApproval": False,
       "title": "Stateless Proxy Execution"
   }
   
   response = await client.post(url, headers=headers, json=data, timeout=15.0)
   
   if response.status_code != 200:
       logger.error(f"Failed to create Jules session. Status: {response.status_code}, Body: {response.text}")
       if response.status_code == 429 or "Quota exceeded" in response.text:
           raise HTTPException(status_code=429, detail="Jules API Quota Exceeded. Rate limit hit.")
       raise HTTPException(status_code=502, detail=f"Upstream Jules API Error: {response.text}")
       
   session_data = response.json()
   return session_data.get("id")

async def poll_jules_activities(client: httpx.AsyncClient, session_id: str) -> str:
   """
   Asynchronously polls the Jules session activities until a terminal state is reached.
   """
   # The session_id format from creation is typically "sessions/{id}"
   # Activities endpoint expects: /v1alpha/{session_id}/activities
   url = f"{JULES_API_BASE}/{session_id}/activities?pageSize=50"
   headers = {
       "x-goog-api-key": JULES_API_KEY
   }
   
   max_attempts = 120 # Polling limit (e.g., ~4 minutes maximum execution time)
   attempts = 0
   
   while attempts < max_attempts:
       attempts += 1
       response = await client.get(url, headers=headers, timeout=10.0)
       
       if response.status_code != 200:
           logger.error(f"Failed to poll activities. Status: {response.status_code}")
           raise HTTPException(status_code=502, detail="Failed to communicate with Jules API during polling.")
           
       activities_data = response.json()
       activities = activities_data.get("activities", [])
       
       is_completed = False
       final_output = ""
       
       # Parse activities chronologically to find terminal states
       for activity in activities:
           if "sessionFailed" in activity:
               logger.error(f"Session {session_id} failed.")
               raise HTTPException(status_code=500, detail="Jules Agent execution failed internally.")
               
           if "sessionCompleted" in activity:
               is_completed = True
               
           # Extract output payloads from the agent
           if activity.get("originator") == "agent":
               if "agentMessaged" in activity:
                   final_output = activity.get("description", final_output)
               elif "progressUpdated" in activity:
                   final_output = activity["progressUpdated"].get("description", final_output)
                   
       if is_completed:
           return final_output
           
       # Yield control back to the asyncio event loop
       await asyncio.sleep(2.0)
       
   raise HTTPException(status_code=504, detail="Proxy timeout: Jules Agent took too long to complete the task.")

def construct_strict_prompt(messages: List[Message]) -> str:
   """
   Flattens the OpenAI messages array into a single string and injects the overriding system prompt.
   """
   system_directive = (
       "CRITICAL SYSTEM OVERRIDE: You are currently operating as a stateless, localized LLM endpoint. "
       "You do not possess a workspace, you do not have access to GitHub, and you cannot execute files. "
       "Analyze the following conversation data, perform the requested task, and return the final output "
       "ONLY as a raw JSON string matching the standard output format. "
       "DO NOT create files. DO NOT make pull requests. DO NOT include conversational filler, greetings, "
       "or explanations. DO NOT wrap the output in markdown blocks (e.g., avoid ```json). "
       "Return the raw JSON payload exclusively.\n\n"
       "--- START CONVERSATION HISTORY ---\n"
   )
   
   conversation = ""
   for msg in messages:
       conversation += f"Role [{msg.role}]: {msg.content}\n\n"
       
   return system_directive + conversation + "--- END CONVERSATION HISTORY ---\nOUTPUT RAW JSON ONLY:"

# ==========================================
# API Endpoints
# ==========================================

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
   """
   The primary proxy endpoint. Mimics standard stateless LLM behavior.
   """
   if not JULES_API_KEY:
       raise HTTPException(status_code=500, detail="Server misconfiguration: Missing JULES_API_KEY")
       
   flattened_prompt = construct_strict_prompt(request.messages)
   
   async with httpx.AsyncClient() as client:
       session_id = await initiate_jules_session(client, flattened_prompt)
       logger.info(f"Successfully initiated repoless Jules Session: {session_id}")
       raw_output = await poll_jules_activities(client, session_id)
       
   # Output Sanitization
   sanitized_output = raw_output.strip()
   if sanitized_output.startswith("```json"):
       sanitized_output = sanitized_output[7:]
   if sanitized_output.startswith("```"):
       sanitized_output = sanitized_output[3:]
   if sanitized_output.endswith("```"):
       sanitized_output = sanitized_output[:-3]
   sanitized_output = sanitized_output.strip()

   # Construct the OpenAI-compatible response
   response = ChatCompletionResponse(
       id=f"chatcmpl-{session_id.split('/')[-1]}",
       created=int(time.time()),
       model=request.model,
       choices=[
           Choice(
               message=MessageResponse(content=sanitized_output)
           )
       ]
   )
   
   return response

if __name__ == "__main__":
   import uvicorn
   uvicorn.run(app, host="0.0.0.0", port=8000)
