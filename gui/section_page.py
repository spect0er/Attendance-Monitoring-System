"""
gui/section_page.py
===================
SCREEN 1 – Section Manager

Responsibilities
----------------
• Display a list of existing sections loaded from database/sections/.
• "Create New Section" → open a form to enter a section name and build a
  student table (Roll Number | Name).
• "Register Faces" (per student row) → open webcam, capture 30 photos,
  save them to  database/sections/<Section>/<Roll>_<Name>/img1.jpg …
• "Save Section" → write students.xlsx into the section folder.
• "Train Model" → call FaceRecognizer.train() + save_model() for the section.
• "Open Attendance" → navigate to Screen 2 (main_page).
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import cv2

# Import our backend modules (from the parent package)
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from face_recognizer import FaceRecognizer

# ─────────────────────────────────────────────────────────────────────────────
# Theme constants – shared with all pages
# ─────────────────────────────────────────────────────────────────────────────
BG          = "#0f1117"   # very dark background
PANEL       = "#1a1d27"   # card / panel background
ACCENT      = "#4f8ef7"   # primary blue accent
ACCENT2     = "#7c3aed"   # purple secondary accent
SUCCESS     = "#22c55e"   # green
WARNING     = "#f59e0b"   # amber
DANGER      = "#ef4444"   # red
TEXT        = "#e2e8f0"   # light text
SUBTEXT     = "#94a3b8"   # muted text
BORDER      = "#2d3148"   # subtle border
FONT_TITLE  = ("Segoe UI", 20, "bold")
FONT_HEAD   = ("Segoe UI", 13, "bold")
FONT_BODY   = ("Segoe UI", 11)
FONT_SMALL  = ("Segoe UI", 9)
FONT_BTN    = ("Segoe UI", 10, "bold")

DB_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        "database", "sections")


# ─────────────────────────────────────────────────────────────────────────────
class SectionPage(tk.Frame):
    """
    Screen 1 – Section Manager.

    This frame is embedded inside the main App window.  The App swaps between
    frames using grid_forget / grid.
    """

    def __init__(self, parent, app):
        """
        Parameters
        ----------
        parent : tk.Widget  The container widget (App's root window or frame).
        app    : App        Reference to the main application controller.
        """
        super().__init__(parent, bg=BG)
        self.app = app
        self._build_ui()
        self.refresh_section_list()

    # ─────────────────────────────────────────────────────────────────────────
    # UI Construction
    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        """Build the top-level layout: sidebar + main content area."""
        # ── Top title bar ────────────────────────────────────────────────────
        title_bar = tk.Frame(self, bg=PANEL, height=60)
        title_bar.pack(fill="x", side="top")
        tk.Label(
            title_bar, text="📋  Section Manager",
            bg=PANEL, fg=TEXT, font=FONT_TITLE, pady=14
        ).pack(side="left", padx=20)

        # Button to navigate to Attendance (Screen 2)
        tk.Button(
            title_bar, text="→  Take Attendance",
            bg=ACCENT, fg="white", font=FONT_BTN,
            relief="flat", cursor="hand2", padx=12,
            command=self.app.show_main_page,
        ).pack(side="right", padx=16, pady=12)

        # ── Body: left list + right content ──────────────────────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Left sidebar – existing sections
        self._build_sidebar(body)

        # Right panel – section detail / form
        self.right_frame = tk.Frame(body, bg=BG)
        self.right_frame.pack(side="left", fill="both", expand=True, padx=(12, 0))

        self._show_welcome()

    # ─────────────────────────────────────────────────────────────────────────
    def _build_sidebar(self, parent):
        """Left panel showing existing sections and a 'Create' button."""
        sidebar = tk.Frame(parent, bg=PANEL, width=220, bd=0,
                           highlightbackground=BORDER, highlightthickness=1)
        sidebar.pack(side="left", fill="y", padx=(0, 0))
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="Sections", bg=PANEL, fg=SUBTEXT,
                 font=FONT_SMALL).pack(anchor="w", padx=12, pady=(12, 4))

        # Scrollable listbox
        list_frame = tk.Frame(sidebar, bg=PANEL)
        list_frame.pack(fill="both", expand=True, padx=8)

        scrollbar = tk.Scrollbar(list_frame, bg=PANEL, troughcolor=BG)
        scrollbar.pack(side="right", fill="y")

        self.section_listbox = tk.Listbox(
            list_frame, bg=PANEL, fg=TEXT, font=FONT_BODY,
            selectbackground=ACCENT, selectforeground="white",
            relief="flat", bd=0, highlightthickness=0,
            yscrollcommand=scrollbar.set, activestyle="none",
            cursor="hand2",
        )
        self.section_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.section_listbox.yview)
        self.section_listbox.bind("<<ListboxSelect>>", self._on_section_select)

        # Create new section button
        tk.Button(
            sidebar, text="＋  Create New Section",
            bg=ACCENT2, fg="white", font=FONT_BTN,
            relief="flat", cursor="hand2", pady=8,
            command=self._open_create_form,
        ).pack(fill="x", padx=8, pady=8)

    # ─────────────────────────────────────────────────────────────────────────
    def _show_welcome(self):
        """Show a placeholder when no section is selected."""
        for w in self.right_frame.winfo_children():
            w.destroy()

        tk.Label(
            self.right_frame,
            text="Select a section from the list\nor create a new one.",
            bg=BG, fg=SUBTEXT, font=("Segoe UI", 14), justify="center"
        ).pack(expand=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Section list helpers
    # ─────────────────────────────────────────────────────────────────────────
    def refresh_section_list(self):
        """Reload section folders from disk and repopulate the listbox."""
        self.section_listbox.delete(0, tk.END)
        os.makedirs(DB_ROOT, exist_ok=True)

        sections = sorted([
            d for d in os.listdir(DB_ROOT)
            if os.path.isdir(os.path.join(DB_ROOT, d))
        ])
        for s in sections:
            self.section_listbox.insert(tk.END, f"  {s}")

    def _on_section_select(self, event):
        """Show the detail view for the selected section."""
        sel = self.section_listbox.curselection()
        if not sel:
            return
        name = self.section_listbox.get(sel[0]).strip()
        self._show_section_detail(name)

    # ─────────────────────────────────────────────────────────────────────────
    # Section Detail View (existing section)
    # ─────────────────────────────────────────────────────────────────────────
    def _show_section_detail(self, section_name: str):
        """Display information and actions for an existing section."""
        for w in self.right_frame.winfo_children():
            w.destroy()

        section_path = os.path.join(DB_ROOT, section_name)

        # Title
        hdr = tk.Frame(self.right_frame, bg=BG)
        hdr.pack(fill="x", pady=(0, 12))
        tk.Label(hdr, text=f"Section: {section_name}",
                 bg=BG, fg=TEXT, font=FONT_HEAD).pack(side="left")

        # Action buttons row
        btn_row = tk.Frame(self.right_frame, bg=BG)
        btn_row.pack(fill="x", pady=(0, 16))

        tk.Button(
            btn_row, text="🧠  Train Model",
            bg=SUCCESS, fg="white", font=FONT_BTN,
            relief="flat", cursor="hand2", padx=14, pady=6,
            command=lambda: self._train_model(section_name, section_path),
        ).pack(side="left", padx=(0, 10))

        # Model status indicator
        model_path = os.path.join(section_path, "model.yml")
        model_status = "✅ Model trained" if os.path.exists(model_path) else "⚠️  Not trained yet"
        model_color  = SUCCESS if os.path.exists(model_path) else WARNING
        tk.Label(
            btn_row, text=model_status,
            bg=BG, fg=model_color, font=FONT_SMALL
        ).pack(side="left")

        # Student table
        self._build_student_table(section_path, section_name, readonly=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Create New Section Form
    # ─────────────────────────────────────────────────────────────────────────
    def _open_create_form(self):
        """Show the 'Create New Section' form in the right panel."""
        for w in self.right_frame.winfo_children():
            w.destroy()

        # ── Section name field ────────────────────────────────────────────────
        form_top = tk.Frame(self.right_frame, bg=BG)
        form_top.pack(fill="x", pady=(0, 12))

        tk.Label(form_top, text="Section Name:", bg=BG, fg=TEXT,
                 font=FONT_BODY).grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.section_name_var = tk.StringVar()
        name_entry = tk.Entry(
            form_top, textvariable=self.section_name_var,
            bg=PANEL, fg=TEXT, insertbackground=TEXT,
            font=FONT_BODY, relief="flat",
            highlightbackground=BORDER, highlightthickness=1, width=22,
        )
        name_entry.grid(row=0, column=1, sticky="w")
        name_entry.focus()

        # ── Student table ─────────────────────────────────────────────────────
        self.student_rows = []  # list of (roll_var, name_var)
        self.table_frame  = tk.Frame(self.right_frame, bg=BG)
        self.table_frame.pack(fill="both", expand=True)

        self._build_editable_table()

        # ── Bottom action buttons ──────────────────────────────────────────────
        btn_row = tk.Frame(self.right_frame, bg=BG)
        btn_row.pack(fill="x", pady=10)

        tk.Button(
            btn_row, text="＋  Add Row",
            bg=PANEL, fg=TEXT, font=FONT_BTN,
            relief="flat", cursor="hand2", padx=10, pady=6,
            highlightbackground=BORDER, highlightthickness=1,
            command=self._add_student_row,
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            btn_row, text="💾  Save Section",
            bg=ACCENT, fg="white", font=FONT_BTN,
            relief="flat", cursor="hand2", padx=14, pady=6,
            command=self._save_section,
        ).pack(side="left")

    # ─────────────────────────────────────────────────────────────────────────
    def _build_editable_table(self):
        """Render the column headers for the editable student table."""
        hdr = tk.Frame(self.table_frame, bg=PANEL)
        hdr.pack(fill="x", pady=(0, 4))
        for col, w in [("Roll Number", 14), ("Name", 22), ("Action", 14)]:
            tk.Label(hdr, text=col, bg=PANEL, fg=SUBTEXT,
                     font=FONT_SMALL, width=w, anchor="w").pack(side="left", padx=4)

        # Container for data rows
        self.rows_container = tk.Frame(self.table_frame, bg=BG)
        self.rows_container.pack(fill="both", expand=True)

        # Start with 3 blank rows
        for _ in range(3):
            self._add_student_row()

    # ─────────────────────────────────────────────────────────────────────────
    def _add_student_row(self):
        """Append one blank student row (Roll Number | Name | Register button)."""
        row_idx = len(self.student_rows)
        roll_var = tk.StringVar()
        name_var = tk.StringVar()
        self.student_rows.append((roll_var, name_var))

        row_frame = tk.Frame(self.rows_container, bg=BG)
        row_frame.pack(fill="x", pady=2)

        entry_style = dict(
            bg=PANEL, fg=TEXT, insertbackground=TEXT,
            font=FONT_BODY, relief="flat",
            highlightbackground=BORDER, highlightthickness=1,
        )

        tk.Entry(row_frame, textvariable=roll_var, width=14,
                 **entry_style).pack(side="left", padx=4)
        tk.Entry(row_frame, textvariable=name_var, width=22,
                 **entry_style).pack(side="left", padx=4)

        tk.Button(
            row_frame, text="📸 Register",
            bg=WARNING, fg="white", font=FONT_SMALL,
            relief="flat", cursor="hand2", padx=8,
            command=lambda idx=row_idx: self._register_faces(idx),
        ).pack(side="left", padx=4)

    # ─────────────────────────────────────────────────────────────────────────
    def _register_faces(self, row_idx: int):
        """
        Capture 30 face photos for the student in row_idx using the webcam.

        Saves images to:
          database/sections/<SectionName>/<Roll>_<Name>/img1.jpg …
        """
        section_name = self.section_name_var.get().strip()
        if not section_name:
            messagebox.showwarning("Missing", "Enter a Section Name first.")
            return

        roll_var, name_var = self.student_rows[row_idx]
        roll = roll_var.get().strip()
        name = name_var.get().strip()

        if not roll or not name:
            messagebox.showwarning(
                "Missing", "Enter Roll Number and Name before registering faces."
            )
            return

        # Build save path
        safe_name   = name.replace(" ", "_")
        student_dir = os.path.join(DB_ROOT, section_name,
                                   f"{roll}_{safe_name}")
        os.makedirs(student_dir, exist_ok=True)

        # Run capture in a background thread so the GUI stays responsive
        threading.Thread(
            target=self._capture_faces,
            args=(student_dir, roll, name),
            daemon=True,
        ).start()

    # ─────────────────────────────────────────────────────────────────────────
    def _capture_faces(self, save_dir: str, roll: str, name: str):
        """
        Webcam capture loop: detect and save 30 face images.

        Runs in a daemon thread.  Opens an OpenCV window, shows live feed
        with a countdown, closes when 30 faces are captured or user presses Q.
        """
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Camera Error", "Cannot open webcam.")
            return

        cascade_path = os.path.join(
            cv2.data.haarcascades, "haarcascade_frontalface_default.xml"
        )
        face_cascade = cv2.CascadeClassifier(cascade_path)

        count  = 0
        target = 30

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
            )

            for (x, y, w, h) in faces:
                if count < target:
                    count += 1
                    face_roi = gray[y: y + h, x: x + w]
                    face_roi = cv2.resize(face_roi, (100, 100))
                    img_path = os.path.join(save_dir, f"img{count}.jpg")
                    cv2.imwrite(img_path, face_roi)

                # Draw box
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 220, 80), 2)

            # Overlay progress text
            cv2.putText(
                frame,
                f"Capturing {roll} – {name}: {count}/{target}  (Q to abort)",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                (0, 220, 80) if count < target else (0, 180, 255), 2, cv2.LINE_AA,
            )

            cv2.imshow("Face Registration – press Q to abort", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == ord("Q") or count >= target:
                break

        cap.release()
        cv2.destroyAllWindows()

        # Notify user on the main thread
        msg = (f"✅ Captured {count} images for {roll} – {name}."
               if count == target
               else f"⚠️  Only {count}/{target} images captured.")
        self.after(0, lambda: messagebox.showinfo("Face Registration", msg))

    # ─────────────────────────────────────────────────────────────────────────
    def _save_section(self):
        """
        Validate inputs, create the section folder, and save students.xlsx.
        """
        import pandas as pd

        section_name = self.section_name_var.get().strip()
        if not section_name:
            messagebox.showwarning("Missing", "Please enter a Section Name.")
            return

        # Collect valid rows
        records = []
        for roll_var, name_var in self.student_rows:
            roll = roll_var.get().strip()
            name = name_var.get().strip()
            if roll and name:
                records.append({"Roll Number": roll, "Name": name})

        if not records:
            messagebox.showwarning(
                "Empty", "Add at least one student before saving."
            )
            return

        section_path = os.path.join(DB_ROOT, section_name)
        os.makedirs(section_path, exist_ok=True)

        df = pd.DataFrame(records)
        out_path = os.path.join(section_path, "students.xlsx")
        df.to_excel(out_path, index=False, engine="openpyxl")

        self.refresh_section_list()
        messagebox.showinfo(
            "Saved",
            f"Section '{section_name}' saved with {len(records)} student(s).\n"
            f"File: {out_path}",
        )

    # ─────────────────────────────────────────────────────────────────────────
    def _train_model(self, section_name: str, section_path: str):
        """
        Train the LBPH model on all registered faces in the section folder.
        Shows a progress dialog while training runs in a background thread.
        """
        # Progress popup
        popup = tk.Toplevel(self)
        popup.title("Training…")
        popup.configure(bg=BG)
        popup.geometry("340x120")
        popup.resizable(False, False)
        tk.Label(
            popup,
            text=f"Training LBPH model for '{section_name}'…\nPlease wait.",
            bg=BG, fg=TEXT, font=FONT_BODY, pady=20
        ).pack()
        progress = ttk.Progressbar(popup, mode="indeterminate", length=280)
        progress.pack(pady=4)
        progress.start(12)

        def do_train():
            try:
                recognizer = FaceRecognizer()
                n = recognizer.train(section_path)
                recognizer.save_model(section_path)
                self.after(0, lambda: _done(n, None))
            except Exception as exc:
                self.after(0, lambda: _done(0, str(exc)))

        def _done(n_students, error):
            progress.stop()
            popup.destroy()
            if error:
                messagebox.showerror("Training Failed", error)
            else:
                messagebox.showinfo(
                    "Training Complete",
                    f"✅ Model trained on {n_students} student(s).\n"
                    f"Saved to: {section_path}",
                )
                # Refresh to update the model status label
                self._show_section_detail(section_name)

        threading.Thread(target=do_train, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    def _build_student_table(self, section_path: str,
                              section_name: str, readonly=True):
        """
        Show the student list for an existing section in a read-only Treeview.
        Also shows a 'Register Faces' button per row.
        """
        import pandas as pd

        student_file = os.path.join(section_path, "students.xlsx")
        if not os.path.exists(student_file):
            tk.Label(self.right_frame,
                     text="No students.xlsx found in this section.",
                     bg=BG, fg=SUBTEXT, font=FONT_BODY).pack(pady=8)
            return

        df = pd.read_excel(student_file, dtype=str)

        # ── Treeview ──────────────────────────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Custom.Treeview",
            background=PANEL, foreground=TEXT,
            fieldbackground=PANEL, rowheight=28,
            font=FONT_BODY,
        )
        style.configure(
            "Custom.Treeview.Heading",
            background=BG, foreground=SUBTEXT, font=FONT_SMALL,
        )
        style.map("Custom.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "white")])

        tree_frame = tk.Frame(self.right_frame, bg=BG)
        tree_frame.pack(fill="both", expand=True, pady=8)

        tree = ttk.Treeview(
            tree_frame,
            columns=("Roll Number", "Name", "Registered"),
            show="headings", style="Custom.Treeview",
        )
        for col, w in [("Roll Number", 130), ("Name", 200), ("Registered", 100)]:
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="w")

        for _, row in df.iterrows():
            roll      = str(row.get("Roll Number", "")).strip()
            name      = str(row.get("Name", "")).strip()
            safe_name = name.replace(" ", "_")
            face_dir  = os.path.join(section_path, f"{roll}_{safe_name}")
            registered = "✅ Yes" if os.path.isdir(face_dir) and len(
                [f for f in os.listdir(face_dir) if f.endswith(".jpg")]
            ) > 0 else "❌ No"
            tree.insert("", tk.END, values=(roll, name, registered))

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
