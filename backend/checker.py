import pdfplumber
import re
import language_tool_python

tool = language_tool_python.LanguageTool('en-US')


def extract_text(file):
    with pdfplumber.open(file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    return text


def check_grammar(text):
    matches = tool.check(text)

    errors = []
    for m in matches[:20]:
        errors.append({
            "message": m.message,
            "suggestions": m.replacements,
            "context": text[m.offset:m.offset+50]
        })

    return errors


def check_citations(text):
    pattern = r"\[\d+\]"   # IEEE style

    citations = re.findall(pattern, text)

    return {
        "total_citations": len(citations),
        "examples": citations[:10]
    }


def check_format(text):

    issues = []

    if "Abstract" not in text:
        issues.append("Abstract section missing")

    if "References" not in text:
        issues.append("References section missing")

    if len(text.split()) < 1000:
        issues.append("Paper seems too short")

    return issues