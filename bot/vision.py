"""Vision pipeline from screen capture to structured game state."""

from dataclasses import dataclass
import re
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import pytesseract
from mss import mss

from bot.config import RuntimeConfig
from bot.game_state import (
    BeltStatus,
    EnemyDetection,
    EnemyTrack,
    GameState,
    GroundItemDetection,
    PickitMatch,
    ResourceStatus,
    TeammateDetection,
)


@dataclass(frozen=True)
class NameplateCrop:
    center: Tuple[int, int]
    bbox: Tuple[int, int, int, int]
    crop: np.ndarray


class Vision:
    def __init__(self, config: RuntimeConfig, capture_region: dict):
        """Initialize a new `Vision` instance.

        Parameters:
            config: Parameter containing configuration values that guide behavior.
            capture_region: Parameter for capture region used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            None. The constructor sets up instance state.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
            - May perform I/O or logging through called dependencies.
        """
        self.config = config
        self.capture_region = capture_region
        self.sct = mss()
        self.teammate_template = cv2.imread(
            str(config.teammate_template_path),
            cv2.IMREAD_UNCHANGED,
        )

    def set_capture_region(self, capture_region: dict):
        """Set capture region.

        Parameters:
            capture_region: Parameter for capture region used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            None.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self.capture_region = capture_region

    def grab_frame(self) -> np.ndarray:
        """Grab frame.

        Parameters:
            None.

        Local Variables:
            frame: Local variable representing image frame data for vision processing.

        Returns:
            A value matching the annotated return type `np.ndarray`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        frame = np.array(self.sct.grab(self.capture_region))
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    def is_loading(self, frame: np.ndarray) -> bool:
        """Is loading.

        Parameters:
            frame: Parameter representing image frame data for vision processing.

        Local Variables:
            gray: Local variable for gray used in this routine.
            mean_brightness: Local variable for mean brightness used in this routine.
            stddev: Local variable for stddev used in this routine.

        Returns:
            A value matching the annotated return type `bool`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        stddev = float(np.std(gray))
        return (
            mean_brightness < self.config.loading_brightness_threshold
            and stddev < self.config.loading_stddev_threshold
        )

    def get_player_position(self, frame: np.ndarray) -> Tuple[int, int]:
        # First pass: use center of automap region as stable proxy.
        """Get player position.

        Parameters:
            frame: Parameter representing image frame data for vision processing.

        Local Variables:
            h: Local variable for h used in this routine.
            w: Local variable for w used in this routine.

        Returns:
            A value matching the annotated return type `Tuple[int, int]`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        h, w, _ = frame.shape
        return (w // 2, h // 2)

    def _green_marker_candidates(self, frame: np.ndarray) -> List[Tuple[int, int]]:
        """Internal helper to green marker candidates.

        Parameters:
            frame: Parameter representing image frame data for vision processing.

        Local Variables:
            area: Local variable for area used in this routine.
            contour: Local variable for contour used in this routine.
            contours: Local variable for contours used in this routine.
            h: Local variable for h used in this routine.
            hsv: Local variable for hsv used in this routine.
            kernel: Local variable for kernel used in this routine.
            lower: Local variable for lower used in this routine.
            mask: Local variable for mask used in this routine.
            points: Local variable for points used in this routine.
            upper: Local variable for upper used in this routine.
            w: Local variable for w used in this routine.
            x: Local variable for x used in this routine.
            y: Local variable for y used in this routine.

        Returns:
            A value matching the annotated return type `List[Tuple[int, int]]`.

        Side Effects:
            - May mutate mutable containers or objects in place.
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower = np.array([35, 70, 70], dtype=np.uint8)
        upper = np.array([90, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)

        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        points: List[Tuple[int, int]] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 8 or area > 250:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            points.append((x + w // 2, y + h // 2))

        return points

    def _template_candidates(self, frame: np.ndarray) -> List[Tuple[int, int]]:
        """Internal helper to template candidates.

        Parameters:
            frame: Parameter representing image frame data for vision processing.

        Local Variables:
            gray_frame: Local variable representing image frame data for vision processing.
            gray_template: Local variable for gray template used in this routine.
            h: Local variable for h used in this routine.
            loc: Local variable for loc used in this routine.
            points: Local variable for points used in this routine.
            pt: Local variable for pt used in this routine.
            result: Local variable holding a computed outcome from a prior step.
            template: Local variable for template used in this routine.
            w: Local variable for w used in this routine.

        Returns:
            A value matching the annotated return type `List[Tuple[int, int]]`.

        Side Effects:
            - May mutate mutable containers or objects in place.
        """
        if self.teammate_template is None:
            return []

        template = self.teammate_template
        if template.ndim == 3 and template.shape[2] == 4:
            template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        w, h = gray_template.shape[::-1]
        result = cv2.matchTemplate(gray_frame, gray_template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(result >= self.config.teammate_template_threshold)

        points: List[Tuple[int, int]] = []
        for pt in zip(*loc[::-1]):
            points.append((pt[0] + w // 2, pt[1] + h // 2))

        return points

    def _dedupe_points(self, points: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Internal helper to dedupe points.

        Parameters:
            points: Parameter for points used in this routine.

        Local Variables:
            deduped: Local variable for deduped used in this routine.
            min_sep: Local variable for min sep used in this routine.
            p: Local variable for p used in this routine.
            point: Local variable for point used in this routine.

        Returns:
            A value matching the annotated return type `List[Tuple[int, int]]`.

        Side Effects:
            - May mutate mutable containers or objects in place.
        """
        deduped: List[Tuple[int, int]] = []
        min_sep = self.config.teammate_min_separation_px

        for point in points:
            if not any((point[0] - p[0]) ** 2 + (point[1] - p[1]) ** 2 < min_sep ** 2 for p in deduped):
                deduped.append(point)

        return deduped

    def _extract_name_crop(self, frame: np.ndarray, center: Tuple[int, int]) -> Optional[NameplateCrop]:
        """Internal helper to extract name crop.

        Parameters:
            frame: Parameter representing image frame data for vision processing.
            center: Parameter for center used in this routine.

        Local Variables:
            crop: Local variable for crop used in this routine.
            crop_h: Local variable for crop h used in this routine.
            crop_w: Local variable for crop w used in this routine.
            cx: Local variable for cx used in this routine.
            cy: Local variable for cy used in this routine.
            h: Local variable for h used in this routine.
            w: Local variable for w used in this routine.
            x1: Local variable for x1 used in this routine.
            x2: Local variable for x2 used in this routine.
            y1: Local variable for y1 used in this routine.
            y2: Local variable for y2 used in this routine.

        Returns:
            A value matching the annotated return type `Optional[NameplateCrop]`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        cx, cy = center
        h, w, _ = frame.shape

        crop_w = 90
        crop_h = 24
        x1 = max(0, cx)
        y1 = max(0, cy - crop_h // 2)
        x2 = min(w, x1 + crop_w)
        y2 = min(h, y1 + crop_h)

        if x2 - x1 < 20 or y2 - y1 < 10:
            return None

        crop = frame[y1:y2, x1:x2]
        return NameplateCrop(center=center, bbox=(x1, y1, x2, y2), crop=crop)

    def _ocr_text_line(self, crop: np.ndarray, psm: int, whitelist: str) -> Tuple[str, float]:
        """Internal helper to ocr text line.

        Parameters:
            crop: Parameter for crop used in this routine.
            psm: Parameter for psm used in this routine.
            whitelist: Parameter for whitelist used in this routine.

        Local Variables:
            bw: Local variable for bw used in this routine.
            conf: Local variable for conf used in this routine.
            conf_raw: Local variable for conf raw used in this routine.
            config: Local variable containing configuration values that guide behavior.
            confs: Local variable for confs used in this routine.
            data: Local variable for data used in this routine.
            gray: Local variable for gray used in this routine.
            i: Local variable used as a position index while iterating.
            parts: Local variable for parts used in this routine.
            raw: Local variable for raw used in this routine.
            text: Local variable for text used in this routine.

        Returns:
            A value matching the annotated return type `Tuple[str, float]`.

        Side Effects:
            - May mutate mutable containers or objects in place.
        """
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        config = f"--oem 3 --psm {psm} -c tessedit_char_whitelist={whitelist}"
        data = pytesseract.image_to_data(
            bw,
            output_type=pytesseract.Output.DICT,
            config=config,
            lang=self.config.ocr_language,
        )

        parts: List[str] = []
        confs: List[float] = []
        for i, raw in enumerate(data.get("text", [])):
            text = (raw or "").strip()
            if not text:
                continue

            conf_raw = data.get("conf", ["-1"])[i]
            try:
                conf = float(conf_raw)
            except ValueError:
                conf = -1.0

            if conf < 0:
                continue

            parts.append(text)
            confs.append(conf)

        if not parts:
            return ("", 0.0)

        return (" ".join(parts), float(sum(confs) / len(confs)))

    def _ocr_name(self, crop: np.ndarray) -> Tuple[str, float]:
        """Internal helper to ocr name.

        Parameters:
            crop: Parameter for crop used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `Tuple[str, float]`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        return self._ocr_text_line(
            crop,
            psm=self.config.ocr_psm,
            whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
        )

    def _chat_command_roi_bounds(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        """Compute bounded OCR ROI for in-game chat command scanning."""
        h, w, _ = frame.shape

        left_pct = max(0.0, min(1.0, float(self.config.chat_command_roi_left_pct)))
        top_pct = max(0.0, min(1.0, float(self.config.chat_command_roi_top_pct)))
        right_pct = max(0.0, min(1.0, float(self.config.chat_command_roi_right_pct)))
        bottom_pct = max(0.0, min(1.0, float(self.config.chat_command_roi_bottom_pct)))

        x1 = int(w * min(left_pct, right_pct))
        x2 = int(w * max(left_pct, right_pct))
        y1 = int(h * min(top_pct, bottom_pct))
        y2 = int(h * max(top_pct, bottom_pct))

        x1 = max(0, min(x1, w - 1))
        x2 = max(x1 + 1, min(x2, w))
        y1 = max(0, min(y1, h - 1))
        y2 = max(y1 + 1, min(y2, h))
        return (x1, y1, x2, y2)

    def scan_chat_lines(self, frame: np.ndarray, max_lines: int = 6) -> List[Tuple[str, float]]:
        """OCR in-game chat box and return recent lines as `(text, confidence)` tuples."""
        if frame is None or frame.size == 0:
            return []

        x1, y1, x2, y2 = self._chat_command_roi_bounds(frame)
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return []

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        config = (
            "--oem 3 --psm 6 "
            "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#:/_-[]()'.,<>+ "
        )
        data = pytesseract.image_to_data(
            bw,
            output_type=pytesseract.Output.DICT,
            config=config,
            lang=self.config.ocr_language,
        )

        grouped: Dict[Tuple[int, int, int], List[Tuple[str, float, int, int, int, int]]] = {}
        min_confidence = float(self.config.chat_command_ocr_confidence_threshold)

        for i, raw in enumerate(data.get("text", [])):
            text = (raw or "").strip()
            if not text:
                continue

            conf_raw = data.get("conf", ["-1"])[i]
            try:
                conf = float(conf_raw)
            except Exception:
                conf = -1.0

            if conf < min_confidence:
                continue

            try:
                block_num = int(data.get("block_num", [0])[i])
                par_num = int(data.get("par_num", [0])[i])
                line_num = int(data.get("line_num", [0])[i])
                left = int(data.get("left", [0])[i])
                top = int(data.get("top", [0])[i])
                width = int(data.get("width", [0])[i])
                height = int(data.get("height", [0])[i])
            except Exception:
                continue

            key = (block_num, par_num, line_num)
            grouped.setdefault(key, []).append((text, conf, left, top, width, height))

        line_rows: List[Tuple[int, str, float]] = []
        for words in grouped.values():
            if not words:
                continue

            words_sorted = sorted(words, key=lambda item: item[2])
            line_text = " ".join(word[0] for word in words_sorted).strip()
            if not line_text:
                continue

            line_top = min(word[3] for word in words_sorted)
            line_confidence = float(sum(word[1] for word in words_sorted) / len(words_sorted))
            line_rows.append((line_top, line_text, line_confidence))

        if not line_rows:
            return []

        line_rows.sort(key=lambda row: row[0])
        limited = line_rows[-max(1, int(max_lines)) :]
        return [(row[1], row[2]) for row in limited]

    def iter_nameplate_crops(self, frame: np.ndarray) -> List[NameplateCrop]:
        """Iter nameplate crops.

        Parameters:
            frame: Parameter representing image frame data for vision processing.

        Local Variables:
            candidates: Local variable for candidates used in this routine.
            center: Local variable for center used in this routine.
            centers: Local variable for centers used in this routine.
            crop: Local variable for crop used in this routine.
            crops: Local variable for crops used in this routine.

        Returns:
            A value matching the annotated return type `List[NameplateCrop]`.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        candidates = self._green_marker_candidates(frame) + self._template_candidates(frame)
        centers = self._dedupe_points(candidates)

        crops: List[NameplateCrop] = []
        for center in centers:
            crop = self._extract_name_crop(frame, center)
            if crop is not None:
                crops.append(crop)

        return crops

    def find_teammates(self, frame: np.ndarray, require_ocr: bool = True) -> List[TeammateDetection]:
        """Find teammates.

        Parameters:
            frame: Parameter representing image frame data for vision processing.
            require_ocr: Parameter for require ocr used in this routine.

        Local Variables:
            confidence: Local variable for confidence used in this routine.
            crop_info: Local variable for crop info used in this routine.
            detections: Local variable for detections used in this routine.
            name: Local variable for name used in this routine.

        Returns:
            A value matching the annotated return type `List[TeammateDetection]`.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        detections: List[TeammateDetection] = []

        for crop_info in self.iter_nameplate_crops(frame):
            name, confidence = self._ocr_name(crop_info.crop)

            if require_ocr:
                if not name:
                    continue
                if confidence < self.config.ocr_name_confidence_threshold:
                    continue

            detections.append(
                TeammateDetection(
                    position=crop_info.center,
                    name=name,
                    confidence=confidence,
                )
            )

        return detections

    def scan_resource_status(self, frame: np.ndarray) -> ResourceStatus:
        """Scan resource status.

        Parameters:
            frame: Parameter representing image frame data for vision processing.

        Local Variables:
            confidence: Local variable for confidence used in this routine.
            h: Local variable for h used in this routine.
            health: Local variable for health used in this routine.
            left: Local variable for left used in this routine.
            mana: Local variable for mana used in this routine.
            right: Local variable for right used in this routine.
            w: Local variable for w used in this routine.
            y1: Local variable for y1 used in this routine.
            y2: Local variable for y2 used in this routine.

        Returns:
            A value matching the annotated return type `ResourceStatus`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        h, w, _ = frame.shape
        if h < 120 or w < 160:
            return ResourceStatus(health_ratio=1.0, mana_ratio=1.0, confidence=0.0)

        y1 = int(h * 0.72)
        y2 = h
        left = frame[y1:y2, 0 : int(w * 0.25)]
        right = frame[y1:y2, int(w * 0.75) : w]

        health = self._dominant_color_fill(left, color="red")
        mana = self._dominant_color_fill(right, color="blue")
        confidence = 0.55

        return ResourceStatus(
            health_ratio=float(max(0.0, min(1.0, health))),
            mana_ratio=float(max(0.0, min(1.0, mana))),
            confidence=confidence,
        )

    def scan_belt_status(self, frame: np.ndarray) -> BeltStatus:
        """Scan belt status.

        Parameters:
            frame: Parameter representing image frame data for vision processing.

        Local Variables:
            belt_roi: Local variable for belt roi used in this routine.
            blue: Local variable for blue used in this routine.
            cell: Local variable for cell used in this routine.
            cell_h: Local variable for cell h used in this routine.
            cell_w: Local variable for cell w used in this routine.
            classified: Local variable for classified used in this routine.
            col: Local variable for col used in this routine.
            cols: Local variable for cols used in this routine.
            confidence: Local variable for confidence used in this routine.
            cx1: Local variable for cx1 used in this routine.
            cx2: Local variable for cx2 used in this routine.
            cy1: Local variable for cy1 used in this routine.
            cy2: Local variable for cy2 used in this routine.
            dominant: Local variable for dominant used in this routine.
            h: Local variable for h used in this routine.
            health_count: Local variable tracking how many items are present or processed.
            hsv: Local variable for hsv used in this routine.
            mana_count: Local variable tracking how many items are present or processed.
            purple: Local variable for purple used in this routine.
            red: Local variable for red used in this routine.
            rejuv_count: Local variable tracking how many items are present or processed.
            row: Local variable for row used in this routine.
            rows: Local variable for rows used in this routine.
            total_slots: Local variable for total slots used in this routine.
            w: Local variable for w used in this routine.
            x1: Local variable for x1 used in this routine.
            x2: Local variable for x2 used in this routine.
            y1: Local variable for y1 used in this routine.
            y2: Local variable for y2 used in this routine.

        Returns:
            A value matching the annotated return type `BeltStatus`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        h, w, _ = frame.shape
        total_slots = max(1, int(self.config.belt_rows) * int(self.config.belt_columns))

        if h < 120 or w < 160:
            return BeltStatus(total_slots=total_slots, confidence=0.0)

        y1 = int(h * 0.82)
        y2 = h
        x1 = int(w * 0.22)
        x2 = int(w * 0.78)
        belt_roi = frame[y1:y2, x1:x2]

        if belt_roi.size == 0:
            return BeltStatus(total_slots=total_slots, confidence=0.0)

        rows = max(1, int(self.config.belt_rows))
        cols = max(1, int(self.config.belt_columns))
        cell_h = max(1, belt_roi.shape[0] // rows)
        cell_w = max(1, belt_roi.shape[1] // cols)

        health_count = 0
        mana_count = 0
        rejuv_count = 0
        classified = 0

        for row in range(rows):
            for col in range(cols):
                cy1 = row * cell_h
                cy2 = belt_roi.shape[0] if row == rows - 1 else (row + 1) * cell_h
                cx1 = col * cell_w
                cx2 = belt_roi.shape[1] if col == cols - 1 else (col + 1) * cell_w
                cell = belt_roi[cy1:cy2, cx1:cx2]
                if cell.size == 0:
                    continue

                hsv = cv2.cvtColor(cell, cv2.COLOR_BGR2HSV)
                red = float(cv2.inRange(hsv, np.array([0, 80, 70], dtype=np.uint8), np.array([10, 255, 255], dtype=np.uint8)).mean() / 255.0)
                blue = float(cv2.inRange(hsv, np.array([95, 70, 70], dtype=np.uint8), np.array([135, 255, 255], dtype=np.uint8)).mean() / 255.0)
                purple = float(cv2.inRange(hsv, np.array([135, 40, 60], dtype=np.uint8), np.array([170, 255, 255], dtype=np.uint8)).mean() / 255.0)

                dominant = max(red, blue, purple)
                if dominant < 0.06:
                    continue

                classified += 1
                if purple >= red and purple >= blue:
                    rejuv_count += 1
                elif red >= blue:
                    health_count += 1
                else:
                    mana_count += 1

        confidence = float(classified / max(1, rows * cols))
        return BeltStatus(
            health_slots_filled=health_count,
            mana_slots_filled=mana_count,
            rejuvenation_slots_filled=rejuv_count,
            total_slots=total_slots,
            confidence=confidence,
        )

    def scan_ground_item_labels(self, frame: np.ndarray, max_labels: int = 12) -> List[GroundItemDetection]:
        """Scan ground item labels.

        Parameters:
            frame: Parameter representing image frame data for vision processing.
            max_labels: Parameter for max labels used in this routine.

        Local Variables:
            bh: Local variable for bh used in this routine.
            block_num: Local variable for block num used in this routine.
            bottom: Local variable for bottom used in this routine.
            bw: Local variable for bw used in this routine.
            center: Local variable for center used in this routine.
            conf: Local variable for conf used in this routine.
            conf_avg: Local variable for conf avg used in this routine.
            conf_raw: Local variable for conf raw used in this routine.
            config: Local variable containing configuration values that guide behavior.
            data: Local variable for data used in this routine.
            detections: Local variable for detections used in this routine.
            gold_amount: Local variable for gold amount used in this routine.
            gray: Local variable for gray used in this routine.
            grouped: Local variable for grouped used in this routine.
            h: Local variable for h used in this routine.
            i: Local variable used as a position index while iterating.
            is_gold: Local variable representing a boolean condition.
            key: Local variable for key used in this routine.
            label: Local variable for label used in this routine.
            left: Local variable for left used in this routine.
            line_num: Local variable for line num used in this routine.
            par_num: Local variable for par num used in this routine.
            raw: Local variable for raw used in this routine.
            right: Local variable for right used in this routine.
            roi: Local variable for roi used in this routine.
            text: Local variable for text used in this routine.
            threshold: Local variable for threshold used in this routine.
            top: Local variable for top used in this routine.
            w: Local variable for w used in this routine.
            word: Local variable for word used in this routine.
            words: Local variable for words used in this routine.
            words_sorted: Local variable for words sorted used in this routine.
            x: Local variable for x used in this routine.
            x1: Local variable for x1 used in this routine.
            x2: Local variable for x2 used in this routine.
            y: Local variable for y used in this routine.
            y1: Local variable for y1 used in this routine.
            y2: Local variable for y2 used in this routine.

        Returns:
            A value matching the annotated return type `List[GroundItemDetection]`.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        h, w, _ = frame.shape
        if h < 80 or w < 80:
            return []

        y1 = int(h * 0.28)
        y2 = int(h * 0.95)
        x1 = int(w * 0.05)
        x2 = int(w * 0.95)

        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return []

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        config = "--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789' ,()-"

        data = pytesseract.image_to_data(
            gray,
            output_type=pytesseract.Output.DICT,
            config=config,
            lang=self.config.ocr_language,
        )

        grouped: Dict[Tuple[int, int, int], List[Tuple[str, float, int, int, int, int]]] = {}
        threshold = float(self.config.ground_item_ocr_confidence_threshold)

        for i, raw in enumerate(data.get("text", [])):
            text = (raw or "").strip()
            if not text:
                continue

            conf_raw = data.get("conf", ["-1"])[i]
            try:
                conf = float(conf_raw)
            except ValueError:
                conf = -1.0

            if conf < threshold:
                continue

            try:
                block_num = int(data.get("block_num", [0])[i])
                par_num = int(data.get("par_num", [0])[i])
                line_num = int(data.get("line_num", [0])[i])
                x = int(data.get("left", [0])[i])
                y = int(data.get("top", [0])[i])
                bw = int(data.get("width", [0])[i])
                bh = int(data.get("height", [0])[i])
            except Exception:
                continue

            key = (block_num, par_num, line_num)
            grouped.setdefault(key, []).append((text, conf, x, y, bw, bh))

        detections: List[GroundItemDetection] = []
        for words in grouped.values():
            if not words:
                continue

            words_sorted = sorted(words, key=lambda item: item[2])
            label = " ".join(word[0] for word in words_sorted).strip()
            if not label:
                continue

            conf_avg = float(sum(word[1] for word in words_sorted) / len(words_sorted))
            left = min(word[2] for word in words_sorted)
            top = min(word[3] for word in words_sorted)
            right = max(word[2] + word[4] for word in words_sorted)
            bottom = max(word[3] + word[5] for word in words_sorted)

            center = (x1 + (left + right) // 2, y1 + (top + bottom) // 2)
            is_gold, gold_amount = self._parse_gold_label(label)

            detections.append(
                GroundItemDetection(
                    position=center,
                    label=label,
                    confidence=conf_avg,
                    is_gold=is_gold,
                    gold_amount=gold_amount,
                )
            )

        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections[: max(1, int(max_labels))]

    def scan_ground_gold(self, frame: np.ndarray, max_labels: int = 12) -> List[GroundItemDetection]:
        """Scan ground gold.

        Parameters:
            frame: Parameter representing image frame data for vision processing.
            max_labels: Parameter for max labels used in this routine.

        Local Variables:
            d: Local variable for d used in this routine.
            detections: Local variable for detections used in this routine.

        Returns:
            A value matching the annotated return type `List[GroundItemDetection]`.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        detections = self.scan_ground_item_labels(frame, max_labels=max_labels)
        return [d for d in detections if d.is_gold]

    def _parse_gold_label(self, label: str) -> Tuple[bool, int]:
        """Internal helper to parse gold label.

        Parameters:
            label: Parameter for label used in this routine.

        Local Variables:
            cleaned: Local variable for cleaned used in this routine.
            match: Local variable for match used in this routine.
            numbers: Local variable for numbers used in this routine.
            raw: Local variable for raw used in this routine.

        Returns:
            A value matching the annotated return type `Tuple[bool, int]`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        raw = label.strip().lower()
        if "gold" not in raw:
            return (False, 0)

        cleaned = raw.replace(",", "")
        match = re.search(r"(\d{1,7})\s*gold", cleaned)
        if match is not None:
            return (True, int(match.group(1)))

        numbers = re.findall(r"\d{1,7}", cleaned)
        if numbers:
            return (True, int(numbers[0]))

        return (True, 0)

    def _dominant_color_fill(self, roi: np.ndarray, color: str) -> float:
        """Internal helper to dominant color fill.

        Parameters:
            roi: Parameter for roi used in this routine.
            color: Parameter for color used in this routine.

        Local Variables:
            b: Local variable for b used in this routine.
            g: Local variable for g used in this routine.
            mask: Local variable for mask used in this routine.
            r: Local variable for r used in this routine.
            ratio: Local variable for ratio used in this routine.

        Returns:
            A value matching the annotated return type `float`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        if roi.size == 0:
            return 0.0

        b = roi[:, :, 0].astype(np.float32)
        g = roi[:, :, 1].astype(np.float32)
        r = roi[:, :, 2].astype(np.float32)

        if color == "red":
            mask = (r > 40.0) & (r > (g * 1.20)) & (r > (b * 1.20))
        elif color == "blue":
            mask = (b > 40.0) & (b > (r * 1.20)) & (b > (g * 1.20))
        else:
            mask = np.zeros_like(r, dtype=bool)

        ratio = float(mask.sum()) / float(mask.size)
        # Scale because only part of the orb region is typically occupied by strong color.
        return min(1.0, ratio * 4.5)

    def scan_enemies(self, frame: np.ndarray) -> List[EnemyDetection]:
        """Stub hook for future enemy scanning logic.

        Current behavior is a conservative red-marker heuristic placeholder that only
        provides approximate enemy points. Replace with sprite/template/model-based
        detection before enabling live combat behavior in production.
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        lower_red_1 = np.array([0, 80, 70], dtype=np.uint8)
        upper_red_1 = np.array([10, 255, 255], dtype=np.uint8)
        lower_red_2 = np.array([160, 80, 70], dtype=np.uint8)
        upper_red_2 = np.array([179, 255, 255], dtype=np.uint8)

        mask_1 = cv2.inRange(hsv, lower_red_1, upper_red_1)
        mask_2 = cv2.inRange(hsv, lower_red_2, upper_red_2)
        mask = cv2.bitwise_or(mask_1, mask_2)

        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detections: List[EnemyDetection] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.config.enemy_scan_min_area or area > self.config.enemy_scan_max_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            detections.append(
                EnemyDetection(
                    position=(x + w // 2, y + h // 2),
                    enemy_type="unknown",
                    confidence=0.25,
                    is_elite=False,
                    combat_relevant=True,
                    danger_priority=2,
                    danger_label="low",
                    danger_tags=("unclassified_enemy",),
                )
            )

        return detections

    def track_enemies(self, enemy_detections: List[EnemyDetection], tracker) -> List[EnemyTrack]:
        """Stub hook for future enemy tracking.

        This delegates to the tracker implementation so behavior can be swapped
        later (Kalman filter, optical flow, ReID, etc.) without changing Vision.
        """
        return tracker.update(enemy_detections)

    def extract_game_state(
        self,
        frame: np.ndarray,
        level_number: int,
        enemy_detections: Optional[List[EnemyDetection]] = None,
        enemy_tracks: Optional[List[EnemyTrack]] = None,
        combat_state: str = "idle",
        resource_status: Optional[ResourceStatus] = None,
        belt_status: Optional[BeltStatus] = None,
        ground_items: Optional[List[GroundItemDetection]] = None,
        gold_items: Optional[List[GroundItemDetection]] = None,
        pickit_matches: Optional[List[PickitMatch]] = None,
    ) -> GameState:
        """Extract game state.

        Parameters:
            frame: Parameter representing image frame data for vision processing.
            level_number: Parameter for level number used in this routine.
            enemy_detections: Parameter for enemy detections used in this routine.
            enemy_tracks: Parameter for enemy tracks used in this routine.
            combat_state: Parameter carrying runtime state information.
            resource_status: Parameter for resource status used in this routine.
            belt_status: Parameter for belt status used in this routine.
            ground_items: Parameter for ground items used in this routine.
            gold_items: Parameter for gold items used in this routine.
            pickit_matches: Parameter for pickit matches used in this routine.

        Local Variables:
            detection: Local variable for detection used in this routine.
            dx: Local variable for dx used in this routine.
            dy: Local variable for dy used in this routine.
            player_position: Local variable for player position used in this routine.
            relative_vectors: Local variable for relative vectors used in this routine.
            teammate_detections: Local variable for teammate detections used in this routine.

        Returns:
            A value matching the annotated return type `GameState`.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        player_position = self.get_player_position(frame)
        teammate_detections = self.find_teammates(frame, require_ocr=True)

        if enemy_detections is None:
            enemy_detections = self.scan_enemies(frame)

        if enemy_tracks is None:
            enemy_tracks = []

        if ground_items is None:
            ground_items = []

        if gold_items is None:
            gold_items = []

        if pickit_matches is None:
            pickit_matches = []

        relative_vectors: List[Tuple[float, float]] = []
        for detection in teammate_detections:
            dx = detection.position[0] - player_position[0]
            dy = detection.position[1] - player_position[1]
            relative_vectors.append((float(dx), float(dy)))

        return GameState(
            automap_matrix=frame,
            teammate_detections=teammate_detections,
            player_position=player_position,
            relative_vectors=relative_vectors,
            enemy_detections=enemy_detections,
            enemy_tracks=enemy_tracks,
            combat_state=combat_state,
            level_number=level_number,
            loading=self.is_loading(frame),
            resource_status=resource_status,
            belt_status=belt_status,
            ground_items=ground_items,
            gold_items=gold_items,
            pickit_matches=pickit_matches,
        )

