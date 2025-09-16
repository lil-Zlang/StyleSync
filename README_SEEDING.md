# Style Weaver Database Seeding Guide

This guide explains how to set up and seed the databases for the Style Weaver application.

## Prerequisites

### Required Databases
1. **Weaviate** - Vector database for wardrobe items
2. **Neo4j** - Graph database for fashion trends

### Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your environment variables in `.env`:
```bash
# Weaviate Configuration
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=  # Optional, leave empty for local development

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here
```

## Database Setup

### Option 1: Using Docker (Recommended)

#### Start Weaviate:
```bash
docker run -d \
  --name weaviate \
  -p 8080:8080 \
  -e QUERY_DEFAULTS_LIMIT=25 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  -e DEFAULT_VECTORIZER_MODULE='text2vec-transformers' \
  -e ENABLE_MODULES='text2vec-transformers' \
  -e TRANSFORMERS_INFERENCE_API='http://t2v-transformers:8080' \
  semitechnologies/weaviate:latest
```

#### Start Neo4j:
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password_here \
  neo4j:latest
```

### Option 2: Local Installation

#### Weaviate:
1. Download from [Weaviate.io](https://weaviate.io/developers/weaviate/installation)
2. Follow installation instructions for your platform
3. Start on port 8080

#### Neo4j:
1. Download from [Neo4j.com](https://neo4j.com/download/)
2. Install Neo4j Desktop or Community Edition
3. Create a new database with credentials matching your `.env` file
4. Start the database on port 7687

## Running the Seeder

### Method 1: Direct Script Execution
```bash
python app/db_seeder.py
```

### Method 2: Convenience Script
```bash
python seed_databases.py
```

## What Gets Seeded

### Weaviate - Personal Wardrobe Items
The script creates a `ClothingItem` class with the following sample items:

1. **White Cotton T-Shirt** (`top_01`)
   - Style tags: casual, basic, minimalist
   - Type: top

2. **Black Oversized Hoodie** (`top_02`)
   - Style tags: streetwear, casual, cozy
   - Type: top

3. **Dark Wash Denim Jeans** (`bottom_01`)
   - Style tags: casual, classic, streetwear
   - Type: bottom

4. **Khaki Chinos** (`bottom_02`)
   - Style tags: business-casual, preppy
   - Type: bottom

### Neo4j - Fashion Trends Knowledge Graph
The script creates trend nodes with relationships to garments and vibes:

#### "90s Revival" Trend:
- **Garments**: denim jeans, graphic t-shirt, oversized hoodie
- **Vibes**: grunge, casual, streetwear, nostalgic

#### "Minimalist Chic" Trend:
- **Garments**: crewneck t-shirt, chinos, blazer  
- **Vibes**: clean, simple, professional, timeless

## Verification

### Check Weaviate Data:
```bash
curl http://localhost:8080/v1/objects
```

### Check Neo4j Data:
1. Open Neo4j Browser at http://localhost:7474
2. Run query: `MATCH (n) RETURN n LIMIT 25`

## Troubleshooting

### Common Issues:

1. **Connection Refused Errors**
   - Ensure databases are running on the correct ports
   - Check firewall settings
   - Verify Docker containers are healthy

2. **Authentication Errors**
   - Check your `.env` file credentials
   - Ensure Neo4j password matches your database setup

3. **Import Errors**
   - Run `pip install -r requirements.txt`
   - Check Python version compatibility (3.8+)

### Error Messages:
- The seeder provides detailed error messages and setup instructions
- Check the console output for specific connection issues
- Verify database logs for additional troubleshooting info

## Success Output

When successful, you should see:
```
🌱 Starting Style Weaver Database Seeding...
==================================================

📦 Seeding Weaviate with wardrobe data...
✅ Weaviate seeding completed successfully!

🕸️  Seeding Neo4j with trend data...
✅ Neo4j seeding completed successfully!

==================================================
🎉 All databases seeded successfully!

You can now:
  - Query Weaviate for clothing items
  - Query Neo4j for fashion trends and relationships
  - Run the Style Weaver application!
```

## Next Steps

After successful seeding:
1. Start the Flask application: `python run.py`
2. Open http://127.0.0.1:5000 in your browser
3. Test the trend selection functionality
4. Proceed with Phase 2 implementation

The seeded data provides a solid foundation for testing the complete Style Weaver workflow!
