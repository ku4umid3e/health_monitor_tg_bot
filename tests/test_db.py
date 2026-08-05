def test_init_db_creates_tables(temp_db):
    from app import db
    with db.UseDB(db.db_name) as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
    assert {"Users", "ArmLocation", "BodyPositions", "Comments", "Measurements", "MeasureDetails", "WellBeing"}.issubset(tables)


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


def test_check_db_exists_upgrades_existing_database(temp_db):
    """Startup must apply new migrations even when Users already exists."""
    from app import db

    with db.UseDB(db.db_name) as cursor:
        cursor.execute("DROP TABLE MedicationIntakes")
        cursor.execute("DROP TABLE Medications")
        cursor.execute(
            "UPDATE alembic_version SET version_num = ?",
            ("c0a6d4e91b72",),
        )

    db.check_db_exists()

    with db.UseDB(db.db_name) as cursor:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name IN ('Medications', 'MedicationIntakes')"
        )
        tables = {row[0] for row in cursor.fetchall()}

    assert tables == {"Medications", "MedicationIntakes"}


def test_check_db_exists_upgrades_legacy_unversioned_database(temp_db):
    """Pre-Alembic volumes must be adopted without recreating existing tables."""
    from app import db

    with db.UseDB(db.db_name) as cursor:
        cursor.execute("DROP TABLE MedicationIntakes")
        cursor.execute("DROP TABLE Medications")
        cursor.execute("DROP TABLE alembic_version")

    db.check_db_exists()

    with db.UseDB(db.db_name) as cursor:
        cursor.execute("SELECT version_num FROM alembic_version")
        assert cursor.fetchone()[0] == "d47a8e2f6c31"
        cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' "
            "AND name IN ('Medications', 'MedicationIntakes')"
        )
        assert cursor.fetchone()[0] == 2
