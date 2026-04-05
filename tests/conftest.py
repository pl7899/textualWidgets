"""
Shared pytest configuration for textual_widgets tests.
"""
import sys
import os

# Ensure the package root is on the path when running pytest from any directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
