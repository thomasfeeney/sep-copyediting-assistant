# SEP Copyediting Assistant

AI-powered copyediting assistant for the Stanford Encyclopedia of Philosophy (SEP). Helps editors verify citation/bibliography consistency and formatting compliance.

**Live**: https://sep-copyediting-assistant-suj4icznca-uw.a.run.app

## Features

- Upload .docx or .html documents for analysis
- Identifies orphan citations (cited but not in bibliography)
- Identifies orphan bibliography entries (in bibliography but never cited)
- Checks citation format compliance with SEP style guide
- Flags low-confidence findings separately

## Tech Stack

- Python Flask
- Google Gemini 3 Flash for document analysis
- python-docx and BeautifulSoup for document parsing
- Google Cloud Run for deployment

## Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "GOOGLE_API_KEY=your-gemini-api-key" > .env
echo "SEP_PASSWORD=SEPeditor" >> .env

# Run the app
python app.py
```

Visit http://localhost:8080 and login with password `SEPeditor`.

## Deployment

Pushes to `main` automatically deploy to Google Cloud Run via GitHub Actions.

## License

Private - Stanford Encyclopedia of Philosophy
