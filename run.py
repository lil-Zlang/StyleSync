#!/usr/bin/env python3
"""
Style Weaver Flask Application Runner

This script initializes and runs the Style Weaver Flask application.
It serves as the main entry point for the web server.
"""

import os
import sys
from app import create_app

def main():
    """
    Main function to run the Flask application.
    """
    try:
        # Create the Flask app using the application factory pattern
        app = create_app()
        
        # Get configuration from environment variables
        host = os.getenv('FLASK_HOST', '127.0.0.1')
        port = int(os.getenv('FLASK_PORT', 5000))
        debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
        
        print(f"""
╔══════════════════════════════════════╗
║            Style Weaver              ║
║        AI Fashion Styling App        ║
╠══════════════════════════════════════╣
║ Server: http://{host}:{port}        ║
║ Debug Mode: {debug}                     ║
║ Environment: {'Development' if debug else 'Production'}          ║
╚══════════════════════════════════════╝
        """)
        
        # Run the Flask application
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug,  # Only use reloader in debug mode
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n\n🛑 Style Weaver server stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Failed to start Style Weaver server: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
