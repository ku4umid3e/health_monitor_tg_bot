import sqlite3
from datetime import datetime, timedelta
import random


db_path = "./app/data/measurements.db"
user_id =1

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("DELETE FROM MeasureDetails")
cur.execute("DELETE FROM Measurements")
cur.execute("DELETE FROM Comments")
conn.commit()

for days_ago in range(35):
    date = datetime.now() - timedelta(days=days_ago)

    hour_morning = random.randint(8, 10)
    minute_morning = random.randint(0, 59)
    ts_morning = date.replace(hour=hour_morning, minute=minute_morning, second=0, microsecond=0)

    hour_evening = random.randint(18, 22)
    minute_evening = random.randint(0, 59)
    ts_evening = date.replace(hour=hour_evening, minute=minute_evening, second=0, microsecond=0)

    for ts in [ts_morning, ts_evening]:
        arm = random.randint(1, 5)
        pos = random.randint(1, 5)
        sys = random.randint(110, 140)
        dia = random.randint(70, 90)
        pulse = random.randint(60, 90)
        comment = f"Тестовый комментарий {ts.strftime('%Y-%m-%d %H:%M')}"
        cur.execute("INSERT INTO Comments (CommentText) VALUES (?)", (comment,))
        comment_id = cur.lastrowid
        cur.execute(
            "INSERT INTO Measurements (UserID, ArmLocationID, BodyPositionID, CommentID, Timestamp) VALUES (?, ?, ?, ?, ?)",
            (user_id, arm, pos, comment_id, ts.strftime("%Y-%m-%d %H:%M:%S"))
        )
        measurement_id = cur.lastrowid
        cur.execute(
            "INSERT INTO MeasureDetails (MeasurementID, SystolicPressure, DiastolicPressure, Pulse) VALUES (?, ?, ?, ?)",
            (measurement_id, sys, dia, pulse)
        )

conn.commit()
conn.close()
print("Тестовые данные успешно добавлены: по 2 измерения в день за 30 дней.")