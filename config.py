import pyautogui

SCREEN_W, SCREEN_H = pyautogui.size()  # gets logical resolution automatically
COLS = 8
ROWS = 5
CANVAS_TOP_LEFT_X = 0
CANVAS_TOP_LEFT_Y = 76
CANVAS_W = 1470
CANVAS_H = 956 - 75.5

MODEL = "gpt-5.4-nano"
MAX_HISTORY = 10

LISTENING_ON_STARTUP = True
GRID_ON_STARTUP = True

GRID_ALIGNMENT_SUBDIVISIONS = 1      # 1-3
GRID_ALIGNMENT_SUBDIVISIONS_MAX = 3
GRID_ALIGNMENT_SUBDIVISIONS_MIN = 1

GRID_MAX_CELLS_FOR_LABELS = 1000

TRANSCRIBER = "deepgram"  # options: "deepgram", "deepgram_streaming", "google"

# Talon Alphabet
# VOICE_LABELS = [
#     "air", "bat", "cap", "drum", "each", "fine", "gust", "harp", "sit", "jury",
#     "crunch", "look", "made", "near", "odd", "pit", "quench", "red", "sun", "trap",
#     "urge", "vest", "whale", "plex", "yank", "zip",
# ]

GRID_MODE = "alignment" 
GRID_PRECISION_CELL_SIZES = [100, 75, 50, 25, 10, 5]  # index increases with detail
GRID_PRECISION_DEFAULT_INDEX = 1  # starts at 100


VOICE_LABELS = [
    "pluto", "moon", "frost", "plant", "sun", "globe", 
    "quartz", "zinc", "flint", "cloud", "bridge", "steel", "vault", "apple", "hat"
]

GRAMMAR_KEYWORDS = [
    # wake up
    "hey", "figma", "listening",
    # command verbs
    "move", "resize", "increase", "decrease", "select", "deselect",
    "zoom", "focus", "pan", "delete", "copy", "cut", "paste", "undo",
    "rename", "group", "ungroup", "label",
    # spatial
    "north", "south", "east", "west", "centre",
    "cell", "sell", "pixels",
    # directions
    "right", "left", "up", "down",
    # grid/overlay
    "grid", "overlay", "labels",
    "show", "hide"
    # grid modes
    "alignment", "precision", "fixed", "uniform",
    # detail
    "detail", "density", "subdivide", "finer", "coarser",
    # navigation
    "fit", "context", "forward", "backward",
]