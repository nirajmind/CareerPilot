import asyncio
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from app.utils.logger import setup_logger
import os
import time
from datetime import datetime

logger = setup_logger()

class MongoHandler:
    def __init__(self):
        self.client = None
        self.db = None

    def connect(self, retries=5, delay=5):
        """Connects to MongoDB synchronously with retries."""
        mongo_uri = os.getenv("MONGO_URI", "mongodb://mongo:27017/careerpilot")
        for i in range(retries):
            try:
                self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
                # The ismaster command is cheap and does not require auth.
                self.client.admin.command('ismaster')
                self.db = self.client.get_database("careerpilot")
                logger.info("Successfully connected to MongoDB.")
                return
            except ConnectionFailure as e:
                logger.error(f"Could not connect to MongoDB: {e}, retrying in {delay}s...")
                time.sleep(delay)
        
        logger.error("Failed to connect to MongoDB after multiple retries.")
        self.client = None
        self.db = None

    def close(self):
        """Closes the MongoDB connection synchronously."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")

    async def insert_log(self, log_data: dict):
        """Inserts a log document asynchronously using a thread."""
        if self.db is not None:
            def sync_insert():
                return self.db.logs.insert_one(log_data)
            result = await asyncio.to_thread(sync_insert)
            logger.info(f"Log inserted with id: {result.inserted_id}")
            return result
        return None

    async def insert_session(self, session_data: dict):
        """Inserts a session document asynchronously using a thread."""
        if self.db is not None:
            def sync_insert():
                return self.db.sessions.insert_one(session_data)
            result = await asyncio.to_thread(sync_insert)
            logger.info(f"Session inserted with id: {result.inserted_id}")
            return result
        return None

    async def get_user(self, username: str):
        """Retrieves a user from the database asynchronously."""
        if self.db is not None:
            def sync_find():
                return self.db.users.find_one({"username": username})
            user = await asyncio.to_thread(sync_find)
            return user
        return None

    async def create_user(self, user_data: dict):
        """Creates a new user in the database asynchronously."""
        if self.db is not None:
            def sync_insert():
                return self.db.users.insert_one(user_data)
            result = await asyncio.to_thread(sync_insert)
            logger.info(f"User created with id: {result.inserted_id}")
            return result
        return None

    async def update_user_password(self, username: str, hashed_password: str):
        """Update user password (already hashed by caller)."""
        if self.db is not None:
            def sync_update():
                return self.db.users.update_one(
                    {"username": username},
                    {
                        "$set": {
                            "password_hash": hashed_password,
                            "updated_at": datetime.now(),
                        }
                    }
                )
            result = await asyncio.to_thread(sync_update)
            logger.info(f"Password updated for user '{username}'")
            return result
        return None

    async def set_user_premium(self, username: str):
        """Mark user as premium (after Stripe payment)."""
        if self.db is not None:
            def sync_update():
                return self.db.users.update_one(
                    {"username": username},
                    {
                        "$set": {
                            "tier": "premium",
                            "updated_at": datetime.now(),
                        },
                        "$addToSet": {"roles": "premium"}
                    }
                )
            result = await asyncio.to_thread(sync_update)
            logger.info(f"User '{username}' upgraded to premium in MongoDB")
            return result
        return None

    async def get_user_by_email(self, email: str):
        """Retrieve user by email."""
        if self.db is not None:
            def sync_find():
                return self.db.users.find_one({"email": email})
            user = await asyncio.to_thread(sync_find)
            return user
        return None

    async def get_system_config(self) -> dict:
        """
        Retrieve system configuration from 'system_config' collection.
        Returns a dictionary merging all config documents (id is the key).
        Example doc: {"_id": "quota", "premium_limit": 500}
        """
        if self.db is not None:
            def sync_get_all():
                return list(self.db.system_config.find({}))
            
            docs = await asyncio.to_thread(sync_get_all)
            
            # Merge into a single dict: {"quota": {...}, "stripe": {...}}
            config_map = {}
            for doc in docs:
                key = doc.get("_id") # e.g., "quota", "gemini"
                if key:
                    config_map[key] = doc
            return config_map
        return {}

mongo_handler = MongoHandler()
