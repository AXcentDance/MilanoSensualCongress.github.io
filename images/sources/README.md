# Preserved 2026 homepage poster

`milano-sensual-congress-2026-hero-poster-source.webp` is the unchanged original
1280 × 720 poster previously served as `images/poster.webp` (96,534 bytes).
It preserves the existing artwork and exact frame for reproducible compression;
it is not a new promotional image or a rights record.

Run `python3 scripts/build_hero_poster.py` to create the 72,610-byte website copy
at the existing `images/poster.webp` URL. The recipe uses WebP quality 40,
method 6, without resizing or cropping. The builder validates the dimensions,
stages conversion before replacement, and supports `--check`. Full-resolution
comparison retains legible lettering and recognizable faces; the dark homepage
overlay remains unchanged. Quality 50 and 60 candidates were 80,820 and
87,942 bytes respectively.

This input is excluded from the generic responsive-image builder. The existing
full-viewport video uses `object-fit: cover`; selecting a landscape poster only
from a phone's narrow viewport width would not account for the taller crop.
