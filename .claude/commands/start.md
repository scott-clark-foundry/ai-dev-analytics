# Start Session Command

Begin or resume work on a session file.

Usage: `/start [session] [task_number]`

Examples:
- `/start 001*` - Start session 001 from the beginning
- `/start 001* 2` - Start session 001 at Task 2
- `/start 002-api` - Start session matching "002-api"

## Process:

1. **Find session file**
   - Look in `sessions/` directory
   - Match pattern (e.g., 001* matches 001-foundation-setup.md)
   - Load the file

2. **Navigate to task**
   - If task number provided, jump to that task
   - Otherwise start from first incomplete task

3. **Update CLAUDE.md**
   - Set current session and task in the state section

4. **Begin work**
   - Show current task and subtasks
   - Work through subtasks sequentially
   - Focus on one subtask at a time

5. **Task completion**
   - Run /check before moving to next task
   - Note completion (user tracks externally)

## Working Style:
- Complete subtasks in order
- Ask for clarification if unclear
- Commit at logical boundaries
- Quality over speed