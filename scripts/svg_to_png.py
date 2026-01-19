import subprocess
import sys
from tkinter import filedialog

from app import paths

file_paths = filedialog.askopenfilenames(filetypes=[("svg", "*.svg")], initialdir=paths.STATIC_DIR)

if not file_paths:
    print("No selected files, aborting")
    sys.exit()

print("Selected files:", *file_paths, sep="\n")
sys.exit(subprocess.check_call(["inkscape", "--export-type=png", *file_paths]))  # noqa: S603, S607
