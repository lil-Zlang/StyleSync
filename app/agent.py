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
import base64
import io
from PIL import Image
import requests

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
        
        # Create keyword search terms from trend DNA
        garments = trend_dna["garments"]
        vibes = trend_dna["vibes"]
        
        logger.info(f"Searching for clothes matching garments: {garments} and vibes: {vibes}")
        
        outfit_items = []
        
        # Find best matching top based on keywords
        top_query = (
            client.query
            .get("ClothingItem", ["item_id", "description", "image_url", "type", "style_tags"])
            .with_where({
                "path": ["type"],
                "operator": "Equal",
                "valueText": "top"
            })
            .with_limit(10)  # Get more items to filter
        )
        
        top_result = top_query.do()
        if top_result["data"]["Get"]["ClothingItem"]:
            # Score tops based on keyword matches
            best_top = None
            best_score = 0
            
            for item in top_result["data"]["Get"]["ClothingItem"]:
                score = _calculate_match_score(item, garments, vibes)
                if score > best_score:
                    best_score = score
                    best_top = item
            
            if best_top:
                outfit_items.append({
                    "item_id": best_top["item_id"],
                    "description": best_top["description"],
                    "image_url": best_top["image_url"],
                    "type": best_top["type"],
                    "style_tags": best_top["style_tags"]
                })
                logger.info(f"Found matching top: {best_top['description']} (score: {best_score})")
        
        # Find best matching bottom based on keywords
        bottom_query = (
            client.query
            .get("ClothingItem", ["item_id", "description", "image_url", "type", "style_tags"])
            .with_where({
                "path": ["type"],
                "operator": "Equal",
                "valueText": "bottom"
            })
            .with_limit(10)  # Get more items to filter
        )
        
        bottom_result = bottom_query.do()
        if bottom_result["data"]["Get"]["ClothingItem"]:
            # Score bottoms based on keyword matches
            best_bottom = None
            best_score = 0
            
            for item in bottom_result["data"]["Get"]["ClothingItem"]:
                score = _calculate_match_score(item, garments, vibes)
                if score > best_score:
                    best_score = score
                    best_bottom = item
            
            if best_bottom:
                outfit_items.append({
                    "item_id": best_bottom["item_id"],
                    "description": best_bottom["description"],
                    "image_url": best_bottom["image_url"],
                    "type": best_bottom["type"],
                    "style_tags": best_bottom["style_tags"]
                })
                logger.info(f"Found matching bottom: {best_bottom['description']} (score: {best_score})")
        
        return outfit_items
        
    except Exception as e:
        logger.error(f"Failed to find matching clothes: {str(e)}")
        return []


def _calculate_match_score(item: Dict[str, Any], garments: List[str], vibes: List[str]) -> int:
    """
    Calculate a match score for a clothing item based on trend keywords.
    
    Args:
        item (Dict[str, Any]): Clothing item from Weaviate
        garments (List[str]): List of garment types from trend DNA
        vibes (List[str]): List of vibes from trend DNA
        
    Returns:
        int: Match score (higher is better)
    """
    score = 0
    description = item.get("description", "").lower()
    style_tags = [tag.lower() for tag in item.get("style_tags", [])]
    
    # Score based on garment type matches in description
    for garment in garments:
        garment_lower = garment.lower()
        if garment_lower in description:
            score += 5
        # Check for partial matches
        garment_words = garment_lower.split()
        for word in garment_words:
            if word in description:
                score += 2
    
    # Score based on vibe matches in style tags
    for vibe in vibes:
        vibe_lower = vibe.lower()
        if vibe_lower in style_tags:
            score += 3
        # Check for partial matches in description
        if vibe_lower in description:
            score += 2
    
    # Score based on style tag matches
    for tag in style_tags:
        for vibe in vibes:
            if vibe.lower() in tag:
                score += 2
    
    return score


