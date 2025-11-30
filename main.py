import os
import textwrap
import logging
from pathlib import Path
from fastapi import FastAPI, Form, Depends
from fastapi.responses import Response, PlainTextResponse
from typing import Optional
from pydantic import BaseModel
import google.generativeai as genai
from twilio.rest import Client
from config import settings
from agents.orchestrator import OrchestratorAgent

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Holistic Life Orchestrator")

def init_vault_structure():
    """
    Ensures the basic file structure exists for a Clone-and-Run experience.
    """
    vault_root = Path("vault")
    structure = [
        vault_root / "Inbox",
        vault_root / "Finance",
        vault_root / "Projects",
        vault_root / "Goals",
        vault_root / "Notes",
        vault_root / "University", # Added based on KnowledgeAgent
        vault_root / "Internal"
    ]

    logger.info("📁 Initializing Vault Structure...")
    
    if not vault_root.exists():
        vault_root.mkdir(parents=True, exist_ok=True)

    for folder in structure:
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"   - Created: {folder}")
            
    # Ensure essential files exist to prevent initial read errors
    inbox_file = vault_root / "Inbox.md"
    if not inbox_file.exists():
        inbox_file.write_text("# Inbox\n\n", encoding="utf-8")
        logger.info("   - Created: Inbox.md")

# Execute Initialization on Startup
init_vault_structure()

# Initialize Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY)

# Initialize Twilio Client
twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

# Initialize Orchestrator (AI Assistant)
# We initialize it here so it persists across requests (simple in-memory for now)
orchestrator = OrchestratorAgent()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "active",
        "model": settings.GEMINI_MODEL,
        "agent": "AI Assistant Online"
    }

@app.post("/bot")
async def bot_webhook(
    From: str = Form(...),
    To: str = Form(...), # The Twilio Sandbox Number
    Body: str = Form(None), # Body can be empty if it's just media
    MediaUrl0: Optional[str] = Form(None),
    MediaContentType0: Optional[str] = Form(None)
):
    """
    Twilio Webhook Endpoint.
    Receives 'From' (User's WhatsApp number), 'To' (Sandbox number), and 'Body'.
    Also handles MediaUrl0 (first attachment) if present.
    Sends response directly via Twilio API.
    """
    logger.info(f"Received message from {From} to {To}. Body: '{Body}', Media: {MediaUrl0}")

    # Delegate to Orchestrator
    # We pass None if Body is empty/None to ensure clarity, though process_message handles it.
    user_text = Body if Body else ""
    
    # Pass 'From' as the sender identifier for session management
    response_text = await orchestrator.process_message(
        message=user_text,
        sender=From,
        media_url=MediaUrl0,
        media_type=MediaContentType0
    )

    # Chunk the message safely to avoid WhatsApp 1600 char limit
    # Using 1200 to be safe with emojis and multi-byte chars
    chunks = textwrap.wrap(response_text, width=1200, replace_whitespace=False)
    
    for chunk in chunks:
        try:
            message = twilio_client.messages.create(
                from_=To,  # The Sandbox Number (received in request)
                to=From,   # The User's Number
                body=chunk
            )
            logger.info(f"📤 Sent Message SID: {message.sid}")
        except Exception as e:
            logger.error(f"❌ Error sending message: {e}")

    # Return simple OK as we've handled the response manually
    return "OK"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
