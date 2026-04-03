#!/usr/bin/env python3
"""
Luxon Memory MCP Server
SQLite + Ollama bge-m3 벡터 임베딩 + BM25 하이브리드 검색
Frimion 방식: WAL 프로토콜, Superseded 마킹, 하이브리드 검색
"""
import logging
import os
from fastmcp import FastMCP

logger = logging.getLogger(__name__)

from utils.embedding import get_embedding, embedding_to_blob, blob_to_embedding, cosine_similarity
from utils.sqlite_helpers import get_db as _get_db

# === Config ===
DB_PATH = os.environ.get("MEMORY_DB_PATH", "/opt/nexus-finance-mcp/memory/memory.db")
SUPERSEDE_THRESHOLD = 0.85
TOP_K_DEFAULT = 5

mcp = FastMCP("memory-mcp")


# === DB Init ===
def get_db():
    return _get_db(DB_PATH)


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            importance REAL DEFAULT 0.5,
            embedding BLOB,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            superseded_by INTEGER,
            source TEXT DEFAULT 'unknown',
            FOREIGN KEY (superseded_by) REFERENCES memories(id)
        );
        CREATE INDEX IF NOT EXISTS idx_category ON memories(category);
        CREATE INDEX IF NOT EXISTS idx_superseded ON memories(superseded_by);
    """)
    try:
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(content, category, content=memories, content_rowid=id)")
    except Exception as e:
        logger.warning(f"FTS table creation skipped (may already exist): {e}")
    db.commit()
    db.close()


def rrf_merge(vector_results, bm25_results, k=60):
    """RRF merge for memory search (tuple-based results)."""
    scores = {}
    for rank, (id_, score, content, cat) in enumerate(vector_results):
        scores[id_] = scores.get(id_, 0) + 1.0 / (k + rank + 1)
    for rank, (id_, content, cat) in enumerate(bm25_results):
        scores[id_] = scores.get(id_, 0) + 1.0 / (k + rank + 1)

    all_items = {}
    for id_, score, content, cat in vector_results:
        all_items[id_] = (content, cat)
    for id_, content, cat in bm25_results:
        all_items[id_] = (content, cat)

    merged = [(id_, scores[id_], all_items[id_][0], all_items[id_][1]) for id_ in scores]
    merged.sort(key=lambda x: x[1], reverse=True)
    return merged

# === MCP Tools ===
@mcp.tool()
def memory_store(content: str, category: str = "general", importance: float = 0.5, source: str = "claude-code") -> str:
    """중요한 사실/결정/선호를 영구 저장. category: user/feedback/project/reference/decision/general"""
    db = get_db()
    emb = get_embedding(content)
    emb_blob = embedding_to_blob(emb) if emb else None

    superseded_ids = []
    if emb:
        rows = db.execute(
            "SELECT id, content, embedding FROM memories WHERE superseded_by IS NULL AND category=?",
            (category,)
        ).fetchall()
        for row in rows:
            if row["embedding"]:
                old_emb = blob_to_embedding(row["embedding"])
                sim = cosine_similarity(emb, old_emb)
                if sim >= SUPERSEDE_THRESHOLD:
                    superseded_ids.append((row["id"], row["content"][:50], sim))

    cur = db.execute(
        "INSERT INTO memories (content, category, importance, embedding, source) VALUES (?, ?, ?, ?, ?)",
        (content, category, importance, emb_blob, source)
    )
    new_id = cur.lastrowid

    for old_id, _, _ in superseded_ids:
        db.execute("UPDATE memories SET superseded_by=?, updated_at=datetime('now') WHERE id=?", (new_id, old_id))

    try:
        db.execute("INSERT INTO memories_fts(rowid, content, category) VALUES (?, ?, ?)", (new_id, content, category))
    except Exception as e:
        logger.warning(f"FTS insert failed for memory #{new_id}: {e}")

    db.commit()
    db.close()

    result = f"Stored memory #{new_id} [{category}]"
    if superseded_ids:
        result += f" (superseded {len(superseded_ids)} old entries)"
    return result

@mcp.tool()
def memory_search(query: str, top_k: int = TOP_K_DEFAULT, category: str = "") -> str:
    """하이브리드 검색: 벡터(의미) + BM25(키워드) + RRF. 한국어 의미검색 지원."""
    db = get_db()

    vector_results = []
    query_emb = get_embedding(query)
    if query_emb:
        if category:
            rows = db.execute(
                "SELECT id, content, category, embedding FROM memories WHERE superseded_by IS NULL AND category=?",
                (category,)
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT id, content, category, embedding FROM memories WHERE superseded_by IS NULL"
            ).fetchall()

        scored = []
        for row in rows:
            if row["embedding"]:
                sim = cosine_similarity(query_emb, blob_to_embedding(row["embedding"]))
                scored.append((row["id"], sim, row["content"], row["category"]))
        scored.sort(key=lambda x: x[1], reverse=True)
        vector_results = scored[:top_k * 2]

    bm25_results = []
    try:
        if category:
            fts_rows = db.execute(
                "SELECT rowid, content, category FROM memories_fts WHERE memories_fts MATCH ? AND category=? LIMIT ?",
                (query, category, top_k * 2)
            ).fetchall()
        else:
            fts_rows = db.execute(
                "SELECT rowid, content, category FROM memories_fts WHERE memories_fts MATCH ? LIMIT ?",
                (query, top_k * 2)
            ).fetchall()
        bm25_results = [(r["rowid"], r["content"], r["category"]) for r in fts_rows]
    except Exception as e:
        logger.warning(f"BM25 search failed (FTS may not be available): {e}")

    if vector_results and bm25_results:
        merged = rrf_merge(vector_results, bm25_results)
    elif vector_results:
        merged = vector_results
    elif bm25_results:
        merged = [(id_, 1.0, content, cat) for id_, content, cat in bm25_results]
    else:
        db.close()
        return "No memories found."

    db.close()

    results = []
    for item in merged[:top_k]:
        results.append(f"#{item[0]} [{item[3]}] (score:{item[1]:.3f}): {item[2]}")

    return "\n".join(results) if results else "No memories found."

@mcp.tool()
def memory_list(category: str = "", limit: int = 20) -> str:
    """카테고리별 기억 목록 조회"""
    db = get_db()
    if category:
        rows = db.execute(
            "SELECT id, content, category, importance, created_at, source FROM memories WHERE superseded_by IS NULL AND category=? ORDER BY created_at DESC LIMIT ?",
            (category, limit)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT id, content, category, importance, created_at, source FROM memories WHERE superseded_by IS NULL ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    db.close()

    if not rows:
        return "No memories found."

    results = []
    for r in rows:
        content_preview = r["content"][:100] + ("..." if len(r["content"]) > 100 else "")
        results.append(f"#{r['id']} [{r['category']}] {content_preview} (imp:{r['importance']}, {r['created_at']}, src:{r['source']})")
    return "\n".join(results)

@mcp.tool()
def memory_forget(memory_id: int) -> str:
    """특정 기억 삭제 (soft delete)"""
    db = get_db()
    row = db.execute("SELECT id FROM memories WHERE id=?", (memory_id,)).fetchone()
    if not row:
        db.close()
        return f"Memory #{memory_id} not found."
    db.execute("UPDATE memories SET superseded_by=-1, updated_at=datetime('now') WHERE id=?", (memory_id,))
    db.commit()
    db.close()
    return f"Memory #{memory_id} forgotten."

@mcp.tool()
def memory_stats() -> str:
    """메모리 시스템 통계"""
    db = get_db()
    total = db.execute("SELECT COUNT(*) as c FROM memories").fetchone()["c"]
    active = db.execute("SELECT COUNT(*) as c FROM memories WHERE superseded_by IS NULL").fetchone()["c"]
    cats = db.execute("SELECT category, COUNT(*) as c FROM memories WHERE superseded_by IS NULL GROUP BY category").fetchall()
    db.close()

    lines = [f"Total: {total} (active: {active}, superseded: {total - active})"]
    for cat in cats:
        lines.append(f"  [{cat['category']}]: {cat['c']}")
    return "\n".join(lines)

if __name__ == "__main__":
    mcp.run(transport="stdio")

class MemoryServer:
    def __init__(self):
        init_db()
        self.mcp = mcp