async def generate_hacker_mode_image() -> Optional[str]:
    """
    Simple hacker mode function that combines hacker tee + model image using Gemini 2.5 Flash Image Preview.
    This follows the exact pattern from the user's example code.
    
    Returns:
        Optional[str]: Base64 encoded image of the final composition, or None if failed
    """
    try:
        from google import genai as new_genai
        from google.genai import types
        from PIL import Image
        from io import BytesIO
        
        logger.info("🎨 Starting Hacker Mode image generation...")
        
        # Initialize client
        client = new_genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        
        # Load local images
        hacker_tee_path = '/Users/langgui/Downloads/styleSync/assets/hacker_tee.jpg'
        model_path = '/Users/langgui/Downloads/styleSync/assets/model.png'
        
        logger.info(f"Loading hacker tee from: {hacker_tee_path}")
        logger.info(f"Loading model from: {model_path}")
        
        hacker_tee_image = Image.open(hacker_tee_path)
        model_image = Image.open(model_path)
        
        # Create the professional e-commerce fashion photo prompt (following user's example)
        text_input = """Create a professional e-commerce fashion photo. Take the hacker tee from the first image and let the person from the second image wear it. Generate a realistic, full-body shot of the person wearing the hacker tee, with the lighting and shadows adjusted to match the environment. Make it look like a professional fashion photograph."""
        
        logger.info("📤 Generating image with Gemini 2.5 Flash Image Preview...")
        
        # Generate image using exact API structure from user's example
        response = client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=[hacker_tee_image, model_image, text_input],
        )
        
        # Extract image parts (following user's example exactly)
        image_parts = [
            part.inline_data.data
            for part in response.candidates[0].content.parts
            if part.inline_data
        ]
        
        if image_parts:
            # Convert to base64 for frontend (following user's pattern)
            generated_image_data = base64.b64encode(image_parts[0]).decode('utf-8')
            logger.info("✅ Hacker Mode image generated successfully!")
            return f"data:image/png;base64,{generated_image_data}"
        else:
            logger.warning("No image data returned from Gemini")
            return None
            
    except Exception as e:
        logger.error(f"Hacker Mode image generation failed: {str(e)}")
        return None


