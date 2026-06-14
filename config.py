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

TRANSCRIBER = "deepgram_streaming"  # options: "deepgram", "deepgram_streaming", "google"

# Talon Alphabet
VOICE_LABELS = [
    "air", "bat", "cap", "drum", "each", "fine", "gust", "harp", "sit", "jury",
    "crunch", "look", "made", "near", "odd", "pit", "quench", "red", "sun", "trap",
    "urge", "vest", "whale", "plex", "yank", "zip",
]