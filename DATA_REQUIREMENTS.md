# Data Requirements From User

This file lists every required data element you need to provide, where to place it, and the filename scheme.

All paths are relative to repo root: `C:\github\python_bot`.

For enemy monster detection datasets (hover-name OCR + monster image recognition), use [MONSTER_DATA_STRUCTURE.md](MONSTER_DATA_STRUCTURE.md).

## 1) Required Inputs (Must Provide)

| Data Element | Required | Destination | Filename Scheme | Example |
|---|---|---|---|---|
| Teammate marker template (green X) | Yes | `bot/templates/` | Exact filename required | `bot/templates/green_x.png` |
| Ally-name OCR raw crops/screenshots | Yes | `data/ocr/raw/ally_names/` | `ally_<allyname>__act<act>__zone<zone>__state<static|motion|hard>__idx####.png` | `ally_Ari__act2__zoneLutGholein__statemotion__idx0007.png` |
| Command-message OCR raw screenshots/crops | Yes | `data/ocr/raw/commands/` | `cmd_<command>__sender<name>__ctx<normal|combat|noise>__idx####.png` | `cmd_follow__senderAri__ctxcombat__idx0012.png` |
| Command negative (non-command) chat lines | Yes | `data/ocr/raw/commands_neg/` | `neg_chat__sender<name>__ctx<normal|combat|noise>__idx####.png` | `neg_chat__senderAri__ctxnoise__idx0045.png` |
| Ally-name labels TSV | Yes | `data/ocr/labeled/` | Exact filename required | `data/ocr/labeled/ally_labels.tsv` |
| Command labels TSV | Yes | `data/ocr/labeled/` | Exact filename required | `data/ocr/labeled/command_labels.tsv` |
| Negative chat labels TSV | Yes | `data/ocr/labeled/` | Exact filename required | `data/ocr/labeled/command_negative_labels.tsv` |
| Command vocabulary list | Yes | `data/ocr/labeled/` | Exact filename required | `data/ocr/labeled/command_vocab.txt` |
| Pickit database ruleset | Yes (for auto loot) | `data/pickit/` | Exact filename required | `data/pickit/default_pickit.json` |

## 2) Label File Formats (Required)

### 2.1 Ally labels
File: `data/ocr/labeled/ally_labels.tsv`

Format (tab-separated):
`relative_path<TAB>text`

Example:
`data/ocr/raw/ally_names/ally_Ari__act2__zoneLutGholein__statemotion__idx0007.png	Ari`

### 2.2 Command labels
File: `data/ocr/labeled/command_labels.tsv`

Format:
`relative_path<TAB>text`

Example:
`data/ocr/raw/commands/cmd_follow__senderAri__ctxcombat__idx0012.png	follow`

### 2.3 Negative chat labels
File: `data/ocr/labeled/command_negative_labels.tsv`

Format:
`relative_path<TAB>text`

Use exact chat text or a sentinel like `__NEGATIVE__` (pick one style and keep it consistent).

Example:
`data/ocr/raw/commands_neg/neg_chat__senderAri__ctxnoise__idx0045.png	__NEGATIVE__`

### 2.4 Command vocabulary
File: `data/ocr/labeled/command_vocab.txt`

One command per line.

Example:
```
follow
stop
town
tp
hold
assist
```

## 3) Minimum Data Counts You Must Collect

### 3.1 Ally-name OCR (automap font, in motion)
Minimum raw target:
- 40 distinct ally names
- 35 images per name
- Total: 1,400

Recommended raw target:
- 80 distinct ally names
- 50 images per name
- Total: 4,000

Required per-name distribution (minimum set):
- 15 static (clear baseline)
- 15 motion (camera/player movement)
- 5 hard cases (low contrast, clutter, overlaps)

### 3.2 Command-message OCR
Assumed command vocabulary:
- 20 commands

Minimum raw target:
- Command positives: 80 per command (1,600)
- Non-command negatives: 1,000
- Sender diversity: >= 30 unique sender names
- Total: 2,600

Recommended raw target:
- Command positives: 150 per command (3,000)
- Non-command negatives: 2,000
- Sender diversity: >= 50 unique sender names
- Total: 5,000

## 4) Augmentation Outputs (Generated, But You Should Keep)

Script: `scripts/augment_ocr_dataset.py`

Recommended output locations:
- Ally augments: `data/ocr/augmented/ally_names/`
- Command augments: `data/ocr/augmented/commands/`

Generated filename scheme (from script):
- `<source_stem>__aug_####.png`
- optional original copy: `<source_stem>__original.png`

Generated manifest (per output dir):
- `augmentation_manifest.jsonl`

## 5) Optional But Strongly Recommended Inputs

| Data Element | Destination | Filename Scheme | Example |
|---|---|---|---|
| Vision calibration screenshots | `bot/tests/screenshots/` | `vision_<topic>__idx####.png` | `vision_automap_dense_party__idx0003.png` |
| Teammate template variants (different resolutions/UI scales) | `bot/templates/variants/` | `green_x__scale<percent>__idx##.png` | `green_x__scale125__idx01.png` |
| Manual train/val split files | `data/ocr/labeled/splits/` | `train.txt`, `val.txt` | `data/ocr/labeled/splits/val.txt` |
| OCR error audit log from dry runs | `logs/` | `ocr_miss_audit_YYYYMMDD.md` | `logs/ocr_miss_audit_20260415.md` |

## 6) Tesstrain Ground Truth (When You Start Training)

If you convert to tesstrain format, place generated ground-truth files in:
- `data/ocr/tesstrain_groundtruth/`

Expected pair scheme:
- image: `<id>.png`
- text: `<id>.gt.txt`

Example:
- `data/ocr/tesstrain_groundtruth/ally_Ari_0001.png`
- `data/ocr/tesstrain_groundtruth/ally_Ari_0001.gt.txt`

## 7) Trained Model Output (After Training)

Final traineddata filename recommendation:
- `diablo2.traineddata`

Install destination (outside repo):
- `C:\Program Files\Tesseract-OCR\tessdata\diablo2.traineddata`

Then set runtime OCR language code to `diablo2` in config.

## 8) Example Directory Layout

```
bot/templates/
  green_x.png
  variants/

data/ocr/raw/
  ally_names/
  commands/
  commands_neg/

data/ocr/labeled/
  ally_labels.tsv
  command_labels.tsv
  command_negative_labels.tsv
  command_vocab.txt
  splits/

# generated by script


data/pickit/
  default_pickit.json
data/ocr/augmented/
  ally_names/
  commands/
```

## 9) Final Pre-Training Checklist

- `bot/templates/green_x.png` exists
- Ally raw counts meet minimum target
- Command raw + negative counts meet minimum target
- Labels are complete and tab-separated
- `command_vocab.txt` exists and is finalized
- Augmentation generated and manifests present
- Validation split exists (`10-20%` holdout)
