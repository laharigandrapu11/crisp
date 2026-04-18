import sys
from pathlib import Path

# Add stage2_huffman/ to sys.path so `import huffman` works
sys.path.insert(0, str(Path(__file__).parent.parent))
