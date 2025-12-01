# Prometeo: Your Local-First AI Chief of Staff ⚡️🧠

> **Privacy-First. Local Storage. Proactive Intelligence.**

Prometeo is a sophisticated **Multi-Agent System (MAS)** designed to act as your personal Chief of Staff. Unlike standard chatbots, Prometeo operates on a "Local-First" philosophy: it uses your local file system (Markdown files) as its database, ensuring that your financial logs, project plans, and personal notes remain yours.

Powered by **Google Gemini 1.5 Flash** and a robust **ReAct (Reasoning + Acting)** architecture, Prometeo doesn't just answer questions—it plans, executes, and manages your life through a WhatsApp interface.

---

## 🤖 The Squad (Architecture)

Prometeo is not a single bot; it's a team of specialized agents orchestrated by a central brain.

| Agent | Role | Function | Storage |
| :--- | :--- | :--- | :--- |
| **Nexus (Orchestrator)** | **The Boss** | Handles intent, multimodal input (Voice/Image), and manages the "Staff". Polyglot & Proactive. | `vault/Internal` |
| **The CFO (Finance)** | **Guardian of Wealth** | Tracks expenses, categorizes transactions, performs audits, and gives ruthless financial advice. | `vault/Finance` |
| **The PM (Projects)** | **The Planner** | turns vague ideas into concrete Work Breakdown Structures (WBS) and Weekly Sprints. | `vault/Projects` |
| **The Coach (Goals)** | **The Motivator** | Tracks habits, streaks, and ensures alignment with your 5-Year Vision. | `vault/Goals` |
| **The Librarian (Knowledge)** | **The Academic** | Organizes notes, tags content, researches topics, and generates study plans. | `vault/Notes` |

---

## 🛠️ Prerequisites

Before you start, ensure you have the following:

1.  **Python 3.10+** installed.
2.  **Twilio Account**: Required to set up the WhatsApp Sandbox (or a live number).
3.  **Google Gemini API Key**: Get one from [Google AI Studio](https://aistudio.google.com/) (Free tier works great).
4.  **Ngrok** (Optional but recommended): To expose your local server to Twilio's webhook.

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/FrankMdza/AiAssistant.git
cd AiAssistant
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory. You can copy the example:
```bash
cp .env.example .env
```

**Required Variables:**

| Variable | Description |
| :--- | :--- |
| `GOOGLE_API_KEY` | Your Google Gemini API Key. |
| `TWILIO_ACCOUNT_SID` | Found in your Twilio Console. |
| `TWILIO_AUTH_TOKEN` | Found in your Twilio Console. |
| `GEMINI_MODEL` | Recommended: `gemini-1.5-flash` (Stable) or `gemini-2.5-flash` (if available). |

### 5. Run the Server
```bash
uvicorn main:app --reload
```

Prometeo will start on `http://localhost:8000`. The **Self-Healing Vault** will automatically create the `vault/` folder structure on the first run.

---

## 📡 Connecting to WhatsApp

1.  Start **Ngrok** to tunnel your localhost:
    ```bash
    ngrok http 8000
    ```
2.  Copy the **HTTPS** forwarding URL (e.g., `https://a1b2c3d4.ngrok.io`).
3.  Go to your **Twilio Console** > Messaging > Settings > WhatsApp Sandbox Settings.
4.  Paste your URL into the **"When a message comes in"** field and append `/bot`.
    *   Example: `https://a1b2c3d4.ngrok.io/bot`
5.  Save.

---

## 💡 Usage Guide

### Phase 1: Tabula Rasa (Initialization)
When you first message Prometeo, it has no name and no memory of you.
1.  **User:** "Hello" or "Hola"
2.  **Prometeo:** "System Online. Identity pending. What would you like to call me?"
3.  **User:** "Jarvis" (or any name)
4.  **Prometeo:** "Identity established. I am Jarvis. I don't have a user profile. Could you introduce yourself?"

### Phase 2: Command Examples

**💰 Finance (The CFO)**
*   "Uber to airport 25000" *(Auto-categorizes as Transport)*
*   "Lunch with client 50 USD"
*   "How did we do this week?" *(Triggers Audit)*
*   "Delete the last transaction"

**🏗️ Projects (The PM)**
*   "I want to learn Python" *(Creates Project + WBS)*
*   "Plan my week for the Python project" *(Generates Weekly Sprint in Inbox)*
*   "Add to inbox: Call Mom tomorrow"

**🏃 Goals (The Coach)**
*   "I went to the gym" *(Logs Habit)*
*   "Morning briefing" *(Summary of Tasks, Finance, and Motivation)*
*   "This is my vision: I want to retire on a beach" *(Creates 5-Year Manifesto)*

**🧠 Knowledge (The Librarian)**
*   "Research Quantum Computing" *(Generates Academic Summary)*
*   "Create a study plan for Machine Learning"
*   "Take a note: The sky is blue because of Rayleigh scattering"

---

## 📂 Project Structure

```
prometeo/
├── agents/             # The Brains
│   ├── orchestrator.py # Nexus (Main Logic)
│   ├── finance.py      # CFO
│   ├── projects.py     # PM
│   ├── goals.py        # Coach
│   └── knowledge.py    # Librarian
├── vault/              # Your Data (Auto-generated)
│   ├── Inbox.md
│   ├── Finance/
│   ├── Projects/
│   ├── Goals/
│   └── Notes/
├── main.py             # FastAPI App & Webhook
├── config.py           # Settings Management
└── requirements.txt
```

---

## 📄 License

This project is licensed under the **GPLv3 License**. Free to use, modify, and share.

---

---
*Built with ❤️ by [FrankMdza](https://github.com/FrankMdza)*
