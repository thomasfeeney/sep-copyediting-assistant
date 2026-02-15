# SEP Copyediting Assistant

AI-powered copyediting assistant for the [Stanford Encyclopedia of Philosophy](https://plato.stanford.edu/) (SEP). Helps editors verify citation/bibliography consistency and formatting compliance.

## Features

- Upload .docx or .html documents for analysis
- Identifies orphan citations (cited but not in bibliography)
- Identifies orphan bibliography entries (in bibliography but never cited)
- Checks bibliography formatting against SEP style rules
- Flags low-confidence findings separately
- Handles SEP-specific conventions: historical works with modern editions, classical works without anachronistic dates, em-dash page ranges, `[Author Year available online]` accessibility format
- Strips SEP editorial markup (`todo_note` comments, endnote links) before analysis

## Tech Stack

- **Framework**: Python Flask with Jinja2 templates
- **LLM**: Google Gemini 3 Flash (`gemini-3-flash-preview`)
- **Document Parsing**: python-docx for .docx, BeautifulSoup for .html
- **Deployment**: Google Cloud Run (auto-deployed via GitHub Actions)

## Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with required variables
echo "GOOGLE_API_KEY=your-gemini-api-key" > .env
echo "SEP_PASSWORD=your-chosen-password" >> .env

# Run the app
python app.py
```

Visit http://localhost:8080 and log in with the password you set in `.env`.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Gemini API key from [Google AI Studio](https://aistudio.google.com/) |
| `SEP_PASSWORD` | Yes | Password for the app login gate |
| `SECRET_KEY` | No | Flask session secret (a default is used in development) |

## Deployment

Pushes to `main` automatically deploy to Google Cloud Run via GitHub Actions. The production password and API key are managed through GitHub Secrets and GCP Secret Manager, respectively.

## Project Structure

```
├── app.py                 # Flask routes: /, /login, /analyze, /sample
├── config.py              # Environment config, model settings
├── services/
│   ├── document_parser.py # Parses .docx/.html, strips editorial markup, preserves italics
│   └── gemini_analyzer.py # Gemini API integration, JSON parsing/repair
├── prompts/
│   └── sep_style.py       # SEP citation rules embedded in LLM prompts
├── templates/             # Jinja2 templates (login, main UI)
├── static/style.css       # Stanford cardinal red theme
├── sample_data/           # Sample documents for demo
├── Dockerfile             # Cloud Run container
└── .github/workflows/
    └── deploy.yml         # Auto-deploy to Cloud Run on push to main
```

## License

For use by the Stanford Encyclopedia of Philosophy.
