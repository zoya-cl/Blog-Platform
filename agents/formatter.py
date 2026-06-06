import os
import re
import math
import json
import config
from topic_selection import queue_manager

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #1a1a1a;
            background-color: #f8fafc;
            line-height: 1.7;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 800px;
            margin: 40px auto;
            padding: 40px;
            background-color: #ffffff;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }}
        h1 {{
            font-size: 2.25rem;
            font-weight: 800;
            color: #0f172a;
            line-height: 1.25;
            margin-bottom: 20px;
        }}
        h2 {{
            font-size: 1.5rem;
            font-weight: 700;
            color: #1e293b;
            margin-top: 40px;
            margin-bottom: 16px;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 8px;
        }}
        h3 {{
            font-size: 1.25rem;
            font-weight: 600;
            color: #334155;
            margin-top: 24px;
            margin-bottom: 12px;
        }}
        p {{
            margin-top: 0;
            margin-bottom: 24px;
            font-size: 1.05rem;
        }}
        a {{
            color: #2563eb;
            text-decoration: none;
            border-bottom: 1px solid transparent;
            transition: border-color 0.15s ease;
        }}
        a:hover {{
            border-color: #2563eb;
        }}
        .header-meta {{
            font-size: 0.9rem;
            color: #64748b;
            background-color: #f1f5f9;
            padding: 12px 18px;
            border-radius: 6px;
            margin-bottom: 30px;
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
        }}
        .header-meta span {{
            font-weight: 600;
        }}
        hr {{
            border: 0;
            height: 1px;
            background: #e2e8f0;
            margin: 30px 0;
        }}
        pre {{
            background-color: #0f172a;
            color: #e2e8f0;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            margin-bottom: 24px;
        }}
        code {{
            font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
            font-size: 0.9em;
            background-color: #f1f5f9;
            padding: 3px 6px;
            border-radius: 4px;
        }}
        pre code {{
            background-color: transparent;
            padding: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
            font-size: 0.95rem;
        }}
        th {{
            background-color: #f8fafc;
            border-bottom: 2px solid #e2e8f0;
            color: #475569;
            font-weight: 700;
            padding: 12px 16px;
            text-align: left;
        }}
        td {{
            border-bottom: 1px solid #e2e8f0;
            padding: 12px 16px;
            color: #334155;
        }}
        blockquote {{
            border-left: 4px solid #cbd5e1;
            margin: 0 0 24px 0;
            padding-left: 20px;
            color: #475569;
            font-style: italic;
        }}
        .alert {{
            border-left: 4px solid;
            border-radius: 6px;
            margin-bottom: 24px;
            padding: 16px 20px;
        }}
        .alert-title {{
            font-weight: 700;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .alert-tip {{
            background-color: #f0fdf4;
            border-left-color: #22c55e;
            color: #166534;
        }}
        .alert-tip .alert-title {{
            color: #15803d;
        }}
        .alert-warning {{
            background-color: #fffbeb;
            border-left-color: #f59e0b;
            color: #92400e;
        }}
        .alert-warning .alert-title {{
            color: #b45309;
        }}
        ul, ol {{
            margin-top: 0;
            margin-bottom: 24px;
            padding-left: 30px;
        }}
        li {{
            margin-bottom: 8px;
        }}
        /* ── Component blocks ─────────────────────────────────────────── */
        .component-card {{
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            margin: 28px 0;
            overflow: hidden;
            background: #ffffff;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }}
        .component-label {{
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #94a3b8;
            padding: 6px 16px;
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
        }}
        /* code_block */
        .component-code pre {{
            margin: 0;
            border-radius: 0;
            padding: 20px;
        }}
        .component-code .code-explanation {{
            padding: 12px 20px;
            font-size: 0.9rem;
            color: #475569;
            background: #f8fafc;
            border-top: 1px solid #e2e8f0;
            font-style: italic;
        }}
        /* table component */
        .component-table table {{
            margin: 0;
            border-radius: 0;
        }}
        /* quiz component */
        .component-quiz {{
            padding: 20px 24px;
        }}
        .quiz-question {{
            font-weight: 700;
            font-size: 1rem;
            color: #1e293b;
            margin-bottom: 14px;
        }}
        .quiz-options {{
            list-style: none;
            padding: 0;
            margin: 0 0 14px 0;
        }}
        .quiz-options li {{
            padding: 9px 14px;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            margin-bottom: 7px;
            cursor: default;
            font-size: 0.95rem;
            color: #334155;
            transition: background 0.15s;
        }}
        .quiz-options li.correct-answer {{
            background: #f0fdf4;
            border-color: #22c55e;
            color: #15803d;
            font-weight: 600;
        }}
        .quiz-explanation {{
            font-size: 0.88rem;
            color: #64748b;
            border-top: 1px dashed #e2e8f0;
            padding-top: 10px;
            font-style: italic;
        }}
        /* comparison_widget */
        .component-comparison {{
            padding: 20px 24px;
        }}
        .comparison-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 14px;
        }}
        .comparison-side {{
            border-radius: 8px;
            overflow: hidden;
        }}
        .comparison-side-title {{
            background: #1e293b;
            color: #f1f5f9;
            font-weight: 700;
            font-size: 0.85rem;
            padding: 8px 14px;
            letter-spacing: 0.02em;
        }}
        .comparison-metrics {{
            border: 1px solid #e2e8f0;
            border-top: none;
            border-radius: 0 0 8px 8px;
        }}
        .comparison-metric-row {{
            display: flex;
            gap: 0;
        }}
        .metric-name {{
            background: #f8fafc;
            font-size: 0.82rem;
            font-weight: 600;
            color: #475569;
            padding: 8px 12px;
            border-bottom: 1px solid #e2e8f0;
            min-width: 130px;
        }}
        .metric-value {{
            font-size: 0.85rem;
            color: #1e293b;
            padding: 8px 12px;
            border-bottom: 1px solid #e2e8f0;
            flex: 1;
        }}
        @media (max-width: 600px) {{
            .comparison-grid {{ grid-template-columns: 1fr; }}
        }}
        /* roadmap / vertical step-flow */
        .component-roadmap {{
            padding: 24px 24px 12px;
        }}
        .roadmap-title {{
            font-weight: 700;
            font-size: 1.05rem;
            color: #1e293b;
            margin-bottom: 20px;
        }}
        .roadmap-steps {{
            position: relative;
            padding-left: 44px;
        }}
        .roadmap-steps::before {{
            content: '';
            position: absolute;
            left: 14px;
            top: 4px;
            bottom: 4px;
            width: 2px;
            background: linear-gradient(180deg, #6366f1, #a78bfa);
            border-radius: 2px;
        }}
        .roadmap-step {{
            position: relative;
            margin-bottom: 24px;
        }}
        .roadmap-step:last-child {{
            margin-bottom: 8px;
        }}
        .roadmap-step-number {{
            position: absolute;
            left: -44px;
            top: 0;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: #fff;
            font-weight: 700;
            font-size: 0.8rem;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 6px rgba(99,102,241,0.3);
        }}
        .roadmap-step-label {{
            font-weight: 600;
            font-size: 0.95rem;
            color: #1e293b;
            margin-bottom: 4px;
        }}
        .roadmap-step-desc {{
            font-size: 0.85rem;
            color: #64748b;
            line-height: 1.5;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(4px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .confirm-btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 6px 12px rgba(37,99,235,0.3);
            background: linear-gradient(135deg, #1d4ed8, #1e40af);
        }}
        .confirm-btn:active {{
            transform: translateY(1px);
            box-shadow: 0 2px 4px rgba(37,99,235,0.1);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="header-meta">
            <div>Category: <span>{category}</span></div>
            <div>Date: <span>{date}</span></div>
            <div>Word Count: <span>{word_count} words</span></div>
            <div>Reading Time: <span>{reading_time_minutes} min</span></div>
            <div>Quality Score: <span>{quality_score}/10</span></div>
            <div>Revisions: <span>{revision_count}</span></div>
        </div>
        <hr>
        <div class="blog-body">
            {body_html}
        </div>
    </div>
    <script>
        function triggerConfirmation(widgetId) {{
            const widget = document.getElementById(widgetId);
            if (!widget) return;
            const btn = widget.querySelector('.confirm-btn');
            const successState = widget.querySelector('.confirm-success-state');
            if (btn && successState) {{
                btn.style.display = 'none';
                successState.style.display = 'block';
            }}
        }}
    </script>
</body>
</html>
"""

def sanitize_title(title: str) -> str:
    """
    Sanitizes title into a clean slug-like format suitable for filenames.
    Converts to lowercase, removes special characters, replaces spaces with hyphens,
    and truncates to 80 characters.
    """
    s = title.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s_]+", "-", s)
    s = s[:80]
    s = s.strip("-")
    return s

def convert_callouts(text: str) -> str:
    """
    Scans the text line-by-line and converts '💡 tip:' and '⚠️ common mistake:'
    patterns into GitHub markdown-native alert syntax (TIP/WARNING blockquotes).
    """
    lines = text.split("\n")
    processed_lines = []
    
    for line in lines:
        tip_match = re.match(r"^\s*💡\s*tip:\s*(.+)$", line, re.IGNORECASE)
        warning_match = re.match(r"^\s*⚠️\s*common\s+mistake:\s*(.+)$", line, re.IGNORECASE)
        
        if tip_match:
            processed_lines.append("> [!TIP]")
            processed_lines.append(f"> {tip_match.group(1).strip()}")
        elif warning_match:
            processed_lines.append("> [!WARNING]")
            processed_lines.append(f"> {warning_match.group(1).strip()}")
        else:
            processed_lines.append(line)
            
    return "\n".join(processed_lines)

# ---------------------------------------------------------------------------
# Component block renderer  (COMPONENT: … } spec → HTML)
# ---------------------------------------------------------------------------

_COMPONENT_RE = re.compile(
    r"^COMPONENT:\s*\ntype:\s*(\S+)\s*\nprops:\s*(\{.*?^\})",
    re.MULTILINE | re.DOTALL
)

def _parse_props(raw: str) -> dict:
    """Parse the props JSON block, stripping escaped newlines from code strings."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Attempt lightweight recovery: replace literal \n with actual newlines
        fixed = raw.replace("\\n", "\n")
        try:
            return json.loads(fixed)
        except Exception:
            return {}

def _render_table(props: dict) -> str:
    headers = props.get("headers", [])
    rows = props.get("rows", [])
    caption = props.get("caption", "")
    html = ['<div class="component-card">']
    html.append('<div class="component-label">Table</div>')
    html.append('<div class="component-table"><table>')
    if caption:
        html.append(f"<caption style='padding:10px 16px;font-size:.85rem;color:#64748b;text-align:left;'>{caption}</caption>")
    if headers:
        html.append("<thead><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead>")
    html.append("<tbody>")
    for row in rows:
        if isinstance(row, dict):
            # Extract row values in the order of headers
            cells = [row.get(h, row.get(h.lower(), "")) for h in headers]
        else:
            cells = row
        html.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    html.append("</tbody></table></div></div>")
    return "\n".join(html)

def _render_code_block(props: dict) -> str:
    lang = props.get("language", "text")
    code = props.get("code", "").replace("\\n", "\n")
    explanation = props.get("explanation", "")
    code_esc = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = [
        '<div class="component-card">',
        f'<div class="component-label">Code · {lang}</div>',
        '<div class="component-code">',
        f'<pre><code class="language-{lang}">{code_esc.strip()}</code></pre>',
    ]
    if explanation:
        html.append(f'<div class="code-explanation">{explanation}</div>')
    html.append("</div></div>")
    return "\n".join(html)

def _render_quiz(props: dict) -> str:
    question = props.get("question", "")
    options = props.get("options", [])
    correct = props.get("correct_answer", "")
    explanation = props.get("explanation", "")
    html = [
        '<div class="component-card">',
        '<div class="component-label">Knowledge Check</div>',
        '<div class="component-quiz">',
        f'<div class="quiz-question">{question}</div>',
        '<ul class="quiz-options">',
    ]
    for opt in options:
        cls = ' class="correct-answer"' if opt == correct else ""
        html.append(f"<li{cls}>{opt}</li>")
    html.append("</ul>")
    if explanation:
        html.append(f'<div class="quiz-explanation">✦ {explanation}</div>')
    html.append("</div></div>")
    return "\n".join(html)

def _render_comparison(props: dict) -> str:
    left_title = props.get("left_title", "Option A")
    right_title = props.get("right_title", "Option B")
    metrics = props.get("metrics", [])
    html = [
        '<div class="component-card">',
        '<div class="component-label">Comparison</div>',
        '<div class="component-comparison">',
        '<div class="comparison-grid">',
        # Left column
        '<div class="comparison-side">',
        f'<div class="comparison-side-title">{left_title}</div>',
        '<div class="comparison-metrics">',
    ]
    for m in metrics:
        html.append('<div class="comparison-metric-row">')
        html.append(f'<div class="metric-name">{m.get("name", "")}</div>')
        html.append(f'<div class="metric-value">{m.get("left", "")}</div>')
        html.append("</div>")
    html.append("</div></div>")  # close metrics + left side
    # Right column
    html.append('<div class="comparison-side">')
    html.append(f'<div class="comparison-side-title">{right_title}</div>')
    html.append('<div class="comparison-metrics">')
    for m in metrics:
        html.append('<div class="comparison-metric-row">')
        html.append(f'<div class="metric-name">{m.get("name", "")}</div>')
        html.append(f'<div class="metric-value">{m.get("right", "")}</div>')
        html.append("</div>")
    html.append("</div></div>")  # close metrics + right side
    html.append("</div></div></div>")  # close grid + comparison + card
    return "\n".join(html)

def _render_roadmap(props: dict) -> str:
    title = props.get("title", "")
    steps = props.get("steps", [])
    html = [
        '<div class="component-card">',
        '<div class="component-label">Roadmap</div>',
        '<div class="component-roadmap">',
    ]
    if title:
        html.append(f'<div class="roadmap-title">{title}</div>')
    html.append('<div class="roadmap-steps">')
    for i, step in enumerate(steps, 1):
        label = step.get("label", f"Step {i}")
        desc = step.get("description", "")
        html.append('<div class="roadmap-step">')
        html.append(f'<div class="roadmap-step-number">{i}</div>')
        html.append(f'<div class="roadmap-step-label">{label}</div>')
        if desc:
            html.append(f'<div class="roadmap-step-desc">{desc}</div>')
        html.append('</div>')
    html.append('</div>')  # close roadmap-steps
    html.append('</div></div>')  # close roadmap + card
    return "\n".join(html)

def _render_checklist(props: dict) -> str:
    title = props.get("title", "Checklist")
    items = props.get("items", [])
    html = [
        '<div class="component-card">',
        '<div class="component-label">Checklist</div>',
        '<div class="component-checklist" style="padding: 20px 24px;">',
    ]
    if title:
        html.append(f'<div class="checklist-title" style="font-weight: 700; font-size: 1.05rem; color: #1e293b; margin-bottom: 16px;">{title}</div>')
    
    html.append('<ul class="checklist-items" style="list-style: none; padding: 0; margin: 0;">')
    for item in items:
        html.append(
            f'<li style="display: flex; align-items: flex-start; gap: 12px; margin-bottom: 12px; font-size: 0.95rem; color: #334155;">'
            f'<span style="display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; border-radius: 4px; border: 2px solid #6366f1; color: #6366f1; margin-top: 2px; flex-shrink: 0; font-size: 0.8rem; font-weight: 800;">✓</span>'
            f'<span>{item}</span>'
            f'</li>'
        )
    html.append('</ul>')
    html.append('</div></div>')
    return "\n".join(html)

_COMPONENT_RENDERERS = {
    "table": _render_table,
    "code_block": _render_code_block,
    "quiz": _render_quiz,
    "comparison_widget": _render_comparison,
    "roadmap": _render_roadmap,
    "checklist": _render_checklist,
    "confirm": lambda props: _render_confirm(props),
}

def _render_confirm(props: dict) -> str:
    title = props.get("title", "Test Yourself")
    prompt = props.get("prompt", "Confirm your understanding.")
    button_text = props.get("button_text", "Confirm")
    image_path = props.get("image_path", "")
    success_message = props.get("success_message", "Confirmed!")
    
    import uuid
    widget_id = f"confirm_widget_{str(uuid.uuid4())[:8]}"
    
    html = [
        f'<div class="component-card" id="{widget_id}">',
        f'<div class="component-label">Confirm Understanding</div>',
        '<div class="component-confirm" style="padding: 24px 24px; text-align: center; background: linear-gradient(135deg, #f8fafc, #eff6ff); border-radius: 0 0 10px 10px;">',
    ]
    if title:
        html.append(f'<div class="confirm-title" style="font-weight: 800; font-size: 1.25rem; color: #1e3a8a; margin-bottom: 12px;">{title}</div>')
    if prompt:
        html.append(f'<div class="confirm-prompt" style="font-size: 1rem; color: #4b5563; margin-bottom: 20px; line-height: 1.6;">{prompt}</div>')
        
    if image_path:
        html.append(
            f'<div class="confirm-image-container" style="margin-bottom: 24px; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: #fff; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">'
            f'<img src="{image_path}" alt="Infographic Visual" style="max-width: 100%; height: auto; display: block; margin: 0 auto;">'
            f'</div>'
        )
        
    html.append(
        f'<button class="confirm-btn" onclick="triggerConfirmation(\'{widget_id}\')" style="background: linear-gradient(135deg, #2563eb, #1d4ed8); color: #ffffff; border: none; padding: 12px 24px; font-size: 0.95rem; font-weight: 700; border-radius: 6px; cursor: pointer; transition: all 0.2s ease; box-shadow: 0 4px 6px rgba(37,99,235,0.2);">'
        f'{button_text}'
        f'</button>'
    )
    
    html.append(
        f'<div class="confirm-success-state" style="display: none; color: #166534; font-weight: 700; font-size: 1.05rem; padding: 12px; background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; margin-top: 15px; animation: fadeIn 0.4s ease;">'
        f'{success_message}'
        f'</div>'
    )
    
    html.append('</div></div>')
    return "\n".join(html)

def render_component_blocks(text: str) -> str:
    """
    Replaces COMPONENT: … } spec blocks with rendered HTML.
    Called on the text that will become HTML; the MD file keeps raw specs.
    """
    def replacer(match):
        comp_type = match.group(1).strip().lower()
        props_raw = match.group(2)
        props = _parse_props(props_raw)
        renderer = _COMPONENT_RENDERERS.get(comp_type)
        if renderer:
            return renderer(props)
        return (
            f'<div class="component-card">'
            f'<div class="component-label">{comp_type}</div>'
            f'<div style="padding:16px 20px;font-size:.9rem;color:#475569;">'
            f'<em>[Component type <code>{comp_type}</code> — props omitted in HTML preview]</em>'
            f'</div></div>'
        )
    return _COMPONENT_RE.sub(replacer, text)

def markdown_to_html(markdown_text: str) -> str:
    """
    Converts simple Markdown body text into clean, structured HTML blocks.
    Supports headings, paragraphs, code blocks, lists, links, tables, and alerts.
    """
    # 1. Capture code blocks
    code_blocks = []
    def save_code(match):
        lang = match.group(1) or "text"
        code = match.group(2)
        placeholder = f"<!--CODEBLOCK_PLACEHOLDER_{len(code_blocks)}-->"
        code_escaped = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html_code = f"<pre><code class=\"language-{lang}\">{code_escaped.strip()}</code></pre>"
        code_blocks.append(html_code)
        return placeholder
    
    temp_text = re.sub(r"```(\w*)\n(.*?)\n```", save_code, markdown_text, flags=re.DOTALL)
    
    # 2. Capture tables
    tables = []
    def save_table(match):
        table_markdown = match.group(0)
        placeholder = f"<!--TABLE_PLACEHOLDER_{len(tables)}-->"
        lines = table_markdown.strip().split("\n")
        if len(lines) < 2:
            return table_markdown
            
        html_table = ["<table>"]
        alignments = []
        for col in lines[1].split("|")[1:-1]:
            col_strip = col.strip()
            if col_strip.startswith(":") and col_strip.endswith(":"):
                alignments.append('style="text-align: center;"')
            elif col_strip.endswith(":"):
                alignments.append('style="text-align: right;"')
            else:
                alignments.append('style="text-align: left;"')
                
        headers = [h.strip() for h in lines[0].split("|")[1:-1]]
        html_table.append("<thead><tr>")
        for idx, h in enumerate(headers):
            align = alignments[idx] if idx < len(alignments) else ""
            html_table.append(f"<th {align}>{h}</th>")
        html_table.append("</tr></thead><tbody>")
        
        for row in lines[2:]:
            cols = [c.strip() for c in row.split("|")[1:-1]]
            if not cols:
                continue
            html_table.append("<tr>")
            for idx, c in enumerate(cols):
                align = alignments[idx] if idx < len(alignments) else ""
                html_table.append(f"<td {align}>{c}</td>")
            html_table.append("</tr>")
            
        html_table.append("</tbody></table>")
        tables.append("\n".join(html_table))
        return placeholder

    temp_text = re.sub(r"(?:^\|[^\n]+\|\r?\n?)+", save_table, temp_text, flags=re.MULTILINE)

    # 3. GitHub alerts blocks
    def parse_alerts(match):
        alert_type = match.group(1).lower()
        alert_content = match.group(2)
        alert_content_clean = re.sub(r"^>\s*", "", alert_content, flags=re.MULTILINE).strip()
        icon = "💡" if alert_type == "tip" else "⚠️"
        title = "TIP" if alert_type == "tip" else "WARNING"
        return f'<div class="alert alert-{alert_type}"><div class="alert-title">{icon} {title}</div><div class="alert-content">{alert_content_clean}</div></div>'
        
    temp_text = re.sub(r"^>\s*\[!(TIP|WARNING)\]\r?\n((?:^>.*(?:\r?\n|$))*)", parse_alerts, temp_text, flags=re.MULTILINE)

    # 4. Standard Blockquotes
    def parse_blockquotes(match):
        bq_content = match.group(0)
        bq_clean = re.sub(r"^>\s*", "", bq_content, flags=re.MULTILINE).strip()
        return f"<blockquote>{bq_clean}</blockquote>"
        
    temp_text = re.sub(r"(?:^>[^!][^\n]*\r?\n?)+", parse_blockquotes, temp_text, flags=re.MULTILINE)

    # 5. Headings
    temp_text = re.sub(r"^##\s+(.+)$", r"<h2>\1</h2>", temp_text, flags=re.MULTILINE)
    temp_text = re.sub(r"^###\s+(.+)$", r"<h3>\1</h3>", temp_text, flags=re.MULTILINE)
    temp_text = re.sub(r"^####\s+(.+)$", r"<h4>\1</h4>", temp_text, flags=re.MULTILINE)

    # 6. Horizontal Rules
    temp_text = re.sub(r"^---\s*$", r"<hr>", temp_text, flags=re.MULTILINE)

    # 7. Unordered Lists
    def parse_unordered_lists(match):
        list_items = match.group(0).strip().split("\n")
        html_list = ["<ul>"]
        for item in list_items:
            item_clean = re.sub(r"^[-*+]\s+", "", item).strip()
            html_list.append(f"<li>{item_clean}</li>")
        html_list.append("</ul>")
        return "\n".join(html_list)
        
    temp_text = re.sub(r"(?:^[-*+]\s+[^\n]+\r?\n?)+", parse_unordered_lists, temp_text, flags=re.MULTILINE)

    # 8. Ordered Lists
    def parse_ordered_lists(match):
        list_items = match.group(0).strip().split("\n")
        html_list = ["<ol>"]
        for item in list_items:
            item_clean = re.sub(r"^\d+\.\s+", "", item).strip()
            html_list.append(f"<li>{item_clean}</li>")
        html_list.append("</ol>")
        return "\n".join(html_list)
        
    temp_text = re.sub(r"(?:^\d+\.\s+[^\n]+\r?\n?)+", parse_ordered_lists, temp_text, flags=re.MULTILINE)

    # 9. Images, Bold, Italic, Inline Code, Links
    temp_text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1" style="max-width: 100%; height: auto; border-radius: 8px; margin: 24px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); display: block;">', temp_text)
    temp_text = re.sub(r"\*\*([^\*]+)\*\*", r"<strong>\1</strong>", temp_text)
    temp_text = re.sub(r"\*([^\*]+)\*", r"<em>\1</em>", temp_text)
    temp_text = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", temp_text)
    temp_text = re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', temp_text)

    # 10. Split Paragraphs
    blocks = temp_text.split("\n\n")
    html_blocks = []
    for block in blocks:
        block_strip = block.strip()
        if not block_strip:
            continue
        if block_strip.startswith("<h") or block_strip.startswith("<div") or block_strip.startswith("<ul") or block_strip.startswith("<ol") or block_strip.startswith("<blockquote>") or block_strip.startswith("<table") or block_strip.startswith("<!--") or block_strip.startswith("<pre>") or block_strip.startswith("<hr>"):
            html_blocks.append(block_strip)
        else:
            p_text = block_strip.replace("\n", " ")
            html_blocks.append(f"<p>{p_text}</p>")

    final_html = "\n\n".join(html_blocks)

    # Restore placeholders
    for i, table_html in enumerate(tables):
        final_html = final_html.replace(f"<!--TABLE_PLACEHOLDER_{i}-->", table_html)
    for i, code_html in enumerate(code_blocks):
        final_html = final_html.replace(f"<!--CODEBLOCK_PLACEHOLDER_{i}-->", code_html)

    return final_html

def clean_fact_citations(text: str) -> str:
    """
    Cleans up any literal [fact_N](url) citations that slipped through
    and replaces [fact_N] with a human-readable domain name (e.g. Scaler, PayScale, etc.).
    """
    from urllib.parse import urlparse
    
    def replacer(match):
        url = match.group(1)
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith("www."):
                domain = domain[4:]
            
            if "." in domain:
                name = domain.split(".")[0]
                if name.lower() == "gsdcouncil":
                    source_name = "GSD Council"
                else:
                    source_name = name.capitalize()
            else:
                source_name = domain.capitalize() if domain else "Source"
        except Exception:
            source_name = "Source"
            
        return f"[{source_name}]({url})"
        
    return re.sub(r"\[fact_\d+\]\((.*?)\)", replacer, text)

def format_post(state: dict) -> dict:
    """
    Pure Python formatter function called after LangGraph workflow completion.
    Calculates final word counts/reading time, outputs sidecar JSON and MD files,
    updates DB status to published, and cleans up retrieval cache.
    """
    print("\n--- Running Post-Processing Formatter ---")
    
    trace_id = state.get("trace_id", "")
    topic = state.get("topic", "")
    category = state.get("category", "")
    metadata = state.get("metadata", {})
    
    final_blog = state.get("final_blog", "")
    if not final_blog:
        final_blog = state.get("assembled_draft", "")
        
    if not final_blog:
        print("Error: No blog post text found in state to format.")
        return state

    # Step 1: Calculate Word Count & Reading Time
    word_count = len(final_blog.split())
    reading_time_minutes = math.ceil(word_count / 200)
    metadata["word_count"] = word_count
    
    # Step 2: Convert Callouts and Clean Fact Citations
    processed_blog = convert_callouts(final_blog)
    processed_blog = clean_fact_citations(processed_blog)
    
    # Step 3: Determine File Names and Handle Collisions
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(_project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = sanitize_title(metadata.get("title", topic))
    if not base_name:
        base_name = "blog-post"
        
    md_filename = f"{base_name}.md"
    json_filename = f"{base_name}.json"
    
    md_filepath = os.path.join(output_dir, md_filename)
    json_filepath = os.path.join(output_dir, json_filename)
    
    if os.path.exists(md_filepath) or os.path.exists(json_filepath):
        suffix = trace_id[:6] if trace_id else "post"
        md_filename = f"{base_name}-{suffix}.md"
        json_filename = f"{base_name}-{suffix}.json"
        md_filepath = os.path.join(output_dir, md_filename)
        json_filepath = os.path.join(output_dir, json_filename)
        
    # Step 4: Construct and Write Metadata JSON sidecar
    quality_score = float(metadata.get("quality_score", 0.0))
    revision_count = int(metadata.get("revision_count", 0))
    
    json_data = {
        "title": metadata.get("title", topic),
        "slug": metadata.get("slug", base_name),
        "date": metadata.get("date", ""),
        "category": category,
        "audience_level": state.get("audience_level", "fresher"),
        "tags": metadata.get("tags", []),
        "meta_description": metadata.get("meta_description", ""),
        "focus_keyword": metadata.get("focus_keyword", ""),
        "secondary_keywords": metadata.get("secondary_keywords", []),
        "word_count": word_count,
        "word_count_target": state.get("word_count_target", 0),
        "section_count_target": state.get("section_count_target", 0),
        "reading_time_minutes": reading_time_minutes,
        "quality_score": quality_score,
        "revision_count": revision_count,
        "prompt_version": int(metadata.get("prompt_version", config.PROMPT_VERSION)),
        "generated_images": state.get("generated_images", []),
        "approved": "no"
    }
    
    with open(json_filepath, "w", encoding="utf-8") as jf:
        json.dump(json_data, jf, indent=2)
    print(f"Sidecar metadata saved successfully to: {json_filepath}")
    
    # Step 5: Stitch and Write Markdown File
    header_line = (
        f"**Category:** {category} | "
        f"**Date:** {json_data['date']} | "
        f"**Word Count:** {word_count} | "
        f"**Reading Time:** {reading_time_minutes} min | "
        f"**Score:** {quality_score:.1f}/10 | "
        f"**Revisions:** {revision_count}"
    )
    
    full_markdown = f"# {json_data['title']}\n\n{header_line}\n---\n\n{processed_blog}"
    
    with open(md_filepath, "w", encoding="utf-8") as mf:
        mf.write(full_markdown)
    print(f"Final markdown blog post saved successfully to: {md_filepath}")
    
    # Step 6: Mark Topic Queue as Published in MongoDB with Markdown and JSON metadata
    print(f"Marking topic as published in MongoDB with filename: {md_filename}")
    queue_manager.mark_published(
        trace_id=trace_id,
        filename=md_filename,
        score=quality_score,
        word_count=word_count,
        markdown_content=full_markdown,
        metadata_json=json.dumps(json_data)
    )
    
    # Step 7: Delete Retrieval Ingestion Cache
    # Use __file__-based absolute path (same resolution strategy as retrieval_cache.py's CACHE_DIR)
    # so it resolves correctly regardless of what os.getcwd() returns at runtime.
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache_filepath = os.path.join(_project_root, "cache", "retrieval", f"{trace_id}.json")
    if os.path.exists(cache_filepath):
        try:
            os.remove(cache_filepath)
            print(f"Successfully deleted retrieval cache file: {cache_filepath}")
        except Exception as e:
            print(f"Warning: Failed to delete retrieval cache file {cache_filepath}: {e}")
            
    state["final_blog"] = processed_blog
    metadata["word_count"] = word_count
    state["metadata"] = metadata
    
    return state
