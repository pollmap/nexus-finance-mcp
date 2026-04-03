"""Map chart tools and implementations for VizServer."""
import logging
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


def register_map_tools(server):
    """Register map chart tools on the VizServer instance."""

    @server.mcp.tool()
    def viz_map_choropleth(
        data: List[Dict[str, Any]],
        location_col: str = "country",
        value_col: str = "value",
        title: str = "Choropleth Map",
        color_scale: str = "RdYlGn",
        location_mode: str = "country names",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        국가/지역별 색상 지도 (GDP, 수출, 물가, 인구 등 비교)

        Args:
            data: [{"country": "South Korea", "value": 1.8}, {"country": "Japan", "value": 0.5}, ...]
            location_col: 위치 컬럼 (국가명 또는 ISO 코드)
            value_col: 색상 인코딩할 값 컬럼
            title: 차트 제목
            color_scale: 색상 스케일 (RdYlGn, Viridis, Blues 등)
            location_mode: "country names" 또는 "ISO-3" 또는 "USA-states"
        """
        return _create_map_choropleth(server, data, location_col, value_col, title, color_scale, location_mode, save_html, save_png)

    @server.mcp.tool()
    def viz_map_scatter(
        data: List[Dict[str, Any]],
        lat_col: str = "lat",
        lon_col: str = "lon",
        size_col: str = None,
        color_col: str = None,
        label_col: str = None,
        title: str = "Scatter Map",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        좌표 기반 포인트 지도 (항만, 공장, 임상시험 위치, 부동산 등)

        Args:
            data: [{"name": "부산항", "lat": 35.18, "lon": 129.08, "volume": 22000000}, ...]
            lat_col: 위도 컬럼
            lon_col: 경도 컬럼
            size_col: 포인트 크기 컬럼 (선택)
            color_col: 색상 구분 컬럼 (선택)
            label_col: 라벨 컬럼 (선택)
            title: 차트 제목
        """
        return _create_map_scatter(server, data, lat_col, lon_col, size_col, color_col, label_col, title, save_html, save_png)

    @server.mcp.tool()
    def viz_map_flow(
        data: List[Dict[str, Any]],
        from_lat: str = "from_lat",
        from_lon: str = "from_lon",
        to_lat: str = "to_lat",
        to_lon: str = "to_lon",
        value_col: str = "value",
        label_col: str = None,
        title: str = "Flow Map",
        save_html: bool = True,
        save_png: bool = True,
    ) -> Dict[str, Any]:
        """
        흐름 지도 (무역 경로, 운임 흐름, 공급망, 이주 등)

        Args:
            data: [{"from_lat": 37.57, "from_lon": 126.98, "to_lat": 37.77, "to_lon": -122.42, "value": 5000, "label": "한국→미국"}, ...]
            from_lat/from_lon: 출발 좌표
            to_lat/to_lon: 도착 좌표
            value_col: 흐름 두께 컬럼
            label_col: 라벨 컬럼
            title: 차트 제목
        """
        return _create_map_flow(server, data, from_lat, from_lon, to_lat, to_lon, value_col, label_col, title, save_html, save_png)


# ========================================================================
# Implementation Functions
# ========================================================================

def _create_map_choropleth(server, data, location_col, value_col, title, color_scale, location_mode, save_html, save_png):
    """Create choropleth map."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("map_choropleth")

        # Map location_mode to plotly locationmode
        mode_map = {
            "country names": "country names",
            "ISO-3": "ISO-3",
            "USA-states": "USA-states",
        }
        plotly_mode = mode_map.get(location_mode, "country names")

        fig = px.choropleth(
            df, locations=location_col, locationmode=plotly_mode,
            color=value_col, title=title,
            color_continuous_scale=color_scale,
            hover_name=location_col,
        )
        fig.update_layout(template="plotly_white", geo=dict(showframe=False, showcoastlines=True))
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "map_choropleth", "title": title, "data_points": len(df), "files": paths}
    except Exception as e:
        logger.error(f"Map choropleth error: {e}")
        return {"error": True, "message": f"Map choropleth creation failed: {e}"}


def _create_map_scatter(server, data, lat_col, lon_col, size_col, color_col, label_col, title, save_html, save_png):
    """Create scatter map with points on geographic coordinates."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("map_scatter")

        fig = px.scatter_geo(
            df, lat=lat_col, lon=lon_col,
            size=size_col, color=color_col,
            hover_name=label_col,
            title=title,
            color_discrete_sequence=server.COLOR_SEQUENCE,
        )
        fig.update_layout(template="plotly_white", geo=dict(showframe=False, showcoastlines=True, showland=True, landcolor="rgb(243, 243, 243)"))
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "map_scatter", "title": title, "data_points": len(df), "files": paths}
    except Exception as e:
        logger.error(f"Map scatter error: {e}")
        return {"error": True, "message": f"Map scatter creation failed: {e}"}


def _create_map_flow(server, data, from_lat, from_lon, to_lat, to_lon, value_col, label_col, title, save_html, save_png):
    """Create flow map showing connections between geographic points."""
    if not data:
        return {"error": True, "message": "Empty data — no records to chart"}
    try:
        df = pd.DataFrame(data)
        filename = server._generate_filename("map_flow")

        fig = go.Figure()

        # Normalize line widths
        max_val = df[value_col].max() if value_col in df.columns else 1
        min_width, max_width = 1, 8

        for i, row in df.iterrows():
            # Calculate line width proportional to value
            val = row.get(value_col, 1) if value_col in df.columns else 1
            width = min_width + (val / max_val) * (max_width - min_width) if max_val > 0 else 2
            color = server.COLOR_SEQUENCE[i % len(server.COLOR_SEQUENCE)]
            label = str(row.get(label_col, f"Flow {i+1}")) if label_col and label_col in df.columns else f"Flow {i+1}"

            # Draw the flow line
            fig.add_trace(go.Scattergeo(
                lon=[row[from_lon], row[to_lon]],
                lat=[row[from_lat], row[to_lat]],
                mode='lines',
                line=dict(width=width, color=color),
                name=label,
                hoverinfo='name',
            ))

            # Draw endpoint markers
            fig.add_trace(go.Scattergeo(
                lon=[row[from_lon], row[to_lon]],
                lat=[row[from_lat], row[to_lat]],
                mode='markers',
                marker=dict(size=6, color=color),
                showlegend=False,
                hoverinfo='skip',
            ))

        fig.update_layout(
            title=title, template="plotly_white",
            showlegend=True,
            geo=dict(showframe=False, showcoastlines=True, showland=True,
                     landcolor="rgb(243, 243, 243)", projection_type="natural earth"),
        )
        paths = server._save_plotly(fig, filename, save_html, save_png)
        return {"success": True, "chart_type": "map_flow", "title": title, "flows": len(df), "files": paths}
    except Exception as e:
        logger.error(f"Map flow error: {e}")
        return {"error": True, "message": f"Map flow creation failed: {e}"}
