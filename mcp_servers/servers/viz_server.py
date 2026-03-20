"""
Visualization MCP Server - Interactive Charts and Static Images.

Provides tools for creating financial visualizations:
- Candlestick charts (stock prices)
- Line charts (time series)
- Bar charts (comparisons)
- Heatmaps (correlation, sensitivity)
- Scatter plots (relationships)
- Waterfall charts (value bridges)
- Dual-axis charts (multi-metric)

Dual output: Plotly HTML (interactive) + Matplotlib PNG (static)

Run standalone: python -m mcp_servers.servers.viz_server
"""
import base64
import io
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from fastmcp import FastMCP

from mcp_servers.core.cache_manager import CacheManager, get_cache

logger = logging.getLogger(__name__)

# Output directory for charts
CHARTS_DIR = PROJECT_ROOT / "output" / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)


class VizServer:
    """Visualization MCP Server for financial charts."""

    # Color palette for consistent styling
    COLORS = {
        "primary": "#2196F3",
        "secondary": "#FF9800",
        "success": "#4CAF50",
        "danger": "#F44336",
        "warning": "#FFC107",
        "info": "#00BCD4",
        "dark": "#37474F",
        "light": "#ECEFF1",
    }

    # Color sequence for multi-series
    COLOR_SEQUENCE = [
        "#2196F3", "#FF9800", "#4CAF50", "#F44336",
        "#9C27B0", "#00BCD4", "#795548", "#607D8B",
        "#E91E63", "#3F51B5",
    ]

    def __init__(self, cache: CacheManager = None):
        """
        Initialize Visualization server.

        Args:
            cache: Cache manager instance
        """
        self._cache = cache or get_cache()
        self._setup_matplotlib()

        # Create FastMCP server
        self.mcp = FastMCP("viz")
        self._register_tools()

        logger.info("Visualization MCP Server initialized")

    def _setup_matplotlib(self) -> None:
        """Setup matplotlib for Korean font support."""
        # Try to find Korean font
        korean_fonts = ['Malgun Gothic', 'NanumGothic', 'AppleGothic', 'Noto Sans KR']

        for font_name in korean_fonts:
            try:
                font_path = fm.findfont(fm.FontProperties(family=font_name))
                if font_path and 'ttf' in font_path.lower():
                    plt.rcParams['font.family'] = font_name
                    plt.rcParams['axes.unicode_minus'] = False
                    logger.info(f"Using Korean font: {font_name}")
                    return
            except Exception:
                continue

        logger.warning("Korean font not found, using default")

    def _register_tools(self) -> None:
        """Register MCP tools."""

        @self.mcp.tool()
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
            return self.create_line_chart(
                data, x_col, y_col, group_col, title, x_label, y_label,
                save_html, save_png
            )

        @self.mcp.tool()
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
            return self.create_bar_chart(
                data, x_col, y_col, title, horizontal, color_col,
                save_html, save_png
            )

        @self.mcp.tool()
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
            return self.create_candlestick(
                data, date_col, open_col, high_col, low_col, close_col,
                volume_col, title, save_html, save_png
            )

        @self.mcp.tool()
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
            return self.create_heatmap(
                data, x_labels, y_labels, title, color_scale,
                show_values, save_html, save_png
            )

        @self.mcp.tool()
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
            return self.create_scatter(
                data, x_col, y_col, color_col, size_col, title,
                x_label, y_label, add_trendline, save_html, save_png
            )

        @self.mcp.tool()
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
            return self.create_waterfall(
                data, category_col, value_col, title, save_html, save_png
            )

        @self.mcp.tool()
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
            return self.create_dual_axis(
                data, x_col, y1_col, y2_col, title, y1_label, y2_label,
                save_html, save_png
            )

        @self.mcp.tool()
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
            return self.create_pie_chart(
                data, names_col, values_col, title, hole, save_html, save_png
            )

        @self.mcp.tool()
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
            return self.create_correlation_matrix(
                data, columns, title, save_html, save_png
            )

        @self.mcp.tool()
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
            return self.create_sensitivity_heatmap(
                matrix, title, x_label, y_label, current_value,
                save_html, save_png
            )

    # ========================================================================
    # Implementation Methods
    # ========================================================================

    def _generate_filename(self, chart_type: str) -> str:
        """Generate unique filename for chart."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{chart_type}_{timestamp}"

    def _save_plotly(self, fig: go.Figure, filename: str, save_html: bool, save_png: bool) -> Dict[str, str]:
        """Save Plotly figure to files."""
        paths = {}

        if save_html:
            html_path = CHARTS_DIR / f"{filename}.html"
            fig.write_html(str(html_path))
            paths["html"] = str(html_path)
            logger.info(f"Saved HTML: {html_path}")

        if save_png:
            try:
                png_path = CHARTS_DIR / f"{filename}.png"
                fig.write_image(str(png_path), width=1200, height=800)
                paths["png"] = str(png_path)
                logger.info(f"Saved PNG: {png_path}")
            except Exception as e:
                logger.warning(f"PNG export failed (kaleido not installed?): {e}")
                paths["png_error"] = str(e)

        return paths

    def _save_matplotlib(self, fig: plt.Figure, filename: str) -> Dict[str, str]:
        """Save Matplotlib figure to PNG."""
        paths = {}
        try:
            png_path = CHARTS_DIR / f"{filename}_mpl.png"
            fig.savefig(str(png_path), dpi=150, bbox_inches='tight', facecolor='white')
            paths["png_matplotlib"] = str(png_path)
            plt.close(fig)
        except Exception as e:
            logger.warning(f"Matplotlib save failed: {e}")
            paths["png_error"] = str(e)
        return paths

    def create_line_chart(
        self,
        data: List[Dict[str, Any]],
        x_col: str,
        y_col: str,
        group_col: str,
        title: str,
        x_label: str,
        y_label: str,
        save_html: bool,
        save_png: bool,
    ) -> Dict[str, Any]:
        """Create line chart."""
        try:
            df = pd.DataFrame(data)
            filename = self._generate_filename("line")

            # Plotly
            if group_col and group_col in df.columns:
                fig = px.line(
                    df, x=x_col, y=y_col, color=group_col,
                    title=title, color_discrete_sequence=self.COLOR_SEQUENCE
                )
            else:
                fig = px.line(df, x=x_col, y=y_col, title=title)

            fig.update_layout(
                xaxis_title=x_label or x_col,
                yaxis_title=y_label or y_col,
                template="plotly_white",
                hovermode="x unified",
            )

            paths = self._save_plotly(fig, filename, save_html, save_png)

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

    def create_bar_chart(
        self,
        data: List[Dict[str, Any]],
        x_col: str,
        y_col: str,
        title: str,
        horizontal: bool,
        color_col: str,
        save_html: bool,
        save_png: bool,
    ) -> Dict[str, Any]:
        """Create bar chart."""
        try:
            df = pd.DataFrame(data)
            filename = self._generate_filename("bar")

            if horizontal:
                fig = px.bar(
                    df, y=x_col, x=y_col, color=color_col,
                    title=title, orientation='h',
                    color_discrete_sequence=self.COLOR_SEQUENCE
                )
            else:
                fig = px.bar(
                    df, x=x_col, y=y_col, color=color_col,
                    title=title,
                    color_discrete_sequence=self.COLOR_SEQUENCE
                )

            fig.update_layout(template="plotly_white")

            paths = self._save_plotly(fig, filename, save_html, save_png)

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

    def create_candlestick(
        self,
        data: List[Dict[str, Any]],
        date_col: str,
        open_col: str,
        high_col: str,
        low_col: str,
        close_col: str,
        volume_col: str,
        title: str,
        save_html: bool,
        save_png: bool,
    ) -> Dict[str, Any]:
        """Create candlestick chart."""
        try:
            df = pd.DataFrame(data)
            filename = self._generate_filename("candlestick")

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

            paths = self._save_plotly(fig, filename, save_html, save_png)

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

    def create_heatmap(
        self,
        data: List[List[float]],
        x_labels: List[str],
        y_labels: List[str],
        title: str,
        color_scale: str,
        show_values: bool,
        save_html: bool,
        save_png: bool,
    ) -> Dict[str, Any]:
        """Create heatmap."""
        try:
            filename = self._generate_filename("heatmap")
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

            paths = self._save_plotly(fig, filename, save_html, save_png)

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

    def create_scatter(
        self,
        data: List[Dict[str, Any]],
        x_col: str,
        y_col: str,
        color_col: str,
        size_col: str,
        title: str,
        x_label: str,
        y_label: str,
        add_trendline: bool,
        save_html: bool,
        save_png: bool,
    ) -> Dict[str, Any]:
        """Create scatter plot."""
        try:
            df = pd.DataFrame(data)
            filename = self._generate_filename("scatter")

            trendline = "ols" if add_trendline else None

            fig = px.scatter(
                df, x=x_col, y=y_col,
                color=color_col, size=size_col,
                title=title, trendline=trendline,
                color_discrete_sequence=self.COLOR_SEQUENCE
            )

            fig.update_layout(
                xaxis_title=x_label or x_col,
                yaxis_title=y_label or y_col,
                template="plotly_white",
            )

            paths = self._save_plotly(fig, filename, save_html, save_png)

            # Calculate correlation if numeric
            correlation = None
            if df[x_col].dtype in ['float64', 'int64'] and df[y_col].dtype in ['float64', 'int64']:
                correlation = df[x_col].corr(df[y_col])

            return {
                "success": True,
                "chart_type": "scatter",
                "title": title,
                "data_points": len(df),
                "correlation": round(correlation, 4) if correlation else None,
                "files": paths,
            }

        except Exception as e:
            logger.error(f"Scatter error: {e}")
            return {"error": True, "message": str(e)}

    def create_waterfall(
        self,
        data: List[Dict[str, Any]],
        category_col: str,
        value_col: str,
        title: str,
        save_html: bool,
        save_png: bool,
    ) -> Dict[str, Any]:
        """Create waterfall chart."""
        try:
            df = pd.DataFrame(data)
            filename = self._generate_filename("waterfall")

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
                increasing={"marker": {"color": self.COLORS["success"]}},
                decreasing={"marker": {"color": self.COLORS["danger"]}},
                totals={"marker": {"color": self.COLORS["primary"]}},
            ))

            fig.update_layout(
                title=title,
                template="plotly_white",
                showlegend=False,
            )

            paths = self._save_plotly(fig, filename, save_html, save_png)

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

    def create_dual_axis(
        self,
        data: List[Dict[str, Any]],
        x_col: str,
        y1_col: str,
        y2_col: str,
        title: str,
        y1_label: str,
        y2_label: str,
        save_html: bool,
        save_png: bool,
    ) -> Dict[str, Any]:
        """Create dual-axis chart."""
        try:
            df = pd.DataFrame(data)
            filename = self._generate_filename("dual_axis")

            fig = make_subplots(specs=[[{"secondary_y": True}]])

            # Primary Y-axis
            fig.add_trace(
                go.Scatter(
                    x=df[x_col], y=df[y1_col],
                    name=y1_label or y1_col,
                    line=dict(color=self.COLORS["primary"])
                ),
                secondary_y=False,
            )

            # Secondary Y-axis
            fig.add_trace(
                go.Scatter(
                    x=df[x_col], y=df[y2_col],
                    name=y2_label or y2_col,
                    line=dict(color=self.COLORS["secondary"])
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

            paths = self._save_plotly(fig, filename, save_html, save_png)

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

    def create_pie_chart(
        self,
        data: List[Dict[str, Any]],
        names_col: str,
        values_col: str,
        title: str,
        hole: float,
        save_html: bool,
        save_png: bool,
    ) -> Dict[str, Any]:
        """Create pie/donut chart."""
        try:
            df = pd.DataFrame(data)
            filename = self._generate_filename("pie")

            fig = px.pie(
                df, names=names_col, values=values_col,
                title=title, hole=hole,
                color_discrete_sequence=self.COLOR_SEQUENCE
            )

            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(template="plotly_white")

            paths = self._save_plotly(fig, filename, save_html, save_png)

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

    def create_correlation_matrix(
        self,
        data: List[Dict[str, Any]],
        columns: List[str],
        title: str,
        save_html: bool,
        save_png: bool,
    ) -> Dict[str, Any]:
        """Create correlation matrix heatmap."""
        try:
            df = pd.DataFrame(data)
            filename = self._generate_filename("correlation")

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

            paths = self._save_plotly(fig, filename, save_html, save_png)

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

    def create_sensitivity_heatmap(
        self,
        matrix: Dict[str, Dict[str, float]],
        title: str,
        x_label: str,
        y_label: str,
        current_value: float,
        save_html: bool,
        save_png: bool,
    ) -> Dict[str, Any]:
        """Create sensitivity analysis heatmap from DCF results."""
        try:
            filename = self._generate_filename("sensitivity")

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

            paths = self._save_plotly(fig, filename, save_html, save_png)

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

    def run(self) -> None:
        """Run the MCP server."""
        logger.info("Starting Visualization MCP Server...")
        self.mcp.run()


def main():
    """Main entry point for standalone server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    server = VizServer()
    server.run()


if __name__ == "__main__":
    main()
