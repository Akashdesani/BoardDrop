import subprocess
import os
import sys
import tkinter as tk
from tkinter import messagebox

# Hide the root Tkinter window so an empty background window doesn't appear
root = tk.Tk()
root.withdraw()

# Reliably get the application directory whether run as a script or compiled .exe
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

captcha = os.path.join(APP_DIR, "Captcha.exe")

# Check if Captcha executable exists
if not os.path.exists(captcha):
    messagebox.showerror(
        "Error",
        f"Captcha.exe not found!\n\nExpected location:\n{captcha}"
    )
    sys.exit(1)

# Run the Captcha process and wait for it to finish
result = subprocess.run([captcha])

# If return code is 0 (Verification Successful)
if result.returncode == 0:
    uninstaller = os.path.join(APP_DIR, "unins000.exe")

    # Proceed to trigger the main uninstaller
    if os.path.exists(uninstaller):
        subprocess.Popen([uninstaller])
        sys.exit(0)
    else:
        messagebox.showerror(
            "Error",
            f"unins000.exe not found!\n\nExpected location:\n{uninstaller}"
        )
        sys.exit(1)
else:
    # If the user cancelled the captcha or it failed
    sys.exit(1)