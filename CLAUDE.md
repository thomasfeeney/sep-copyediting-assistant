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
#   SEP_PASSWORD=your-chosen-password

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
│   ├── document_parser.py # Parses .docx/.html, strips editorial markup, preserves italics
│   └── gemini_analyzer.py # Gemini API integration, JSON parsing/repair
├── prompts/
│   └── sep_style.py       # SEP citation rules for LLM prompts
├── templates/             # Jinja2 templates (login, main UI)
├── static/style.css       # Stanford cardinal red theme
├── sample_data/           # Sample documents for demo
└── Dockerfile             # Cloud Run container
```

## Key Implementation Details

### Document Parsing (`services/document_parser.py`)
- Searches from END of document for "Bibliography" heading
- Preserves italics as `<i>...</i>` markers for LLM analysis
- Strips `<span class="todo_note">` editorial comments from HTML
- Strips endnote links (`notes.html`) from HTML to avoid confusing `[1]`, `[2]` markers with citations
- Supports both .docx and .html input

### LLM Prompt (`prompts/sep_style.py`)
- Encodes SEP bibliography format rules (journal articles, books, edited volumes, reprints, etc.)
- Handles historical works with modern editions, classical works without anachronistic dates
- Accepts ampersand (&) in parenthetical citations (SEP house style)
- Accepts `[Author Year available online]` accessibility format
- Distinguishes en-dashes in page ranges from hyphens in DOIs
- Instructs LLM to ignore endnote markers

### Gemini Integration (`services/gemini_analyzer.py`)
- Uses `max_output_tokens=32768` for large documents
- Includes JSON extraction and repair logic for truncated responses
- Prompt asks for counts + issues only to keep response size manageable

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Gemini API key |
| `SEP_PASSWORD` | Yes | Password for login gate (no default; must be set) |
| `SECRET_KEY` | No | Flask session secret |

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

## SEP Citation Style Rules (in prompts/sep_style.py)

- **Standard**: `(Author Year, page)` or `Author (Year, page)`
- **Historical works**: `(Author OriginalYear [ModernYear, page])`
- **Classical works**: `(Title, location)` - NO anachronistic dates
- **Bibliography**: Author, First, Year, "Title", *Journal*, Vol(Issue): pages.
- **Online materials**: `[Available online]` or `[Author Year available online]`
- **In-text ampersand**: `(Author & Author Year)` is accepted in parenthetical citations

## Priority TODO

1. **Migrate Gemini SDK** (`google-generativeai` -> `google-genai`). The old package was
   deprecated Nov 2025 and is no longer receiving updates. Migration is confined to
   `services/gemini_analyzer.py` and `requirements.txt`. Key changes:
   - `import google.generativeai as genai` -> `from google import genai` + `from google.genai import types`
   - `genai.configure(api_key=...)` -> `client = genai.Client(api_key=...)`
   - `genai.GenerativeModel(model_name=..., system_instruction=...)` -> pass both per-call
   - `model.generate_content(prompt, generation_config=genai.GenerationConfig(...))` ->
     `client.models.generate_content(model=..., contents=..., config=types.GenerateContentConfig(...))`
   - `system_instruction` moves from model constructor into `GenerateContentConfig`
   - `response.text` unchanged; JSON parsing/repair logic should not need changes
   - pip: `google-generativeai>=0.8.0` -> `google-genai>=1.0.0`
