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
        "origins": ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
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
    Code completion endpoint for AI-powered autocomplete suggestions.
    
    Request body:
    {
        "context": "string",  # Code before cursor
        "position": number,   # Cursor position
        "language": "string"  # Programming language
    }
    
    Response:
    {
        "completion": "string",
        "confidence": number
    }
    """
    # Check if assistant is available
    if assistant is None:
        return jsonify({"completion": "", "confidence": 0, "error": "AI not configured"})
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        context = data.get("context", "")
        language = data.get("language", "python")
        
        if not context.strip():
            return jsonify({"completion": "", "confidence": 0})
        
        # Use the code generation LLM for completions
        # Build a completion-focused prompt
        prompt = f"""Complete the following {language} code. Only provide the completion, no explanations.
Code context:
```{language}
{context}
```

Provide ONLY the next few lines of code that should follow. Be concise."""

        try:
            result = assistant.code_llm.invoke(prompt)
            completion = (result.content or "").strip()
            
            # Clean up the completion - remove markdown code blocks if present
            if completion.startswith("```"):
                lines = completion.split("\n")
                # Remove first and last lines if they're code block markers
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                completion = "\n".join(lines)
            
            return jsonify({
                "completion": completion,
                "confidence": 0.8
            })
            
        except Exception as llm_error:
            print(f"LLM completion error: {llm_error}")
            return jsonify({"completion": "", "confidence": 0})
        
    except Exception as e:
        print(f"Error in /api/complete: {e}")
        return jsonify({"error": str(e), "completion": "", "confidence": 0}), 500


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
║     GET  /api/sessions - List sessions                   ║
║  🔧 Debug Mode: {str(debug).upper():5}                              ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    app.run(host="0.0.0.0", port=port, debug=debug)
