# Tradeoffs

## Why Motion Detection First

The Pi must run this project even without a dedicated accelerator and even when camera hardware is missing. Motion detection is:

- cheap enough for CPU-only execution
- deterministic for testing with a sample video
- robust enough to produce clips and metadata immediately

## Why Person Detection Is Optional

OpenCV's built-in HOG person detector is usable for a lightweight secondary signal, but it is much heavier than the motion baseline. It is disabled by default so the app remains responsive on constrained Raspberry Pi deployments.

## Why Sample Video Fallback Matters

Without a sample fallback, the project would be blocked by missing hardware. The generated demo video guarantees:

- the pipeline is runnable on day one
- tests and local smoke checks work without a camera
- dashboard, storage, and event flow can be demoed consistently

## Clip Format Choice

The app writes AVI clips with MJPG because that is broadly supported with OpenCV on Raspberry Pi and avoids codec surprises that often happen with MP4 container and encoder combinations on minimal systems.
