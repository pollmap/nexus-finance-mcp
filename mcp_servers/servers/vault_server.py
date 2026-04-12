"""
Vault MCP Server — Obsidian Vault 공유 지식 베이스 접근.

Tools (6):
- vault_search: 전문 검색 (키워드 grep)
- vault_read: 노트 읽기
- vault_list: 노트 목록 (폴더/에이전트/기간 필터)
- vault_recent: 최근 수정 노트
- vault_tags: 전체 태그 목록
- vault_write: 노트 쓰기 (에이전트별 권한 체크)
"""
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

VAULT_ROOT = Path("/root/obsidian-vault")

# AGENTS.md 기반 쓰기 권한
WRITE_PERMS = {
    # === Karpathy 3-layer structure (2026-04-12 migration) ===
    # VPS agents
    "hermes": ["inbox/hermes", "raw", "wiki", "projects", "memory/agents", "outputs"],
    "nexus": ["inbox/nexus", "raw", "wiki", "memory/agents"],
    "oracle": ["inbox/oracle", "raw", "wiki", "memory/agents"],
    # VPS subagents (legacy, mapped to new paths)
    "merchant": ["inbox/hermes", "projects"],
    "treasurer": ["inbox/hermes", "projects"],
    "prophet": ["inbox/oracle", "raw/research-papers", "projects"],
    "voyager": ["inbox/nexus", "raw", "wiki"],
    # WSL agents
    "gate": ["inbox", "projects"],
    "chief": ["inbox", "projects"],
    "doge": ["inbox/doge", "raw", "wiki", "memory/agents"],
}

# Forbidden write paths (agent-proof)
FORBIDDEN_WRITE = ["memory/chanhi", "_system"]

BLOCKED_PREFIXES = (".obsidian", ".git")


GIT_STATUS_FILE = VAULT_ROOT / ".git-push-status"


def _git_auto_commit(rel_path: str, agent: str):
    """vault_write 후 비동기 git commit + push. 응답을 블로킹하지 않음."""
    import threading

    def _run():
        try:
            subprocess.run(["git", "-C", str(VAULT_ROOT), "add", rel_path],
                           capture_output=True, timeout=10, check=True)
            subprocess.run(["git", "-C", str(VAULT_ROOT), "commit", "-m",
                            f"vault: {agent} wrote {rel_path}"],
                           capture_output=True, timeout=10, check=True)
            result = subprocess.run(["git", "-C", str(VAULT_ROOT), "push"],
                                    capture_output=True, timeout=30)
            if result.returncode != 0:
                err = result.stderr.decode("utf-8", errors="replace").strip()
                logger.error(f"git push failed for {rel_path}: {err}")
                GIT_STATUS_FILE.write_text(f"FAIL|{rel_path}|{agent}|{err}\n")
            else:
                logger.info(f"git push OK: {rel_path} by {agent}")
                if GIT_STATUS_FILE.exists():
                    GIT_STATUS_FILE.unlink()
        except subprocess.CalledProcessError as e:
            logger.warning(f"git auto-commit failed: {e}")
            GIT_STATUS_FILE.write_text(f"FAIL|{rel_path}|{agent}|{e}\n")
        except Exception as e:
            logger.warning(f"git auto-commit failed: {e}")

    threading.Thread(target=_run, daemon=True).start()


def _safe_path(relative: str) -> Path:
    """Resolve path within vault, blocking traversal and forbidden dirs."""
    clean = relative.lstrip("/")
    resolved = (VAULT_ROOT / clean).resolve()
    if not str(resolved).startswith(str(VAULT_ROOT.resolve())):
        raise ValueError(f"경로 접근 거부: vault 외부 경로 — {relative}")
    for prefix in BLOCKED_PREFIXES:
        if clean.startswith(prefix):
            raise ValueError(f"경로 접근 거부: {prefix}/ 폴더 접근 불가")
    return resolved


