from setuptools import setup, find_packages

setup(
    name="notemd-mcp",
    version="0.4.0",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'notemd-mcp = notemd_mcp.main:start_server',
        ],
    },
)
