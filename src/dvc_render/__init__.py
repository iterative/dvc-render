"""
Library for rendering DVC plots
"""
from .html import render_html  # noqa: F401
from .image import ImageRenderer
from .plotly import PlotlyRenderer  # noqa: F401
from .vega import VegaRenderer
from .vega_templates import TEMPLATES  # noqa: F401

RENDERERS = [ImageRenderer, PlotlyRenderer, VegaRenderer]
