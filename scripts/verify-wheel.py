"""Check an installed wheel outside the source tree without contacting providers."""
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

wheel_paths = [Path(sys.argv[1])] if len(sys.argv) == 2 else list(Path('artifacts').glob('*.whl'))
if len(sys.argv) > 2 or len(wheel_paths) != 1:
    raise SystemExit('Pass one wheel path, or leave exactly one wheel in artifacts/.')
wheel = wheel_paths[0].resolve()
with zipfile.ZipFile(wheel) as archive:
    required = {'main.py', 'notemd_core.py', 'config.py', 'markdown_processing.py'}
    if not required.issubset(archive.namelist()):
        raise RuntimeError('Wheel is missing runtime modules')

with tempfile.TemporaryDirectory(prefix='notemd-wheel-', dir=wheel.parent) as directory:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-deps', '--no-compile', '--target', directory, str(wheel)], check=True)
    # The runtime dependencies come from the test environment; all project modules
    # must resolve from the isolated install, never from the checkout.
    script = '''
import importlib, importlib.metadata, pathlib, sys
root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
for name in ('main', 'notemd_core', 'config', 'markdown_processing'):
    module = importlib.import_module(name)
    assert pathlib.Path(module.__file__).resolve().is_relative_to(root), module.__file__
distribution = next(d for d in importlib.metadata.distributions(path=[str(root)]) if d.metadata['Name'] == 'notemd-mcp')
entry = next(e for e in distribution.entry_points if e.group == 'console_scripts' and e.name == 'notemd-mcp')
assert callable(entry.load())
print('Installed wheel modules and console entry verified.')
'''
    subprocess.run([sys.executable, '-c', script, directory], cwd=directory, check=True)
