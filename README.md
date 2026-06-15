Version 5.1.0

5.2.0 - Updates Ahead of Day Two User Testing
n/a

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

---

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

---

3.1.0 - Figma Plugin with Backend (01/06/26) 
- Added chain of thought for improved reasoning (this was later retracted due to latency issues)
- Added model routing (e.g. uses a more powerful model gpt-4o-mini for more complex tasks and gpt-5.4-turbo for simpler tasks)
- Contextual grid based reasoning e.g. move <object> to grid cell <n>

3.0.0 - Figma Plugin with Backend (26/05/26) 
- Added overlay with basic grid and node labelling 

---

2.0.0 - Figma Plugin with Backend (17/05/26) 
- FastAPI backend with HTTP polling (POST /update, POST /command, GET /command)
- Google speech API with synchronous transcription 
- LLM for command handling (no regex)
- Nodes loaded from `code.js` (figma sandbox)
- Figma node IPC handled locally as a JSON file
- Command dequeue

---

1.0.0 - Figma Starter Code (15/05/26) - distributed on (20/05/26)
First codebase to be shared with the Talon community slack
- Figma plugin (code.js + ui.html) with no backend
- Single `code.js` file for commands
- Text input box in `ui.html` enables users to transcribe commands using their own dictation software
- Basic command handler that handles a small set of fixed commands: select, zoom, zoom fit, focus, centre, pan, move, resize, rect, text