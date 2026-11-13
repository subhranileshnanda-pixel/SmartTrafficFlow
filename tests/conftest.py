import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")          # run Pygame without a window
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "simulation"))
sys.path.insert(0, os.path.join(ROOT, "backend"))           # backend first: both folders have a main.py