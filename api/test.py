from fastapi import FastAPI

# Create a simple FastAPI app for testing
app = FastAPI(title="Test API")

@app.get("/")
async def root():
    return {"message": "Test API is working!"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Export for Vercel
handler = app
