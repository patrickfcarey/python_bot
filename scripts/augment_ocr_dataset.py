"""Generate OCR augmentation variants from one or more source images.

Example (single image -> many variants):
python scripts/augment_ocr_dataset.py \
  --input data/ocr/raw/example.png \
  --output-dir data/ocr/augmented/example \
  --variants-per-image 120 \
  --seed 42

Example (directory -> many variants per image):
python scripts/augment_ocr_dataset.py \
  --input data/ocr/raw \
  --output-dir data/ocr/augmented/raw \
  --variants-per-image 18 \
  --seed 42
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable, Dict, List, Sequence, Tuple

import cv2
import numpy as np

VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


AugmentOp = Callable[[np.ndarray, np.random.Generator], Tuple[np.ndarray, Dict[str, object]]]


def _clip_uint8(image: np.ndarray) -> np.ndarray:
    """Internal helper to clip uint8.

    Parameters:
        image: Parameter for image used in this routine.

    Local Variables:
        None declared inside the function body.

    Returns:
        A value matching the annotated return type `np.ndarray`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    return np.clip(image, 0, 255).astype(np.uint8)


def _brightness_contrast(image: np.ndarray, rng: np.random.Generator) -> Tuple[np.ndarray, Dict[str, object]]:
    """Internal helper to brightness contrast.

    Parameters:
        image: Parameter for image used in this routine.
        rng: Parameter for rng used in this routine.

    Local Variables:
        adjusted: Local variable for adjusted used in this routine.
        alpha: Local variable for alpha used in this routine.
        beta: Local variable for beta used in this routine.

    Returns:
        A value matching the annotated return type `Tuple[np.ndarray, Dict[str, object]]`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    alpha = float(rng.uniform(0.70, 1.35))
    beta = float(rng.uniform(-35.0, 35.0))
    adjusted = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
    return adjusted, {"op": "brightness_contrast", "alpha": round(alpha, 3), "beta": round(beta, 3)}


def _gamma_shift(image: np.ndarray, rng: np.random.Generator) -> Tuple[np.ndarray, Dict[str, object]]:
    """Internal helper to gamma shift.

    Parameters:
        image: Parameter for image used in this routine.
        rng: Parameter for rng used in this routine.

    Local Variables:
        adjusted: Local variable for adjusted used in this routine.
        gamma: Local variable for gamma used in this routine.
        inv_gamma: Local variable for inv gamma used in this routine.
        table: Local variable for table used in this routine.
        value: Local variable for value used in this routine.

    Returns:
        A value matching the annotated return type `Tuple[np.ndarray, Dict[str, object]]`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    gamma = float(rng.uniform(0.65, 1.55))
    inv_gamma = 1.0 / gamma
    table = np.array([((value / 255.0) ** inv_gamma) * 255 for value in np.arange(256)]).astype("uint8")
    adjusted = cv2.LUT(image, table)
    return adjusted, {"op": "gamma", "gamma": round(gamma, 3)}


def _down_up_scale(image: np.ndarray, rng: np.random.Generator) -> Tuple[np.ndarray, Dict[str, object]]:
    """Internal helper to down up scale.

    Parameters:
        image: Parameter for image used in this routine.
        rng: Parameter for rng used in this routine.

    Local Variables:
        down_h: Local variable for down h used in this routine.
        down_interp: Local variable for down interp used in this routine.
        down_modes: Local variable for down modes used in this routine.
        down_w: Local variable for down w used in this routine.
        height: Local variable for height used in this routine.
        reduced: Local variable for reduced used in this routine.
        restored: Local variable for restored used in this routine.
        scale: Local variable for scale used in this routine.
        up_interp: Local variable for up interp used in this routine.
        up_modes: Local variable for up modes used in this routine.
        width: Local variable for width used in this routine.

    Returns:
        A value matching the annotated return type `Tuple[np.ndarray, Dict[str, object]]`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    height, width = image.shape[:2]
    scale = float(rng.uniform(0.45, 0.92))

    down_w = max(8, int(width * scale))
    down_h = max(8, int(height * scale))

    down_modes: Sequence[int] = (cv2.INTER_AREA, cv2.INTER_LINEAR, cv2.INTER_NEAREST)
    up_modes: Sequence[int] = (cv2.INTER_LINEAR, cv2.INTER_CUBIC, cv2.INTER_NEAREST)

    down_interp = int(down_modes[int(rng.integers(0, len(down_modes)))])
    up_interp = int(up_modes[int(rng.integers(0, len(up_modes)))])

    reduced = cv2.resize(image, (down_w, down_h), interpolation=down_interp)
    restored = cv2.resize(reduced, (width, height), interpolation=up_interp)

    return restored, {
        "op": "scale_loss",
        "scale": round(scale, 3),
        "down_interp": down_interp,
        "up_interp": up_interp,
    }


def _gaussian_blur(image: np.ndarray, rng: np.random.Generator) -> Tuple[np.ndarray, Dict[str, object]]:
    """Internal helper to gaussian blur.

    Parameters:
        image: Parameter for image used in this routine.
        rng: Parameter for rng used in this routine.

    Local Variables:
        blurred: Local variable for blurred used in this routine.
        kernel_choices: Local variable for kernel choices used in this routine.
        kernel_size: Local variable for kernel size used in this routine.
        sigma: Local variable for sigma used in this routine.

    Returns:
        A value matching the annotated return type `Tuple[np.ndarray, Dict[str, object]]`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    kernel_choices = (3, 5, 7)
    kernel_size = int(kernel_choices[int(rng.integers(0, len(kernel_choices)))])
    sigma = float(rng.uniform(0.6, 2.0))
    blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)
    return blurred, {"op": "gaussian_blur", "kernel": kernel_size, "sigma": round(sigma, 3)}


