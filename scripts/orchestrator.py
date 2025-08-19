#!/usr/bin/env python3
"""
Estimation Orchestrator

This CLI script:
 1) Reads BA and Engineer personas from `personas/`.
 2) Accepts a Confluence link and fetches its content via Confluence REST API.
 3) Generates BA estimation notes (Markdown) using the BA persona.
 4) Generates a completed PERT estimation sheet (Markdown) using the Engineer persona and the provided template.
 5) Stores all outputs in a fresh folder under `estimations/`.

Environment variables required (Atlassian Cloud):
  - ATLASSIAN_URL (e.g., https://your-domain.atlassian.net/wiki)
  - ATLASSIAN_USER_EMAIL
  - ATLASSIAN_API_TOKEN

Note on Jira: Jira access, if needed, uses the same Atlassian variables above.

OpenAI:
  - OPENAI_API_KEY

Note: This script does not depend on MCP runtime; instead it fetches Confluence content directly
      and supplies it to the model. You can extend it to add more retrieval if needed.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import os
import re
from pathlib import Path
import shutil
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse

import requests

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
)
from rich.traceback import install as rich_traceback_install

try:
    # OpenAI >= 1.0.0
    from openai import OpenAI
except Exception:  # pragma: no cover - fallback for older installations
    OpenAI = None  # type: ignore

try:
    # Lightweight HTML->Markdown converter for Confluence storage content
    from markdownify import markdownify as html_to_md
except Exception:
    html_to_md = None  # type: ignore


REPO_ROOT = Path(__file__).resolve().parents[1]
PERSONAS_DIR = REPO_ROOT / "personas"
TEMPLATES_DIR = REPO_ROOT / "templates"
ESTIMATIONS_DIR = REPO_ROOT / "estimations"

console = Console()
rich_traceback_install(show_locals=False)

class OrchestratorError(Exception):
    pass


@dataclasses.dataclass
class ConfluenceConfig:
    base_url: str  # Confluence base with '/wiki'
    email: str
    api_token: str
    root_base: str  # Atlassian root base without '/wiki'


def read_text_file(path: Path) -> str:
    if not path.exists():
        raise OrchestratorError(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


def _make_safe_folder_name(name_hint: Optional[str]) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", name_hint or "estimation").strip("-")


def get_output_dir_path(name_hint: Optional[str]) -> Path:
    safe_hint = _make_safe_folder_name(name_hint)
    return ESTIMATIONS_DIR / safe_hint


def ensure_output_dir(name_hint: Optional[str], force: bool) -> Path:
    folder = get_output_dir_path(name_hint)
    if folder.exists():
        if not force:
            raise OrchestratorError(
                f"Output folder already exists: {folder}. Use --force to overwrite, or choose a different --name."
            )
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def parse_confluence_config_from_env() -> ConfluenceConfig:
    # Prefer new variable names; support older names as fallback for compatibility.
    base_url = os.getenv("ATLASSIAN_URL") or os.getenv("CONFLUENCE_BASE_URL")
    email = (
        os.getenv("ATLASSIAN_USER_EMAIL")
        or os.getenv("CONFLUENCE_EMAIL")
    )
    token = (
        os.getenv("ATLASSIAN_API_KEY")
        or os.getenv("ATLASSIAN_API_TOKEN")
        or os.getenv("CONFLUENCE_API_TOKEN")
    )
    if not all([base_url, email, token]):
        raise OrchestratorError(
            "Missing Atlassian env vars. Set ATLASSIAN_URL, ATLASSIAN_USER_EMAIL, ATLASSIAN_API_TOKEN"
        )
    root_base = _normalize_root_base_url(base_url)
    wiki_base = _ensure_wiki_suffix(root_base)
    return ConfluenceConfig(base_url=wiki_base, email=email, api_token=token, root_base=root_base)


def _normalize_root_base_url(url: str) -> str:
    """Normalize to Atlassian root base (no trailing '/wiki')."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise OrchestratorError("ATLASSIAN_URL must be a full URL, e.g. https://<domain>.atlassian.net")
    path = (parsed.path or "").rstrip("/")
    # Strip '/wiki' if present
    if path.endswith("/wiki"):
        path = path[:-5]
    normalized = parsed._replace(path=path)
    return urlunparse(normalized).rstrip("/")


def _ensure_wiki_suffix(root_base: str) -> str:
    parsed = urlparse(root_base)
    path = (parsed.path or "").rstrip("/")
    path = f"{path}/wiki" if not path.endswith("/wiki") else path
    return urlunparse(parsed._replace(path=path)).rstrip("/")


