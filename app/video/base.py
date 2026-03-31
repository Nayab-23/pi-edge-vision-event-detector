from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np


@dataclass(slots=True)
class FramePacket:
    frame: np.ndarray
    frame_index: int
    timestamp: float
    source_mode: str


@dataclass(slots=True)
class SourceInfo:
    mode: str
    label: str
    details: dict[str, Any] = field(default_factory=dict)


class VideoSource(Protocol):
    info: SourceInfo

    def open(self) -> None: ...

    def read(self) -> FramePacket | None: ...

    def close(self) -> None: ...
