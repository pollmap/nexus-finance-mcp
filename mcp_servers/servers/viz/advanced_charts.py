"""Advanced chart tools and implementations for VizServer."""
import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


def register_advanced_tools(server):
    """Register advanced chart tools on the VizServer instance."""

    @server.mcp.tool()
    def viz_radar(
        data: List[Dict[str, Any]],
        categories: List[str] = None,
        value_col: str = "value",
        group_col: str = None,
        title: str = "Radar Chart",
        fill: bool = True,
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        레이더/스파이더 차트 생성 (다변량 비교 — PER/PBR/ROE 등 팩터 비교)

        Args:
            data: 데이터 리스트 [{"factor": "PER", "value": 80, "company": "삼성전자"}, ...]
                  또는 카테고리별 값 [{"company": "삼성", "PER": 80, "PBR": 60, "ROE": 90}, ...]
            categories: 축 카테고리 리스트 (없으면 factor 컬럼 사용)
            value_col: 값 컬럼명
            group_col: 그룹(비교 대상) 컬럼
            title: 차트 제목
            fill: 영역 채우기 여부
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_radar(server, data, categories, value_col, group_col, title, fill, save_html, save_png)

    @server.mcp.tool()
    def viz_bubble(
        data: List[Dict[str, Any]],
        x_col: str,
        y_col: str,
        size_col: str,
        color_col: str = None,
        label_col: str = None,
        title: str = "Bubble Chart",
        x_label: str = "",
        y_label: str = "",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        버블 차트 생성 (3변수 비교 — PER vs ROE vs 시가총액)

        Args:
            data: [{"stock": "삼성", "per": 12, "roe": 15, "market_cap": 500, "sector": "IT"}, ...]
            x_col: X축 컬럼
            y_col: Y축 컬럼
            size_col: 버블 크기 컬럼
            color_col: 색상 구분 컬럼
            label_col: 레이블 컬럼
            title: 차트 제목
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_bubble(server, data, x_col, y_col, size_col, color_col, label_col, title, x_label, y_label, save_html, save_png)

    @server.mcp.tool()
    def viz_lollipop(
        data: List[Dict[str, Any]],
        category_col: str = "category",
        value_col: str = "value",
        title: str = "Lollipop Chart",
        horizontal: bool = True,
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        롤리팝 차트 생성 (깔끔한 바 차트 대안, 순위 비교)

        Args:
            data: [{"category": "삼성전자", "value": 85}, ...]
            category_col: 카테고리 컬럼
            value_col: 값 컬럼
            title: 차트 제목
            horizontal: 가로 방향
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_lollipop(server, data, category_col, value_col, title, horizontal, save_html, save_png)

    @server.mcp.tool()
    def viz_slope(
        data: List[Dict[str, Any]],
        label_col: str = "label",
        start_col: str = "start",
        end_col: str = "end",
        start_label: str = "Before",
        end_label: str = "After",
        title: str = "Slope Chart",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        슬로프 차트 생성 (전후 비교, 순위 변동)

        Args:
            data: [{"label": "삼성전자", "start": 70000, "end": 85000}, ...]
            label_col: 라벨 컬럼
            start_col: 시작값 컬럼
            end_col: 끝값 컬럼
            start_label: 시작 시점 레이블
            end_label: 종료 시점 레이블
            title: 차트 제목
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_slope(server, data, label_col, start_col, end_col, start_label, end_label, title, save_html, save_png)

    @server.mcp.tool()
    def viz_parallel(
        data: List[Dict[str, Any]],
        dimensions: List[str] = None,
        color_col: str = None,
        title: str = "Parallel Coordinates",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        평행좌표 차트 생성 (다변량 스크리닝, 종목 필터링)

        Args:
            data: [{"stock": "삼성", "PER": 12, "PBR": 1.5, "ROE": 15, "배당률": 2.1}, ...]
            dimensions: 축으로 사용할 컬럼 리스트
            color_col: 색상 구분 컬럼 (수치형 또는 범주형)
            title: 차트 제목
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_parallel(server, data, dimensions, color_col, title, save_html, save_png)

    @server.mcp.tool()
    def viz_combo(
        data: List[Dict[str, Any]],
        x_col: str,
        bar_cols: List[str] = None,
        line_cols: List[str] = None,
        title: str = "Combo Chart",
        bar_label: str = "",
        line_label: str = "",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        콤보 차트 생성 (바+라인 자유 조합)

        Args:
            data: [{"date": "2024Q1", "매출": 100, "영업이익": 20, "영업이익률": 20.0}, ...]
            x_col: X축 컬럼
            bar_cols: 바로 표시할 컬럼 리스트
            line_cols: 라인으로 표시할 컬럼 리스트
            title: 차트 제목
            bar_label: 바 Y축 레이블
            line_label: 라인 Y축 레이블
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_combo(server, data, x_col, bar_cols, line_cols, title, bar_label, line_label, save_html, save_png)

    @server.mcp.tool()
    def viz_gantt(
        data: List[Dict[str, Any]],
        task_col: str = "task",
        start_col: str = "start",
        end_col: str = "end",
        group_col: str = None,
        title: str = "Gantt Chart",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        간트 차트 생성 (프로젝트 타임라인, IPO 일정, 이벤트 스케줄)

        Args:
            data: [{"task": "실사", "start": "2024-01-01", "end": "2024-03-01", "phase": "Phase1"}, ...]
            task_col: 태스크 컬럼
            start_col: 시작일 컬럼
            end_col: 종료일 컬럼
            group_col: 그룹/단계 컬럼 (색상 구분)
            title: 차트 제목
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_gantt(server, data, task_col, start_col, end_col, group_col, title, save_html, save_png)

    @server.mcp.tool()
    def viz_marimekko(
        data: List[Dict[str, Any]],
        x_col: str = "category",
        y_col: str = "share",
        group_col: str = "segment",
        title: str = "Marimekko Chart",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        마리메코 차트 생성 (가변폭 누적바 — 시장점유율×세그먼트)

        Args:
            data: [{"category": "한국", "segment": "전자", "share": 40, "width": 30}, ...]
            x_col: X축 카테고리 (폭이 다름)
            y_col: Y축 비율
            group_col: 세그먼트 컬럼
            title: 차트 제목
            save_html: HTML 저장 여부
            save_png: PNG 저장 여부
        """
        return _create_marimekko(server, data, x_col, y_col, group_col, title, save_html, save_png)


# ========================================================================
# Implementation Functions
# ========================================================================

def _create_radar(server, data, categories, value_col, group_col, title, fill, save_html, save_png):
    """Create radar/spider chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("radar")

        fig = go.Figure()

        if categories and group_col:
            # Wide format: each row is a group, categories are columns
            for _, row in df.iterrows():
                values = [row[c] for c in categories]
                values.append(values[0])  # Close the polygon
                cats = categories + [categories[0]]
                fig.add_trace(go.Scatterpolar(
                    r=values, theta=cats, name=row[group_col],
                    fill='toself' if fill else 'none', opacity=0.7,
                ))
        elif group_col and 'factor' in df.columns:
            # Long format with factor column
            for grp in df[group_col].unique():
                grp_df = df[df[group_col] == grp]
                values = grp_df[value_col].tolist()
                cats = grp_df['factor'].tolist()
                values.append(values[0])
                cats.append(cats[0])
                fig.add_trace(go.Scatterpolar(
                    r=values, theta=cats, name=str(grp),
                    fill='toself' if fill else 'none', opacity=0.7,
                ))
        else:
            # Simple single radar
            cats = df.iloc[:, 0].tolist() if not categories else categories
            values = df[value_col].tolist()
            values.append(values[0])
            cats_closed = cats + [cats[0]]
            fig.add_trace(go.Scatterpolar(
                r=values, theta=cats_closed, name=title,
                fill='toself' if fill else 'none',
            ))

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True)),
            title=title, template="plotly_white",
            showlegend=True,
        )
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "radar", "title": title, "files": paths}
    except Exception as e:
        logger.error(f"Radar error: {e}")
        return {"error": True, "message": str(e)}


def _create_bubble(server, data, x_col, y_col, size_col, color_col, label_col, title, x_label, y_label, save_html, save_png):
    """Create bubble chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("bubble")

        fig = px.scatter(
            df, x=x_col, y=y_col, size=size_col,
            color=color_col, hover_name=label_col,
            title=title, size_max=60,
            color_discrete_sequence=server.COLOR_SEQUENCE,
        )

        if label_col and label_col in df.columns:
            fig.update_traces(textposition='top center', textfont_size=9)

        fig.update_layout(
            xaxis_title=x_label or x_col,
            yaxis_title=y_label or y_col,
            template="plotly_white",
        )
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "bubble", "title": title, "data_points": len(df), "files": paths}
    except Exception as e:
        logger.error(f"Bubble error: {e}")
        return {"error": True, "message": str(e)}


def _create_lollipop(server, data, category_col, value_col, title, horizontal, save_html, save_png):
    """Create lollipop chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data).sort_values(value_col, ascending=True)
        filename = server._generate_filename("lollipop")

        fig = go.Figure()

        if horizontal:
            for i, row in df.iterrows():
                fig.add_trace(go.Scatter(
                    x=[0, row[value_col]], y=[row[category_col], row[category_col]],
                    mode='lines', line=dict(color='#B0BEC5', width=2),
                    showlegend=False,
                ))
            fig.add_trace(go.Scatter(
                x=df[value_col], y=df[category_col],
                mode='markers', marker=dict(size=12, color=server.COLORS["primary"]),
                name=value_col,
            ))
        else:
            for i, row in df.iterrows():
                fig.add_trace(go.Scatter(
                    x=[row[category_col], row[category_col]], y=[0, row[value_col]],
                    mode='lines', line=dict(color='#B0BEC5', width=2),
                    showlegend=False,
                ))
            fig.add_trace(go.Scatter(
                x=df[category_col], y=df[value_col],
                mode='markers', marker=dict(size=12, color=server.COLORS["primary"]),
                name=value_col,
            ))

        fig.update_layout(title=title, template="plotly_white", showlegend=False)
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "lollipop", "title": title, "data_points": len(df), "files": paths}
    except Exception as e:
        logger.error(f"Lollipop error: {e}")
        return {"error": True, "message": str(e)}


def _create_slope(server, data, label_col, start_col, end_col, start_label, end_label, title, save_html, save_png):
    """Create slope chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("slope")

        fig = go.Figure()

        for i, row in df.iterrows():
            color = server.COLOR_SEQUENCE[i % len(server.COLOR_SEQUENCE)]
            # Line
            fig.add_trace(go.Scatter(
                x=[start_label, end_label],
                y=[row[start_col], row[end_col]],
                mode='lines+markers+text',
                line=dict(color=color, width=2),
                marker=dict(size=10),
                text=[f"{row[label_col]}: {row[start_col]:,.0f}", f"{row[end_col]:,.0f}"],
                textposition=["middle left", "middle right"],
                textfont=dict(size=10),
                name=str(row[label_col]),
                showlegend=False,
            ))

        fig.update_layout(
            title=title, template="plotly_white",
            xaxis=dict(type='category'),
        )
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "slope", "title": title, "items": len(df), "files": paths}
    except Exception as e:
        logger.error(f"Slope error: {e}")
        return {"error": True, "message": str(e)}


def _create_parallel(server, data, dimensions, color_col, title, save_html, save_png):
    """Create parallel coordinates chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("parallel")

        if not dimensions:
            dimensions = [c for c in df.select_dtypes(include=[np.number]).columns if c != color_col]

        dims = []
        for col in dimensions:
            dims.append(dict(
                range=[df[col].min(), df[col].max()],
                label=col,
                values=df[col],
            ))

        color_vals = None
        colorscale = "Viridis"
        if color_col and color_col in df.columns:
            if df[color_col].dtype in ['float64', 'int64']:
                color_vals = df[color_col]
            else:
                df['_color_idx'] = pd.Categorical(df[color_col]).codes
                color_vals = df['_color_idx']

        fig = go.Figure(data=go.Parcoords(
            line=dict(
                color=color_vals,
                colorscale=colorscale,
                showscale=True if color_vals is not None else False,
            ),
            dimensions=dims,
        ))

        fig.update_layout(title=title, template="plotly_white")
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "parallel_coordinates", "title": title, "dimensions": dimensions, "data_points": len(df), "files": paths}
    except Exception as e:
        logger.error(f"Parallel coordinates error: {e}")
        return {"error": True, "message": str(e)}


def _create_combo(server, data, x_col, bar_cols, line_cols, title, bar_label, line_label, save_html, save_png):
    """Create combo chart (bars + lines)."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("combo")

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        bar_cols = bar_cols or []
        line_cols = line_cols or []

        # Bars
        for i, col in enumerate(bar_cols):
            fig.add_trace(go.Bar(
                x=df[x_col], y=df[col], name=col,
                marker_color=server.COLOR_SEQUENCE[i % len(server.COLOR_SEQUENCE)],
                opacity=0.8,
            ), secondary_y=False)

        # Lines on secondary axis
        for i, col in enumerate(line_cols):
            fig.add_trace(go.Scatter(
                x=df[x_col], y=df[col], name=col,
                mode='lines+markers',
                line=dict(color=server.COLOR_SEQUENCE[(len(bar_cols) + i) % len(server.COLOR_SEQUENCE)], width=3),
                marker=dict(size=8),
            ), secondary_y=True)

        fig.update_layout(title=title, template="plotly_white", barmode='group', hovermode="x unified")
        fig.update_yaxes(title_text=bar_label or ", ".join(bar_cols), secondary_y=False)
        fig.update_yaxes(title_text=line_label or ", ".join(line_cols), secondary_y=True)

        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "combo", "title": title, "bar_series": bar_cols, "line_series": line_cols, "files": paths}
    except Exception as e:
        logger.error(f"Combo chart error: {e}")
        return {"error": True, "message": str(e)}


def _create_gantt(server, data, task_col, start_col, end_col, group_col, title, save_html, save_png):
    """Create Gantt chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("gantt")

        df[start_col] = pd.to_datetime(df[start_col])
        df[end_col] = pd.to_datetime(df[end_col])

        fig = px.timeline(
            df, x_start=start_col, x_end=end_col, y=task_col,
            color=group_col, title=title,
            color_discrete_sequence=server.COLOR_SEQUENCE,
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(template="plotly_white")
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "gantt", "title": title, "tasks": len(df), "files": paths}
    except Exception as e:
        logger.error(f"Gantt error: {e}")
        return {"error": True, "message": str(e)}


def _create_marimekko(server, data, x_col, y_col, group_col, title, save_html, save_png):
    """Create Marimekko (variable-width stacked bar) chart."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("marimekko")

        # Calculate widths from category totals
        categories = df[x_col].unique()
        cat_totals = df.groupby(x_col)[y_col].sum()
        total = cat_totals.sum()
        widths = {cat: cat_totals[cat] / total for cat in categories}

        fig = go.Figure()

        segments = df[group_col].unique()
        x_pos = 0

        for cat in categories:
            cat_df = df[df[x_col] == cat]
            w = widths[cat]
            cat_total = cat_df[y_col].sum()
            y_base = 0

            for i, seg in enumerate(segments):
                seg_rows = cat_df[cat_df[group_col] == seg]
                if len(seg_rows) > 0:
                    val = seg_rows[y_col].values[0]
                    pct = val / cat_total * 100 if cat_total > 0 else 0
                    color = server.COLOR_SEQUENCE[i % len(server.COLOR_SEQUENCE)]

                    fig.add_trace(go.Bar(
                        x=[x_pos + w / 2], y=[pct], width=[w * 0.95],
                        base=y_base, name=str(seg),
                        marker_color=color,
                        text=f"{pct:.0f}%", textposition="inside",
                        showlegend=(cat == categories[0]),
                        hovertemplate=f"{cat}<br>{seg}: {val:,.0f} ({pct:.1f}%)<extra></extra>",
                    ))
                    y_base += pct

            x_pos += w

        fig.update_layout(
            title=title, template="plotly_white",
            barmode='stack',
            xaxis=dict(
                tickmode='array',
                tickvals=[sum(list(widths.values())[:i]) + widths[cat] / 2 for i, cat in enumerate(categories)],
                ticktext=list(categories),
            ),
            yaxis=dict(title="비율 (%)", range=[0, 100]),
        )
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "marimekko", "title": title, "categories": len(categories), "segments": len(segments), "files": paths}
    except Exception as e:
        logger.error(f"Marimekko error: {e}")
        return {"error": True, "message": str(e)}
