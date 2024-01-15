import os
from typing import List, Tuple, Dict

import sqlite3


conn = sqlite3.connect(os.path.join("db", "measurements.db"))
cursor = conn.cursor()


def get_user():
    pass


def get_cursor() -> sqlite3.Cursor:
    """
    Returns the SQLite cursor.

    This function retrieves and returns the SQLite cursor, allowing you to
    perform SQL queries and operations directly on the database.

    Note:
    - Ensure the connection (conn) and cursor (cursor) are initialized before calling this function.

    Returns:
    sqlite3.Cursor: The SQLite cursor object.

    Example:
    >>> cursor = get_cursor()
    >>> cursor.execute("SELECT * FROM Measurements")
    >>> rows = cursor.fetchall()

    Raises:
    sqlite3.Error: If there is an error during the SQL execution.
    """
    return cursor


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
    cursor.execute(f"DELETE FROM {table} WHERE id={row_id}")
    conn.commit()


def insert(table: str, column_values: Dict):
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
    values = [tuple(column_values.values())]
    placeholders = ", ".join("?" * len(column_values.keys()))
    cursor.executemany(
        f"INSERT INTO {table} "
        f"({columns}) "
        f"VALUES ({placeholders})",
        values)
    conn.commit()


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
    Initializes the database by executing SQL commands from the 'createdb.sql' file.

    This function reads SQL commands from the 'createdb.sql' file and executes them
    using the SQLite cursor to initialize the database with necessary tables and schema.

    Note:
    - Ensure the connection (conn) and cursor (cursor) are initialized before calling this function.

    Example:
    >>> _init_db()

    Raises:
    sqlite3.Error: If there is an error during the SQL execution.
    FileNotFoundError: If the 'createdb.sql' file is not found.
    """
    with open("createdb.sql", "r") as f:
        sql = f.read()
    cursor.executescript(sql)
    conn.commit()


def check_db_exists():
    """
    Checks if the 'expense' table exists in the database.

    This function executes a SQL SELECT query to check if a table named 'expense' exists
    in the database. If the table is found, the function returns without taking any action.
    If the table does not exist, it calls the '_init_db()' function to initialize the database.

    Note:
    - Ensure the connection (conn) and cursor (cursor) are initialized before calling this function.
    - '_init_db()' is assumed to be a function responsible for creating the necessary tables.

    Example:
    >>> check_db_exists()

    Raises:
    sqlite3.Error: If there is an error during the SQL execution.
    """
    cursor.execute("SELECT name FROM sqlite_master "
                   "WHERE type='table' AND name='Users'")
    table_exists = cursor.fetchall()
    if table_exists:
        return
    _init_db()


check_db_exists()
