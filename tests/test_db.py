def test_init_db_creates_tables(temp_db):
    from app import db
    with db.UseDB(db.db_name) as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
    assert {"Users", "ArmLocation", "BodyPositions", "Comments", "Measurements", "MeasureDetails"}.issubset(tables)


def test_insert_and_get_user(temp_db):
    from app import db

    class EU:
        id = 111
        first_name = "A"
        last_name = "B"
        username = "ab"

    user = db.get_user(EU)
    assert user["UserID"] > 0
    assert user["TelegramId"] == 111

    # second call should fetch existing
    user2 = db.get_user(EU)
    assert user2["UserID"] == user["UserID"]
