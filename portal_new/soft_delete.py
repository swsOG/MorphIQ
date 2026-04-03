"""
Client soft-delete: schema helpers, timestamped soft delete, manual hard-delete cascade, purge.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta


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


def tables_with_client_id_column(conn: sqlite3.Connection) -> set[str]:
    out: set[str] = set()
    for table in list_user_tables(conn):
        if table == "clients":
            continue
        if "client_id" in table_columns(conn, table):
            out.add(table)
    return out


def document_child_tables(conn: sqlite3.Connection) -> set[str]:
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


def tables_referencing_clients_via_client_id(conn: sqlite3.Connection) -> set[str]:
    found: set[str] = set()
    for table in list_user_tables(conn):
        for fk in fk_list(conn, table):
            if fk["from"] == "client_id" and fk["table"] == "clients":
                found.add(table)
    return found


def deletion_nodes(conn: sqlite3.Connection) -> set[str]:
    return (
        tables_with_client_id_column(conn)
        | document_child_tables(conn)
        | tables_referencing_clients_via_client_id(conn)
    ) - {"clients"}


def build_delete_edges(conn: sqlite3.Connection, nodes: set[str]) -> list[tuple[str, str]]:
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


def hard_delete_client_cascade(conn: sqlite3.Connection, client_id: int) -> None:
    """Permanently remove client rows and dependents (manual cascade)."""
    nodes = deletion_nodes(conn)
    edges = build_delete_edges(conn, nodes)
    order = topological_delete_order(nodes, edges)

    for table in order:
        cols = table_columns(conn, table)
        plan = delete_plan_for_table(conn, table, cols)
        if plan is None:
            continue
        sql, nph = plan
        conn.execute(sql, (client_id,) * nph)

    conn.execute(f"DELETE FROM {quote_ident('clients')} WHERE id = ?", (client_id,))


def _add_column_if_missing(
    conn: sqlite3.Connection, table: str, column: str, decl: str
) -> None:
    cols = table_columns(conn, table)
    if column in cols:
        return
    conn.execute(f"ALTER TABLE {quote_ident(table)} ADD COLUMN {column} {decl}")


def ensure_deleted_at_schema(conn: sqlite3.Connection) -> None:
    """Add nullable deleted_at to clients, all client_id tables, and document_fields."""
    _add_column_if_missing(conn, "clients", "deleted_at", "TEXT")
    for table in list_user_tables(conn):
        if table == "clients":
            continue
        cols = table_columns(conn, table)
        if "client_id" in cols:
            _add_column_if_missing(conn, table, "deleted_at", "TEXT")
    if "document_fields" in list_user_tables(conn):
        _add_column_if_missing(conn, "document_fields", "deleted_at", "TEXT")


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def soft_delete_client(conn: sqlite3.Connection, client_id: int) -> tuple[str, str]:
    """
    Set deleted_at on the client row and all dependent rows (tables with client_id + document_fields).
    Returns (client_name, timestamp_iso).
    """
    cur = conn.execute(
        f"SELECT id, name FROM {quote_ident('clients')} WHERE id = ? AND deleted_at IS NULL",
        (client_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError("Client not found or already deleted")

    name = row["name"] if isinstance(row, sqlite3.Row) else row[1]
    ts = utc_now_iso()

    for table in sorted(tables_with_client_id_column(conn)):
        if table == "clients":
            continue
        conn.execute(
            f"UPDATE {quote_ident(table)} SET deleted_at = ? WHERE client_id = ? AND deleted_at IS NULL",
            (ts, client_id),
        )

    if "document_fields" in list_user_tables(conn):
        conn.execute(
            f"""
            UPDATE {quote_ident('document_fields')}
            SET deleted_at = ?
            WHERE document_id IN (SELECT id FROM {quote_ident('documents')} WHERE client_id = ?)
              AND deleted_at IS NULL
            """,
            (ts, client_id),
        )

    conn.execute(
        f"UPDATE {quote_ident('clients')} SET deleted_at = ? WHERE id = ?",
        (ts, client_id),
    )
    return (name, ts)


def purge_expired_soft_deletes(conn: sqlite3.Connection, retention_days: int = 30) -> int:
    """
    Hard-delete clients (and dependents) whose deleted_at is older than retention_days.
    Uses SQLite datetime comparison. Returns number of clients purged.
    """
    mod = f"-{int(retention_days)} days"
    cur = conn.execute(
        f"""
        SELECT id FROM {quote_ident('clients')}
        WHERE deleted_at IS NOT NULL
          AND datetime(deleted_at) < datetime('now', '{mod}')
        """
    )
    ids = [r[0] for r in cur.fetchall()]
    for cid in ids:
        hard_delete_client_cascade(conn, cid)
    return len(ids)
