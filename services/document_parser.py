"""
Document parser for .docx and .html files.
Preserves formatting information (especially italics) for accurate analysis.
"""

import re
from io import BytesIO
from typing import Tuple
from docx import Document
from docx.shared import Pt
from bs4 import BeautifulSoup


def parse_docx(file_content: bytes) -> Tuple[str, str]:
    """
    Parse a .docx file and extract text with formatting markers.

    Returns:
        Tuple of (main_text, bibliography_text)
        Text includes <i>...</i> markers for italicized content.
    """
    doc = Document(BytesIO(file_content))

    # First pass: collect all paragraphs with formatting
    all_paragraphs = []
    for para in doc.paragraphs:
        para_parts = []
        for run in para.runs:
            text = run.text
            if not text:
                continue
            if run.italic:
                text = f'<i>{text}</i>'
            para_parts.append(text)
        para_text = ''.join(para_parts)
        all_paragraphs.append((para.text.strip(), para_text))  # (raw_text, formatted_text)

    # Second pass: find the LAST occurrence of bibliography heading
    # (it should be near the end of the document)
    bib_headings = ['bibliography', 'references', 'works cited']
    bib_index = -1

    # Search from the end, but bibliography should be in roughly the last 30% of doc
    min_search_index = len(all_paragraphs) // 2  # Don't look in first half

    for i in range(len(all_paragraphs) - 1, min_search_index, -1):
        raw_text = all_paragraphs[i][0].lower()
        if raw_text in bib_headings:
            bib_index = i
            break

    # If not found in latter half, search more broadly but prefer later occurrences
    if bib_index == -1:
        for i in range(len(all_paragraphs) - 1, -1, -1):
            raw_text = all_paragraphs[i][0].lower()
            if raw_text in bib_headings:
                bib_index = i
                break

    # Split into main text and bibliography
    if bib_index != -1:
        main_text_parts = [p[1] for p in all_paragraphs[:bib_index]]
        bibliography_parts = [p[1] for p in all_paragraphs[bib_index + 1:]]
    else:
        main_text_parts = [p[1] for p in all_paragraphs]
        bibliography_parts = []

    # Clean up
    main_text = '\n\n'.join(main_text_parts)
    main_text = _clean_italic_tags(main_text)

    bibliography_text = '\n\n'.join(bibliography_parts)
    bibliography_text = _clean_italic_tags(bibliography_text)

    return main_text, bibliography_text


def parse_html(file_content: bytes) -> Tuple[str, str]:
    """
    Parse an .html file and extract text with formatting preserved.

    Returns:
        Tuple of (main_text, bibliography_text)
    """
    # Try to decode with common encodings
    for encoding in ['utf-8', 'latin-1', 'cp1252']:
        try:
            html_str = file_content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        html_str = file_content.decode('utf-8', errors='replace')

    soup = BeautifulSoup(html_str, 'lxml')

    # Remove script and style elements
    for element in soup(['script', 'style', 'meta', 'link']):
        element.decompose()

    # Remove SEP editorial todo_note comments (e.g., <span class="todo_note">***words*</span>)
    for element in soup.find_all(class_='todo_note'):
        element.decompose()

    # Remove endnote markers (superscripted links to notes.html like [1], [2], etc.)
    for a_tag in soup.find_all('a', href=True):
        if 'notes.html' in a_tag['href']:
            a_tag.decompose()

    # Find bibliography section
    bib_section = None
    bib_header = None

    # Look for bibliography heading
    for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div']:
        for elem in soup.find_all(tag):
            text = elem.get_text().strip().lower()
            if text in ['bibliography', 'references', 'works cited']:
                bib_header = elem
                break
        if bib_header:
            break

    # Extract main text and bibliography
    if bib_header:
        # Get all content before bibliography
        main_parts = []
        bib_parts = []
        found_bib = False

        for elem in soup.body.descendants if soup.body else soup.descendants:
            if elem == bib_header:
                found_bib = True
                continue

            if hasattr(elem, 'get_text'):
                # Skip if this is a parent of bib_header
                if bib_header in elem.descendants if hasattr(elem, 'descendants') else False:
                    continue

        # Simpler approach: split by bibliography header
        full_html = str(soup)
        bib_patterns = [
            r'<h\d[^>]*>\s*Bibliography\s*</h\d>',
            r'<p[^>]*>\s*<b>\s*Bibliography\s*</b>\s*</p>',
            r'<p[^>]*>\s*<strong>\s*Bibliography\s*</strong>\s*</p>',
        ]

        split_point = None
        for pattern in bib_patterns:
            match = re.search(pattern, full_html, re.IGNORECASE)
            if match:
                split_point = match.start()
                break

        if split_point:
            main_soup = BeautifulSoup(full_html[:split_point], 'lxml')
            bib_soup = BeautifulSoup(full_html[split_point:], 'lxml')
        else:
            main_soup = soup
            bib_soup = BeautifulSoup('', 'lxml')
    else:
        main_soup = soup
        bib_soup = BeautifulSoup('', 'lxml')

    main_text = _extract_text_with_formatting(main_soup)
    bibliography_text = _extract_text_with_formatting(bib_soup)

    return main_text, bibliography_text


def _extract_text_with_formatting(soup: BeautifulSoup) -> str:
    """Extract text from soup, preserving italic markers."""
    # Convert <i>, <em>, and italic-styled spans to markers
    for tag in soup.find_all(['i', 'em']):
        tag.insert_before('<i>')
        tag.insert_after('</i>')
        tag.unwrap()

    # Handle styled spans (Word often uses these)
    for span in soup.find_all('span'):
        style = span.get('style', '')
        if 'italic' in style.lower():
            span.insert_before('<i>')
            span.insert_after('</i>')

    text = soup.get_text(separator='\n')
    text = _clean_italic_tags(text)

    # Clean up excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +', ' ', text)

    return text.strip()


def _clean_italic_tags(text: str) -> str:
    """Clean up consecutive or nested italic tags."""
    # Merge consecutive italic tags
    text = re.sub(r'</i>\s*<i>', '', text)
    # Remove empty italic tags
    text = re.sub(r'<i>\s*</i>', '', text)
    return text


def detect_bibliography_with_llm(text: str) -> str:
    """
    Fallback: Use LLM to identify the bibliography section if heading-based
    detection fails. This is called from the analyzer service.
    """
    # This function exists as a placeholder - the actual LLM call
    # happens in gemini_analyzer.py
    return ""


def get_document_text(file_content: bytes, filename: str) -> Tuple[str, str]:
    """
    Parse a document and return main text and bibliography.

    Args:
        file_content: Raw file bytes
        filename: Original filename (used to determine format)

    Returns:
        Tuple of (main_text, bibliography_text)
    """
    filename_lower = filename.lower()

    if filename_lower.endswith('.docx'):
        return parse_docx(file_content)
    elif filename_lower.endswith('.html') or filename_lower.endswith('.htm'):
        return parse_html(file_content)
    else:
        raise ValueError(f"Unsupported file format: {filename}. Please upload .docx or .html files.")
