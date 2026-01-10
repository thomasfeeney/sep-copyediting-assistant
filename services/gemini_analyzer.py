"""
Gemini LLM integration for citation/bibliography analysis.
"""

import json
import re
from typing import Optional
import google.generativeai as genai
from prompts.sep_style import SYSTEM_PROMPT, ANALYSIS_PROMPT


class AnalysisResult:
    """Container for analysis results."""

    def __init__(self, raw_response: dict):
        # Handle new counts format or legacy format
        counts = raw_response.get('counts', {})
        self.total_citations = counts.get('citations', 0)
        self.total_bibliography = counts.get('bibliography_entries', 0)

        # Legacy support: if old format with arrays
        if 'citations_found' in raw_response:
            self.total_citations = len(raw_response.get('citations_found', []))
        if 'bibliography_entries' in raw_response and isinstance(raw_response['bibliography_entries'], list):
            self.total_bibliography = len(raw_response.get('bibliography_entries', []))

        self.orphan_citations = raw_response.get('orphan_citations', [])
        self.orphan_bibliography = raw_response.get('orphan_bibliography', [])
        self.format_issues = raw_response.get('format_issues', [])
        self.error = raw_response.get('error')

    def has_issues(self) -> bool:
        """Check if any issues were found."""
        return bool(self.orphan_citations or self.orphan_bibliography or self.format_issues)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'orphan_citations': self.orphan_citations,
            'orphan_bibliography': self.orphan_bibliography,
            'format_issues': self.format_issues,
            'error': self.error,
            'summary': {
                'total_citations': self.total_citations,
                'total_bibliography': self.total_bibliography,
                'orphan_citations_count': len(self.orphan_citations),
                'orphan_bibliography_count': len(self.orphan_bibliography),
                'format_issues_count': len(self.format_issues),
            }
        }


class GeminiAnalyzer:
    """Analyzer using Google Gemini for SEP document analysis."""

    def __init__(self, api_key: str, model_name: str = 'gemini-2.0-flash'):
        """
        Initialize the Gemini analyzer.

        Args:
            api_key: Google API key for Gemini
            model_name: Gemini model to use
        """
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_PROMPT
        )

    def analyze_document(self, main_text: str, bibliography_text: str) -> AnalysisResult:
        """
        Analyze a document for citation/bibliography issues.

        Args:
            main_text: The main body of the document (with italic markers)
            bibliography_text: The bibliography section (with italic markers)

        Returns:
            AnalysisResult containing all findings
        """
        # Construct the full document for analysis
        document = f"""
=== MAIN TEXT ===
{main_text}

=== BIBLIOGRAPHY ===
{bibliography_text}
"""

        prompt = ANALYSIS_PROMPT + document

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=1.0,
                    max_output_tokens=32768,
                )
            )

            # Parse the JSON response
            result_text = response.text

            # Try to extract JSON from the response (may be wrapped in markdown code blocks)
            result_data = self._extract_json(result_text)
            if result_data:
                return AnalysisResult(result_data)

            # If extraction failed, try direct parse
            result_data = json.loads(result_text)
            return AnalysisResult(result_data)

        except json.JSONDecodeError as e:
            # Try to extract and repair JSON from the response
            result_text = response.text if 'response' in dir() else ''

            # Try to find and parse the most complete JSON object
            repaired_json = self._try_repair_json(result_text)
            if repaired_json:
                return AnalysisResult(repaired_json)

            return AnalysisResult({
                'error': f"Failed to parse LLM response as JSON: {str(e)}. The document may be too large - try a shorter section."
            })

        except Exception as e:
            return AnalysisResult({
                'error': f"Analysis failed: {str(e)}"
            })

    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract JSON from response that may have markdown or other text."""
        if not text:
            return None

        # Remove markdown code blocks if present
        text = text.strip()
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()

        # Try to parse directly
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in the text
        start = text.find('{')
        if start != -1:
            # Find matching closing brace
            depth = 0
            for i, char in enumerate(text[start:], start):
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i+1])
                        except json.JSONDecodeError:
                            break

        return None

    def _try_repair_json(self, text: str) -> Optional[dict]:
        """Attempt to repair truncated JSON responses."""
        if not text:
            return None

        # First try: direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Second try: find JSON object
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Third try: truncated JSON - close open structures
        try:
            # Find the start of JSON
            start = text.find('{')
            if start == -1:
                return None

            truncated = text[start:]

            # Count open brackets/braces
            open_braces = truncated.count('{') - truncated.count('}')
            open_brackets = truncated.count('[') - truncated.count(']')

            # Check if we're in a string (odd number of unescaped quotes)
            in_string = False
            i = len(truncated) - 1
            while i >= 0 and truncated[i] != '\n':
                if truncated[i] == '"' and (i == 0 or truncated[i-1] != '\\'):
                    in_string = not in_string
                i -= 1

            # Close the string if needed
            if in_string:
                truncated += '"'

            # Close arrays and objects
            truncated += ']' * open_brackets
            truncated += '}' * open_braces

            return json.loads(truncated)
        except (json.JSONDecodeError, Exception):
            pass

        return None

    def detect_bibliography_section(self, full_text: str) -> Optional[str]:
        """
        Use LLM to identify the bibliography section when heading-based
        detection fails.

        Args:
            full_text: The complete document text

        Returns:
            The bibliography section text, or None if not found
        """
        prompt = """Examine the following document and extract ONLY the bibliography/references section.
Return just the bibliography entries, one per line. If there is no clear bibliography section, return "NO_BIBLIOGRAPHY_FOUND".

Document:
""" + full_text

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                )
            )

            result = response.text.strip()
            if result == "NO_BIBLIOGRAPHY_FOUND":
                return None
            return result

        except Exception:
            return None
