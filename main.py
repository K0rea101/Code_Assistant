import os
from dotenv import load_dotenv
from routing import LangGraphCodeAssistant

load_dotenv(".env")

def main():
    """Terminal-based interface for the Code Assistant"""
    print("=" * 60)
    print("🤖 Smart Python Code Assistant (Terminal Interface)")
    print("=" * 60)
    print("\nInitializing assistant...")
    
    try:
        assistant = LangGraphCodeAssistant()
        print("✅ Assistant initialized successfully!\n")
    except Exception as e:
        print(f"❌ Error initializing assistant: {e}")
        return
    
    print("Commands:")
    print("  - Type your question or request")
    print("  - Type 'quit' or 'exit' to close")
    print("  - Type 'clear' to clear screen")
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
            
            print("\n🤖 Assistant:")
            print("-" * 60)
            
            # Process the request
            result = assistant.process(user_input)
            
            # Display intent
            intent = result.get("intent", "unknown")
            print(f"Intent: {intent.upper()}")
            print("-" * 60)
            
            # Display response
            response = result.get("generated_response", "No response generated.")
            print(f"\n{response}\n")
            print("-" * 60)
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    main()
