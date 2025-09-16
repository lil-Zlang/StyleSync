"""
Strands Agent Logic for Style Weaver

This module contains the core agent logic that orchestrates:
1. Trend analysis from Neo4j knowledge graph
2. Wardrobe matching from Weaviate vector database
3. Image generation using Gemini API
"""

import os
import asyncio
from typing import Dict, List, Any, Optional
import logging
from dotenv import load_dotenv

# Database and AI imports
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

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
if genai:
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if gemini_api_key and gemini_api_key != 'YOUR_GEMINI_API_KEY':
        genai.configure(api_key=gemini_api_key)
        logger.info("Gemini API configured successfully")
    else:
        logger.warning("Gemini API key not configured")


async def generate_style_board(trend_name: str) -> Dict[str, Any]:
    """
    Main Strands Agent function that orchestrates the complete style generation process.
    
    This function:
    1. Queries Neo4j for trend DNA (garments and vibes)
    2. Uses semantic search in Weaviate to find matching clothes
    3. Generates a magazine-style outfit image using Gemini
    4. Returns a complete style board with all components
    
    Args:
        trend_name (str): The name of the fashion trend to generate a style for
        
    Returns:
        Dict[str, Any]: Complete style board with generated image and outfit details
    """
    logger.info(f"🎨 Starting style board generation for trend: {trend_name}")
    
    try:
        # Step 1: Query Neo4j for the Trend's DNA
        logger.info("Step 1: Analyzing trend DNA from Neo4j...")
        trend_dna = await _query_trend_dna(trend_name)
        
        if not trend_dna:
            return {
                "success": False,
                "error": f"Trend '{trend_name}' not found in knowledge graph",
                "message": "Please check the trend name and try again"
            }
        
        # Step 2: Query Weaviate for Matching Clothes
        logger.info("Step 2: Finding matching clothes from wardrobe...")
        outfit_items = await _find_matching_clothes(trend_dna)
        
        if not outfit_items:
            return {
                "success": False,
                "error": "No matching clothes found in wardrobe",
                "message": "Your wardrobe doesn't have items matching this trend"
            }
        
        # Step 3: Generate the Final Image with Gemini
        logger.info("Step 3: Generating outfit image with Gemini...")
        generated_image_url = await _generate_outfit_image(outfit_items, trend_dna)
        
        # Step 4: Return the Final Payload
        result = {
            "success": True,
            "trend": trend_name,
            "generated_image_url": generated_image_url,
            "outfit_items": outfit_items,
            "trend_dna": trend_dna,
            "message": f"Successfully generated style board for {trend_name}"
        }
        
        logger.info(f"✅ Style board generation completed for {trend_name}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Style board generation failed for {trend_name}: {str(e)}")
        return {
            "success": False,
            "trend": trend_name,
            "error": str(e),
            "message": "Style board generation failed"
        }


async def _query_trend_dna(trend_name: str) -> Optional[Dict[str, Any]]:
    """
    Step 1: Query Neo4j for the trend's DNA (garments and vibes).
    
    Args:
        trend_name (str): Name of the trend to analyze
        
    Returns:
        Optional[Dict[str, Any]]: Trend DNA with garments and vibes, or None if not found
    """
    if GraphDatabase is None:
        logger.error("Neo4j client library not available")
        return None
    
    try:
        # Connect to Neo4j
        neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD', 'your_password')
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        with driver.session() as session:
            # Cypher query to get trend's garments and vibes
            query = """
            MATCH (t:Trend {name: $trend_name})-[:CONSISTS_OF]->(g:Garment),
                  (t)-[:HAS_VIBE]->(v:Vibe)
            RETURN collect(DISTINCT g.name) as garments, 
                   collect(DISTINCT v.name) as vibes
            """
            
            result = session.run(query, trend_name=trend_name)
            record = result.single()
            
            if record and (record["garments"] or record["vibes"]):
                trend_dna = {
                    "trend_name": trend_name,
                    "garments": record["garments"],
                    "vibes": record["vibes"]
                }
                logger.info(f"Found trend DNA: {len(record['garments'])} garments, {len(record['vibes'])} vibes")
                return trend_dna
            else:
                logger.warning(f"No trend data found for: {trend_name}")
                return None
                
        driver.close()
        
    except Exception as e:
        logger.error(f"Failed to query trend DNA: {str(e)}")
        return None


