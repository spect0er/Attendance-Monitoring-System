"""
gui/result_page.py
==================
SCREEN 3 – Attendance Result Page

Responsibilities
----------------
• Receive an AttendanceManager instance (already populated with Present/Absent).
• Display the full attendance table: Roll Number | Name | Status | Date.
• Show a summary banner: Total Present / Total Absent / Total Students.
• "Save to Excel" button → calls mgr.save_to_excel() and shows the saved path.
• "Back to Main"  button → navigate back to Screen 2.
• "New Session"   button → navigate back to Screen 1.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from attendance import AttendanceManager

# ── Theme constants ───────────────────────────────────────────────────────────
BG         = "#0f1117"
PANEL      = "#1a1d27"
ACCENT     = "#4f8ef7"
ACCENT2    = "#7c3aed"
SUCCESS    = "#22c55e"
WARNING    = "#f59e0b"
DANGER     = "#ef4444"
TEXT       = "#e2e8f0"
SUBTEXT    = "#94a3b8"
BORDER     = "#2d3148"
FONT_TITLE = ("Segoe UI", 20, "bold")
FONT_HEAD  = ("Segoe UI", 13, "bold")
FONT_BODY  = ("Segoe UI", 11)
FONT_SMALL = ("Segoe UI", 9)
FONT_BTN   = ("Segoe UI", 10, "bold")

OUTPUT_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")


# ─────────────────────────────────────────────────────────────────────────────
class ResultPage(tk.Frame):
    """
    Screen 3 – Attendance Result.

    Created fresh each time the App navigates here so it always reflects
    the latest session data.
    """

    def __init__(self, parent, app, mgr: AttendanceManager):
        """
        Parameters
        ----------
        parent : tk.Widget       Container widget.
        app    : App             Main application controller.
        mgr    : AttendanceManager  Populated with this session's data.
        """
        super().__init__(parent, bg=BG)
        self.app = app
        self.mgr = mgr
        self._build_ui()

    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        """Construct the full page layout."""
        # ── Title bar ────────────────────────────────────────────────────────
        title_bar = tk.Frame(self, bg=PANEL, height=60)
        title_bar.pack(fill="x")

        tk.Label(
            title_bar, text="✅  Attendance Results",
            bg=PANEL, fg=TEXT, font=FONT_TITLE, pady=14,
        ).pack(side="left", padx=20)

        # Navigation buttons (top-right)
        nav_frame = tk.Frame(title_bar, bg=PANEL)
        nav_frame.pack(side="right", padx=16, pady=10)

        tk.Button(
            nav_frame, text="←  Back to Main",
            bg=PANEL, fg=SUBTEXT, font=FONT_BTN,
            relief="flat", cursor="hand2", padx=12,
            command=self.app.show_main_page,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            nav_frame, text="🔄  New Session",
            bg=ACCENT2, fg="white", font=FONT_BTN,
            relief="flat", cursor="hand2", padx=12,
            command=self.app.show_section_page,
        ).pack(side="left")

        # ── Summary banner ────────────────────────────────────────────────────
        summary = self.mgr.get_summary()
        self._build_summary_banner(summary)

        # ── Data table ────────────────────────────────────────────────────────
        self._build_table()

        # ── Save button ──────────────────────────────────────────────────────
        tk.Button(
            self, text="💾  Save to Excel",
            bg=SUCCESS, fg="white", font=("Segoe UI", 11, "bold"),
            relief="flat", cursor="hand2", padx=20, pady=8,
            command=self._save_excel,
        ).pack(pady=16)

        # Save-path status label
        self.save_status_var = tk.StringVar()
        tk.Label(
            self, textvariable=self.save_status_var,
            bg=BG, fg=SUCCESS, font=FONT_SMALL, wraplength=600,
        ).pack()

    # ─────────────────────────────────────────────────────────────────────────
    def _build_summary_banner(self, summary: dict):
        """
        Show a row of stat cards: Present | Absent | Total.

        Colour codes: green = present, red = absent, blue = total.
        """
        banner = tk.Frame(self, bg=BG)
        banner.pack(fill="x", padx=24, pady=(16, 8))

        cards = [
            ("Total Present",  summary["present"], SUCCESS),
            ("Total Absent",   summary["absent"],  DANGER),
            ("Total Students", summary["total"],   ACCENT),
        ]

        for title, value, color in cards:
            card = tk.Frame(
                banner, bg=PANEL, bd=0,
                highlightbackground=color, highlightthickness=2,
            )
            card.pack(side="left", expand=True, fill="x", padx=8, ipady=12)

            tk.Label(card, text=str(value), bg=PANEL, fg=color,
                     font=("Segoe UI", 28, "bold")).pack()
            tk.Label(card, text=title, bg=PANEL, fg=SUBTEXT,
                     font=FONT_SMALL).pack()

        # Section + date info below the cards
        info_frame = tk.Frame(self, bg=BG)
        info_frame.pack(fill="x", padx=24, pady=(4, 0))
        tk.Label(
            info_frame,
            text=f"Section: {self.mgr.section_name}   |   "
                 f"Date: {self.mgr.session_date}",
            bg=BG, fg=SUBTEXT, font=FONT_SMALL,
        ).pack(anchor="w")

    # ─────────────────────────────────────────────────────────────────────────
    def _build_table(self):
        """
        Build a styled Treeview showing Roll Number | Name | Status | Date.

        Rows for Present students are highlighted green; Absent rows are red.
        """
        # Configure ttk style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Res.Treeview",
            background=PANEL, foreground=TEXT,
            fieldbackground=PANEL, rowheight=30,
            font=FONT_BODY,
        )
        style.configure(
            "Res.Treeview.Heading",
            background=BG, foreground=SUBTEXT,
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Res.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "white")])

        # Container with scrollbar
        table_frame = tk.Frame(self, bg=BG)
        table_frame.pack(fill="both", expand=True, padx=24, pady=8)

        tree = ttk.Treeview(
            table_frame,
            columns=("Roll Number", "Name", "Status", "Date"),
            show="headings",
            style="Res.Treeview",
        )

        # Column definitions
        col_widths = {
            "Roll Number": 130,
            "Name":        220,
            "Status":       110,
            "Date":        120,
        }
        for col, w in col_widths.items():
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="w")

        # Tag colours: green for Present, red for Absent
        tree.tag_configure("present", foreground=SUCCESS)
        tree.tag_configure("absent",  foreground=DANGER)

        # Insert rows from the attendance DataFrame
        df = self.mgr.get_dataframe()
        for _, row in df.iterrows():
            status = row["Status"]
            tag    = "present" if status == "Present" else "absent"
            tree.insert("", tk.END,
                        values=(row["Roll Number"], row["Name"],
                                status, row["Date"]),
                        tags=(tag,))

        # Scrollbar
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)

    # ─────────────────────────────────────────────────────────────────────────
    def _save_excel(self):
        """
        Save the attendance DataFrame to:
          outputs/<SectionName>/attendance_<date>.xlsx

        Shows the saved path in the status label.
        """
        try:
            saved_path = self.mgr.save_to_excel(output_base_dir=OUTPUT_ROOT)
            self.save_status_var.set(f"✅ Saved: {saved_path}")
        except Exception as exc:
            messagebox.showerror("Save Error", str(exc))
