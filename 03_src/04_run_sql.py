from pathlib import Path
import sqlite3
import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATABASE_PATH = (
    PROJECT_ROOT
    / "04_sql"
    / "business_intelligence.db"
)

SQL_FILE = (
    PROJECT_ROOT
    / "04_sql"
    / "analysis_queries.sql"
)


# ============================================================
# 2. CONNECT TO DATABASE
# ============================================================

connection = sqlite3.connect(DATABASE_PATH)

print("=" * 70)
print("DATABASE CONNECTED")
print("=" * 70)


# ============================================================
# 3. READ SQL FILE
# ============================================================

with open(SQL_FILE, "r", encoding="utf-8") as file:
    sql_script = file.read()


# ============================================================
# 4. SPLIT SQL SCRIPT INTO QUERIES
# ============================================================

queries = [
    query.strip()
    for query in sql_script.split(";")
    if query.strip()
]


print("\nTotal SQL queries:", len(queries))


# ============================================================
# 5. EXECUTE EACH QUERY
# ============================================================

for query_number, query in enumerate(queries, start=1):

    print("\n" + "=" * 70)
    print(f"QUERY {query_number}")
    print("=" * 70)

    try:

        result = pd.read_sql_query(
            query,
            connection
        )

        print(result.to_string(index=False))

    except Exception as error:

        print("ERROR:")
        print(error)


# ============================================================
# 6. CLOSE DATABASE
# ============================================================

connection.close()

print("\n" + "=" * 70)
print("SQL ANALYSIS COMPLETE")
print("=" * 70)