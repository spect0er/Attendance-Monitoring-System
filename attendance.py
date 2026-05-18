"""
attendance.py
=============
Manages the student roster and attendance records for one session.

Responsibilities
----------------
1. Load the student list from students.xlsx in a section folder.
2. Initialise every student as "Absent".
3. Mark a specific student "Present" by roll number (called from recognizer).
4. Provide summary statistics (present / absent counts).
5. Build and return the final attendance DataFrame.
6. Save the DataFrame to  outputs/<SectionName>/attendance_<date>.xlsx.

Excel columns (students.xlsx)
-----------------------------
  Roll Number | Name

Excel columns (attendance_<date>.xlsx)
--------------------------------------
  Roll Number | Name | Status | Date
"""

import os
import pandas as pd
from datetime import date


class AttendanceManager:
    """
    Tracks attendance for a single class session.

    Parameters
    ----------
    section_name : str   Human-readable name, e.g. "CSE-A".
    section_path : str   Full path to the section folder.
    session_date : str   "YYYY-MM-DD".  Defaults to today.
    """

    def __init__(self, section_name: str, section_path: str,
                 session_date: str = None):
        self.section_name = section_name
        self.section_path = section_path
        self.session_date = session_date or date.today().strftime("%Y-%m-%d")

        # Load student list
        student_file = os.path.join(section_path, "students.xlsx")
        if not os.path.exists(student_file):
            raise FileNotFoundError(
                f"students.xlsx not found in: {section_path}\n"
                "Create the section and save the student list first."
            )

        self.students_df = pd.read_excel(student_file, dtype=str)
        self.students_df.columns = self.students_df.columns.str.strip()

        # Normalise column names
        if "Roll Number" not in self.students_df.columns:
            raise ValueError("students.xlsx must have a 'Roll Number' column.")
        if "Name" not in self.students_df.columns:
            raise ValueError("students.xlsx must have a 'Name' column.")

        # attendance dict: {roll_number: "Present" | "Absent"}
        self.attendance: dict = {
            str(row["Roll Number"]).strip(): "Absent"
            for _, row in self.students_df.iterrows()
        }

        print(f"[AttendanceManager] Section '{section_name}' – "
              f"{len(self.attendance)} student(s) loaded.")

    # ─────────────────────────────────────────────────────────────────────────
    def mark_present(self, roll_no: str):
        """
        Mark a student as Present.

        Parameters
        ----------
        roll_no : str  The student's roll number (must match students.xlsx).
        """
        roll_no = str(roll_no).strip()
        if roll_no in self.attendance:
            self.attendance[roll_no] = "Present"

    # ─────────────────────────────────────────────────────────────────────────
    def get_summary(self) -> dict:
        """
        Return attendance counts.

        Returns
        -------
        dict with keys: present, absent, total
        """
        present = sum(1 for s in self.attendance.values() if s == "Present")
        total   = len(self.attendance)
        return {"present": present, "absent": total - present, "total": total}

    # ─────────────────────────────────────────────────────────────────────────
    def get_dataframe(self) -> pd.DataFrame:
        """
        Build and return the full attendance DataFrame.

        Columns: Roll Number | Name | Status | Date
        """
        records = []
        for _, row in self.students_df.iterrows():
            roll = str(row["Roll Number"]).strip()
            records.append({
                "Roll Number": roll,
                "Name":        str(row["Name"]).strip(),
                "Status":      self.attendance.get(roll, "Absent"),
                "Date":        self.session_date,
            })
        return pd.DataFrame(records)

    # ─────────────────────────────────────────────────────────────────────────
    def save_to_excel(self, output_base_dir: str = "outputs") -> str:
        """
        Save attendance to  <output_base_dir>/<SectionName>/attendance_<date>.xlsx

        Parameters
        ----------
        output_base_dir : str  Root outputs folder. Default "outputs".

        Returns
        -------
        str  Full path to the saved file.
        """
        out_dir = os.path.join(output_base_dir, self.section_name)
        os.makedirs(out_dir, exist_ok=True)

        filename = f"attendance_{self.session_date}.xlsx"
        out_path = os.path.join(out_dir, filename)

        df = self.get_dataframe()
        df.to_excel(out_path, index=False, engine="openpyxl")

        print(f"[AttendanceManager] ✅ Saved → {out_path}")
        return out_path
