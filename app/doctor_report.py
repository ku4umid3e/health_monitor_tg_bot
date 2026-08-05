"""Generate a printable 90-day measurement report for a doctor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
import textwrap
from zoneinfo import ZoneInfo

from health_statistics import build_statistics_report


MOSCOW_TZ = ZoneInfo("Europe/Moscow")


@dataclass(frozen=True)
class DoctorReportRow:
    """One measurement formatted for the doctor's table."""

    timestamp: datetime
    systolic: int
    diastolic: int
    pulse: int
    wellbeing: str
    comment: str


@dataclass(frozen=True)
class MedicationReportRow:
    """One medication event formatted for the doctor's report."""

    timestamp: datetime
    name: str
    dose: str
    status: str
    comment: str


def utc_to_moscow(value: str | datetime) -> datetime:
    """Interpret stored SQLite timestamps as UTC and convert them to MSK."""
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(MOSCOW_TZ)


def prepare_report_rows(rows: list[tuple]) -> list[DoctorReportRow]:
    """Convert repository tuples to chronological, typed report rows."""
    result = [
        DoctorReportRow(
            timestamp=utc_to_moscow(row[1]),
            systolic=int(row[2]),
            diastolic=int(row[3]),
            pulse=int(row[4]),
            comment=str(row[7] or "—"),
            wellbeing=str(row[8] or "Не указано"),
        )
        for row in rows
    ]
    return sorted(result, key=lambda item: item.timestamp)


def prepare_medication_rows(rows: list[tuple]) -> list[MedicationReportRow]:
    """Convert medication repository tuples to chronological MSK events."""
    result = [
        MedicationReportRow(
            timestamp=utc_to_moscow(row[3]),
            name=str(row[1]),
            dose=str(row[2] or "—"),
            status=str(row[4]),
            comment=str(row[5] or "—"),
        )
        for row in rows
    ]
    return sorted(result, key=lambda item: item.timestamp)


def _wrap(value: str, width: int) -> str:
    return "\n".join(textwrap.wrap(value, width=width) or ["—"])


def _recent_medications(
    measurement: DoctorReportRow,
    medication_items: list[MedicationReportRow],
) -> str:
    """Describe medications taken during the 24 hours before a measurement."""
    descriptions = []
    for medication in medication_items:
        seconds = (measurement.timestamp - medication.timestamp).total_seconds()
        if medication.status != "taken" or not 0 <= seconds <= 24 * 60 * 60:
            continue
        hours, remainder = divmod(int(seconds), 3600)
        minutes = remainder // 60
        dose = f" {medication.dose}" if medication.dose != "—" else ""
        descriptions.append(f"{medication.name}{dose} — {hours} ч {minutes} мин назад")
    return "; ".join(descriptions) or "—"


def _table_rows(
    items: list[DoctorReportRow],
    medication_items: list[MedicationReportRow] | None = None,
) -> list[list[str]]:
    """Build table rows, splitting long comments without dropping text."""
    result: list[list[str]] = []
    medication_items = medication_items or []
    for item in items:
        comment_lines = textwrap.wrap(item.comment, width=42) or ["—"]
        medication_text = _recent_medications(item, medication_items)
        combined_lines = textwrap.wrap(medication_text, width=28) or ["—"]
        line_count = max(len(comment_lines), len(combined_lines))
        chunks = range(0, line_count, 3)
        for chunk_index, start in enumerate(chunks):
            if chunk_index == 0:
                prefix = [
                    item.timestamp.strftime("%d.%m.%Y"),
                    item.timestamp.strftime("%H:%M"),
                    f"{item.systolic}/{item.diastolic}",
                    str(item.pulse),
                    _wrap(item.wellbeing, 12),
                ]
            else:
                prefix = ["", "", "", "", ""]
            result.append([
                *prefix,
                "\n".join(combined_lines[start:start + 3]),
                "\n".join(comment_lines[start:start + 3]),
            ])
    return result


