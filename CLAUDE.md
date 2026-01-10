# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered copyediting assistant for the Stanford Encyclopedia of Philosophy (SEP). Helps editors verify citation/bibliography consistency and formatting compliance.

**Live URL**: https://sep-copyediting-assistant-suj4icznca-uw.a.run.app

## Tech Stack

- **Framework**: Python Flask with Jinja2 templates
- **LLM**: Google Gemini 3 Flash (`gemini-3-flash-preview`)
- **Document Parsing**: python-docx for .docx, BeautifulSoup for .html
- **Deployment**: Google Cloud Run (auto-deployed via GitHub Actions)

## Development

```bash
# Set up virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment - create .env with:
#   GOOGLE_API_KEY=your-key-here
#   SEP_PASSWORD=SEPeditor  (optional, default)

# Run development server
python app.py
# Opens at http://localhost:8080
```

## Project Structure

```
├── .github/workflows/
│   └── deploy.yml         # Auto-deploy to Cloud Run on push to main
├── app.py                 # Flask routes: /, /login, /analyze, /sample
├── config.py              # Environment config, model settings
├── services/
│   ├── document_parser.py # Parses .docx/.html, preserves italics
│   └── gemini_analyzer.py # Gemini API integration, JSON parsing
├── prompts/
│   └── sep_style.py       # SEP citation rules for LLM prompts
├── templates/             # Jinja2 templates
├── static/style.css       # Stanford cardinal red theme
├── sample_data/           # Sample documents for demo
└── Dockerfile             # Cloud Run container
```

## Key Implementation Details

### Document Parsing (`services/document_parser.py`)
- Searches from END of document for "Bibliography" heading
- Preserves italics as `<i>...</i>` markers for LLM analysis
- Supports both .docx and .html input

### Gemini Integration (`services/gemini_analyzer.py`)
- Uses `max_output_tokens=32768` for large documents
- Includes JSON extraction and repair logic for truncated responses
- Prompt asks for counts + issues only to keep response size manageable

## CI/CD

Every push to `main` auto-deploys to Cloud Run via GitHub Actions.

### GitHub Secrets Required
- `GCP_PROJECT_ID` - Google Cloud project ID
- `WIF_PROVIDER` - Workload Identity Federation provider
- `WIF_SERVICE_ACCOUNT` - Service account for deployments
- `SEP_PASSWORD` - App login password

### GCP Resources
- **Project**: sep-copyediting-assistant
- **Region**: us-west1
- **Secret Manager**: GOOGLE_API_KEY (Gemini API key)

## SEP Citation Style Rules

- **Standard**: `(Author Year, page)` or `Author (Year, page)`
- **Historical works**: `(Author OriginalYear [ModernYear, page])`
- **Classical works**: `(Title, location)` - NO anachronistic dates
- **Bibliography**: Author, First, Year, "Title", *Journal*, Vol(Issue): pages.
