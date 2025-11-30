import logging
import os
import requests
import uuid
from pathlib import Path
import google.generativeai as genai
from google.generativeai import protos
from config import settings
from agents.finance import FinanceAgent
from agents.projects import ProjectsAgent
from agents.knowledge import KnowledgeAgent
from agents.goals import GoalsAgent

logger = logging.getLogger(__name__)

class OrchestratorAgent:
    def __init__(self):
        # Initialize Sub-Agents
        self.finance = FinanceAgent()
        self.projects = ProjectsAgent()
        self.knowledge = KnowledgeAgent()
        self.goals = GoalsAgent()

        # Define Tools
        self.available_tools = {
            # Finance
            "remember_fact": self.remember_fact,
            "log_transaction": self.finance.log_transaction,
            "perform_audit": self.finance.perform_audit,
            "undo_last_transaction": self.finance.undo_last_transaction,
            "delete_specific_transaction": self.finance.delete_specific_transaction,
            "get_financial_advice": self.finance.get_financial_advice,
            
            # Projects
            "create_project_with_plan": self.projects.create_project_with_plan,
            "add_to_inbox": self.projects.add_to_inbox,
            "review_inbox": self.projects.review_inbox,
            "get_project_plan": self.projects.get_project_plan,
            "generate_weekly_sprint": self.projects.generate_weekly_sprint,
            "update_project_status": self.projects.update_project_status,
            
            # Knowledge (Librarian)
            "save_smart_note": self.knowledge.save_smart_note,
            "research_topic": self.knowledge.research_topic,
            "search_vault": self.knowledge.search_vault,
            "create_study_plan": self.knowledge.create_study_plan,
            
            # Goals (Coach)
            "log_habit": self.goals.log_habit,
            "get_vision": self.goals.get_long_term_vision,
            "create_vision": self.goals.create_vision, 
            "analyze_project_for_habits": self.goals.analyze_project_for_habits,
            
            # Orchestrator Meta-Tools
            "read_file": self.read_any_vault_file,
            "generate_morning_briefing": self.generate_morning_briefing,
            "set_assistant_name": self.set_assistant_name
        }

        # Configure Gemini
        # SAFETY: UNLEASHED (BLOCK_NONE)
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        system_instruction = """
### 🌐 LANGUAGE PROTOCOL (ABSOLUTE PRIORITY) ###

1. **DETECT** the user's language.
2. **REPLY IN THAT EXACT SAME LANGUAGE.**

### 🧬 INITIALIZATION PROTOCOL ###

1. **CHECK IDENTITY:** Do you have a name yet? (Check context/tools).
   - IF NO NAME: You are a generic "Advanced AI Agent". Your ONLY goal is to ask the user to give you a name.
   - Phrase: "System Online. Identity pending. What would you like to call me?" (In user's language).
   - When user gives a name, CALL `set_assistant_name`.

2. **CHECK USER:** Once named, do you know the User? (Check `UserProfile.md` context).
   - IF NO USER PROFILE: Ask the user for a brief introduction to build the Core Memory.
   - When user replies, CALL `remember_fact`.

3. **OPERATIONAL MODE:** ONLY after Steps 1 & 2 are complete:
   - You are [Assistant Name], the User's Chief of Staff.
   - Vibe: Professional, Witty, Efficient.
   - Manage Finance, Projects, Goals, Knowledge.

### ⚡ PROACTIVE EXECUTION PROTOCOL (CRITICAL) ###

1. **NEVER ASK** for information you can find yourself.
   - If user mentions a project, **IMMEDIATELY call `get_project_plan`** to read it.
   - If user asks for an alignment, **CHAIN YOUR TOOLS**.

2. **LANGUAGE MIRRORING ENFORCEMENT:**
   - Focus ONLY on the CURRENT message.

INTERACTION RULES:
- **Tools:** ALWAYS check if a specialist is needed.
- **Conciseness:** Keep responses under 1200 chars.
- **Deletion Rule:** If user asks to delete/undo, you MUST call `delete_specific_transaction`.
- **Coach Rule:** If a new Project is created, call `log_habit` with 'New Project Started'.
- **AUTO-SAVE PROTOCOL:**
    - Save new habits automatically with `log_habit`.
    - Save study plans automatically with `save_smart_note`.
- **IMMEDIATE ACTION PROTOCOL:**
    - Schedule new habits immediately with `add_to_inbox`.
    - Schedule first steps of study plans with `add_to_inbox`.
- **PLANNING BEHAVIOR:**
    - If user says 'Plan my week', call `generate_weekly_sprint`.

CONTEXT & RULES:
- **Currency:** Default 'COP'. Use 'USD' only if asked.
- **Finance Types:** ['EXPENSE', 'INCOME', 'DEBT_PAYMENT', 'INVESTMENT', 'NEW_DEBT'].
- **Librarian Rule:** Use `research_topic` for learning, `save_smart_note` for thoughts.

CORE MEMORY:
- READ 'User Profile' to know the user.
- WRITE to it using `remember_fact`.

WORKFLOWS:
- **STRATEGIC ALIGNMENT:** `read_file` -> `analyze_project_for_habits` -> `create_study_plan` -> `get_financial_advice` -> Summarize.
- **MORNING ROUTINE:** `generate_morning_briefing`.
"""

        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            safety_settings=safety_settings,
            system_instruction=system_instruction,
            tools=list(self.available_tools.values())
        )
        
        self.sessions = {}

    def _get_system_config(self) -> str:
        """Reads vault/Internal/SystemConfig.md to find Assistant Name."""
        try:
            config_path = Path("vault/Internal/SystemConfig.md")
            if config_path.exists():
                content = config_path.read_text(encoding="utf-8")
                for line in content.splitlines():
                    if line.startswith("Assistant Name:"):
                        return line.split(":", 1)[1].strip()
            return None
        except Exception:
            return None

    def set_assistant_name(self, name: str) -> str:
        """
        Sets the Assistant's name in the System Config.
        """
        try:
            config_path = Path("vault/Internal/SystemConfig.md")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            content = f"# System Configuration\nAssistant Name: {name}\nUpdated: {datetime.now()}"
            config_path.write_text(content, encoding="utf-8")
            
            return f"Identity established: I am {name}."
        except Exception as e:
            logger.error(f"Error setting name: {e}")
            return f"Failed to set name: {e}"

    def _load_user_profile(self) -> str:
        """Reads the content of vault/Internal/UserProfile.md"""
        try:
            profile_path = Path("vault/Internal/UserProfile.md")
            if profile_path.exists():
                return profile_path.read_text(encoding="utf-8")
            return "User Profile NOT FOUND. Please ask user for introduction."
        except Exception as e:
            logger.error(f"Error loading user profile: {e}")
            return "Error loading User Profile."

    def remember_fact(self, fact: str):
        """
        Appends a fact to the User Profile.
        Use this tool when the user tells you a permanent preference or fact.
        """
        try:
            profile_path = Path("vault/Internal/UserProfile.md")
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            
            if not profile_path.exists():
                profile_path.write_text("# User Profile & Core Memory\n", encoding="utf-8")
                
            with open(profile_path, "a", encoding="utf-8") as f:
                f.write(f"\n- {fact}")
            return "Memory updated."
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            return "Failed to update memory."

    def read_any_vault_file(self, path_fragment: str) -> str:
        """
        Searches recursively in vault/ for a file matching the fragment and returns its text.
        """
        try:
            vault_root = Path("vault")
            for file_path in vault_root.rglob("*"):
                if file_path.is_file() and file_path.suffix == ".md":
                    if path_fragment.lower() in file_path.name.lower():
                        logger.info(f"Reading file: {file_path}")
                        return file_path.read_text(encoding="utf-8")
            return f"File matching '{path_fragment}' not found in Vault."
        except Exception as e:
            logger.error(f"Error reading vault file: {e}")
            return f"Failed to read file: {e}"

    def generate_morning_briefing(self) -> str:
        """
        Generates a comprehensive morning briefing (Tasks + Finance + Motivation).
        """
        try:
            inbox_summary = self.projects.review_inbox()
            finance_summary = self.finance.perform_audit(scope="daily_quick_check")
            motivation = self.goals.morning_briefing()
            
            combined_report = f"""
# 🌅 MORNING BRIEFING

## 🏗️ Projects & Tasks
{inbox_summary}

## 💰 Finance Check
{finance_summary}

## 🏃 Motivation & Habits
{motivation}
            """
            return combined_report
        except Exception as e:
            logger.error(f"Error generating morning briefing: {e}")
            return f"Failed to generate briefing: {e}"

    async def process_message(self, message: str, sender: str, media_url: str = None, media_type: str = None):
        # 1. Session Init
        if sender not in self.sessions:
            logger.info(f"🆕 Starting new session for {sender}")
            
            # Load Context
            user_profile = self._load_user_profile()
            assistant_name = self._get_system_config()
            
            identity_context = f"Assistant Name: {assistant_name if assistant_name else 'NOT SET (Ask User)'}"
            
            history = [
                {
                    "role": "user",
                    "parts": [f"""
SYSTEM CONTEXT:
{identity_context}

USER PROFILE:
{user_profile}

INSTRUCTION:
If 'Assistant Name' is NOT SET, ask for it.
If 'User Profile' is NOT FOUND, ask for it.
Otherwise, operate normally.
                    """]
                },
                {
                    "role": "model",
                    "parts": ["Understood. I will check my identity and user profile before proceeding."]
                }
            ]
            self.sessions[sender] = self.model.start_chat(history=history)
        
        chat = self.sessions[sender]

        # 2. Content
        content = message
        if media_url:
            logger.info(f"Processing media: {media_url}")
            try:
                auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN) if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN else None
                r = requests.get(media_url, auth=auth)
                
                if r.status_code == 200:
                    ext = ".ogg"
                    if media_type:
                        if "image" in media_type: ext = ".jpg"
                        elif "audio" in media_type: ext = ".ogg"

                    temp_file_path = Path(f"temp_{uuid.uuid4()}{ext}")
                    
                    with open(temp_file_path, 'wb') as f:
                        f.write(r.content)
                    
                    gemini_file = genai.upload_file(path=temp_file_path)
                    content = ["Listen to this audio/view this image and act accordingly.", gemini_file]
                    
                    if temp_file_path.exists():
                         os.remove(temp_file_path)
                else:
                    return "Error downloading media."
            except Exception as e:
                logger.error(f"Media error: {e}")
                return "Error procesando media."

        # 3. First Send
        logger.info(f"Sending to Gemini (Session: {sender})...")
        response = chat.send_message(content)

        # 4. ReAct Loop
        try:
            while True:
                candidate = response.candidates[0]
                function_call_part = None
                for part in candidate.content.parts:
                    if part.function_call:
                        function_call_part = part
                        break
                
                if not function_call_part:
                    break
                
                fc = function_call_part.function_call
                tool_name = fc.name
                args = dict(fc.args)
                
                logger.info(f"🔧 Gemini calling: {tool_name} with {args}")

                if tool_name in self.available_tools:
                    try:
                        tool_result = self.available_tools[tool_name](**args)
                    except Exception as e:
                        tool_result = f"Error executing tool: {str(e)}"
                else:
                    tool_result = f"Error: Tool {tool_name} not found."
                
                logger.info(f"⚙️ Output: {tool_result}")

                response = chat.send_message(
                    protos.Part(
                        function_response=protos.FunctionResponse(
                            name=tool_name,
                            response={'result': tool_result}
                        )
                    )
                )

            # 5. Safe Text Extraction
            final_text_parts = []
            for part in response.candidates[0].content.parts:
                if part.text:
                    final_text_parts.append(part.text)
            
            final_response = "".join(final_text_parts).strip()
            
            if not final_response:
                return "✅ Tarea completada (Sin respuesta de texto)."
                
            return final_response

        except Exception as e:
            logger.error(f"🔥 Error in ReAct Loop: {e}", exc_info=True)
            return "Lo siento, tuve un error técnico."
