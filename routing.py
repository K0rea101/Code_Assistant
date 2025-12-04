import os
import json
from datetime import datetime
from dotenv import load_dotenv
from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI

load_dotenv(".env")

# ---------- State ----------

class AssistantState(TypedDict):
    user_input: str
    intent: str
    retrieved_examples: List[Dict[str, Any]]
    generated_response: str
    uploaded_files: List[Dict[str, str]]  # [{filename, text}]
    conversation_history: List[Dict[str, Any]]  # [{role, content, timestamp, intent}]
    context_summary: str  # Summary of recent conversation


# ---------- Intent Classifier ----------

class LLMIntentClassifier:
    """
    LLM-based intent classification (OpenRouter via LangChain ChatOpenAI).
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            model="openai/gpt-oss-20b:free",
            temperature=0.1,
            max_tokens=100,
        )

    def classify_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Classify the prompt into one of:
          - generate  (user wants to add/modify/produce code)
          - explain   (user wants explanation of code/files/concepts)
          - debug     (user wants help fixing errors, tracebacks, failing tests)
          - unsupported
        Return JSON: {"task": "<...>", "user_input": "<original>"}
        """
        prompt = f"""
You are an intent classifier for a Python code assistant.

Decide the task from ONLY the user's message (files may be attached as context later):
- "generate": add/modify/produce code (e.g., "add a function", "refactor", "write tests").
- "explain": explain a codebase/file/concept ("explain", "what does this do").
- "debug": fix errors/tracebacks/failing tests; user mentions "error", "traceback", "bug", "fails".
- "unsupported": unrelated to Python and Javascript at all.

Respond ONLY with compact JSON exactly like:
{{"task":"<generate|explain|debug|unsupported>","user_input":"{user_input}"}}

Input: {user_input}
JSON:
""".strip()

        try:
            res = self.llm.invoke(prompt)
            content = (res.content or "").strip()
            if "{" in content:
                s = content.find("{")
                e = content.rfind("}") + 1
                return json.loads(content[s:e])
        except Exception as e:
            print(f"Intent classification error: {e}")

        # Fallback rules
        lower = user_input.lower()
        if any(k in lower for k in ["traceback", "exception", "error", "failing", "bug", "stack trace"]):
            return {"task": "debug", "user_input": user_input}
        if any(k in lower for k in ["explain", "what is", "what does", "how does"]):
            return {"task": "explain", "user_input": user_input}
        return {"task": "generate", "user_input": user_input}


# ---------- Main Assistant via LangGraph ----------

