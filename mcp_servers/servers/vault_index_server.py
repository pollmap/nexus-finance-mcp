"""
Vault Index MCP Server — Obsidian Vault 시맨틱 검색 + 벡터 인덱싱.

기존 vault_server.py의 grep 검색을 보완하는 벡터 기반 시맨틱 검색.
Ollama bge-m3 임베딩 + SQLite + RRF 하이브리드 검색.

Tools (3):
- vault_index: Vault 노트 전체/증분 벡터 인덱싱
- vault_semantic_search: 시맨틱 검색 (의미 기반)
- vault_related: 특정 노트와 유사한 노트 찾기
"""
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP

from utils.embedding import get_embedding, embedding_to_blob, blob_to_embedding, cosine_similarity
from utils.sqlite_helpers import get_db as _get_db

logger = logging.getLogger(__name__)

# === Config ===
VAULT_ROOT = Path("/root/obsidian-vault")
DB_DIR = Path("/opt/nexus-finance-mcp/vault")
DB_PATH = DB_DIR / "vault_index.db"
BLOCKED_PREFIXES = (".obsidian", ".git", "scripts", "templates", ".trash")
MAX_CHUNK_CHARS = 2000  # 청크 최대 길이
OVERLAP_CHARS = 200     # 청크 간 오버랩


# === Text Processing ===
def parse_frontmatter(text: str) -> dict:
    """YAML frontmatter 추출."""
    meta = {}
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            for line in text[3:end].strip().split("\n"):
                if ":" in line:
                    key, _, val = line.partition(":")
                    meta[key.strip()] = val.strip()
    return meta


