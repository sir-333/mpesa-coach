import os
import json
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("API_KEY")
client = genai.Client(api_key=api_key)

# --- CHAT SYSTEM PROMPT (R-T-C-C-O) ---
ROLE = "You are Pesa Coach, a friendly money coach for young adults."
TASK = "The user tells you what they spent, one or two items at a time."
CONTEXT = "The user is in Kenya and uses Kenyan shillings (KES)."
CONSTRAINTS = "Only talk about the user's spending. Never invent prices."
OUTPUT = 'Reply ONLY with valid JSON and nothing else, e.g. {"reply": "your message"}'
SYSTEM_PROMPT = f"{ROLE}\n{TASK}\n{CONTEXT}\n{CONSTRAINTS}\n{OUTPUT}"

# --- 3. SUMMARY PROMPT (R-T-C-C-O) ---
SUMMARY_ROLE = "You are Pesa Coach, a financial assistant summarizing a user's spending session."
SUMMARY_TASK = "Analyze the provided chat log and summarize the user's spending items and total spent."
SUMMARY_CONTEXT = "All amounts are in Kenyan shillings (KES) for a young adult in Kenya."
SUMMARY_CONSTRAINTS = "Base the summary strictly on the provided session log. Do not invent items or prices."
SUMMARY_OUTPUT = 'Reply ONLY with valid JSON containing a "summary" field, e.g. {"summary": "Your session summary..."}'
SUMMARY_SYSTEM_PROMPT = (
    f"{SUMMARY_ROLE}\n{SUMMARY_TASK}\n{SUMMARY_CONTEXT}\n{SUMMARY_CONSTRAINTS}\n{SUMMARY_OUTPUT}"
)


def run_chat_session():
    # Initialize variables BEFORE the chat loop so each session starts fresh
    history = []
    session_log = []
    budget_limit = 0.0  # Fixes NameError if /summary is called early

    print("\n--- Pesa Coach Started (Type /help for commands or 'exit' to finish) ---")

    # Main Chat Loop
    while True:
        user_text = input("You: ").strip()
        if not user_text:
            print("Please type something.")
            continue

        if user_text.lower() == "exit":
            print("Session ended.")
            break

        # --- MENU / SLASH COMMANDS ---
        if user_text.startswith("/"):
            command = user_text.lower()
            if command == "/help":
                print("\nAvailable Commands:")
                print("  /summary - View total spent this session")
                print("  /budget  - Set a KES spending limit")
                print("  /save    - Export your log to a JSON file")
                print("  /clear   - Reset conversation memory")
                print("  exit     - Quit Pesa Coach\n")
            elif command == "/budget":
                try:
                    budget_limit = float(input("Enter your budget limit (KES): "))
                    print(f"Budget set to KES {budget_limit:,.2f}")
                except ValueError:
                    print("Invalid number. Please try /budget again.")
            elif command == "/summary":
                print(f"\nTotal messages logged: {len(session_log)}")
                if budget_limit > 0:
                    print(f"Current budget limit: KES {budget_limit:,.2f}\n")
            elif command == "/save":
                with open("pesa_session.json", "w") as f:
                    json.dump(session_log, f, indent=2)
                print("Saved session to pesa_session.json!")
            elif command == "/clear":
                history.clear()
                print("Conversation memory cleared.")
            else:
                print("Unknown command. Type /help to see options.")
            continue

        # --- AI CHAT RESPONSE ---
        history.append(types.Content(role="user", parts=[types.Part(text=user_text)]))
        session_log.append({"role": "user", "text": user_text})

        # --- 2. 1-TIME AUTOMATIC RETRY FOR AI CHAT CALL ---
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=history,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json"
                    )
                )

                # Parse and validate JSON immediately
                data = json.loads(response.text)
                required_keys = {"reply"}
                if not isinstance(data, dict) or not required_keys.issubset(data.keys()):
                    raise ValueError(f"Missing required JSON keys. Got: {list(data.keys())}")
                if not isinstance(data["reply"], str) or not data["reply"].strip():
                    raise ValueError("The 'reply' field must be a non-empty string.")

                print("Coach:", data["reply"])

                session_log.append({"role": "coach", "text": data["reply"]})
                history.append(types.Content(role="model", parts=[types.Part(text=response.text)]))

                with open("cache.json", "w") as f:
                    json.dump(data, f, indent=2)

                break  # Success! Exit the retry loop

            except Exception as error:
                if attempt == 0:
                    # First attempt failed; loop back to retry once
                    continue
                else:
                    # Second attempt also failed; show error and clean up history
                    print("Sorry, I could not reach the AI or parse the response. Please try again.")
                    print("Details:", error)
                    history.pop()  # Remove the failed user message from history

    # --- SAVE SESSION AFTER THE CHAT LOOP ENDS ---
    if session_log:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        os.makedirs("sessions", exist_ok=True)
        filename = f"sessions/session_{stamp}.json"

        try:
            summary_response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=f"Session log:\n{json.dumps(session_log)}",
                config=types.GenerateContentConfig(
                    system_instruction=SUMMARY_SYSTEM_PROMPT,
                    response_mime_type="application/json"
                )
            )
            session_summary = json.loads(summary_response.text)
        except Exception as e:
            session_summary = f"Could not generate summary: {e}"

        session_data = {
            "timestamp": stamp,
            "summary": session_summary,
            "messages": session_log
        }

        with open(filename, "w") as f:
            json.dump(session_data, f, indent=2)
        print("Session saved to", filename)


def view_past_sessions():
    print("\n--- Past Sessions ---")
    try:
        files = sorted(os.listdir("sessions"))
        if not files:
            print("No saved sessions found.")
            return

        for idx, file in enumerate(files, start=1):
            print(f"  {idx}. {file}")

        choice = input("\nEnter the file number or filename to view: ").strip()

        # Allow the user to pick either by list number or by typing the filename
        if choice.isdigit() and 1 <= int(choice) <= len(files):
            selected_file = os.path.join("sessions", files[int(choice) - 1])
        else:
            selected_file = os.path.join("sessions", choice)

        with open(selected_file, "r") as f:
            content = json.load(f)
            print(f"\nContents of {selected_file}:")
            print(json.dumps(content, indent=2))

    except FileNotFoundError:
        print("Error: That session file or folder was not found.")
    except json.JSONDecodeError:
        print("Error: The selected file is not valid JSON.")


# --- 1. OUTER MAIN MENU LOOP ---
while True:
    print("\n=== PESA COACH MAIN MENU ===")
    print("1. Start chat session")
    print("2. View past sessions")
    print("3. Exit")

    menu_choice = input("Choose an option (1-3): ").strip()

    if menu_choice == "1":
        run_chat_session()
    elif menu_choice == "2":
        view_past_sessions()
    elif menu_choice == "3":
        print("Goodbye!")
        break
    else:
        print("Invalid choice. Please enter 1, 2, or 3.")