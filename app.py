"""
SEP Copyediting Assistant - Flask Application
"""

import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from config import Config
from services.document_parser import get_document_text
from services.gemini_analyzer import GeminiAnalyzer

app = Flask(__name__)
app.config.from_object(Config)


def get_analyzer(model_name: str = None):
    """Create a Gemini analyzer with the specified model."""
    if model_name is None:
        model_name = Config.DEFAULT_MODEL
    # Validate model name
    if model_name not in Config.GEMINI_MODELS:
        model_name = Config.DEFAULT_MODEL
    return GeminiAnalyzer(
        api_key=app.config['GOOGLE_API_KEY'],
        model_name=model_name
    )


def login_required(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login."""
    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == app.config['SEP_PASSWORD']:
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            error = 'Invalid password'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    """Handle logout."""
    session.pop('authenticated', None)
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """Main application page."""
    return render_template(
        'index.html',
        models=Config.GEMINI_MODELS,
        default_model=Config.DEFAULT_MODEL
    )


@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    """Analyze an uploaded document."""
    # Check for file upload
    if 'document' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['document']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Check file extension
    filename = file.filename.lower()
    if not (filename.endswith('.docx') or filename.endswith('.html') or filename.endswith('.htm')):
        return jsonify({'error': 'Please upload a .docx or .html file'}), 400

    # Get selected model
    selected_model = request.form.get('model', Config.DEFAULT_MODEL)

    try:
        # Read file content
        file_content = file.read()

        # Parse the document
        main_text, bibliography_text = get_document_text(file_content, file.filename)

        # Check if bibliography was found
        if not bibliography_text.strip():
            # Try LLM-based detection
            analyzer = get_analyzer(selected_model)
            full_text = main_text + "\n\n" + bibliography_text
            detected_bib = analyzer.detect_bibliography_section(full_text)
            if detected_bib:
                bibliography_text = detected_bib
            else:
                return jsonify({
                    'error': 'Could not identify a Bibliography section. Please ensure your document has a clearly labeled "Bibliography" heading.'
                }), 400

        # Analyze the document
        analyzer = get_analyzer(selected_model)
        result = analyzer.analyze_document(main_text, bibliography_text)

        if result.error:
            return jsonify({'error': result.error}), 500

        return jsonify(result.to_dict())

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500


@app.route('/sample')
@login_required
def load_sample():
    """Load the sample Leibniz document for demonstration."""
    sample_path = os.path.join(app.root_path, 'sample_data', 'leibniz-evil.docx')

    if not os.path.exists(sample_path):
        return jsonify({'error': 'Sample file not found'}), 404

    # Get selected model from query string
    selected_model = request.args.get('model', Config.DEFAULT_MODEL)

    try:
        with open(sample_path, 'rb') as f:
            file_content = f.read()

        # Parse the document
        main_text, bibliography_text = get_document_text(file_content, 'leibniz-evil.docx')

        # Check if bibliography was found
        if not bibliography_text.strip():
            analyzer = get_analyzer(selected_model)
            full_text = main_text + "\n\n" + bibliography_text
            detected_bib = analyzer.detect_bibliography_section(full_text)
            if detected_bib:
                bibliography_text = detected_bib

        # Analyze the document
        analyzer = get_analyzer(selected_model)
        result = analyzer.analyze_document(main_text, bibliography_text)

        if result.error:
            return jsonify({'error': result.error}), 500

        return jsonify(result.to_dict())

    except Exception as e:
        return jsonify({'error': f'Failed to load sample: {str(e)}'}), 500


@app.route('/download-sample')
@login_required
def download_sample():
    """Download the sample Leibniz document."""
    return send_from_directory(
        os.path.join(app.root_path, 'sample_data'),
        'leibniz-evil.docx',
        as_attachment=True
    )


@app.route('/health')
def health():
    """Health check endpoint for Cloud Run."""
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    # Development server
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
