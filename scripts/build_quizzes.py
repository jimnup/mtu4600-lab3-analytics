"""Build Canvas-importable QTI quiz packages from the plain-text question files.

    uv run python scripts/build_quizzes.py              # every quizzes/*.txt
    uv run python scripts/build_quizzes.py --check      # parse only, report counts
    uv run python scripts/build_quizzes.py quizzes/lab3_nb04_ml_credit_risk.txt

Intended for the instructor. Each quizzes/<name>.txt becomes:

    quizzes/qti/<name>-qti.zip      import into Canvas: Settings > Import Course Content
                                    > "QTI .zip file" (creates an unpublished Classic Quiz)
    quizzes/keys/<name>-key.md      printable answer key with explanations

The question format is the same one text2qti reads, so the files stay readable and
easy to edit by hand:

    Quiz title: Notebook 01 - pandas Fundamentals
    Quiz description: One or two sentences shown to students.

    1. Question stem. `inline code` and **bold** are allowed.
    ... Explanation shown to the student after they submit.
    a) Wrong option
    *b) Correct option (marked with an asterisk)
    c) Wrong option
    d) Wrong option

    2. True or false: a statement to judge.
    ... Explanation.
    *a) True
    b) False

A question whose only options are True and False is exported as a Canvas
true/false question; everything else is multiple choice. Only the Python
standard library is used, so no extra packages are needed.
"""

from __future__ import annotations

import hashlib
import html
import re
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
QUIZ_DIR = REPO / "quizzes"

STEM = re.compile(r"^(\d+)\.\s+(.*)$")
OPTION = re.compile(r"^(\*?)([a-z])\)\s+(.*)$")
FEEDBACK = re.compile(r"^\.\.\.\s*(.*)$")
HEADER = re.compile(r"^Quiz (title|description):\s*(.*)$", re.IGNORECASE)
MATH = re.compile(r"\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\d)")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse(path: Path) -> dict:
    """Read a question file into {'title', 'description', 'questions': [...]}."""
    quiz = {"title": path.stem, "description": "", "questions": []}
    current = None
    in_fence = False
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.rstrip()
        if line.strip().startswith("```"):
            in_fence = not in_fence
            if current is not None:
                current["stem"].append(line)
            continue
        if in_fence:
            if current is not None:
                current["stem"].append(line)
            continue
        if not line.strip():
            continue
        if m := HEADER.match(line):
            quiz[m.group(1).lower()] = m.group(2).strip()
        elif m := STEM.match(line):
            current = {"n": int(m.group(1)), "stem": [m.group(2)], "feedback": [], "options": [], "line": lineno}
            quiz["questions"].append(current)
        elif current is None:
            raise SystemExit(f"{path.name}:{lineno}: text before the first question: {line!r}")
        elif m := FEEDBACK.match(line):
            current["feedback"].append(m.group(1))
        elif m := OPTION.match(line):
            current["options"].append({"correct": m.group(1) == "*", "text": m.group(3).strip()})
        elif current["options"]:
            current["options"][-1]["text"] += " " + line.strip()   # wrapped option text
        elif current["feedback"]:
            current["feedback"][-1] += " " + line.strip()          # wrapped feedback text
        else:
            current["stem"].append(line)                           # multi-line stem
    for q in quiz["questions"]:
        where = f"{path.name} question {q['n']} (line {q['line']})"
        if len(q["options"]) < 2:
            raise SystemExit(f"{where}: needs at least two options")
        if sum(o["correct"] for o in q["options"]) != 1:
            raise SystemExit(f"{where}: mark exactly one option correct with '*'")
        q["type"] = (
            "true_false_question"
            if [o["text"].lower() for o in q["options"]] == ["true", "false"]
            else "multiple_choice_question"
        )
    return quiz


# ---------------------------------------------------------------------------
# Light Markdown -> HTML (code spans, bold, italics, fenced code blocks)
# ---------------------------------------------------------------------------

def inline(text: str) -> str:
    parts = re.split(r"(`[^`]+`)", text)
    out = []
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            out.append("<code>" + html.escape(p[1:-1]) + "</code>")
        else:
            # $math$ -> \(math\), which Canvas renders with MathJax. Currency such as
            # "$76 to $348" is left alone: math must hug both dollar signs.
            p = MATH.sub(r"\\(\1\\)", p)
            p = html.escape(p, quote=False)
            p = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p)
            p = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", p)
            out.append(p)
    return "".join(out)


def to_html(lines: list[str]) -> str:
    out, para, code, in_code = [], [], [], False
    for line in lines:
        if line.strip().startswith("```"):
            if in_code:
                out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
                code, in_code = [], False
            else:
                if para:
                    out.append("<p>" + inline(" ".join(para)) + "</p>")
                    para = []
                in_code = True
            continue
        (code if in_code else para).append(line if in_code else line.strip())
    if para:
        out.append("<p>" + inline(" ".join(para)) + "</p>")
    return "".join(out)


