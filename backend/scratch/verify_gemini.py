import os
import sys
from dotenv import load_dotenv

# Ensure backend directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env variables
load_dotenv()

def test_gemini():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("Error: GEMINI_API_KEY is not set in backend/.env")
        print("Please configure GEMINI_API_KEY to test the API connection.")
        return False
        
    try:
        import google.generativeai as genai
        from pydantic import BaseModel, Field
        from typing import List
    except ImportError as e:
        print(f"Error: Dependency missing. Run pip install google-generativeai pydantic first. Details: {e}")
        return False

    print("Configuring Google Gemini SDK...")
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    print(f"Using model: {model_name}")

    try:
        # Test 1: Standard text generation
        print("\nTest 1: Running basic text generation...")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello! Give me a one-sentence greeting.")
        print(f"Response: {response.text.strip()}")
        
        # Test 2: Structured outputs using Pydantic schema
        print("\nTest 2: Running structured outputs generation...")
        class TestSchema(BaseModel):
            summary: str = Field(description="A 1-sentence summary of the text.")
            tags: List[str] = Field(description="List of 3 relevant tags.")
            
        test_prompt = "The Google Gemini API allows developers to access Google's model family for language processing tasks."
        response_structured = model.generate_content(
            f"Analyze this text: {test_prompt}",
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": TestSchema
            }
        )
        print(f"Structured response JSON: {response_structured.text.strip()}")
        print("\nAll tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\nAPI Error during execution: {e}")
        return False

if __name__ == "__main__":
    test_gemini()
