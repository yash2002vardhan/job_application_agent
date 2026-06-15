# apply-to-job-agent

A simple [agno](https://github.com/agno-agi/agno) agent that applies to a job for
you. It reads your resume and uses it to **tailor** the application, and it talks
to a job-application **MCP server** (which you provide) to actually fetch the role
and submit the application.

## Setup

```bash
uv sync
cp .env.example .env   # then edit .env
```

Fill in `.env`:

- `OPENAI_API_KEY` — your OpenAI key (model defaults to `gpt-4o`)
- `RESUME_PATH` — path to your resume (`.pdf`, `.txt`, or `.md`)
- One of:
  - `MCP_COMMAND` — a stdio MCP server command, e.g. `npx -y some-job-mcp-server`
  - `MCP_URL` (+ optional `MCP_TRANSPORT=streamable-http|sse`) — an HTTP MCP server

## Run

```bash
uv run apply-agent "Apply to the Senior Backend Engineer role at Acme."
```

The agent will inspect the MCP server's tools, pull the job details, draft answers
grounded in your resume, and confirm with you before any irreversible submit.

## How it works

- `apply_agent/resume.py` — loads your resume into plain text (PDF via `pypdf`).
- `apply_agent/main.py` — builds the agno `Agent` with your resume as context and
  the MCP server's tools, then runs your task.