# ---------------------------------------------------------------------------
# QTI 1.2 (Canvas flavour) writers
# ---------------------------------------------------------------------------

def ident(*parts) -> str:
    return "g" + hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()


def x(text: str) -> str:
    """Escape for placement inside an XML element."""
    return html.escape(text, quote=True)


def field(label: str, value) -> str:
    return (f"<qtimetadatafield><fieldlabel>{label}</fieldlabel>"
            f"<fieldentry>{x(str(value))}</fieldentry></qtimetadatafield>")


def item_xml(quiz_id: str, q: dict) -> str:
    item_id = ident(quiz_id, q["n"], q["stem"])
    answer_ids = [str(1000 * q["n"] + i) for i in range(len(q["options"]))]
    correct = answer_ids[[o["correct"] for o in q["options"]].index(True)]
    # Canvas exports true/false choices as plain text; multiple-choice choices as HTML.
    plain = q["type"] == "true_false_question"
    labels = "".join(
        f'<response_label ident="{aid}"><material>'
        + (f'<mattext texttype="text/plain">{x(o["text"])}</mattext>' if plain
           else f'<mattext texttype="text/html">{x(inline(o["text"]))}</mattext>')
        + "</material></response_label>"
        for aid, o in zip(answer_ids, q["options"])
    )
    feedback = " ".join(q["feedback"]).strip()
    fb_cond = (
        '<respcondition continue="Yes"><conditionvar><other/></conditionvar>'
        '<displayfeedback feedbacktype="Response" linkrefid="general_fb"/></respcondition>'
        if feedback else ""
    )
    fb_item = (
        '<itemfeedback ident="general_fb"><flow_mat><material>'
        f'<mattext texttype="text/html">{x(to_html([feedback]))}</mattext>'
        "</material></flow_mat></itemfeedback>"
        if feedback else ""
    )
    return (
        f'<item ident="{item_id}" title="Question {q["n"]}">'
        "<itemmetadata><qtimetadata>"
        + field("question_type", q["type"])
        + field("points_possible", "1.0")
        + field("original_answer_ids", ",".join(answer_ids))
        + field("assessment_question_identifierref", ident("aq", item_id))
        + "</qtimetadata></itemmetadata>"
        "<presentation><material>"
        f'<mattext texttype="text/html">{x(to_html(q["stem"]))}</mattext>'
        '</material><response_lid ident="response1" rcardinality="Single"><render_choice>'
        + labels
        + "</render_choice></response_lid></presentation>"
        '<resprocessing><outcomes><decvar maxvalue="100" minvalue="0" varname="SCORE" vartype="Decimal"/></outcomes>'
        + fb_cond
        + f'<respcondition continue="No"><conditionvar><varequal respident="response1">{correct}</varequal>'
        '</conditionvar><setvar action="Set" varname="SCORE">100</setvar></respcondition>'
        "</resprocessing>"
        + fb_item
        + "</item>"
    )


def assessment_xml(quiz_id: str, quiz: dict) -> str:
    items = "".join(item_xml(quiz_id, q) for q in quiz["questions"])
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<questestinterop xmlns="http://www.imsglobal.org/xsd/ims_qtiasiv1p2" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:schemaLocation="http://www.imsglobal.org/xsd/ims_qtiasiv1p2 '
        'http://www.imsglobal.org/xsd/ims_qtiasiv1p2p1.xsd">'
        f'<assessment ident="{quiz_id}" title="{x(quiz["title"])}">'
        "<qtimetadata>" + field("cc_maxattempts", "unlimited") + "</qtimetadata>"
        '<section ident="root_section">' + items + "</section></assessment></questestinterop>\n"
    )


def meta_xml(quiz_id: str, quiz: dict) -> str:
    desc = x(to_html([quiz["description"]])) if quiz["description"] else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<quiz identifier="{quiz_id}" xmlns="http://canvas.instructure.com/xsd/cccv1p0" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:schemaLocation="http://canvas.instructure.com/xsd/cccv1p0 '
        'https://canvas.instructure.com/xsd/cccv1p0.xsd">'
        f"<title>{x(quiz['title'])}</title>"
        f"<description>{desc}</description>"
        "<shuffle_answers>true</shuffle_answers>"
        "<scoring_policy>keep_highest</scoring_policy>"
        "<hide_results></hide_results>"
        "<quiz_type>assignment</quiz_type>"
        f"<points_possible>{len(quiz['questions'])}.0</points_possible>"
        "<require_lockdown_browser>false</require_lockdown_browser>"
        "<require_lockdown_browser_for_results>false</require_lockdown_browser_for_results>"
        "<require_lockdown_browser_monitor>false</require_lockdown_browser_monitor>"
        "<show_correct_answers>true</show_correct_answers>"
        "<anonymous_submissions>false</anonymous_submissions>"
        "<could_be_locked>false</could_be_locked>"
        "<allowed_attempts>-1</allowed_attempts>"
        "<one_question_at_a_time>false</one_question_at_a_time>"
        "<cant_go_back>false</cant_go_back>"
        "<available>false</available>"
        "<one_time_results>false</one_time_results>"
        "<show_correct_answers_last_attempt>false</show_correct_answers_last_attempt>"
        "<only_visible_to_overrides>false</only_visible_to_overrides>"
        "<module_locked>false</module_locked>"
        "</quiz>\n"
    )


