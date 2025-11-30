import os
from pathlib import Path
import google.generativeai as genai
from config import settings
import logging
from datetime import datetime

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KnowledgeAgent:
    def __init__(self):
        self.notes_path = Path("vault/Notes")
        self.university_path = Path("vault/University")
        self.notes_path.mkdir(parents=True, exist_ok=True)
        self.university_path.mkdir(parents=True, exist_ok=True)

        # Librarian Persona
        self.librarian_instruction = """
        ROLE: You are the Head Librarian of the User's Second Brain. You are academic, rigorous, and obsessed with connecting ideas.
        GOAL: Organize knowledge, tag content intelligently, and build knowledge graphs.
        OUTPUT: Structured, enriched content.
        """
        
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=self.librarian_instruction
        )

    def save_smart_note(self, title: str, content: str) -> str:
        """
        Saves a note with AI-generated tags and links.
        """
        try:
            # Sanitize filename
            safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
            file_path = self.notes_path / f"{safe_title}.md"
            
            # AI Enrichment
            prompt = f"""
            Analyze this content for a smart note.
            CONTENT: {content}
            
            TASKS:
            1. Summarize it in 2 sentences.
            2. Generate 3 relevant #tags (lowercase).
            3. Suggest 2 WikiLinks to potential related concepts (e.g. [[Productivity]]).
            
            OUTPUT FORMAT:
            Summary: ...
            Tags: #tag1 #tag2
            Links: [[Link1]], [[Link2]]
            """
            
            response = self.model.generate_content(prompt)
            enrichment = response.text
            
            # Construct File
            file_content = f"""---
type: note
created: {datetime.now().strftime("%Y-%m-%d")}
tags: []
---

# {title}

{content}

## Librarian's Context 🧠
{enrichment}
"""
            file_path.write_text(file_content, encoding="utf-8")
            return f"Note '{title}' saved. Enriched with metadata."

        except Exception as e:
            logger.error(f"Error saving smart note: {e}")
            return f"Failed to save note: {e}"

    def research_topic(self, topic: str) -> str:
        """
        Generates an academic summary of a topic using internal knowledge.
        """
        try:
            prompt = f"""
            Conduct a mini-research session on: '{topic}'.
            Provide a structured academic summary including:
            - Key Definitions
            - Historical Context
            - Main Arguments/Theories
            - Critical Analysis
            """
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error researching topic: {e}")
            return f"Failed to research topic: {e}"

    def search_vault(self, query: str) -> str:
        """
        Searches the vault for snippets matching the query.
        """
        try:
            matches = []
            # Iterate through all MD files in vault
            vault_root = Path("vault")
            for file_path in vault_root.rglob("*.md"):
                if "Internal" in str(file_path): continue # Skip internal system files
                
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if query.lower() in content.lower():
                    # Extract a snippet
                    idx = content.lower().find(query.lower())
                    start = max(0, idx - 50)
                    end = min(len(content), idx + 100)
                    snippet = content[start:end].replace("\n", " ")
                    matches.append(f"- **{file_path.name}**: ...{snippet}...")
            
            if not matches:
                return f"No matches found for '{query}' in the Vault."
            
            return "Found these related notes:\n" + "\n".join(matches[:5])

        except Exception as e:
            logger.error(f"Error searching vault: {e}")
            return f"Failed to search vault: {e}"

    def create_study_plan(self, topic_or_project: str) -> str:
        """
        Creates a learning path/syllabus for a topic or project.
        """
        try:
            prompt = f"""
            Create a learning path/syllabus for: {topic_or_project}.
            
            INSTRUCTIONS:
            - Break it down into levels (Beginner, Intermediate, Advanced).
            - Suggest specific search terms for each level.
            - Suggest a structure for taking notes (e.g., specific sub-topics).
            """
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error creating study plan: {e}")
            return f"Failed to create study plan: {e}"
