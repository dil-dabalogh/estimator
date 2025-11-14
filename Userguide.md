# User Guide

## Overview

The Estimation Tool generates Business Analyst notes and PERT estimates from Confluence pages or Jira issues using AI. The tool provides real-time progress updates and allows you to download the generated artifacts.

## Getting Started

1. Open the web application in your browser
2. You'll see a form where you can enter Confluence or Jira URLs

## Setting Up Confluence Export (Optional)

Before creating estimations, you can configure where exported estimations will be saved in Confluence:

1. In the "Confluence Estimation Location" section, enter the URL of the parent Confluence page
   - Example: `https://diligentbrands.atlassian.net/wiki/spaces/RCP/pages/5699995053/Top-down+Estimation`
2. This location will be used for all exports in the current session
3. You can leave this blank if you don't plan to export to Confluence

## Creating Estimations

### Single Estimation

1. Enter a Confluence page URL or Jira issue URL
2. The name field will automatically populate with the page/issue title after a brief moment
   - You can edit this name to customize it
   - A loading spinner appears while fetching the title
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

- XS (Green): < 2 weeks
- S (Blue): 2-4 weeks
- M (Yellow): 4-8 weeks
- L (Orange): 8-16 weeks
- XL (Red): 16-26 weeks
- XXL (Purple): ≥ 26 weeks

### Man-week Estimates

The tool extracts the total man-week estimate from the PERT analysis.

## Downloading Results

1. Wait for the estimation to complete (green checkmark)
2. Click "Download" under BA Notes to get the Business Analyst notes
3. Click "Download" under PERT to get the PERT estimation
4. Files are downloaded as Markdown (.md) files

## Exporting to Confluence

Once an estimation is completed, you can export it directly to Confluence:

### Prerequisites
- Enter a parent page URL in the "Confluence Estimation Location" field before or after generating estimations
- Ensure you have edit permissions on the target Confluence space

### Exporting
1. Wait for the estimation to complete (green checkmark)
2. In the "Export to Confluence" column, click the "Export" button
3. The button will show "Exporting..." while creating the page
4. On success:
   - The button changes to "View Page"
   - Click "View Page" to open the created Confluence page in a new tab
5. On failure:
   - An error message appears below the button
   - Common errors:
     - **"Page already exists"**: A page with this name already exists in the target location
     - **"Please enter a Confluence parent page URL"**: You need to set the parent location first
     - **Network errors**: Check your internet connection and Confluence access

### Content Structure
The exported Confluence page contains:
1. **PERT Estimate** (top section)
2. **Separator line**
3. **BA Estimation Notes** (bottom section)

All content is formatted using Confluence's markdown rendering for proper display.

### Important Notes
- Each estimation must have a unique name to avoid conflicts
- Pages are created as children of the configured parent page
- If a page with the same name exists, the export will fail (duplicate prevention)
- You can export multiple estimations to the same parent location

## Error Handling

If an estimation fails:
- An error icon will appear in the Status column
- The error message will be displayed below the table
- Other estimations in the batch will continue processing

## Tips

- Names are automatically fetched from Confluence/Jira pages when you enter a URL
- You can edit the auto-populated name before submitting
- Use descriptive names for your estimations for easy identification
- The ballpark parameter helps guide the AI to align estimates
- Multiple estimations are processed in parallel for speed
- Keep the browser tab open while processing
- Set up the Confluence export location at the start of your session to streamline the workflow
- Use clear, unique names to avoid duplicate page errors when exporting to Confluence
- The "View Page" button after successful export opens the page in a new tab so you can continue working

