"""Hierarchical chart tools and implementations for VizServer."""
import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


def register_hierarchical_tools(server):
    """Register hierarchical chart tools on the VizServer instance."""

    @server.mcp.tool()
    def viz_treemap(
        data: List[Dict[str, Any]],
        path_cols: List[str] = None,
        value_col: str = "value",
        color_col: str = None,
        title: str = "Treemap",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        트리맵 생성 (계층적 비율 시각화 — 시가총액, 포트폴리오, 섹터 비중)

        Args:
            data: 데이터 리스트 [{"sector": "IT", "stock": "삼성전자", "value": 500, "change": 2.3}, ...]
            path_cols: 계층 경로 컬럼 리스트 ["sector", "stock"]
            value_col: 크기 컬럼
            color_col: 색상 컬럼 (수익률 등)
            title: 차트 제목
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_treemap(server, data, path_cols, value_col, color_col, title, save_html, save_png)

    @server.mcp.tool()
    def viz_sunburst(
        data: List[Dict[str, Any]],
        path_cols: List[str] = None,
        value_col: str = "value",
        color_col: str = None,
        title: str = "Sunburst Chart",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        선버스트 차트 생성 (동심원 계층 구조 — 섹터→산업→종목)

        Args:
            data: 데이터 리스트 [{"sector": "IT", "industry": "반도체", "stock": "삼성전자", "value": 500}, ...]
            path_cols: 계층 경로 컬럼 ["sector", "industry", "stock"]
            value_col: 크기 컬럼
            color_col: 색상 컬럼
            title: 차트 제목
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_sunburst(server, data, path_cols, value_col, color_col, title, save_html, save_png)

    @server.mcp.tool()
    def viz_funnel(
        data: List[Dict[str, Any]],
        stage_col: str = "stage",
        value_col: str = "value",
        title: str = "Funnel Chart",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        퍼널 차트 생성 (단계별 전환율, 딜 파이프라인)

        Args:
            data: 데이터 리스트 [{"stage": "리드", "value": 1000}, {"stage": "상담", "value": 500}, ...]
            stage_col: 단계 컬럼
            value_col: 값 컬럼
            title: 차트 제목
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_funnel(server, data, stage_col, value_col, title, save_html, save_png)

    @server.mcp.tool()
    def viz_gauge(
        value: float,
        min_val: float = 0,
        max_val: float = 100,
        title: str = "Gauge",
        thresholds: List[Dict[str, Any]] = None,
        suffix: str = "",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        게이지 차트 생성 (KPI 대시보드, 공포탐욕지수)

        Args:
            value: 현재 값
            min_val: 최소값
            max_val: 최대값
            title: 차트 제목
            thresholds: 구간 설정 [{"range": [0,30], "color": "red"}, {"range": [30,70], "color": "yellow"}, ...]
            suffix: 단위 접미사 (%, 점, 원 등)
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_gauge(server, value, min_val, max_val, title, thresholds, suffix, save_html, save_png)

    @server.mcp.tool()
    def viz_bullet(
        data: List[Dict[str, Any]],
        label_col: str = "label",
        actual_col: str = "actual",
        target_col: str = "target",
        title: str = "Bullet Chart",
        ranges_cols: List[str] = None,
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        불릿 차트 생성 (실적 vs 목표, KPI 추적)

        Args:
            data: [{"label": "매출", "actual": 85, "target": 100, "poor": 50, "ok": 75, "good": 100}, ...]
            label_col: 레이블 컬럼
            actual_col: 실적 컬럼
            target_col: 목표 컬럼
            title: 차트 제목
            ranges_cols: 배경 범위 컬럼 ["poor", "ok", "good"]
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_bullet(server, data, label_col, actual_col, target_col, title, ranges_cols, save_html, save_png)

    @server.mcp.tool()
    def viz_sankey(
        data: List[Dict[str, Any]],
        source_col: str = "source",
        target_col: str = "target",
        value_col: str = "value",
        title: str = "Sankey Diagram",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        산키 다이어그램 생성 (자금 흐름, 무역 흐름, 포트폴리오 리밸런싱)

        Args:
            data: 흐름 데이터 [{"source": "수출", "target": "미국", "value": 500}, ...]
            source_col: 출발 노드 컬럼
            target_col: 도착 노드 컬럼
            value_col: 흐름량 컬럼
            title: 차트 제목
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_sankey(server, data, source_col, target_col, value_col, title, save_html, save_png)


# ========================================================================
# Implementation Functions
# ========================================================================

def _create_treemap(server, data, path_cols, value_col, color_col, title, save_html, save_png):
    """Create treemap."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("treemap")

        if not path_cols:
            path_cols = [c for c in df.columns if c != value_col and c != color_col][:2]

        fig = px.treemap(
            df, path=[px.Constant("All")] + path_cols,
            values=value_col, color=color_col,
            title=title, color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0 if color_col else None,
        )
        fig.update_layout(template="plotly_white")
        fig.update_traces(textinfo="label+value+percent parent")
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "treemap", "title": title, "data_points": len(df), "hierarchy": path_cols, "files": paths}
    except Exception as e:
        logger.error(f"Treemap error: {e}")
        return {"error": True, "message": str(e)}


def _create_sunburst(server, data, path_cols, value_col, color_col, title, save_html, save_png):
    """Create sunburst chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("sunburst")

        if not path_cols:
            path_cols = [c for c in df.columns if c != value_col and c != color_col][:3]

        fig = px.sunburst(
            df, path=path_cols, values=value_col,
            color=color_col, title=title,
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0 if color_col else None,
        )
        fig.update_layout(template="plotly_white")
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "sunburst", "title": title, "data_points": len(df), "hierarchy": path_cols, "files": paths}
    except Exception as e:
        logger.error(f"Sunburst error: {e}")
        return {"error": True, "message": str(e)}


def _create_funnel(server, data, stage_col, value_col, title, save_html, save_png):
    """Create funnel chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("funnel")

        fig = px.funnel(
            df, x=value_col, y=stage_col, title=title,
            color_discrete_sequence=server.COLOR_SEQUENCE,
        )
        fig.update_layout(template="plotly_white")
        paths = server._save_plotly(fig, filename, save_html, save_png)

        # Calculate conversion rates
        values = df[value_col].tolist()
        conversions = []
        for i in range(1, len(values)):
            rate = (values[i] / values[i-1] * 100) if values[i-1] != 0 else 0
            conversions.append({"from": df[stage_col].iloc[i-1], "to": df[stage_col].iloc[i], "rate": round(rate, 1)})

        return {"success": True, "chart_type": "funnel", "title": title, "stages": len(df), "conversion_rates": conversions, "files": paths}
    except Exception as e:
        logger.error(f"Funnel error: {e}")
        return {"error": True, "message": str(e)}


def _create_gauge(server, value, min_val, max_val, title, thresholds, suffix, save_html, save_png):
    """Create gauge chart."""
    try:
        filename = server._generate_filename("gauge")

        # Default thresholds (red/yellow/green)
        if not thresholds:
            r = max_val - min_val
            thresholds = [
                {"range": [min_val, min_val + r * 0.33], "color": "#F44336"},
                {"range": [min_val + r * 0.33, min_val + r * 0.66], "color": "#FFC107"},
                {"range": [min_val + r * 0.66, max_val], "color": "#4CAF50"},
            ]

        steps = [{"range": t["range"], "color": t["color"]} for t in thresholds]

        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=value,
            number={"suffix": suffix},
            title={"text": title},
            gauge={
                "axis": {"range": [min_val, max_val]},
                "bar": {"color": server.COLORS["primary"]},
                "steps": steps,
                "threshold": {
                    "line": {"color": "black", "width": 4},
                    "thickness": 0.75,
                    "value": value,
                },
            },
        ))

        fig.update_layout(template="plotly_white")
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "gauge", "title": title, "value": value, "range": [min_val, max_val], "files": paths}
    except Exception as e:
        logger.error(f"Gauge error: {e}")
        return {"error": True, "message": str(e)}


def _create_bullet(server, data, label_col, actual_col, target_col, title, ranges_cols, save_html, save_png):
    """Create bullet chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("bullet")

        fig = make_subplots(
            rows=len(df), cols=1,
            subplot_titles=df[label_col].tolist(),
            vertical_spacing=0.12,
        )

        for i, (_, row) in enumerate(df.iterrows(), 1):
            actual = row[actual_col]
            target = row[target_col]

            # Background ranges
            if ranges_cols and all(c in df.columns for c in ranges_cols):
                prev = 0
                colors = ["#ECEFF1", "#CFD8DC", "#B0BEC5"]
                for j, rc in enumerate(ranges_cols):
                    fig.add_trace(go.Bar(
                        x=[row[rc] - prev], y=[row[label_col]], orientation='h',
                        marker_color=colors[j % len(colors)],
                        showlegend=False, base=prev,
                    ), row=i, col=1)
                    prev = row[rc]

            # Actual bar
            fig.add_trace(go.Bar(
                x=[actual], y=[row[label_col]], orientation='h',
                marker_color=server.COLORS["primary"],
                width=0.4, showlegend=False,
            ), row=i, col=1)

            # Target line
            fig.add_trace(go.Scatter(
                x=[target, target], y=[row[label_col], row[label_col]],
                mode='markers', marker=dict(symbol='line-ns', size=20, color='black', line_width=3),
                showlegend=False,
            ), row=i, col=1)

        fig.update_layout(title=title, template="plotly_white", barmode='overlay', height=150 * len(df) + 100)
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "bullet", "title": title, "items": len(df), "files": paths}
    except Exception as e:
        logger.error(f"Bullet error: {e}")
        return {"error": True, "message": str(e)}


def _create_sankey(server, data, source_col, target_col, value_col, title, save_html, save_png):
    """Create sankey diagram."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("sankey")

        # Build node list
        all_nodes = list(pd.concat([df[source_col], df[target_col]]).unique())
        node_map = {n: i for i, n in enumerate(all_nodes)}

        # Assign colors
        n = len(all_nodes)
        node_colors = [server.COLOR_SEQUENCE[i % len(server.COLOR_SEQUENCE)] for i in range(n)]

        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15, thickness=20,
                line=dict(color="black", width=0.5),
                label=all_nodes,
                color=node_colors,
            ),
            link=dict(
                source=[node_map[s] for s in df[source_col]],
                target=[node_map[t] for t in df[target_col]],
                value=df[value_col].tolist(),
            ),
        )])

        fig.update_layout(title=title, template="plotly_white", font_size=12)
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "sankey", "title": title, "nodes": len(all_nodes), "flows": len(df), "files": paths}
    except Exception as e:
        logger.error(f"Sankey error: {e}")
        return {"error": True, "message": str(e)}
