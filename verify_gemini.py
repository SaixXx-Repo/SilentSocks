import google.generativeai as genai
import sys
import os

# Ensure we can import from CWD if needed, but here we just test SDK
sys.path.append(os.getcwd())

def test_gemini_name():
    print(f"Testing with Python {sys.version}")
    try:
        # Check if attribute exists (this failed on Py 3.8 / old SDK)
        if not hasattr(genai, 'GenerativeModel'):
             print("Error: genai.GenerativeModel not found (Old SDK)")
             return

        model = genai.GenerativeModel('gemini-1.5-flash')
        print("Success: gemini-1.5-flash accepted by SDK constructor")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_gemini_name()
