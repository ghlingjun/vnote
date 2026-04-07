#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch export Markdown files to PDF.

Uses the same approach as VNote: MD -> HTML -> PDF (via wkhtmltopdf or Qt WebEngine).
Supports VNote rendering style (web.css) and syntax highlight style (highlight.css);
default theme is "pure".

Usage:
  python batch_export_md_to_pdf.py [options] <input_path> [input_path ...]

  input_path: file(s) or folder(s). Folders are scanned for .md files (optional -r for recursive).

Requirements:
  - PDF: default Qt WebEngine (pip install PyQt6 PyQt6-WebEngine); or --use-wkhtmltopdf + wkhtmltopdf
  - MD->HTML: pandoc (recommended) or Python package: pip install markdown

Examples:
  python batch_export_md_to_pdf.py -o ./pdf_out ./notes
  python batch_export_md_to_pdf.py -o ./pdf_out -r ./notebook --theme pure
  python batch_export_md_to_pdf.py -o ./pdf_out --use-wkhtmltopdf -r ./notes
"""

from __future__ import print_function

import argparse
import os
import re
import subprocess
import sys
import tempfile

# Ensure script dir is on path so pdf_export_webengine can be imported when run from any cwd
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

try:
    from pdf_export_webengine import (
        html_to_pdf_webengine,
        is_available as webengine_available,
        get_webengine_error,
    )
except ImportError:
    webengine_available = lambda: False
    html_to_pdf_webengine = None
    get_webengine_error = lambda: "pdf_export_webengine not found (ensure it is next to this script)"

try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False


def find_pandoc():
    """Return path to pandoc or None."""
    try:
        out = subprocess.check_output(
            ["pandoc", "--version"],
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=5,
        )
        if "pandoc" in out.split("\n", 1)[0].lower():
            return "pandoc"
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    for name in ("pandoc.exe", "pandoc"):
        try:
            out = subprocess.check_output(
                [name, "--version"],
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                timeout=5,
            )
            if "pandoc" in out.split("\n", 1)[0].lower():
                return name
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def strip_cite_links(md_content):
    """Remove [xxx](CITE) citation links from markdown content (e.g. [6972d3526f4a160226043e0d](CITE))."""
    return re.sub(r"\[[^\]]*\]\(CITE\)", "", md_content, flags=re.IGNORECASE)


def read_md_file(md_path, encoding="utf-8"):
    """
    Read markdown file with correct encoding. On Windows, fall back to GBK if UTF-8 fails,
    to handle files saved with system default (e.g. GBK) instead of UTF-8.
    """
    try:
        with open(md_path, "r", encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError:
        if sys.platform == "win32":
            try:
                with open(md_path, "r", encoding="gbk") as f:
                    return f.read()
            except (UnicodeDecodeError, LookupError):
                pass
        raise


def md_to_html_pandoc(md_path, html_path, encoding="utf-8"):
    """Convert MD to HTML using pandoc. Returns True on success."""
    pandoc = find_pandoc()
    if not pandoc:
        return False
    try:
        content = read_md_file(md_path, encoding)
        content = strip_cite_links(content)
        cwd = os.path.dirname(os.path.abspath(md_path))
        cmd = [
            pandoc,
            "-f", "markdown+smart+raw_html",
            "-t", "html",
            "--standalone",
            "--metadata", "title=",
            "-o", html_path,
        ]
        # Use binary stdin and send UTF-8 bytes so pandoc gets correct encoding on Windows
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = proc.communicate(input=content.encode("utf-8"), timeout=60)
        return proc.returncode == 0 and os.path.isfile(html_path)
    except Exception:
        return False


def md_to_html_markdown_lib(md_path, html_path, encoding="utf-8"):
    """Convert MD to HTML using Python markdown. Returns True on success."""
    if not HAS_MARKDOWN:
        return False
    try:
        text = read_md_file(md_path, encoding)
        text = strip_cite_links(text)
        html = markdown.markdown(
            text,
            extensions=["extra", "codehilite", "toc", "tables"],
            extension_configs={"codehilite": {"css_class": "highlight"}},
        )
        full = (
            "<!DOCTYPE html><html><head><meta charset=\"utf-8\"/>"
            "<title></title></head><body>{}</body></html>"
        ).format(html)
        with open(html_path, "w", encoding=encoding) as f:
            f.write(full)
        return True
    except Exception:
        return False


def md_to_html(md_path, html_path, prefer_pandoc=True):
    """Convert MD to HTML. Prefer pandoc if available."""
    if prefer_pandoc and find_pandoc():
        if md_to_html_pandoc(md_path, html_path):
            return True
    if md_to_html_markdown_lib(md_path, html_path):
        return True
    if not prefer_pandoc and find_pandoc():
        return md_to_html_pandoc(md_path, html_path)
    return False


def _script_dir():
    """Return directory where this script lives (for resolving repo themes)."""
    return os.path.dirname(os.path.abspath(__file__))


def resolve_theme_paths(theme_name):
    """
    Resolve paths to web.css and highlight.css for a VNote theme name.
    Returns (web_css_path or None, highlight_css_path or None).
    """
    if not theme_name:
        return (None, None)
    name = theme_name.strip().lower()
    script_dir = _script_dir()
    repo_root = os.path.dirname(script_dir)
    repo_themes = os.path.join(repo_root, "src", "data", "extra", "themes", name)
    web_css = os.path.join(repo_themes, "web.css")
    highlight_css = os.path.join(repo_themes, "highlight.css")
    if os.path.isfile(web_css) and os.path.isfile(highlight_css):
        return (web_css, highlight_css)
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        user_themes = os.path.join(base, "vnotex", "themes", name)
    else:
        user_themes = os.path.join(os.path.expanduser("~"), ".config", "vnotex", "themes", name)
    web_css_u = os.path.join(user_themes, "web.css")
    highlight_css_u = os.path.join(user_themes, "highlight.css")
    if os.path.isfile(web_css_u) and os.path.isfile(highlight_css_u):
        return (web_css_u, highlight_css_u)
    w = web_css if os.path.isfile(web_css) else (web_css_u if os.path.isfile(web_css_u) else None)
    h = highlight_css if os.path.isfile(highlight_css) else (
        highlight_css_u if os.path.isfile(highlight_css_u) else None)
    return (w, h)


def resolve_vnote_export_template():
    """Return path to VNote markdown-export-template.html, or None if not found."""
    script_dir = _script_dir()
    repo_root = os.path.dirname(script_dir)
    repo_path = os.path.join(repo_root, "src", "data", "extra", "web", "markdown-export-template.html")
    if os.path.isfile(repo_path):
        return repo_path
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        user_path = os.path.join(base, "vnotex", "web", "markdown-export-template.html")
    else:
        user_path = os.path.join(os.path.expanduser("~"), ".config", "vnotex", "web",
                                 "markdown-export-template.html")
    if os.path.isfile(user_path):
        return user_path
    return None


def _extract_body_inner_html(html_content):
    """Extract inner HTML of <body>...</body>. Returns full content if no body tag."""
    lower = html_content.lower()
    start = lower.find("<body")
    if start == -1:
        return html_content
    start = html_content.find(">", start) + 1
    end = lower.find("</body>", start)
    if end == -1:
        return html_content[start:]
    return html_content[start:end].strip()


def _build_theme_styles_string(web_css_path, highlight_css_path, encoding="utf-8"):
    """Build inline CSS string from web.css and highlight.css (with url rewrite)."""
    styles = []
    for path in (web_css_path, highlight_css_path):
        if not path or not os.path.isfile(path):
            continue
        try:
            css_dir = os.path.dirname(os.path.abspath(path))
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
            content = _rewrite_css_urls(content, css_dir)
            styles.append("/* {} */\n{}".format(os.path.basename(path), content))
        except Exception:
            continue
    return "\n".join(styles) if styles else ""


def _rewrite_css_urls(css_content, css_file_dir):
    """Rewrite relative url(...) in CSS to absolute file:// URLs for wkhtmltopdf."""
    def replace_url(match):
        raw = match.group(1).strip().strip('"\'')
        if not raw or raw.startswith(("http://", "https://", "data:", "#")):
            return match.group(0)
        abs_path = os.path.normpath(os.path.join(css_file_dir, raw))
        if not os.path.isfile(abs_path):
            return match.group(0)
        path_uri = abs_path.replace("\\", "/")
        if sys.platform == "win32" and len(path_uri) >= 2 and path_uri[1] == ":":
            path_uri = "/" + path_uri
        return "url(\"file://%s\")" % path_uri

    return re.sub(r"\burl\s*\(\s*([^)]+)\s*\)", replace_url, css_content)


