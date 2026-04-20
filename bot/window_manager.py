"""Window discovery and centering utilities."""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import logging

import cv2
import numpy as np
import pytesseract
from mss import mss

from bot.config import RuntimeConfig

try:
    import pygetwindow as gw
except Exception:  # pragma: no cover - optional import for non-Windows test envs
    gw = None


@dataclass(frozen=True)
class WindowRect:
    left: int
    top: int
    width: int
    height: int
    title: str
    source: str


class GameWindowManager:
    def __init__(self, config: RuntimeConfig, logger: Optional[logging.Logger] = None):
        """Initialize a new `GameWindowManager` instance.

        Parameters:
            config: Parameter containing configuration values that guide behavior.
            logger: Parameter used to emit diagnostic log messages.

        Local Variables:
            None declared inside the function body.

        Returns:
            None. The constructor sets up instance state.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May mutate mutable containers or objects in place.
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def locate_and_prepare_window(self) -> WindowRect:
        """Locate and prepare window.

        Parameters:
            None.

        Local Variables:
            rect: Local variable for rect used in this routine.
            source: Local variable for source used in this routine.
            window: Local variable for window used in this routine.

        Returns:
            A value matching the annotated return type `WindowRect`.

        Side Effects:
            - Updates instance state through `self` attributes.
            - May perform I/O or logging through called dependencies.
        """
        window = self._find_window_by_title()
        source = "title"

        if window is None:
            window = self._find_window_by_ocr_anchor()
            source = "ocr_anchor"

        if window is None:
            raise RuntimeError(
                "Unable to locate game window by title or OCR anchor keywords. "
                "Update RuntimeConfig.game_window_keywords/ocr_window_keywords."
            )

        self._activate_window(window)
        if self.config.auto_center_window:
            self._center_window(window)

        rect = self._window_to_rect(window, source)
        if rect.width < self.config.min_window_width or rect.height < self.config.min_window_height:
            raise RuntimeError(
                "Detected game window is smaller than minimum expected size: "
                f"{rect.width}x{rect.height}"
            )

        self.logger.info(
            "Using game window '%s' at (%d,%d) size %dx%d via %s",
            rect.title,
            rect.left,
            rect.top,
            rect.width,
            rect.height,
            rect.source,
        )
        return rect

    def build_automap_region(self, window_rect: WindowRect) -> dict:
        """Build automap region.

        Parameters:
            window_rect: Parameter for window rect used in this routine.

        Local Variables:
            height: Local variable for height used in this routine.
            left: Local variable for left used in this routine.
            top: Local variable for top used in this routine.
            width: Local variable for width used in this routine.

        Returns:
            A value matching the annotated return type `dict`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        left = window_rect.left + self.config.automap_offset_x
        top = window_rect.top + self.config.automap_offset_y
        width = min(self.config.automap_width, window_rect.width)
        height = min(self.config.automap_height, window_rect.height)

        return {"left": int(left), "top": int(top), "width": int(width), "height": int(height)}

    def _find_window_by_title(self):
        """Internal helper to find window by title.

        Parameters:
            None.

        Local Variables:
            area: Local variable for area used in this routine.
            best: Local variable for best used in this routine.
            best_area: Local variable for best area used in this routine.
            folded: Local variable for folded used in this routine.
            k: Local variable for k used in this routine.
            keywords: Local variable for keywords used in this routine.
            title: Local variable for title used in this routine.
            window: Local variable for window used in this routine.

        Returns:
            A computed value produced by the routine.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        if gw is None:
            return None

        keywords = [k.casefold() for k in self.config.game_window_keywords]
        best = None
        best_area = 0

        for window in gw.getAllWindows():
            title = (window.title or "").strip()
            if not title:
                continue

            folded = title.casefold()
            if not any(k in folded for k in keywords):
                continue

            area = int(window.width) * int(window.height)
            if area > best_area:
                best = window
                best_area = area

        return best

    def _find_window_by_ocr_anchor(self):
        """Internal helper to find window by ocr anchor.

        Parameters:
            None.

        Local Variables:
            anchor: Local variable for anchor used in this routine.
            windows: Local variable for windows used in this routine.
            x: Local variable for x used in this routine.
            y: Local variable for y used in this routine.

        Returns:
            A computed value produced by the routine.

        Side Effects:
            - Updates instance state through `self` attributes.
        """
        if gw is None:
            return None

        anchor = self._scan_screen_for_anchor()
        if anchor is None:
            return None

        x, y = anchor
        try:
            windows = gw.getWindowsAt(x, y)
        except Exception:
            return None

        if not windows:
            return None

        windows = sorted(windows, key=lambda w: int(w.width) * int(w.height), reverse=True)
        return windows[0]

    def _scan_screen_for_anchor(self) -> Optional[Tuple[int, int]]:
        """Internal helper to scan screen for anchor.

        Parameters:
            None.

        Local Variables:
            bgr: Local variable for bgr used in this routine.
            candidates: Local variable for candidates used in this routine.
            conf: Local variable for conf used in this routine.
            conf_raw: Local variable for conf raw used in this routine.
            data: Local variable for data used in this routine.
            frame: Local variable representing image frame data for vision processing.
            gray: Local variable for gray used in this routine.
            i: Local variable used as a position index while iterating.
            k: Local variable for k used in this routine.
            keyword: Local variable for keyword used in this routine.
            keywords: Local variable for keywords used in this routine.
            mean_x: Local variable for mean x used in this routine.
            mean_y: Local variable for mean y used in this routine.
            monitor: Local variable for monitor used in this routine.
            p: Local variable for p used in this routine.
            raw_text: Local variable for raw text used in this routine.
            sct: Local variable for sct used in this routine.
            text: Local variable for text used in this routine.
            x: Local variable for x used in this routine.
            y: Local variable for y used in this routine.

        Returns:
            A value matching the annotated return type `Optional[Tuple[int, int]]`.

        Side Effects:
            - May mutate mutable containers or objects in place.
            - May perform I/O or logging through called dependencies.
        """
        keywords = [k.casefold() for k in self.config.ocr_window_keywords]

        with mss() as sct:
            monitor = sct.monitors[1]
            frame = np.array(sct.grab(monitor))

        bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        data = pytesseract.image_to_data(
            gray,
            output_type=pytesseract.Output.DICT,
            config="--psm 6",
            lang=self.config.ocr_language,
        )

        candidates: List[Tuple[int, int]] = []
        for i, raw_text in enumerate(data.get("text", [])):
            text = (raw_text or "").strip().casefold()
            if not text:
                continue

            conf_raw = data.get("conf", ["-1"])[i]
            try:
                conf = float(conf_raw)
            except ValueError:
                conf = -1.0

            if conf < 30.0:
                continue

            if not any(keyword in text for keyword in keywords):
                continue

            x = int(data["left"][i] + data["width"][i] / 2)
            y = int(data["top"][i] + data["height"][i] / 2)
            candidates.append((x, y))

        if not candidates:
            return None

        mean_x = int(sum(p[0] for p in candidates) / len(candidates))
        mean_y = int(sum(p[1] for p in candidates) / len(candidates))
        self.logger.info("Found OCR window anchor at (%d,%d)", mean_x, mean_y)
        return (mean_x, mean_y)

    def _activate_window(self, window):
        """Internal helper to activate window.

        Parameters:
            window: Parameter for window used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            None.

        Side Effects:
            - May perform I/O or logging through called dependencies.
        """
        try:
            if hasattr(window, "restore"):
                window.restore()
            if hasattr(window, "activate"):
                window.activate()
        except Exception as exc:
            self.logger.warning("Could not fully activate window: %s", exc)

    def _center_window(self, window):
        """Internal helper to center window.

        Parameters:
            window: Parameter for window used in this routine.

        Local Variables:
            monitor: Local variable for monitor used in this routine.
            screen_height: Local variable for screen height used in this routine.
            screen_width: Local variable for screen width used in this routine.
            sct: Local variable for sct used in this routine.
            target_left: Local variable for target left used in this routine.
            target_top: Local variable for target top used in this routine.

        Returns:
            None.

        Side Effects:
            - May perform I/O or logging through called dependencies.
        """
        with mss() as sct:
            monitor = sct.monitors[1]
            screen_width = int(monitor["width"])
            screen_height = int(monitor["height"])

        target_left = max(0, int((screen_width - int(window.width)) / 2))
        target_top = max(0, int((screen_height - int(window.height)) / 2))

        try:
            window.moveTo(target_left, target_top)
        except Exception as exc:
            self.logger.warning("Could not center window: %s", exc)

    def _window_to_rect(self, window, source: str) -> WindowRect:
        """Internal helper to window to rect.

        Parameters:
            window: Parameter for window used in this routine.
            source: Parameter for source used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            A value matching the annotated return type `WindowRect`.

        Side Effects:
            - No direct side effects beyond returning computed values.
        """
        return WindowRect(
            left=int(window.left),
            top=int(window.top),
            width=int(window.width),
            height=int(window.height),
            title=str(window.title or "unknown"),
            source=source,
        )