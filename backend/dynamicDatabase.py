import mysql.connector as con
import re

# ================= DATABASE CONNECTION =================
connector = con.connect(
    host='localhost',
    user='root',
    password='Soul#13211993',
    database='govconnect'
)

cursor = connector.cursor(dictionary=True)

# ================= CONFIG =================
ALLOWED_TYPES = {
    "string": "VARCHAR(255)",
    "text": "TEXT",
    "int": "INT",
    "float": "FLOAT",
    "bool": "BOOLEAN",
    "date": "DATE"
}

# ================= HELPERS =================
def is_valid_identifier(name: str) -> bool:
    """Validate SQL identifiers to prevent injection"""
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name))


# ================= METADATA TABLE =================
def setup_metadata_table():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dynamic_table_meta (
            table_name VARCHAR(255),
            field_name VARCHAR(255),
            data_type VARCHAR(50),
            show_ui BOOLEAN,
            PRIMARY KEY (table_name, field_name)
        )
    """)
    connector.commit()


# ================= CREATE DYNAMIC TABLE =================
def create_dynamic_database(
    table_name: str,
    fields: list,
    data_type: list,
    show: list
):
    if not is_valid_identifier(table_name):
        raise ValueError("Invalid table name")

    if not (len(fields) == len(data_type) == len(show)):
        raise ValueError("fields, data_type, show must be same length")

    columns_sql = []

    for f, dt in zip(fields, data_type):
        if not is_valid_identifier(f):
            raise ValueError(f"Invalid field name: {f}")

        if dt not in ALLOWED_TYPES:
            raise ValueError(f"Invalid datatype: {dt}")

        columns_sql.append(f"`{f}` {ALLOWED_TYPES[dt]}")

    create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
            id INT AUTO_INCREMENT PRIMARY KEY,
            {', '.join(columns_sql)},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """

    try:
        cursor.execute(create_table_sql)

        for f, dt, s in zip(fields, data_type, show):
            cursor.execute("""
                INSERT INTO dynamic_table_meta (table_name, field_name, data_type, show_ui)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    data_type = VALUES(data_type),
                    show_ui = VALUES(show_ui)
            """, (table_name, f, dt, bool(s)))

        connector.commit()

    except Exception as e:
        connector.rollback()
        raise e


# ================= INSERT DATA =================
def insert_dynamic_data(table_name: str, data: dict):
    if not is_valid_identifier(table_name):
        raise ValueError("Invalid table name")

    fields = []
    placeholders = []
    values = []

    for k, v in data.items():
        if not is_valid_identifier(k):
            raise ValueError(f"Invalid field name: {k}")

        fields.append(f"`{k}`")
        placeholders.append("%s")
        values.append(v)

    sql = f"""
        INSERT INTO `{table_name}` ({', '.join(fields)})
        VALUES ({', '.join(placeholders)})
    """

    cursor.execute(sql, values)
    connector.commit()


# ================= FETCH DATA =================
def fetch_dynamic_data(table_name: str, ui_only=True):
    if not is_valid_identifier(table_name):
        raise ValueError("Invalid table name")

    if ui_only:
        cursor.execute("""
            SELECT field_name FROM dynamic_table_meta
            WHERE table_name=%s AND show_ui=TRUE
        """, (table_name,))
    else:
        cursor.execute("""
            SELECT field_name FROM dynamic_table_meta
            WHERE table_name=%s
        """, (table_name,))

    fields = [row["field_name"] for row in cursor.fetchall()]
    if not fields:
        return []

    sql = f"SELECT id, {', '.join(fields)} FROM `{table_name}`"
    cursor.execute(sql)
    return cursor.fetchall()


# ================= UPDATE DATA =================
def update_dynamic_data(table_name: str, record_id: int, data: dict):
    if not is_valid_identifier(table_name):
        raise ValueError("Invalid table name")

    if not data:
        raise ValueError("No data provided for update")

    set_parts = []
    values = []

    for k, v in data.items():
        if not is_valid_identifier(k):
            raise ValueError(f"Invalid field name: {k}")

        set_parts.append(f"`{k}` = %s")
        values.append(v)

    values.append(record_id)

    sql = f"""
        UPDATE `{table_name}`
        SET {', '.join(set_parts)}
        WHERE id = %s
    """

    cursor.execute(sql, values)
    connector.commit()

    if cursor.rowcount == 0:
        raise ValueError(f"Record with id {record_id} not found in table {table_name}")


# ================= DELETE DATA =================
def delete_dynamic_data(table_name: str, record_id: int):
    if not is_valid_identifier(table_name):
        raise ValueError("Invalid table name")

    sql = f"DELETE FROM `{table_name}` WHERE id = %s"
    cursor.execute(sql, (record_id,))
    connector.commit()

    if cursor.rowcount == 0:
        raise ValueError(f"Record with id {record_id} not found in table {table_name}")


# ================= DELETE FIELD =================
def delete_dynamic_field(table_name: str, field_name: str):
    if not is_valid_identifier(table_name):
        raise ValueError("Invalid table name")

    if not is_valid_identifier(field_name):
        raise ValueError("Invalid field name")

    try:
        # Remove field from metadata
        cursor.execute("""
            DELETE FROM dynamic_table_meta
            WHERE table_name = %s AND field_name = %s
        """, (table_name, field_name))

        # Drop column from table
        sql = f"ALTER TABLE `{table_name}` DROP COLUMN `{field_name}`"
        cursor.execute(sql)

        connector.commit()

    except Exception as e:
        connector.rollback()
        raise e


# ================= DELETE TABLE =================
def delete_dynamic_table(table_name: str):
    if not is_valid_identifier(table_name):
        raise ValueError("Invalid table name")

    try:
        # Remove metadata entries
        cursor.execute("""
            DELETE FROM dynamic_table_meta
            WHERE table_name = %s
        """, (table_name,))

        # Drop the table
        sql = f"DROP TABLE IF EXISTS `{table_name}`"
        cursor.execute(sql)

        connector.commit()

    except Exception as e:
        connector.rollback()
        raise e


# ================= EXAMPLE USAGE =================
if __name__ == "__main__":
    setup_metadata_table()

    create_dynamic_database(
        table_name="citizen_records",
        fields=["name", "age", "disease", "visit_date"],
        data_type=["string", "int", "text", "date"],
        show=[True, True, False, True]
    )

    insert_dynamic_data("citizen_records", {
        "name": "Ramesh",
        "age": 45,
        "disease": "Hypertension",
        "visit_date": "2026-01-15"
    })

    print("UI DATA:")
    print(fetch_dynamic_data("citizen_records", ui_only=True))

    print("FULL DATA:")
    print(fetch_dynamic_data("citizen_records", ui_only=False))
