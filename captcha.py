import os
import sys
import random
import string
import customtkinter as ctk

# ---------------- Theme Setup ----------------
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("BoardDrop Uninstall Verification")
app.geometry("450x320")  
app.resizable(False, False)

# ---------------- Generate Captcha ----------------
captcha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# ---------------- UI Elements ----------------
title = ctk.CTkLabel(
    app,
    text="BoardDrop Uninstall Verification",
    font=("Segoe UI", 20, "bold")
)
title.pack(pady=(25, 10))

lbl = ctk.CTkLabel(
    app,
    text=f"To continue uninstalling, type this code:\n\n{captcha}",
    font=("Consolas", 18)
)
lbl.pack(pady=(0, 10))

entry = ctk.CTkEntry(
    app,
    width=240,
    height=45,
    justify="center",
    font=("Consolas", 20, "bold")
)
entry.pack(pady=10)
entry.focus()  # Auto-focus so the user can start typing immediately

status = ctk.CTkLabel(app, text="", font=("Segoe UI", 13))
status.pack(pady=(0, 5))

# ---------------- Functions ----------------
def verify(event=None):
    if entry.get().strip().upper() == captcha:
        app.destroy()
        os._exit(0)   # Success - return code 0 signals wrapper to proceed
    else:
        status.configure(text="❌ Incorrect code. Please try again.", text_color="#EF4444")
        entry.delete(0, "end")

def cancel(event=None):
    app.destroy()
    os._exit(1)   # Cancel - return code 1 signals wrapper to stop

# ---------------- Keyboard Shortcuts ----------------
app.bind('<Return>', verify)   # Press Enter to Verify
app.bind('<Escape>', cancel)   # Press Esc to Cancel

# ---------------- Buttons ----------------
btn_frame = ctk.CTkFrame(app, fg_color="transparent")
btn_frame.pack(pady=10)

btn_verify = ctk.CTkButton(
    btn_frame, 
    text="Verify & Uninstall", 
    command=verify,
    font=("Segoe UI", 14, "bold"),
    height=38,
    width=140
)
btn_verify.pack(side="left", padx=10)

btn_cancel = ctk.CTkButton(
    btn_frame,
    text="Cancel",
    fg_color="#EF4444",
    hover_color="#DC2626",
    command=cancel,
    font=("Segoe UI", 14, "bold"),
    height=38,
    width=140
)
btn_cancel.pack(side="right", padx=10)

# Handle window close (X button)
app.protocol("WM_DELETE_WINDOW", cancel)

app.mainloop()