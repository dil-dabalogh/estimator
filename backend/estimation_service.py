from pathlib import Path
from typing import Optional
from backend.llm_service import LLMProvider, LLMConfig
from backend.confluence_client import (
    ConfluenceConfig,
    is_jira_issue_url,
    fetch_jira_issue_markdown,
    fetch_confluence_page_markdown,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PERSONAS_DIR = REPO_ROOT / "personas"
TEMPLATES_DIR = REPO_ROOT / "templates"


def load_ba_persona() -> str:
    return (PERSONAS_DIR / "ba.txt").read_text(encoding="utf-8")


def load_engineer_persona() -> str:
    return (PERSONAS_DIR / "engineer.txt").read_text(encoding="utf-8")


def load_pert_template() -> str:
    return (TEMPLATES_DIR / "PERT_TEMPLATE.md").read_text(encoding="utf-8")


def generate_ba_notes(
    provider: LLMProvider,
    confluence_config: ConfluenceConfig,
    url: str,
    llm_config: LLMConfig,
    ballpark: Optional[str] = None,
) -> tuple[str, str, str]:
    ba_prompt = load_ba_persona()
    
    if is_jira_issue_url(url):
        title, page_md = fetch_jira_issue_markdown(confluence_config, url)
    else:
        title, page_md = fetch_confluence_page_markdown(confluence_config, url)
    
    user_instructions = (
        "You will receive a Confluence page link and its content. "
        "Produce the required Markdown estimation analysis."
    )
    user_payload = (
        f"Confluence Link: {url}\n\n"
        f"Confluence Title: {title}\n\n"
        + (f"Initial Ballpark: {ballpark}\n\n" if ballpark else "")
        + f"Confluence Content (Markdown):\n\n{page_md}"
    )
    if ballpark:
        user_instructions += (
            " The initial ballpark is provided; align your suggested breakdown to approximately fit this band."
        )
    
    user_messages = [user_instructions, user_payload]
    
    ba_notes = provider.generate_text(
        system_prompt=ba_prompt,
        user_messages=user_messages,
        config=llm_config,
        ballpark=ballpark,
    )
    
    return title, page_md, ba_notes


def generate_pert_sheet(
    provider: LLMProvider,
    url: str,
    ba_notes_md: str,
    llm_config: LLMConfig,
    ballpark: Optional[str] = None,
) -> str:
    eng_prompt = load_engineer_persona()
    pert_template_md = load_pert_template()
    
    user_instructions = (
        "Using the PERT template, the BA estimation notes, and the Confluence source link, "
        "produce a complete PERT estimation Markdown."
    )
    user_payload = (
        f"Single Source of Truth (Confluence): {url}\n\n"
        f"PERT Template:\n\n{pert_template_md}\n\n"
        + (f"Initial Ballpark: {ballpark}\n\n" if ballpark else "")
        + f"BA Estimation Notes:\n\n{ba_notes_md}"
    )
    if ballpark:
        user_instructions += (
            " Respect the initial ballpark in your totals where practical."
        )
    
    user_messages = [user_instructions, user_payload]
    
    pert_sheet = provider.generate_text(
        system_prompt=eng_prompt,
        user_messages=user_messages,
        config=llm_config,
        ballpark=ballpark,
    )
    
    return pert_sheet