def _parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from markdown."""
    meta = {}
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            fm = text[3:end].strip()
            for line in fm.split("\n"):
                if ":" in line:
                    key, _, val = line.partition(":")
                    meta[key.strip()] = val.strip()
    return meta


def _note_summary(path: Path) -> dict:
    """Build a summary dict for a note file."""
    rel = str(path.relative_to(VAULT_ROOT))
    stat = path.stat()
    text = path.read_text(encoding="utf-8", errors="replace")
    meta = _parse_frontmatter(text)
    return {
        "path": rel,
        "agent": meta.get("agent", ""),
        "date": meta.get("date", ""),
        "tags": meta.get("tags", ""),
        "status": meta.get("status", ""),
        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
        "size": stat.st_size,
    }


class VaultServer:
    def __init__(self):
        self.mcp = FastMCP("vault")
        self._register_tools()
        logger.info("Vault MCP Server initialized")

    def _register_tools(self):

        @self.mcp.tool()
        def vault_search(query: str, folder: str = "", tags: str = "", count: int = 10) -> dict:
            """
            Obsidian Vault 전문 검색. 키워드로 모든 노트 내용을 검색.

            Args:
                query: 검색어 (고정 문자열 매칭)
                folder: 특정 폴더로 제한 (예: "02-Areas", "03-Resources/research-papers")
                tags: 태그 필터 (쉼표 구분, 예: "crypto,defi")
                count: 최대 결과 수 (기본 10)
            """
            if len(query) > 200:
                return {"error": True, "message": "검색어 200자 제한 초과"}
            if not query.strip():
                return {"error": True, "message": "검색어를 입력하세요"}
            if query.lstrip().startswith("-"):
                return {"error": True, "message": "검색어는 '-'로 시작할 수 없습니다"}

            search_dir = VAULT_ROOT
            if folder:
                search_dir = _safe_path(folder)
                if not search_dir.is_dir():
                    return {"error": True, "message": f"폴더 없음: {folder}"}

            try:
                result = subprocess.run(
                    ["grep", "-Fril", "--include=*.md", query, str(search_dir)],
                    capture_output=True, text=True, timeout=10,
                )
            except subprocess.TimeoutExpired:
                return {"error": True, "message": "검색 시간 초과"}

            if not result.stdout.strip():
                return {"success": True, "query": query, "results": [], "total": 0}

            files = result.stdout.strip().split("\n")
            results = []
            tag_filters = [t.strip().lower() for t in tags.split(",") if t.strip()] if tags else []

            for fpath in files:
                p = Path(fpath)
                if not p.exists():
                    continue
                # Skip blocked dirs
                rel = str(p.relative_to(VAULT_ROOT))
                if any(rel.startswith(bp) for bp in BLOCKED_PREFIXES):
                    continue

                summary = _note_summary(p)

                # Tag filter
                if tag_filters:
                    note_tags = summary.get("tags", "").lower()
                    if not any(t in note_tags for t in tag_filters):
                        continue

                # Get matching lines for context
                try:
                    ctx = subprocess.run(
                        ["grep", "-Fin", query, str(p)],
                        capture_output=True, text=True, timeout=5,
                    )
                    matches = ctx.stdout.strip().split("\n")[:3]
                    summary["matches"] = matches
                except Exception:
                    summary["matches"] = []

                results.append(summary)
                if len(results) >= count:
                    break

            return {"success": True, "query": query, "total": len(results), "results": results}

        @self.mcp.tool()
        def vault_read(path: str) -> dict:
            """
            Obsidian Vault 노트 읽기.

            Args:
                path: vault 내 상대 경로 (예: "02-Areas/crypto-markets/oracle-2026-03-18-xxx.md")
            """
            try:
                resolved = _safe_path(path)
            except ValueError as e:
                return {"error": True, "message": str(e)}

            if not resolved.exists():
                return {"error": True, "message": f"파일 없음: {path}"}
            if not resolved.suffix == ".md":
                return {"error": True, "message": "마크다운 파일만 읽기 가능"}
            if resolved.stat().st_size > 5_000_000:
                return {"error": True, "message": f"파일 크기 초과 (5MB 제한): {resolved.stat().st_size} bytes"}

            text = resolved.read_text(encoding="utf-8", errors="replace")
            meta = _parse_frontmatter(text)

            # Separate body from frontmatter
            body = text
            if text.startswith("---"):
                end = text.find("---", 3)
                if end > 0:
                    body = text[end + 3:].strip()

            return {
                "success": True,
                "path": path,
                "metadata": meta,
                "content": body,
                "size": len(text),
            }

        @self.mcp.tool()
        def vault_list(folder: str = "", agent: str = "", days: int = 7, count: int = 20) -> dict:
            """
            Obsidian Vault 노트 목록. 폴더/에이전트/기간으로 필터링.

            Args:
                folder: 폴더 경로 (예: "02-Areas", 빈 문자열이면 전체)
                agent: 에이전트 이름으로 필터 (예: "oracle")
                days: 최근 N일 이내 수정된 파일만 (기본 7, 0이면 전체)
                count: 최대 결과 수 (기본 20)
            """
            search_dir = VAULT_ROOT
            if folder:
                try:
                    search_dir = _safe_path(folder)
                except ValueError as e:
                    return {"error": True, "message": str(e)}
                if not search_dir.is_dir():
                    return {"error": True, "message": f"폴더 없음: {folder}"}

            cutoff = None
            if days > 0:
                cutoff = datetime.now() - timedelta(days=days)

            notes = []
            for p in search_dir.rglob("*.md"):
                rel = str(p.relative_to(VAULT_ROOT))
                if any(rel.startswith(bp) for bp in BLOCKED_PREFIXES):
                    continue
                if cutoff and datetime.fromtimestamp(p.stat().st_mtime) < cutoff:
                    continue
                summary = _note_summary(p)
                if agent and summary.get("agent", "").lower() != agent.lower():
                    continue
                notes.append(summary)

            # Sort by modified desc
            notes.sort(key=lambda x: x["modified"], reverse=True)
            notes = notes[:count]

            return {"success": True, "folder": folder or "(전체)", "total": len(notes), "notes": notes}

        @self.mcp.tool()
        def vault_recent(agent: str = "", count: int = 10) -> dict:
            """
            최근 수정된 노트 목록 (빠른 조회).

            Args:
                agent: 에이전트 이름으로 필터 (빈 문자열이면 전체)
                count: 최대 결과 수 (기본 10)
            """
            notes = []
            for p in VAULT_ROOT.rglob("*.md"):
                rel = str(p.relative_to(VAULT_ROOT))
                if any(rel.startswith(bp) for bp in BLOCKED_PREFIXES):
                    continue
                summary = _note_summary(p)
                if agent and summary.get("agent", "").lower() != agent.lower():
                    continue
                notes.append(summary)

            notes.sort(key=lambda x: x["modified"], reverse=True)
            return {"success": True, "total": len(notes[:count]), "notes": notes[:count]}

        @self.mcp.tool()
        def vault_tags() -> dict:
            """Obsidian Vault 전체 태그 목록 + 사용 빈도."""
            tag_counts = {}
            total_notes = 0

            for p in VAULT_ROOT.rglob("*.md"):
                rel = str(p.relative_to(VAULT_ROOT))
                if any(rel.startswith(bp) for bp in BLOCKED_PREFIXES):
                    continue
                total_notes += 1
                text = p.read_text(encoding="utf-8", errors="replace")
                meta = _parse_frontmatter(text)
                tags_str = meta.get("tags", "")
                # Parse [tag1, tag2] format
                tags_str = tags_str.strip("[]")
                for tag in tags_str.split(","):
                    tag = tag.strip().lower()
                    if tag:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1

            sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
            return {
                "success": True,
                "total_notes": total_notes,
                "total_tags": len(sorted_tags),
                "tags": [{"tag": t, "count": c} for t, c in sorted_tags],
            }

        @self.mcp.tool()
        def vault_write(path: str, content: str, agent: str) -> dict:
            """
            Obsidian Vault에 노트 쓰기/업데이트. 에이전트별 권한 체크.

            Args:
                path: vault 내 상대 경로 (예: "02-Areas/crypto-markets/my-analysis.md")
                content: 마크다운 내용 (frontmatter 포함)
                agent: 작성 에이전트 이름 (hermes/nexus/oracle)
            """
            agent_lower = agent.lower()
            if agent_lower not in WRITE_PERMS:
                return {"error": True, "message": f"알 수 없는 에이전트: {agent}. 허용: {list(WRITE_PERMS.keys())}"}

            try:
                resolved = _safe_path(path)
            except ValueError as e:
                return {"error": True, "message": str(e)}

            if not path.endswith(".md"):
                return {"error": True, "message": "마크다운 파일(.md)만 쓰기 가능"}

            # Check write permission
            rel = str(resolved.relative_to(VAULT_ROOT.resolve()))
            allowed = WRITE_PERMS[agent_lower]
            if not any(rel == prefix or rel.startswith(prefix + "/") for prefix in allowed):
                return {
                    "error": True,
                    "message": f"{agent}은(는) {rel} 경로에 쓰기 권한 없음. 허용 폴더: {allowed}",
                }

            # Forbidden paths (memory/chanhi, _system) — agent-proof
            if any(rel == fp or rel.startswith(fp + "/") for fp in FORBIDDEN_WRITE):
                return {
                    "error": True,
                    "message": f"접근 금지 경로: {rel}. memory/chanhi/와 _system/은 찬희만 수정 가능.",
                }

            # Validate frontmatter
            if not content.startswith("---"):
                return {"error": True, "message": "frontmatter(---) 필수. date, agent, tags, status 포함해야 함"}

            meta = _parse_frontmatter(content)
            required = ["date", "agent", "tags", "status"]
            missing = [k for k in required if k not in meta]
            if missing:
                return {"error": True, "message": f"frontmatter 필수 필드 누락: {missing}"}

            if meta.get("agent", "").lower() != agent_lower:
                return {"error": True, "message": f"frontmatter agent({meta.get('agent')})와 요청 agent({agent}) 불일치"}

            # Write
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")

            # Append to log.md
            try:
                log_path = VAULT_ROOT / "_system" / "log.md"
                if log_path.exists():
                    from datetime import datetime as _dt
                    ts = _dt.now().strftime("%Y-%m-%d %H:%M")
                    log_entry = f"\n## [{ts}] write | {agent_lower} \u2192 {path}\n"
                    with open(log_path, "a", encoding="utf-8") as lf:
                        lf.write(log_entry)
            except Exception as e:
                logger.warning(f"log.md append failed: {e}")

            # Auto git commit + push
            _git_auto_commit(path, agent_lower)

            return {
                "success": True,
                "path": path,
                "size": len(content),
                "message": f"노트 저장 + git push 완료: {path}",
            }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = VaultServer()
    server.mcp.run(transport="stdio")
