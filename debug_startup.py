import sys
import os
sys.path.append(os.getcwd())
import traceback

print(f"CWD: {os.getcwd()}")
print(f"Path: {sys.path}")

print("Checking modules...")
try:
    import data_processor
    print("✅ data_processor imported successfully")
except Exception:
    print("❌ Error importing data_processor:")
    traceback.print_exc()

try:
    import app
    print("✅ app imported successfully (dry run)")
except Exception:
    # app.py runs streamlit code on import so it might fail or warn, but syntax errors will show
    print("⚠️ Error importing app (might be expected if not running via streamlit):")
    traceback.print_exc()
