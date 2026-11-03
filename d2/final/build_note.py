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
import tempfile
with tempfile.TemporaryDirectory() as prof:            # own profile, so a running Edge window can't block it
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={prof}",
                    "--no-first-run", f"--print-to-pdf={HERE / 'D2_Data_Note.pdf'}", (HERE / "D2_Data_Note.html").as_uri()],
                   check=True, capture_output=True, timeout=90)
subprocess.run(["pandoc", "D2_Data_Note.html", "-o", "D2_Data_Note.docx", "--resource-path=."], cwd=HERE, check=True)

import pymupdf
d = pymupdf.open(HERE / "D2_Data_Note.pdf")
print(f"pages: {len(d)}")
for i, p in enumerate(d):
    p.get_pixmap(dpi=110).save(HERE / f"page{i + 1}.png")
