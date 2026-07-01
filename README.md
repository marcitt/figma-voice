# figma-voice

## Overview

A voice-controlled plugin for Figma that enables hands-free interaction with vector design workflows, built as part of my master's research project on speech accessibility for spatial design tasks.

## Architecture

- **Backend:** FastAPI + WebSocket server (Python)
- **Speech recognition:** Deepgram Nova-3 ASR, with keyword biasing for domain-specific terms
- **Command interpretation:** Regex-first matching with LLM fallback (temperature=0, structured outputs) for natural language commands that don't match a known pattern
- **Figma integration:** Two-sandbox plugin architecture - `code.js` (restricted sandbox, direct Figma document access) communicates via `postMessage` with `ui.html` (full browser context, holds the WebSocket connection)
- **macOS overlay:** AppKit/Quartz-based HUD for deterministic visual feedback on recognized commands
- **Undo system:** Typed undo snapshots covering node state, viewport, selection, and overlay state

### Key features

- Wake word system (mostly configured for testing purposes)
- Cardinal handle system
- Dual history architecture for tracking both command and design state over time
- Auto-labelling of design elements to support voice reference by name

## Setup

> **Note:** This plugin currently only runs on macOS. The HUD overlay is built directly on AppKit/Quartz (PyObjC), which has no cross-platform equivalent in this implementation. Windows/Linux support is not currently planned but the backend and command pipeline are largely OS-agnostic if you want to swap out the overlay layer.

### Requirements

- macOS (tested on Sonoma / Sequoia)
- Python 3.11+
- [Figma desktop app](https://www.figma.com/downloads/) (required for plugin development — the browser version doesn't support local plugin loading)
- A [Deepgram](https://deepgram.com/) API key (free tier available)
- Accessibility permissions granted to your terminal/IDE (System Settings -> Privacy & Security -> Accessibility) - required for the overlay to render

### 1. Clone the repo

```bash
git clone https://github.com/marcitt/figma-voice.git
cd figma-voice
```

### 2. Install backend dependencies

Uses conda for convienience 
```bash
conda env create -f environment.yaml
conda activate accessibility-env
```

### 3. Configure your Deepgram API key

Create a `.env` file in the project root:


## Research context
This plugin was evaluated in a repeated-measures usability study (23 participants) comparing task completion time, SUS, and RTLX across three interaction conditions. Full methodology, statistical analysis, and findings live in the companion research repository: [design-accessibility-tools](https://github.com/marcitt/design-accessibility-tools).

## Changelog

5.1.0 - DAY 2 USER TESTING

5.1.0
- Added fixed grid mode as an alternative to the alignment grid mode
- Added keyword biasing in Deepgram
- Switched to non-streaming architecture for improved reliability
- Limited undo to one step only to reduce unusual behaviour 
- Added limits to alignment grid subdivision (limit of n=3 subdivisions)
- Relabelling was changed to manual so labels can be a controlled factor in each study 

5.0.0 - Refactor between Day One User Testing and Day Two Testing
- ASR switched from Google Speech API to Deepgram Nova, significantly improved transcription
- Explored Deepgram Nova streaming implementatin 
- Refactored codebase into individual Python modules e.g. `spatial_commands.py`, `command_processing.py`, `command_dispatch.py` for improved readability and ease of development 

4.1.0 - DAY 1 USER TESTING

4.1.0 - Updates Ahead of Day One User Testing
- Number of grid subdivisions is based on density and cell screen area
- Deprecated Fixed Grid option for now
- HUD to show the transcript vs the executed command / action taken (command is converted to a human readable format)
- Google Speech API for transcription (performed poorly in day one testing)
- "cell" as hard delimiter in command grammar - prevents Google Speech merging "to" as "2" into cell numbers - sell added as a homophone
- WebSocket keepalive (ping_interval=20, ping_timeout=10)

4.0.0 - Initial Release to main /prototype repo (07/06/26)
(First end-to-end git push in the /prototype repo)
- Switched from HTTP polling to websockets to remove latency from polling
- Regex-first for handling fixed commands - which significantly reduces latency
- Node based alignment grid
- Spatial python commands, so that the LLM never manually needs to do any computation 
- Compass style resize and move strategy 
- Voice labels - nodes get relabelled on startup to short words 
- Filters noads based on what is in the viewport 
- Global canvas state stored
- Conversation history (last 10 turns) for contextual commands like do that again
- System vs figma routing via `level` for JSON commands
- `system-prompt.txt` seperated from canvas injection - enables system prompt chacing 
- Removed model routing due to impact on latency 
- Figma plugin commands: select, focus_object, zoom, pan, move, move_absolute, resize_scale, resize_delta, create_rect, create_text, zoom_fit

3.1.0 - Figma Plugin with Backend (01/06/26) 
- Added chain of thought for improved reasoning (this was later retracted due to latency issues)
- Added model routing (e.g. uses a more powerful model gpt-4o-mini for more complex tasks and gpt-5.4-turbo for simpler tasks)
- Contextual grid based reasoning e.g. move <object> to grid cell <n>

3.0.0 - Figma Plugin with Backend (26/05/26) 
- Added overlay with basic grid and node labelling 

2.0.0 - Figma Plugin with Backend (17/05/26) 
- FastAPI backend with HTTP polling (POST /update, POST /command, GET /command)
- Google speech API with synchronous transcription 
- LLM for command handling (no regex)
- Nodes loaded from `code.js` (figma sandbox)
- Figma node IPC handled locally as a JSON file
- Command dequeue

1.0.0 - Figma Starter Code (15/05/26) - distributed on (20/05/26)
First codebase to be shared with the Talon community slack
- Figma plugin (code.js + ui.html) with no backend
- Single `code.js` file for commands
- Text input box in `ui.html` enables users to transcribe commands using their own dictation software
- Basic command handler that handles a small set of fixed commands: select, zoom, zoom fit, focus, centre, pan, move, resize, rect, text