import gradio as gr
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()
# Configure generative ai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))  # Replace with your actual Gemini API key
#Import chatbot file
from ChatbotGemini import ChatBot

# Chatbot Instance
system_instruction = 'You are a friendly and helpful data analyst. The user will ask you question about data analysis, be prepared.'
chatbot = ChatBot(system_instruction)

def respond(message, chat_history):
    sql_query = chatbot.generate_sql_query(message)
    if sql_query=="No SQL query detected":
        response = 'Query Generation Failed. Please try again using more precise language'
    else:
        query_result = ChatBot.query_database_direct(sql_query) #call the method statically
        if 'detail' in query_result:
            response = f"Query invalid: {query_result['detail']}. Please refine te prompt using more domain specific language"
        else:
            insight = chatbot.generate_insight(message,sql_query,query_result)
            response = f"SQL Query:\n {sql_query}\nQuery Result:\n {query_result}\nInsight:\n {insight}"
    chat_history.append((message, response))
    return "", chat_history

with gr.Blocks() as demo:
    chatbot_ui = gr.Chatbot()
    msg = gr.Textbox()
    clear = gr.Button("Clear")

    msg.submit(respond, [msg, chatbot_ui], [msg, chatbot_ui])
    clear.click(lambda: None, None, chatbot_ui, queue=False)

demo.launch()