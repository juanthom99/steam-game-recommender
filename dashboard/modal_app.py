"""Serve the Streamlit dashboard on Modal.

Deploy:  C:/Users/juant/.venvs/steamrec-ml/Scripts/modal deploy dashboard/modal_app.py
The app reads only public, read-only Supabase tables, so no secret is needed.
"""
import shlex
import subprocess
from pathlib import Path

import modal

here = Path(__file__).parent
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("streamlit==1.66.1", "supabase", "pandas", "altair")
         .add_local_file(here / "app.py", "/root/app.py"))
app = modal.App("steamrec-d2-dashboard", image=image)


@app.function(max_containers=1, scaledown_window=300)
@modal.concurrent(max_inputs=50)
@modal.web_server(8000, startup_timeout=120)
def run():
    cmd = ("streamlit run /root/app.py --server.port 8000 --server.address 0.0.0.0 --server.headless true "
           "--server.enableCORS=false --server.enableXsrfProtection=false --browser.gatherUsageStats false")
    subprocess.Popen(shlex.split(cmd))
