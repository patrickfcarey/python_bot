"""OCR dataset capture helpers."""

from dataclasses import dataclass
from pathlib import Path
from typing import List
import json
import time
import logging

import cv2

from bot.vision import Vision


@dataclass(frozen=True)
class OCRCaptureSummary:
    saved: int
    output_dir: Path
    manifest_path: Path


class OCRDatasetCollector:
    def __init__(self, vision: Vision, output_dir: Path, logger: logging.Logger):
        """Initialize a new `OCRDatasetCollector` instance.

        Parameters:
            vision: Parameter for vision used in this routine.
            output_dir: Parameter containing a filesystem location.
            logger: Parameter used to emit diagnostic log messages.

        Local Variables:
            None declared inside the function body.

        Returns:
            None. The constructor sets up instance state.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self.vision = vision
        self.output_dir = output_dir
        self.logger = logger

    def capture(self, sample_goal: int, interval_seconds: float = 0.35) -> OCRCaptureSummary:
        """Capture.

        Parameters:
            sample_goal: Parameter for sample goal used in this routine.
            interval_seconds: Parameter for interval seconds used in this routine.

        Local Variables:
            crop_info: Local variable for crop info used in this routine.
            crops: Local variable for crops used in this routine.
            entries: Local variable for entries used in this routine.
            entry: Local variable for entry used in this routine.
            filename: Local variable for filename used in this routine.
            frame: Local variable representing image frame data for vision processing.
            full_path: Local variable containing a filesystem location.
            handle: Local variable for handle used in this routine.
            line: Local variable for line used in this routine.
            manifest_path: Local variable containing a filesystem location.
            saved: Local variable for saved used in this routine.

        Returns:
            A value matching the annotated return type `OCRCaptureSummary`.

        Side Effects:
            - May mutate mutable containers or objects in place.
            - May perform I/O or logging through called dependencies.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self.output_dir / "manifest.jsonl"

        saved = 0
        entries: List[str] = []

        while saved < sample_goal:
            frame = self.vision.grab_frame()
            crops = self.vision.iter_nameplate_crops(frame)

            if not crops:
                time.sleep(interval_seconds)
                continue

            for crop_info in crops:
                if saved >= sample_goal:
                    break

                filename = f"ocr_{int(time.time() * 1000)}_{saved:05d}.png"
                full_path = self.output_dir / filename
                cv2.imwrite(str(full_path), crop_info.crop)

                entry = {
                    "file": filename,
                    "bbox": {
                        "x1": crop_info.bbox[0],
                        "y1": crop_info.bbox[1],
                        "x2": crop_info.bbox[2],
                        "y2": crop_info.bbox[3],
                    },
                    "center": {"x": crop_info.center[0], "y": crop_info.center[1]},
                    "label": "",
                    "timestamp": time.time(),
                }
                entries.append(json.dumps(entry))
                saved += 1

            self.logger.info("OCR capture progress: %d/%d", saved, sample_goal)
            time.sleep(interval_seconds)

        with manifest_path.open("a", encoding="utf-8") as handle:
            for line in entries:
                handle.write(line + "\n")

        self.logger.info("Saved %d OCR crops to %s", saved, self.output_dir)
        return OCRCaptureSummary(saved=saved, output_dir=self.output_dir, manifest_path=manifest_path)