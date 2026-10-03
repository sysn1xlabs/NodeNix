__version__ = '0.1.2'

import tempfile
from pathlib import Path

def default_output(command):
    """Use the working temporary folder by default on protected Windows PCs."""
    return Path(tempfile.gettempdir()) / 'NodeNix' / command
