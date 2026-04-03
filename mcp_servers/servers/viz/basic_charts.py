"""Basic chart tools and implementations for VizServer."""
import logging
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


def register_basic_tools(server):
    """Register basic chart tools on the VizServer instance."""

    @server.mcp.tool()
    def viz_line_chart(
        data: List[Dict[str, Any]],
        x_col: str = "date",
        y_col: str = "value",
        group_col: str = None,
        title: str = "Line Chart",
        x_label: str = "",
        y_label: str = "",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        라인 차트 생성 (시계열 데이터)

        Args:
            data: 데이터 리스트 [{"date": "2024-01-01", "value": 100, "city": "Seoul"}, ...]
            x_col: X축 컬럼명
            y_col: Y축 컬럼명
            group_col: 그룹 컬럼명 (멀티 시리즈)
            title: 차트 제목
            x_label: X축 레이블
            y_label: Y축 레이블
            save_html: HTML 파일 저장 여부
            save_png: PNG 파일 저장 여부

        Returns:
            차트 정보 및 파일 경로
        """
        return _create_line_chart(
            server, data, x_col, y_col, group_col, title, x_label, y_label,
            save_html, save_png
        )

    @server.mcp.tool()
    def viz_bar_chart(
        data: List[Dict[str, Any]],
        x_col: str = "category",
        y_col: str = "value",
        title: str = "Bar Chart",
        horizontal: bool = False,
        color_col: str = None,
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        바 차트 생성 (비교 데이터)

        Args:
            data: 데이터 리스트 [{"category": "A", "value": 100}, ...]
            x_col: X축 컬럼명
            y_col: Y축 컬럼명
            title: 차트 제목
            horizontal: 가로 바 차트 여부
            color_col: 색상 구분 컬럼
            save_html: HTML 파일 저장 여부
            save_png: PNG 파일 저장 여부

        Returns:
            차트 정보 및 파일 경로
        """
        return _create_bar_chart(
            server, data, x_col, y_col, title, horizontal, color_col,
            save_html, save_png
        )

    @server.mcp.tool()
    def viz_candlestick(
        data: List[Dict[str, Any]],
        date_col: str = "date",
        open_col: str = "open",
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        volume_col: str = None,
        title: str = "Candlestick Chart",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        캔들스틱 차트 생성 (주가 데이터)

        Args:
            data: OHLC 데이터 리스트
            date_col: 날짜 컬럼명
            open_col: 시가 컬럼명
            high_col: 고가 컬럼명
            low_col: 저가 컬럼명
            close_col: 종가 컬럼명
            volume_col: 거래량 컬럼명 (선택)
            title: 차트 제목
            save_html: HTML 파일 저장 여부
            save_png: PNG 파일 저장 여부

        Returns:
            차트 정보 및 파일 경로
        """
        return _create_candlestick(
            server, data, date_col, open_col, high_col, low_col, close_col,
            volume_col, title, save_html, save_png
        )

    @server.mcp.tool()
    def viz_heatmap(
        data: List[List[float]],
        x_labels: List[str],
        y_labels: List[str],
        title: str = "Heatmap",
        color_scale: str = "RdYlGn",
        show_values: bool = True,
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        히트맵 생성 (상관관계, 민감도 분석)

        Args:
            data: 2D 숫자 배열 [[1,2,3], [4,5,6], ...]
            x_labels: X축 레이블 리스트
            y_labels: Y축 레이블 리스트
            title: 차트 제목
            color_scale: 색상 스케일 (RdYlGn, RdBu, Viridis 등)
            show_values: 셀 값 표시 여부
            save_html: HTML 파일 저장 여부
            save_png: PNG 파일 저장 여부

        Returns:
            차트 정보 및 파일 경로
        """
        return _create_heatmap(
            server, data, x_labels, y_labels, title, color_scale,
            show_values, save_html, save_png
        )

    @server.mcp.tool()
    def viz_scatter(
        data: List[Dict[str, Any]],
        x_col: str,
        y_col: str,
        color_col: str = None,
        size_col: str = None,
        title: str = "Scatter Plot",
        x_label: str = "",
        y_label: str = "",
        add_trendline: bool = False,
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        산점도 생성 (상관관계 분석)

        Args:
            data: 데이터 리스트
            x_col: X축 컬럼명
            y_col: Y축 컬럼명
            color_col: 색상 구분 컬럼
            size_col: 크기 구분 컬럼
            title: 차트 제목
            x_label: X축 레이블
            y_label: Y축 레이블
            add_trendline: 추세선 추가 여부
            save_html: HTML 파일 저장 여부
            save_png: PNG 파일 저장 여부

        Returns:
            차트 정보 및 파일 경로
        """
        return _create_scatter(
            server, data, x_col, y_col, color_col, size_col, title,
            x_label, y_label, add_trendline, save_html, save_png
        )

    @server.mcp.tool()
    def viz_waterfall(
        data: List[Dict[str, Any]],
        category_col: str = "category",
        value_col: str = "value",
        title: str = "Waterfall Chart",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        워터폴 차트 생성 (밸류 브릿지)

        Args:
            data: 데이터 리스트 [{"category": "시작", "value": 100}, {"category": "+증가", "value": 20}, ...]
            category_col: 카테고리 컬럼명
            value_col: 값 컬럼명
            title: 차트 제목
            save_html: HTML 파일 저장 여부
            save_png: PNG 파일 저장 여부

        Returns:
            차트 정보 및 파일 경로
        """
        return _create_waterfall(
            server, data, category_col, value_col, title, save_html, save_png
        )

    @server.mcp.tool()
    def viz_dual_axis(
        data: List[Dict[str, Any]],
        x_col: str,
        y1_col: str,
        y2_col: str,
        title: str = "Dual Axis Chart",
        y1_label: str = "",
        y2_label: str = "",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        이중축 차트 생성 (다른 스케일 비교)

        Args:
            data: 데이터 리스트
            x_col: X축 컬럼명
            y1_col: 왼쪽 Y축 컬럼명
            y2_col: 오른쪽 Y축 컬럼명
            title: 차트 제목
            y1_label: 왼쪽 Y축 레이블
            y2_label: 오른쪽 Y축 레이블
            save_html: HTML 파일 저장 여부
            save_png: PNG 파일 저장 여부

        Returns:
            차트 정보 및 파일 경로
        """
        return _create_dual_axis(
            server, data, x_col, y1_col, y2_col, title, y1_label, y2_label,
            save_html, save_png
        )

    @server.mcp.tool()
    def viz_pie_chart(
        data: List[Dict[str, Any]],
        names_col: str = "category",
        values_col: str = "value",
        title: str = "Pie Chart",
        hole: float = 0.0,
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        파이/도넛 차트 생성

        Args:
            data: 데이터 리스트 [{"category": "A", "value": 30}, ...]
            names_col: 이름 컬럼명
            values_col: 값 컬럼명
            title: 차트 제목
            hole: 도넛 홀 크기 (0-1, 0이면 파이)
            save_html: HTML 파일 저장 여부
            save_png: PNG 파일 저장 여부

        Returns:
            차트 정보 및 파일 경로
        """
        return _create_pie_chart(
            server, data, names_col, values_col, title, hole, save_html, save_png
        )

    @server.mcp.tool()
    def viz_correlation_matrix(
        data: List[Dict[str, Any]],
        columns: List[str],
        title: str = "Correlation Matrix",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        상관관계 매트릭스 히트맵 생성

        Args:
            data: 데이터 리스트
            columns: 상관관계 계산할 컬럼 리스트
            title: 차트 제목
            save_html: HTML 파일 저장 여부
            save_png: PNG 파일 저장 여부

        Returns:
            상관계수 및 차트 정보
        """
        return _create_correlation_matrix(
            server, data, columns, title, save_html, save_png
        )

    @server.mcp.tool()
    def viz_sensitivity_heatmap(
        matrix: Dict[str, Dict[str, float]],
        title: str = "Sensitivity Analysis",
        x_label: str = "Terminal Growth Rate",
        y_label: str = "WACC",
        current_value: float = None,
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        DCF 민감도 분석 히트맵 (val_sensitivity_analysis 결과용)

        Args:
            matrix: 민감도 매트릭스 {"7.0%": {"1.0%": 75000, ...}, ...}
            title: 차트 제목
            x_label: X축 레이블
            y_label: Y축 레이블
            current_value: 현재 주가 (강조 표시용)
            save_html: HTML 파일 저장 여부
            save_png: PNG 파일 저장 여부

        Returns:
            차트 정보 및 파일 경로
        """
        return _create_sensitivity_heatmap(
            server, matrix, title, x_label, y_label, current_value,
            save_html, save_png
        )


# ========================================================================
# Implementation Functions
# ========================================================================

def _create_line_chart(server, data, x_col, y_col, group_col, title, x_label, y_label, save_html, save_png):
    """Create line chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("line")

        # Plotly
        if group_col and group_col in df.columns:
            fig = px.line(
                df, x=x_col, y=y_col, color=group_col,
                title=title, color_discrete_sequence=server.COLOR_SEQUENCE
            )
        else:
            fig = px.line(df, x=x_col, y=y_col, title=title)

        fig.update_layout(
            xaxis_title=x_label or x_col,
            yaxis_title=y_label or y_col,
            template="plotly_white",
            hovermode="x unified",
        )

        paths = server._save_plotly(fig, filename, save_html, save_png)

        return {
            "success": True,
            "chart_type": "line",
            "title": title,
            "data_points": len(df),
            "files": paths,
        }

    except Exception as e:
        logger.error(f"Line chart error: {e}")
        return {"error": True, "message": str(e)}


def _create_bar_chart(server, data, x_col, y_col, title, horizontal, color_col, save_html, save_png):
    """Create bar chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("bar")

        if horizontal:
            fig = px.bar(
                df, y=x_col, x=y_col, color=color_col,
                title=title, orientation='h',
                color_discrete_sequence=server.COLOR_SEQUENCE
            )
        else:
            fig = px.bar(
                df, x=x_col, y=y_col, color=color_col,
                title=title,
                color_discrete_sequence=server.COLOR_SEQUENCE
            )

        fig.update_layout(template="plotly_white")

        paths = server._save_plotly(fig, filename, save_html, save_png)

        return {
            "success": True,
            "chart_type": "bar",
            "title": title,
            "data_points": len(df),
            "files": paths,
        }

    except Exception as e:
        logger.error(f"Bar chart error: {e}")
        return {"error": True, "message": str(e)}


def _create_candlestick(server, data, date_col, open_col, high_col, low_col, close_col, volume_col, title, save_html, save_png):
    """Create candlestick chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("candlestick")

        # Create figure with or without volume
        if volume_col and volume_col in df.columns:
            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.7, 0.3]
            )

            # Candlestick
            fig.add_trace(
                go.Candlestick(
                    x=df[date_col],
                    open=df[open_col],
                    high=df[high_col],
                    low=df[low_col],
                    close=df[close_col],
                    name="Price"
                ),
                row=1, col=1
            )

            # Volume
            colors = ['red' if row[close_col] < row[open_col] else 'green'
                     for _, row in df.iterrows()]
            fig.add_trace(
                go.Bar(x=df[date_col], y=df[volume_col], name="Volume",
                      marker_color=colors),
                row=2, col=1
            )

            fig.update_layout(
                title=title,
                xaxis_rangeslider_visible=False,
                template="plotly_white",
            )
        else:
            fig = go.Figure(data=[go.Candlestick(
                x=df[date_col],
                open=df[open_col],
                high=df[high_col],
                low=df[low_col],
                close=df[close_col],
            )])

            fig.update_layout(
                title=title,
                xaxis_rangeslider_visible=False,
                template="plotly_white",
            )

        paths = server._save_plotly(fig, filename, save_html, save_png)

        return {
            "success": True,
            "chart_type": "candlestick",
            "title": title,
            "data_points": len(df),
            "files": paths,
        }

    except Exception as e:
        logger.error(f"Candlestick error: {e}")
        return {"error": True, "message": str(e)}


def _create_heatmap(server, data, x_labels, y_labels, title, color_scale, show_values, save_html, save_png):
    """Create heatmap."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        filename = server._generate_filename("heatmap")
        z_data = np.array(data)

        fig = go.Figure(data=go.Heatmap(
            z=z_data,
            x=x_labels,
            y=y_labels,
            colorscale=color_scale,
            text=np.round(z_data, 2) if show_values else None,
            texttemplate="%{text}" if show_values else None,
            textfont={"size": 10},
            hovertemplate="X: %{x}<br>Y: %{y}<br>Value: %{z:.2f}<extra></extra>",
        ))

        fig.update_layout(
            title=title,
            template="plotly_white",
        )

        paths = server._save_plotly(fig, filename, save_html, save_png)

        return {
            "success": True,
            "chart_type": "heatmap",
            "title": title,
            "dimensions": f"{len(y_labels)} x {len(x_labels)}",
            "files": paths,
        }

    except Exception as e:
        logger.error(f"Heatmap error: {e}")
        return {"error": True, "message": str(e)}


def _create_scatter(server, data, x_col, y_col, color_col, size_col, title, x_label, y_label, add_trendline, save_html, save_png):
    """Create scatter plot."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("scatter")

        trendline = "ols" if add_trendline else None

        fig = px.scatter(
            df, x=x_col, y=y_col,
            color=color_col, size=size_col,
            title=title, trendline=trendline,
            color_discrete_sequence=server.COLOR_SEQUENCE
        )

        fig.update_layout(
            xaxis_title=x_label or x_col,
            yaxis_title=y_label or y_col,
            template="plotly_white",
        )

        paths = server._save_plotly(fig, filename, save_html, save_png)

        # Calculate correlation if numeric
        correlation = None
        if df[x_col].dtype in ['float64', 'int64'] and df[y_col].dtype in ['float64', 'int64']:
            correlation = df[x_col].corr(df[y_col])

        return {
            "success": True,
            "chart_type": "scatter",
            "title": title,
            "data_points": len(df),
            "correlation": round(correlation, 4) if correlation is not None else None,
            "files": paths,
        }

    except Exception as e:
        logger.error(f"Scatter error: {e}")
        return {"error": True, "message": str(e)}


def _create_waterfall(server, data, category_col, value_col, title, save_html, save_png):
    """Create waterfall chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("waterfall")

        # Determine measure type (relative, total, or absolute)
        measures = []
        for i, row in df.iterrows():
            cat = str(row[category_col]).lower()
            if 'total' in cat or 'net' in cat or i == len(df) - 1:
                measures.append("total")
            elif i == 0:
                measures.append("absolute")
            else:
                measures.append("relative")

        fig = go.Figure(go.Waterfall(
            name="",
            orientation="v",
            measure=measures,
            x=df[category_col],
            y=df[value_col],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": server.COLORS["success"]}},
            decreasing={"marker": {"color": server.COLORS["danger"]}},
            totals={"marker": {"color": server.COLORS["primary"]}},
        ))

        fig.update_layout(
            title=title,
            template="plotly_white",
            showlegend=False,
        )

        paths = server._save_plotly(fig, filename, save_html, save_png)

        return {
            "success": True,
            "chart_type": "waterfall",
            "title": title,
            "steps": len(df),
            "files": paths,
        }

    except Exception as e:
        logger.error(f"Waterfall error: {e}")
        return {"error": True, "message": str(e)}


def _create_dual_axis(server, data, x_col, y1_col, y2_col, title, y1_label, y2_label, save_html, save_png):
    """Create dual-axis chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("dual_axis")

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Primary Y-axis
        fig.add_trace(
            go.Scatter(
                x=df[x_col], y=df[y1_col],
                name=y1_label or y1_col,
                line=dict(color=server.COLORS["primary"])
            ),
            secondary_y=False,
        )

        # Secondary Y-axis
        fig.add_trace(
            go.Scatter(
                x=df[x_col], y=df[y2_col],
                name=y2_label or y2_col,
                line=dict(color=server.COLORS["secondary"])
            ),
            secondary_y=True,
        )

        fig.update_layout(
            title=title,
            template="plotly_white",
            hovermode="x unified",
        )

        fig.update_yaxes(title_text=y1_label or y1_col, secondary_y=False)
        fig.update_yaxes(title_text=y2_label or y2_col, secondary_y=True)

        paths = server._save_plotly(fig, filename, save_html, save_png)

        return {
            "success": True,
            "chart_type": "dual_axis",
            "title": title,
            "data_points": len(df),
            "y1_column": y1_col,
            "y2_column": y2_col,
            "files": paths,
        }

    except Exception as e:
        logger.error(f"Dual axis error: {e}")
        return {"error": True, "message": str(e)}


def _create_pie_chart(server, data, names_col, values_col, title, hole, save_html, save_png):
    """Create pie/donut chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("pie")

        fig = px.pie(
            df, names=names_col, values=values_col,
            title=title, hole=hole,
            color_discrete_sequence=server.COLOR_SEQUENCE
        )

        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(template="plotly_white")

        paths = server._save_plotly(fig, filename, save_html, save_png)

        return {
            "success": True,
            "chart_type": "donut" if hole > 0 else "pie",
            "title": title,
            "categories": len(df),
            "files": paths,
        }

    except Exception as e:
        logger.error(f"Pie chart error: {e}")
        return {"error": True, "message": str(e)}


def _create_correlation_matrix(server, data, columns, title, save_html, save_png):
    """Create correlation matrix heatmap."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("correlation")

        # Calculate correlation matrix
        corr_matrix = df[columns].corr()

        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=columns,
            y=columns,
            colorscale="RdBu",
            zmid=0,
            text=np.round(corr_matrix.values, 2),
            texttemplate="%{text}",
            textfont={"size": 10},
            hovertemplate="%{x} vs %{y}: %{z:.3f}<extra></extra>",
            colorbar=dict(title="Correlation"),
        ))

        fig.update_layout(
            title=title,
            template="plotly_white",
        )

        paths = server._save_plotly(fig, filename, save_html, save_png)

        return {
            "success": True,
            "chart_type": "correlation_matrix",
            "title": title,
            "variables": columns,
            "correlation_matrix": corr_matrix.to_dict(),
            "files": paths,
        }

    except Exception as e:
        logger.error(f"Correlation matrix error: {e}")
        return {"error": True, "message": str(e)}


def _create_sensitivity_heatmap(server, matrix, title, x_label, y_label, current_value, save_html, save_png):
    """Create sensitivity analysis heatmap from DCF results."""
    if not matrix:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        filename = server._generate_filename("sensitivity")

        # Convert nested dict to arrays
        y_labels = list(matrix.keys())
        x_labels = list(matrix[y_labels[0]].keys())
        z_data = [[matrix[y][x] for x in x_labels] for y in y_labels]

        # Create annotation text
        text = [[f"{int(matrix[y][x]):,}" for x in x_labels] for y in y_labels]

        fig = go.Figure(data=go.Heatmap(
            z=z_data,
            x=x_labels,
            y=y_labels,
            colorscale="RdYlGn",
            text=text,
            texttemplate="%{text}",
            textfont={"size": 9},
            hovertemplate=f"{y_label}: %{{y}}<br>{x_label}: %{{x}}<br>Value: %{{z:,.0f}}<extra></extra>",
            colorbar=dict(title="Share Price"),
        ))

        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label,
            template="plotly_white",
        )

        # Add current price annotation if provided
        if current_value:
            fig.add_annotation(
                text=f"Current: {current_value:,.0f}",
                xref="paper", yref="paper",
                x=1.15, y=0.5,
                showarrow=False,
                font=dict(size=12, color="black"),
            )

        paths = server._save_plotly(fig, filename, save_html, save_png)

        return {
            "success": True,
            "chart_type": "sensitivity_heatmap",
            "title": title,
            "wacc_range": y_labels,
            "growth_range": x_labels,
            "current_value": current_value,
            "files": paths,
        }

    except Exception as e:
        logger.error(f"Sensitivity heatmap error: {e}")
        return {"error": True, "message": str(e)}