class LangGraphCodeAssistant:
    def __init__(self):
        self.intent_classifier = LLMIntentClassifier()

        # LLMs
        self.code_llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            model="kwaipilot/kat-coder-pro:free",
            temperature=0.2,
            max_tokens=1024,
            timeout=60,
            max_retries=1                                                                      
        )
        self.explain_llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            model="meta-llama/llama-3.3-70b-instruct:free",
            temperature=0.2,
            max_tokens=600,
            timeout=50,
            max_retries=1
        )
        self.debug_llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            model="kwaipilot/kat-coder-pro:free",
            temperature=0.2,
            max_tokens=700,
            timeout=50,
            max_retries=1
        )

        self.build_graph()

    # ---------- Nodes ----------

    def _format_conversation_context(self, history: List[Dict[str, Any]], max_turns: int = 5) -> str:
        """Format recent conversation history for context."""
        if not history:
            return "(No previous conversation)"
        
        recent = history[-max_turns:] if len(history) > max_turns else history
        context_parts = []
        
        for turn in recent:
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            intent = turn.get("intent", "")
            
            if role == "user":
                context_parts.append(f"User asked ({intent}): {content[:200]}..." if len(content) > 200 else f"User asked ({intent}): {content}")
            elif role == "assistant":
                context_parts.append(f"Assistant responded: {content[:200]}..." if len(content) > 200 else f"Assistant: {content}")
        
        return "\n".join(context_parts) if context_parts else "(No previous conversation)"

    def _format_files_for_context(self, files: List[Dict[str, str]], max_chars: int = 240000) -> str:
        """Serialize uploaded files into a compact, LLM-friendly section."""
        parts = []
        used = 0
        for f in files or []:
            name = f.get("filename", "uploaded_file.py")
            text = f.get("text", "")
            chunk = f"### FILE: {name}\n{text}\n"
            if used + len(chunk) > max_chars:
                remaining = max_chars - used
                if remaining > 200:
                    chunk = f"### FILE: {name}\n{text[:remaining]}\n... [truncated]\n"
                    parts.append(chunk)
                break
            parts.append(chunk)
            used += len(chunk)
        return "\n".join(parts) if parts else "(no attached files)"

    def unsupported_intent_node(self, state: AssistantState):
        state["generated_response"] = (
            "Sorry, I can only generate, explain, or debug Python code. "
            "Try: 'Add a function to ...', 'Explain this file ...', or 'Debug this error ...'."
        )
        return state

    def classify_intent_node(self, state: AssistantState):
        try:
            result = self.intent_classifier.classify_intent(state["user_input"])
            state["intent"] = result["task"]
            print(f"Intent classified as: {state['intent']}")
        except Exception as e:
            print(f"Intent classification error: {e}")
            state["intent"] = "generate"
        return state

    def generate_code_node(self, state: AssistantState):
        try:
            files_ctx = self._format_files_for_context(state.get("uploaded_files", []))
            conv_ctx = self._format_conversation_context(state.get("conversation_history", []))
            
            # Detect language from user input
            user_lower = state['user_input'].lower()
            if any(kw in user_lower for kw in ['javascript', 'js', 'node', 'typescript', 'ts', 'java']):
                lang_tag = "javascript"
            else:
                lang_tag = "python"
            
            prompt = f"""You are a senior Software engineer, proficient in Python and Javascript.

IMPORTANT INSTRUCTIONS:
- DO NOT use first-person language (I, me, my, I'll, I will, let me)
- Write in second-person (you, your) when addressing the user OR use neutral third-person
- Be direct and professional
- Start directly with the plan, not with "I will" or "Let me"

Conversation Context (refer to this if relevant):
{conv_ctx}

Current User Request:
{state['user_input']}

Attached files (use them if relevant; modify or add code as requested):
{files_ctx}

Task: If the user asks to add/modify code in the attached files, propose a minimal patch. If the user asks to generate code in the user request, provide a clear and concise implementation.
IMPORTANT: If the user refers to "earlier code" or "previous code", check the conversation context above.

Return:
1) Short plan in paragraphs format (describe what will be implemented/modified, no first-person language)
2) Code implementation
3) Code Explanation (It has to be very descriptive and informative)
4) Notes/assumptions
make sure the code is in a markdown code block with ```{lang_tag} tags, and the code ends with ```.
"""
            res = self.code_llm.invoke(prompt)
            content = (res.content or "").strip()
            if not content.startswith("```"):
                content = f"```markdown\n{content}\n```"
            state["generated_response"] = content
        except Exception as e:
            state["generated_response"] = f"Error generating code: {e}"
        return state

    def explain_code_node(self, state: AssistantState):
        try:
            files_ctx = self._format_files_for_context(state.get("uploaded_files", []))
            conv_ctx = self._format_conversation_context(state.get("conversation_history", []))
            
            prompt = f"""You are a Python and Javascript tutor.

IMPORTANT INSTRUCTIONS:
- DO NOT use first-person language (I, me, my, I'll, let me)
- Address the user directly using "you/your" OR use neutral explanations
- Be clear and educational
- Start explanations directly without "I will explain"            

Conversation Context (refer to previous discussion if relevant):
{conv_ctx}

Current User Question:
{state['user_input']}

If files are provided, explain *those files* in context of the question:
{files_ctx}

Provide:
- Clear explanation
- Key functions/classes and their roles
- Complexity/edge cases
- Suggestions for improvement (brief)
- Reference previous conversation if the user asks about "that code" or "earlier example"
"""
            res = self.explain_llm.invoke(prompt)
            state["generated_response"] = (res.content or "").strip()
        except Exception as e:
            state["generated_response"] = f"Error explaining: {e}"
        return state

    def debug_file_node(self, state: AssistantState):
        try:
            files_ctx = self._format_files_for_context(state.get("uploaded_files", []))
            conv_ctx = self._format_conversation_context(state.get("conversation_history", []))
            
            # Detect language from user input or files
            user_lower = state['user_input'].lower()
            if any(kw in user_lower for kw in ['javascript', 'js', 'node', 'typescript', 'ts', 'java']):
                lang_tag = "javascript"
            elif state.get("uploaded_files"):
                # Check file extensions
                for f in state["uploaded_files"]:
                    filename = f.get("filename", "").lower()
                    if filename.endswith(('.js', '.ts', '.jsx', '.tsx')):
                        lang_tag = "javascript"
                        break
                else:
                    lang_tag = "python"
            else:
                lang_tag = "python"
            
            prompt = f"""You are a senior Python and Javascript debugger.

IMPORTANT INSTRUCTIONS:
- DO NOT use first-person language (I, me, my, I'll, let me)
- Present findings directly and professionally
- Use neutral language or address the user as "you"
- Start directly with analysis, not "I will analyze"            

Conversation Context (check if error relates to previous discussion):
{conv_ctx}

Current User Goal:
{state['user_input']}

Analyze the attached file(s), find likely issues, and propose a fix:
{files_ctx}

Return a compact, actionable report:

1) Summary (1–2 sentences)
2) Root cause analysis (bullets)
3) Code fix in {lang_tag} programming code:
```{lang_tag}
# patch here
4) quick checks
"""
            res = self.debug_llm.invoke(prompt)
            state["generated_response"] = (res.content or "").strip() or "No debug output."

        except Exception as e:
            state["generated_response"] = f"Error during debugging: {e}"

        return state
    
