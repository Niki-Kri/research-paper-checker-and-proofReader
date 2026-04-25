from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

import pdfplumber
import language_tool_python
import fitz
import textstat
import re
import io
import os


app = Flask(__name__)
CORS(app)

tool = language_tool_python.LanguageTool("en-US")




# ============================================================
# ROLE: Niki Kumari - Format Checker
# Publisher rules used for checking research paper format
# ============================================================

FORMAT_RULES = {
    "IEEE": {
        "font": "Times",
        "font_size": 10,
        "columns": 2,
        "sections": [
            "Abstract",
            "Introduction",
            "Methodology",
            "Results",
            "Conclusion",
            "References"
        ]
    },

    "Springer": {
        "font": "Times",
        "font_size": 10,
        "columns": 2,
        "sections": [
            "Abstract",
            "Introduction",
            "Related Work",
            "Methodology",
            "Results",
            "Conclusion",
            "References"
        ]
    },

    "Elsevier": {
        "font": "Times",
        "font_size": 11,
        "columns": 1,
        "sections": [
            "Abstract",
            "Introduction",
            "Methodology",
            "Results",
            "Discussion",
            "Conclusion",
            "References"
        ]
    }
}


@app.route("/")
def home():
    return "Research Paper Format Checker Backend Running"


# ============================================================
# ROLE: Sukriti Kumari - PDF Ingestion
# This part extracts text and PDF bytes from uploaded paper
# ============================================================

def extract_text_from_pdf(file_bytes):
    text = ""

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

    except Exception as e:
        print("PDF text extraction error:", e)

    return text


def get_pdf_doc(file_bytes):
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return doc
    except Exception as e:
        print("PDF opening error:", e)
        return None


def detect_title(text):
    lines = text.split("\n")

    skip_words = [
        "abstract",
        "keywords",
        "index terms",
        "introduction",
        "methodology",
        "results",
        "discussion",
        "conclusion",
        "references"
    ]

    for line in lines[:20]:
        clean_line = line.strip()

        if not clean_line:
            continue

        if clean_line.lower() in skip_words:
            continue

        if 5 < len(clean_line) < 150:
            return clean_line

    return "Title not detected"


def extract_description(text):
    lower_text = text.lower()

    match = re.search(
        r"abstract\s*(.*?)(introduction|keywords|index terms|1\.)",
        lower_text,
        re.DOTALL
    )

    if match:
        start = match.start(1)
        end = match.end(1)
        description = text[start:end]
    else:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        description = " ".join(lines[:7])

    description = re.sub(r"\s+", " ", description).strip()

    if len(description) > 800:
        description = description[:800] + "..."

    return description


# ============================================================
# ROLE: Niki Kumari - Format Checker
# This part checks publisher, sections, font, size and columns
# ============================================================

def detect_publisher(text):
    text = text.lower()

    scores = {
        "IEEE": 0,
        "Springer": 0,
        "Elsevier": 0
    }

    if "ieee" in text:
        scores["IEEE"] += 3
    if "index terms" in text:
        scores["IEEE"] += 2
    if re.search(r"\[\d+\]", text):
        scores["IEEE"] += 1

    if "springer" in text:
        scores["Springer"] += 3
    if "keywords:" in text:
        scores["Springer"] += 1

    if "elsevier" in text:
        scores["Elsevier"] += 3
    if "article history" in text:
        scores["Elsevier"] += 2

    best = max(scores, key=scores.get)

    if scores[best] == 0:
        return "Unknown Format"

    return best


def check_sections(text, required_sections):
    lower_text = text.lower()
    sections = {}

    for section in required_sections:
        sec = section.lower()

        if sec in lower_text:
            sections[section] = "Found"

        elif section == "Methodology" and "methods" in lower_text:
            sections[section] = "Found"

        else:
            sections[section] = "Not Found"

    return sections


def calculate_structure_score(sections):
    total = len(sections)
    found = 0

    for status in sections.values():
        if status == "Found":
            found += 1

    if total == 0:
        return 0

    return round((found / total) * 10, 2)


