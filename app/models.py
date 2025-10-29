from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class MeasurementDraft:
    systolic: int
    diastolic: int
    pulse: int
    body_position_text: Optional[str]
    arm_location_text: Optional[str]
    well_being_text: Optional[str]
    comment_text: Optional[str]


@dataclass
class MeasurementEdit:
    measurement_id: int
    systolic: Optional[int] = None
    diastolic: Optional[int] = None
    pulse: Optional[int] = None
    position_name: Optional[str] = None
    location_name: Optional[str] = None
    well_being: Optional[str] = None
    comments: Optional[str] = None
