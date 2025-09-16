"""
Database Seeder for Style Weaver

This module contains functions to seed both Neo4j and Weaviate databases
with initial data for testing and demonstration purposes.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Database imports
try:
    import weaviate
    from weaviate.auth import AuthApiKey
except ImportError:
    weaviate = None
    AuthApiKey = None

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_weaviate() -> bool:
    """
    Seed Weaviate with sample wardrobe items and their vector representations.
    
    Returns:
        bool: True if seeding successful, False otherwise
    """
    logger.info("Starting Weaviate seeding...")
    
    # Check if Weaviate is available
    if weaviate is None:
        logger.error("Weaviate client library not installed. Run: pip install weaviate-client")
        return False
    
    try:
        # Sample wardrobe data as specified
        sample_wardrobe = [
            {
                "item_id": "top_01", 
                "image_url": "https://raw.githubusercontent.com/lil-Zlang/StyleSync/main/assets/white_tee.jpg", 
                "description": "A classic white cotton crewneck t-shirt.", 
                "type": "top", 
                "style_tags": ["casual", "basic", "minimalist"]
            },
            {
                "item_id": "top_02", 
                "image_url": "https://raw.githubusercontent.com/lil-Zlang/StyleSync/main/assets/black_hoodie.jpg", 
                "description": "A comfortable black oversized hoodie.", 
                "type": "top", 
                "style_tags": ["streetwear", "casual", "cozy"]
            },
            {
                "item_id": "bottom_01", 
                "image_url": "https://raw.githubusercontent.com/lil-Zlang/StyleSync/main/assets/blue_jeans.jpg", 
                "description": "Dark wash slim-fit denim jeans.", 
                "type": "bottom", 
                "style_tags": ["casual", "classic", "streetwear"]
            },
            {
                "item_id": "bottom_02", 
                "image_url": "https://raw.githubusercontent.com/lil-Zlang/StyleSync/main/assets/khaki_chinos.jpg", 
                "description": "Light brown khaki chinos.", 
                "type": "bottom", 
                "style_tags": ["business-casual", "preppy"]
            },
                {
                "item_id": "top_03", 
                "image_url": "https://raw.githubusercontent.com/lil-Zlang/StyleSync/main/assets/hacker_tee.jpg", 
                "description": "hacker tee.", 
                "type": "top", 
                "style_tags": ["hackers-casual", "cozy"]
            }
        ]
        
        # Connect to Weaviate
        weaviate_url = os.getenv('WEAVIATE_URL', 'http://localhost:8080')
        weaviate_api_key = os.getenv('WEAVIATE_API_KEY')
        
        # Create Weaviate client
        if weaviate_api_key:
            auth_config = AuthApiKey(api_key=weaviate_api_key)
            client = weaviate.Client(
                url=weaviate_url,
                auth_client_secret=auth_config
            )
        else:
            client = weaviate.Client(url=weaviate_url)
        
        logger.info(f"Connected to Weaviate at {weaviate_url}")
        
        # Check if client is ready
        if not client.is_ready():
            logger.error("Weaviate client is not ready")
            return False
        
        # Define ClothingItem class schema
        clothing_item_schema = {
            "class": "ClothingItem",
            "description": "A clothing item in the user's wardrobe",
            "vectorizer": "text2vec-transformers",
            "moduleConfig": {
                "text2vec-transformers": {
                    "poolingStrategy": "masked_mean",
                    "vectorizeClassName": False
                }
            },
            "properties": [
                {
                    "name": "item_id",
                    "dataType": ["text"],
                    "description": "Unique identifier for the clothing item",
                    "moduleConfig": {
                        "text2vec-transformers": {
                            "skip": True,
                            "vectorizePropertyName": False
                        }
                    }
                },
                {
                    "name": "image_url",
                    "dataType": ["text"],
                    "description": "URL to the clothing item image",
                    "moduleConfig": {
                        "text2vec-transformers": {
                            "skip": True,
                            "vectorizePropertyName": False
                        }
                    }
                },
                {
                    "name": "description",
                    "dataType": ["text"],
                    "description": "Detailed description of the clothing item",
                    "moduleConfig": {
                        "text2vec-transformers": {
                            "skip": False,
                            "vectorizePropertyName": False
                        }
                    }
                },
                {
                    "name": "type",
                    "dataType": ["text"],
                    "description": "Type of clothing (top, bottom, outerwear, etc.)",
                    "moduleConfig": {
                        "text2vec-transformers": {
                            "skip": False,
                            "vectorizePropertyName": False
                        }
                    }
                },
                {
                    "name": "style_tags",
                    "dataType": ["text[]"],
                    "description": "Style tags associated with the item",
                    "moduleConfig": {
                        "text2vec-transformers": {
                            "skip": False,
                            "vectorizePropertyName": False
                        }
                    }
                }
            ]
        }
        
        # Clear existing data to ensure fresh start
        try:
            if client.schema.exists("ClothingItem"):
                logger.info("Deleting existing ClothingItem class...")
                client.schema.delete_class("ClothingItem")
        except Exception as e:
            logger.warning(f"Could not delete existing class: {str(e)}")
        
        # Create the schema
        logger.info("Creating ClothingItem class schema...")
        client.schema.create_class(clothing_item_schema)
        
        # Add wardrobe items to Weaviate
        logger.info("Adding wardrobe items to Weaviate...")
        
        with client.batch as batch:
            batch.batch_size = 100
            batch.dynamic = True
            
            for item in sample_wardrobe:
                # Create vector-friendly text from description and style tags
                vectorize_text = f"{item['description']} {' '.join(item['style_tags'])}"
                
                properties = {
                    "item_id": item["item_id"],
                    "image_url": item["image_url"],
                    "description": item["description"],
                    "type": item["type"],
                    "style_tags": item["style_tags"]
                }
                
                batch.add_data_object(
                    data_object=properties,
                    class_name="ClothingItem"
                )
                
                logger.info(f"Added item: {item['item_id']} - {item['description']}")
        
        # Verify the data was added
        result = client.query.aggregate("ClothingItem").with_meta_count().do()
        item_count = result["data"]["Aggregate"]["ClothingItem"][0]["meta"]["count"]
        logger.info(f"Successfully added {item_count} clothing items to Weaviate")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to seed Weaviate: {str(e)}")
        return False


def seed_neo4j() -> bool:
    """
    Seed Neo4j with fashion trend data and relationships.
    
    Returns:
        bool: True if seeding successful, False otherwise
    """
    logger.info("Starting Neo4j seeding...")
    
    # Check if Neo4j is available
    if GraphDatabase is None:
        logger.error("Neo4j client library not installed. Run: pip install neo4j")
        return False
    
    try:
        # Fashion trends data as specified
        fashion_trends = {
            "90s Revival": {
                "garments": ["denim jeans", "graphic t-shirt", "oversized hoodie"],
                "vibes": ["grunge", "casual", "streetwear", "nostalgic"]
            },
            "Minimalist Chic": {
                "garments": ["crewneck t-shirt", "chinos", "blazer"],
                "vibes": ["clean", "simple", "professional", "timeless"]
            }
        }
        
        # Connect to Neo4j
        neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD', 'your_password')
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        logger.info(f"Connected to Neo4j at {neo4j_uri}")
        
        with driver.session() as session:
            # Clear the database for a fresh start
            logger.info("Clearing existing Neo4j data...")
            session.run("MATCH (n) DETACH DELETE n")
            
            # Process each fashion trend
            for trend_name, trend_data in fashion_trends.items():
                logger.info(f"Creating trend: {trend_name}")
                
                # Create trend node
                session.run(
                    "CREATE (t:Trend {name: $trend_name})",
                    trend_name=trend_name
                )
                
                # Create garment nodes and relationships
                for garment in trend_data["garments"]:
                    session.run("""
                        MATCH (t:Trend {name: $trend_name})
                        MERGE (g:Garment {name: $garment_name})
                        CREATE (t)-[:CONSISTS_OF]->(g)
                    """, trend_name=trend_name, garment_name=garment)
                    logger.info(f"  Added garment: {garment}")
                
                # Create vibe nodes and relationships
                for vibe in trend_data["vibes"]:
                    session.run("""
                        MATCH (t:Trend {name: $trend_name})
                        MERGE (v:Vibe {name: $vibe_name})
                        CREATE (t)-[:HAS_VIBE]->(v)
                    """, trend_name=trend_name, vibe_name=vibe)
                    logger.info(f"  Added vibe: {vibe}")
            
            # Verify the data was created
            result = session.run("MATCH (t:Trend) RETURN count(t) as trend_count")
            trend_count = result.single()["trend_count"]
            
            result = session.run("MATCH (g:Garment) RETURN count(g) as garment_count")
            garment_count = result.single()["garment_count"]
            
            result = session.run("MATCH (v:Vibe) RETURN count(v) as vibe_count")
            vibe_count = result.single()["vibe_count"]
            
            logger.info(f"Successfully created {trend_count} trends, {garment_count} garments, {vibe_count} vibes")
        
        driver.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to seed Neo4j: {str(e)}")
        return False


def main():
    """Main function to run database seeding."""
    print("🌱 Starting Style Weaver Database Seeding...")
    print("=" * 50)
    
    success = True
    
    # Seed Weaviate
    print("\n📦 Seeding Weaviate with wardrobe data...")
    if seed_weaviate():
        print("✅ Weaviate seeding completed successfully!")
    else:
        print("❌ Weaviate seeding failed!")
        success = False
    
    # Seed Neo4j
    print("\n🕸️  Seeding Neo4j with trend data...")
    if seed_neo4j():
        print("✅ Neo4j seeding completed successfully!")
    else:
        print("❌ Neo4j seeding failed!")
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All databases seeded successfully!")
        print("\nYou can now:")
        print("  - Query Weaviate for clothing items")
        print("  - Query Neo4j for fashion trends and relationships")
        print("  - Run the Style Weaver application!")
    else:
        print("💥 Database seeding failed. Check the logs above for details.")
        print("\nMake sure:")
        print("  - Weaviate is running on http://localhost:8080")
        print("  - Neo4j is running on bolt://localhost:7687")
        print("  - Your .env file has the correct credentials")


if __name__ == "__main__":
    main()
