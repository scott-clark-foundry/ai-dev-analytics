# Project Context

AI Development Analytics Tool - Track AI-assisted development sessions
Stack: Python 3.11, FastAPI, SQLite
Architecture: Hexagonal (Ports & Adapters)

## Commands
- `/start [session] [task]` - Start working on a session (e.g., /start 001* 2)
- `/check` - Run quality checks (lint, type, test)

## Workflow
1. Load session file from sessions/ directory
2. Work through tasks sequentially
3. Run /check before task transitions
4. Focus on one subtask at a time

## Project Details
See @.claude/project.md for full tech stack

## Current State
Working on: Session 002 - API Backend Foundation
Session: 002
Task: Task 3 - OpenAI Usage API Integration