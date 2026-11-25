"""Production server entrypoint.

Usage (from apps/api): uv run python serve.py

Serves the API AND the built Astro frontend (apps/web-astro/dist) on a
single port when the dist directory exists — the native production mode.
Build the frontend first: npm run build (repo root).

On Windows this must be the entrypoint (not `uvicorn app.main:app`):
psycopg async requires a selector event loop. uvicorn.run() installs its
own loop/policy (Proactor on Windows), so here we build the selector loop
explicitly and run the uvicorn server inside it.
"""

import asyncio
import os
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    config = uvicorn.Config(
        "app.main:app",
        host=os.environ.get("BCA_HOST", "127.0.0.1"),
        port=int(os.environ.get("BCA_PORT", "8000")),
        log_level="info",
    )
    server = uvicorn.Server(config)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.serve())