# ---------- Graph Definition ----------

    def build_graph(self):
        workflow = StateGraph(AssistantState)

        workflow.add_node("classify_intent", self.classify_intent_node)
        workflow.add_node("generate_code", self.generate_code_node)
        workflow.add_node("explain_code", self.explain_code_node)
        workflow.add_node("debug_file", self.debug_file_node)
        workflow.add_node("unsupported_intent", self.unsupported_intent_node)

        workflow.set_entry_point("classify_intent")

        workflow.add_conditional_edges(
            "classify_intent",
            lambda s: s["intent"],
            {
                "generate": "generate_code",
                "explain": "explain_code",
                "debug": "debug_file",
                "unsupported": "unsupported_intent",
            },
        )
        workflow.add_edge("generate_code", END)
        workflow.add_edge("explain_code", END)
        workflow.add_edge("debug_file", END)
        workflow.add_edge("unsupported_intent", END)

        self.graph = workflow.compile()

# ---------- Public APIs ------------

    def process(self, user_input: str, uploaded_files: Optional[List[Dict[str, str]]] = None, 
                conversation_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Main entry: prompt is classified; files (if any) are provided as context to the routed node."""
        
        state: AssistantState = {
                "user_input": user_input,
                "intent": "",
                "retrieved_examples": [],
                "generated_response": "",
                "uploaded_files": uploaded_files or [],
                "conversation_history": conversation_history or [],
                "context_summary": "",
        }
        try:
            result = self.graph.invoke(state)
            
            # Add current turn to history
            result["conversation_history"].append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat(),
                "intent": result.get("intent", "unknown")
            })
            result["conversation_history"].append({
                "role": "assistant",
                "content": result.get("generated_response", ""),
                "timestamp": datetime.now().isoformat(),
                "intent": result.get("intent", "unknown")
            })
            
            return result
        
        except Exception as e:

            print(f"Graph execution error: {e}")
            return {
            "user_input": user_input,
            "intent": "error",
            "retrieved_examples": [],
            "generated_response": f"Error processing request: {e}",
            "uploaded_files": uploaded_files or [],
            "conversation_history": [],
            }
