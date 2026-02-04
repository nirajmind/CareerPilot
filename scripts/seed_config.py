
import os
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# ------------------------------------------------------------------------------
# Configuration Seader Script
# ------------------------------------------------------------------------------
# Usage: 
#   export MONGO_URI="mongodb://user:pass@host:port/db"
#   python scripts/seed_config.py
# ------------------------------------------------------------------------------

def get_mongo_client():
    """Connect to MongoDB using environment variable."""
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("❌ Error: MONGO_URI environment variable is not set.")
        print("Usage: export MONGO_URI='mongodb://...'; python scripts/seed_config.py")
        sys.exit(1)

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # Verify connection
        client.admin.command('ismaster')
        print(f"✅ Connected to MongoDB at: {mongo_uri.split('@')[-1]}") # Mask credentials
        return client
    except ConnectionFailure as e:
        print(f"❌ Could not connect to MongoDB: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error connecting to MongoDB: {e}")
        sys.exit(1)

def seed_config(client):
    """Insert or update configuration documents."""
    db = client.get_database("careerpilot") # Assuming database name is fixed
    collection = db.system_config

    # --- CONFIGURATION DATA (PLACEHOLDERS) ---
    # REPLACE THESE VALUES WITH YOUR ACTUAL CONSTANTS BEFORE RUNNING
    
    # 1. Quota Configuration
    quota_config = {
        "_id": "quota",
        "free_tier_daily_limit": 5,      # Default: 5
        "premium_tier_daily_limit": 100  # Default: 100
    }

    # 2. Gemini Models Configuration
    gemini_config = {
        "_id": "gemini",
        "gemini_model": "v1beta/models/gemini-3-pro-preview",         # Placeholder
        "gemini_vision_model": "v1beta/models/gemini-3-pro-preview",   # Placeholder
        "gemini_embedding_model": "v1/models/text-embedding-004"     # Placeholder (Optional)
    }

    # 3. Stripe Configuration (Optional keys if you added them to dynamic loading)
    # Based on server.py inspection, currently only Quota and Gemini are actively loaded.
    # You can add others here if you expand the loading logic in server.py.

    configs_to_seed = [quota_config, gemini_config]

    print("\n--- Seeding Configuration ---")
    for config in configs_to_seed:
        config_id = config["_id"]
        try:
            # Upsert: Update if exists, Insert if not
            result = collection.update_one(
                {"_id": config_id},
                {"$set": config},
                upsert=True
            )
            
            if result.upserted_id:
                print(f"✅ Inserted new config: '{config_id}'")
            elif result.modified_count > 0:
                print(f"✅ Updated existing config: '{config_id}'")
            else:
                print(f"ℹ️  Config '{config_id}' is already up to date.")
                
        except OperationFailure as e:
            print(f"❌ Failed to seed '{config_id}': {e}")
        except Exception as e:
            print(f"❌ Unexpected error seeding '{config_id}': {e}")

    print("\n✅ Seeding complete.")

if __name__ == "__main__":
    client = get_mongo_client()
    seed_config(client)
    client.close()