async def _generate_outfit_image(outfit_items: List[Dict[str, Any]], trend_dna: Dict[str, Any]) -> Optional[str]:
    """
    Step 3: Use Gemini to analyze and combine clothing items onto the model image.
    
    Args:
        outfit_items (List[Dict[str, Any]]): Selected outfit items
        trend_dna (Dict[str, Any]): Trend DNA for context
        
    Returns:
        Optional[str]: Base64 encoded image of the generated outfit, or None if failed
    """
    if genai is None:
        logger.error("Google Generative AI library not available")
        return None
    
    # Special handling for Hacker Mode - use the simple implementation
    if trend_dna.get('trend_name') == 'Hacker Mode':
        logger.info("🎯 Using specialized Hacker Mode image generation...")
        hacker_image = await generate_hacker_mode_image()
        if hacker_image:
            return hacker_image
        else:
            logger.warning("Hacker Mode generation failed, falling back to general approach")
    
    if not outfit_items:
        logger.warning("No outfit items provided for image generation")
        return None
    
    try:
        # Load the base model image from GitHub
        model_image_url = "https://raw.githubusercontent.com/lil-Zlang/StyleSync/main/assets/model.png"
        logger.info(f"Loading base model image from: {model_image_url}")
        
        response = requests.get(model_image_url)
        if response.status_code != 200:
            logger.error(f"Failed to load model image: {response.status_code}")
            return None
        
        # Convert to base64 for Gemini
        model_image_b64 = base64.b64encode(response.content).decode('utf-8')
        
        # Extract descriptions for prompt
        top_description = "a stylish top"
        bottom_description = "matching bottoms"
        clothing_images = []
        
        for item in outfit_items:
            if item["type"] == "top":
                top_description = item["description"]
            elif item["type"] == "bottom":
                bottom_description = item["description"]
            
            # Try to load clothing item images
            if item.get("image_url"):
                try:
                    img_response = requests.get(item["image_url"])
                    if img_response.status_code == 200:
                        clothing_images.append({
                            "type": item["type"],
                            "description": item["description"],
                            "image_b64": base64.b64encode(img_response.content).decode('utf-8')
                        })
                except Exception as e:
                    logger.warning(f"Could not load clothing image: {e}")
        
        # Create vibes string
        vibes_string = ", ".join(trend_dna["vibes"])
        
        # Craft the prompt for Gemini to describe the outfit visualization
        prompt = f"""I have a base model image and need you to help me create a fashion outfit visualization. 

Based on this model and the following clothing items:
- {top_description}
- {bottom_description}

The style should embody: {vibes_string}

Please analyze the model image and describe exactly how these clothing items would look when worn by this model. Be specific about:
1. How the {top_description} would fit and look on this model
2. How the {bottom_description} would complement the top and fit the model
3. The overall aesthetic matching the {trend_dna['trend_name']} trend
4. Color coordination and styling details

Make your description vivid and detailed as if you're seeing the complete outfit on the model."""
        
        logger.info("Analyzing outfit combination with Gemini...")
        logger.debug(f"Prompt: {prompt}")
        
        # Use Gemini 2.5 Flash Image Preview for actual image generation (Advanced composition)
        try:
            logger.info("🎨 Generating new photo using Gemini 2.5 Flash Image Preview...")
            
            # Import both genai libraries at the top to avoid scope issues
            try:
                from google import genai as new_genai
                from google.genai import types
                new_api_available = True
            except ImportError:
                logger.warning("New google-genai library not available")
                new_api_available = False
            
            # Load clothing item images
            clothing_images = []
            for item in outfit_items:
                if item.get("image_url"):
                    try:
                        img_response = requests.get(item["image_url"])
                        if img_response.status_code == 200:
                            clothing_img = Image.open(io.BytesIO(img_response.content))
                            clothing_images.append({
                                "type": item["type"],
                                "description": item["description"],
                                "image": clothing_img
                            })
                    except Exception as e:
                        logger.warning(f"Could not load clothing image: {e}")
            
            # Create the composition prompt using the API documentation format
            composition_prompt = f"""Create a professional fashion photo. Take the clothing items from the provided images and let the person from the model image wear them. Generate a realistic, full-body shot of the person wearing:

- {top_description}
- {bottom_description}

Style: {trend_dna['trend_name']} with {vibes_string} vibes.

Generate a realistic photo where the person is naturally wearing these clothes, with proper lighting and shadows adjusted to match the environment. Make it look like a professional fashion photograph."""

            # Try using the new Gemini Client API structure if available
            if new_api_available:
                try:
                    logger.info("Trying new Google GenAI Client API...")
                    
                    # Initialize the new client (using exact API structure from documentation)
                    client = new_genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
                    
                    # Load model image as PIL Image
                    model_response = requests.get(model_image_url)
                    model_pil_image = Image.open(io.BytesIO(model_response.content))
                    
                    # General approach for all trends
                    content_list = [model_pil_image] + [c["image"] for c in clothing_images] + [composition_prompt]
                    
                    logger.info(f"📤 Sending {len(content_list)} items to Gemini 2.5 Flash Image Preview...")
                    
                    response = client.models.generate_content(
                        model="gemini-2.5-flash-image-preview",
                        contents=content_list,
                    )
                    
                    # Extract generated image
                    image_parts = [
                        part.inline_data.data
                        for part in response.candidates[0].content.parts
                        if part.inline_data
                    ]
                    
                    if image_parts:
                        # Convert to base64 for frontend
                        generated_image_data = base64.b64encode(image_parts[0]).decode('utf-8')
                        logger.info("✅ Successfully generated new photo with Gemini!")
                        return f"data:image/png;base64,{generated_image_data}"
                    
                    logger.warning("No image data returned from new API")
                    
                except Exception as new_api_error:
                    logger.warning(f"New Gemini Client API failed: {str(new_api_error)}")
            
            # Fallback to old API structure
            if genai is not None:
                try:
                    logger.info("Trying fallback with GenerativeModel API...")
                    image_model = genai.GenerativeModel('gemini-2.5-flash-image-preview')
                    
                    # Prepare content for old API
                    content_parts = [composition_prompt]
                    
                    # Add model image
                    content_parts.append({
                        "mime_type": "image/png",
                        "data": model_image_b64
                    })
                    
                    # Add clothing images
                    for clothing in clothing_images:
                        # Convert PIL image to base64
                        buffer = io.BytesIO()
                        clothing["image"].save(buffer, format='PNG')
                        clothing_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        
                        content_parts.append({
                            "mime_type": "image/png",
                            "data": clothing_b64
                        })
                    
                    response = image_model.generate_content(content_parts)
                    
                    # Check for generated image
                    if hasattr(response, 'candidates') and response.candidates:
                        for candidate in response.candidates:
                            if hasattr(candidate, 'content') and candidate.content.parts:
                                for part in candidate.content.parts:
                                    if hasattr(part, 'inline_data') and part.inline_data:
                                        generated_image_data = part.inline_data.data
                                        logger.info("✅ Generated image with fallback API!")
                                        return f"data:image/png;base64,{generated_image_data}"
                    
                    logger.warning("Fallback API also returned no image data")
                    
                except Exception as fallback_error:
                    logger.warning(f"Fallback API also failed: {str(fallback_error)}")
            
            # If image generation fails, create professional visualization
            logger.info("Image generation failed, creating professional visualization...")
            outfit_description = f"AI-generated {trend_dna['trend_name']} outfit featuring {top_description} and {bottom_description}. This style embodies {vibes_string} for a perfect {trend_dna['trend_name']} look."
            return await _create_professional_outfit_visualization(model_image_url, outfit_items, outfit_description, trend_dna)
            
        except Exception as error:
            logger.error(f"Complete image generation failed: {str(error)}")
            
            # Final fallback
            fallback_description = f"Professional {trend_dna['trend_name']} outfit featuring {top_description} and {bottom_description}."
            return await _create_professional_outfit_visualization(model_image_url, outfit_items, fallback_description, trend_dna)
        
    except Exception as e:
        logger.error(f"Failed to generate outfit image: {str(e)}")
        return None


