"""
HTTP server and request handlers.
"""

from .handlers import DuplicateReviewHandler, create_handler_class
from .html_template import generate_html_page

__all__ = [
    "DuplicateReviewHandler",
    "create_handler_class",
    "generate_html_page",
]
