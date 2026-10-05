from pathlib import Path

from setuptools import setup

README_PATH = Path(__file__).with_name("README.md")
LONG_DESCRIPTION = README_PATH.read_text(encoding="utf-8") if README_PATH.exists() else ""

setup(
    name="notemd-mcp",
    version="0.6.1",
    description="Notemd MCP server for AI-powered text processing and knowledge workflows.",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    py_modules=['main', 'notemd_core', 'config', 'markdown_processing'],
    python_requires='>=3.10',
    install_requires=Path(__file__).with_name('requirements.txt').read_text(encoding='utf-8').splitlines(),
    entry_points={
        'console_scripts': [
            'notemd-mcp = main:start_server',
        ],
    },
)
