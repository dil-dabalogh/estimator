from __future__ import annotations

import re
from typing import Tuple, Optional
from urllib.parse import urlparse, urlunparse
import requests

try:
    from markdownify import markdownify as html_to_md
except Exception:
    html_to_md = None


class ConfluenceConfig:
    def __init__(self, base_url: str, email: str, api_token: str, root_base: str):
        self.base_url = base_url
        self.email = email
        self.api_token = api_token
        self.root_base = root_base


def normalize_root_base_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("ATLASSIAN_URL must be a full URL")
    path = (parsed.path or "").rstrip("/")
    if path.endswith("/wiki"):
        path = path[:-5]
    normalized = parsed._replace(path=path)
    return urlunparse(normalized).rstrip("/")


def ensure_wiki_suffix(root_base: str) -> str:
    parsed = urlparse(root_base)
    path = (parsed.path or "").rstrip("/")
    path = f"{path}/wiki" if not path.endswith("/wiki") else path
    return urlunparse(parsed._replace(path=path)).rstrip("/")


def parse_confluence_config(base_url: str, email: str, api_token: str) -> ConfluenceConfig:
    root_base = normalize_root_base_url(base_url)
    wiki_base = ensure_wiki_suffix(root_base)
    return ConfluenceConfig(base_url=wiki_base, email=email, api_token=api_token, root_base=root_base)


def is_jira_issue_url(url: str) -> bool:
    return bool(re.search(r"/browse/[A-Z][A-Z0-9]+-\d+", url, re.IGNORECASE))


def extract_jira_key(url: str) -> Optional[str]:
    m = re.search(r"/browse/([A-Z][A-Z0-9]+-\d+)", url, re.IGNORECASE)
    return m.group(1).upper() if m else None


def convert_html_to_markdown(html: str) -> str:
    if not html:
        return ""
    if html_to_md is None:
        text = re.sub(r"<\/?[^>]+>", "", html)
        return text
    return html_to_md(html, strip=['style', 'script'])


def fetch_jira_issue_markdown(cfg: ConfluenceConfig, url: str) -> Tuple[str, str]:
    key = extract_jira_key(url)
    if not key:
        raise ValueError("Could not extract Jira issue key from URL")
    
    session = requests.Session()
    session.auth = (cfg.email, cfg.api_token)
    session.headers.update({"Accept": "application/json"})
    issue_url = f"{cfg.root_base}/rest/api/3/issue/{key}?expand=renderedFields,fields"
    resp = session.get(issue_url, timeout=30)
    
    if resp.status_code != 200:
        raise ValueError(f"Jira fetch failed (status {resp.status_code})")
    
    data = resp.json()
    fields = data.get("fields", {})
    rendered = data.get("renderedFields", {})
    summary = fields.get("summary") or key
    html_desc = rendered.get("description") or ""
    md_desc = convert_html_to_markdown(html_desc) if html_desc else ""
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
    page_id = extract_confluence_page_id(url)
    if not page_id:
        raise ValueError("Could not extract Confluence pageId from URL")

    session = requests.Session()
    session.auth = (cfg.email, cfg.api_token)
    session.headers.update({"Accept": "application/json"})

    v2_url = f"{cfg.base_url}/api/v2/pages/{page_id}?body-format=storage"
    resp = session.get(v2_url, timeout=30)
    if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/json"):
        data = resp.json()
        title = data.get("title") or "Untitled"
        storage = (data.get("body") or {}).get("storage") or {}
        html = storage.get("value") or ""
        md = convert_html_to_markdown(html)
        return title, md

    v1_url = f"{cfg.base_url}/rest/api/content/{page_id}?expand=body.storage,version"
    resp = session.get(v1_url, timeout=30)
    if resp.status_code != 200:
        raise ValueError(f"Confluence fetch failed (status {resp.status_code})")
    data = resp.json()
    title = data.get("title") or "Untitled"
    body = (data.get("body") or {}).get("storage") or {}
    html = body.get("value") or ""
    md = convert_html_to_markdown(html)
    return title, md

