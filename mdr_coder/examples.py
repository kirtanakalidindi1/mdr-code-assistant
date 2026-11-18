"""Example outlines to try the tool with."""
from .outline import Outline

EXAMPLES: dict[str, Outline] = {
    "Eye-surgery laser (Nadine's example)": Outline(
        device_name="Ophthalmic surgical laser",
        intended_purpose="A laser system used in eye surgery to reshape the cornea.",
        is_active=True,
        characteristics=["Delivered with a sterile single-use patient interface"],
        processes=["Assembled from electronic components and optics", "Packaging and labelling"],
    ),
    "AI ECG photo app (SaMD)": Outline(
        device_name="ECG photo analysis app",
        intended_purpose=(
            "Standalone software that analyses a photo of a 12-lead ECG using a machine learning "
            "algorithm. It detects possible arrhythmias for review by a clinician."
        ),
        is_active=True,
        characteristics=["Calculates heart rate and QT interval from the ECG"],
        processes=["Distributed with electronic labelling and instructions for use"],
    ),
    "Wearable ECG patch with arrhythmia software": Outline(
        device_name="Wearable ECG patch",
        intended_purpose=(
            "A wearable patch that records the ECG for up to 14 days. Software detects atrial "
            "fibrillation and other arrhythmias for review by a cardiologist."
        ),
        is_active=True,
        characteristics=["Measures heart rate continuously", "Firmware controls recording and Bluetooth upload"],
        processes=["Manufactured using electronic components and a plastic housing", "Packaging and labelling"],
    ),
}
