@echo off
REM Batch export Markdown to PDF (same stack as VNote: wkhtmltopdf).
REM Usage: batch_export_md_to_pdf.cmd [options] <input_path> [input_path ...]
REM Example: batch_export_md_to_pdf.cmd -o pdf_out -r .\notes

set SCRIPT_DIR=%~dp0
set PYTHON=
where python >nul 2>&1 && set PYTHON=python
if "%PYTHON%"=="" where python3 >nul 2>&1 && set PYTHON=python3
if "%PYTHON%"=="" (
  echo Error: python or python3 not found in PATH.
  exit /b 1
)

"%PYTHON%" "%SCRIPT_DIR%batch_export_md_to_pdf.py" %*