def is_jira_issue_url(url: str) -> bool:
    return bool(re.search(r"/browse/[A-Z][A-Z0-9]+-\d+", url, re.IGNORECASE))


def extract_jira_key(url: str) -> Optional[str]:
    m = re.search(r"/browse/([A-Z][A-Z0-9]+-\d+)", url, re.IGNORECASE)
    return m.group(1).upper() if m else None


def fetch_jira_issue_markdown(cfg: ConfluenceConfig, url: str) -> Tuple[str, str]:
    """Return (title, markdown) for a Jira issue URL.

    Uses renderedFields.description (HTML) when available and converts to Markdown.
    """
    key = extract_jira_key(url)
    if not key:
        raise OrchestratorError("Could not extract Jira issue key from URL.")
    session = requests.Session()
    session.auth = (cfg.email, cfg.api_token)
    session.headers.update({"Accept": "application/json"})
    issue_url = f"{cfg.root_base}/rest/api/3/issue/{key}?expand=renderedFields,fields"
    resp = session.get(issue_url, timeout=30)
    if resp.status_code != 200:
        raise OrchestratorError(f"Jira fetch failed (status {resp.status_code}). URL: {issue_url}")
    data = resp.json()
    fields = data.get("fields", {})
    rendered = data.get("renderedFields", {})
    summary = fields.get("summary") or key
    html_desc = rendered.get("description") or ""
    md_desc = _convert_html_to_markdown(html_desc) if html_desc else ""
    issuetype = (fields.get("issuetype") or {}).get("name") or "Issue"
    status = ((fields.get("status") or {}).get("name")) or "Unknown"
    project = (fields.get("project") or {}).get("key") or ""
    labels = fields.get("labels") or []
    labels_md = ", ".join(labels) if labels else "(none)"
    body_md = (
        f"# Jira Issue\n\n"
        f"- Link: {url}\n"
        f"- Key: {key}\n"
        f"- Project: {project}\n"
        f"- Type: {issuetype}\n"
        f"- Status: {status}\n"
        f"- Labels: {labels_md}\n\n"
        f"## Summary\n\n{summary}\n\n"
        f"## Description\n\n{md_desc or '_No description_'}\n"
    )
    return summary, body_md


def extract_confluence_page_id(url: str) -> Optional[str]:
    # Supported formats:
    #  - .../pages/viewpage.action?pageId=123456
    #  - .../pages/123456/Some-Title
    #  - .../wiki/spaces/SPACE/pages/123456/Some-Title
    patterns = [
        r"[?&]pageId=(\d+)",
        r"/pages/(\d+)(?:/|$)",
        r"/pages/viewpage\.action.*?[?&]pageId=(\d+)",
        r"/spaces/.+?/pages/(\d+)(?:/|$)",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def fetch_confluence_page_markdown(cfg: ConfluenceConfig, url: str) -> Tuple[str, str]:
    """Return (title, markdown) for the given Confluence page URL.

    Attempts to fetch storage format and convert to Markdown.
    """
    page_id = extract_confluence_page_id(url)
    if not page_id:
        raise OrchestratorError("Could not extract Confluence pageId from URL.")

    # Prefer v2 API if available, else fallback to v1
    session = requests.Session()
    session.auth = (cfg.email, cfg.api_token)
    session.headers.update({"Accept": "application/json"})

    # Try v2
    v2_url = f"{cfg.base_url}/api/v2/pages/{page_id}?body-format=storage"
    resp = session.get(v2_url, timeout=30)
    if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/json"):
        data = resp.json()
        title = data.get("title") or "Untitled"
        storage = (data.get("body") or {}).get("storage") or {}
        html = storage.get("value") or ""
        md = _convert_html_to_markdown(html)
        return title, md

    # Fallback to v1 (Cloud)
    v1_url = f"{cfg.base_url}/rest/api/content/{page_id}?expand=body.storage,version"
    resp = session.get(v1_url, timeout=30)
    if resp.status_code != 200:
        raise OrchestratorError(
            f"Confluence fetch failed (status {resp.status_code}). URL tried: {v2_url} then {v1_url}"
        )
    data = resp.json()
    title = data.get("title") or "Untitled"
    body = (data.get("body") or {}).get("storage") or {}
    html = body.get("value") or ""
    md = _convert_html_to_markdown(html)
    return title, md


def _convert_html_to_markdown(html: str) -> str:
    if not html:
        return ""
    if html_to_md is None:
        # Minimal fallback: strip tags crudely
        text = re.sub(r"<\/?[^>]+>", "", html)
        return text
    return html_to_md(html, strip=['style', 'script'])


def get_openai_client() -> OpenAI:
    if OpenAI is None:
        raise OrchestratorError(
            "openai package not available. Install dependencies from requirements.txt"
        )
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise OrchestratorError("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)


def generate_ba_notes(
    client: OpenAI,
    ba_system_prompt: str,
    confluence_url: str,
    confluence_title: str,
    confluence_markdown: str,
    model: str,
    ballpark: Optional[str] = None,
) -> str:
    user_instructions = (
        "You will receive a Confluence page link and its content. "
        "Produce the required Markdown estimation analysis."
    )
    user_payload = (
        f"Confluence Link: {confluence_url}\n\n"
        f"Confluence Title: {confluence_title}\n\n"
        + (f"Initial Ballpark (from PM or stakeholder): {ballpark}\n\n" if ballpark else "")
        + f"Confluence Content (Markdown):\n\n{confluence_markdown}"
    )
    if ballpark:
        user_instructions += (
            " The initial ballpark is provided; align your suggested breakdown to approximately fit this band. "
            "If you see a justified deviation, call it out explicitly and provide a within-ballpark alternative."
        )
    create_kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": ba_system_prompt},
            {"role": "user", "content": user_instructions},
            {"role": "user", "content": user_payload},
        ],
    }
    if not model.lower().startswith("gpt-5"):
        create_kwargs["temperature"] = 0.2
    resp = client.chat.completions.create(**create_kwargs)
    content = resp.choices[0].message.content or ""
    return content.strip()


