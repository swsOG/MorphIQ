"""
Safely delete stale/test clients from portal.db (manual cascade; no hardcoded tables).

Usage:
  python admin_delete_client.py "Client1" "Test Client" "Testing" "Client 5"
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

# Deploy root: same directory as this script (no hardcoded drive/path).
BASE = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE / "portal.db"


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def list_user_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )
    return [r[0] for r in cur.fetchall()]


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({quote_ident(table)})")
    return {row[1] for row in cur.fetchall()}


def fk_list(conn: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    cur = conn.execute(f"PRAGMA foreign_key_list({quote_ident(table)})")
    return cur.fetchall()


def tables_referencing_clients_via_client_id(conn: sqlite3.Connection) -> set[str]:
    """Tables with a declared FK: client_id -> clients.id."""
    found: set[str] = set()
    for table in list_user_tables(conn):
        for fk in fk_list(conn, table):
            if fk["from"] == "client_id" and fk["table"] == "clients":
                found.add(table)
    return found


def tables_with_client_id_column(conn: sqlite3.Connection) -> set[str]:
    """Any user table (except clients) that has a client_id column."""
    out: set[str] = set()
    for table in list_user_tables(conn):
        if table == "clients":
            continue
        cols = table_columns(conn, table)
        if "client_id" in cols:
            out.add(table)
    return out


def document_child_tables(conn: sqlite3.Connection) -> set[str]:
    """
    Tables that reference documents but do not carry client_id (e.g. document_fields).
    Declared FKs: document_id -> documents.
    """
    out: set[str] = set()
    if "documents" not in list_user_tables(conn):
        return out
    for table in list_user_tables(conn):
        if table == "clients":
            continue
        cols = table_columns(conn, table)
        if "client_id" in cols:
            continue
        for fk in fk_list(conn, table):
            if fk["from"] == "document_id" and fk["table"] == "documents":
                out.add(table)
    return out


def deletion_nodes(conn: sqlite3.Connection) -> set[str]:
    """Tables to clear before removing the clients row (schema-derived, no hardcoded names)."""
    return (
        tables_with_client_id_column(conn)
        | document_child_tables(conn)
        | tables_referencing_clients_via_client_id(conn)
    ) - {"clients"}


def build_delete_edges(conn: sqlite3.Connection, nodes: set[str]) -> list[tuple[str, str]]:
    """
    Edges (child, parent): child rows must be deleted before parent rows
    for FKs that do not reference clients directly.
    """
    edges: list[tuple[str, str]] = []
    expanded = nodes | {"documents", "properties"}
    for child in nodes:
        for fk in fk_list(conn, child):
            parent = fk["table"]
            if parent == "clients":
                continue
            if parent not in expanded:
                continue
            edges.append((child, parent))
    return edges


def topological_delete_order(nodes: set[str], edges: list[tuple[str, str]]) -> list[str]:
    """
    Order tables so child rows are cleared before parent rows (FK child -> parent).
    Kahn: edge child -> parent means parent must wait until child table is processed.
    """
    nodes = set(nodes)
    in_degree: dict[str, int] = {n: 0 for n in nodes}
    for child, parent in edges:
        if child not in nodes or parent not in nodes:
            continue
        in_degree[parent] += 1

    parents_after_child: dict[str, list[str]] = {}
    for child, parent in edges:
        if child not in nodes or parent not in nodes:
            continue
        parents_after_child.setdefault(child, []).append(parent)

    ready = sorted([n for n in nodes if in_degree[n] == 0])
    order: list[str] = []
    while ready:
        u = ready.pop(0)
        order.append(u)
        for p in sorted(parents_after_child.get(u, ())):
            in_degree[p] -= 1
            if in_degree[p] == 0:
                ready.append(p)
        ready.sort()

    if len(order) != len(nodes):
        remaining = sorted(nodes - set(order))
        raise RuntimeError(
            "Could not resolve FK delete order (cycle?). Remaining tables: "
            + ", ".join(remaining)
        )
    return order


def delete_plan_for_table(
    conn: sqlite3.Connection, table: str, cols: set[str]
) -> tuple[str, int] | None:
    """
    Return (sql, placeholder_count) for DELETE scoped to one client.
    Each ? is bound to the same client_id.
    """
    if "client_id" in cols:
        return (f"DELETE FROM {quote_ident(table)} WHERE client_id = ?", 1)
    if "document_id" in cols:
        has_fk = any(
            fk["from"] == "document_id" and fk["table"] == "documents" for fk in fk_list(conn, table)
        )
        if has_fk or "documents" in list_user_tables(conn):
            return (
                f"DELETE FROM {quote_ident(table)} WHERE document_id IN "
                f"(SELECT id FROM {quote_ident('documents')} WHERE client_id = ?)",
                1,
            )
    if "property_id" in cols and "client_id" not in cols and "properties" in list_user_tables(conn):
        return (
            f"DELETE FROM {quote_ident(table)} WHERE property_id IN "
            f"(SELECT id FROM {quote_ident('properties')} WHERE client_id = ?)",
            1,
        )
    return None


def delete_client_cascade(conn: sqlite3.Connection, client_id: int) -> dict[str, int]:
    """Remove one client and dependent rows; return table -> rows deleted."""
    nodes = deletion_nodes(conn)
    edges = build_delete_edges(conn, nodes)
    order = topological_delete_order(nodes, edges)
    counts: dict[str, int] = {}

    for table in order:
        cols = table_columns(conn, table)
        plan = delete_plan_for_table(conn, table, cols)
        if plan is None:
            continue
        sql, nph = plan
        cur = conn.execute(sql, (client_id,) * nph)
        rc = cur.rowcount
        if rc is not None and rc > 0:
            counts[table] = rc

    cur = conn.execute(f"DELETE FROM {quote_ident('clients')} WHERE id = ?", (client_id,))
    if cur.rowcount:
        counts["clients"] = cur.rowcount
    return counts


def resolve_client_ids(conn: sqlite3.Connection, name: str) -> list[int]:
    cur = conn.execute(
        f"SELECT id FROM {quote_ident('clients')} WHERE name = ? ORDER BY id",
        (name,),
    )
    return [r[0] for r in cur.fetchall()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delete stale/test clients from portal.db (manual cascade, schema-driven)."
    )
    parser.add_argument(
        "clients",
        nargs="*",
        default=[],
        help='Exact client names as in clients.name, e.g. "Sample Agency Alpha"',
    )
    args = parser.parse_args()

    if not args.clients:
        print(
            "Usage: python admin_delete_client.py <client_name> [<client_name> ...]\n"
            "Example: python admin_delete_client.py \"Client1\" \"Test Client\" \"Testing\" \"Client 5\"\n"
            f"Database: {DEFAULT_DB} (override with DATABASE_URL environment variable)",
            flush=True,
        )
        sys.exit(0)

    db_path = Path(os.environ.get("DATABASE_URL", str(DEFAULT_DB)))
    if not db_path.is_file():
        print(f"ERROR: database not found: {db_path}", flush=True)
        sys.exit(1)

    for raw_name in args.clients:
        name = raw_name.strip()
        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("PRAGMA foreign_keys = ON")
            conn.row_factory = sqlite3.Row

            ids = resolve_client_ids(conn, name)
            if not ids:
                print(f'WARNING: no client named "{name}" - skipped.', flush=True)
                continue

            for cid in ids:
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    counts = delete_client_cascade(conn, cid)
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise

                detail_tables = [f"{t}:{n}" for t, n in sorted(counts.items()) if t != "clients"]
                detail = f" [{', '.join(detail_tables)}]" if detail_tables else ""
                print(
                    f'OK: deleted client "{name}" (id={cid}){detail}; removed clients row.',
                    flush=True,
                )
        except Exception as e:
            print(f'ERROR: failed for "{name}": {e}', flush=True)
            sys.exit(1)
        finally:
            if conn is not None:
                conn.close()


if __name__ == "__main__":
    main()