def manifest_xml(quiz_id: str, quiz: dict) -> str:
    dep = ident("meta", quiz_id)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<manifest identifier="{ident("manifest", quiz_id)}" '
        'xmlns="http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1" '
        'xmlns:lom="http://ltsc.ieee.org/xsd/imsccv1p1/LOM/resource" '
        'xmlns:imsmd="http://www.imsglobal.org/xsd/imsmd_v1p2" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:schemaLocation="http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1 '
        'http://www.imsglobal.org/xsd/imscp_v1p1.xsd '
        'http://ltsc.ieee.org/xsd/imsccv1p1/LOM/resource '
        'http://www.imsglobal.org/profile/cc/ccv1p1/LOM/ccv1p1_lomresource_v1p0.xsd '
        'http://www.imsglobal.org/xsd/imsmd_v1p2 http://www.imsglobal.org/xsd/imsmd_v1p2p2.xsd">'
        "<metadata><schema>IMS Content</schema><schemaversion>1.1.3</schemaversion>"
        f"<imsmd:lom><imsmd:general><imsmd:title><imsmd:string>{x(quiz['title'])}</imsmd:string>"
        "</imsmd:title></imsmd:general></imsmd:lom></metadata>"
        "<organizations/><resources>"
        f'<resource identifier="{quiz_id}" type="imsqti_xmlv1p2">'
        f'<file href="{quiz_id}/{quiz_id}.xml"/><dependency identifierref="{dep}"/></resource>'
        f'<resource identifier="{dep}" type="associatedcontent/imscc_xmlv1p1/learning-application-resource" '
        f'href="{quiz_id}/assessment_meta.xml"><file href="{quiz_id}/assessment_meta.xml"/></resource>'
        "</resources></manifest>\n"
    )


def answer_key(quiz: dict) -> str:
    out = [f"# Answer key: {quiz['title']}", "", quiz["description"], ""]
    for q in quiz["questions"]:
        kind = "True/False" if q["type"] == "true_false_question" else "Multiple choice"
        out.append(f"**{q['n']}. ({kind})** " + "\n".join(q["stem"]))
        out.append("")
        for letter, o in zip("abcdefgh", q["options"]):
            mark = "**✓**" if o["correct"] else "  "
            out.append(f"- {mark} {letter}) {o['text']}")
        if q["feedback"]:
            out.append("")
            out.append("> " + " ".join(q["feedback"]))
        out.append("")
    return "\n".join(out)


def build(path: Path, check_only: bool = False) -> dict:
    quiz = parse(path)
    if check_only:
        return quiz
    quiz_id = ident("quiz", path.stem)
    (QUIZ_DIR / "qti").mkdir(parents=True, exist_ok=True)
    (QUIZ_DIR / "keys").mkdir(parents=True, exist_ok=True)
    zip_path = QUIZ_DIR / "qti" / f"{path.stem}-qti.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("imsmanifest.xml", manifest_xml(quiz_id, quiz))
        z.writestr(f"{quiz_id}/{quiz_id}.xml", assessment_xml(quiz_id, quiz))
        z.writestr(f"{quiz_id}/assessment_meta.xml", meta_xml(quiz_id, quiz))
    (QUIZ_DIR / "keys" / f"{path.stem}-key.md").write_text(answer_key(quiz), encoding="utf-8")
    return quiz


def main() -> int:
    args = sys.argv[1:]
    check = "--check" in args
    files = [Path(a).resolve() for a in args if not a.startswith("--")] or sorted(QUIZ_DIR.glob("*.txt"))
    if not files:
        print("No quiz files found in", QUIZ_DIR)
        return 1
    for f in files:
        quiz = build(f, check_only=check)
        qs = quiz["questions"]
        tf = sum(q["type"] == "true_false_question" for q in qs)
        print(f"{f.name}: {len(qs)} questions ({len(qs) - tf} multiple choice, {tf} true/false)"
              + ("" if check else " -> quizzes/qti/ and quizzes/keys/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
