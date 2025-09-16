"""
Flask API Routes for Style Weaver

This module defines the API endpoints for the Style Weaver application.
"""

from flask import Blueprint, request, jsonify, render_template
import asyncio
import logging
from app.agent import StyleWeaverAgent, generate_style_board

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
main = Blueprint('main', __name__)

# Initialize the agent
style_agent = StyleWeaverAgent()


@main.route('/')
def index():
    """
    Serve the main frontend page.
    
    Returns:
        str: Rendered HTML template
    """
    logger.info("Serving main index page")
    return render_template('index.html')


@main.route('/api/generate-style', methods=['POST'])
def generate_style():
    """
    Phase 4 API endpoint to generate a style board based on a trend.
    
    Expected JSON payload:
    {
        "trend_name": "trend_name"
    }
    
    Returns:
        JSON: Complete style board with generated image and outfit items
    """
    try:
        # Get trend from request
        data = request.get_json()
        if not data or 'trend_name' not in data:
            logger.warning("Invalid request: missing trend_name parameter")
            return jsonify({
                "success": False,
                "error": "Missing 'trend_name' parameter in request body"
            }), 400
        
        trend_name = data['trend_name']
        logger.info(f"🎨 Processing style generation request for trend: {trend_name}")
        
        # Process the style generation using the async agent function
        try:
            # Run the async function in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(generate_style_board(trend_name))
            loop.close()
        except Exception as e:
            logger.error(f"Error in async style generation: {str(e)}")
            return jsonify({
                "success": False,
                "error": "Style generation failed",
                "message": str(e)
            }), 500
        
        # Log the result
        if result['success']:
            logger.info(f"✅ Style generation successful for trend: {trend_name}")
        else:
            logger.error(f"❌ Style generation failed for trend: {trend_name}")
        
        # Return appropriate status code
        status_code = 200 if result['success'] else 500
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Unexpected error in generate_style endpoint: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500


