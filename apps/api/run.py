"""Dev server entrypoint.

Usage (from apps/api): uv run python run.py

On Windows this must be the entrypoint (not `uvicorn app.main:app` directly):
psycopg async requires a selector event loop, and uvicorn creates its loop
before importing the app, so the policy has to be set first.
"""

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)