async def _create_professional_outfit_visualization(model_image_url: str, outfit_items: List[Dict[str, Any]], description: str, trend_dna: Dict[str, Any]) -> Optional[str]:
    """
    Create a professional outfit visualization that looks like a fashion magazine layout.
    
    Args:
        model_image_url (str): URL of the base model image
        outfit_items (List[Dict[str, Any]]): Clothing items for the outfit
        description (str): Gemini's styling analysis
        trend_dna (Dict[str, Any]): Trend information
        
    Returns:
        Optional[str]: Base64 encoded professional visualization
    """
    try:
        # Load base model image
        response = requests.get(model_image_url)
        model_img = Image.open(io.BytesIO(response.content))
        
        # Convert to RGB for consistent processing
        if model_img.mode != 'RGB':
            model_img = model_img.convert('RGB')
        
        from PIL import ImageDraw, ImageFont, ImageEnhance, ImageFilter
        
        # Create a magazine-style layout
        # Final dimensions for a professional look
        final_width = 1200
        final_height = 800
        
        # Create the main canvas with a modern gradient background
        canvas = Image.new('RGB', (final_width, final_height), color='#f8f9fa')
        
        # Create a subtle gradient background
        for y in range(final_height):
            alpha = y / final_height
            color_r = int(248 + (255 - 248) * alpha)
            color_g = int(249 + (255 - 249) * alpha) 
            color_b = int(250 + (255 - 250) * alpha)
            for x in range(final_width):
                canvas.putpixel((x, y), (color_r, color_g, color_b))
        
        draw = ImageDraw.Draw(canvas)
        
        # Load fonts
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
            subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
            body_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Resize and position model image (left side)
        model_height = 600
        model_width = int(model_img.width * (model_height / model_img.height))
        model_resized = model_img.resize((model_width, model_height), Image.Resampling.LANCZOS)
        
        # Add subtle shadow effect to model image
        shadow_offset = 8
        shadow = Image.new('RGBA', (model_width + shadow_offset, model_height + shadow_offset), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rectangle([(shadow_offset, shadow_offset), (model_width + shadow_offset, model_height + shadow_offset)], fill=(0, 0, 0, 50))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=4))
        
        # Paste shadow and model
        model_x = 50
        model_y = (final_height - model_height) // 2
        canvas.paste(shadow, (model_x - shadow_offset, model_y - shadow_offset), shadow)
        canvas.paste(model_resized, (model_x, model_y))
        
        # Right panel for outfit information
        panel_x = model_x + model_width + 60
        panel_width = final_width - panel_x - 50
        
        # Add trend title
        current_y = 80
        trend_title = f"{trend_dna['trend_name']} Style"
        draw.text((panel_x, current_y), trend_title, font=title_font, fill='#2c3e50')
        current_y += 50
        
        # Add vibes subtitle
        vibes_text = " • ".join(trend_dna['vibes'])
        draw.text((panel_x, current_y), vibes_text.title(), font=subtitle_font, fill='#34495e')
        current_y += 40
        
        # Add clothing items section
        draw.text((panel_x, current_y), "OUTFIT PIECES", font=subtitle_font, fill='#2c3e50')
        current_y += 30
        
        # Load and display clothing items
        for item in outfit_items:
            if item.get("image_url"):
                try:
                    # Download clothing image
                    clothing_response = requests.get(item["image_url"])
                    if clothing_response.status_code == 200:
                        clothing_img = Image.open(io.BytesIO(clothing_response.content))
                        
                        # Resize clothing image
                        clothing_size = 80
                        clothing_img = clothing_img.resize((clothing_size, clothing_size), Image.Resampling.LANCZOS)
                        
                        # Paste clothing image
                        canvas.paste(clothing_img, (panel_x, current_y))
                        
                        # Add description next to image
                        desc_x = panel_x + clothing_size + 15
                        desc_text = item['description']
                        
                        # Wrap text
                        words = desc_text.split()
                        lines = []
                        current_line = []
                        for word in words:
                            test_line = " ".join(current_line + [word])
                            bbox = draw.textbbox((0, 0), test_line, font=body_font)
                            if bbox[2] - bbox[0] < panel_width - clothing_size - 20:
                                current_line.append(word)
                            else:
                                if current_line:
                                    lines.append(" ".join(current_line))
                                current_line = [word]
                        if current_line:
                            lines.append(" ".join(current_line))
                        
                        # Draw text lines
                        text_y = current_y + 10
                        for line in lines[:2]:  # Limit to 2 lines
                            draw.text((desc_x, text_y), line, font=body_font, fill='#34495e')
                            text_y += 18
                        
                        current_y += clothing_size + 20
                        
                except Exception as e:
                    logger.warning(f"Could not display clothing image: {e}")
        
        # Add styling advice section
        if current_y < final_height - 200:
            current_y += 20
            draw.text((panel_x, current_y), "AI STYLING ADVICE", font=subtitle_font, fill='#2c3e50')
            current_y += 30
            
            # Wrap and display styling advice
            if description:
                advice_words = description.split()[:60]  # Limit words
                advice_lines = []
                current_line = []
                for word in advice_words:
                    test_line = " ".join(current_line + [word])
                    bbox = draw.textbbox((0, 0), test_line, font=small_font)
                    if bbox[2] - bbox[0] < panel_width - 10:
                        current_line.append(word)
                    else:
                        if current_line:
                            advice_lines.append(" ".join(current_line))
                        current_line = [word]
                if current_line:
                    advice_lines.append(" ".join(current_line))
                
                for line in advice_lines[:8]:  # Limit to 8 lines
                    draw.text((panel_x, current_y), line, font=small_font, fill='#7f8c8d')
                    current_y += 16
        
        # Add footer
        footer_y = final_height - 30
        footer_text = "Generated by AI Fashion Assistant • StyleSync"
        footer_bbox = draw.textbbox((0, 0), footer_text, font=small_font)
        footer_width = footer_bbox[2] - footer_bbox[0]
        footer_x = (final_width - footer_width) // 2
        draw.text((footer_x, footer_y), footer_text, font=small_font, fill='#bdc3c7')
        
        # Convert to base64
        buffer = io.BytesIO()
        canvas.save(buffer, format='PNG', quality=95)
        img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{img_b64}"
        
    except Exception as e:
        logger.error(f"Failed to create professional outfit visualization: {str(e)}")
        return None


