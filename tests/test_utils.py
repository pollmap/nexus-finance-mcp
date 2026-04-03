"""
Tests for shared utility modules.
"""
import sys
import os
import struct
import math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.validation import (
    validate_stock_code,
    validate_series_id,
    validate_search_query,
    validate_date,
    validate_date_range,
    validate_positive_int,
)
from utils.embedding import embedding_to_blob, blob_to_embedding, cosine_similarity
from utils.sqlite_helpers import get_db
import pytest
import tempfile


# === Validation Tests ===

class TestValidateStockCode:
    def test_valid_korean(self):
        assert validate_stock_code("005930") == "005930"

    def test_valid_us(self):
        assert validate_stock_code("AAPL") == "AAPL"

    def test_valid_with_dot(self):
        # RELIANCE.NS is 12 chars, exceeds max 10 — use shorter example
        assert validate_stock_code("TCS.NS") == "TCS.NS"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_stock_code("")

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="too long"):
            validate_stock_code("A" * 11)

    def test_special_chars_raises(self):
        with pytest.raises(ValueError):
            validate_stock_code("005930; DROP TABLE")


class TestValidateSeriesId:
    def test_valid(self):
        assert validate_series_id("GDP") == "GDP"
        assert validate_series_id("UNRATE") == "UNRATE"
        assert validate_series_id("DFF_RATE") == "DFF_RATE"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            validate_series_id("")

    def test_special_chars_raises(self):
        with pytest.raises(ValueError):
            validate_series_id("GDP;DROP")


class TestValidateSearchQuery:
    def test_valid(self):
        assert validate_search_query("bitcoin price") == "bitcoin price"

    def test_korean(self):
        assert validate_search_query("삼성전자 주가") == "삼성전자 주가"

    def test_strips_dangerous(self):
        result = validate_search_query("test<script>alert(1)</script>")
        assert "<" not in result
        assert ">" not in result

    def test_truncates_long(self):
        result = validate_search_query("a" * 300, max_length=200)
        assert len(result) == 200

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            validate_search_query("")


class TestValidateDate:
    def test_valid(self):
        assert validate_date("2024-01-15") == "2024-01-15"

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid"):
            validate_date("01-15-2024")

    def test_invalid_date(self):
        with pytest.raises(ValueError):
            validate_date("2024-13-01")


class TestValidateDateRange:
    def test_valid_range(self):
        s, e = validate_date_range("2024-01-01", "2024-12-31")
        assert s == "2024-01-01"
        assert e == "2024-12-31"

    def test_reversed_raises(self):
        with pytest.raises(ValueError, match="must be before"):
            validate_date_range("2024-12-31", "2024-01-01")

    def test_none_ok(self):
        s, e = validate_date_range(None, None)
        assert s is None and e is None


class TestValidatePositiveInt:
    def test_valid(self):
        assert validate_positive_int(10) == 10

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="must be positive"):
            validate_positive_int(0)

    def test_too_large_raises(self):
        with pytest.raises(ValueError, match="too large"):
            validate_positive_int(99999, max_val=100)


# === Embedding Tests ===

class TestEmbeddingUtils:
    def test_blob_roundtrip(self):
        original = [0.1, 0.2, 0.3, 0.4, 0.5]
        blob = embedding_to_blob(original)
        restored = blob_to_embedding(blob)
        for a, b in zip(original, restored):
            assert abs(a - b) < 1e-6

    def test_cosine_identical(self):
        v = [1.0, 0.0, 0.0]
        assert abs(cosine_similarity(v, v) - 1.0) < 1e-6

    def test_cosine_orthogonal(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(cosine_similarity(a, b)) < 1e-6

    def test_cosine_opposite(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(cosine_similarity(a, b) - (-1.0)) < 1e-6

    def test_cosine_zero_vector(self):
        a = [0.0, 0.0]
        b = [1.0, 1.0]
        assert cosine_similarity(a, b) == 0.0


# === SQLite Helper Tests ===

class TestSqliteHelpers:
    def test_get_db_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "sub", "test.db")
            db = get_db(db_path)
            assert db is not None
            # WAL mode should be set
            mode = db.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode.lower() == "wal"
            db.close()

    def test_get_db_row_factory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = get_db(db_path)
            db.execute("CREATE TABLE t (id INTEGER, name TEXT)")
            db.execute("INSERT INTO t VALUES (1, 'test')")
            row = db.execute("SELECT * FROM t").fetchone()
            assert row["id"] == 1
            assert row["name"] == "test"
            db.close()
