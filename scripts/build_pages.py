"""Package only source and web assets, never the local database."""
from pathlib import Path
import shutil
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist"
OUT.mkdir(exist_ok=True)
for folder in ("web", "app"):
    target = OUT / folder
    target.mkdir(exist_ok=True)
    for source in (ROOT / folder).iterdir():
        if source.suffix in (".py", ".js", ".css"):
            shutil.copy2(source, target / source.name)
html = (ROOT / "web/index.html").read_text(encoding="utf-8")
html = html.replace('/assets/styles.css', './web/styles.css').replace('/assets/app.js', './web/pages.js')
(OUT / "index.html").write_text(html, encoding="utf-8")
(OUT / "python-files.json").write_text(json.dumps(["app/" + p.name for p in (ROOT / "app").glob("*.py")]), encoding="utf-8")
(OUT / ".nojekyll").touch()
print("GitHub Pages artifact ready: dist/")
