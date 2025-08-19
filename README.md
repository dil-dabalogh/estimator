## PERT Estimation Workspace

This repository provides a lightweight, Markdown-first workflow for PERT (Program Evaluation and Review Technique) estimation. It includes a reusable template and an `estimations/` folder to keep estimates organized and reviewable in version control.

### What is PERT?

PERT models three time estimates for each task:

- **Optimistic (O)**: Best-case duration assuming everything goes well
- **Most likely (M)**: Realistic duration given typical conditions
- **Pessimistic (P)**: Worst-case duration assuming notable risks occur

From these, you compute:

- **Expected duration (E)**: \( E = \frac{O + 4M + P}{6} \)
- **Standard deviation (σ)**: \( \sigma = \frac{P - O}{6} \)
- **Variance (σ²)**: \( \sigma^2 = \left(\frac{P - O}{6}\right)^2 \)

Project- or workstream-level uncertainty can be approximated by summing task variances on the critical path and taking the square root for overall σ. Confidence windows (assuming approximate normality):

- **~68%**: \( E \pm 1\sigma \)
- **~95%**: \( E \pm 2\sigma \)
- **~99.7%**: \( E \pm 3\sigma \)

Note: PERT is a model; use judgment. Task independence and normality assumptions rarely hold perfectly.

### Repository layout

- `templates/PERT_TEMPLATE.md`: Canonical Markdown template for new estimates
- `estimations/`: Place all new Markdown estimates here
- Root contains legacy Excel artifacts for reference only; new estimates should use Markdown

### Create a new estimate (quick start)

1. Copy the template:
   - `cp templates/PERT_TEMPLATE.md estimations/2025-01-01-my-project-my-feature.md`
2. Fill the metadata block (title, date, author, assumptions, risks, dependencies).
3. Add or edit tasks in the table with O/M/P values. Compute E and σ per row using the formulas above.
4. Roll up totals and compute overall σ and confidence ranges for the scope you care about (e.g., critical path or entire set with caution).
5. Commit the estimate so changes are tracked in version control.

### Good practices

- **Granularity**: Break down tasks until O/M/P can be reasoned about (often 0.5–3 days per task in knowledge work).
- **Rationales**: Briefly note why P is larger than O—dependencies, unknowns, or risks.
- **Dependencies**: Call out cross-team or vendor dependencies explicitly.
- **Assumptions**: List constraints (environments, access, data availability) to make the estimate auditable.
- **Review**: Have a peer review the breakdown and assumptions, not just the totals.

### Example row computation

For a row with `O=4h`, `M=6h`, `P=10h`:

- `E = (4 + 4×6 + 10) / 6 = (4 + 24 + 10) / 6 = 38 / 6 ≈ 6.33h`
- `σ = (10 − 4) / 6 = 6 / 6 = 1.0h`

### Conventions

- Units: hours are preferred for task-level detail; days can be used for rollups (assume 1 day = 8 hours unless stated otherwise).
- File names: `YYYY-MM-DD-project-feature.md`
- Use plain Markdown to keep estimates readable and diff-friendly.

### Legacy Excel artifacts

This repository previously used Excel-based PERT templates. They are kept at the root for reference only. New estimates should be Markdown-based using `templates/PERT_TEMPLATE.md`.

### Orchestrator CLI

The `scripts/orchestrator.py` script automates estimation with personas:

- Reads BA and Engineer personas from `personas/`
- Takes a Confluence URL, fetches the page content via Confluence API
- Generates BA estimation notes (Markdown)
- Generates a completed PERT estimation sheet using `templates/PERT_TEMPLATE.md`
- Writes all artifacts into a fresh folder under `estimations/`

#### Setup

1. Python 3.10+
2. Install deps:

```bash
pip install -r requirements.txt
```

3. Environment variables (Atlassian Cloud + OpenAI):

```bash
export ATLASSIAN_URL="https://<your-domain>.atlassian.net/wiki"
export ATLASSIAN_USER_EMAIL="you@company.com"
export ATLASSIAN_API_TOKEN="<token>"
export OPENAI_API_KEY="<openai-key>"
```

#### Usage

```bash
python scripts/orchestrator.py "https://<your-domain>.atlassian.net/wiki/spaces/SPACE/pages/<pageId>/Title" \
  --name "MyFeature" \
  --model gpt-4o-mini
```

Outputs include:
- `estimations/MyFeature-YYYYMMDD-HHMMSS/BA_Estimation_Notes.md`
- `estimations/.../PERT_Estimate.md`
- `estimations/.../input.confluence.page.md`
- `estimations/.../PERT_TEMPLATE.md`
- `estimations/.../metadata.json`

Notes:
- Confluence storage HTML is converted to Markdown via `markdownify` with a simple fallback.
- You can switch the OpenAI model via `--model`.

### Roadmap (optional)

- Add a small CLI or script to parse Markdown tables and compute rollups automatically.
- Add CI checks that validate table structure and recompute totals.


