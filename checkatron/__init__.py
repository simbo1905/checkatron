"""
Checkatron - SQL diff generation tool for database table comparisons.
"""

__version__ = "0.1.0"

from .diffgen import build_sql, parse_args

__all__ = ["build_sql", "parse_args"]
