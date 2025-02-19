import requests
import json
from pathlib import Path
import re
import os
import psycopg2

# Set Ollama API URL endpoint
OLLAMA_API_URL = "http://localhost:11434/api/chat"

# Define initial setup function. This function only needs to be run once
def initial_setup():
    instruction = 'You are a friendly and helpful data analyst. The user will ask you question about data analysis, be prepared.'
    chat= [{'role':'system',
            'content':instruction}]
    payload = {
    "model":"deepseek-r1:8b",
    "messages":chat,
    "stream":False,
    "temperature": 0.0
}
    response = requests.post(OLLAMA_API_URL,json=payload).json()

    chat.append({'role':'assistant',
                        'content':response['message']['content']})
    return chat

# Define natural language query function. This function takes natural language as input and outputs SQL query.
def generate_sql_query(chat_hist,natural_language):
    script_dir = Path.cwd()
    # # Navigate to the parent directory and then into the Context folder
    # context_dir = script_dir.parent / "Context"

    # Construct the full path to the file
    file_path = script_dir / "Context" / "MASTER_FUNDING.txt"

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

SQL Query:
"""
    chat_hist.append({"role":"user","content":prompt})
    payload = {
        "model": "deepseek-r1:8b",  # if needed, or remove if the API defaults to it
        "messages": chat_hist,
        "temperature": 0.0,  # Lower temperature can help ensure deterministic output
        "stream":False
    }
    response = requests.post(OLLAMA_API_URL, json=payload).json()
    
    # The structure may vary based on the API; assume generated text is in this field:
    reply = response['message']['content']
    chat_hist.append({"role":"assistant","content":reply})

    # Get SQL query
    pattern = r"```sql\n(.*?)\n```"

    # Search for the pattern
    match = re.search(pattern, reply, re.DOTALL)

    # Extracted SQL query
    sql_query = match.group(1) if match else None

    # Return SQL if SQL query found
    if sql_query is not None:
        return chat_hist,sql_query
    else:
        return chat_hist,"No SQL query detected"

# Define insight generating function. This function took query result and outputs insight
def generate_insight(chat_hist,natural_language, sql_query, query_result):
    # Format the query result in a readable way (e.g., JSON)
    formatted_result = json.dumps(query_result, indent=2)
    
    prompt = f"""
You are a data analyst. You first received the following natural language request:
"{natural_language}"

Based on that, an SQL query was generated and executed:
{sql_query}

The query returned the following result:
{formatted_result}

Please provide a detailed explanation of the insights, trends, or key points that can be derived from these results if necessary.
"""
    chat_hist.append({"role":"user","content":prompt})
    payload = {
        "model": "deepseek-r1:8b",
        "messages": chat_hist,
        "temperature": 0.7,
        "stream": False
    }
    response = requests.post(OLLAMA_API_URL, json=payload).json()
    insight = response['message']['content']
    chat_hist.append({"role":"assistant","content":insight})
    return chat_hist,insight

# Define database query function. This function took sql query and outputs the resulting query.
def query_database(sql_query):
    # Endpoint for query middleware
    API_URL = "http://127.0.0.1:8000/query"
    response = requests.post(API_URL, json={"query": sql_query})
    return response.json()

# Run initial setup
print("Initialize model...")
chat_hist = initial_setup()

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
    chat_hist, sql_query = generate_sql_query(chat_hist,naturalQuery) 
    if sql_query=="No SQL query detected":
        print('Query Generation Failed.')
        naturalQuery=input("Please try again using more precise language: ")
        naturalQuery=f'''The previous question doesn't generate sql statement.
        Here is the new question: {naturalQuery}'''
    else:
        # Query database from the generated query
        query_result = query_database(sql_query)
        if 'detail' in query_result:
            print(sql_query)
            print(f"Query invalid: {query_result['detail']}")
            naturalQuery=input("Please refine te prompt using more domain specific language: ")
            continue
        else:
            print(sql_query)
            print(query_result) 
            chat_hist, insight = generate_insight(chat_hist,naturalQuery,sql_query,query_result)
            print(insight)
            print("***********")
    run = input("Do you want to continue? [Y/n]: ").upper()
    finish = True