async def _create_enhanced_outfit_visualization(model_image_url: str, outfit_items: List[Dict[str, Any]], description: str) -> Optional[str]:
    """
    Create an enhanced visualization showing the model with clothing items overlaid/composited.
    
    Args:
        model_image_url (str): URL of the base model image
        outfit_items (List[Dict[str, Any]]): Clothing items to overlay
        description (str): Gemini's description of how the outfit should look
        
    Returns:
        Optional[str]: Base64 encoded composite image showing outfit on model
    """
    try:
        # Load base model image
        response = requests.get(model_image_url)
        model_img = Image.open(io.BytesIO(response.content))
        
        # Convert to RGBA for transparency support
        if model_img.mode != 'RGBA':
            model_img = model_img.convert('RGBA')
        
        from PIL import ImageDraw, ImageFont, ImageEnhance, ImageFilter
        
        # Create a working copy
        composite = model_img.copy()
        draw = ImageDraw.Draw(composite)
        
        # Load clothing item images
        clothing_overlays = []
        for item in outfit_items:
            if item.get("image_url"):
                try:
                    clothing_response = requests.get(item["image_url"])
                    if clothing_response.status_code == 200:
                        clothing_img = Image.open(io.BytesIO(clothing_response.content))
                        if clothing_img.mode != 'RGBA':
                            clothing_img = clothing_img.convert('RGBA')
                        clothing_overlays.append({
                            'image': clothing_img,
                            'type': item['type'],
                            'description': item['description']
                        })
                except Exception as e:
                    logger.warning(f"Could not load clothing image for {item['description']}: {e}")
        
        # Get model dimensions
        model_width, model_height = composite.size
        
        # Try to overlay clothing items onto the model (simplified approach)
        for overlay in clothing_overlays:
            clothing_img = overlay['image']
            clothing_type = overlay['type']
            
            # Resize clothing to fit proportionally on model
            if clothing_type == "top":
                # Position top clothing in upper body area
                target_width = int(model_width * 0.4)  # 40% of model width
                target_height = int(model_height * 0.3)  # 30% of model height
                x_pos = int(model_width * 0.3)  # Center horizontally
                y_pos = int(model_height * 0.2)  # Upper body position
            elif clothing_type == "bottom":
                # Position bottom clothing in lower body area
                target_width = int(model_width * 0.35)  # 35% of model width
                target_height = int(model_height * 0.4)  # 40% of model height
                x_pos = int(model_width * 0.32)  # Center horizontally
                y_pos = int(model_height * 0.5)  # Lower body position
            else:
                continue
            
            # Resize clothing image
            clothing_resized = clothing_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # Make clothing semi-transparent for blending
            clothing_alpha = clothing_resized.copy()
            clothing_alpha = ImageEnhance.Brightness(clothing_alpha).enhance(0.8)  # Slightly darker
            
            # Create a mask for better blending
            mask = Image.new('L', (target_width, target_height), 180)  # Semi-transparent mask
            
            # Paste clothing onto model with transparency
            try:
                composite.paste(clothing_alpha, (x_pos, y_pos), mask)
            except:
                # Fallback without mask if it fails
                composite.paste(clothing_resized, (x_pos, y_pos))
        
        # Add a subtle overlay effect to make it look more integrated
        overlay_effect = Image.new('RGBA', composite.size, (255, 255, 255, 20))
        composite = Image.alpha_composite(composite, overlay_effect)
        
        # Add text annotation
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        except:
            title_font = ImageFont.load_default()
            font = ImageFont.load_default()
        
        # Add title at the bottom
        title = "AI-Generated Outfit Visualization"
        draw = ImageDraw.Draw(composite)
        
        # Create a semi-transparent background for text
        text_bg = Image.new('RGBA', composite.size, (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_bg)
        
        # Add background rectangle for text
        text_y = model_height - 60
        text_draw.rectangle([(0, text_y), (model_width, model_height)], fill=(0, 0, 0, 128))
        
        # Composite text background
        composite = Image.alpha_composite(composite, text_bg)
        
        # Add title text
        draw = ImageDraw.Draw(composite)
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (model_width - title_width) // 2
        draw.text((title_x, text_y + 10), title, font=title_font, fill='white')
        
        # Add outfit description
        desc_short = description[:80] + "..." if len(description) > 80 else description
        desc_bbox = draw.textbbox((0, 0), desc_short, font=font)
        desc_width = desc_bbox[2] - desc_bbox[0]
        desc_x = (model_width - desc_width) // 2
        draw.text((desc_x, text_y + 35), desc_short, font=font, fill='white')
        
        # Convert back to RGB for JPEG encoding
        if composite.mode == 'RGBA':
            rgb_composite = Image.new('RGB', composite.size, (255, 255, 255))
            rgb_composite.paste(composite, mask=composite.split()[-1])
            composite = rgb_composite
        
        # Convert to base64
        buffer = io.BytesIO()
        composite.save(buffer, format='PNG', quality=95)
        img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{img_b64}"
        
    except Exception as e:
        logger.error(f"Failed to create enhanced outfit visualization: {str(e)}")
        return None


async def _create_outfit_composite(model_image_url: str, outfit_items: List[Dict[str, Any]], description: str) -> Optional[str]:
    """
    Create a composite image showing the outfit items overlaid on the model.
    
    Args:
        model_image_url (str): URL of the base model image
        outfit_items (List[Dict[str, Any]]): Clothing items to overlay
        description (str): Gemini's description of how the outfit should look
        
    Returns:
        Optional[str]: Base64 encoded composite image
    """
    try:
        # Load base model image
        response = requests.get(model_image_url)
        model_img = Image.open(io.BytesIO(response.content))
        
        # Convert to RGBA for transparency support
        if model_img.mode != 'RGBA':
            model_img = model_img.convert('RGBA')
        
        from PIL import ImageDraw, ImageFont, ImageEnhance
        
        # Create a working copy
        composite = model_img.copy()
        
        # Load and overlay clothing item images
        clothing_overlays = []
        for item in outfit_items:
            if item.get("image_url"):
                try:
                    # Download clothing item image
                    clothing_response = requests.get(item["image_url"])
                    if clothing_response.status_code == 200:
                        clothing_img = Image.open(io.BytesIO(clothing_response.content))
                        if clothing_img.mode != 'RGBA':
                            clothing_img = clothing_img.convert('RGBA')
                        clothing_overlays.append({
                            'image': clothing_img,
                            'type': item['type'],
                            'description': item['description']
                        })
                except Exception as e:
                    logger.warning(f"Could not load clothing image for {item['description']}: {e}")
        
        # Create a side-by-side layout: model + clothing items
        # Calculate dimensions for layout
        model_width, model_height = composite.size
        
        # Create side panel for clothing items
        panel_width = 300
        total_width = model_width + panel_width + 40  # 20px padding on each side
        total_height = max(model_height, 600)
        
        # Create final canvas
        final_canvas = Image.new('RGB', (total_width, total_height), color='#f8f9fa')
        
        # Paste model image on the left
        model_x = 20
        model_y = (total_height - model_height) // 2 if model_height < total_height else 0
        final_canvas.paste(composite, (model_x, model_y), composite if composite.mode == 'RGBA' else None)
        
        # Create clothing items panel on the right
        panel_x = model_width + 40
        panel_y = 20
        
        # Draw clothing items in the side panel
        draw = ImageDraw.Draw(final_canvas)
        
        # Try to use a nice font
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except:
            title_font = ImageFont.load_default()
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Add title to clothing panel
        draw.text((panel_x, panel_y), "Outfit Items:", font=title_font, fill='#333333')
        current_y = panel_y + 30
        
        # Add each clothing item to the panel
        for overlay in clothing_overlays:
            clothing_img = overlay['image']
            
            # Resize clothing image to fit in panel
            max_size = (panel_width - 40, 150)
            clothing_img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Paste clothing image
            img_x = panel_x + (panel_width - clothing_img.width) // 2
            final_canvas.paste(clothing_img, (img_x, current_y), clothing_img if clothing_img.mode == 'RGBA' else None)
            
            # Add description below image
            desc_y = current_y + clothing_img.height + 5
            
            # Wrap text to fit panel width
            words = overlay['description'].split()
            lines = []
            current_line = []
            for word in words:
                test_line = " ".join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] < panel_width - 20:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))
            
            # Draw text lines
            for line in lines[:2]:  # Limit to 2 lines
                draw.text((panel_x + 10, desc_y), line, font=font, fill='#666666')
                desc_y += 18
            
            current_y = desc_y + 20
        
        # Add Gemini styling advice at the bottom of panel
        if current_y < total_height - 100:
            draw.text((panel_x, current_y), "AI Styling Advice:", font=font, fill='#333333')
            current_y += 25
            
            # Wrap styling advice
            advice_words = description.split()[:30]  # Limit words
            advice_lines = []
            current_line = []
            for word in advice_words:
                test_line = " ".join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=small_font)
                if bbox[2] - bbox[0] < panel_width - 20:
                    current_line.append(word)
                else:
                    if current_line:
                        advice_lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line:
                advice_lines.append(" ".join(current_line))
            
            for line in advice_lines[:4]:  # Limit to 4 lines
                draw.text((panel_x + 10, current_y), line, font=small_font, fill='#888888')
                current_y += 16
        
        # Convert to base64
        buffer = io.BytesIO()
        final_canvas.save(buffer, format='PNG')
        img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{img_b64}"
        
    except Exception as e:
        logger.error(f"Failed to create composite image: {str(e)}")
        return None


