from pathlib import Path

from setuptools import setup, find_packages

README_PATH = Path(__file__).with_name("README.md")
LONG_DESCRIPTION = README_PATH.read_text(encoding="utf-8") if README_PATH.exists() else ""

setup(
    name="notemd-mcp",
    version="0.6.1",
    description="Notemd MCP server for AI-powered text processing and knowledge workflows.",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'notemd-mcp = notemd_mcp.main:start_server',
        ],
    },
)
