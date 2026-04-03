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
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
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
        """Register MCP tools from all chart modules."""
        from .basic_charts import register_basic_tools
        from .statistical_charts import register_statistical_tools
        from .hierarchical_charts import register_hierarchical_tools
        from .advanced_charts import register_advanced_tools
        from .map_charts import register_map_tools

        register_basic_tools(self)
        register_statistical_tools(self)
        register_hierarchical_tools(self)
        register_advanced_tools(self)
        register_map_tools(self)

    # ========================================================================
    # Helper Methods
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
