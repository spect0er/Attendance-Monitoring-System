"""
face_recognizer.py
==================
LBPH (Local Binary Pattern Histogram) Face Recognizer module.

What is LBPH?
  - A classical texture-based algorithm that encodes a face image as a
    histogram of local binary patterns.
  - For each pixel, it compares the pixel's value to its 8 neighbours and
    builds a binary code; these codes across the whole image form a feature
    histogram.
  - Recognition works by comparing the histogram of an unknown face to the
    stored histograms of known faces (nearest-neighbour search).
  - Advantages: fast, works with small training sets, robust to illumination
    changes, built into opencv-contrib-python.

Workflow
--------
  Train  : recognizer.train(section_path)        # reads face images, trains model
  Save   : recognizer.save_model(section_path)   # writes model.yml + label_map.json
  Load   : recognizer.load_model(section_path)   # reads them back
  Predict: recognizer.predict(face_roi_gray)      # returns (roll_no, name, confidence)
"""

import cv2
import json
import os
import numpy as np


class FaceRecognizer:
    """
    Wraps OpenCV's LBPH Face Recognizer with train / save / load / predict API.

    Attributes
    ----------
    recognizer  : cv2.face.LBPHFaceRecognizer  The underlying OpenCV object.
    label_map   : dict   int label → {"roll": str, "name": str}
    trained     : bool   True once train() or load_model() has been called.
    """

    # Confidence threshold – predictions above this value are considered
    # "Unknown" (too low similarity).  Lower = stricter matching.
    CONFIDENCE_THRESHOLD = 85.0

    def __init__(self):
        """Create an untrained LBPH recognizer."""
        # createLBPHFaceRecognizer lives in the 'face' sub-module of
        # opencv-contrib-python (not in the plain opencv-python package).
        self.recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=1, neighbors=8, grid_x=8, grid_y=8
        )
        self.label_map: dict = {}   # {int_label: {"roll": ..., "name": ...}}
        self.trained: bool   = False

    # ─────────────────────────────────────────────────────────────────────────
    def train(self, section_path: str) -> int:
        """
        Train the LBPH recognizer on all face images in a section folder.

        Expected folder structure
        ─────────────────────────
          section_path/
            <RollNo>_<Name>/
              img1.jpg
              img2.jpg
              ...
            <RollNo2>_<Name2>/
              ...

        Each sub-folder name must be  "<RollNo>_<Name>"  (e.g. "CS001_Alice").
        Images inside must be JPEG/PNG face crops.

        Parameters
        ----------
        section_path : str  Path to the section folder (contains student dirs).

        Returns
        -------
        int  Number of unique students (labels) trained.

        Raises
        ------
        ValueError  If no valid face images were found.
        """
        faces_list  = []   # list of grayscale face numpy arrays
        labels_list = []   # list of int labels (one per image)
        label_counter = 0
        self.label_map = {}

        # Iterate over every sub-directory in the section folder
        for entry in sorted(os.listdir(section_path)):
            student_dir = os.path.join(section_path, entry)
            if not os.path.isdir(student_dir):
                continue  # skip files like students.xlsx, model.yml etc.

            # Parse roll number and name from folder name "RollNo_Name"
            parts = entry.split("_", 1)
            if len(parts) < 2:
                print(f"[FaceRecognizer] Skipping folder (bad name): {entry}")
                continue

            roll_no  = parts[0]
            stu_name = parts[1].replace("_", " ")

            # Assign an integer label to this student
            int_label = label_counter
            self.label_map[int_label] = {"roll": roll_no, "name": stu_name}
            label_counter += 1

            # Load every image in the student's folder
            img_count = 0
            for img_file in sorted(os.listdir(student_dir)):
                if not img_file.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue
                img_path = os.path.join(student_dir, img_file)
                img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    continue
                # Resize to a standard size for consistent feature extraction
                img = cv2.resize(img, (100, 100))
                faces_list.append(img)
                labels_list.append(int_label)
                img_count += 1

            print(f"[FaceRecognizer] Loaded {img_count} images "
                  f"for {roll_no} – {stu_name}")

        if len(faces_list) == 0:
            raise ValueError(
                "No face images found in the section folder.\n"
                "Register faces for at least one student before training."
            )

        # Train the LBPH model
        self.recognizer.train(faces_list, np.array(labels_list))
        self.trained = True
        print(f"[FaceRecognizer] ✅ Model trained on {len(faces_list)} images "
              f"across {label_counter} student(s).")
        return label_counter

    # ─────────────────────────────────────────────────────────────────────────
    def save_model(self, section_path: str):
        """
        Save the trained model and label map to disk.

        Saves
        -----
          <section_path>/model.yml       – LBPH model weights
          <section_path>/label_map.json  – int label → roll/name mapping

        Parameters
        ----------
        section_path : str  The section's folder path.
        """
        if not self.trained:
            raise RuntimeError("Model has not been trained yet.  Call train() first.")

        model_path     = os.path.join(section_path, "model.yml")
        label_map_path = os.path.join(section_path, "label_map.json")

        self.recognizer.save(model_path)

        # JSON keys must be strings; convert int keys → str
        json_map = {str(k): v for k, v in self.label_map.items()}
        with open(label_map_path, "w", encoding="utf-8") as f:
            json.dump(json_map, f, indent=2)

        print(f"[FaceRecognizer] Model saved → {model_path}")
        print(f"[FaceRecognizer] Label map saved → {label_map_path}")

    # ─────────────────────────────────────────────────────────────────────────
    def load_model(self, section_path: str):
        """
        Load a previously trained model and its label map from disk.

        Parameters
        ----------
        section_path : str  The section's folder path.

        Raises
        ------
        FileNotFoundError  If model.yml or label_map.json does not exist.
        """
        model_path     = os.path.join(section_path, "model.yml")
        label_map_path = os.path.join(section_path, "label_map.json")

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Trained model not found: {model_path}\n"
                "Train the model first via 'Train Model for this Section'."
            )
        if not os.path.exists(label_map_path):
            raise FileNotFoundError(
                f"Label map not found: {label_map_path}\n"
                "Re-train the model to regenerate the label map."
            )

        self.recognizer.read(model_path)

        with open(label_map_path, "r", encoding="utf-8") as f:
            json_map = json.load(f)
        # Convert string keys back to int
        self.label_map = {int(k): v for k, v in json_map.items()}

        self.trained = True
        print(f"[FaceRecognizer] Model loaded from: {model_path}")
        print(f"[FaceRecognizer] {len(self.label_map)} student(s) in label map.")

    # ─────────────────────────────────────────────────────────────────────────
    def predict(self, face_roi_gray):
        """
        Predict the identity of a detected face region.

        Parameters
        ----------
        face_roi_gray : numpy.ndarray
            Grayscale crop of the detected face bounding box.
            Should already be preprocessed (equalized etc.).

        Returns
        -------
        roll_no    : str   Student's roll number, or "Unknown".
        name       : str   Student's name, or "Unknown".
        confidence : float Lower = more confident.  Above CONFIDENCE_THRESHOLD
                           the prediction is treated as Unknown.
        """
        if not self.trained:
            return "Unknown", "Unknown", 999.0

        # Resize to the same size used during training
        face_resized = cv2.resize(face_roi_gray, (100, 100))

        label, confidence = self.recognizer.predict(face_resized)

        if confidence > self.CONFIDENCE_THRESHOLD:
            return "Unknown", "Unknown", confidence

        info = self.label_map.get(label, {"roll": "Unknown", "name": "Unknown"})
        return info["roll"], info["name"], confidence
