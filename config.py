import pyautogui

SCREEN_W, SCREEN_H = pyautogui.size()  # gets logical resolution automatically
COLS = 8
ROWS = 5
CANVAS_TOP_LEFT_X = 0
CANVAS_TOP_LEFT_Y = 76
CANVAS_W = 1470
CANVAS_H = 956 - 75.5

# FAST_MODEL = "gpt-5-nano"
# REASONING_MODEL = "gpt-4o-mini"
REASONING_MODEL = "gpt-5-mini"
MAX_HISTORY = 10