def _motion_blur(image: np.ndarray, rng: np.random.Generator) -> Tuple[np.ndarray, Dict[str, object]]:
    """Internal helper to motion blur.

    Parameters:
        image: Parameter for image used in this routine.
        rng: Parameter for rng used in this routine.

    Local Variables:
        angle: Local variable for angle used in this routine.
        blurred: Local variable for blurred used in this routine.
        center: Local variable for center used in this routine.
        denom: Local variable for denom used in this routine.
        kernel: Local variable for kernel used in this routine.
        kernel_choices: Local variable for kernel choices used in this routine.
        kernel_size: Local variable for kernel size used in this routine.
        matrix: Local variable for matrix used in this routine.
        rotated: Local variable for rotated used in this routine.

    Returns:
        A value matching the annotated return type `Tuple[np.ndarray, Dict[str, object]]`.

    Side Effects:
        - May mutate mutable containers or objects in place.
    """
    kernel_choices = (3, 5, 7, 9, 11)
    kernel_size = int(kernel_choices[int(rng.integers(0, len(kernel_choices)))])
    angle = float(rng.uniform(-45.0, 45.0))

    kernel = np.zeros((kernel_size, kernel_size), dtype=np.float32)
    kernel[kernel_size // 2, :] = 1.0

    center = (kernel_size / 2.0 - 0.5, kernel_size / 2.0 - 0.5)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(kernel, matrix, (kernel_size, kernel_size))

    denom = float(rotated.sum())
    if denom > 0:
        rotated /= denom

    blurred = cv2.filter2D(image, -1, rotated)
    return blurred, {"op": "motion_blur", "kernel": kernel_size, "angle": round(angle, 3)}


def _gaussian_noise(image: np.ndarray, rng: np.random.Generator) -> Tuple[np.ndarray, Dict[str, object]]:
    """Internal helper to gaussian noise.

    Parameters:
        image: Parameter for image used in this routine.
        rng: Parameter for rng used in this routine.

    Local Variables:
        noise: Local variable for noise used in this routine.
        noisy: Local variable for noisy used in this routine.
        sigma: Local variable for sigma used in this routine.

    Returns:
        A value matching the annotated return type `Tuple[np.ndarray, Dict[str, object]]`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    sigma = float(rng.uniform(3.0, 24.0))
    noise = rng.normal(0.0, sigma, image.shape).astype(np.float32)
    noisy = _clip_uint8(image.astype(np.float32) + noise)
    return noisy, {"op": "gaussian_noise", "sigma": round(sigma, 3)}


def _jpeg_artifacts(image: np.ndarray, rng: np.random.Generator) -> Tuple[np.ndarray, Dict[str, object]]:
    """Internal helper to jpeg artifacts.

    Parameters:
        image: Parameter for image used in this routine.
        rng: Parameter for rng used in this routine.

    Local Variables:
        decoded: Local variable for decoded used in this routine.
        encoded: Local variable for encoded used in this routine.
        ok: Local variable for ok used in this routine.
        quality: Local variable for quality used in this routine.

    Returns:
        A value matching the annotated return type `Tuple[np.ndarray, Dict[str, object]]`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    quality = int(rng.integers(22, 95))
    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return image, {"op": "jpeg_artifacts", "quality": quality, "status": "encode_failed"}

    decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if decoded is None:
        return image, {"op": "jpeg_artifacts", "quality": quality, "status": "decode_failed"}

    return decoded, {"op": "jpeg_artifacts", "quality": quality, "status": "ok"}


def _sharpen(image: np.ndarray, rng: np.random.Generator) -> Tuple[np.ndarray, Dict[str, object]]:
    """Internal helper to sharpen.

    Parameters:
        image: Parameter for image used in this routine.
        rng: Parameter for rng used in this routine.

    Local Variables:
        amount: Local variable for amount used in this routine.
        blurred: Local variable for blurred used in this routine.
        sharpened: Local variable for sharpened used in this routine.
        sigma: Local variable for sigma used in this routine.

    Returns:
        A value matching the annotated return type `Tuple[np.ndarray, Dict[str, object]]`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    amount = float(rng.uniform(0.3, 1.3))
    sigma = float(rng.uniform(0.8, 1.8))
    blurred = cv2.GaussianBlur(image, (0, 0), sigmaX=sigma)
    sharpened = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
    return sharpened, {"op": "sharpen", "amount": round(amount, 3), "sigma": round(sigma, 3)}


def _perspective_jitter(image: np.ndarray, rng: np.random.Generator) -> Tuple[np.ndarray, Dict[str, object]]:
    """Internal helper to perspective jitter.

    Parameters:
        image: Parameter for image used in this routine.
        rng: Parameter for rng used in this routine.

    Local Variables:
        dst: Local variable for dst used in this routine.
        height: Local variable for height used in this routine.
        matrix: Local variable for matrix used in this routine.
        max_shift: Local variable for max shift used in this routine.
        src: Local variable for src used in this routine.
        warped: Local variable for warped used in this routine.
        width: Local variable for width used in this routine.

    Returns:
        A value matching the annotated return type `Tuple[np.ndarray, Dict[str, object]]`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    height, width = image.shape[:2]
    max_shift = float(max(1.0, min(width, height) * 0.045))

    src = np.float32([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
    dst = src + rng.uniform(-max_shift, max_shift, size=(4, 2)).astype(np.float32)

    matrix = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(image, matrix, (width, height), borderMode=cv2.BORDER_REPLICATE)

    return warped, {"op": "perspective_jitter", "max_shift": round(max_shift, 3)}


def _gray_recolor(image: np.ndarray, rng: np.random.Generator) -> Tuple[np.ndarray, Dict[str, object]]:
    """Internal helper to gray recolor.

    Parameters:
        image: Parameter for image used in this routine.
        rng: Parameter for rng used in this routine.

    Local Variables:
        gray: Local variable for gray used in this routine.
        recolor: Local variable for recolor used in this routine.
        tint: Local variable for tint used in this routine.

    Returns:
        A value matching the annotated return type `Tuple[np.ndarray, Dict[str, object]]`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    recolor = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    tint = float(rng.uniform(-18.0, 18.0))
    recolor = cv2.convertScaleAbs(recolor, alpha=1.0, beta=tint)
    return recolor, {"op": "gray_recolor", "tint": round(tint, 3)}


AUGMENTERS: Sequence[AugmentOp] = (
    _brightness_contrast,
    _gamma_shift,
    _down_up_scale,
    _gaussian_blur,
    _motion_blur,
    _gaussian_noise,
    _jpeg_artifacts,
    _sharpen,
    _perspective_jitter,
    _gray_recolor,
)


def augment_image(base_image: np.ndarray, rng: np.random.Generator) -> Tuple[np.ndarray, List[Dict[str, object]]]:
    """Augment image.

    Parameters:
        base_image: Parameter for base image used in this routine.
        rng: Parameter for rng used in this routine.

    Local Variables:
        chosen: Local variable for chosen used in this routine.
        history: Local variable for history used in this routine.
        idx: Local variable for idx used in this routine.
        indices: Local variable for indices used in this routine.
        op_count: Local variable tracking how many items are present or processed.
        op_meta: Local variable for op meta used in this routine.
        output: Local variable for output used in this routine.

    Returns:
        A value matching the annotated return type `Tuple[np.ndarray, List[Dict[str, object]]]`.

    Side Effects:
        - May mutate mutable containers or objects in place.
    """
    output = base_image.copy()
    op_count = int(rng.integers(3, 7))

    indices = np.arange(len(AUGMENTERS))
    rng.shuffle(indices)
    chosen = indices[:op_count]

    history: List[Dict[str, object]] = []
    for idx in chosen:
        output, op_meta = AUGMENTERS[int(idx)](output, rng)
        history.append(op_meta)

    return _clip_uint8(output), history


def collect_input_images(input_path: Path) -> List[Path]:
    """Collect input images.

    Parameters:
        input_path: Parameter containing a filesystem location.

    Local Variables:
        files: Local variable for files used in this routine.
        path: Local variable for path used in this routine.

    Returns:
        A value matching the annotated return type `List[Path]`.

    Side Effects:
        - May mutate mutable containers or objects in place.
    """
    if input_path.is_file():
        return [input_path]

    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    files: List[Path] = []
    for path in input_path.rglob("*"):
        if path.is_file() and path.suffix.lower() in VALID_EXTENSIONS:
            files.append(path)

    files.sort()
    return files


def save_manifest(manifest_path: Path, entries: List[Dict[str, object]]):
    """Save manifest.

    Parameters:
        manifest_path: Parameter containing a filesystem location.
        entries: Parameter for entries used in this routine.

    Local Variables:
        handle: Local variable for handle used in this routine.
        item: Local variable for item used in this routine.

    Returns:
        None.

    Side Effects:
        - May perform I/O or logging through called dependencies.
    """
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as handle:
        for item in entries:
            handle.write(json.dumps(item, ensure_ascii=True) + "\n")


def parse_args() -> argparse.Namespace:
    """Parse args.

    Parameters:
        None.

    Local Variables:
        parser: Local variable for parser used in this routine.

    Returns:
        A value matching the annotated return type `argparse.Namespace`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    parser = argparse.ArgumentParser(description="Generate OCR image augmentation variants")
    parser.add_argument("--input", required=True, help="Input image file or directory")
    parser.add_argument("--output-dir", required=True, help="Output directory for augmented images")
    parser.add_argument(
        "--variants-per-image",
        type=int,
        default=24,
        help="How many augmented images to generate per input image",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible augmentation",
    )
    parser.add_argument(
        "--output-ext",
        choices=("png", "jpg"),
        default="png",
        help="Output image format",
    )
    parser.add_argument(
        "--copy-original",
        action="store_true",
        help="Copy original images into output directory",
    )
    return parser.parse_args()


def main() -> int:
    """Main.

    Parameters:
        None.

    Local Variables:
        args: Local variable for args used in this routine.
        augmented: Local variable for augmented used in this routine.
        idx: Local variable for idx used in this routine.
        image: Local variable for image used in this routine.
        input_path: Local variable containing a filesystem location.
        manifest_entries: Local variable for manifest entries used in this routine.
        manifest_path: Local variable containing a filesystem location.
        ops: Local variable for ops used in this routine.
        original_name: Local variable for original name used in this routine.
        original_path: Local variable containing a filesystem location.
        out_name: Local variable for out name used in this routine.
        out_path: Local variable containing a filesystem location.
        output_dir: Local variable containing a filesystem location.
        rng: Local variable for rng used in this routine.
        source: Local variable for source used in this routine.
        sources: Local variable for sources used in this routine.
        stem: Local variable for stem used in this routine.
        total_written: Local variable for total written used in this routine.

    Returns:
        A value matching the annotated return type `int`.

    Side Effects:
        - May mutate mutable containers or objects in place.
        - May perform I/O or logging through called dependencies.
    """
    args = parse_args()

    if args.variants_per_image <= 0:
        raise ValueError("--variants-per-image must be greater than 0")

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = collect_input_images(input_path)
    if not sources:
        raise RuntimeError(f"No input images found at {input_path}")

    rng = np.random.default_rng(args.seed)
    manifest_entries: List[Dict[str, object]] = []

    total_written = 0
    for source in sources:
        image = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if image is None:
            print(f"[WARN] Skipping unreadable image: {source}")
            continue

        stem = source.stem

        if args.copy_original:
            original_name = f"{stem}__original.{args.output_ext}"
            original_path = output_dir / original_name
            cv2.imwrite(str(original_path), image)
            total_written += 1
            manifest_entries.append(
                {
                    "source": str(source),
                    "output": str(original_path),
                    "type": "original",
                    "ops": [],
                }
            )

        for idx in range(args.variants_per_image):
            augmented, ops = augment_image(image, rng)
            out_name = f"{stem}__aug_{idx:04d}.{args.output_ext}"
            out_path = output_dir / out_name
            cv2.imwrite(str(out_path), augmented)

            total_written += 1
            manifest_entries.append(
                {
                    "source": str(source),
                    "output": str(out_path),
                    "type": "augmented",
                    "variant_index": idx,
                    "ops": ops,
                }
            )

    manifest_path = output_dir / "augmentation_manifest.jsonl"
    save_manifest(manifest_path, manifest_entries)

    print(
        "Generated "
        f"{total_written} images from {len(sources)} source image(s). "
        f"Manifest: {manifest_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())