async def _find_matching_clothes(trend_dna: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Step 2: Query Weaviate for clothes matching the trend DNA.
    
    Args:
        trend_dna (Dict[str, Any]): Trend DNA with garments and vibes
        
    Returns:
        List[Dict[str, Any]]: List of matching clothing items
    """
    if weaviate is None:
        logger.error("Weaviate client library not available")
        return []
    
    try:
        # Connect to Weaviate
        weaviate_url = os.getenv('WEAVIATE_URL', 'http://localhost:8080')
        weaviate_api_key = os.getenv('WEAVIATE_API_KEY')
        
        if weaviate_api_key:
            auth_config = AuthApiKey(api_key=weaviate_api_key)
            client = weaviate.Client(
                url=weaviate_url,
                auth_client_secret=auth_config
            )
        else:
            client = weaviate.Client(url=weaviate_url)
        
        if not client.is_ready():
            logger.error("Weaviate client is not ready")
            return []
        
        # Create descriptive search string from trend DNA
        garments_str = ", ".join(trend_dna["garments"])
        vibes_str = ", ".join(trend_dna["vibes"])
        search_concept = f"An outfit with a vibe of {vibes_str}, featuring {garments_str}"
        
        logger.info(f"Searching for clothes with concept: {search_concept}")
        
        outfit_items = []
        
        # Find best matching top
        top_query = (
            client.query
            .get("ClothingItem", ["item_id", "description", "image_url", "type", "style_tags"])
            .with_near_text({"concepts": [search_concept]})
            .with_where({
                "path": ["type"],
                "operator": "Equal",
                "valueText": "top"
            })
            .with_limit(1)
        )
        
        top_result = top_query.do()
        if top_result["data"]["Get"]["ClothingItem"]:
            top_item = top_result["data"]["Get"]["ClothingItem"][0]
            outfit_items.append({
                "item_id": top_item["item_id"],
                "description": top_item["description"],
                "image_url": top_item["image_url"],
                "type": top_item["type"],
                "style_tags": top_item["style_tags"]
            })
            logger.info(f"Found matching top: {top_item['description']}")
        
        # Find best matching bottom
        bottom_query = (
            client.query
            .get("ClothingItem", ["item_id", "description", "image_url", "type", "style_tags"])
            .with_near_text({"concepts": [search_concept]})
            .with_where({
                "path": ["type"],
                "operator": "Equal",
                "valueText": "bottom"
            })
            .with_limit(1)
        )
        
        bottom_result = bottom_query.do()
        if bottom_result["data"]["Get"]["ClothingItem"]:
            bottom_item = bottom_result["data"]["Get"]["ClothingItem"][0]
            outfit_items.append({
                "item_id": bottom_item["item_id"],
                "description": bottom_item["description"],
                "image_url": bottom_item["image_url"],
                "type": bottom_item["type"],
                "style_tags": bottom_item["style_tags"]
            })
            logger.info(f"Found matching bottom: {bottom_item['description']}")
        
        return outfit_items
        
    except Exception as e:
        logger.error(f"Failed to find matching clothes: {str(e)}")
        return []


async def _generate_outfit_image(outfit_items: List[Dict[str, Any]], trend_dna: Dict[str, Any]) -> Optional[str]:
    """
    Step 3: Generate a magazine-style outfit image using Gemini.
    
    Args:
        outfit_items (List[Dict[str, Any]]): Selected outfit items
        trend_dna (Dict[str, Any]): Trend DNA for context
        
    Returns:
        Optional[str]: URL of generated image, or None if failed
    """
    if genai is None:
        logger.error("Google Generative AI library not available")
        return None
    
    if not outfit_items:
        logger.warning("No outfit items provided for image generation")
        return None
    
    try:
        # Extract descriptions for prompt
        top_description = "a stylish top"
        bottom_description = "matching bottoms"
        
        for item in outfit_items:
            if item["type"] == "top":
                top_description = item["description"]
            elif item["type"] == "bottom":
                bottom_description = item["description"]
        
        # Create vibes string
        vibes_string = ", ".join(trend_dna["vibes"])
        
        # Craft the prompt for Gemini
        prompt = f"""Create a high-quality, product photography flat lay of a stylish outfit on a clean, neutral background (like light gray wood or marble). The outfit should look like it's from a fashion blog or magazine. 

The outfit consists of:
- {top_description}
- {bottom_description}

The overall style should be {vibes_string}. 

The image should be:
- Professional product photography quality
- Clean, minimalist composition
- Well-lit with soft shadows
- Items arranged aesthetically as a flat lay
- Background should be neutral (light gray, white, or natural wood)
- Style should convey the {trend_dna['trend_name']} trend aesthetic

Make it look like a high-end fashion blog or magazine feature."""
        
        logger.info("Generating image with Gemini...")
        logger.debug(f"Prompt: {prompt}")
        
        # Generate image using Gemini
        model = genai.GenerativeModel('gemini-pro-vision')  # or appropriate model
        
        # Note: This is a placeholder for image generation
        # The actual Gemini API for image generation might have different syntax
        # For now, we'll return a placeholder URL
        logger.warning("Gemini image generation not fully implemented - returning placeholder")
        
        # TODO: Implement actual Gemini image generation
        # response = model.generate_content(prompt)
        # return response.image_url if hasattr(response, 'image_url') else None
        
        return "https://via.placeholder.com/400x600/f8f9fa/333333?text=Generated+Outfit+Image"
        
    except Exception as e:
        logger.error(f"Failed to generate outfit image: {str(e)}")
        return None


# Legacy class for backward compatibility
class StyleWeaverAgent:
    """
    Legacy StyleWeaverAgent class for backward compatibility.
    New implementations should use the generate_style_board function directly.
    """
    
    def __init__(self):
        """Initialize the Style Weaver Agent."""
        logger.info("StyleWeaverAgent initialized (legacy mode)")
    
    def initialize_connections(self) -> bool:
        """Initialize connections - always returns True in new implementation."""
        return True
    
    def weave_style(self, trend_name: str) -> Dict[str, Any]:
        """
        Legacy wrapper for the new generate_style_board function.
        
        Args:
            trend_name (str): The trend to weave into an outfit
            
        Returns:
            Dict[str, Any]: Complete styling result
        """
        try:
            # Run the async function in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(generate_style_board(trend_name))
            loop.close()
            
            # Transform result to match legacy format
            if result["success"]:
                return {
                    "success": True,
                    "trend": trend_name,
                    "trend_analysis": result.get("trend_dna", {}),
                    "selected_items": result.get("outfit_items", []),
                    "outfit_image": result.get("generated_image_url"),
                    "message": result.get("message", "Style generated successfully")
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Legacy style weaving failed: {str(e)}")
            return {
                "success": False,
                "trend": trend_name,
                "error": str(e),
                "message": "Style weaving failed"
            }
