# 🎮 PyDex

[![Tests](https://github.com/Meobanh22/pydex/actions/workflows/test.yml/badge.svg)](https://github.com/Meobanh22/pydex/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-Rich-magenta.svg)](https://github.com/Textualize/rich)

> A gamified, Pokédex-style CLI tool to explore, track, and master the Python Standard Library. 🐍✨

---

## 🌟 Key Features

- ⚡ **Offline-First & Lightning Fast**: Pre-bundled with an embedded SQLite database containing **18 standard library modules** and **485 functions**. Zero network latency.
- 🔍 **Smart AST Project Scanner**: Recursively scans `.py` files using Python's Abstract Syntax Tree (`ast`), resolves complex chained/submodule calls (`os.path.join`, `datetime.datetime.now`), and unlocks new functions in your Dex!
- ⭐ **Core Mastery System**: 119 essential functions marked with gold stars (`★`) to help you focus on industry-standard APIs.
- 🔎 **Intelligent Search & Typo Suggestions**: Search functions by name or arguments with smart result ranking and fuzzy "Did you mean?" suggestions powered by `difflib`.
- 📝 **Personal Note-Taking**: Attach study notes or reminders directly to any function.
- 🧪 **Enterprise Quality**: Covered by a complete `pytest` suite and automated multi-version GitHub Actions CI.

---

## 📦 Installation

Clone the repository and install it in editable mode:

```bash
git clone https://github.com/Meobanh22/pydex.git
cd pydex
pip install -e .
```

---

## 🚀 Quick Start & Commands

### 1. Open your Dex (Progress Overview)
View your overall completion rate and progress across standard modules:
```bash
# View active modules with discoveries
pydex open

# View all 18 modules (including 0% progress)
pydex open -a

# Inspect unlocked functions inside a specific module
pydex open math
```

### 2. Scan Code to Unlock Functions
Point PyDex to any Python file or directory to scan for standard library usage:
```bash
# Scan current directory recursively
pydex scan

# Scan a specific file or folder
pydex scan my_script.py
pydex scan src/
```

### 3. Search Functions with Smart Suggestions
Search functions by name or argument, with automatic truncation and suggestions:
```bash
# Exact search
pydex search sqrt

# Partial match search
pydex search get -p

# Search by argument name
pydex search --by-arg encoding

# Typo tolerance (fuzzy matching)
pydex search pirnt
# Output: Did you mean: print, input, randint?
```

### 4. Personal Notes
Add your own learning notes to any function:
```bash
# Add or update a note
pydex note sqrt "Calculates square root; faster than x ** 0.5 for floats."

# View note
pydex note sqrt

# Clear note
pydex note sqrt -c
```

---

## 🏗️ Architecture & Tech Stack

- **CLI Engine**: Built with `argparse` and styled with `rich` tables, panels, and badges.
- **AST Parsing**: Native `ast` module traversal with custom attribute unnesting (`ast.Attribute`).
- **Data Layer**: Embedded SQLite with version migration pragmas (`PRAGMA user_version`) and in-memory test isolation.
- **CI / CD**: GitHub Actions matrix workflow testing on Python 3.10, 3.11, 3.12, and 3.13 on Ubuntu.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.

Developed with ❤️ by **Nguyen Duy Manh (Meobanh)**.

