#!/usr/bin/env python3
"""
MongoDB Migration and Setup Script for BlogGraph-AI
This script sets up MongoDB and verifies the connection.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from topic_selection import mongo_db
import config

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def setup_mongodb():
    """Initialize MongoDB connection and collections."""
    print_header("MongoDB Setup & Verification")
    
    print("\n1. Connecting to MongoDB...")
    try:
        client = mongo_db.get_mongo_client()
        print(f"   ✓ Connected to {os.getenv('MONGODB_URI', 'mongodb://localhost:27017')}")
    except Exception as e:
        print(f"   ✗ Failed to connect: {e}")
        print("\n   MongoDB Setup Instructions:")
        print("   - Windows: choco install mongodb-community")
        print("   - macOS: brew install mongodb-community")
        print("   - Linux: sudo apt-get install mongodb")
        print("   - Docker: docker run -d -p 27017:27017 mongo:latest")
        return False
    
    print("\n2. Initializing database and indexes...")
    try:
        mongo_db.init_db()
        print("   ✓ Database initialized")
    except Exception as e:
        print(f"   ✗ Database initialization failed: {e}")
        return False
    
    print("\n3. Verifying collections...")
    try:
        db = mongo_db.get_db()
        collections = db.list_collection_names()
        if mongo_db.MONGODB_COLLECTION_TOPICS in collections:
            print(f"   ✓ Collection '{mongo_db.MONGODB_COLLECTION_TOPICS}' exists")
        else:
            print(f"   ⚠ Collection '{mongo_db.MONGODB_COLLECTION_TOPICS}' not found")
    except Exception as e:
        print(f"   ✗ Collection verification failed: {e}")
        return False
    
    print("\n4. Checking document count...")
    try:
        db = mongo_db.get_db()
        collection = db[mongo_db.MONGODB_COLLECTION_TOPICS]
        count = collection.count_documents({})
        print(f"   ✓ Total documents: {count}")
        
        if count == 0:
            print("   → Database is empty. Will seed on first pipeline run.")
    except Exception as e:
        print(f"   ✗ Document count check failed: {e}")
        return False
    
    print("\n5. Verifying indexes...")
    try:
        collection = db[mongo_db.MONGODB_COLLECTION_TOPICS]
        indexes = collection.list_indexes()
        index_names = [idx['name'] for idx in indexes]
        print("   ✓ Indexes created:")
        for idx_name in index_names:
            if idx_name != '_id_':
                print(f"     - {idx_name}")
    except Exception as e:
        print(f"   ✗ Index verification failed: {e}")
        return False
    
    return True


def print_config_info():
    """Display configuration information."""
    print_header("Configuration Summary")
    
    print(f"\n   MongoDB URI:      {os.getenv('MONGODB_URI', 'mongodb://localhost:27017')}")
    print(f"   Database:         {mongo_db.MONGODB_DATABASE}")
    print(f"   Collection:       {mongo_db.MONGODB_COLLECTION_TOPICS}")
    print(f"\n   Categories ({len(config.CATEGORIES)}):")
    for i, cat in enumerate(config.CATEGORIES, 1):
        print(f"     {i:2d}. {cat}")
    
    print(f"\n   Retry Caps:")
    for key, val in getattr(config, 'RETRY_CAPS', {}).items():
        print(f"     - {key}: {val} attempts")


def print_next_steps():
    """Display next steps after setup."""
    print_header("Next Steps")
    
    print("\n✓ MongoDB is ready! You can now run:")
    print("\n   1. Start the pipeline:")
    print("      python run.py")
    print("\n   2. Or start the web dashboard:")
    print("      python main.py")
    print("      → Open http://127.0.0.1:8000/dashboard")
    print("\n   3. To migrate from SQLite (if you have existing data):")
    print("      python scripts/migrate_sqlite_to_mongodb.py")


if __name__ == "__main__":
    print("\n" + "█"*60)
    print("█  BlogGraph-AI: MongoDB Setup Script")
    print("█"*60)
    
    # Check environment
    print("\nChecking environment...")
    env_file = Path(".env")
    if not env_file.exists():
        print("   ⚠ .env file not found. Using .env.example defaults.")
    else:
        print("   ✓ .env file loaded")
    
    # Setup MongoDB
    if setup_mongodb():
        print_config_info()
        print_next_steps()
        print("\n" + "█"*60)
        print("█  Setup Complete! 🎉")
        print("█"*60 + "\n")
        sys.exit(0)
    else:
        print("\n" + "█"*60)
        print("█  Setup Failed! ❌")
        print("█"*60 + "\n")
        sys.exit(1)
