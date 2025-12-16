"""
FAISS-based embedding storage for fast similarity search.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional


class FAISSEmbeddingStore:
    """FAISS-based embedding store for fast similarity search."""

    def __init__(self, embeddings_dir: Path):
        try:
            import pickle

            import faiss
        except ImportError:
            raise ImportError(
                "FAISS not available. Install with: pip install faiss-cpu"
            )

        self.embeddings_dir = embeddings_dir
        self.index = faiss.read_index(str(embeddings_dir / "embeddings.index"))

        with open(embeddings_dir / "metadata.pkl", "rb") as f:
            self.metadata = pickle.load(f)

        print(f"Loaded FAISS index with {self.index.ntotal} vectors")

    def search_species(
        self, species_name: str, threshold: float = 0.85
    ) -> List[Dict[str, Any]]:
        """Find similar images within a species using cached embeddings."""
        try:
            import pickle

            import numpy as np
        except ImportError:
            return []

        # Get all images for this species
        species_items = [m for m in self.metadata if m["species"] == species_name]
        if len(species_items) < 2:
            return []

        # Get their indices in the FAISS index
        species_indices = [
            i for i, m in enumerate(self.metadata) if m["species"] == species_name
        ]

        # Extract their embeddings (need full metadata for this)
        with open(self.embeddings_dir / "metadata_full.pkl", "rb") as f:
            full_metadata = pickle.load(f)

        species_embeddings = [full_metadata[i]["embedding"] for i in species_indices]
        embeddings_array = np.array(species_embeddings, dtype="float32")

        # Normalize for cosine similarity
        import faiss

        faiss.normalize_L2(embeddings_array)

        # Find similar pairs using threshold
        n = len(species_embeddings)

        # Union-Find for grouping
        parent = list(range(n))

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[py] = px

        # Compare all pairs
        for i in range(n):
            for j in range(i + 1, n):
                sim = np.dot(embeddings_array[i], embeddings_array[j])
                if sim >= threshold:
                    union(i, j)

        # Group by root
        groups_dict = {}
        for i in range(n):
            root = find(i)
            if root not in groups_dict:
                groups_dict[root] = []
            groups_dict[root].append(species_items[i])

        # Format as groups (only groups with >1 image)
        result_groups = []
        group_id = 1
        for group_items in groups_dict.values():
            if len(group_items) > 1:
                # Sort by size
                group_items.sort(key=lambda x: -x["size"])
                result_groups.append(
                    {
                        "group_id": group_id,
                        "images": [
                            {
                                "filename": item["filename"],
                                "size": item["size"],
                                "path": f"/image/{species_name}/{item['filename']}",
                            }
                            for item in group_items
                        ],
                        "count": len(group_items),
                    }
                )
                group_id += 1

        return result_groups

    def get_status(self) -> Dict[str, Any]:
        """Get status information about the FAISS store."""
        return {
            "available": True,
            "count": self.index.ntotal,
            "location": str(self.embeddings_dir),
        }


def init_faiss_store(embeddings_dir: Path) -> Optional[FAISSEmbeddingStore]:
    """Initialize FAISS store if embeddings exist."""
    # Check directory exists
    if not embeddings_dir.exists():
        print(f"⚠️  Embeddings directory not found: {embeddings_dir.absolute()}")
        print(f"   Current working directory: {Path.cwd()}")
        return None

    # Check index file exists
    index_file = embeddings_dir / "embeddings.index"
    if not index_file.exists():
        print(f"⚠️  embeddings.index not found in: {embeddings_dir.absolute()}")
        try:
            files = list(embeddings_dir.iterdir())
            print(
                f"   Directory contains {len(files)} items: {[f.name for f in files[:5]]}"
            )
        except Exception:
            pass
        return None

    # Check metadata file exists
    metadata_file = embeddings_dir / "metadata.pkl"
    if not metadata_file.exists():
        print(f"⚠️  metadata.pkl not found in: {embeddings_dir.absolute()}")
        return None

    # Try to load
    try:
        return FAISSEmbeddingStore(embeddings_dir)
    except Exception as e:
        print(f"⚠️  Could not load FAISS store: {e}")
        print(f"   Embeddings directory: {embeddings_dir.absolute()}")
        return None