def detect_basic_layout(file_bytes):
    doc = get_pdf_doc(file_bytes)

    result = {
        "font": "Not detected",
        "font_size": 0,
        "columns": 1
    }

    if doc is None or len(doc) == 0:
        return result

    try:
        first_page = doc[0]
        blocks = first_page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()

                    if len(text) > 3:
                        result["font"] = span["font"]
                        result["font_size"] = round(span["size"])
                        break

                if result["font"] != "Not detected":
                    break

            if result["font"] != "Not detected":
                break

        page_width = first_page.rect.width
        text_blocks = first_page.get_text("blocks")

        left_blocks = 0
        right_blocks = 0

        for block in text_blocks:
            x0 = block[0]

            if x0 < page_width / 2:
                left_blocks += 1
            else:
                right_blocks += 1

        if left_blocks > 2 and right_blocks > 2:
            result["columns"] = 2
        else:
            result["columns"] = 1

    except Exception as e:
        print("Layout detection error:", e)

    return result


def detect_formatting_violations(file_bytes, rules):
    doc = get_pdf_doc(file_bytes)
    issues = []

    if doc is None:
        return issues

    try:
        for page_no, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()

                        if not text or len(text) < 4:
                            continue

                        font_name = span["font"]
                        font_size = round(span["size"], 2)

                        expected_font = rules["font"]
                        expected_size = rules["font_size"]

                        if expected_font not in font_name:
                            issues.append({
                                "type": "Font Type Violation",
                                "text": text[:60],
                                "page": page_no + 1,
                                "found": font_name,
                                "expected": expected_font
                            })

                        if abs(font_size - expected_size) > 1:
                            issues.append({
                                "type": "Font Size Violation",
                                "text": text[:60],
                                "page": page_no + 1,
                                "found": font_size,
                                "expected": expected_size
                            })

                        if len(issues) >= 50:
                            return issues

    except Exception as e:
        print("Formatting violation error:", e)

    return issues


def compare_with_all_formats(text, file_bytes):
    format_results = {}
    layout = detect_basic_layout(file_bytes)

    for format_name, rules in FORMAT_RULES.items():
        sections = check_sections(text, rules["sections"])
        structure_score = calculate_structure_score(sections)

        formatting_issues = []

        if layout["font"] != "Not detected":
            if rules["font"] not in layout["font"]:
                formatting_issues.append({
                    "type": "Font Issue",
                    "message": f"Expected {rules['font']} font but found {layout['font']}"
                })

        if layout["font_size"] != 0:
            if layout["font_size"] != rules["font_size"]:
                formatting_issues.append({
                    "type": "Font Size Issue",
                    "message": f"Expected font size {rules['font_size']} but found {layout['font_size']}"
                })

        if layout["columns"] != rules["columns"]:
            formatting_issues.append({
                "type": "Column Layout Issue",
                "message": f"Expected {rules['columns']} column layout but found {layout['columns']}"
            })

        issue_penalty = min(len(formatting_issues), 5)
        format_score = round((structure_score * 0.7) + ((10 - issue_penalty) * 0.3), 2)

        format_results[format_name] = {
            "score": format_score,
            "sections": sections,
            "formatting_issues": formatting_issues
        }

    return format_results


# ============================================================
# ROLE: Vinay Verma - Citation Checker
# This part detects citation count and citation style
# ============================================================

def detect_citation_style(text):
    ieee_count = len(re.findall(r"\[\d+\]", text))
    apa_count = len(re.findall(r"\([A-Za-z]+,\s*\d{4}\)", text))
    mla_count = len(re.findall(r"\([A-Za-z]+\s+\d+\)", text))
    chicago_count = len(re.findall(r"\n\s*\d+\.\s+[A-Z]", text))

    scores = {
        "IEEE": ieee_count,
        "APA": apa_count,
        "MLA": mla_count,
        "Chicago": chicago_count
    }

    detected_style = max(scores, key=scores.get)

    if scores[detected_style] == 0:
        return "Unknown", scores

    return detected_style, scores


def validate_citations(text, detected_style):
    issues = []

    if detected_style == "IEEE":
        if not re.search(r"\[\d+\]", text):
            issues.append("IEEE citations like [1], [2] are missing.")

        if re.search(r"\([A-Za-z]+,\s*\d{4}\)", text):
            issues.append("APA style citation found inside IEEE format.")

    elif detected_style == "APA":
        if not re.search(r"\([A-Za-z]+,\s*\d{4}\)", text):
            issues.append("APA citations are missing.")

        if re.search(r"\[\d+\]", text):
            issues.append("IEEE style citation found inside APA format.")

    elif detected_style == "MLA":
        if re.search(r"\[\d+\]", text):
            issues.append("IEEE style citation found inside MLA format.")

    elif detected_style == "Chicago":
        if not re.search(r"\n\s*\d+\.\s+", text):
            issues.append("Chicago numbered notes are missing.")

    else:
        issues.append("Citation style could not be detected clearly.")

    return issues