def inject_styles_into_html(html_path, web_css_path, highlight_css_path, encoding="utf-8"):
    """Inject web.css and highlight.css content into HTML as <style> in <head>."""
    if not web_css_path and not highlight_css_path:
        return
    styles = []
    for path in (web_css_path, highlight_css_path):
        if not path or not os.path.isfile(path):
            continue
        try:
            css_dir = os.path.dirname(os.path.abspath(path))
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
            content = _rewrite_css_urls(content, css_dir)
            styles.append("/* {} */\n{}".format(os.path.basename(path), content))
        except Exception:
            continue
    if not styles:
        return
    style_block = "<style type=\"text/css\">\n{}</style>".format("\n".join(styles))
    with open(html_path, "r", encoding=encoding) as f:
        html = f.read()
    if "<head>" in html:
        html = html.replace("<head>", "<head>\n  " + style_block, 1)
    elif "</head>" in html:
        html = html.replace("</head>", "  " + style_block + "\n</head>", 1)
    else:
        html = "<head>" + style_block + "</head>" + html
    with open(html_path, "w", encoding=encoding) as f:
        f.write(html)


def apply_vnote_export_template(html_path, template_path, body_content, style_content, title,
                                 encoding="utf-8"):
    """Replace html_path with VNote export template filled with body_content and style_content."""
    with open(template_path, "r", encoding=encoding) as f:
        tpl = f.read()
    title_escaped = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    tpl = tpl.replace("<!-- VX_TITLE_PLACEHOLDER -->", "<title>%s</title>" % title_escaped)
    tpl = tpl.replace("/* VX_GLOBAL_STYLES_PLACEHOLDER */", "")
    tpl = tpl.replace("/* VX_STYLES_PLACEHOLDER */", "")
    tpl = tpl.replace("/* VX_STYLES_CONTENT_PLACEHOLDER */", style_content or "")
    tpl = tpl.replace("<!-- VX_HEAD_PLACEHOLDER -->", "")
    tpl = tpl.replace("<!-- VX_BODY_CLASS_LIST_PLACEHOLDER -->", "")
    tpl = tpl.replace("<!-- VX_CONTENT_PLACEHOLDER -->", body_content or "")
    for start_mark, end_mark in [
        ("<!-- VX_OUTLINE_PANEL_START -->", "<!-- VX_OUTLINE_PANEL_END -->"),
        ("<!-- VX_OUTLINE_BUTTON_START -->", "<!-- VX_OUTLINE_BUTTON_END -->"),
    ]:
        start_i = tpl.find(start_mark)
        end_i = tpl.find(end_mark)
        if start_i != -1 and end_i != -1 and end_i > start_i:
            tpl = tpl[:start_i] + tpl[end_i + len(end_mark):]
    with open(html_path, "w", encoding=encoding) as f:
        f.write(tpl)


