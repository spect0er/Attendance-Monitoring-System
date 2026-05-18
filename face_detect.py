"""
face_detect.py
==============
Haar Cascade face detection module.

What is Haar Cascade?
  Invented by Viola & Jones (2001).  OpenCV ships with pre-trained XML files
  that encode thousands of "rectangular features" learned from face/non-face
  images.  The classifier slides a detection window across the image at
  multiple scales and votes on whether each region contains a face.

  It is fast, lightweight, and works well for frontal faces — ideal for a
  real-time classroom system.

Key parameters
--------------
  scaleFactor  : how much to shrink the image at each pyramid step
                 1.1 = 10 % smaller each step (accurate but slower)
                 1.3 = 30 % smaller        (faster, may miss some faces)
  minNeighbors : a candidate box must have this many overlapping neighbours
                 before it is accepted.  Lower → more (possibly false) hits.
  minSize      : smallest face box accepted (pixels).  Filters out tiny blobs.
"""

import cv2
import os


class FaceDetector:
    """
    Wraps OpenCV's Haar Cascade and provides a clean detect / draw API.

    Usage
    -----
        detector = FaceDetector()
        faces    = detector.detect_faces(preprocessed_gray)
        annotated = detector.draw_boxes(color_frame, faces, labels)
    """

    def __init__(
        self,
        cascade_path=None,
        scale_factor=1.1,
        min_neighbors=5,
        min_size=(60, 60),
    ):
        """
        Load the Haar Cascade XML file.

        Parameters
        ----------
        cascade_path  : str or None  Path to the XML file.  None → built-in.
        scale_factor  : float        Image pyramid reduction ratio.
        min_neighbors : int          Minimum neighbour count for acceptance.
        min_size      : tuple        Minimum face dimensions (w, h) in pixels.
        """
        if cascade_path is None:
            # cv2.data.haarcascades gives the folder shipped with opencv
            cascade_path = os.path.join(
                cv2.data.haarcascades,
                "haarcascade_frontalface_default.xml",
            )

        if not os.path.exists(cascade_path):
            raise FileNotFoundError(
                f"Haar Cascade XML not found: {cascade_path}\n"
                "Ensure opencv-contrib-python is installed correctly."
            )

        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            raise RuntimeError(f"Failed to load cascade from: {cascade_path}")

        self.scale_factor  = scale_factor
        self.min_neighbors = min_neighbors
        self.min_size      = min_size

    # ─────────────────────────────────────────────────────────────────────────
    def detect_faces(self, preprocessed_frame):
        """
        Detect faces in a preprocessed (grayscale, equalized) frame.

        Parameters
        ----------
        preprocessed_frame : numpy.ndarray  Output of preprocess_frame().

        Returns
        -------
        faces : list of (x, y, w, h) tuples.  Empty list if none detected.
        """
        raw = self.face_cascade.detectMultiScale(
            preprocessed_frame,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            minSize=self.min_size,
            flags=cv2.CASCADE_SCALE_IMAGE,
        )
        if len(raw) == 0:
            return []
        return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in raw]

    # ─────────────────────────────────────────────────────────────────────────
    def draw_boxes(self, frame, faces, labels=None,
                   color=(0, 220, 80), thickness=2):
        """
        Draw bounding boxes (and optional name labels) on a colour frame.

        Parameters
        ----------
        frame     : numpy.ndarray      Original BGR colour frame.
        faces     : list of (x,y,w,h)  From detect_faces().
        labels    : list of str or None  One label per face (e.g. student name).
        color     : tuple              BGR colour for the box.
        thickness : int                Line thickness.

        Returns
        -------
        annotated : numpy.ndarray  Copy of frame with boxes drawn.
        """
        annotated = frame.copy()
        for idx, (x, y, w, h) in enumerate(faces):
            # Draw rectangle
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, thickness)

            # Determine label text
            if labels and idx < len(labels):
                label = labels[idx]
            else:
                label = f"Face {idx + 1}"

            # Filled background for text readability
            (tw, th), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1
            )
            cv2.rectangle(
                annotated, (x, y - th - 8), (x + tw + 6, y), color, cv2.FILLED
            )
            cv2.putText(
                annotated, label,
                (x + 3, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (0, 0, 0), 1, cv2.LINE_AA,
            )
        return annotated

    # ─────────────────────────────────────────────────────────────────────────
    def count_faces(self, faces):
        """Return the number of detected faces."""
        return len(faces)
