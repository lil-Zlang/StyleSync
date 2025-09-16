#!/usr/bin/env python3
"""
Test Weaviate Connection and Display Clothing Items
"""

import weaviate
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_weaviate_connection():
    """Test Weaviate connection and display clothing items"""
    print("🔍 Testing Weaviate Connection...")
    print("=" * 50)
    
    try:
        # Get configuration from environment
        weaviate_url = os.getenv('WEAVIATE_URL', 'http://localhost:8080')
        weaviate_api_key = os.getenv('WEAVIATE_API_KEY')
        weaviate_hostname = os.getenv('WEAVIATE_HOSTNAME')
        
        print(f"📡 Weaviate URL: {weaviate_url}")
        print(f"🔐 API Key configured: {'Yes' if weaviate_api_key else 'No'}")
        print(f"🌐 Hostname: {weaviate_hostname if weaviate_hostname else 'Not set'}")
        print()
        
        # Create Weaviate client
        if weaviate_api_key and weaviate_hostname:
            # Cloud configuration
            print("☁️ Connecting to Weaviate Cloud...")
            client = weaviate.Client(
                url=f"https://{weaviate_hostname}",
                auth_client_secret=weaviate.AuthApiKey(api_key=weaviate_api_key)
            )
        else:
            # Local configuration
            print("🏠 Connecting to Local Weaviate...")
            client = weaviate.Client(url=weaviate_url)
        
        # Test connection
        if client.is_ready():
            print("✅ Weaviate is ready and connected!")
            print()
            
            # Get schema information
            schema = client.schema.get()
            classes = schema.get('classes', [])
            clothing_class = next((cls for cls in classes if cls['class'] == 'ClothingItem'), None)
            
            if clothing_class:
                print("✅ ClothingItem class exists!")
                print(f"📊 Properties: {[prop['name'] for prop in clothing_class.get('properties', [])]}")
                print()
                
                # Query clothing items
                print("👕 Fetching clothing items from database...")
                print("-" * 50)
                
                result = client.query.get(
                    "ClothingItem", 
                    ["item_id", "description", "image_url", "type", "style_tags"]
                ).with_limit(10).do()
                
                # Display results
                if result and 'data' in result and 'Get' in result['data'] and 'ClothingItem' in result['data']['Get']:
                    items = result['data']['Get']['ClothingItem']
                    print(f"📦 Found {len(items)} clothing items:")
                    print()
                    
                    for i, item in enumerate(items, 1):
                        print(f"🔹 Item {i}:")
                        print(f"   ID: {item.get('item_id', 'N/A')}")
                        print(f"   Type: {item.get('type', 'N/A')}")
                        print(f"   Description: {item.get('description', 'N/A')}")
                        print(f"   Image URL: {item.get('image_url', 'N/A')}")
                        print(f"   Style Tags: {item.get('style_tags', [])}")
                        print()
                    
                    # Pretty print JSON for verification
                    print("📋 JSON Output:")
                    print(json.dumps(result, indent=2))
                    
                else:
                    print("❌ No clothing items found in database!")
                    print("🔧 You may need to run the database seeding script:")
                    print("   python seed_databases.py")
                    
            else:
                print("❌ ClothingItem class doesn't exist!")
                print("🔧 Available classes:", [cls['class'] for cls in classes])
                print("🔧 You need to run the database seeding script:")
                print("   python seed_databases.py")
                
        else:
            print("❌ Weaviate is not ready!")
            print("🔧 Make sure Weaviate is running and accessible")
            
    except Exception as e:
        print(f"💥 Error connecting to Weaviate: {str(e)}")
        print("🔧 Troubleshooting:")
        print("   1. Check if Weaviate is running")
        print("   2. Verify your .env file configuration")
        print("   3. Make sure you have the weaviate-client library installed:")
        print("      pip install weaviate-client")

if __name__ == "__main__":
    test_weaviate_connection()

