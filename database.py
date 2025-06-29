from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
import os
from typing import Optional

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb+srv://vickykumar776655:ztpFeM5U1TdLinoT@feedback.c8anxdj.mongodb.net/?retryWrites=true&w=majority&appName=Feedback")
DATABASE_NAME = "feedback_system"

client: Optional[AsyncIOMotorClient] = None
database = None

async def init_db():
    global client, database
    client = AsyncIOMotorClient(MONGODB_URL, server_api=ServerApi('1'))
    database = client[DATABASE_NAME]
    
    await create_indexes()
    print("Database connected successfully")

async def create_indexes():
    await database.users.create_index("email", unique=True)
    await database.users.create_index("employee_id", unique=True)
    
    await database.feedback.create_index([("employee_id", 1), ("created_at", -1)])
    await database.feedback.create_index("manager_id")
    
    await database.forms.create_index("manager_id")

async def get_database():
    return database

async def close_db():
    if client:
        client.close()
