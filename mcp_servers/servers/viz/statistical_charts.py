"""Statistical chart tools and implementations for VizServer."""
import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


def register_statistical_tools(server):
    """Register statistical chart tools on the VizServer instance."""

    @server.mcp.tool()
    def viz_area_chart(
        data: List[Dict[str, Any]],
        x_col: str = "date",
        y_col: str = "value",
        group_col: str = None,
        title: str = "Area Chart",
        stacked: bool = True,
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        영역 차트 생성 (누적 트렌드, 포트폴리오 구성 변화)

        Args:
            data: 데이터 리스트 [{"date": "2024-01", "value": 100, "sector": "IT"}, ...]
            x_col: X축 컬럼명
            y_col: Y축 컬럼명
            group_col: 그룹 컬럼명 (스택 시리즈)
            title: 차트 제목
            stacked: 스택 여부 (True=누적, False=겹침)
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_area_chart(server, data, x_col, y_col, group_col, title, stacked, save_html, save_png)

    @server.mcp.tool()
    def viz_stacked_bar(
        data: List[Dict[str, Any]],
        x_col: str = "category",
        y_col: str = "value",
        stack_col: str = "group",
        title: str = "Stacked Bar Chart",
        horizontal: bool = False,
        normalized: bool = False,
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        누적 막대 차트 생성 (구성비 분석, 부문별 비교)

        Args:
            data: 데이터 리스트 [{"category": "2024Q1", "value": 100, "group": "매출"}, ...]
            x_col: X축 컬럼명
            y_col: Y축 컬럼명
            stack_col: 스택 구분 컬럼
            title: 차트 제목
            horizontal: 가로 방향
            normalized: 100% 정규화 여부
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_stacked_bar(server, data, x_col, y_col, stack_col, title, horizontal, normalized, save_html, save_png)

    @server.mcp.tool()
    def viz_histogram(
        data: List[Dict[str, Any]],
        value_col: str = "value",
        bins: int = 30,
        group_col: str = None,
        title: str = "Histogram",
        x_label: str = "",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        히스토그램 생성 (수익률 분포, 주가 분포 분석)

        Args:
            data: 데이터 리스트 [{"value": 0.05}, {"value": -0.02}, ...]
            value_col: 값 컬럼명
            bins: 구간 수
            group_col: 그룹별 겹침 히스토그램
            title: 차트 제목
            x_label: X축 레이블
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_histogram(server, data, value_col, bins, group_col, title, x_label, save_html, save_png)

    @server.mcp.tool()
    def viz_box_plot(
        data: List[Dict[str, Any]],
        value_col: str = "value",
        group_col: str = "category",
        title: str = "Box Plot",
        show_points: bool = False,
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        박스플롯 생성 (분포 비교, 이상치 탐지)

        Args:
            data: 데이터 리스트 [{"value": 100, "category": "IT"}, ...]
            value_col: 값 컬럼명
            group_col: 그룹 컬럼명
            title: 차트 제목
            show_points: 개별 데이터 포인트 표시
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_box_plot(server, data, value_col, group_col, title, show_points, save_html, save_png)

    @server.mcp.tool()
    def viz_violin(
        data: List[Dict[str, Any]],
        value_col: str = "value",
        group_col: str = "category",
        title: str = "Violin Plot",
        show_box: bool = True,
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        바이올린 플롯 생성 (분포 형태 비교, 밀도+상자수염 결합)

        Args:
            data: 데이터 리스트 [{"value": 100, "category": "IT"}, ...]
            value_col: 값 컬럼명
            group_col: 그룹 컬럼명
            title: 차트 제목
            show_box: 내부 상자수염 표시
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_violin(server, data, value_col, group_col, title, show_box, save_html, save_png)

    @server.mcp.tool()
    def viz_density(
        data: List[Dict[str, Any]],
        value_col: str = "value",
        group_col: str = None,
        title: str = "Density Plot",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        밀도 플롯 생성 (확률밀도 분포, 수익률 분포 비교)

        Args:
            data: [{"value": 0.05, "group": "KOSPI"}, ...]
            value_col: 값 컬럼
            group_col: 그룹 컬럼 (여러 분포 겹쳐서 비교)
            title: 차트 제목
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_density(server, data, value_col, group_col, title, save_html, save_png)


# ========================================================================
# Implementation Functions
# ========================================================================

def _create_area_chart(server, data, x_col, y_col, group_col, title, stacked, save_html, save_png):
    """Create area chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("area")

        if group_col and group_col in df.columns:
            fig = px.area(
                df, x=x_col, y=y_col, color=group_col,
                title=title, color_discrete_sequence=server.COLOR_SEQUENCE,
                groupnorm="percent" if stacked else None,
            )
            if not stacked:
                fig.update_traces(opacity=0.6)
        else:
            fig = px.area(df, x=x_col, y=y_col, title=title)

        fig.update_layout(template="plotly_white", hovermode="x unified")
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "area", "title": title, "data_points": len(df), "files": paths}
    except Exception as e:
        logger.error(f"Area chart error: {e}")
        return {"error": True, "message": str(e)}


def _create_stacked_bar(server, data, x_col, y_col, stack_col, title, horizontal, normalized, save_html, save_png):
    """Create stacked bar chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("stacked_bar")
        barnorm = "percent" if normalized else None

        if horizontal:
            fig = px.bar(
                df, y=x_col, x=y_col, color=stack_col, title=title,
                orientation='h', barmode='stack',
                color_discrete_sequence=server.COLOR_SEQUENCE,
            )
        else:
            fig = px.bar(
                df, x=x_col, y=y_col, color=stack_col, title=title,
                barmode='stack', color_discrete_sequence=server.COLOR_SEQUENCE,
            )

        if barnorm:
            fig.update_layout(barnorm=barnorm)
        fig.update_layout(template="plotly_white")
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "stacked_bar", "title": title, "data_points": len(df), "normalized": normalized, "files": paths}
    except Exception as e:
        logger.error(f"Stacked bar error: {e}")
        return {"error": True, "message": str(e)}


def _create_histogram(server, data, value_col, bins, group_col, title, x_label, save_html, save_png):
    """Create histogram."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("histogram")

        fig = px.histogram(
            df, x=value_col, nbins=bins, color=group_col,
            title=title, barmode="overlay",
            color_discrete_sequence=server.COLOR_SEQUENCE,
        )
        if group_col:
            fig.update_traces(opacity=0.7)
        fig.update_layout(
            xaxis_title=x_label or value_col,
            yaxis_title="빈도",
            template="plotly_white",
        )
        paths = server._save_plotly(fig, filename, save_html, save_png)

        stats = {
            "mean": float(df[value_col].mean()),
            "std": float(df[value_col].std()),
            "median": float(df[value_col].median()),
            "min": float(df[value_col].min()),
            "max": float(df[value_col].max()),
        }
        return {"success": True, "chart_type": "histogram", "title": title, "data_points": len(df), "statistics": stats, "files": paths}
    except Exception as e:
        logger.error(f"Histogram error: {e}")
        return {"error": True, "message": str(e)}


def _create_box_plot(server, data, value_col, group_col, title, show_points, save_html, save_png):
    """Create box plot."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("box")
        points = "all" if show_points else "outliers"

        fig = px.box(
            df, x=group_col, y=value_col, title=title,
            points=points, color=group_col,
            color_discrete_sequence=server.COLOR_SEQUENCE,
        )
        fig.update_layout(template="plotly_white", showlegend=False)
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "box_plot", "title": title, "groups": df[group_col].nunique(), "data_points": len(df), "files": paths}
    except Exception as e:
        logger.error(f"Box plot error: {e}")
        return {"error": True, "message": str(e)}


def _create_violin(server, data, value_col, group_col, title, show_box, save_html, save_png):
    """Create violin plot."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("violin")

        fig = px.violin(
            df, x=group_col, y=value_col, title=title,
            box=show_box, points="all", color=group_col,
            color_discrete_sequence=server.COLOR_SEQUENCE,
        )
        fig.update_layout(template="plotly_white", showlegend=False)
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "violin", "title": title, "groups": df[group_col].nunique(), "files": paths}
    except Exception as e:
        logger.error(f"Violin error: {e}")
        return {"error": True, "message": str(e)}


def _create_density(server, data, value_col, group_col, title, save_html, save_png):
    """Create density plot using histogram with KDE-like smoothing."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("density")

        fig = go.Figure()

        if group_col and group_col in df.columns:
            for i, grp in enumerate(df[group_col].unique()):
                grp_data = df[df[group_col] == grp][value_col].dropna()
                color = server.COLOR_SEQUENCE[i % len(server.COLOR_SEQUENCE)]

                # KDE using numpy
                from scipy.stats import gaussian_kde
                kde = gaussian_kde(grp_data)
                x_range = np.linspace(grp_data.min(), grp_data.max(), 200)
                fig.add_trace(go.Scatter(
                    x=x_range, y=kde(x_range), mode='lines',
                    fill='tozeroy', name=str(grp),
                    line=dict(color=color, width=2), opacity=0.6,
                ))
        else:
            vals = df[value_col].dropna()
            from scipy.stats import gaussian_kde
            kde = gaussian_kde(vals)
            x_range = np.linspace(vals.min(), vals.max(), 200)
            fig.add_trace(go.Scatter(
                x=x_range, y=kde(x_range), mode='lines',
                fill='tozeroy', name=value_col,
                line=dict(color=server.COLORS["primary"], width=2),
            ))

        fig.update_layout(title=title, template="plotly_white", xaxis_title=value_col, yaxis_title="밀도")
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "density", "title": title, "data_points": len(df), "files": paths}
    except Exception as e:
        logger.error(f"Density error: {e}")
        return {"error": True, "message": str(e)}
