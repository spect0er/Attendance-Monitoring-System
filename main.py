"""
main.py
=======
Real-Time Attendance Monitoring System — GUI Entry Point
=========================================================

Run this file to launch the application:
    python main.py

Technology Stack
----------------
  GUI       : tkinter (built into Python — no install needed)
  Detection : OpenCV Haar Cascade (haarcascade_frontalface_default.xml)
  Recognition: LBPH Face Recognizer (opencv-contrib-python)
  Data       : pandas + openpyxl for Excel read / write
  No deep learning — purely classical Computer Vision.

Project Layout
--------------
  main.py             ← YOU ARE HERE  (App controller + entry point)
  preprocess.py       ← grayscale, blur, histogram equalization
  face_detect.py      ← Haar Cascade detection
  face_recognizer.py  ← LBPH train, predict, save, load
  attendance.py       ← roster management, Excel export
  gui/
    section_page.py   ← Screen 1 – Section Manager
    main_page.py      ← Screen 2 – Take Attendance
    result_page.py    ← Screen 3 – Results
  database/sections/  ← auto-created; holds face images + trained models
  outputs/            ← attendance Excel files are saved here
"""

import os
import sys
import tkinter as tk
from tkinter import font as tk_font

# ── Ensure the project root is on sys.path so all imports resolve cleanly ──
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from gui.section_page import SectionPage
from gui.main_page    import MainPage
from gui.result_page  import ResultPage


# ─────────────────────────────────────────────────────────────────────────────
# App – main controller
# ─────────────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    """
    Root Tk window and page controller.

    Manages three "screens" by packing / unpacking frames:
      Screen 1 – SectionPage   (section creation, face registration, training)
      Screen 2 – MainPage      (attendance configuration + live processing)
      Screen 3 – ResultPage    (attendance table + Excel save)

    Navigation flow
    ---------------
      SectionPage  →  MainPage  →  ResultPage
           ↑______________↑______________|
    """

    # ── Window geometry ───────────────────────────────────────────────────────
    WIN_WIDTH  = 960
    WIN_HEIGHT = 680
    WIN_TITLE  = "🎓  Real-Time Attendance Monitoring System"

    def __init__(self):
        super().__init__()

        # ── Window setup ──────────────────────────────────────────────────────
        self.title(self.WIN_TITLE)
        self.geometry(f"{self.WIN_WIDTH}x{self.WIN_HEIGHT}")
        self.minsize(800, 580)
        self.configure(bg="#0f1117")

        # Centre the window on screen
        self._centre_window()

        # ── Create required directories ───────────────────────────────────────
        os.makedirs(os.path.join(PROJECT_ROOT, "database", "sections"),
                    exist_ok=True)
        os.makedirs(os.path.join(PROJECT_ROOT, "outputs"), exist_ok=True)

        # ── Build screens ─────────────────────────────────────────────────────
        self.section_page = SectionPage(self, self)
        self.main_page    = MainPage(self, self)
        self.result_page  = None   # built fresh each session

        # ── Show starting screen ──────────────────────────────────────────────
        self.current_frame = None
        self.show_section_page()

    # ─────────────────────────────────────────────────────────────────────────
    # Navigation helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _switch(self, new_frame: tk.Frame):
        """Hide the current frame and show the new one."""
        if self.current_frame is not None:
            self.current_frame.pack_forget()
        new_frame.pack(fill="both", expand=True)
        self.current_frame = new_frame

    def show_section_page(self):
        """Navigate to Screen 1 – Section Manager."""
        self.section_page.refresh_section_list()
        self._switch(self.section_page)

    def show_main_page(self):
        """Navigate to Screen 2 – Take Attendance."""
        self.main_page.on_show()
        self._switch(self.main_page)

    def show_result_page(self, mgr):
        """
        Navigate to Screen 3 – Attendance Results.

        Parameters
        ----------
        mgr : AttendanceManager  Populated attendance data for this session.
        """
        # Rebuild result page with fresh data each time
        if self.result_page is not None:
            self.result_page.destroy()

        self.result_page = ResultPage(self, self, mgr)
        self._switch(self.result_page)

    # ─────────────────────────────────────────────────────────────────────────
    def _centre_window(self):
        """Position the window in the middle of the screen."""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - self.WIN_WIDTH)  // 2
        y  = (sh - self.WIN_HEIGHT) // 2
        self.geometry(f"{self.WIN_WIDTH}x{self.WIN_HEIGHT}+{x}+{y}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
