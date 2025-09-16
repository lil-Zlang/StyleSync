#!/usr/bin/env python3
"""
Database Seeding Script for Style Weaver

This is a convenience script to run the database seeding from the project root.
Usage: python seed_databases.py
"""

import sys
import os

# Add the project root to Python path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db_seeder import main

if __name__ == "__main__":
    main()
