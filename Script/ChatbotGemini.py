import requests
import json
from pathlib import Path
import re
import os
import psycopg2
import google.generativeai as genai
from dotenv import load_dotenv

class ChatBot:
    def __init__(self, system_instruction, model_name="gemini-2.0-flash"): #specifying the model name
        """
        Initializes the ChatBot with system instructions and Google Gemini API.

        Args:
            system_instruction (str): Instructions given to the chatbot to guide its responses.
        """
        self.system_instruction = system_instruction
        self.model_name = model_name
        self.model = genai.GenerativeModel(self.model_name) #Initialize the model
        self.chat = self.model.start_chat(history=[])  # Initialize the chat session with empty history.  Crucially, this is a *chat* model, so we manage the history within the chat object.

        #Prime the chat with the system instruction
        response = self.chat.send_message(self.system_instruction) #send system instruction
        #print(response.text)  #optional print to see how the LLM interprets the instruction
        self.conversation_history = [f"System: {system_instruction}"]

    def get_response(self, user_input):
        """
        Generates a response to user input using the Google Gemini API, taking into account
        system instructions and conversation history.

        Args:
            user_input (str): The user's message.

        Returns:
            str: The chatbot's response.
        """
        try:
            response = self.chat.send_message(user_input)
            response_text = response.text #Extract just the textual response
        except Exception as e:
            response_text = f"Error: {e}"  # Handle potential API errors

        self.conversation_history.append(f"User: {user_input}")
        self.conversation_history.append(f"Bot: {response_text}")
        return response_text

    def print_conversation(self):
        """Prints the entire conversation history."""
        for message in self.conversation_history:
            print(message)

    def generate_sql_query(self, natural_language):
        script_dir = Path.cwd()
        # # Navigate to the parent directory and then into the Context folder
        context_dir = script_dir.parent / "AI Assistant" / "Context"

        # Construct the full path to the file
        file_path = context_dir / "MASTER_FUNDING.txt"

        # Open context file in read mode
        with open(file_path, "r") as file:
            # Read the entire file content
            content = file.read()

        prompt = f"""
You are an expert SQL generator. Translate the following natural language request into a valid SQL query. 
Make sure the query is properly formatted and is tailored for our database schema.
The database we are using is PostgreSQL. Do not use backtick for column names.
The table in the database is "master_funding", it uses the following schema:
{content}

Request: {natural_language}

SQL Query:"""
        response = self.get_response(prompt)

        # Get SQL query
        pattern = r"```sql\n(.*?)\n```"

        # Search for the pattern
        match = re.search(pattern, response, re.DOTALL)

        # Extracted SQL query
        sql_query = match.group(1) if match else None

        # Return SQL if SQL query found
        if sql_query is not None:
            return sql_query
        else:
            return "No SQL query detected"
    def generate_insight(self,natural_language, sql_query, query_result):
        # Format the query result in a readable way (e.g., JSON)
        formatted_result = json.dumps(query_result, indent=2)
        
        prompt = f"""
    You are a data analyst. You first received the following natural language request:
    "{natural_language}"

    Based on that, an SQL query was generated and executed:
    {sql_query}

    The query returned the following result:
    {formatted_result}

    Please show the result in tabular format and provide a brief explanation of the insights, trends, or key points that can be derived from these results if necessary.
    """
        response = self.get_response(prompt)
        return response
    def query_database(sql_query):
        # Endpoint for query middleware
        API_URL = "http://127.0.0.1:8000/query"
        response = requests.post(API_URL, json={"query": sql_query})
        return response.json()
    def query_database_direct(sql_query):
        try:
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASS")
            )
            cur = conn.cursor()
            cur.execute(sql_query)
            result = cur.fetchall() # Or cur.fetchone()
            conn.commit()
        except psycopg2.Error as e:
            result = f"Database error: {e}"
        finally:
            if conn:
                cur.close()
                conn.close()
            return result
        
# Example usage
if __name__ == "__main__":
    # Configure generative ai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))  # Replace with your actual Gemini API key

    system_instruction = 'You are a friendly and helpful data analyst. The user will ask you question about data analysis, be prepared.'
    chatbot = ChatBot(system_instruction)  # Create an instance of the ChatBot class

    print("Chatbot initialized.")

    # Run query and result generation
    loop = 0
    run = "Y"
    naturalQuery = None
    finish = False
    while run=="Y": 
        loop += 1
        if naturalQuery is None:
            naturalQuery=input("Enter yout data related question: ") # Natural query input
        elif loop>1 and finish==True:
            naturalQuery=input("Enter yout data related question: ") # Natural query input
        finish=False 
        # Generate natural query
        sql_query = chatbot.generate_sql_query(naturalQuery)  # Call the method on the *instance*
        if sql_query=="No SQL query detected":
            print('Query Generation Failed.')
            naturalQuery=input("Please try again using more precise language: ")
            naturalQuery=f'''The previous question doesn't generate sql statement.
            Here is the new question: {naturalQuery}'''
        else:
            # Query database from the generated query
            query_result = ChatBot.query_database_direct(sql_query) #call the method statically
            if 'detail' in query_result:
                print(sql_query)
                print(f"Query invalid: {query_result['detail']}")
                naturalQuery=input("Please refine te prompt using more domain specific language: ")
                continue
            else:
                print(sql_query)
                print(query_result) 
                insight = chatbot.generate_insight(naturalQuery,sql_query,query_result)
                print(insight)
                print("***********")
        run = input("Do you want to continue? [Y/n]: ").upper()
        finish = True