def extract_body(text: str) -> str:
    """frontmatter 제거 후 본문만 추출."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            return text[end + 3:].strip()
    return text


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    """텍스트를 청크로 분할. 짧은 노트는 하나의 청크."""
    if len(text) <= max_chars:
        return [text] if text.strip() else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        # 문단 경계에서 자르기
        if end < len(text):
            newline_pos = text.rfind("\n\n", start, end)
            if newline_pos > start + max_chars // 2:
                end = newline_pos
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap if end < len(text) else len(text)

    return chunks


# === DB ===
def get_db():
    return _get_db(str(DB_PATH))


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS vault_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            chunk_idx INTEGER DEFAULT 0,
            title TEXT,
            content_preview TEXT,
            embedding BLOB,
            tags TEXT DEFAULT '',
            agent TEXT DEFAULT '',
            folder TEXT DEFAULT '',
            file_mtime REAL,
            indexed_at TEXT DEFAULT (datetime('now')),
            UNIQUE(path, chunk_idx)
        );
        CREATE INDEX IF NOT EXISTS idx_vault_path ON vault_notes(path);
        CREATE INDEX IF NOT EXISTS idx_vault_folder ON vault_notes(folder);
        CREATE INDEX IF NOT EXISTS idx_vault_agent ON vault_notes(agent);
        CREATE INDEX IF NOT EXISTS idx_vault_mtime ON vault_notes(file_mtime);
    """)
    # FTS5 for BM25
    try:
        db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS vault_notes_fts
            USING fts5(content_preview, tags, title, content=vault_notes, content_rowid=id)
        """)
    except Exception as e:
        logger.warning(f"FTS table creation skipped: {e}")
    db.commit()
    db.close()


def sync_fts(db, note_id: int, title: str, preview: str, tags: str):
    """FTS 인덱스 동기화."""
    try:
        db.execute("INSERT OR REPLACE INTO vault_notes_fts(rowid, content_preview, tags, title) VALUES (?, ?, ?, ?)",
                   (note_id, preview, tags, title))
    except Exception as e:
        logger.warning(f"FTS sync failed for note #{note_id}: {e}")


# === RRF Merge ===
def rrf_merge(vector_results: list, bm25_results: list, k: int = 60) -> list:
    """Reciprocal Rank Fusion으로 벡터 + BM25 결과 병합."""
    scores = {}
    data = {}

    for rank, item in enumerate(vector_results):
        nid = item["id"]
        scores[nid] = scores.get(nid, 0) + 1.0 / (k + rank + 1)
        data[nid] = item

    for rank, item in enumerate(bm25_results):
        nid = item["id"]
        scores[nid] = scores.get(nid, 0) + 1.0 / (k + rank + 1)
        if nid not in data:
            data[nid] = item

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [{"score": round(scores[nid], 4), **data[nid]} for nid in sorted_ids]


class VaultIndexServer:
    def __init__(self):
        self.mcp = FastMCP("vault-index")
        init_db()
        self._register_tools()
        logger.info("Vault Index MCP Server initialized")

    def _register_tools(self):

        @self.mcp.tool()
        def vault_index(mode: str = "incremental", folder: str = "") -> dict:
            """
            Vault 노트를 벡터 인덱싱. bge-m3 임베딩으로 시맨틱 검색 가능하게.

            Args:
                mode: "full" (전체 재인덱싱) 또는 "incremental" (변경분만, 기본값)
                folder: 특정 폴더만 인덱싱 (빈 문자열이면 전체)
            """
            db = get_db()
            search_dir = VAULT_ROOT
            if folder:
                search_dir = VAULT_ROOT / folder.lstrip("/")
                if not search_dir.is_dir():
                    db.close()
                    return {"error": True, "message": f"폴더 없음: {folder}"}

            if mode == "full":
                db.execute("DELETE FROM vault_notes")
                try:
                    db.execute("DELETE FROM vault_notes_fts")
                except Exception as e:
                    logger.warning(f"FTS table clear failed: {e}")
                db.commit()

            # 기존 인덱싱된 파일의 mtime 맵
            existing = {}
            if mode == "incremental":
                for row in db.execute("SELECT DISTINCT path, file_mtime FROM vault_notes"):
                    existing[row["path"]] = row["file_mtime"]

            stats = {"indexed": 0, "skipped": 0, "errors": 0, "chunks": 0}
            md_files = list(search_dir.rglob("*.md"))

            # 삭제된 파일 정리
            current_paths = set()
            for p in md_files:
                rel = str(p.relative_to(VAULT_ROOT))
                if not any(rel.startswith(bp) for bp in BLOCKED_PREFIXES):
                    current_paths.add(rel)

            if mode == "incremental":
                for old_path in list(existing.keys()):
                    if old_path not in current_paths:
                        db.execute("DELETE FROM vault_notes WHERE path = ?", (old_path,))
                        stats["indexed"] += 1

            for p in md_files:
                rel = str(p.relative_to(VAULT_ROOT))
                if any(rel.startswith(bp) for bp in BLOCKED_PREFIXES):
                    continue

                mtime = p.stat().st_mtime

                # 증분 모드: mtime 변경 없으면 스킵
                if mode == "incremental" and rel in existing:
                    if abs(existing[rel] - mtime) < 1.0:
                        stats["skipped"] += 1
                        continue

                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                    if len(text.strip()) < 10:
                        stats["skipped"] += 1
                        continue

                    meta = parse_frontmatter(text)
                    body = extract_body(text)
                    title = p.stem
                    tags = meta.get("tags", "")
                    agent = meta.get("agent", "")
                    folder_name = str(p.parent.relative_to(VAULT_ROOT))

                    # 기존 청크 삭제
                    db.execute("DELETE FROM vault_notes WHERE path = ?", (rel,))

                    # 청크 분할 + 임베딩
                    chunks = chunk_text(body)
                    if not chunks:
                        chunks = [title]  # 최소한 제목이라도

                    for idx, chunk in enumerate(chunks):
                        # 임베딩 텍스트: 제목 + 태그 + 본문 청크
                        embed_text = f"{title}\n{tags}\n{chunk}"
                        emb = get_embedding(embed_text)
                        if emb is None:
                            stats["errors"] += 1
                            continue

                        preview = chunk[:500]
                        cursor = db.execute(
                            """INSERT INTO vault_notes
                               (path, chunk_idx, title, content_preview, embedding, tags, agent, folder, file_mtime)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (rel, idx, title, preview, embedding_to_blob(emb), tags, agent, folder_name, mtime),
                        )
                        sync_fts(db, cursor.lastrowid, title, preview, tags)
                        stats["chunks"] += 1

                    stats["indexed"] += 1

                except Exception as e:
                    logger.error(f"Index error for {rel}: {e}")
                    stats["errors"] += 1

            db.commit()

            # 총 인덱스 통계
            total_notes = db.execute("SELECT COUNT(DISTINCT path) FROM vault_notes").fetchone()[0]
            total_chunks = db.execute("SELECT COUNT(*) FROM vault_notes").fetchone()[0]
            db.close()

            return {
                "success": True,
                "mode": mode,
                "this_run": stats,
                "total_index": {"notes": total_notes, "chunks": total_chunks},
            }

        @self.mcp.tool()
        def vault_semantic_search(
            query: str,
            folder: str = "",
            agent: str = "",
            count: int = 10,
            hybrid: bool = True,
        ) -> dict:
            """
            Vault 시맨틱 검색. 의미 기반으로 관련 노트를 찾아줌.

            Args:
                query: 검색 쿼리 (자연어 가능, 예: "통화정책과 금리 인하의 관계")
                folder: 폴더 필터 (예: "02-Areas")
                agent: 에이전트 필터 (예: "oracle")
                count: 최대 결과 수 (기본 10)
                hybrid: True면 벡터+BM25 하이브리드, False면 벡터만 (기본 True)
            """
            if not query.strip():
                return {"error": True, "message": "검색어를 입력하세요"}

            db = get_db()

            # 총 인덱스 확인
            total = db.execute("SELECT COUNT(*) FROM vault_notes").fetchone()[0]
            if total == 0:
                db.close()
                return {"error": True, "message": "인덱스가 비어있음. vault_index를 먼저 실행하세요."}

            # 1) 벡터 검색
            query_emb = get_embedding(query)
            if query_emb is None:
                db.close()
                return {"error": True, "message": "임베딩 생성 실패. Ollama 상태를 확인하세요."}

            where_clauses = []
            params = []
            if folder:
                where_clauses.append("folder LIKE ?")
                params.append(f"{folder}%")
            if agent:
                where_clauses.append("agent = ?")
                params.append(agent)

            where_sql = ""
            if where_clauses:
                where_sql = "WHERE " + " AND ".join(where_clauses)

            rows = db.execute(
                f"SELECT id, path, chunk_idx, title, content_preview, embedding, tags, agent, folder FROM vault_notes {where_sql}",
                params,
            ).fetchall()

            vector_results = []
            for row in rows:
                if row["embedding"] is None:
                    continue
                emb = blob_to_embedding(row["embedding"])
                sim = cosine_similarity(query_emb, emb)
                vector_results.append({
                    "id": row["id"],
                    "path": row["path"],
                    "chunk_idx": row["chunk_idx"],
                    "title": row["title"],
                    "preview": row["content_preview"],
                    "tags": row["tags"],
                    "agent": row["agent"],
                    "folder": row["folder"],
                    "vector_score": round(sim, 4),
                })

            vector_results.sort(key=lambda x: x["vector_score"], reverse=True)
            vector_results = vector_results[: count * 3]  # RRF용 여유

            # 2) BM25 검색 (hybrid mode)
            bm25_results = []
            if hybrid:
                try:
                    fts_rows = db.execute(
                        "SELECT rowid, content_preview, tags, title FROM vault_notes_fts WHERE vault_notes_fts MATCH ? ORDER BY rank LIMIT ?",
                        (query, count * 3),
                    ).fetchall()
                    for frow in fts_rows:
                        # rowid로 원본 테이블에서 메타 정보 가져오기
                        orig = db.execute(
                            "SELECT id, path, chunk_idx, title, content_preview, tags, agent, folder FROM vault_notes WHERE id = ?",
                            (frow["rowid"],),
                        ).fetchone()
                        if orig:
                            bm25_results.append({
                                "id": orig["id"],
                                "path": orig["path"],
                                "chunk_idx": orig["chunk_idx"],
                                "title": orig["title"],
                                "preview": orig["content_preview"],
                                "tags": orig["tags"],
                                "agent": orig["agent"],
                                "folder": orig["folder"],
                            })
                except Exception as e:
                    logger.warning(f"BM25 search error: {e}")

            db.close()

            # 3) 결과 병합
            if hybrid and bm25_results:
                merged = rrf_merge(vector_results, bm25_results)
            else:
                merged = [{"score": r["vector_score"], **r} for r in vector_results]

            # 같은 path의 중복 청크 제거 (최고 점수만 유지)
            seen_paths = {}
            deduplicated = []
            for item in merged:
                p = item["path"]
                if p not in seen_paths:
                    seen_paths[p] = True
                    deduplicated.append(item)

            deduplicated = deduplicated[:count]

            return {
                "success": True,
                "query": query,
                "mode": "hybrid" if hybrid else "vector",
                "total": len(deduplicated),
                "results": deduplicated,
            }

        @self.mcp.tool()
        def vault_related(path: str, count: int = 5) -> dict:
            """
            특정 노트와 유사한 노트 찾기. 지식 그래프 탐색용.

            Args:
                path: vault 내 노트 경로 (예: "02-Areas/crypto-markets/analysis.md")
                count: 최대 결과 수 (기본 5)
            """
            db = get_db()

            # 해당 노트의 임베딩 가져오기 (첫 번째 청크)
            row = db.execute(
                "SELECT embedding, title, tags, folder FROM vault_notes WHERE path = ? AND chunk_idx = 0",
                (path,),
            ).fetchone()

            if row is None:
                db.close()
                return {"error": True, "message": f"인덱스에 없는 노트: {path}. vault_index를 실행하세요."}

            if row["embedding"] is None:
                db.close()
                return {"error": True, "message": f"임베딩 없음: {path}"}

            source_emb = blob_to_embedding(row["embedding"])
            source_title = row["title"]

            # 전체 노트와 유사도 계산
            all_rows = db.execute(
                "SELECT id, path, chunk_idx, title, content_preview, embedding, tags, agent, folder FROM vault_notes WHERE path != ?",
                (path,),
            ).fetchall()

            similarities = []
            for r in all_rows:
                if r["embedding"] is None:
                    continue
                emb = blob_to_embedding(r["embedding"])
                sim = cosine_similarity(source_emb, emb)
                similarities.append({
                    "path": r["path"],
                    "chunk_idx": r["chunk_idx"],
                    "title": r["title"],
                    "preview": r["content_preview"][:300],
                    "tags": r["tags"],
                    "agent": r["agent"],
                    "folder": r["folder"],
                    "similarity": round(sim, 4),
                })

            db.close()

            similarities.sort(key=lambda x: x["similarity"], reverse=True)

            # 같은 path 중복 제거
            seen = {}
            deduped = []
            for item in similarities:
                p = item["path"]
                if p not in seen:
                    seen[p] = True
                    deduped.append(item)

            deduped = deduped[:count]

            return {
                "success": True,
                "source": {"path": path, "title": source_title},
                "total": len(deduped),
                "related": deduped,
            }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = VaultIndexServer()
    server.mcp.run(transport="stdio")
