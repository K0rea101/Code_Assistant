import os
from dotenv import load_dotenv
from routing import LangGraphCodeAssistant

load_dotenv(".env")

def main():
    """Terminal-based interface for the Code Assistant"""
    print("=" * 60)
    print("🤖 Smart Python Code Assistant (with Context Memory)")
    print("=" * 60)
    print("\nInitializing assistant...")
    
    try:
        assistant = LangGraphCodeAssistant()
        conversation_history = []  # Track conversation across turns
        print("✅ Assistant initialized successfully!\n")
    except Exception as e:
        print(f"❌ Error initializing assistant: {e}")
        return
    
    print("Commands:")
    print("  - Type your question or request")
    print("  - Type 'quit' or 'exit' to close")
    print("  - Type 'clear' to clear screen")
    print("  - Type 'history' to show recent conversation")
    print("-" * 60)
    
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
                
            if user_input.lower() == 'clear':
                os.system('cls' if os.name == 'nt' else 'clear')
                continue
            
            # Show conversation history
            if user_input.lower() == 'history':
                print("\n" + "="*60)
                print("📜 CONVERSATION HISTORY (last 10 turns)")
                print("="*60)
                if not conversation_history:
                    print("No conversation history yet.")
                else:
                    recent = conversation_history[-10:]
                    for i, turn in enumerate(recent, 1):
                        role = turn.get('role', 'unknown')
                        content = turn.get('content', '')[:150]
                        timestamp = turn.get('timestamp', 'N/A')
                        intent = turn.get('intent', 'N/A')
                        print(f"\n[{i}] {role.upper()} ({intent}) at {timestamp}")
                        print(f"{content}..." if len(turn.get('content', '')) > 150 else content)
                print("\n" + "="*60 + "\n")
                continue
            
            print("\n🤖 Assistant:")
            print("-" * 60)
            
            # Process the request with conversation history
            result = assistant.process(user_input, conversation_history=conversation_history)
            
            # Display intent
            intent = result.get("intent", "unknown")
            print(f"Intent: {intent.upper()}")
            print("-" * 60)
            
            # Display response
            response = result.get("generated_response", "No response generated.")
            print(f"\n{response}\n")
            print("-" * 60)
            
            # Update conversation history from result
            conversation_history = result.get('conversation_history', conversation_history)
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    main()