def html_to_pdf(wkhtmltopdf_exe, html_path, pdf_path, extra_args=None, cwd=None, verbose=False):
    """Convert HTML to PDF via wkhtmltopdf. Returns (True, None) or (False, error_message)."""
    args = [
        wkhtmltopdf_exe,
        "--encoding", "utf-8",
        "--enable-local-file-access",
        "--quiet",
    ]
    if extra_args:
        args.extend(extra_args)
    args.append(html_path)
    args.append(pdf_path)
    try:
        proc = subprocess.Popen(
            args,
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        _, stderr = proc.communicate(timeout=120)
        if proc.returncode != 0 or not os.path.isfile(pdf_path):
            err = (stderr or "").strip() or "wkhtmltopdf exited with code %s" % proc.returncode
            return (False, err)
        return (True, None)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        return (False, "wkhtmltopdf timed out")
    except Exception as e:
        return (False, str(e))


def collect_md_files(paths, recursive=False):
    """Yield absolute paths of .md files from given file/folder paths."""
    for p in paths:
        if not os.path.exists(p):
            print("Warning: path does not exist:", p, file=sys.stderr)
            continue
        absp = os.path.abspath(p)
        if os.path.isfile(absp):
            if absp.lower().endswith(".md"):
                yield absp
            else:
                print("Warning: not a .md file:", p, file=sys.stderr)
        else:
            for root, _, files in os.walk(absp):
                for f in files:
                    if f.lower().endswith(".md"):
                        yield os.path.join(root, f)
                if not recursive:
                    break


def main():
    parser = argparse.ArgumentParser(
        description="Batch export Markdown files to PDF (wkhtmltopdf or Qt WebEngine)."
    )
    parser.add_argument("input_path", nargs="+", help="Markdown file(s) or folder(s) to export")
    parser.add_argument("-o", "--output-dir", default=None, help="Output directory for PDFs")
    parser.add_argument("-r", "--recursive", action="store_true", help="Include subfolders")
    parser.add_argument("--wkhtmltopdf", default="wkhtmltopdf",
                        help="Path to wkhtmltopdf (used only with --use-wkhtmltopdf)")
    parser.add_argument("--wkhtmltopdf-args", default="", help="Extra args for wkhtmltopdf")
    parser.add_argument("--use-wkhtmltopdf", action="store_true",
                        help="Use wkhtmltopdf for PDF (default is Qt WebEngine when available)")
    parser.add_argument("--theme", default="pure", help="VNote theme (default: pure)")
    parser.add_argument("--web-css", default=None, help="Path to web.css")
    parser.add_argument("--highlight-css", default=None, help="Path to highlight.css")
    parser.add_argument("--use-vnote-template", action="store_true",
                        help="Use VNote export HTML template")
    parser.add_argument("--no-pandoc", action="store_true", help="Use only Python markdown lib")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Only list files")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Default: use Qt WebEngine when available; else wkhtmltopdf. Use --use-wkhtmltopdf to force wk.
    use_webengine = not args.use_wkhtmltopdf and webengine_available()
    if use_webengine and html_to_pdf_webengine is None:
        use_webengine = False

    wk = None
    if not use_webengine:
        wk = args.wkhtmltopdf
        if not os.path.isabs(wk):
            for d in os.environ.get("PATH", "").split(os.pathsep):
                cand = os.path.join(d.strip(), wk)
                if os.path.isfile(cand):
                    wk = cand
                    break
        if not os.path.isfile(wk) and sys.platform == "win32" and not wk.lower().endswith(".exe"):
            if os.path.isfile(wk + ".exe"):
                wk = wk + ".exe"
        if not os.path.isfile(wk):
            if args.use_wkhtmltopdf:
                print("Error: wkhtmltopdf not found. Install from https://wkhtmltopdf.org/downloads.html "
                      "or omit --use-wkhtmltopdf to use Qt WebEngine (pip install PyQt6 PyQt6-WebEngine).",
                      file=sys.stderr)
            else:
                print("Error: Qt WebEngine not available and wkhtmltopdf not found.",
                      file=sys.stderr)
                err = get_webengine_error() if callable(get_webengine_error) else None
                if err:
                    print("  Qt WebEngine error: %s" % err, file=sys.stderr)
                print("  To use Qt WebEngine (default): pip install PyQt6 PyQt6-WebEngine", file=sys.stderr)
                print("  Ensure pdf_export_webengine.py is in the same folder as this script.", file=sys.stderr)
                print("  Or install wkhtmltopdf and run with: --use-wkhtmltopdf", file=sys.stderr)
            sys.exit(1)

    extra_args = []
    if args.wkhtmltopdf_args:
        extra_args = re.split(r"\s+", args.wkhtmltopdf_args.strip())

    web_css = args.web_css
    highlight_css = args.highlight_css
    if web_css is None or highlight_css is None:
        theme_web, theme_highlight = resolve_theme_paths(args.theme)
        if web_css is None:
            web_css = theme_web
        if highlight_css is None:
            highlight_css = theme_highlight
    if args.verbose and (web_css or highlight_css):
        print("Styles: web=%s highlight=%s" % (web_css or "(none)", highlight_css or "(none)"))

    md_files = list(collect_md_files(args.input_path, args.recursive))
    if not md_files:
        print("No .md files found.", file=sys.stderr)
        sys.exit(0)

    if args.dry_run:
        for f in md_files:
            print(f)
        sys.exit(0)

    out_dir = args.output_dir
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    failed = []
    for md_path in md_files:
        base = os.path.splitext(os.path.basename(md_path))[0]
        pdf_name = base + ".pdf"
        if out_dir:
            pdf_path = os.path.join(out_dir, pdf_name)
        else:
            pdf_path = os.path.join(os.path.dirname(md_path), pdf_name)

        if args.verbose:
            print("Exporting:", md_path, "->", pdf_path)

        tmp_parent = None
        if sys.platform == "win32":
            tmp_parent = out_dir if out_dir else os.path.dirname(md_path)
        try:
            tmp = tempfile.mkdtemp(prefix="vnote_batch_pdf_", dir=tmp_parent)
        except (OSError, PermissionError):
            tmp = tempfile.mkdtemp(prefix="vnote_batch_pdf_")
        try:
            html_path = os.path.join(tmp, "temp.html")
            if not md_to_html(md_path, html_path, prefer_pandoc=not args.no_pandoc):
                print("Failed to convert MD to HTML:", md_path, file=sys.stderr)
                failed.append(md_path)
                continue
            if args.use_vnote_template:
                template_path = resolve_vnote_export_template()
                if not template_path or not os.path.isfile(template_path):
                    print("Warning: VNote export template not found, falling back to inline styles",
                          file=sys.stderr)
                    inject_styles_into_html(html_path, web_css, highlight_css)
                else:
                    with open(html_path, "r", encoding="utf-8") as f:
                        body_content = _extract_body_inner_html(f.read())
                    style_content = _build_theme_styles_string(web_css, highlight_css)
                    apply_vnote_export_template(html_path, template_path, body_content,
                                                style_content, "")
            else:
                inject_styles_into_html(html_path, web_css, highlight_css)
            cwd = os.path.dirname(os.path.abspath(md_path))
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            if "<base " not in html_content and "<base " not in html_content.lower():
                cwd_uri = cwd.replace("\\", "/")
                if sys.platform == "win32" and len(cwd_uri) >= 2 and cwd_uri[1] == ":":
                    cwd_uri = "/" + cwd_uri
                base_tag = '<base href="file://{}/">'.format(cwd_uri)
                if "<head>" in html_content:
                    html_content = html_content.replace("<head>", "<head>\n  " + base_tag, 1)
                else:
                    html_content = "<head>" + base_tag + "</head>" + html_content
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
            tmp_pdf = os.path.join(tmp, "out.pdf")
            if use_webengine:
                base_url = cwd.replace("\\", "/")
                if sys.platform == "win32" and len(base_url) >= 2 and base_url[1] == ":":
                    base_url = "/" + base_url
                ok, err = html_to_pdf_webengine(html_path, tmp_pdf, base_url)
            else:
                ok, err = html_to_pdf(wk, html_path, tmp_pdf, extra_args=extra_args, cwd=cwd,
                                      verbose=args.verbose)
            if not ok:
                print("Failed to convert HTML to PDF:", md_path, file=sys.stderr)
                if err:
                    print("  %s" % err, file=sys.stderr)
                failed.append(md_path)
                continue
            try:
                import shutil
                shutil.copy2(tmp_pdf, pdf_path)
            except Exception as e:
                print("Failed to copy PDF:", e, file=sys.stderr)
                failed.append(md_path)
                continue
        finally:
            try:
                import shutil as _shutil
                _shutil.rmtree(tmp, ignore_errors=True)
            except Exception:
                pass
        print("OK:", pdf_path)

    if failed:
        print("Failed count:", len(failed), file=sys.stderr)
        sys.exit(1)
    print("Done. Exported", len(md_files), "file(s).")


if __name__ == "__main__":
    main()
