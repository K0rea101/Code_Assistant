"""
Flask Backend for Code IDE with AI Assistant
Provides REST API endpoints for the frontend to communicate with the LangGraph code assistant.
"""

import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for frontend communication
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:*"],
        "methods": ["GET", "POST", "OPTIONS", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Check for API key before initializing assistant
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
assistant = None

if OPENROUTER_API_KEY and OPENROUTER_API_KEY != "your_openrouter_api_key_here":
    try:
        from routing import LangGraphCodeAssistant
        assistant = LangGraphCodeAssistant()
        print("✅ AI Assistant initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize AI Assistant: {e}")
        assistant = None
else:
    print("⚠️  OPENROUTER_API_KEY not configured. AI features will be disabled.")
    print("   Create a .env file with: OPENROUTER_API_KEY=your_key_here")

# In-memory session storage for conversation history
sessions = {}


def get_session(session_id: str) -> dict:
    """Get or create a session for storing conversation history."""
    if session_id not in sessions:
        sessions[session_id] = {
            "conversation_history": [],
            "created_at": datetime.now().isoformat()
        }
    return sessions[session_id]


@app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "message": "Code IDE Backend is running",
        "version": "1.0.0"
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint for AI assistant interactions.
    
    Request body:
    {
        "user_input": "string",
        "uploaded_files": [{"filename": "string", "text": "string"}],
        "conversation_history": [...],
        "session_id": "string" (optional)
    }
    
    Response:
    {
        "intent": "string",
        "generated_response": "string",
        "conversation_history": [...]
    }
    """
    # Check if assistant is available
    if assistant is None:
        return jsonify({
            "error": "AI Assistant not configured. Please set OPENROUTER_API_KEY in .env file.",
            "intent": "error",
            "generated_response": "⚠️ The AI assistant is not configured. Please add your OpenRouter API key to the .env file and restart the server.",
            "conversation_history": []
        }), 503
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        user_input = data.get("user_input", "")
        if not user_input.strip():
            return jsonify({"error": "user_input is required"}), 400
        
        uploaded_files = data.get("uploaded_files", [])
        session_id = data.get("session_id", "default")
        
        # Get conversation history from request or session
        conversation_history = data.get("conversation_history")
        if conversation_history is None:
            session = get_session(session_id)
            conversation_history = session["conversation_history"]
        
        # Process the request through the AI assistant
        result = assistant.process(
            user_input=user_input,
            uploaded_files=uploaded_files,
            conversation_history=conversation_history
        )
        
        # Update session with new conversation history
        session = get_session(session_id)
        session["conversation_history"] = result.get("conversation_history", [])
        
        return jsonify({
            "intent": result.get("intent", "unknown"),
            "generated_response": result.get("generated_response", ""),
            "conversation_history": result.get("conversation_history", [])
        })
        
    except Exception as e:
        print(f"Error in /api/chat: {e}")
        return jsonify({
            "error": str(e),
            "intent": "error",
            "generated_response": f"An error occurred while processing your request: {str(e)}",
            "conversation_history": []
        }), 500


@app.route("/api/complete", methods=["POST"])
def complete():
    """
    AI-powered code completion endpoint (Copilot-style).
    
    Request body:
    {
        "content": "string",        # Full file content
        "cursor_position": number,  # Cursor position (0-indexed)
        "language": "string",       # Programming language (python, javascript, typescript)
        "last_char": "string"       # Optional: last character typed
    }
    
    Response:
    {
        "completion": "string",      # Suggested completion text
        "confidence": number,        # 0.0 - 1.0
        "triggered": boolean,        # Whether completion was triggered
        "trigger_reason": "string",  # Why it was/wasn't triggered
        "context": {...}             # Additional context info
    }
    """
    try:
        # Initialize completion service (lazy load)
        global completion_service
        if 'completion_service' not in globals():
            from completion_service import CompletionService
            try:
                completion_service = CompletionService()
                print("✅ Completion service initialized")
            except Exception as init_error:
                print(f"❌ Failed to initialize completion service: {init_error}")
                return jsonify({
                    "completion": "",
                    "confidence": 0,
                    "triggered": False,
                    "error": "Completion service not available"
                }), 503
        
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        content = data.get("content", "")
        cursor_position = data.get("cursor_position", len(content))
        language = data.get("language", "python")
        last_char = data.get("last_char")
        
        # Validate inputs
        if not content:
            return jsonify({
                "completion": "",
                "confidence": 0,
                "triggered": False,
                "trigger_reason": "Empty content"
            })
        
        if cursor_position < 0 or cursor_position > len(content):
            return jsonify({
                "error": "Invalid cursor_position",
                "triggered": False
            }), 400
        
        # Generate completion
        result = completion_service.generate_completion(
            content=content,
            cursor_position=cursor_position,
            language=language
        )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in /api/complete: {e}")
        return jsonify({
            "error": str(e),
            "completion": "",
            "confidence": 0,
            "triggered": False
        }), 500


@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    """List all active sessions."""
    return jsonify({
        "sessions": list(sessions.keys()),
        "count": len(sessions)
    })


@app.route("/api/sessions/<session_id>", methods=["GET"])
def get_session_info(session_id: str):
    """Get session information and history."""
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404
    
    session = sessions[session_id]
    return jsonify({
        "session_id": session_id,
        "conversation_history": session["conversation_history"],
        "created_at": session["created_at"],
        "message_count": len(session["conversation_history"])
    })


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id: str):
    """Delete a session and its history."""
    if session_id in sessions:
        del sessions[session_id]
        return jsonify({"message": f"Session {session_id} deleted"})
    return jsonify({"error": "Session not found"}), 404


@app.route("/api/sessions/<session_id>/clear", methods=["POST"])
def clear_session(session_id: str):
    """Clear conversation history for a session."""
    session = get_session(session_id)
    session["conversation_history"] = []
    return jsonify({"message": f"Session {session_id} history cleared"})


@app.route("/api/run", methods=["POST"])
def run_code():
    """
    Execute Python or JavaScript code and return the output.
    
    Note: Interactive scripts using input() are not supported.
    The script runs in non-interactive mode with no stdin.
    
    Request body:
    {
        "code": "string",      # Code to execute
        "language": "string"   # "python" or "javascript"
    }
    
    Response:
    {
        "stdout": "string",    # Standard output
        "stderr": "string",    # Standard error
        "error": "string",     # Execution error if any
        "exit_code": number    # Exit code
    }
    """
    import subprocess
    import tempfile
    import sys
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        code = data.get("code", "")
        language = data.get("language", "python").lower()
        
        if not code.strip():
            return jsonify({"error": "No code provided"}), 400
        
        if language not in ["python", "javascript"]:
            return jsonify({"error": f"Unsupported language: {language}. Only 'python' and 'javascript' are supported."}), 400
        
        # Check if code uses input() - warn user
        uses_input = False
        if language == "python":
            # Simple check for input() usage
            if "input(" in code:
                uses_input = True
        elif language == "javascript":
            # Check for readline, prompt, etc.
            if any(x in code for x in ["readline", "prompt(", "process.stdin"]):
                uses_input = True
        
        # Create a temporary file to run the code
        if language == "python":
            suffix = ".py"
            # Use the same Python interpreter that's running this server
            # Add -u for unbuffered output
            cmd = [sys.executable, "-u"]
        else:  # javascript
            suffix = ".js"
            cmd = ["node"]
        
        # Write code to temp file and execute
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Run with timeout of 10 seconds (shorter timeout for better UX)
            # Use stdin=subprocess.DEVNULL to prevent hanging on input()
            result = subprocess.run(
                cmd + [temp_file],
                capture_output=True,
                text=True,
                timeout=10,
                stdin=subprocess.DEVNULL,  # No stdin - prevents hanging on input()
                cwd=tempfile.gettempdir()
            )
            
            stderr = result.stderr
            error_msg = None
            
            # Check for EOFError which indicates input() was used
            if "EOFError" in stderr and uses_input:
                error_msg = "⚠️ Interactive input (input(), readline, etc.) is not supported in this environment. Please modify your code to use hardcoded values or function parameters instead."
            
            return jsonify({
                "stdout": result.stdout,
                "stderr": stderr,
                "exit_code": result.returncode,
                "error": error_msg
            })
            
        except subprocess.TimeoutExpired:
            return jsonify({
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
                "error": "⏱️ Execution timed out (10 second limit). Check for infinite loops or long-running operations."
            })
        except FileNotFoundError as e:
            interpreter = "Python" if language == "python" else "Node.js"
            return jsonify({
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
                "error": f"{interpreter} interpreter not found. Please ensure it's installed and in your PATH."
            })
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
                
    except Exception as e:
        print(f"Error in /api/run: {e}")
        return jsonify({
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "error": str(e)
        }), 500


# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║           Code IDE Backend Server Starting               ║
╠══════════════════════════════════════════════════════════╣
║  🚀 Server: http://localhost:{port}                       ║
║  📡 API Endpoints:                                       ║
║     POST /api/chat     - AI chat assistant               ║
║     POST /api/complete - Code completion                 ║
║     POST /api/run      - Run Python/JS code              ║
║     GET  /api/sessions - List sessions                   ║
║  🔧 Debug Mode: {str(debug).upper():5}                              ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    app.run(host="0.0.0.0", port=port, debug=debug)
