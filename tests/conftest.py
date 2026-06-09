import sys
import os

# Add the project root to sys.path so tests can find the 'src' package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
