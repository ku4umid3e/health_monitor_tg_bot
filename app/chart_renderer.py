"""Render health statistics as PNG images for Telegram."""

from __future__ import annotations

from io import BytesIO

try:
    from .health_statistics import StatisticsReport
except ImportError:  # Direct execution with PYTHONPATH=app
    from health_statistics import StatisticsReport


def render_statistics_chart(report: StatisticsReport) -> BytesIO:
    """Render blood pressure and pulse panels into an in-memory PNG."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    timestamps = [point.timestamp for point in report.chart_points]
    systolic = [point.systolic for point in report.chart_points]
    diastolic = [point.diastolic for point in report.chart_points]
    pulse = [point.pulse for point in report.chart_points]

    figure, (pressure_axis, pulse_axis) = plt.subplots(
        2, 1, figsize=(10, 7), sharex=True, constrained_layout=True,
    )
    pressure_axis.plot(timestamps, systolic, "o-", label="Систолическое", color="#d62728")
    pressure_axis.plot(timestamps, diastolic, "o-", label="Диастолическое", color="#1f77b4")
    pulse_axis.plot(timestamps, pulse, "o-", label="Пульс", color="#2ca02c")

    if report.daily_aggregation:
        pressure_axis.fill_between(
            timestamps,
            [point.systolic_min for point in report.chart_points],
            [point.systolic_max for point in report.chart_points],
            color="#d62728",
            alpha=0.12,
        )
        pressure_axis.fill_between(
            timestamps,
            [point.diastolic_min for point in report.chart_points],
            [point.diastolic_max for point in report.chart_points],
            color="#1f77b4",
            alpha=0.12,
        )
        pulse_axis.fill_between(
            timestamps,
            [point.pulse_min for point in report.chart_points],
            [point.pulse_max for point in report.chart_points],
            color="#2ca02c",
            alpha=0.12,
        )

    pressure_axis.set_title(f"Измерения за {report.days} дней")
    pressure_axis.set_ylabel("мм рт. ст.")
    pulse_axis.set_ylabel("уд/мин")
    pulse_axis.set_xlabel("Дата")
    pressure_axis.legend(loc="best")
    pulse_axis.legend(loc="best")
    pressure_axis.grid(alpha=0.25)
    pulse_axis.grid(alpha=0.25)

    locator = mdates.AutoDateLocator(minticks=3, maxticks=10)
    pulse_axis.xaxis.set_major_locator(locator)
    pulse_axis.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))

    image = BytesIO()
    image.name = f"statistics_{report.days}_days.png"
    figure.savefig(image, format="png", dpi=140)
    plt.close(figure)
    image.seek(0)
    return image
