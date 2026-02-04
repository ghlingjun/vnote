# VNote 脚本说明

本目录包含 VNote 项目相关的辅助脚本，主要用于开发环境初始化、版本更新及 **Markdown 批量导出 PDF**。

---

## 一、批量导出 Markdown 为 PDF

### 1.1 功能概述

`batch_export_md_to_pdf.py` 可将一个或多个 Markdown 文件批量导出为 PDF，流程与 VNote 内建导出一致：

- **MD → HTML**：使用 pandoc（推荐）或 Python `markdown` 库
- **HTML → PDF**：默认使用 **Qt WebEngine**（与 VNote 中不勾选「使用 wkhtmltopdf」时相同），可选 **wkhtmltopdf**

支持：

- VNote 主题样式：**渲染样式**（web.css）与 **语法高亮样式**（highlight.css），默认主题为 **pure**
- 可选使用 VNote 导出模板（`markdown-export-template.html`）以更接近软件内导出版式
- 导出前自动移除文中的 `[xxx](CITE)` 引用链接

### 1.2 依赖

| 用途 | 依赖 | 说明 |
|------|------|------|
| **PDF 生成（默认）** | PyQt6 + PyQt6-WebEngine | `pip install PyQt6 PyQt6-WebEngine` |
| **PDF 生成（可选）** | wkhtmltopdf | 使用 `--use-wkhtmltopdf` 时需安装 |
| **MD→HTML** | pandoc（推荐）或 markdown | 无 pandoc 时：`pip install markdown` |

可选依赖可一并安装：

```bash
pip install -r requirements-export.txt
pip install PyQt6 PyQt6-WebEngine
```

### 1.3 基本用法

```bash
# 导出指定目录下所有 .md 到 pdf_out（不递归子目录）
python scripts/batch_export_md_to_pdf.py -o ./pdf_out ./notes

# 递归导出目录及子目录下所有 .md
python scripts/batch_export_md_to_pdf.py -o ./pdf_out -r ./notebook

# 导出指定文件
python scripts/batch_export_md_to_pdf.py -o ./pdf_out README.md docs/guide.md

# 不指定 -o 时，PDF 生成在与对应 .md 同目录
python scripts/batch_export_md_to_pdf.py -r ./notes
```

Windows 下也可使用：

```cmd
scripts\batch_export_md_to_pdf.cmd -o pdf_out -r notes
```

### 1.4 参数说明

| 参数 | 说明 |
|------|------|
| `input_path` | 一个或多个 .md 文件或目录（必填） |
| `-o, --output-dir` | PDF 输出目录；不指定则与对应 .md 同目录 |
| `-r, --recursive` | 对目录递归处理子目录 |
| `--theme` | VNote 主题名，用于 web.css 与 highlight.css（默认：pure） |
| `--web-css` | 渲染样式 web.css 的路径，覆盖 `--theme` 中的 web.css |
| `--highlight-css` | 语法高亮样式 highlight.css 的路径，覆盖 `--theme` 中的 highlight.css |
| `--use-vnote-template` | 使用 VNote 导出 HTML 模板，版式更接近软件内导出 |
| `--use-wkhtmltopdf` | 使用 wkhtmltopdf 生成 PDF（默认在有 PyQt6-WebEngine 时使用 Qt WebEngine） |
| `--wkhtmltopdf` | wkhtmltopdf 可执行文件路径（仅在使用 `--use-wkhtmltopdf` 时有效） |
| `--wkhtmltopdf-args` | 传给 wkhtmltopdf 的额外参数（如 `--margin-top 10mm`） |
| `--no-pandoc` | 不使用 pandoc，仅用 Python markdown 库做 MD→HTML |
| `-n, --dry-run` | 只列出将要导出的 .md，不执行导出 |
| `-v, --verbose` | 输出详细过程 |

### 1.5 使用示例

```bash
# 导出指定目录下所有 .md 到 pdf_out（不递归子目录）
python scripts/batch_export_md_to_pdf.py -o "D:\\workspace\\python\\output" "D:\\workspace\\python\\output"
python scripts/batch_export_md_to_pdf.py -o "D:\workspace\python\tools\output\enterprise_evaluation\260129\202602" "D:\workspace\python\tools\output\enterprise_evaluation\260129"

# 默认：Qt WebEngine + pure 主题
python scripts/batch_export_md_to_pdf.py -o ./pdf_out -r ./notes

# 使用其他主题（如 solarized-light）
python scripts/batch_export_md_to_pdf.py -o ./pdf_out --theme solarized-light -r ./notes

# 使用 VNote 导出模板
python scripts/batch_export_md_to_pdf.py -o ./pdf_out --use-vnote-template -r ./notes

# 强制使用 wkhtmltopdf
python scripts/batch_export_md_to_pdf.py -o ./pdf_out --use-wkhtmltopdf --wkhtmltopdf "C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe" -r ./notes

# 仅列出将要导出的文件
python scripts/batch_export_md_to_pdf.py -n -r ./notes
```

### 1.6 主题与样式

- 主题会从以下位置查找（与 VNote 一致）：
  - 仓库内：`src/data/extra/themes/<主题名>/`
  - 用户配置：Windows `%APPDATA%/vnotex/themes/`，Linux/macOS `~/.config/vnotex/themes/`
- 使用 `--web-css`、`--highlight-css` 可单独指定两个 CSS 文件路径，覆盖主题中的对应文件。

### 1.7 与 VNote 软件导出的差异

- 默认使用 **Qt WebEngine**（Chromium）时，渲染与 VNote 内「不勾选 wkhtmltopdf」的导出接近。
- HTML 结构由 pandoc/markdown 生成，与 VNote 预览的 DOM 不完全一致，同一套 CSS 下版式可能略有差异。
- 使用 `--use-vnote-template` 可让页面外壳更接近软件内导出。

### 1.8 相关文件

- **batch_export_md_to_pdf.py**：主脚本
- **pdf_export_webengine.py**：Qt WebEngine 导出模块（需与主脚本同目录，或保证可导入）
- **batch_export_md_to_pdf.cmd**：Windows 下调用主脚本的批处理
- **requirements-export.txt**：可选 Python 依赖（markdown、PyQt6-WebEngine 等）
- **INTEGRATE_WEBENGINE.md**：Qt WebEngine 接入说明（供二次开发参考）

---

## 二、其他脚本

| 脚本 | 说明 |
|------|------|
| **init.sh / init.cmd** | 初始化开发环境（Linux/macOS 用 init.sh，Windows 用 init.cmd） |
| **update_version.py** | 更新项目版本号 |
| **pre-commit** | Git 提交前钩子（如代码格式检查） |

使用方式见项目根目录 `AGENTS.md` 中的 Setup 与 Build 说明。