def generate_pert_sheet(
    client: OpenAI,
    eng_system_prompt: str,
    pert_template_md: str,
    confluence_url: str,
    ba_notes_md: str,
    model: str,
    ballpark: Optional[str] = None,
) -> str:
    user_instructions = (
        "Using the PERT template, the BA estimation notes, and the Confluence source link, "
        "produce a complete PERT estimation Markdown."
    )
    user_payload = (
        f"Single Source of Truth (Confluence): {confluence_url}\n\n"
        f"PERT Template:\n\n{pert_template_md}\n\n"
        + (f"Initial Ballpark (from PM or stakeholder): {ballpark}\n\n" if ballpark else "")
        + f"BA Estimation Notes:\n\n{ba_notes_md}"
    )
    if ballpark:
        user_instructions += (
            " Respect the initial ballpark in your totals where practical. If exceeding it, explicitly justify, "
            "and include a within-ballpark alternative rollup."
        )
    create_kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": eng_system_prompt},
            {"role": "user", "content": user_instructions},
            {"role": "user", "content": user_payload},
        ],
    }
    if not model.lower().startswith("gpt-5"):
        create_kwargs["temperature"] = 0.2
    resp = client.chat.completions.create(**create_kwargs)
    content = resp.choices[0].message.content or ""
    return content.strip()


app = typer.Typer(add_completion=False, help="Orchestrates BA and Engineer estimations from a Confluence page.")


