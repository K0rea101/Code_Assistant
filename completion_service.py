"""
AI-Powered Code Completion Service
Provides Copilot-style code completions using OpenRouter's DeepSeek Coder model.
"""
import os
import re
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


class CompletionService:
    """
    Standalone service for AI-powered code completion.
    Handles context building, trigger detection, and LLM-based suggestions.
    """
    
    # Trigger characters that should prompt completions
    TRIGGER_CHARS = {'.', '(', '=', ':', '[', '{', '\n', ' '}
    
    # Language-specific keywords that suggest completion opportunities
    COMPLETION_KEYWORDS = {
        'python': ['def', 'class', 'if', 'for', 'while', 'import', 'from', 'return', 'raise', 'with', 'try', 'except'],
        'javascript': ['function', 'const', 'let', 'var', 'class', 'if', 'for', 'while', 'return', 'import', 'export', 'async', 'await'],
        'typescript': ['function', 'const', 'let', 'var', 'class', 'interface', 'type', 'if', 'for', 'while', 'return', 'import', 'export', 'async', 'await'],
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the completion service with Kat Coder model.
        
        Args:
            api_key: OpenRouter API key (defaults to env variable)
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")
        
        # Initialize LLM - use Gemini Flash (more reliable than DeepSeek free tier)
        self.llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
            model="kwaipilot/kat-coder-pro:free",  # More reliable for completions
            temperature=0.3,  # Low temperature for more deterministic completions
            max_tokens=200,   # Short completions (a few lines)
            timeout=15,       # Quick timeout for responsive UX
            max_retries=2
        )
    
    def should_trigger_completion(
        self, 
        content: str, 
        cursor_position: int, 
        language: str,
        last_char: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Determine if completion should be triggered based on context.
        
        Args:
            content: Full file content
            cursor_position: Current cursor position (0-indexed)
            language: Programming language (python, javascript, typescript)
            last_char: Last character typed (optional)
        
        Returns:
            Tuple of (should_trigger: bool, reason: str)
        """
        # Safety check
        if cursor_position < 0 or cursor_position > len(content):
            return False, "Invalid cursor position"
        
        # Get text before cursor
        before_cursor = content[:cursor_position]
        
        # Don't trigger on empty content
        if not before_cursor.strip():
            return False, "Empty content"
        
        # Check if last character is a trigger
        if last_char and last_char in self.TRIGGER_CHARS:
            return True, f"Trigger char: '{last_char}'"
        
        # Check if cursor is after a trigger character
        if before_cursor and before_cursor[-1] in self.TRIGGER_CHARS:
            return True, f"After trigger char: '{before_cursor[-1]}'"
        
        # Check for language-specific keywords
        keywords = self.COMPLETION_KEYWORDS.get(language.lower(), [])
        for keyword in keywords:
            # Look for keyword followed by space or opening bracket
            pattern = rf'\b{re.escape(keyword)}\s*[\(\[\{{]?\s*$'
            if re.search(pattern, before_cursor):
                return True, f"After keyword: '{keyword}'"
        
        # Check if typing a word that could be completed
        # Match partial identifier (letters, numbers, underscores)
        word_match = re.search(r'[\w]+$', before_cursor)
        if word_match:
            partial_word = word_match.group()
            # Trigger if we have at least 2 characters
            if len(partial_word) >= 2:
                return True, f"Partial word: '{partial_word}'"
        
        return False, "No trigger detected"
    
    def build_context(
        self,
        content: str,
        cursor_position: int,
        language: str,
        context_window: int = 2000
    ) -> Dict[str, Any]:
        """
        Build context around the cursor for the LLM.
        
        Args:
            content: Full file content
            cursor_position: Cursor position (0-indexed)
            language: Programming language
            context_window: Max characters before/after cursor to include
        
        Returns:
            Dict with before_cursor, after_cursor, language, line_number
        """
        # Split at cursor
        before_cursor = content[:cursor_position]
        after_cursor = content[cursor_position:]
        
        # Limit context window
        if len(before_cursor) > context_window:
            before_cursor = before_cursor[-context_window:]
        
        if len(after_cursor) > context_window:
            after_cursor = after_cursor[:context_window]
        
        # Calculate current line number
        line_number = before_cursor.count('\n') + 1
        
        # Get current line content
        lines_before = before_cursor.split('\n')
        current_line = lines_before[-1] if lines_before else ""
        
        # Calculate indentation
        indent = len(current_line) - len(current_line.lstrip())
        
        return {
            "before_cursor": before_cursor,
            "after_cursor": after_cursor,
            "language": language,
            "line_number": line_number,
            "current_line": current_line,
            "indent_level": indent
        }
    
    def generate_completion(
        self,
        content: str,
        cursor_position: int,
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        Generate code completion suggestion.
        
        Args:
            content: Full file content
            cursor_position: Cursor position
            language: Programming language
        
        Returns:
            Dict with completion, confidence, trigger_reason, context
        """
        # Check if we should trigger
        last_char = content[cursor_position - 1] if cursor_position > 0 else None
        should_trigger, trigger_reason = self.should_trigger_completion(
            content, cursor_position, language, last_char
        )
        
        if not should_trigger:
            return {
                "completion": "",
                "confidence": 0.0,
                "trigger_reason": trigger_reason,
                "triggered": False
            }
        
        # Build context
        ctx = self.build_context(content, cursor_position, language)
        
        # Create completion prompt
        prompt = self._build_completion_prompt(ctx)
        
        try:
            # Call LLM
            response = self.llm.invoke(prompt)
            raw_completion = (response.content or "").strip()
            
            # Post-process completion
            completion = self._clean_completion(raw_completion, ctx)
            
            # Calculate confidence based on completion quality
            confidence = self._calculate_confidence(completion, ctx)
            
            return {
                "completion": completion,
                "confidence": confidence,
                "trigger_reason": trigger_reason,
                "triggered": True,
                "context": {
                    "line_number": ctx["line_number"],
                    "language": language
                }
            }
            
        except Exception as e:
            return {
                "completion": "",
                "confidence": 0.0,
                "error": str(e),
                "triggered": True,
                "trigger_reason": trigger_reason
            }
    
    def _build_completion_prompt(self, ctx: Dict[str, Any]) -> str:
        """
        Build the LLM prompt for code completion.
        
        Args:
            ctx: Context dictionary from build_context()
        
        Returns:
            Formatted prompt string
        """
        language = ctx["language"]
        before = ctx["before_cursor"]
        after = ctx["after_cursor"]
        
        # Simpler, more direct prompt that works better with free models
        if after.strip():
            # Fill-in-the-middle completion
            prompt = f"""You are a code completion assistant. Complete the {language} code.

Code so far:
{before}[COMPLETE HERE]

What comes after:
{after}

Write ONLY the code that goes in [COMPLETE HERE]. Be brief (1-3 lines). No explanations."""
        else:
            # End-of-file completion - even simpler
            prompt = f"""Complete this {language} code. Write ONLY the next 1-3 lines:

{before}"""
        
        return prompt
    
    def _clean_completion(self, raw_completion: str, ctx: Dict[str, Any]) -> str:
        """
        Clean and format the LLM's raw completion output.
        
        Args:
            raw_completion: Raw text from LLM
            ctx: Context dictionary
        
        Returns:
            Cleaned completion text
        """
        completion = raw_completion
        
        # Remove markdown code blocks
        if "```" in completion:
            # Extract content between code fences
            lines = completion.split('\n')
            in_code_block = False
            cleaned_lines = []
            
            for line in lines:
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block or not any(line.strip().startswith(p) for p in ["```", "Here", "This", "The"]):
                    cleaned_lines.append(line)
            
            completion = '\n'.join(cleaned_lines)
        
        # Remove common explanation prefixes
        explanation_patterns = [
            r'^(Here\'s|Here is|This is|The|A|An)\s+.*?:\s*',
            r'^(Sure|Okay|Alright)[,!]?\s+',
            r'^(I|You|We)\s+(can|will|should|might)\s+.*?:\s*'
        ]
        
        for pattern in explanation_patterns:
            completion = re.sub(pattern, '', completion, flags=re.IGNORECASE | re.MULTILINE)
        
        # Trim whitespace
        completion = completion.strip()
        
        # Limit to reasonable length (max 5 lines)
        lines = completion.split('\n')
        if len(lines) > 5:
            completion = '\n'.join(lines[:5])
        
        return completion
    
    def _calculate_confidence(self, completion: str, ctx: Dict[str, Any]) -> float:
        """
        Calculate confidence score for the completion.
        
        Args:
            completion: Cleaned completion text
            ctx: Context dictionary
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not completion:
            return 0.0
        
        confidence = 0.5  # Base confidence
        
        # Boost confidence for certain patterns
        if re.search(r'def\s+\w+\(', completion):  # Function definition
            confidence += 0.2
        if re.search(r'class\s+\w+', completion):  # Class definition
            confidence += 0.2
        if re.search(r'return\s+', completion):    # Return statement
            confidence += 0.1
        if re.search(r'import\s+\w+', completion):  # Import statement
            confidence += 0.15
        
        # Reduce confidence for very short completions
        if len(completion) < 5:
            confidence -= 0.2
        
        # Boost for proper indentation matching
        current_indent = ctx.get("indent_level", 0)
        completion_indent = len(completion) - len(completion.lstrip())
        if abs(completion_indent - current_indent) <= 4:
            confidence += 0.1
        
        # Clamp between 0 and 1
        return max(0.0, min(1.0, confidence))


# Standalone test/demo function
def demo():
    """Demo the completion service with sample code."""
    import json
    
    service = CompletionService()
    
    # Test case 1: Function definition
    code1 = """def calculate_factorial(n):
    if n == 0:
        return 1
    """
    
    result1 = service.generate_completion(code1, len(code1), "python")
    print("=" * 60)
    print("Test 1: Complete function body")
    print("=" * 60)
    print(f"Context:\n{code1}")
    print(f"\nResult:\n{json.dumps(result1, indent=2)}")
    
    # Test case 2: After dot (method call)
    code2 = """data = [1, 2, 3, 4, 5]
result = data."""
    
    result2 = service.generate_completion(code2, len(code2), "python")
    print("\n" + "=" * 60)
    print("Test 2: After dot (method suggestion)")
    print("=" * 60)
    print(f"Context:\n{code2}")
    print(f"\nResult:\n{json.dumps(result2, indent=2)}")
    
    # Test case 3: JavaScript class
    code3 = """class UserManager {
    constructor("""
    
    result3 = service.generate_completion(code3, len(code3), "javascript")
    print("\n" + "=" * 60)
    print("Test 3: JavaScript constructor parameters")
    print("=" * 60)
    print(f"Context:\n{code3}")
    print(f"\nResult:\n{json.dumps(result3, indent=2)}")


if __name__ == "__main__":
    demo()
