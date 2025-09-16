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
