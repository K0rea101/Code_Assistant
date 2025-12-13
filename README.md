# 🚀 Code Assistant IDE

A modern, web-based Code IDE with an integrated AI Assistant powered by LangGraph and OpenRouter. Features include intelligent code completion (Copilot-style), AI chat assistance, and real-time code execution for Python and JavaScript.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Node.js](https://img.shields.io/badge/node.js-20+-green.svg)

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Installation](#-installation)
- [Usage](#-usage)
- [API Reference](#-api-reference)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [Docker Deployment](#-docker-deployment)
- [Contributing](#-contributing)

---

## ✨ Features

### 🤖 AI-Powered Code Completion (Copilot-Style)
- **Inline suggestions**: Ghost text appears as you type
- **Smart triggering**: 500ms debounce to avoid excessive API calls
- **Context-aware**: Sends full file content and cursor position to AI
- **Accept with Tab**: Press `Tab` to accept, `Escape` to dismiss
- **Confidence filtering**: Only shows suggestions above 20% confidence threshold

### 💬 AI Chat Assistant
- **Conversational AI**: Ask questions about coding, debugging, explanations
- **Code context awareness**: Automatically includes your current code in context
- **Markdown rendering**: Responses rendered with syntax highlighting
- **Session management**: Conversation history preserved per session
- **Copy code blocks**: One-click copy for code snippets in responses

### ▶️ Code Execution
- **Python & JavaScript**: Execute code directly in the browser
- **Real-time output**: See stdout, stderr, and exit codes
- **Timeout protection**: 10-second limit prevents infinite loops
- **Error handling**: Friendly messages for common issues
- **No input() support**: Warns users about interactive scripts

### 📝 Code Editor
- **CodeMirror 6**: Modern, extensible editor framework
- **Syntax highlighting**: Python and JavaScript support
- **Dark/Light themes**: Toggle between Dracula dark and light mode
- **Line numbers**: Full gutter with line numbers
- **Bracket matching**: Automatic bracket/parenthesis matching
- **Search & replace**: Built-in search functionality
- **Keyboard shortcuts**: `Ctrl+S` to save, standard editor commands

### 💾 File Operations
- **New document**: Clear editor for fresh start
- **Open file**: Load `.py` or `.js` files from disk
- **Save file**: Download current content with appropriate extension
- **Auto language detection**: Detects language from file extension

### 📊 Status Bar
- **Line count**: Total lines in document
- **Character count**: Total characters
- **Cursor position**: Current line and column
- **Language indicator**: Shows active language mode

### 🔧 Resizable Chat Panel
- **Drag to resize**: Adjust chat sidebar width (250-600px)
- **Collapsible**: Toggle visibility with button
- **Responsive**: Full-screen on mobile devices

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                   │
│  ┌─────────────────────────┐    ┌─────────────────────────────────┐ │
│  │     CodeMirror 6        │    │       AI Chat Sidebar           │ │
│  │     Code Editor         │    │                                 │ │
│  │                         │    │  • Markdown rendering           │ │
│  │  • Syntax highlighting  │    │  • Code syntax highlighting     │ │
│  │  • AI ghost completions │    │  • Copy code blocks             │ │
│  │  • Theme switching      │    │  • Typing indicators            │ │
│  └───────────┬─────────────┘    └───────────────┬─────────────────┘ │
│              │                                   │                   │
│              │  HTTP REST API                    │                   │
└──────────────┼───────────────────────────────────┼───────────────────┘
               │                                   │
               ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         BACKEND (Flask)                              │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │ /api/complete│  │  /api/chat   │  │      /api/run            │   │
│  │              │  │              │  │                          │   │
│  │ Completion   │  │  LangGraph   │  │  subprocess execution    │   │
│  │ Service      │  │  Assistant   │  │  Python / Node.js        │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────────┘   │
│         │                 │                                          │
│         └────────┬────────┘                                          │
│                  ▼                                                   │
│         ┌───────────────┐                                            │
│         │  OpenRouter   │                                            │
│         │     API       │                                            │
│         └───────────────┘                                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🛠 Tech Stack

### Frontend
| Technology | Purpose |
|------------|---------|
| **CodeMirror 6** | Code editor framework |
| **Rollup** | Module bundler |
| **marked.js** | Markdown parsing |
| **highlight.js** | Syntax highlighting in chat |
| **Vanilla JS** | No framework dependencies |

### Backend
| Technology | Purpose |
|------------|---------|
| **Flask** | Web framework |
| **Flask-CORS** | Cross-origin resource sharing |
| **LangGraph** | AI agent orchestration |
| **OpenRouter** | LLM API gateway |
| **python-dotenv** | Environment management |

---

## 📦 Installation

### Prerequisites
- Python 3.11+
- Node.js 20+
- npm or yarn
- OpenRouter API key

### 1. Clone the Repository
```bash
git clone https://github.com/K0rea101/Code_Assistant.git
cd Code_Assistant
```

### 2. Backend Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "OPENROUTER_API_KEY=your_api_key_here" > .env
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Build the bundle
npm run build

cd ..
```

### 4. Run the Application
```bash
# Terminal 1: Start backend
python app.py

# Terminal 2: Start frontend (optional - can use backend to serve)
cd frontend && npm start
```

### 5. Access the Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000

---

## 🎮 Usage

### Code Completion
1. Start typing code in the editor
2. Wait ~500ms after stopping
3. Ghost text appears with AI suggestion
4. Press `Tab` to accept or `Escape` to dismiss

### AI Chat
1. Click the chat input at bottom of sidebar
2. Type your question (e.g., "How do I sort a list in Python?")
3. Press `Enter` or click `Send`
4. View response with syntax-highlighted code blocks
5. Click `📋 Copy` to copy code snippets

### Running Code
1. Write Python or JavaScript code
2. Click `▶️ Run` button
3. View output in the panel that appears
4. Click `✕` to close output panel

### File Operations
- **📄 New**: Clear the editor
- **📂 Open**: Load a file from your computer
- **💾 Save**: Download current file
- **Language dropdown**: Switch between Python/JavaScript

### Theme Toggle
- Click `☀️ Light` / `🌙 Dark` to toggle theme

---

## 📡 API Reference

### `POST /api/chat`
AI chat assistant endpoint.

**Request:**
```json
{
  "user_input": "How do I reverse a string in Python?",
  "uploaded_files": [],
  "conversation_history": [],
  "session_id": "default"
}
```

**Response:**
```json
{
  "intent": "code_help",
  "generated_response": "To reverse a string in Python...",
  "conversation_history": [...]
}
```

### `POST /api/complete`
Code completion endpoint.

**Request:**
```json
{
  "content": "def hello(",
  "cursor_position": 10,
  "language": "python",
  "last_char": "("
}
```

**Response:**
```json
{
  "completion": "name):\n    return f'Hello, {name}!'",
  "confidence": 0.85,
  "triggered": true,
  "trigger_reason": "After opening parenthesis"
}
```

### `POST /api/run`
Execute code endpoint.

**Request:**
```json
{
  "code": "print('Hello, World!')",
  "language": "python"
}
```

**Response:**
```json
{
  "stdout": "Hello, World!\n",
  "stderr": "",
  "exit_code": 0,
  "error": null
}
```

### `GET /api/sessions`
List all active sessions.

### `GET /api/sessions/<session_id>`
Get session details and history.

### `DELETE /api/sessions/<session_id>`
Delete a session.

### `POST /api/sessions/<session_id>/clear`
Clear conversation history for a session.

---

## 📁 Project Structure

```
Code_Assistant/
├── app.py                    # Flask backend entry point
├── routing.py                # LangGraph AI assistant logic
├── completion_service.py     # AI code completion service
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (create this)
├── docker-compose.yml        # Docker orchestration
├── Dockerfile.backend        # Backend container
├── README.md                 # This file
│
└── frontend/
    ├── index.html            # Main HTML page
    ├── styles.css            # All CSS styles
    ├── chat.js               # AI chat sidebar logic
    ├── package.json          # Node.js dependencies
    ├── rollup.config.js      # Bundler configuration
    ├── Dockerfile.frontend   # Frontend container
    │
    ├── src/
    │   └── editor.js         # CodeMirror editor + AI completion
    │
    └── dist/
        └── editor.bundle.js  # Compiled bundle (generated)
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Required: OpenRouter API key for AI features
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Optional: Server configuration
PORT=8000
FLASK_DEBUG=true
```

### Frontend Configuration

Edit `frontend/src/editor.js` for completion settings:
```javascript
const COMPLETION_DELAY_MS = 500;        // Debounce delay
const COMPLETION_MIN_CONFIDENCE = 0.2;  // Minimum confidence threshold
const MIN_CHARS_FOR_COMPLETION = 3;     // Minimum content length
```

Edit `frontend/chat.js` for API endpoint:
```javascript
const API_CONFIG = {
  endpoint: 'http://localhost:8000/api/chat'
};
```

---

## 🐳 Docker Deployment

### Quick Start with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Access Points
| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |

### Individual Container Commands

```bash
# Build backend only
docker build -f Dockerfile.backend -t code-ide-backend .

# Build frontend only
docker build -f frontend/Dockerfile.frontend -t code-ide-frontend ./frontend

# Run backend
docker run -p 8000:8000 --env-file .env code-ide-backend

# Run frontend
docker run -p 5173:5173 code-ide-frontend
```

---

## 🔑 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Tab` | Accept AI completion |
| `Escape` | Dismiss AI completion |
| `Ctrl+S` / `Cmd+S` | Save document |
| `Ctrl+F` / `Cmd+F` | Find in document |
| `Ctrl+Z` / `Cmd+Z` | Undo |
| `Ctrl+Shift+Z` / `Cmd+Shift+Z` | Redo |
| `Enter` (in chat) | Send message |
| `Shift+Enter` (in chat) | New line in message |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [CodeMirror](https://codemirror.net/) - The excellent code editor framework
- [OpenRouter](https://openrouter.ai/) - LLM API gateway
- [LangGraph](https://langchain-ai.github.io/langgraph/) - AI agent orchestration
- [highlight.js](https://highlightjs.org/) - Syntax highlighting
- [marked](https://marked.js.org/) - Markdown parser

---

<p align="center">
  Made with ❤️ by <span>بلدية المحلة</span>
</p>