def citation_analysis(text):
    ieee = re.findall(r"\[\d+\]", text)
    apa = re.findall(r"\([A-Za-z]+,\s*\d{4}\)", text)
    mla = re.findall(r"\([A-Za-z]+\s+\d+\)", text)

    total_citations = len(ieee) + len(apa) + len(mla)

    detected_style, style_scores = detect_citation_style(text)
    issues = validate_citations(text, detected_style)

    if total_citations >= 5:
        status = "✔ Follows citation guidelines"
        valid = True
    else:
        status = "✖ Too few citations"
        valid = False
        issues.append("Paper should contain at least 5 citations.")

    return {
        "count": total_citations,
        "status": status,
        "valid": valid,
        "detected_style": detected_style,
        "style_scores": style_scores,
        "issues": issues
    }


# ============================================================
# ROLE: Tanmay Kumar - Grammar Checker and Backend
# This part checks grammar, weak phrases, tone and readability
# ============================================================

def get_full_sentence(text, start_index):
    left = text.rfind(".", 0, start_index)
    right = text.find(".", start_index)

    if left == -1:
        left = 0
    else:
        left += 1

    if right == -1:
        right = len(text)

    return text[left:right].strip()


def check_grammar(text):
    issues = []

    try:
        matches = tool.check(text)

        for match in matches[:30]:
            start = match.offset
            end = match.offset + match.error_length
            wrong_text = text[start:end]

            severity = "High" if match.rule_issue_type == "misspelling" else "Medium"

            issues.append({
                "type": "Grammar Issue",
                "error_text": wrong_text,
                "sentence": get_full_sentence(text, start),
                "message": match.message,
                "suggestions": match.replacements[:3],
                "rule": match.rule_id,
                "severity": severity
            })

    except Exception as e:
        print("Grammar checking error:", e)

    return issues


def detect_weak_phrases(text):
    issues = []

    weak_words = {
        r"\bvery\b": "Avoid 'very'. Use a stronger academic word.",
        r"\breally\b": "Avoid 'really'. Use formal wording.",
        r"\ba lot\b": "Use a specific quantity instead of 'a lot'.",
        r"\bstuff\b": "Replace 'stuff' with a formal word.",
        r"\bthings\b": "Replace 'things' with a specific term.",
        r"\bgood\b": "Use a more precise academic word.",
        r"\bbad\b": "Use a more precise academic word.",
        r"\bi think\b": "Avoid personal opinion in academic writing.",
        r"\bwe believe\b": "Avoid subjective phrases in research papers."
    }

    lower_text = text.lower()

    for pattern, message in weak_words.items():
        for match in re.finditer(pattern, lower_text):
            issues.append({
                "type": "Weak Phrase",
                "error_text": match.group(),
                "sentence": get_full_sentence(text, match.start()),
                "message": message,
                "suggestions": ["Use precise academic wording"],
                "rule": "WEAK_PHRASE",
                "severity": "Low"
            })

            if len(issues) >= 20:
                return issues

    return issues


def check_academic_tone(text):
    lower_text = text.lower()

    informal_words = [" i ", " we ", " you ", " stuff ", " things ", " a lot "]
    informal_count = 0

    for word in informal_words:
        informal_count += lower_text.count(word)

    sentences = text.count(".") + text.count("?") + text.count("!")

    if sentences == 0:
        sentences = 1

    ratio = informal_count / sentences
    score = 10 - min(int(ratio * 20), 10)

    suggestions = []

    if informal_count > 0:
        suggestions.append("Avoid personal pronouns like I, we and you.")

    if "!" in text:
        suggestions.append("Avoid exclamation marks in academic writing.")

    if "very" in lower_text or "really" in lower_text:
        suggestions.append("Avoid informal intensifiers like very or really.")

    if len(suggestions) == 0:
        suggestions.append("Academic tone is appropriate.")

    return {
        "score": score,
        "suggestions": suggestions
    }


def check_readability(text):
    try:
        score = textstat.flesch_reading_ease(text)
        grade = textstat.flesch_kincaid_grade(text)
    except Exception:
        score = 0
        grade = 0

    suggestions = []

    if score < 30:
        suggestions.append("Very difficult to read. Try to simplify long sentences.")
    elif score < 50:
        suggestions.append("Difficult readability. Use shorter and clearer sentences.")
    elif score < 70:
        suggestions.append("Moderate readability. Clarity can be improved.")
    else:
        suggestions.append("Good readability.")

    if grade > 14:
        suggestions.append("Writing is too complex for general academic readers.")
    elif grade < 8:
        suggestions.append("Writing may be too simple for a research paper.")

    return {
        "score": round(score, 2),
        "grade": round(grade, 2),
        "suggestions": suggestions
    }