async def _create_styled_placeholder(description: str, trend_dna: Dict[str, Any]) -> str:
    """
    Create a styled placeholder image with outfit information.
    
    Args:
        description (str): Gemini's outfit description
        trend_dna (Dict[str, Any]): Trend information
        
    Returns:
        str: Base64 encoded placeholder image
    """
    try:
        from PIL import ImageDraw, ImageFont
        
        # Create a styled image
        width, height = 400, 600
        img = Image.new('RGB', (width, height), color='#f8f9fa')
        draw = ImageDraw.Draw(img)
        
        # Try to use a nice font
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except:
            title_font = ImageFont.load_default()
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Add title
        title = f"{trend_dna['trend_name']} Outfit"
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        draw.text((title_x, 50), title, font=title_font, fill='#333333')
        
        # Add vibes
        vibes = ", ".join(trend_dna['vibes'])
        vibes_text = f"Style: {vibes}"
        vibes_bbox = draw.textbbox((0, 0), vibes_text, font=font)
        vibes_width = vibes_bbox[2] - vibes_bbox[0]
        vibes_x = (width - vibes_width) // 2
        draw.text((vibes_x, 100), vibes_text, font=font, fill='#666666')
        
        # Add description (wrapped)
        desc_lines = []
        words = description.split()
        current_line = []
        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=small_font)
            if bbox[2] - bbox[0] < width - 40:
                current_line.append(word)
            else:
                if current_line:
                    desc_lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            desc_lines.append(" ".join(current_line))
        
        # Limit to first 10 lines
        desc_lines = desc_lines[:10]
        
        y_offset = 150
        for line in desc_lines:
            draw.text((20, y_offset), line, font=small_font, fill='#444444')
            y_offset += 20
        
        # Add footer
        footer = "Generated by AI Fashion Assistant"
        footer_bbox = draw.textbbox((0, 0), footer, font=small_font)
        footer_width = footer_bbox[2] - footer_bbox[0]
        footer_x = (width - footer_width) // 2
        draw.text((footer_x, height - 30), footer, font=small_font, fill='#888888')
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{img_b64}"
        
    except Exception as e:
        logger.error(f"Failed to create styled placeholder: {str(e)}")
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="


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