def render_doctor_report(
    rows: list[tuple],
    medication_rows: list[tuple] | None = None,
    *,
    days: int = 90,
) -> BytesIO:
    """Render chart, summary and full measurement table to an in-memory PDF."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    prepared = prepare_report_rows(rows)
    medications = prepare_medication_rows(medication_rows or [])
    if not prepared:
        raise ValueError("Cannot render an empty doctor report")

    # Aggregate by Moscow calendar day, not by the stored UTC date.
    localized_rows = [
        (row[0], utc_to_moscow(row[1]), *row[2:])
        for row in rows
    ]
    statistics = build_statistics_report(
        localized_rows, days=days, daily_aggregation=True,
    )
    output = BytesIO()
    output.name = f"doctor_report_{prepared[0].timestamp:%Y-%m-%d}_{prepared[-1].timestamp:%Y-%m-%d}.pdf"

    with PdfPages(output, metadata={"Title": "Отчёт об артериальном давлении"}) as pdf:
        figure, (pressure_axis, pulse_axis) = plt.subplots(
            2, 1, figsize=(11.69, 8.27), sharex=True, constrained_layout=True,
        )
        chart_times = [point.timestamp for point in statistics.chart_points]
        pressure_axis.plot(
            chart_times,
            [point.systolic for point in statistics.chart_points],
            "o-", label="Систолическое", color="#d62728",
        )
        pressure_axis.plot(
            chart_times,
            [point.diastolic for point in statistics.chart_points],
            "o-", label="Диастолическое", color="#1f77b4",
        )
        pulse_axis.plot(
            chart_times,
            [point.pulse for point in statistics.chart_points],
            "o-", label="Пульс", color="#2ca02c",
        )
        if medications:
            marker_y = max(point.pulse for point in statistics.chart_points) + 3
            visible_medications = [
                item for item in medications
                if prepared[0].timestamp <= item.timestamp <= prepared[-1].timestamp
                and item.status == "taken"
            ]
            pulse_axis.scatter(
                [item.timestamp for item in visible_medications],
                [marker_y] * len(visible_medications),
                marker="v", color="#9467bd", label="Приём лекарства", zorder=5,
            )
        pressure_axis.set_title(
            "Отчёт для врача за 90 дней\n"
            f"Период: {prepared[0].timestamp:%d.%m.%Y}–{prepared[-1].timestamp:%d.%m.%Y}; "
            f"измерений: {len(prepared)}; медианное АД: "
            f"{statistics.median_systolic:g}/{statistics.median_diastolic:g}; "
            f"медианный пульс: {statistics.median_pulse:g}"
        )
        pressure_axis.set_ylabel("мм рт. ст.")
        pulse_axis.set_ylabel("уд/мин")
        pulse_axis.set_xlabel("Дата и время (MSK)")
        pressure_axis.legend(loc="best")
        pulse_axis.legend(loc="best")
        pressure_axis.grid(alpha=0.25)
        pulse_axis.grid(alpha=0.25)
        locator = mdates.AutoDateLocator(minticks=3, maxticks=12)
        pulse_axis.xaxis.set_major_locator(locator)
        pulse_axis.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        figure.text(
            0.5, 0.005,
            "График показывает дневные медианы и носит информационный характер.",
            ha="center", fontsize=8,
        )
        pdf.savefig(figure)
        plt.close(figure)

        all_table_rows = _table_rows(prepared, medications)
        page_size = 14
        for offset in range(0, len(all_table_rows), page_size):
            page_rows = all_table_rows[offset:offset + page_size]
            figure, axis = plt.subplots(figsize=(11.69, 8.27))
            axis.axis("off")
            axis.set_title(
                "Все измерения (время MSK)", loc="left", fontsize=13, pad=12,
            )
            table = axis.table(
                cellText=page_rows,
                colLabels=["Дата", "Время", "АД", "Пульс", "Самочувствие", "Лекарства за 24 ч", "Комментарий"],
                colWidths=[0.09, 0.06, 0.08, 0.06, 0.11, 0.25, 0.35],
                cellLoc="left", colLoc="left", loc="upper center",
            )
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.scale(1, 1.75)
            for (row_index, _), cell in table.get_celld().items():
                if row_index == 0:
                    cell.set_facecolor("#dbe8f4")
                    cell.set_text_props(weight="bold")
                elif row_index % 2 == 0:
                    cell.set_facecolor("#f5f5f5")
            figure.text(
                0.98, 0.02,
                f"Страница записей {offset // page_size + 1}",
                ha="right", fontsize=8,
            )
            pdf.savefig(figure, bbox_inches="tight")
            plt.close(figure)

        if medications:
            medication_table_rows = []
            status_labels = {"taken": "Принят", "skipped": "Пропущен"}
            for item in medications:
                comment_lines = textwrap.wrap(item.comment, width=55) or ["—"]
                for index in range(0, len(comment_lines), 3):
                    first = index == 0
                    medication_table_rows.append([
                        item.timestamp.strftime("%d.%m.%Y") if first else "",
                        item.timestamp.strftime("%H:%M") if first else "",
                        item.name if first else "",
                        item.dose if first else "",
                        status_labels.get(item.status, item.status) if first else "",
                        "\n".join(comment_lines[index:index + 3]),
                    ])
            for offset in range(0, len(medication_table_rows), page_size):
                figure, axis = plt.subplots(figsize=(11.69, 8.27))
                axis.axis("off")
                axis.set_title("Приёмы лекарств (время MSK)", loc="left", fontsize=13, pad=12)
                table = axis.table(
                    cellText=medication_table_rows[offset:offset + page_size],
                    colLabels=["Дата", "Время", "Лекарство", "Доза", "Статус", "Комментарий"],
                    colWidths=[0.11, 0.08, 0.20, 0.12, 0.12, 0.37],
                    cellLoc="left", colLoc="left", loc="upper center",
                )
                table.auto_set_font_size(False)
                table.set_fontsize(8)
                table.scale(1, 1.75)
                for (row_index, _), cell in table.get_celld().items():
                    if row_index == 0:
                        cell.set_facecolor("#e6dcef")
                        cell.set_text_props(weight="bold")
                    elif row_index % 2 == 0:
                        cell.set_facecolor("#f5f5f5")
                pdf.savefig(figure, bbox_inches="tight")
                plt.close(figure)

    output.seek(0)
    return output
