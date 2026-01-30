#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF export via Qt WebEngine (same engine as VNote when "使用 wkhtmltopdf" is unchecked).

Use this to get PDF output that matches VNote's in-app export (Chromium rendering).
Requires: PyQt6 + PyQt6-WebEngine, or PyQt5 + PyQt5-WebEngine, or PySide6/PySide2 with WebEngine.

  pip install PyQt6 PyQt6-WebEngine   # or PyQt5 / PySide6 / PySide2

Usage from batch_export_md_to_pdf.py: set --webengine and do not pass --wkhtmltopdf path.
"""

from __future__ import print_function

import os
import sys

# Optional: run headless on Linux (no display)
if sys.platform.startswith("linux"):
    if "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

_WEBENGINE_IMPL = None  # (app, PageClass, QUrl, make_layout)
_WEBENGINE_LAST_ERROR = None  # last exception when import failed


def get_webengine_error():
    """Return the last error message when Qt WebEngine failed to load, or None."""
    global _WEBENGINE_LAST_ERROR
    if _WEBENGINE_IMPL is not None and _WEBENGINE_IMPL != "unavailable":
        return None
    _try_import_webengine()  # ensure we tried
    return _WEBENGINE_LAST_ERROR


def _try_import_webengine():
    """Try to import Qt WebEngine. Returns (app, PageClass, QUrl, make_layout) or None."""
    global _WEBENGINE_IMPL, _WEBENGINE_LAST_ERROR
    if _WEBENGINE_IMPL is not None:
        return _WEBENGINE_IMPL if _WEBENGINE_IMPL != "unavailable" else None

    # Prefer PyQt6 -> PyQt5 -> PySide6 -> PySide2
    for name in ("PyQt6", "PyQt5", "PySide6", "PySide2"):
        try:
            if name == "PyQt6":
                from PyQt6.QtWidgets import QApplication
                from PyQt6.QtCore import QUrl, QMarginsF
                from PyQt6.QtWebEngineWidgets import QWebEngineView
                from PyQt6.QtGui import QPageLayout, QPageSize
                app = QApplication.instance() or QApplication(sys.argv + ["--no-sandbox"])
                PageClass = QWebEngineView

                def make_layout():
                    ps = QPageSize(QPageSize.PageSizeId.A4)
                    return QPageLayout(ps, QPageLayout.Orientation.Portrait,
                                      QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter)

                _WEBENGINE_IMPL = (app, PageClass, QUrl, make_layout)
                _WEBENGINE_LAST_ERROR = None
                return _WEBENGINE_IMPL
            elif name == "PyQt5":
                from PyQt5.QtWidgets import QApplication
                from PyQt5.QtCore import QUrl
                from PyQt5.QtWebEngineWidgets import QWebEngineView
                from PyQt5.QtPrintSupport import QPageLayout, QPageSize, QMarginsF
                app = QApplication.instance() or QApplication(sys.argv + ["--no-sandbox"])
                PageClass = QWebEngineView

                def make_layout():
                    ps = QPageSize(QPageSize.A4)
                    return QPageLayout(ps, QPageLayout.Portrait, QMarginsF(10, 10, 10, 10),
                                      QPageLayout.Millimeter)

                _WEBENGINE_IMPL = (app, PageClass, QUrl, make_layout)
                _WEBENGINE_LAST_ERROR = None
                return _WEBENGINE_IMPL
            elif name == "PySide6":
                from PySide6.QtWidgets import QApplication
                from PySide6.QtCore import QUrl, QMarginsF
                from PySide6.QtWebEngineWidgets import QWebEngineView
                from PySide6.QtPrintSupport import QPageLayout
                from PySide6.QtGui import QPageSize
                app = QApplication.instance() or QApplication(sys.argv + ["--no-sandbox"])
                PageClass = QWebEngineView

                def make_layout():
                    ps = QPageSize(QPageSize.PageSizeId.A4)
                    return QPageLayout(ps, QPageLayout.Orientation.Portrait,
                                      QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter)

                _WEBENGINE_IMPL = (app, PageClass, QUrl, make_layout)
                _WEBENGINE_LAST_ERROR = None
                return _WEBENGINE_IMPL
            elif name == "PySide2":
                from PySide2.QtWidgets import QApplication
                from PySide2.QtCore import QUrl
                from PySide2.QtWebEngineWidgets import QWebEngineView
                from PySide2.QtPrintSupport import QPageLayout, QPageSize, QMarginsF
                app = QApplication.instance() or QApplication(sys.argv + ["--no-sandbox"])
                PageClass = QWebEngineView

                def make_layout():
                    ps = QPageSize(QPageSize.A4)
                    return QPageLayout(ps, QPageLayout.Portrait, QMarginsF(10, 10, 10, 10),
                                      QPageLayout.Millimeter)

                _WEBENGINE_IMPL = (app, PageClass, QUrl, make_layout)
                _WEBENGINE_LAST_ERROR = None
                return _WEBENGINE_IMPL
        except Exception as e:
            # Keep first error (likely PyQt6) so user sees why their installed binding failed
            if _WEBENGINE_LAST_ERROR is None:
                _WEBENGINE_LAST_ERROR = "%s: %s" % (type(e).__name__, e)
            continue

    _WEBENGINE_IMPL = "unavailable"
    return None


def html_to_pdf_webengine(html_path, pdf_path, base_url, encoding="utf-8"):
    """
    Convert HTML file to PDF using Qt WebEngine (Chromium), same as VNote when not using wkhtmltopdf.

    Returns (True, None) on success, (False, error_message) on failure.
    base_url: directory URL for resolving relative links (e.g. file:///path/to/md_dir/).
    """
    impl = _try_import_webengine()
    if not impl:
        return (False, "Qt WebEngine not available. Install e.g. PyQt6 + PyQt6-WebEngine")

    try:
        app, PageClass, QUrl, make_layout = impl
    except Exception:
        return (False, "Qt WebEngine setup failed")

    if not os.path.isfile(html_path):
        return (False, "HTML file not found: %s" % html_path)

    with open(html_path, "r", encoding=encoding) as f:
        html_content = f.read()

    # Ensure base_url is a file:// URL ending with /
    base = base_url.replace("\\", "/").strip()
    if base and not base.endswith("/"):
        base = base + "/"
    if base and not base.startswith("file:"):
        if sys.platform == "win32" and len(base) >= 2 and base[1] == ":":
            base = "file:///" + base
        else:
            base = "file://" + (base if base.startswith("/") else "/" + base)

    url = QUrl(base)
    view = PageClass()
    # Do not show window (same as VNote headless export)
    view.resize(1, 1)
    page = view.page()

    result = {"success": False, "error": None, "done": False}

    def on_load_finished(ok):
        if not ok:
            result["error"] = "Failed to load HTML"
            result["done"] = True
            return
        try:
            layout = make_layout()

            def on_pdf_ready(data):
                try:
                    pdf_bytes = data.data() if hasattr(data, "data") else data
                    if pdf_bytes:
                        with open(pdf_path, "wb") as out:
                            out.write(pdf_bytes)
                        result["success"] = True
                except Exception as e:
                    result["error"] = str(e)
                result["done"] = True

            page.printToPdf(on_pdf_ready, layout)
        except Exception as e:
            result["error"] = str(e)
            result["done"] = True

    def on_pdf_finished(path, success):
        if hasattr(path, "toString"):
            path = path.toString()
        result["success"] = bool(success)
        if not success:
            result["error"] = "printToPdf failed for %s" % path
        result["done"] = True

    try:
        page.loadFinished.connect(on_load_finished)
        if hasattr(view, "pdfPrintingFinished"):
            view.pdfPrintingFinished.connect(on_pdf_finished)
    except Exception:
        pass

    view.setHtml(html_content, url)

    # Process events until load + print finish (with timeout)
    import time
    deadline = time.time() + 60
    while not result["done"] and time.time() < deadline:
        app.processEvents()
        time.sleep(0.05)

    if not result["done"]:
        result["error"] = "Timeout waiting for PDF"
    if result["error"]:
        return (False, result["error"])
    if not result["success"]:
        return (False, "PDF was not written")
    return (True, None)


def is_available():
    """Return True if Qt WebEngine can be used."""
    return _try_import_webengine() is not None


if __name__ == "__main__":
    # Minimal test: html_to_pdf_webengine in.html out.pdf file:///path/to/dir/
    if len(sys.argv) < 4:
        print("Usage: pdf_export_webengine.py <html> <pdf> <base_url>")
        sys.exit(1)
    ok, err = html_to_pdf_webengine(sys.argv[1], sys.argv[2], sys.argv[3])
    if ok:
        print("OK:", sys.argv[2])
    else:
        print("Error:", err, file=sys.stderr)
        sys.exit(1)
