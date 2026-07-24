"""Prepare measurement statistics for text summaries and charts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import median
from typing import Iterable, Sequence


@dataclass(frozen=True)
class MeasurementPoint:
    timestamp: datetime
    systolic: int
    diastolic: int
    pulse: int


@dataclass(frozen=True)
class ChartPoint:
    timestamp: datetime
    systolic: float
    diastolic: float
    pulse: float
    systolic_min: int
    systolic_max: int
    diastolic_min: int
    diastolic_max: int
    pulse_min: int
    pulse_max: int


@dataclass(frozen=True)
class StatisticsReport:
    measurements: Sequence[MeasurementPoint]
    chart_points: Sequence[ChartPoint]
    days: int
    daily_aggregation: bool

    @property
    def count(self) -> int:
        return len(self.measurements)

    @property
    def median_systolic(self) -> float:
        return median(point.systolic for point in self.measurements)

    @property
    def median_diastolic(self) -> float:
        return median(point.diastolic for point in self.measurements)

    @property
    def median_pulse(self) -> float:
        return median(point.pulse for point in self.measurements)


def _parse_timestamp(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def rows_to_measurements(rows: Iterable[tuple]) -> list[MeasurementPoint]:
    """Convert repository rows into chronological measurement points."""
    points = [
        MeasurementPoint(
            timestamp=_parse_timestamp(row[1]),
            systolic=int(row[2]),
            diastolic=int(row[3]),
            pulse=int(row[4]),
        )
        for row in rows
    ]
    return sorted(points, key=lambda point: point.timestamp)


def _as_chart_point(points: Sequence[MeasurementPoint]) -> ChartPoint:
    systolic = [point.systolic for point in points]
    diastolic = [point.diastolic for point in points]
    pulse = [point.pulse for point in points]
    return ChartPoint(
        timestamp=points[0].timestamp,
        systolic=median(systolic),
        diastolic=median(diastolic),
        pulse=median(pulse),
        systolic_min=min(systolic),
        systolic_max=max(systolic),
        diastolic_min=min(diastolic),
        diastolic_max=max(diastolic),
        pulse_min=min(pulse),
        pulse_max=max(pulse),
    )


def build_statistics_report(
    rows: Iterable[tuple],
    *,
    days: int,
    daily_aggregation: bool,
) -> StatisticsReport:
    """Build raw weekly or daily-aggregated monthly statistics."""
    measurements = rows_to_measurements(rows)
    if daily_aggregation:
        grouped: dict[datetime.date, list[MeasurementPoint]] = {}
        for point in measurements:
            grouped.setdefault(point.timestamp.date(), []).append(point)
        chart_points = [
            _as_chart_point(grouped[day])
            for day in sorted(grouped)
        ]
    else:
        chart_points = [_as_chart_point([point]) for point in measurements]
    return StatisticsReport(
        measurements=measurements,
        chart_points=chart_points,
        days=days,
        daily_aggregation=daily_aggregation,
    )


def format_statistics_caption(report: StatisticsReport) -> str:
    """Return a compact Russian caption for a Telegram photo."""
    start = report.measurements[0].timestamp.strftime("%d.%m.%Y")
    end = report.measurements[-1].timestamp.strftime("%d.%m.%Y")
    aggregation = "Дневные медианы" if report.daily_aggregation else "Все измерения"
    return (
        f"📊 Сводка за {report.days} дней\n"
        f"Период: {start}–{end}\n"
        f"Измерений: {report.count}\n"
        f"Медианное АД: {report.median_systolic:g}/{report.median_diastolic:g}\n"
        f"Медианный пульс: {report.median_pulse:g}\n"
        f"{aggregation}\n\n"
        "График носит информационный характер и не заменяет консультацию врача."
    )
