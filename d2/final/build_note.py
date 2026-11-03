"""Build the D2 data note: fill repo link, tag and commit, then print to PDF with Edge and convert to Word.

Run: PYTHONUTF8=1 C:/Users/juant/.venvs/steamrec-ml/Scripts/python d2/final/build_note.py [repo_url] [tag] [commit]
Out: d2/final/D2_Data_Note.html, .pdf, .docx
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
repo, tag, commit = (sys.argv[1:] + ["(link pending)", "d2-submission", "pending"])[:3] if len(sys.argv) > 1 else ("(link pending)", "d2-submission", "pending")

s = (HERE / "D2_Data_Note.src.html").read_text(encoding="utf-8")
s = s.replace("{{REPO}}", repo).replace("{{REPO_SHORT}}", repo.replace("https://", "")).replace("{{TAG}}", tag).replace("{{COMMIT}}", commit)
(HERE / "D2_Data_Note.html").write_text(s, encoding="utf-8")
import shutil
import tempfile
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
browser = CHROME if Path(CHROME).exists() else EDGE
with tempfile.TemporaryDirectory() as tmp:             # own profile and output file, so nothing open can block it
    out = Path(tmp) / "note.pdf"
    import time
    prof = Path(tempfile.gettempdir()) / "d2note_browser_profile"   # reused: a fresh profile's first run is slow
    proc = subprocess.Popen([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={prof}",
                             "--no-first-run", f"--print-to-pdf={out}", (HERE / "D2_Data_Note.html").as_uri()],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    last, t0 = -1, time.time()                          # headless Chrome can linger after writing: wait for a stable file
    while time.time() - t0 < 90:
        time.sleep(1.5)
        size = out.stat().st_size if out.exists() else -1
        if size > 0 and size == last:
            break
        last = size
    proc.kill(); proc.wait()
    if not out.exists():
        raise SystemExit("PDF was not written")
    shutil.copyfile(out, HERE / "D2_Data_Note.pdf")
subprocess.run(["pandoc", "D2_Data_Note.html", "-o", "D2_Data_Note.docx", "--resource-path=."], cwd=HERE, check=True)

import pymupdf
d = pymupdf.open(HERE / "D2_Data_Note.pdf")
print(f"pages: {len(d)}")
for i, p in enumerate(d):
    p.get_pixmap(dpi=110).save(HERE / f"page{i + 1}.png")
