from pathlib import Path
import zipfile

pkg = Path('dist/package')
out = Path('dist/TinyRoguesTracker-v2-windows.zip')
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for name in ['TinyRoguesTracker.exe', 'ids.json', 'README.md', 'report.txt', 'report.csv']:
        z.write(pkg / name, name)
print(out)
