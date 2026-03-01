"""Custom exceptions fuer das Clustering-Modul (Slice 6).

Taxonomy-Editing Exceptions: Rename, Merge, Split, Undo.
"""


class ClusterNotFoundError(Exception):
    """Raised when a cluster does not exist or belongs to a different project."""

    pass


class UndoExpiredError(Exception):
    """Raised when the 30-second undo window has expired."""

    pass


class SplitValidationError(Exception):
    """Raised when split subclusters don't cover all original facts exactly."""

    pass


class MergeConflictError(Exception):
    """Raised when source_cluster_id == target_cluster_id."""

    pass
