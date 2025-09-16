#!/usr/bin/env python3
"""
Style Weaver Startup Script

This script provides an easy way to start the Style Weaver application
with proper checks and user-friendly messages.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required. Current version:", sys.version)
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_dependencies():
    """Check if required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    required_packages = ['flask', 'python-dotenv', 'weaviate-client', 'neo4j', 'google-generativeai']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n📦 Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True

def check_environment():
    """Check environment configuration."""
    print("🔧 Checking environment configuration...")
    
    env_file = Path('.env')
    if not env_file.exists():
        print("   ❌ .env file not found")
        return False
    
    print("   ✅ .env file exists")
    
    # Check for placeholder values
    with open('.env', 'r') as f:
        env_content = f.read()
        
    if 'YOUR_GEMINI_API_KEY' in env_content:
        print("   ⚠️  Gemini API key not configured (using placeholder)")
    else:
        print("   ✅ Gemini API key configured")
    
    return True

def check_database_connections():
    """Check if databases are accessible."""
    print("🗄️  Checking database connections...")
    
    # Check Neo4j
    try:
        from neo4j import GraphDatabase
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'your_password')
        
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        print("   ✅ Neo4j connection successful")
        neo4j_ok = True
    except Exception as e:
        print(f"   ❌ Neo4j connection failed: {str(e)}")
        neo4j_ok = False
    
    # Check Weaviate
    try:
        import weaviate
        url = os.getenv('WEAVIATE_URL', 'http://localhost:8080')
        client = weaviate.Client(url=url)
        client.is_ready()
        print("   ✅ Weaviate connection successful")
        weaviate_ok = True
    except Exception as e:
        print(f"   ❌ Weaviate connection failed: {str(e)}")
        weaviate_ok = False
    
    return neo4j_ok, weaviate_ok

def start_application():
    """Start the Style Weaver application."""
    print("\n🚀 Starting Style Weaver...")
    print("=" * 50)
    
    try:
        # Import and create the app
        from app import create_app
        app = create_app()
        
        print("🎨 Style Weaver is starting up...")
        print("📍 Application will be available at: http://127.0.0.1:5000")
        print("🔄 Press Ctrl+C to stop the server")
        print("=" * 50)
        
        # Start the Flask development server
        app.run(host='127.0.0.1', port=5000, debug=True)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Style Weaver stopped by user.")
    except Exception as e:
        print(f"\n❌ Failed to start Style Weaver: {str(e)}")
        return False
    
    return True

def main():
    """Main startup function."""
    print("🎨 Style Weaver Startup Check")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        print("\n💡 Install missing dependencies and try again.")
        sys.exit(1)
    
    # Check environment
    if not check_environment():
        print("\n💡 Configure your .env file and try again.")
        sys.exit(1)
    
    # Check database connections
    neo4j_ok, weaviate_ok = check_database_connections()
    
    if not (neo4j_ok and weaviate_ok):
        print("\n⚠️  Database connections failed, but Style Weaver can still run.")
        print("   The app will show appropriate error messages to users.")
        print("   To enable full functionality:")
        if not neo4j_ok:
            print("   - Start Neo4j: docker run -d -p 7687:7687 --name neo4j -e NEO4J_AUTH=neo4j/password neo4j:latest")
        if not weaviate_ok:
            print("   - Start Weaviate: docker run -d -p 8080:8080 --name weaviate semitechnologies/weaviate:latest")
        print("   - Run: python seed_databases.py")
        
        response = input("\n🤔 Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("👋 Startup cancelled. Fix database connections and try again.")
            sys.exit(1)
    
    print("\n✅ All checks passed! Starting application...")
    
    # Start the application
    if not start_application():
        sys.exit(1)

if __name__ == "__main__":
    main()
