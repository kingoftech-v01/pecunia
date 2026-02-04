"""
Transaction Importers Module.

Provides import functionality for various financial data formats.
"""
from .base import BaseImporter, ImportResult, ImportError, ValidationError
from .csv_importer import CSVImporter
from .ofx_importer import OFXImporter
from .qif_importer import QIFImporter

__all__ = [
    'BaseImporter',
    'ImportResult',
    'ImportError',
    'ValidationError',
    'CSVImporter',
    'OFXImporter',
    'QIFImporter',
]


def get_importer_for_file(filename: str) -> type:
    """
    Get the appropriate importer class based on file extension.

    Args:
        filename: Name of the file to import

    Returns:
        Importer class appropriate for the file type

    Raises:
        ValueError: If file type is not supported
    """
    extension = filename.lower().split('.')[-1]

    importers = {
        'csv': CSVImporter,
        'ofx': OFXImporter,
        'qfx': OFXImporter,
        'qif': QIFImporter,
    }

    if extension not in importers:
        supported = ', '.join(importers.keys())
        raise ValueError(
            f"Unsupported file type: .{extension}. "
            f"Supported formats: {supported}"
        )

    return importers[extension]
