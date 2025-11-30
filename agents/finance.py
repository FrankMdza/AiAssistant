import os
from pathlib import Path
from datetime import datetime
import google.generativeai as genai
from config import settings
import logging
import re

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinanceAgent:
    def __init__(self):
        self.vault_path = Path("vault/Finance")
        self.vault_path.mkdir(parents=True, exist_ok=True)
        
        # CFO Persona for Audits
        self.audit_system_instruction = """
        ROLE: You are the CFO (Chief Financial Officer) of the User's life. Guardian of wealth.
        
        PRINCIPLES:
        1. **Smart Inference:** If user says "Uber to airport", log as Category="Transport", Description="Uber to Airport". Do not ask.
        2. **Ruthless Judgment:** If the expense is discretionary (coffee, gadgets), be critical. Calculate the opportunity cost.
        3. **Strategic View:** Always context-switch between the immediate expense and the Long-Term Goal.
        
        AUDIT PROTOCOLS (When asked for reports):
        - **Weekly:** Focus on Cash Flow (Income - Expenses). Did we burn money?
        - **Monthly:** Budget Variance. Identify leakages.
        - **Quarterly:** Net Worth & Strategy. Are we growing? Suggest asset allocation changes.
        
        OUTPUT FORMAT:
        Return a structured Markdown report with sections: 
        "## The Numbers", "## The Verdict", "## Action Plan".
        """
        
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=self.audit_system_instruction
        )

    def _get_current_month_file(self) -> Path:
        """Returns path to current month's log file, e.g., vault/Finance/2025-11-Finance.md"""
        current_month = datetime.now().strftime("%Y-%m")
        return self.vault_path / f"{current_month}-Finance.md"

    def _ensure_file_exists(self, file_path: Path):
        """Creates the daily log file with headers if it doesn't exist."""
        if not file_path.exists():
            header = """---
type: finance_log
status: active
created: {date}
---

# Financial Log: {month}

| Date | Type | Category | Description | Amount | Currency |
| :--- | :--- | :--- | :--- | :--- | :--- |
""".format(date=datetime.now().strftime("%Y-%m-%d"), month=datetime.now().strftime("%B %Y"))
            file_path.write_text(header, encoding="utf-8")

    def _parse_markdown_table(self, markdown_content: str) -> list[dict]:
        """
        Parses a Markdown table into a list of dictionaries.
        Assumes standard format: | Header1 | Header2 | ... |
        """
        rows = []
        lines = markdown_content.split('\n')
        headers = []
        
        for line in lines:
            line = line.strip()
            if not line or not line.startswith('|'):
                continue
            
            # Check if it's a header row
            if "Date" in line and not headers:
                headers = [h.strip() for h in line.split('|') if h.strip()]
                continue
                
            # Check if it's a separator row
            if ":---" in line:
                continue
                
            # Data row
            if headers:
                values = [v.strip() for v in line.split('|') if v.strip()]
                if len(values) == len(headers):
                    rows.append(dict(zip(headers, values)))
                    
        return rows

    def log_transaction(self, description: str, amount: float, type: str = "Expense", category: str = "General", currency: str = "USD") -> str:
        """
        Logs a financial transaction.
        If Category is 'General', tries to infer it from description.
        """
        try:
            file_path = self._get_current_month_file()
            self._ensure_file_exists(file_path)
            
            # Smart Inference for Category if 'General'
            if category == "General":
                desc_lower = description.lower()
                if any(x in desc_lower for x in ["uber", "taxi", "bus", "train", "gas"]): category = "Transport"
                elif any(x in desc_lower for x in ["food", "lunch", "dinner", "groceries", "market", "arepa"]): category = "Food"
                elif any(x in desc_lower for x in ["netflix", "spotify", "movie", "game"]): category = "Entertainment"
                elif any(x in desc_lower for x in ["salary", "freelance", "client"]): category = "Income"
            
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # Append to markdown table
            # Standard: | Date | Type | Category | Description | Amount | Currency |
            row = f"| {date_str} | {type} | {category} | {description} | {amount} | {currency} |\n"
            
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(row)
                
            return f"Transaction logged: {type} of {amount} {currency} for '{description}' ({category})."
            
        except Exception as e:
            logger.error(f"Error logging transaction: {e}")
            return f"Failed to log transaction: {e}"

    def perform_audit(self, scope: str = "weekly") -> str:
        """
        Performs a financial audit based on the scope (weekly/monthly/quarterly).
        Reads logs, parses them, and asks the CFO Brain for a report.
        """
        try:
            # 1. Read Data
            file_path = self._get_current_month_file()
            if not file_path.exists():
                return "No financial records found for this month to audit."
            
            raw_data = file_path.read_text(encoding="utf-8")
            
            # 2. Parse Data
            prompt = f"""
            Perform a **{scope.upper()} AUDIT** on the following financial log data.
            
            DATA:
            {raw_data}
            
            INSTRUCTIONS:
            - Analyze the spending patterns.
            - Calculate totals if not explicit.
            - Follow the 'AUDIT PROTOCOLS' for a {scope} review.
            - Be critical and strategic.
            """
            
            response = self.model.generate_content(prompt)
            return response.text

        except Exception as e:
            logger.error(f"Error performing audit: {e}")
            return f"Failed to perform audit: {e}"

    def delete_specific_transaction(self, criteria: str) -> str:
        """
        Smart Fuzzy Deletion: Removes a transaction matching criteria (amount or text).
        Deletes the MOST RECENT match if duplicates exist.
        """
        try:
            file_path = self._get_current_month_file()
            if not file_path.exists():
                return "No transaction file found for this month."
            
            lines = file_path.read_text(encoding="utf-8").splitlines()
            
            # Preprocessing Criteria
            clean_criteria = criteria.lower().replace("$", "").replace(",", "").replace("usd", "").replace("cop", "").strip()
            criteria_number = None
            # Extract potential number from criteria (e.g. "6000000" from "delete 6000000")
            try:
                # Find first sequence of digits/decimals
                match = re.search(r'\d+(\.\d+)?', clean_criteria)
                if match:
                    criteria_number = match.group(0)
            except:
                pass

            match_index = -1

            # Iterate to find LAST match (most recent)
            for i, line in enumerate(lines):
                # Skip headers/metadata
                if line.startswith("| Date") or line.startswith("| :---") or line.strip() == "" or line.startswith("#") or line.startswith("---") or line.startswith("type:"):
                    continue
                
                line_lower = line.lower()
                
                # Check 1: Exact Number Match
                if criteria_number and criteria_number in line_lower:
                    match_index = i
                # Check 2: Text Substring Match
                elif clean_criteria in line_lower:
                    match_index = i
            
            if match_index != -1:
                deleted_line = lines[match_index]
                del lines[match_index]
                
                # Write back
                file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                logger.info(f"Deleted transaction: {deleted_line}")
                return f"Successfully deleted transaction: {deleted_line}"
            else:
                return f"No matching transaction found for '{criteria}'."

        except Exception as e:
            logger.error(f"Error deleting transaction: {e}")
            return f"Failed to delete transaction: {e}"
            
    def undo_last_transaction(self) -> str:
        """
        Removes the very last transaction logged.
        """
        try:
            file_path = self._get_current_month_file()
            if not file_path.exists():
                return "No transaction file found."
            
            lines = file_path.read_text(encoding="utf-8").splitlines()
            
            # Find last data line
            for i in range(len(lines) - 1, -1, -1):
                line = lines[i]
                if line.strip() and line.startswith("|") and not line.startswith("| Date") and not line.startswith("| :---"):
                    deleted_line = lines.pop(i)
                    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    return f"Undid last transaction: {deleted_line}"
            
            return "No transactions found to undo."
            
        except Exception as e:
             logger.error(f"Error undoing transaction: {e}")
             return f"Failed to undo transaction: {e}"

    def get_financial_advice(self, question: str) -> str:
        """
        Asks the CFO for advice without a full audit.
        """
        try:
            # 1. Read Data (for context)
            file_path = self._get_current_month_file()
            context_data = ""
            if file_path.exists():
                context_data = file_path.read_text(encoding="utf-8")[-2000:] # Last 2000 chars for context

            prompt = f"""
            The user is asking for financial advice.
            
            USER QUESTION: "{question}"
            
            CONTEXT (Recent Transactions):
            {context_data}
            
            INSTRUCTIONS:
            - Answer as the strict CFO.
            - Check if the request aligns with recent spending.
            - Give a YES/NO recommendation with reasoning.
            """
            
            response = self.model.generate_content(prompt)
            return response.text

        except Exception as e:
            logger.error(f"Error getting financial advice: {e}")
            return f"Failed to get advice: {e}"
