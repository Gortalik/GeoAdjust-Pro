import sys
import os

# Print current directory and Python path
print("Current directory:", os.getcwd())
print("Python path:", sys.path[:3])

# Try to add the src directory to the path
src_path = os.path.join(os.getcwd(), 'src')
print("Adding to path:", src_path)
print("Updated Python path:", sys.path[:3])

# Try to import the module
try:
    from geoadjust.io.formats.sdr import SDRParser
    print("SUCCESS: SDRParser imported successfully")
except Exception as e:
    print("ERROR: Failed to import SDRParser:", e)
    import traceback
    traceback.print_exc()