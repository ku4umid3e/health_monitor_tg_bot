from __future__ import annotations

from typing import Dict, Tuple, Any


def render_last_measurement(row: Tuple[Any, ...]) -> str:
    (
        _id,
        ts,
        sys_p,
        dia_p,
        pulse,
        pos_name,
        arm_name,
        comment_text,
        well_being_name,
    ) = row
    return (
        "Последнее измерение:\n"
        f"Дата/время: {ts}\n"
        f"АД: {sys_p}/{dia_p}, Пульс: {pulse}\n"
        f"Положение: {pos_name or 'Не указано'}, Манжета: {arm_name or 'Не указано'}\n"
        f"Самочувствие: {well_being_name or 'Не указано'}\n"
        f"Комментарий: {comment_text or '—'}"
    )


def render_edit_summary(measurement_data: Dict[str, object]) -> str:
    return (
        "Изменение последнего измерения:\n"
        f"АД: {measurement_data.get('SystolicPressure')}/"
        f"{measurement_data.get('DiastolicPressure')}, "
        f"Пульс: {measurement_data.get('Pulse')}\n"
        f"Положение: {measurement_data.get('PositionName') or 'Не указано'}, "
        f"Манжета: {measurement_data.get('LocationName') or 'Не указано'}\n"
        f"Самочувствие: {measurement_data.get('WellBeing') or 'Не указано'}\n"
        f"Комментарий: {measurement_data.get('Comments') or '—'}"
    )


def render_receipt(draft: Dict[str, object]) -> str:
    comment = draft.get('comment') or '—'
    return (
        'Супер! Я записал измерение:\n'
        f"АД: {draft['pressure'][0]}/{draft['pressure'][1]}, Пульс: {draft['pulse'][0]}\n"
        f"Положение: {draft['body_position']}, Манжета: {draft['arm_location']}\n"
        f"Самочувствие: {draft['well_being']}\n"
        f"Комментарий: {comment}"
    )

