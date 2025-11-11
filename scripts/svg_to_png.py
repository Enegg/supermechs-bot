import subprocess
import sys
import tkinter as tk
from tkinter import filedialog

from app import paths

root = tk.Tk()
root.withdraw()
file_paths = filedialog.askopenfilenames(filetypes=[("svg", "*.svg")], initialdir=paths.STATIC_DIR)
print("Selected files:", *file_paths, sep="\n")

if not file_paths:
    sys.exit()

sys.exit(subprocess.check_call(["inkscape", "--export-type=png", *file_paths]))  # noqa: S603, S607