@main.route('/api/weave-style', methods=['POST'])
def weave_style():
    """
    Legacy API endpoint for backward compatibility.
    Redirects to the new generate-style endpoint.
    """
    try:
        # Get trend from request (support both 'trend' and 'trend_name')
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "Missing request body"
            }), 400
        
        # Support both parameter names for compatibility
        trend_name = data.get('trend_name') or data.get('trend')
        if not trend_name:
            return jsonify({
                "success": False,
                "error": "Missing 'trend_name' or 'trend' parameter in request body"
            }), 400
        
        # Forward to the new endpoint logic
        data['trend_name'] = trend_name
        request._cached_json = data  # Update cached JSON
        
        return generate_style()
        
    except Exception as e:
        logger.error(f"Unexpected error in legacy weave_style endpoint: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500


@main.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify the API is running.
    
    Returns:
        JSON: Health status
    """
    logger.info("Health check requested")
    return jsonify({
        "status": "healthy",
        "service": "Style Weaver API",
        "version": "1.0.0"
    })


@main.route('/api/chat', methods=['POST'])
def chat():
    """
    Chat endpoint for conversational style assistance.
    
    Expected JSON payload:
    {
        "message": "user message"
    }
    
    Returns:
        JSON: Bot response with optional style suggestion
    """
    try:
        # Get message from request
        data = request.get_json()
        if not data or 'message' not in data:
            logger.warning("Invalid request: missing message parameter")
            return jsonify({
                "success": False,
                "error": "Missing 'message' parameter in request body"
            }), 400
        
        user_message = data['message'].strip()
        logger.info(f"💬 Processing chat message: {user_message}")
        
        # Process the message and generate response
        response_data = process_chat_message(user_message)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500


def process_chat_message(message):
    """
    Process user chat message and generate appropriate response.
    
    Args:
        message (str): User's message
        
    Returns:
        dict: Response data with bot message and optional style suggestion
    """
    message_lower = message.lower()
    
    # Style-related keywords and responses
    style_keywords = {
        '90s': {
            'style': '90s Revival',
            'responses': [
                "I love the 90s vibe! Think grunge, oversized flannels, and that effortlessly cool streetwear aesthetic. 🎸",
                "90s Revival is all about that nostalgic, rebellious spirit with baggy jeans and vintage tees! ✨",
                "The 90s Revival style brings back that iconic grunge and hip-hop influenced look! 🎯"
            ]
        },
        'grunge': {
            'style': '90s Revival',
            'responses': [
                "Grunge is such a timeless look! Perfect for that edgy, laid-back 90s Revival style. 🎸",
                "Love the grunge aesthetic! It's a key part of our 90s Revival trend. 🔥"
            ]
        },
        'minimalist': {
            'style': 'Minimalist Chic',
            'responses': [
                "Minimalist Chic is perfect for that clean, sophisticated look! ✨",
                "I love minimalist style - it's all about quality pieces and timeless elegance! 💎",
                "Minimalist Chic focuses on simple, refined pieces that make a statement through subtlety! 🌟"
            ]
        },
        'clean': {
            'style': 'Minimalist Chic',
            'responses': [
                "A clean aesthetic sounds perfect for Minimalist Chic! Think simple lines and neutral colors. ✨",
                "Clean and simple - that's the essence of Minimalist Chic style! 💫"
            ]
        },
        'professional': {
            'style': 'Minimalist Chic',
            'responses': [
                "For a professional look, Minimalist Chic is ideal - sophisticated yet approachable! 👔",
                "Professional style with a modern twist? Minimalist Chic has you covered! ✨"
            ]
        },
        'tech': {
            'style': 'Hacker Mode',
            'responses': [
                "Tech-inspired fashion? Hacker Mode is perfect - it's all about that innovative, digital aesthetic! 🎯",
                "Hacker Mode combines tech culture with street style for a truly unique look! 💻",
                "Love the tech vibe! Hacker Mode creates that perfect intersection of innovation and style! ⚡"
            ]
        },
        'hacker': {
            'style': 'Hacker Mode',
            'responses': [
                "Hacker Mode is our most innovative style - tech-inspired looks that make a statement! 🎯",
                "The Hacker Mode aesthetic is all about that cutting-edge, digital nomad vibe! 💻"
            ]
        },
        'innovative': {
            'style': 'Hacker Mode',
            'responses': [
                "Innovative style calls for Hacker Mode - where technology meets fashion! ⚡",
                "For something truly innovative, try Hacker Mode - it's our most unique aesthetic! 🚀"
            ]
        }
    }
    
    # Mood-based responses
    mood_keywords = {
        'casual': "For a casual day, I'd recommend something comfortable yet stylish! What kind of casual are you thinking - laid-back grunge or clean minimalist? 😊",
        'formal': "For formal occasions, Minimalist Chic offers that perfect sophisticated elegance! 👔",
        'creative': "Feeling creative? Hacker Mode might be perfect for expressing your innovative side! 🎨",
        'confident': "Confidence looks good in any style! What aesthetic matches your confident mood today? 💪",
        'relaxed': "For a relaxed vibe, 90s Revival offers that perfect laid-back, effortless cool! 😌",
        'edgy': "Edgy style calls for some 90s Revival grunge vibes! 🔥",
        'sophisticated': "Sophisticated style is exactly what Minimalist Chic delivers! ✨"
    }
    
    # Check for style keywords
    suggested_style = None
    response = None
    
    for keyword, info in style_keywords.items():
        if keyword in message_lower:
            suggested_style = info['style']
            import random
            response = random.choice(info['responses'])
            break
    
    # Check for mood keywords if no style match
    if not response:
        for keyword, mood_response in mood_keywords.items():
            if keyword in message_lower:
                response = mood_response
                break
    
    # Greeting responses
    greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening']
    if not response and any(greeting in message_lower for greeting in greetings):
        response = "Hey there! 👋 I'm excited to help you find your perfect style today! What kind of look are you going for? Casual, formal, or something unique? 🎨"
    
    # Question responses
    questions = ['what', 'how', 'why', 'when', 'where', 'which']
    if not response and any(q in message_lower for q in questions):
        if 'style' in message_lower or 'fashion' in message_lower:
            response = "Great question! I can help you explore different styles based on your mood, occasion, or personal preferences. Try describing how you want to feel or look! ✨"
        else:
            response = "That's an interesting question! I'm here to help with style and fashion advice. What kind of look are you trying to achieve? 🎨"
    
    # Default response
    if not response:
        response = "I love your style curiosity! 💫 Tell me more about what you're looking for - are you feeling more casual, professional, or want to try something completely different? I'm here to help you find the perfect look! ✨"
    
    return {
        "success": True,
        "response": response,
        "suggested_style": suggested_style
    }


@main.route('/api/trends', methods=['GET'])
def get_available_trends():
    """
    Get list of available trends from the knowledge graph.
    
    Returns:
        JSON: List of available trends
    """
    try:
        logger.info("Fetching available trends from Neo4j")
        
        # Query Neo4j for actual trends
        from neo4j import GraphDatabase
        import os
        
        neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD', 'your_password')
        
        trends = []
        
        try:
            driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            
            with driver.session() as session:
                # Get all trends with their vibes for descriptions
                query = """
                MATCH (t:Trend)-[:HAS_VIBE]->(v:Vibe)
                RETURN t.name as trend_name, collect(v.name) as vibes
                ORDER BY t.name
                """
                
                result = session.run(query)
                
                for record in result:
                    trend_name = record["trend_name"]
                    vibes = record["vibes"]
                    description = f"A style with {', '.join(vibes[:3])} vibes"  # Use first 3 vibes
                    
                    trends.append({
                        "name": trend_name,
                        "description": description
                    })
            
            driver.close()
            
        except Exception as db_error:
            logger.warning(f"Could not connect to Neo4j: {str(db_error)}")
            # Fallback to static trends if database is not available
            trends = [
                {
                    "name": "90s Revival",
                    "description": "A style with grunge, casual, streetwear vibes"
                },
                {
                    "name": "Minimalist Chic", 
                    "description": "A style with clean, simple, professional vibes"
                },
                {
                    "name": "Hacker Mode",
                    "description": "A style with tech-inspired, innovative vibes"
                }
            ]
        
        return jsonify({
            "success": True,
            "trends": trends,
            "count": len(trends)
        })
        
    except Exception as e:
        logger.error(f"Error fetching trends: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch trends",
            "message": str(e)
        }), 500


# Error handlers
@main.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    logger.warning(f"404 error: {request.url}")
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404


@main.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"500 error: {str(error)}")
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500
