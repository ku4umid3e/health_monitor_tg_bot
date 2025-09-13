from typing import List, Tuple, Dict
import logging
import sqlite3

from logging_config import configure_logging
import os


configure_logging()
logger = logging.getLogger(__name__)
db_name = "/app/data/measurements.db"


class ConnectionError(Exception):
    pass


class UseDB:
    """Context manager for SQLite database access.

    Opens a connection to the configured SQLite database on entry and
    commits and closes it on exit. Provides a cursor for executing SQL
    statements within the context block.
    """
    def __init__(self, conf) -> None:
        self.config = conf

    def __enter__(self) -> sqlite3.Cursor:
        """Open a database connection and return a cursor."""
        try:
            self.conn = sqlite3.connect(self.config)
            self.cursor = self.conn.cursor()
            return self.cursor
        except sqlite3.Error as err:
            logger.error(f"ERROR:{err}")
            raise ConnectionError(err)

    def __exit__(self, exc_type, exc_value, exc_trace) -> None:
        self.conn.commit()
        self.cursor.close()
        self.conn.close()


def get_user(effective_user):
    """Return user record by Telegram user; create it if missing."""
    logger.info(f"get_user {type(effective_user)}:{effective_user}")
    sql_select = """
        SELECT UserID, First_name, Last_name, Username, TelegramId FROM Users WHERE TelegramId =?
        """
    with UseDB(db_name) as cursor:
        cursor.execute(sql_select, (effective_user.id,))
        user = cursor.fetchall()
    if not user:
        logger.info(f"No user found for {effective_user.id}")
        return create_user(effective_user)
    key = ['UserID', 'First_name', 'Last_name', 'Username', 'TelegramId']
    user = dict(zip(key, user[0]))
    logger.info(f'Reqest in db = {user}')
    return user


def create_user(effective_user):
    """Insert a new user based on Telegram's effective_user and return dict."""
    user = {
                "TelegramId": effective_user.id,
                "First_name": effective_user.first_name,
                "Last_name": effective_user.last_name,
                "Username": effective_user.username,
            }
    user_id = insert('Users', user)
    logger.info(f"Inserted user {effective_user.id} with id {user_id}")
    user["UserID"] = user_id
    return user


def delete(table: str, row_id: int) -> None:
    """
    Deletes a row from the specified table based on the provided row ID.

    This function constructs and executes a SQL DELETE query to remove a row
    from the specified database table based on the given row ID.

    Args:
    table (str): The name of the table from which to delete the row.
    row_id (int): The unique identifier of the row to be deleted.

    Example:
    >>> delete("Measurements", 123)

    Note:
    - Ensure the connection (conn) and cursor (cursor) are initialized before calling this function.
    - Commit the changes to the database after calling this function.

    Raises:
    sqlite3.Error: If there is an error during the SQL execution.
    """
    row_id = int(row_id)
    with UseDB(db_name) as cursor:
        cursor.execute(f"DELETE FROM {table} WHERE id={row_id}")


def insert(table: str, column_values: Dict) -> int:
    """
    Inserts a new row into the specified table with the given column values.

    This function constructs and executes a SQL INSERT query to add a new row
    to the specified database table. It takes a dictionary of column-value pairs,
    where keys are column names and values are the corresponding values for the new row.

    Args:
    table (str): The name of the table to insert the new row into.
    column_values (Dict): A dictionary representing column-value pairs for the new row.

    Example:
    >>> insert("users", {"name": "Alice", "telegramId": "123456789"})

    Note:
    - Ensure the keys in the column_values dictionary match the columns in the table.
    - The connection (conn) and cursor (cursor) should be initialized before calling this function.
    - Commit the changes to the database after calling this function.

    Raises:
    sqlite3.Error: If there is an error during the SQL execution.

    """
    columns = ', '.join(column_values.keys())
    values = tuple(column_values.values())
    placeholders = ", ".join("?" * len(column_values.keys()))
    with UseDB(db_name) as cursor:
        cursor.execute(
            f"INSERT INTO {table} "
            f"({columns}) "
            f"VALUES ({placeholders})",
            values)
        return cursor.lastrowid


def fetchall(table: str, columns: List[str]) -> List[Tuple]:
    """
    Fetches all rows from a specified table with specified columns.

    This function executes a SQL SELECT query to fetch all rows from the specified
    database table, considering the provided list of columns. It then transforms the
    result into a list of dictionaries, where each dictionary represents a row with
    column names as keys and corresponding values.

    Args:
    table (str): The name of the table to fetch data from.
    columns (List[str]): A list of column names to include in the SELECT query.

    Returns:
    List[Tuple]: A list of tuples, where each tuple represents a row from the table.
                Each tuple contains values for the specified columns.

    Example:
    >>> fetchall("users", ["id", "name", "telegramId"])
    [(1, 'John Doe', '123456789'), (2, 'Jane Doe', '213456789'), ...]
    """
    columns_joined = ", ".join(columns)
    with UseDB(db_name) as cursor:
        cursor.execute(f"SELECT {columns_joined} FROM {table}")
        rows = cursor.fetchall()
        result = []
        for row in rows:
            dict_row = {}
            for index, column in enumerate(columns):
                dict_row[column] = row[index]
            result.append(dict_row)
    return result


def _init_db() -> None:
    """
    This function reads SQL commands from the 'createdb.sql' file and executes them
    using the SQLite cursor to initialize the database with necessary tables and schema.
    """
    base_dir = os.path.dirname(__file__)
    schema_path = os.path.join(base_dir, "createdb.sql")
    with open(schema_path, "r") as f:
        sql = f.read()
    with UseDB(db_name) as cursor:
        cursor.executescript(sql)


def check_db_exists():
    """
    This function executes a SQL SELECT query to check if a table named 'Users' exists
    in the database. If the table is found, the function returns without taking any action.
    If the table does not exist, it calls the '_init_db()' function to initialize the database.
    """
    logger.info("Check db")
    with UseDB(db_name) as cursor:
        cursor.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='Users'"
        )
        table_exists = cursor.fetchall()
        if table_exists:
            return
        logger.info("Init db")
        _init_db()


check_db_exists()
