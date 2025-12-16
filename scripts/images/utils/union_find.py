"""
Union-Find (Disjoint Set Union) data structure for grouping similar items.
"""

from typing import Dict, List


class UnionFind:
    """
    Union-Find data structure with path compression and union by rank.

    Used for efficiently grouping similar images (duplicates or CNN-similar).
    """

    def __init__(self, n: int):
        """
        Initialize Union-Find with n elements.

        Args:
            n: Number of elements (0 to n-1)
        """
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        """
        Find the root of element x with path compression.

        Args:
            x: Element index

        Returns:
            Root index of the set containing x
        """
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> None:
        """
        Union the sets containing x and y using union by rank.

        Args:
            x: First element index
            y: Second element index
        """
        px, py = self.find(x), self.find(y)
        if px == py:
            return
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1

    def groups(self) -> Dict[int, List[int]]:
        """
        Get all groups as a dict mapping root -> list of member indices.

        Returns:
            Dict where keys are root indices and values are lists of all
            indices in that group (including the root).
        """
        result: Dict[int, List[int]] = {}
        for i in range(len(self.parent)):
            root = self.find(i)
            if root not in result:
                result[root] = []
            result[root].append(i)
        return result

    def groups_with_multiple(self) -> List[List[int]]:
        """
        Get only groups with more than one member.

        Returns:
            List of groups, where each group is a list of member indices.
        """
        return [members for members in self.groups().values() if len(members) > 1]
