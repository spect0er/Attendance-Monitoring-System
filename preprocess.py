"""
preprocess.py
=============
Image pre-processing pipeline used before face detection / recognition.

Pipeline (in order)
-------------------
  1. Convert BGR frame to Grayscale   – Haar & LBPH both need single-channel images
  2. Apply Gaussian Blur              – removes sensor noise / JPEG artefacts
  3. Histogram Equalization           – normalises brightness across varied lighting

Call preprocess_frame(frame) from any other module; it returns the fully
processed grayscale image ready for detection or recognition.
"""

import cv2  # OpenCV


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 – Grayscale conversion
# ─────────────────────────────────────────────────────────────────────────────
def convert_to_grayscale(frame):
    """
    Convert a colour BGR image to grayscale.

    Haar Cascade and LBPH Face Recognizer both work on single-channel
    (grayscale) images.  Removing colour also speeds up processing.

    Parameters
    ----------
    frame : numpy.ndarray
        Raw BGR image from camera / video / file.

    Returns
    -------
    gray : numpy.ndarray
        Single-channel grayscale image.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return gray


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 – Gaussian Blur
# ─────────────────────────────────────────────────────────────────────────────
def apply_gaussian_blur(gray_frame, kernel_size=(5, 5)):
    """
    Smooth the grayscale image to reduce noise.

    A Gaussian kernel averages each pixel with its neighbours, suppressing
    random pixel variations that would otherwise create phantom edges and
    confuse the face detector.

    Parameters
    ----------
    gray_frame  : numpy.ndarray   Grayscale image.
    kernel_size : tuple           Odd-valued (width, height). Default (5, 5).

    Returns
    -------
    blurred : numpy.ndarray   Smoothed grayscale image.
    """
    blurred = cv2.GaussianBlur(gray_frame, kernel_size, sigmaX=0)
    return blurred


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 – Histogram Equalization
# ─────────────────────────────────────────────────────────────────────────────
def equalize_histogram(blurred_frame):
    """
    Stretch the pixel-intensity histogram to improve contrast.

    In a classroom some students sit under bright lights, others in shadow.
    Equalisation makes the brightness distribution uniform so faces are
    consistently visible regardless of lighting conditions.

    Parameters
    ----------
    blurred_frame : numpy.ndarray   Blurred grayscale image.

    Returns
    -------
    equalized : numpy.ndarray   Contrast-enhanced grayscale image.
    """
    equalized = cv2.equalizeHist(blurred_frame)
    return equalized


# ─────────────────────────────────────────────────────────────────────────────
# Combined pipeline – the only function other modules need to call
# ─────────────────────────────────────────────────────────────────────────────
def preprocess_frame(frame, kernel_size=(5, 5)):
    """
    Run the full preprocessing pipeline on a single frame.

    colour → grayscale → gaussian blur → histogram equalization

    Parameters
    ----------
    frame       : numpy.ndarray   Raw BGR image.
    kernel_size : tuple           Gaussian blur kernel. Default (5, 5).

    Returns
    -------
    preprocessed : numpy.ndarray  Ready-to-use grayscale image.
    """
    gray         = convert_to_grayscale(frame)
    blurred      = apply_gaussian_blur(gray, kernel_size)
    preprocessed = equalize_histogram(blurred)
    return preprocessed
