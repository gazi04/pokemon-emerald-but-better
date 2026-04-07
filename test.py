import os

test_path = "assets/sprite/pokemon/front/treecko_front.png"
if os.path.exists(test_path):
    print("✅ Path is valid and file found!")
else:
    print("❌ File not found. Check your folder names!")
