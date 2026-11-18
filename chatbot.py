from google import genai
from dotenv import load_dotenv
import os
from google.genai import types

load_dotenv()
api_key=os.getenv("API_KEY")
client=genai.Client(api_key=api_key)
role = "You are a music directior in a band."
task = "Your job is to shape the overall artistic, musical and logistical flow of a live show, tour or recording session."
context = "You work at wanavokali band, rebrand and produce a new genre. band members are so good at what they do so you must match their energy, a good number are genz figure out how to handle them."
constraints = "Only answer questions about contemporary music."
output = "Keep answers short"

#RAG
knowledge = [
    "Rehersals are held on Tuesday and Friday at from 6pm to 11pm.",
    "Every member must carry their own drinking water and snerks, instruments in-eyers.",
    "The first three rehersals take them through general knowledge.",
    "Each class lasts 30 minutes.",
]

chat = client.chats.create(
    model="gemini-3.5-flash",
    config=types.GenerateContentConfig(system_instruction=role + " " + task + constraints + " " + output + " " + context)
)

print ("Started")

while True:
    message=input("you: ")
    
    if message.lower() == "exit":
        print("Goodbye!")
        break
    
    try:
        response = chat.send_message(message)
        print("Gemini: ", response.text)
        
    except Exception as error:
        print("error: ", error)