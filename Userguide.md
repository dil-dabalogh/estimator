# User Guide

## Overview

The Estimation Tool generates Business Analyst notes and PERT estimates from Confluence pages or Jira issues using AI. The tool provides real-time progress updates and allows you to download the generated artifacts.

## Getting Started

1. Open the web application in your browser
2. You'll see a form where you can enter Confluence or Jira URLs

## Creating Estimations

### Single Estimation

1. Enter a Confluence page URL or Jira issue URL
2. Provide a unique name for this estimation
3. Optionally, enter a ballpark estimate (e.g., "30 manweeks")
4. Click "Generate Estimations"

### Multiple Estimations

1. Click "Add Another URL" to add more estimation requests
2. Each URL needs a unique name
3. You can remove URLs by clicking the X button
4. Click "Generate Estimations" when ready

### URL Formats Supported

**Confluence:**
- `https://your-domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Page-Title`
- `https://your-domain.atlassian.net/wiki/pages/viewpage.action?pageId=123456`

**Jira:**
- `https://your-domain.atlassian.net/browse/PROJECT-123`

## Understanding Results

### Real-time Progress

Once you submit, you'll see a results table with real-time progress for each estimation:

- Fetching - Retrieving content from Confluence/Jira
- BA Generation - Creating Business Analyst notes
- PERT Generation - Creating PERT estimation
- Completed - Ready to download
- Failed - An error occurred

### T-shirt Sizes

The tool automatically calculates a T-shirt size based on the PERT man-week estimate:

- XS (Green): < 1 week
- S (Blue): < 6 weeks
- M (Yellow): < 12 weeks
- L (Orange): < 40 weeks
- XL (Red): < 60 weeks
- XXL (Purple): ≥ 60 weeks

### Man-week Estimates

The tool extracts the total man-week estimate from the PERT analysis.

## Downloading Results

1. Wait for the estimation to complete (green checkmark)
2. Click "Download" under BA Notes to get the Business Analyst notes
3. Click "Download" under PERT to get the PERT estimation
4. Files are downloaded as Markdown (.md) files

## Error Handling

If an estimation fails:
- An error icon will appear in the Status column
- The error message will be displayed below the table
- Other estimations in the batch will continue processing

## Tips

- Use descriptive names for your estimations for easy identification
- The ballpark parameter helps guide the AI to align estimates
- Multiple estimations are processed in parallel for speed
- Keep the browser tab open while processing

