import os
import sys
import asyncio
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.client import ChatClient
from src.personality.manager import PersonaManager
from dotenv import load_dotenv

load_dotenv()

class CLIApp:
    def __init__(self):
        self.manager = PersonaManager()
        self.client = ChatClient()
        self.current_persona_id = "default_wife"
        self.history = []

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        persona = self.manager.get_persona(self.current_persona_id)
        print("=" * 50)
        print(f"AI Wife Chatbot - {persona.metadata.id} (v{persona.metadata.version})")
        print(f"Model: {persona.metadata.target_model}")
        print("Commands: /switch, /list, /reload, /exit")
        print("=" * 50)

    def switch_persona(self):
        print("\nAvailable Personas:")
        personas = self.manager.list_personas()
        for idx, p in enumerate(personas):
            print(f"{idx + 1}. {p['id']} - {p['tags']}")
        
        try:
            choice = input("\nSelect Persona (ID or Number): ").strip()
            found_id = None
            
            # Check if user entered a number
            if choice.isdigit() and 1 <= int(choice) <= len(personas):
                 found_id = personas[int(choice) - 1]['id']
            # Check if user entered an ID
            elif any(p['id'] == choice for p in personas):
                found_id = choice
            
            if found_id:
                self.current_persona_id = found_id
                self.history = [] # Reset history on switch
                print(f"Switched to {found_id}")
            else:
                print("Invalid selection.")
        except Exception as e:
            print(f"Error switching: {e}")

    def run(self):
        self.clear_screen()
        self.print_header()
        
        # Initial Greeting
        persona = self.manager.get_persona(self.current_persona_id)
        if persona:
             print(f"\n{persona.prompts.greeting}")
             self.history.append(AIMessage(content=persona.prompts.greeting))

        while True:
            try:
                user_input = input("\nYou: ").strip()
                if not user_input:
                    continue

                if user_input.lower() == "/exit":
                    print("Goodbye!")
                    break
                elif user_input.lower() == "/list":
                    for p in self.manager.list_personas():
                        print(f"- {p['id']}: {p['description']}")
                    continue
                elif user_input.lower() == "/switch":
                    self.switch_persona()
                    self.print_header()
                    # Re-send greeting
                    persona = self.manager.get_persona(self.current_persona_id)
                    print(f"\n{persona.prompts.greeting}")
                    self.history = [AIMessage(content=persona.prompts.greeting)]
                    continue
                elif user_input.lower() == "/reload":
                    self.manager.reload()
                    print("Personas reloaded.")
                    continue

                # Prepare messages
                persona = self.manager.get_persona(self.current_persona_id)
                system_prompt = SystemMessage(content=persona.prompts.system)
                
                messages = [system_prompt] + self.history + [HumanMessage(content=user_input)]

                print("Wife: ", end="", flush=True)
                
                # Streaming response
                full_response = ""
                response_text = self.client.chat(messages, temperature=persona.config.temperature)
                print(response_text)
                
                self.history.append(HumanMessage(content=user_input))
                self.history.append(AIMessage(content=response_text))

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")

if __name__ == "__main__":
    app = CLIApp()
    app.run()