# ============================================================
# ROLE: Divyansh Rao - Report Generation
# This part creates highlighted PDF and final JSON report
# ============================================================

def generate_error_pdf(file_bytes, writing_issues):
    output_path = "highlighted_errors.pdf"

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        seen = set()

        for page_no, page in enumerate(doc):
            for issue in writing_issues:
                error_text = issue.get("error_text", "").strip()

                if not error_text:
                    continue

                if error_text.lower() in ["tone issue", "grammar issue"]:
                    continue

                key = (page_no, error_text)

                if key in seen:
                    continue

                seen.add(key)

                areas = page.search_for(error_text)

                for area in areas:
                    highlight = page.add_highlight_annot(area)
                    highlight.update()

        doc.save(output_path)

    except Exception as e:
        print("Highlighted PDF generation error:", e)

    return output_path


def make_global_formatting_issues(text, file_bytes, best_format):
    issues = []

    word_count = len(text.split())

    if word_count < 1500:
        issues.append({
            "type": "Length Issue",
            "message": "Paper is too short. Research paper should usually contain at least 1500 words."
        })

    if "abstract" not in text.lower():
        issues.append({
            "type": "Missing Section",
            "message": "Abstract section is missing."
        })

    if "references" not in text.lower():
        issues.append({
            "type": "Missing Section",
            "message": "References section is missing."
        })

    citation_data = citation_analysis(text)

    if citation_data["count"] < 5:
        issues.append({
            "type": "Citation Issue",
            "message": "Too few citations found in the paper."
        })

    layout_issues = detect_formatting_violations(file_bytes, FORMAT_RULES[best_format])
    issues.extend(layout_issues)

    return issues


# ============================================================
# MAIN BACKEND API
# ROLE: Tanmay Kumar - Backend Integration
# This route connects all modules together
# ============================================================

@app.route("/check", methods=["POST"])
def check_paper():
    if "file" not in request.files:
        return jsonify({
            "error": "No file uploaded"
        }), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({
            "error": "No file selected"
        }), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({
            "error": "Only PDF files are allowed"
        }), 400

    file_bytes = file.read()

    text = extract_text_from_pdf(file_bytes)

    if len(text.strip()) == 0:
        return jsonify({
            "error": "Could not extract text from PDF"
        }), 400

    title = detect_title(text)
    description = extract_description(text)

    publisher = detect_publisher(text)

    format_results = compare_with_all_formats(text, file_bytes)
    best_format = max(format_results, key=lambda x: format_results[x]["score"])

    if publisher == "Unknown Format":
        publisher = best_format

    grammar_issues = check_grammar(text)
    weak_phrase_issues = detect_weak_phrases(text)

    tone_data = check_academic_tone(text)
    readability_data = check_readability(text)
    citation_data = citation_analysis(text)

    tone_issues = []

    for suggestion in tone_data["suggestions"]:
        tone_issues.append({
            "type": "Tone Issue",
            "error_text": "Tone Issue",
            "sentence": "",
            "message": suggestion,
            "suggestions": [],
            "rule": "ACADEMIC_TONE",
            "severity": "Low"
        })

    all_writing_issues = grammar_issues + weak_phrase_issues + tone_issues

    highlighted_pdf = generate_error_pdf(file_bytes, all_writing_issues)

    all_formatting_issues = make_global_formatting_issues(
        text,
        file_bytes,
        best_format
    )

    summary = {
        "grammar_issues": len(all_writing_issues),
        "citations": citation_data["count"],
        "formatting_issues": len(all_formatting_issues),
        "word_count": len(text.split())
    }

    final_report = {
        "title": title,
        "publisher": publisher,
        "description": description,
        "summary": summary,

        "writing_issues": all_writing_issues,

        "readability_analysis": readability_data,

        "citation_analysis": citation_data,

        "formatting_analysis": format_results,

        "all_formatting_issues": all_formatting_issues,

        "tone_analysis": tone_data,

        "download_url": "http://127.0.0.1:5000/download"
    }

    return jsonify(final_report)


@app.route("/download", methods=["GET"])
def download_file():
    pdf_path = "highlighted_errors.pdf"

    if not os.path.exists(pdf_path):
        return jsonify({
            "error": "Highlighted PDF not generated yet"
        }), 404

    return send_file(pdf_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)