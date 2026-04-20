# OCR Workflow (Data Collection, Augmentation, Labeling, Training)

This document defines concrete OCR dataset targets for:
- automap ally-name recognition
- chat command/message recognition

It also includes a script that can turn one source screenshot into many training variants.

For enemy monster OCR/visual datasets (hover-name bar + monster body imagery), use [MONSTER_DATA_STRUCTURE.md](MONSTER_DATA_STRUCTURE.md).

## 1. Tooling Requirements

- Tesseract OCR 5.x installed on Windows and available on `PATH`
- Python environment with repo dependencies installed
- Diablo II running in stable window mode (windowed or borderless windowed)

## 2. Dataset Types and Required Counts

### 2.1 Ally Name OCR (Automap)

Goal: read ally names reliably while moving and under blur/compression/noise.

Minimum first-pass raw dataset:
- `40` distinct ally names
- `35` raw crops per name
- total raw crops: `1,400`

Recommended raw dataset:
- `80` distinct ally names
- `50` raw crops per name
- total raw crops: `4,000`

Per-name raw capture distribution:
- `15` stationary captures (clear font baseline)
- `15` motion captures (running/teleporting camera movement)
- `5` hard-case captures (low contrast, clutter, partial overlaps)

For recommended set, scale to:
- `20` stationary
- `20` motion
- `10` hard-case

### 2.2 Command Message OCR (Chat/Command Recognition)

Goal: read issued commands from chat reliably and avoid false triggers.

Assumed command vocabulary size:
- `20` command phrases (example: `follow`, `stop`, `town`, `tp`, etc.)

Minimum first-pass raw dataset:
- command positives: `80` per command (`1,600` total)
- non-command negatives: `1,000`
- sender-name variability: at least `30` unique senders represented
- total raw chat lines: `2,600`

Recommended raw dataset:
- command positives: `150` per command (`3,000` total)
- non-command negatives: `2,000`
- sender-name variability: at least `50` unique senders represented
- total raw chat lines: `5,000`

## 2.3 Go-Live Dataset Gates (Must Pass)

Use these gates before first live non-dry-run operation. If any gate fails, continue data collection/iteration.

### Ally-name OCR gates
- Data volume gate: at least the minimum dataset in section 2.1 (`1,400` raw crops across `40` names).
- Motion coverage gate: per name, include all three conditions (`stationary`, `motion`, `hard-case`).
- Validation split gate: keep a real holdout set of at least `15%` that is never used in training.
- Exact-match accuracy gate (stationary holdout): `>= 97%`.
- Exact-match accuracy gate (motion + hard-case holdout): `>= 93%`.
- Blank/unknown output gate on ally-name holdout: `<= 1.5%`.

### Command-message OCR gates
- Data volume gate: at least the minimum dataset in section 2.2 (`2,600` raw lines total).
- Sender diversity gate: at least `30` unique sender names in the minimum set.
- Validation split gate: keep a real holdout set of at least `15%` with command and non-command lines.
- Command recall gate on holdout (true command lines): `>= 95%`.
- Command precision gate on holdout (trigger correctness): `>= 98%`.
- False-trigger gate on non-command holdout lines: `<= 1` false trigger per `1,000` lines.

### Operational readiness gate
- Run `ocr-bench` on live capture (not synthetic only) and confirm stable timings plus acceptable recognition quality.
- Re-check these gates after any OCR model/language update or major capture pipeline change.

## 3. Augmentation Script (One Image -> Many Training Images)

Script path:
- `scripts/augment_ocr_dataset.py`

### 3.1 Single-image expansion example

```powershell
python scripts/augment_ocr_dataset.py `
  --input data/ocr/raw/example.png `
  --output-dir data/ocr/augmented/example `
  --variants-per-image 120 `
  --seed 42
```

### 3.2 Directory expansion example

```powershell
python scripts/augment_ocr_dataset.py `
  --input data/ocr/raw `
  --output-dir data/ocr/augmented/raw `
  --variants-per-image 12 `
  --seed 42 `
  --copy-original
```

### 3.3 What the script simulates

Each variant applies a random chain of quality and motion effects:
- brightness/contrast shifts
- gamma changes
- downscale-upscale quality loss
- Gaussian blur
- motion blur
- Gaussian noise
- JPEG compression artifacts
- sharpening
- slight perspective jitter
- grayscale/tint remapping

A manifest is written to:
- `augmentation_manifest.jsonl`

## 4. Recommended Augmentation Multipliers

For ally-name OCR:
- minimum raw: `1,400`
- recommended multiplier: `12x`
- resulting training images: `16,800`

For command-message OCR:
- minimum raw: `2,600`
- recommended multiplier: `8x`
- resulting training images: `20,800`

Important:
- keep at least `70%` real captures in final training mix
- synthetic variants improve robustness but should not replace real motion captures

## 5. Labeling Requirements

Each crop/line requires an exact text label.

Recommended format:
- `filename<TAB>label`

Example:
```
ocr_1712661000000_00001.png\tPlayerOne
ocr_1712661000100_00002.png\tfollow
```

Store curated labels in:
- `data/ocr/labeled/`

## 6. Dataset Quality Rules

- remove unreadable, empty, or corrupted crops
- keep class and sender diversity high
- reserve `10-20%` holdout for validation
- retain difficult negatives to reduce command false positives

## 7. Tesseract Fine-Tuning (High-Level)

1. convert labeled files to tesstrain format
2. prepare `GROUND_TRUTH_DIR`
3. train from `START_MODEL=eng`
4. evaluate on holdout set
5. deploy `.traineddata`

Example command shape:

```bash
make training \
  MODEL_NAME=diablo2 \
  START_MODEL=eng \
  TESSDATA=/path/to/tessdata \
  GROUND_TRUTH_DIR=/path/to/ground-truth
```

## 8. Deployment Requirements

When custom `.traineddata` is ready:
- place it in Tesseract `tessdata` directory
- set `ocr_language` in `RuntimeConfig`
- rerun dry-run validation sessions

## 9. Continuous Iteration Loop

1. collect misses during dry-run sessions
2. add more hard real captures (especially motion + low contrast)
3. regenerate synthetic variants with script
4. retrain and compare precision/recall
5. promote only when command false-positive rate is acceptable