@app.command("run")
def run(
    source_url: str = typer.Argument(..., help="Confluence page URL or Jira issue URL for the estimation"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Name of the output folder (defaults to Confluence/Jira title)"),
    model: str = typer.Option("gpt-5", "--model", "-m", help="OpenAI chat model to use"),
    ballpark: Optional[str] = typer.Option(None, "--ballpark", help='Initial very high-level target (e.g., "30 manweeks")'),
    force: bool = typer.Option(False, "--force", help="Overwrite the output folder if it already exists (not allowed with --pert-only)"),
    business_analyst: bool = typer.Option(False, "--business-analyst", help="Only generate BA_Estimation_Notes.md and skip PERT"),
    pert_only: bool = typer.Option(False, "--pert-only", help="Only generate PERT_Estimate.md using existing BA_Estimation_Notes.md in an existing folder"),
) -> None:
    console.rule("[bold cyan]Estimation Orchestrator")

    with Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Loading personas and template...", start=True)
        ba_prompt = read_text_file(PERSONAS_DIR / "ba.txt")
        eng_prompt = read_text_file(PERSONAS_DIR / "engineer.txt")
        pert_template_md = read_text_file(TEMPLATES_DIR / "PERT_TEMPLATE.md")
        progress.update(task, description="Reading Atlassian credentials...")

        # Validate option combinations
        if business_analyst and pert_only:
            raise OrchestratorError("--business-analyst and --pert-only are mutually exclusive")

        cfg = parse_confluence_config_from_env()
        if is_jira_issue_url(source_url):
            progress.update(task, description="Fetching Jira issue...")
            title, page_md = fetch_jira_issue_markdown(cfg, source_url)
        else:
            progress.update(task, description="Fetching Confluence page...")
            title, page_md = fetch_confluence_page_markdown(cfg, source_url)

        out_dir_path = get_output_dir_path(name or title)

        created_files: list[str] = []
        if pert_only:
            progress.update(task, description="Validating existing folder and BA notes...")
            if not out_dir_path.exists():
                raise OrchestratorError(f"--pert-only requires an existing folder, but not found: {out_dir_path}")
            ba_notes_path = out_dir_path / "BA_Estimation_Notes.md"
            if not ba_notes_path.exists():
                raise OrchestratorError(
                    f"--pert-only requires existing BA_Estimation_Notes.md in {out_dir_path}"
                )

            ba_notes = ba_notes_path.read_text(encoding="utf-8")

            pert_path = out_dir_path / "PERT_Estimate.md"
            if pert_path.exists() and not force:
                raise OrchestratorError(
                    f"PERT_Estimate.md already exists in {out_dir_path}. Re-run with --force to overwrite."
                )

            progress.update(task, description="Initializing OpenAI client...")
            client = get_openai_client()

            progress.update(task, description="Generating PERT estimation sheet (using existing BA notes)...")
            pert_sheet = generate_pert_sheet(
                client=client,
                eng_system_prompt=eng_prompt,
                pert_template_md=pert_template_md,
                confluence_url=source_url,
                ba_notes_md=ba_notes,
                model=model,
                ballpark=ballpark,
            )
            (out_dir_path / "PERT_Estimate.md").write_text(pert_sheet, encoding="utf-8")
            created_files.append("PERT_Estimate.md")

            out_dir = out_dir_path
        else:
            progress.update(task, description="Preparing output folder...")
            out_dir = ensure_output_dir(name or title, force=force)

            # Write inputs
            (out_dir / "input.source.url.txt").write_text(source_url, encoding="utf-8")
            (out_dir / "input.confluence.page.md").write_text(page_md, encoding="utf-8")
            (out_dir / "PERT_TEMPLATE.md").write_text(pert_template_md, encoding="utf-8")
            created_files.extend(["input.source.url.txt", "input.confluence.page.md", "PERT_TEMPLATE.md"])

            progress.update(task, description="Initializing OpenAI client...")
            client = get_openai_client()

            if business_analyst:
                progress.update(task, description="Generating BA estimation notes...")
                ba_notes = generate_ba_notes(
                    client=client,
                    ba_system_prompt=ba_prompt,
                    confluence_url=source_url,
                    confluence_title=title,
                    confluence_markdown=page_md,
                    model=model,
                    ballpark=ballpark,
                )
                (out_dir / "BA_Estimation_Notes.md").write_text(ba_notes, encoding="utf-8")
                created_files.append("BA_Estimation_Notes.md")
                mode = "ba-only"
            else:
                progress.update(task, description="Generating BA estimation notes...")
                ba_notes = generate_ba_notes(
                    client=client,
                    ba_system_prompt=ba_prompt,
                    confluence_url=source_url,
                    confluence_title=title,
                    confluence_markdown=page_md,
                    model=model,
                    ballpark=ballpark,
                )
                (out_dir / "BA_Estimation_Notes.md").write_text(ba_notes, encoding="utf-8")
                created_files.append("BA_Estimation_Notes.md")

                progress.update(task, description="Generating PERT estimation sheet...")
                pert_sheet = generate_pert_sheet(
                    client=client,
                    eng_system_prompt=eng_prompt,
                    pert_template_md=pert_template_md,
                    confluence_url=source_url,
                    ba_notes_md=ba_notes,
                    model=model,
                    ballpark=ballpark,
                )
                (out_dir / "PERT_Estimate.md").write_text(pert_sheet, encoding="utf-8")
                created_files.append("PERT_Estimate.md")
                mode = "full"

            # Metadata for created/overwritten folder
            metadata = {
                "source_url": source_url,
                "confluence_title": title,
                "created_at": dt.datetime.now().isoformat(),
                "model": model,
                "mode": mode,
            }
            (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            created_files.append("metadata.json")

    console.print(Panel.fit(f"Saved outputs to\n[bold]{out_dir}[/bold]", title="Done", subtitle="Estimation artifacts"))
    console.print(Panel(Markdown("\n".join(["**Files created/updated**"] + [f"- {f}" for f in created_files])), title="Summary"))


if __name__ == "__main__":
    app()


