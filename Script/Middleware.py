from fastapi import FastAPI, HTTPException, Depends
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "port": os.getenv("DB_PORT"),
}

# Create a connection pool
async def get_db():
    return await asyncpg.create_pool(**DB_CONFIG)

@app.on_event("startup")
async def startup():
    app.state.db_pool = await asyncpg.create_pool(**DB_CONFIG)

@app.on_event("shutdown")
async def shutdown():
    await app.state.db_pool.close()

# Dependency for database connection
async def get_connection():
    async with app.state.db_pool.acquire() as connection:
        yield connection

# Route to execute SQL queries
@app.post("/query")
async def query_db(query: str, conn=Depends(get_connection)):
    try:
        query = query.strip().lower()

        if "select" in query:
            results = await conn.fetch(query)
            return {"data": [dict(row) for row in results]}
        else:
            await conn.execute(query)
            return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Run the API with:
# uvicorn main:app --reload
