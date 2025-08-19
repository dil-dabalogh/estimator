## Estimation Workspace (PERT + BA/Engineer Orchestrator)

This repository provides a production-ready, Markdown-first workflow for generating Business Analyst (BA) estimation notes and PERT (Program Evaluation and Review Technique) estimates from a Confluence page or Jira issue. It includes:

- `scripts/orchestrator.py`: CLI that fetches source content, invokes personas, and generates artifacts
- `templates/PERT_TEMPLATE.md`: Canonical PERT template
- `personas/`: BA and Engineer personas
- `estimations/`: Output folder tracked in git, with contents ignored (via `.gitignore`, except `.gitkeep`)

### What is PERT?

PERT models three time estimates for each task:

- **Optimistic (O)**: Best-case duration assuming everything goes well
- **Most likely (M)**: Realistic duration given typical conditions
- **Pessimistic (P)**: Worst-case duration assuming notable risks occur

From these, you compute:

- **Expected duration (E)**: \( E = \frac{O + 4M + P}{6} \)
- **Standard deviation (σ)**: \( \sigma = \frac{P - O}{6} \)
- **Variance (σ²)**: \( \sigma^2 = \left(\frac{P - O}{6}\right)^2 \)

Confidence windows (assuming approximate normality):

- **~68%**: \( E \pm 1\sigma \)
- **~95%**: \( E \pm 2\sigma \)
- **~99.7%**: \( E \pm 3\sigma \)

Use judgment: assumptions (independence, distribution shape) rarely hold perfectly.

### Repository layout

- `scripts/orchestrator.py`: Orchestration CLI
- `templates/PERT_TEMPLATE.md`: PERT template used by the orchestrator
- `personas/ba.txt`, `personas/engineer.txt`: Personas used for generation
- `estimations/`: Output directory (tracked, contents ignored except `.gitkeep`)

### Prerequisites

- Python 3.10+
- Access to Atlassian Cloud Confluence/Jira (API token)
- OpenAI API key

### Installation

```bash
pip install -r requirements.txt
```

### Configuration (environment variables)

```bash
export ATLASSIAN_URL="https://<your-domain>.atlassian.net/wiki"   # includes /wiki
export ATLASSIAN_USER_EMAIL="you@company.com"
export ATLASSIAN_API_TOKEN="<token>"
export OPENAI_API_KEY="<openai-key>"
```

The CLI supports both Confluence page URLs and Jira issue URLs.

### Usage

Basic full run (BA notes + PERT):

```bash
python scripts/orchestrator.py run "https://<domain>.atlassian.net/wiki/spaces/SPACE/pages/<pageId>/Title" \
  --name "MyFeature" \
  --model gpt-5
```

Outputs (no timestamp in folder name):

- `estimations/MyFeature/BA_Estimation_Notes.md`
- `estimations/MyFeature/PERT_Estimate.md`
- `estimations/MyFeature/input.confluence.page.md`
- `estimations/MyFeature/PERT_TEMPLATE.md`
- `estimations/MyFeature/input.source.url.txt`
- `estimations/MyFeature/metadata.json`

Optional parameters:

- `--ballpark "30 manweeks"`: Provide an initial high-level target to guide results
- `--model MODEL`: Set OpenAI chat model (default: `gpt-5`)

#### Intermediate flows

- BA-only (generates only BA notes):

```bash
python scripts/orchestrator.py run "<url>" --name "MyFeature" --business-analyst
```

- PERT-only (requires existing folder and BA notes):

```bash
python scripts/orchestrator.py run "<url>" --name "MyFeature" --pert-only
```

Rules for PERT-only:

- The folder `estimations/MyFeature` must already exist
- `BA_Estimation_Notes.md` must exist in that folder
- If `PERT_Estimate.md` already exists, you must pass `--force` to overwrite

#### Overwrite and safety rules

- When creating a new folder or re-running a full/BA-only flow into an existing folder, `--force` is required to overwrite the folder
- `--business-analyst` and `--pert-only` are mutually exclusive

### Troubleshooting

- Missing Atlassian configuration: ensure `ATLASSIAN_URL`, `ATLASSIAN_USER_EMAIL`, and `ATLASSIAN_API_TOKEN` are set
- Missing OpenAI key: ensure `OPENAI_API_KEY` is set
- URL parsing fails: verify the Confluence pageId or confirm the Jira issue URL format
- `--pert-only` errors:
  - Folder not found → create via a prior full or BA-only run
  - BA notes missing → run a BA-only or full flow first
  - PERT exists without `--force` → re-run with `--force`

### Git and repository hygiene

- The `estimations/` directory is part of the repo, but its contents are ignored via `.gitignore`, except for `.gitkeep`
- Generated artifacts won’t be committed accidentally; commit curated changes (personas, templates, scripts)

### Good practices for estimation

- **Granularity**: Break down tasks until O/M/P are defensible
- **Assumptions & risks**: Document constraints and uncertainties
- **Dependencies**: Call out cross-team/vendor dependencies
- **Peer review**: Review the breakdown and assumptions, not just totals

### Notes

- Confluence storage HTML is converted to Markdown with `markdownify` (fallback strips HTML tags if unavailable)
- Jira issue descriptions are fetched from rendered fields when available



