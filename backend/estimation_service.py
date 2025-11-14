from pathlib import Path
from typing import Optional
from llm_service import LLMProvider, LLMConfig
from confluence_client import (
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
    
    if ballpark:
        user_instructions += (
            f"\n\n**IMPORTANT CONSTRAINT**: The stakeholder has provided a ballpark estimate of {ballpark}. "
            "Your breakdown and analysis MUST be scoped and structured to align with this target. "
            "This is a business constraint that must be respected. Adjust scope, assumptions, and complexity analysis accordingly."
        )
    
    user_payload = (
        f"Confluence Link: {url}\n\n"
        f"Confluence Title: {title}\n\n"
        + (f"**BALLPARK CONSTRAINT: {ballpark}**\n\n" if ballpark else "")
        + f"Confluence Content (Markdown):\n\n{page_md}"
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
    
    if ballpark:
        user_instructions += (
            f"\n\n**CRITICAL CONSTRAINT**: The stakeholder has provided a ballpark estimate of {ballpark}. "
            "Your PERT estimates (O, M, P values) and final totals MUST target this ballpark as closely as possible. "
            "This is a business constraint, not a suggestion. Adjust your optimistic, most-likely, and pessimistic "
            "estimates to ensure the final Expected (E) total aligns with the ballpark. If scope needs to be adjusted "
            "to meet this constraint, note it in assumptions."
        )
    
    user_payload = (
        f"Single Source of Truth (Confluence): {url}\n\n"
        + (f"**BALLPARK TARGET: {ballpark}** ← YOUR TOTAL MUST ALIGN WITH THIS\n\n" if ballpark else "")
        + f"PERT Template:\n\n{pert_template_md}\n\n"
        + f"BA Estimation Notes:\n\n{ba_notes_md}"
    )
    
    user_messages = [user_instructions, user_payload]
    
    pert_sheet = provider.generate_text(
        system_prompt=eng_prompt,
        user_messages=user_messages,
        config=llm_config,
        ballpark=ballpark,
    )
    
    return pert_sheet

