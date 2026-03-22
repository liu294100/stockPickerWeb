import os
import sqlite3
from typing import Any


class StockStore:
    def __init__(self):
        data_dir = os.path.join(os.getcwd(), "data")
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = os.path.join(data_dir, "stocks.db")
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stocks (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    industry TEXT NOT NULL,
                    market TEXT NOT NULL,
                    watchlist INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def count(self):
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(1) AS c FROM stocks").fetchone()
            return int(row["c"] if row else 0)

    def bulk_seed(self, rows: list[dict[str, Any]]):
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO stocks(code, name, industry, market, watchlist)
                VALUES(:code, :name, :industry, :market, :watchlist)
                """,
                rows,
            )
            conn.commit()

    def list_stocks(self, market: str | None = None, watchlist_only: bool = False):
        sql = "SELECT code, name, industry, market, watchlist FROM stocks WHERE 1=1"
        params = []
        if market and market != "ALL":
            sql += " AND market = ?"
            params.append(market)
        if watchlist_only:
            sql += " AND watchlist = 1"
        sql += " ORDER BY market, code"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def get_stock(self, code: str):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT code, name, industry, market, watchlist FROM stocks WHERE code = ?",
                (code,),
            ).fetchone()
            return dict(row) if row else None

    def upsert_stock(self, code: str, name: str, industry: str, market: str, watchlist: bool = True):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO stocks(code, name, industry, market, watchlist, updated_at)
                VALUES(?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(code) DO UPDATE SET
                    name = excluded.name,
                    industry = excluded.industry,
                    market = excluded.market,
                    watchlist = excluded.watchlist,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (code, name, industry, market, 1 if watchlist else 0),
            )
            conn.commit()

    def patch_stock(self, code: str, payload: dict[str, Any]):
        target = self.get_stock(code)
        if not target:
            return None
        merged = {
            "name": payload.get("name", target["name"]),
            "industry": payload.get("industry", target["industry"]),
            "market": payload.get("market", target["market"]),
            "watchlist": 1 if payload.get("watchlist", bool(target["watchlist"])) else 0,
        }
        self.upsert_stock(code, merged["name"], merged["industry"], merged["market"], bool(merged["watchlist"]))
        return self.get_stock(code)

    def delete_stock(self, code: str):
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM stocks WHERE code = ?", (code,))
            conn.commit()
            return cur.rowcount > 0

    def set_watchlist(self, code: str, watchlist: bool):
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE stocks SET watchlist = ?, updated_at = CURRENT_TIMESTAMP WHERE code = ?",
                (1 if watchlist else 0, code),
            )
            conn.commit()
            return cur.rowcount > 0
