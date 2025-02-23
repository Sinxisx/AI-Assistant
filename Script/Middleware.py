from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Database Config
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "port": os.getenv("DB_PORT"),
}

# Database Connection
async def get_db():
    return await asyncpg.create_pool(**DB_CONFIG)

@app.on_event("startup")
async def startup():
    app.state.db_pool = await asyncpg.create_pool(**DB_CONFIG)

@app.on_event("shutdown")
async def shutdown():
    await app.state.db_pool.close()

async def get_connection():
    async with app.state.db_pool.acquire() as connection:
        yield connection

# Define a Pydantic Model for API Requests
class QueryRequest(BaseModel):
    query: str

# Updated FastAPI Route with Correct Parsing
@app.post("/query")
async def query_db(request: QueryRequest, conn=Depends(get_connection)):
    try:
        sql_query = request.query.strip()
        if "select" in sql_query:
            results = await conn.fetch(sql_query)
            return {"data": [dict(row) for row in results]}
        else:
            await conn.execute(sql_query)
            return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
