import os
import sys
from dotenv import load_dotenv

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Import app after environment variables are loaded
from main import app

# Import Mangum after app is imported
from mangum import Mangum

# Create handler for Vercel
handler = Mangum(app)
