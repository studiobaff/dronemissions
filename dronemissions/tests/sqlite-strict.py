"""Compile flight-log SQL with SQLite double-quoted strings disabled, as in production."""
import re
import sqlite3
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "public"
db = sqlite3.connect(":memory:")
db.setconfig(sqlite3.SQLITE_DBCONFIG_DQS_DDL, False)
db.setconfig(sqlite3.SQLITE_DBCONFIG_DQS_DML, False)
db.executescript("CREATE TABLE folders(id TEXT); CREATE TABLE missions(id TEXT,folder TEXT,name TEXT); CREATE TABLE versions(id TEXT,mission TEXT,details TEXT);")
statements = []
for name in ("flight-logs.php", "dji-cloud.php"):
    source = (root / name).read_text(encoding="utf-8")
    for match in re.finditer(r"(?:exec|stmt)\('((?:\\.|[^'\\])*)'", source):
        sql = match[1].replace("\\'", "'").replace("\\\\", "\\")
        if sql.startswith("CREATE "):
            db.executescript(sql)
        else:
            statements.append(sql)
for sql in statements:
    db.execute("EXPLAIN " + sql, [None] * sql.count("?"))
print(f"PASS: strict SQLite schema and {len(statements)} flight-log queries")
