import os

def print_tree(startpath):
    print(f"🔍 Current Working Directory: {os.getcwd()}")
    print(f"📂 Scanning tree from: {startpath}\n")
    
    # Check if the path even exists first
    if not os.path.exists(startpath):
        print(f"❌ ERROR: The path '{startpath}' does NOT exist relative to your current location.")
        print("Try scanning '.' (the current directory) instead.")
        return

    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print(f"{indent}📁 {os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print(f"{subindent}📄 {f}")

# First, let's scan the entire current folder to see where everything actually is
if __name__ == "__main__":
    # Scan current directory
    print_tree(".")