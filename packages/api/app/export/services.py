"""
Export service — renders Standard Format documents and Summary Views to PDF
using WeasyPrint (HTML → PDF pipeline, theme-aware).
"""

import io
from weasyprint import HTML, CSS
from app.documents.schemas import StandardFormat
from app.highlights.schemas import SummaryView


_BASE_CSS = """
body { font-family: Georgia, serif; margin: 2cm; color: #1a1a1a; }
h1 { font-size: 2em; border-bottom: 2px solid #333; padding-bottom: 0.2em; }
h2 { font-size: 1.6em; }
h3 { font-size: 1.3em; }
h4, h5, h6 { font-size: 1.1em; }
p  { line-height: 1.7; margin: 0.8em 0; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; }
.highlight { background: #fff3b0; border-left: 4px solid #f4c430; padding: 0.4em 0.8em; }
.ancestor  { color: #555; font-style: italic; margin-bottom: 0.2em; }
"""

_THEME_CSS: dict[str, str] = {
    "default": "",
    "dark": "body { background: #1e1e1e; color: #d4d4d4; } h1,h2,h3 { color: #9cdcfe; }",
    "sepia": "body { background: #f5f0e8; color: #3b2f2f; }",
}


def _nodes_to_html(nodes: list[dict]) -> str:
    parts = []
    for node in nodes:
        ntype = node.get("type")
        text = node.get("text", "") or ""

        if ntype == "heading":
            lvl = node.get("level", 1)
            parts.append(f"<h{lvl}>{text}</h{lvl}>")
        elif ntype == "paragraph":
            parts.append(f"<p>{text}</p>")
        elif ntype == "list_item":
            parts.append(f"<li>{text}</li>")
        elif ntype == "table":
            rows = (node.get("content") or {}).get("rows", [])
            html = "<table>"
            for i, row in enumerate(rows):
                html += "<tr>"
                tag = "th" if i == 0 else "td"
                for cell in row:
                    html += f"<{tag}>{cell or ''}</{tag}>"
                html += "</tr>"
            html += "</table>"
            parts.append(html)
        elif ntype == "image":
            alt = (node.get("content") or {}).get("alt", "")
            parts.append(f"<p><em>[Image: {alt}]</em></p>")
        elif ntype == "code":
            parts.append(f"<pre><code>{text}</code></pre>")

        # Recurse into children
        children = node.get("children", [])
        if children:
            parts.append(_nodes_to_html(children))

    return "\n".join(parts)


def export_standard_format_to_pdf(doc: StandardFormat, theme: str = "default") -> bytes:
    title = doc.meta.title
    body_html = _nodes_to_html([n.model_dump() for n in doc.nodes])
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>{title}</title></head>
    <body>
      <h1>{title}</h1>
      {body_html}
    </body>
    </html>
    """
    theme_css = _THEME_CSS.get(theme, "")
    css = CSS(string=_BASE_CSS + theme_css)
    return HTML(string=html).write_pdf(stylesheets=[css])


def export_summary_to_pdf(summary: SummaryView, theme: str = "default") -> bytes:
    parts = [f"<h1>Summary — {summary.document_title}</h1>"]

    for section in summary.sections:
        ancestors = section.get("ancestors", [])
        nodes = section.get("nodes", [])
        color = section.get("color", "yellow")
        note = section.get("note")

        if ancestors:
            breadcrumb = " › ".join(a["text"] for a in ancestors)
            parts.append(f'<p class="ancestor">{breadcrumb}</p>')

        parts.append('<div class="highlight">')
        parts.append(_nodes_to_html(nodes))
        if note:
            parts.append(f'<p><strong>Note:</strong> {note}</p>')
        parts.append("</div>")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>Summary — {summary.document_title}</title></head>
    <body>{"".join(parts)}</body>
    </html>
    """
    theme_css = _THEME_CSS.get(theme, "")
    css = CSS(string=_BASE_CSS + theme_css)
    return HTML(string=html).write_pdf(stylesheets=[css])
