"""
gui/main_page.py
================
SCREEN 2 – Main / Attendance Page

Responsibilities
----------------
• Dropdown: choose an existing section (loaded from database/sections/).
• Date picker: choose the session date (defaults to today).
• Input mode radio buttons: Image | Video | Webcam.
• File browse button (Image / Video mode only).
• "Take Attendance" button:
    1. Load the LBPH model for the selected section.
    2. Open the source (image / video / webcam).
    3. For each frame:
         a. preprocess.preprocess_frame()   – grayscale → blur → equalization
         b. face_detect.FaceDetector        – Haar Cascade bounding boxes
         c. face_recognizer.FaceRecognizer  – LBPH identity prediction
    4. Draw named bounding boxes on the live feed.
    5. Mark recognized students Present.
    6. On exit → navigate to Screen 3 (result_page) with the data.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import date as dt_date
import cv2

# Ensure parent directory is in the path for module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from preprocess      import preprocess_frame
from face_detect     import FaceDetector
from face_recognizer import FaceRecognizer
from attendance      import AttendanceManager

# ── Theme constants (same palette as section_page) ────────────────────────────
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

DB_ROOT     = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "database", "sections")
OUTPUT_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")


# ─────────────────────────────────────────────────────────────────────────────
class MainPage(tk.Frame):
    """
    Screen 2 – attendance configuration and live processing.

    Communicates results back to the App controller via
    app.show_result_page(attendance_manager).
    """

    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self._build_ui()

    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        """Build the page layout."""
        # ── Title bar ────────────────────────────────────────────────────────
        title_bar = tk.Frame(self, bg=PANEL, height=60)
        title_bar.pack(fill="x")

        tk.Button(
            title_bar, text="←  Sections",
            bg=PANEL, fg=SUBTEXT, font=FONT_BTN,
            relief="flat", cursor="hand2", padx=12,
            command=self.app.show_section_page,
        ).pack(side="left", padx=16, pady=12)

        tk.Label(
            title_bar, text="📷  Take Attendance",
            bg=PANEL, fg=TEXT, font=FONT_TITLE, pady=14,
        ).pack(side="left", padx=8)

        # ── Config card ──────────────────────────────────────────────────────
        card = tk.Frame(self, bg=PANEL, bd=0,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=24, pady=20)

        inner = tk.Frame(card, bg=PANEL)
        inner.pack(padx=20, pady=16, fill="x")

        # Row 0: Section dropdown
        self._row_label(inner, 0, "Section")
        self.section_var = tk.StringVar(value="-- select --")
        self.section_cb  = ttk.Combobox(
            inner, textvariable=self.section_var,
            state="readonly", width=26, font=FONT_BODY,
        )
        self.section_cb.grid(row=0, column=1, sticky="w", pady=6, padx=(0, 20))
        self._populate_sections()

        # Row 1: Date entry
        self._row_label(inner, 1, "Date")
        self.date_var = tk.StringVar(value=dt_date.today().strftime("%Y-%m-%d"))
        tk.Entry(
            inner, textvariable=self.date_var,
            bg=BG, fg=TEXT, insertbackground=TEXT,
            font=FONT_BODY, relief="flat",
            highlightbackground=BORDER, highlightthickness=1, width=16,
        ).grid(row=1, column=1, sticky="w", pady=6, padx=(0, 20))

        # Row 2: Input type radio buttons
        self._row_label(inner, 2, "Input Type")
        self.input_mode = tk.StringVar(value="Webcam")
        mode_frame = tk.Frame(inner, bg=PANEL)
        mode_frame.grid(row=2, column=1, sticky="w", pady=6)
        for mode in ("Image", "Video", "Webcam"):
            tk.Radiobutton(
                mode_frame, text=mode, variable=self.input_mode, value=mode,
                bg=PANEL, fg=TEXT, selectcolor=BG,
                activebackground=PANEL, activeforeground=TEXT,
                font=FONT_BODY, cursor="hand2",
                command=self._on_mode_change,
            ).pack(side="left", padx=(0, 16))

        # Row 3: File browse (hidden initially)
        self._row_label(inner, 3, "File Path")
        self.file_path_var = tk.StringVar()
        self.file_frame    = tk.Frame(inner, bg=PANEL)
        self.file_frame.grid(row=3, column=1, sticky="w", pady=6)

        self.file_entry = tk.Entry(
            self.file_frame, textvariable=self.file_path_var,
            bg=BG, fg=TEXT, insertbackground=TEXT,
            font=FONT_BODY, relief="flat",
            highlightbackground=BORDER, highlightthickness=1, width=30,
        )
        self.file_entry.pack(side="left", padx=(0, 8))
        tk.Button(
            self.file_frame, text="Browse…",
            bg=ACCENT2, fg="white", font=FONT_SMALL,
            relief="flat", cursor="hand2", padx=8,
            command=self._browse_file,
        ).pack(side="left")
        self.file_frame.grid_remove()   # hidden when mode=Webcam

        # ── Status label ──────────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(
            self, textvariable=self.status_var,
            bg=BG, fg=SUBTEXT, font=FONT_SMALL,
        ).pack(pady=(0, 8))

        # ── Take Attendance button ─────────────────────────────────────────────
        tk.Button(
            self, text="▶   Take Attendance",
            bg=ACCENT, fg="white", font=("Segoe UI", 13, "bold"),
            relief="flat", cursor="hand2", padx=24, pady=10,
            command=self._start_attendance,
        ).pack(pady=(0, 20))

    # ─────────────────────────────────────────────────────────────────────────
    # Helper builders
    # ─────────────────────────────────────────────────────────────────────────
    def _row_label(self, parent, row, text):
        """Add a right-aligned label in column 0 of the grid."""
        tk.Label(
            parent, text=text + ":",
            bg=PANEL, fg=SUBTEXT, font=FONT_SMALL, anchor="e", width=10,
        ).grid(row=row, column=0, sticky="e", padx=(0, 12), pady=6)

    def _populate_sections(self):
        """Fill the section dropdown from the database/sections/ folder."""
        os.makedirs(DB_ROOT, exist_ok=True)
        sections = sorted([
            d for d in os.listdir(DB_ROOT)
            if os.path.isdir(os.path.join(DB_ROOT, d))
        ])
        self.section_cb["values"] = sections
        if sections:
            self.section_var.set(sections[0])

    def on_show(self):
        """Called by App when this page becomes visible; refresh dropdown."""
        self._populate_sections()

    # ─────────────────────────────────────────────────────────────────────────
    def _on_mode_change(self):
        """Show/hide the file browse row based on selected input mode."""
        if self.input_mode.get() in ("Image", "Video"):
            self.file_frame.grid()
        else:
            self.file_frame.grid_remove()

    def _browse_file(self):
        """Open a file dialog to pick an image or video file."""
        mode = self.input_mode.get()
        if mode == "Image":
            ftype = [("Image files", "*.jpg *.jpeg *.png *.bmp"), ("All", "*.*")]
        else:
            ftype = [("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All", "*.*")]

        path = filedialog.askopenfilename(filetypes=ftype)
        if path:
            self.file_path_var.set(path)

    # ─────────────────────────────────────────────────────────────────────────
    # Attendance pipeline
    # ─────────────────────────────────────────────────────────────────────────
    def _start_attendance(self):
        """Validate inputs and kick off the processing thread."""
        section = self.section_var.get().strip()
        if not section or section == "-- select --":
            messagebox.showwarning("Missing", "Please select a section.")
            return

        session_date = self.date_var.get().strip()
        if not session_date:
            messagebox.showwarning("Missing", "Please enter a date.")
            return

        mode = self.input_mode.get()
        source = None
        if mode in ("Image", "Video"):
            source = self.file_path_var.get().strip()
            if not source:
                messagebox.showwarning("Missing", "Please select a file.")
                return
            if not os.path.exists(source):
                messagebox.showerror("Not Found", f"File not found:\n{source}")
                return

        section_path = os.path.join(DB_ROOT, section)
        model_path   = os.path.join(section_path, "model.yml")
        if not os.path.exists(model_path):
            messagebox.showerror(
                "No Model",
                f"No trained model found for '{section}'.\n"
                "Go to Section Manager and train the model first.",
            )
            return

        self.status_var.set("Loading model…")
        self.update_idletasks()

        threading.Thread(
            target=self._run_pipeline,
            args=(section, section_path, session_date, mode, source),
            daemon=True,
        ).start()

    # ─────────────────────────────────────────────────────────────────────────
    def _run_pipeline(self, section: str, section_path: str,
                      session_date: str, mode: str, source):
        """
        Background thread: loads model, processes input, marks attendance.

        After processing completes, navigates to the result page on the
        main thread via self.after().
        """
        try:
            # ── Step 1: Load LBPH model ───────────────────────────────────────
            recognizer = FaceRecognizer()
            recognizer.load_model(section_path)
            self.after(0, lambda: self.status_var.set("Model loaded. Processing…"))

            # ── Step 2: Initialise detector and attendance manager ─────────────
            detector = FaceDetector(scale_factor=1.1, min_neighbors=5,
                                     min_size=(60, 60))
            mgr = AttendanceManager(
                section_name=section,
                section_path=section_path,
                session_date=session_date,
            )

            # ── Step 3: Route to correct processing mode ──────────────────────
            if mode == "Image":
                self._process_image(source, detector, recognizer, mgr)
            elif mode == "Video":
                self._process_video(source, detector, recognizer, mgr)
            else:   # Webcam
                self._process_video(0, detector, recognizer, mgr)

            # ── Step 4: Navigate to results on main thread ────────────────────
            self.after(0, lambda: self.app.show_result_page(mgr))
            self.after(0, lambda: self.status_var.set("Ready."))

        except Exception as exc:
            self.after(0, lambda: self.status_var.set("Error."))
            self.after(0, lambda: messagebox.showerror(
                "Processing Error", str(exc)
            ))

    # ─────────────────────────────────────────────────────────────────────────
    def _process_image(self, image_path: str, detector: FaceDetector,
                        recognizer: FaceRecognizer, mgr: AttendanceManager):
        """
        Process a single still image:
          preprocess → detect → recognize → mark attendance → show result.
        """
        frame = cv2.imread(image_path)
        if frame is None:
            raise ValueError(f"Cannot read image: {image_path}")

        preprocessed = preprocess_frame(frame)
        faces        = detector.detect_faces(preprocessed)

        labels = []
        for (x, y, w, h) in faces:
            face_roi = preprocessed[y: y + h, x: x + w]
            roll, name, conf = recognizer.predict(face_roi)
            if roll != "Unknown":
                mgr.mark_present(roll)
                labels.append(f"{roll} ({name})")
            else:
                labels.append(f"Unknown ({conf:.0f})")

        annotated = detector.draw_boxes(frame, faces, labels)

        # Add summary overlay
        summary = mgr.get_summary()
        cv2.putText(
            annotated,
            f"Present: {summary['present']}  Absent: {summary['absent']}  "
            f"Total: {summary['total']}",
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.70,
            (0, 220, 80), 2, cv2.LINE_AA,
        )

        cv2.imshow("Attendance Result – press any key to continue", annotated)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # ─────────────────────────────────────────────────────────────────────────
    def _process_video(self, source, detector: FaceDetector,
                        recognizer: FaceRecognizer, mgr: AttendanceManager):
        """
        Process a video file or webcam stream frame-by-frame.

        Runs until the video ends or the user presses Q.
        Faces recognized with confidence ≤ threshold are marked Present.
        """
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video source: {source}")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            preprocessed = preprocess_frame(frame)
            faces        = detector.detect_faces(preprocessed)

            labels = []
            for (x, y, w, h) in faces:
                face_roi = preprocessed[y: y + h, x: x + w]
                roll, name, conf = recognizer.predict(face_roi)
                if roll != "Unknown":
                    mgr.mark_present(roll)
                    labels.append(f"{name} ({conf:.0f})")
                else:
                    labels.append(f"Unknown")

            annotated = detector.draw_boxes(frame, faces, labels)

            # Info panel
            summary = mgr.get_summary()
            cv2.putText(
                annotated,
                f"Present: {summary['present']}  Absent: {summary['absent']}  "
                f"Total: {summary['total']}   |   Press Q to stop",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.60,
                (0, 220, 80), 2, cv2.LINE_AA,
            )

            cv2.imshow("Real-Time Attendance (press Q to stop)", annotated)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q")):
                break

        cap.release()
        cv2.destroyAllWindows()
