from pathlib import Path
from typing import Optional
from llm_service import LLMProvider, LLMConfig
from confluence_client import (
    ConfluenceConfig,
    is_jira_issue_url,
    fetch_jira_issue_markdown,
    fetch_confluence_page_markdown,
)


# Support both local development and Lambda deployment
# In Lambda, personas and templates are copied to the backend directory
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent

# Try Lambda location first (backend/personas), then fall back to project root
if (BACKEND_DIR / "personas").exists():
    PERSONAS_DIR = BACKEND_DIR / "personas"
    TEMPLATES_DIR = BACKEND_DIR / "templates"
else:
    PERSONAS_DIR = REPO_ROOT / "personas"
    TEMPLATES_DIR = REPO_ROOT / "templates"


def load_requirements_persona() -> str:
    return (PERSONAS_DIR / "requirements_analyst.txt").read_text(encoding="utf-8")


def load_ba_persona() -> str:
    return (PERSONAS_DIR / "ba.txt").read_text(encoding="utf-8")


def load_engineer_persona() -> str:
    return (PERSONAS_DIR / "engineer.txt").read_text(encoding="utf-8")


def load_requirements_template() -> str:
    return (TEMPLATES_DIR / "REQUIREMENTS_TEMPLATE.md").read_text(encoding="utf-8")


def load_ba_notes_template() -> str:
    return (TEMPLATES_DIR / "BA_NOTES_TEMPLATE.md").read_text(encoding="utf-8")


def load_pert_template() -> str:
    return (TEMPLATES_DIR / "PERT_TEMPLATE.md").read_text(encoding="utf-8")


def generate_requirements(
    provider: LLMProvider,
    confluence_config: ConfluenceConfig,
    url: str,
    llm_config: LLMConfig,
    ballpark: Optional[str] = None,
) -> tuple[str, str, str]:
    """
    Generate requirements document from Confluence/Jira source.
    
    Returns:
        tuple of (title, page_md, requirements_md)
    """
    requirements_prompt = load_requirements_persona()
    requirements_template = load_requirements_template()
    
    if is_jira_issue_url(url):
        title, page_md = fetch_jira_issue_markdown(confluence_config, url)
    else:
        title, page_md = fetch_confluence_page_markdown(confluence_config, url)
    
    user_instructions = (
        "You will receive a Confluence page or Jira issue and its content. "
        "Using the Requirements template, produce a complete requirements document in Markdown."
    )
    
    if ballpark:
        user_instructions += (
            f"\n\n**NOTE**: The stakeholder has provided a ballpark estimate of {ballpark}. "
            "This is business context that may inform scope discussions, but do not include "
            "estimates in the requirements document."
        )
    
    user_payload = (
        f"Source Link: {url}\n\n"
        f"Source Title: {title}\n\n"
        + (f"**Ballpark Context: {ballpark}**\n\n" if ballpark else "")
        + f"Requirements Template:\n\n{requirements_template}\n\n"
        + f"Source Content (Markdown):\n\n{page_md}"
    )
    
    user_messages = [user_instructions, user_payload]
    
    requirements_md = provider.generate_text(
        system_prompt=requirements_prompt,
        user_messages=user_messages,
        config=llm_config,
        ballpark=ballpark,
    )
    
    return title, page_md, requirements_md


def generate_ba_notes(
    provider: LLMProvider,
    url: str,
    requirements_md: str,
    llm_config: LLMConfig,
    ballpark: Optional[str] = None,
) -> str:
    """
    Generate BA notes from requirements document.
    
    Args:
        provider: LLM provider instance
        url: Original source URL (for reference)
        requirements_md: Previously generated requirements document
        llm_config: LLM configuration
        ballpark: Optional ballpark estimate
    
    Returns:
        BA notes markdown string
    """
    ba_prompt = load_ba_persona()
    ba_notes_template = load_ba_notes_template()
    
    user_instructions = (
        "You will receive a Requirements document. "
        "Using the BA Notes template, produce engineer-focused scope guidance in Markdown."
    )
    
    if ballpark:
        user_instructions += (
            f"\n\n**CONSTRAINT**: The stakeholder has provided a ballpark estimate of {ballpark}. "
            "Note this as a constraint in your Estimation Guidance section but do not include estimates."
        )
    
    user_payload = (
        f"Single Source of Truth (Original): {url}\n\n"
        + (f"**BALLPARK CONSTRAINT: {ballpark}**\n\n" if ballpark else "")
        + f"BA Notes Template:\n\n{ba_notes_template}\n\n"
        + f"Requirements Document:\n\n{requirements_md}"
    )
    
    user_messages = [user_instructions, user_payload]
    
    ba_notes = provider.generate_text(
        system_prompt=ba_prompt,
        user_messages=user_messages,
        config=llm_config,
        ballpark=ballpark,
    )
    
    return ba_notes


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

