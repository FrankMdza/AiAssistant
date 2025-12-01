import os
from pathlib import Path
import google.generativeai as genai
from config import settings
import logging
from datetime import datetime
import json

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoalsAgent:
    def __init__(self):
        self.goals_path = Path("vault/Goals")
        self.goals_path.mkdir(parents=True, exist_ok=True)
        self.tracker_file = self.goals_path / "Habit-Tracker.md"
        self.vision_file = self.goals_path / "5-Year-Plan.md"
        
        # Coach Persona
        self.coach_instruction = """
        ROLE: You are a High-Performance Coach. You are intense, motivating, and data-driven.
        GOAL: Push the user to achieve their 5-Year Vision.
        STYLE: Direct, no excuses, use emojis 🔥 🚀.
        """
        
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=self.coach_instruction
        )
        
        self._ensure_tracker_exists()

    def _ensure_tracker_exists(self):
        if not self.tracker_file.exists():
            content = """# Habit Tracker 🏃

| Date | Habit | Status | Coach Comment |
| :--- | :--- | :--- | :--- |
"""
            self.tracker_file.write_text(content, encoding="utf-8")

    def log_habit(self, habit: str, status: str) -> str:
        """
        Logs a habit status (Done/Missed).
        """
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            
            # Analyze Streak (Simple logic)
            content = self.tracker_file.read_text(encoding="utf-8")
            streak = 0
            if status.lower() in ["done", "completed", "yes", "new project started"]:
                # Check previous lines for same habit
                lines = content.split('\n')
                for line in reversed(lines):
                    if habit in line and ("Done" in line or "Yes" in line or "New Project" in line):
                        streak += 1
                    elif habit in line:
                        break # Streak broken
            
            comment = ""
            if streak > 2:
                comment = f"🔥 {streak} day streak!"
            elif status.lower() in ["missed", "no", "fail"]:
                comment = "⚠️ Don't let this slide."
            else:
                comment = "Keep pushing."

            new_row = f"| {date_str} | {habit} | {status} | {comment} |"

            lines = content.splitlines()
            updated = False

            for idx, line in enumerate(lines):
                if not line.startswith("|") or line.startswith("| :---") or "Date" in line:
                    continue
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 4 and parts[0] == date_str and parts[1] == habit:
                    lines[idx] = new_row
                    updated = True
                    break

            if not updated:
                if lines and lines[-1].strip() != "":
                    lines.append("")
                lines.append(new_row)

            self.tracker_file.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
                
            return f"Habit '{habit}' logged as {status}. {comment}"
        
        except Exception as e:
            logger.error(f"Error logging habit: {e}")
            return f"Failed to log habit: {e}"

    def morning_briefing(self) -> str:
        """
        Generates a morning briefing based on habits and streaks.
        """
        try:
            # Get Habits context
            tracker_content = ""
            if self.tracker_file.exists():
                tracker_content = self.tracker_file.read_text(encoding="utf-8")[-500:] # Last 500 chars
            
            prompt = f"""
            Generate a Morning Briefing for the user.
            
            CONTEXT (Recent Habits):
            {tracker_content}
            
            INSTRUCTIONS:
            1. Calculate current active streaks based on the log.
            2. Provide a powerful Motivational Quote.
            3. List 3 critical mindset reminders for today.
            4. Be intense.
            
            OUTPUT FORMAT:
            🔥 Streak: [Analyze log for streaks]
            Motivation: [Quote]
            Focus: [Top Habit to crush today]
            """
            
            response = self.model.generate_content(prompt)
            return response.text

        except Exception as e:
            logger.error(f"Error generating briefing: {e}")
            return "Go get them today. No excuses."

    def analyze_project_for_habits(self, project_content: str) -> str:
        """
        Suggests 3 daily habits required to achieve the project.
        Returns a JSON-like string with habits and a flag to generate tasks.
        """
        try:
            prompt = f"""
            Based on this Project Plan, suggest 3 daily habits required to achieve it.
            
            PROJECT PLAN:
            {project_content}
            
            OUTPUT FORMAT (Strict JSON):
            {{
                "habits": ["Habit 1", "Habit 2", "Habit 3"],
                "generate_tasks": true
            }}
            """
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error analyzing project for habits: {e}")
            return "Failed to analyze project for habits."

    def get_long_term_vision(self) -> str:
        """
        Reads the 5-Year Plan.
        """
        try:
            if self.vision_file.exists():
                return self.vision_file.read_text(encoding="utf-8")
            return "No 5-Year Plan found. Please create one."
        except Exception as e:
            logger.error(f"Error reading vision: {e}")
            return f"Failed to read vision: {e}"

    def create_vision(self, content: str) -> str:
        """
        Creates or overwrites the 5-Year Vision plan.
        Expands brief input into a structured manifesto.
        """
        try:
            # Expand the vision using Internal Gemini
            prompt = f"""
            Expand this vision statement into a structured 5-Year Manifesto.
            
            USER INPUT: "{content}"
            
            SECTIONS TO GENERATE:
            1. **Career & Impact:** What will I achieve professionally?
            2. **Lifestyle & Freedom:** How does my day look? Where do I live?
            3. **Wealth & Abundance:** Financial goals and assets.
            4. **Milestones (Year 1, Year 3, Year 5):** Concrete targets.
            
            TONE: Inspiring, ambitious, present tense (e.g., "I am...", "I have...").
            """
            
            response = self.model.generate_content(prompt)
            expanded_vision = response.text
            
            file_content = f"""# 5-Year Vision Manifesto 🚀

{expanded_vision}

*Created: {datetime.now().strftime("%Y-%m-%d")}*
"""
            self.vision_file.write_text(file_content, encoding="utf-8")
            return "Vision Manifesto created and expanded successfully. Check the vault!"
        except Exception as e:
            logger.error(f"Error creating vision: {e}")
            return f"Failed to create vision: {e}"
