"""API route modules."""

import sys
from pathlib import Path

# Ensure package is in path
_package_dir = Path(__file__).parent.parent.parent
if str(_package_dir) not in sys.path:
    sys.path.insert(0, str(_package_dir))

from api.routes.analysis import router as analysis_router
from api.routes.dashboard import router as dashboard_router
from api.routes.deletion import router as deletion_router
from api.routes.images import router as images_router

__all__ = ["dashboard_router", "analysis_router", "images_router", "deletion_router"]
