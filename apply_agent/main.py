"""A simple agno agent that applies to a job, tailoring the application to your resume.

The agent connects to a job-application MCP server (which you provide) and uses
your resume as context to fill out / submit the application.

Configuration (via environment / .env):
  OPENAI_API_KEY     - your OpenAI key
  OPENAI_MODEL       - model id (default: gpt-4o)
  RESUME_PATH        - path to your resume (.pdf, .txt, .md)

  # MCP server: provide EITHER a stdio command OR an HTTP url.
  MCP_COMMAND        - e.g. "npx -y some-job-mcp-server"   (stdio transport)
  MCP_URL            - e.g. "http://localhost:8000/mcp"    (http transport)
  MCP_TRANSPORT      - "streamable-http" (default for url) or "sse"

Usage:
  uv run apply-agent "Apply to the Senior Backend Engineer role at Acme."
"""

from __future__ import annotations

import asyncio
import os
import sys

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools
from dotenv import load_dotenv

from apply_agent.resume import load_resume

INSTRUCTIONS = """\
You are a job-application assistant acting on behalf of the candidate whose
profile and resume are provided below. Your job is to apply to the role the
user specifies, using the tools exposed by the connected job-application MCP
server.

Workflow:
- Start by calling the discovery tools (e.g. list the open roles, then fetch the
  chosen role's overview). The role overview tells you the exact ordered list of
  submission tools to call and the application instructions — follow them.
- Complete every required submission step in order. A typical flow is: submit
  basic details (gets a draft id) -> submit resume -> submit links -> submit any
  required project link -> submit the screening answer to finalize. Pass the
  draft id through to each subsequent step.
- When identifying the agent provenance on any tool that accepts it, use
  agent_name "Claude Code", agent_vendor "Anthropic", agent_model the model in
  use.

Resume submission:
- {resume_directive}

Guidelines:
- Ground every claim in the resume/profile. Never invent experience, skills,
  employers, dates, links, or credentials the candidate does not have.
- Tailor the application to the specific job: emphasize the most relevant
  experience and mirror the language of the job description where it is truthful.
- For free-text fields (cover letter, "why are you a fit", screening questions),
  write concise, specific, professional answers drawn from the resume. For a
  screening question that expects a correct answer, reason it out and retry if
  told it is wrong.
- Before any finalizing/irreversible submit action, summarize exactly what you
  are about to submit and ask the user to confirm, unless they have already told
  you to submit without confirmation.
- If required information is genuinely missing from the profile/resume, ask the
  user rather than guessing. Do NOT trigger the optional pre-screen phone call
  unless the user explicitly consents.

=== CANDIDATE PROFILE ===
{profile}
=== END PROFILE ===

=== CANDIDATE RESUME ===
{resume}
=== END RESUME ===
"""


def build_resume_directive() -> str:
    """Tell the agent how to call submit_resume based on the configured mode."""
    mode = os.getenv("RESUME_SUBMIT_MODE", "text").lower()
    url = os.getenv("RESUME_URL")
    mime = os.getenv("RESUME_MIME_TYPE", "application/pdf")

    if mode == "url":
        if not url:
            raise SystemExit("RESUME_SUBMIT_MODE=url but RESUME_URL is not set.")
        return (
            f"Call submit_resume with ONLY the hosted file: resume_url='{url}' and "
            f"resume_mime_type='{mime}'. Do NOT pass resume_text — the candidate "
            "wants the uploaded resume submitted, not pasted text. Use the resume "
            "content below only to tailor your free-text answers."
        )
    if mode == "both" and url:
        return (
            f"Call submit_resume with BOTH the hosted file (resume_url='{url}', "
            f"resume_mime_type='{mime}') and the resume markdown text below."
        )
    return (
        "Call submit_resume with the resume markdown text (resume_text) shown below."
    )


def build_profile() -> str:
    """Collect candidate details the application needs beyond the resume text."""
    fields = {
        "Full name": os.getenv("CANDIDATE_NAME"),
        "Email": os.getenv("CANDIDATE_EMAIL"),
        "Phone": os.getenv("CANDIDATE_PHONE"),
        "GitHub": os.getenv("GITHUB_URL"),
        "LinkedIn": os.getenv("LINKEDIN_URL"),
        "Agentic project link": os.getenv("AGENTIC_PROJECT_URL"),
        "Hosted resume URL": os.getenv("RESUME_URL"),
    }
    lines = [f"{k}: {v}" for k, v in fields.items() if v]
    return "\n".join(lines) if lines else "(no extra profile fields provided)"


def build_mcp_tools() -> MCPTools:
    command = os.getenv("MCP_COMMAND")
    url = os.getenv("MCP_URL")

    if command:
        return MCPTools(command=command, timeout_seconds=30)
    if url:
        transport = os.getenv("MCP_TRANSPORT", "streamable-http")
        return MCPTools(url=url, transport=transport, timeout_seconds=30)

    raise SystemExit(
        "No MCP server configured. Set MCP_COMMAND (stdio) or MCP_URL (http) "
        "in your environment or .env file."
    )


async def run(task: str) -> None:
    resume_path = os.getenv("RESUME_PATH")
    if not resume_path:
        raise SystemExit("Set RESUME_PATH to your resume file (.pdf/.txt/.md).")
    resume_text = load_resume(resume_path)

    model_id = os.getenv("OPENAI_MODEL", "gpt-4o")

    async with build_mcp_tools() as mcp_tools:
        agent = Agent(
            model=OpenAIChat(id=model_id),
            tools=[mcp_tools],
            instructions=INSTRUCTIONS.format(
                resume_directive=build_resume_directive(),
                profile=build_profile(),
                resume=resume_text,
            ),
            markdown=True,
            add_history_to_messages=True,
        )
        await agent.aprint_response(task, stream=True)


def main() -> None:
    load_dotenv()
    task = " ".join(sys.argv[1:]).strip()
    if not task:
        task = input("What job should I apply to? Describe it: ").strip()
    if not task:
        raise SystemExit("No task provided.")
    asyncio.run(run(task))


if __name__ == "__main__":
    main()
