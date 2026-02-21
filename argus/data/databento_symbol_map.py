"""Bidirectional symbol mapping for Databento instrument_id ↔ ticker symbol.

Databento uses integer instrument_ids for efficiency in streaming data.
This module provides a mapping layer to translate between Databento's
numeric identifiers and human-readable ticker symbols.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass  # SymbolMappingMsg type hint handled via duck typing

logger = logging.getLogger(__name__)


class DatabentoSymbolMap:
    """Bidirectional mapping between Databento instrument_ids and ticker symbols.

    Populated by SymbolMappingMsg events during live session startup.
    Also supports manual population for testing and historical data.

    Thread-safe: The Databento Live client fires callbacks on its internal
    reader thread, so updates to this map must be safe for concurrent access.
    In practice, SymbolMappingMsg events arrive before any data messages,
    so race conditions are unlikely, but we use a simple dict (GIL-protected
    for single-word operations) as the backing store.

    Example:
        >>> symbol_map = DatabentoSymbolMap()
        >>> symbol_map.add_mapping(12345, "AAPL")
        >>> symbol_map.get_symbol(12345)
        'AAPL'
        >>> symbol_map.get_instrument_id("AAPL")
        12345
    """

    def __init__(self) -> None:
        """Initialize an empty symbol map."""
        self._id_to_symbol: dict[int, str] = {}
        self._symbol_to_id: dict[str, int] = {}

    def on_symbol_mapping(self, msg: Any) -> None:
        """Process a SymbolMappingMsg to update the mapping.

        This is the primary way mappings are populated during live sessions.
        SymbolMappingMsg events arrive at session start before any data messages.

        Args:
            msg: Databento SymbolMappingMsg with instrument_id and
                 stype_in_symbol (the human-readable ticker).
        """
        instrument_id: int = msg.instrument_id
        # stype_in_symbol is the ticker in the input symbology type
        symbol: str = msg.stype_in_symbol

        if not symbol or symbol == "":
            logger.warning(
                "Empty symbol in SymbolMappingMsg for instrument_id=%d", instrument_id
            )
            return

        # Handle remapping (instrument_id can change for a symbol during session)
        old_symbol = self._id_to_symbol.get(instrument_id)
        if old_symbol and old_symbol != symbol:
            logger.info(
                "Remapping instrument_id=%d: %s → %s", instrument_id, old_symbol, symbol
            )
            del self._symbol_to_id[old_symbol]

        self._id_to_symbol[instrument_id] = symbol
        self._symbol_to_id[symbol] = instrument_id
        logger.debug("Mapped %s → instrument_id=%d", symbol, instrument_id)

    def add_mapping(self, instrument_id: int, symbol: str) -> None:
        """Manually add a mapping (for testing or historical data).

        Args:
            instrument_id: Databento numeric instrument identifier.
            symbol: Human-readable ticker symbol.
        """
        self._id_to_symbol[instrument_id] = symbol
        self._symbol_to_id[symbol] = instrument_id

    def get_symbol(self, instrument_id: int) -> str | None:
        """Resolve instrument_id → ticker symbol.

        Args:
            instrument_id: Databento numeric instrument identifier.

        Returns:
            Ticker symbol, or None if the instrument_id hasn't been mapped yet.
        """
        return self._id_to_symbol.get(instrument_id)

    def get_instrument_id(self, symbol: str) -> int | None:
        """Resolve ticker symbol → instrument_id.

        Args:
            symbol: Human-readable ticker symbol.

        Returns:
            Instrument ID, or None if the symbol hasn't been mapped yet.
        """
        return self._symbol_to_id.get(symbol)

    def has_symbol(self, symbol: str) -> bool:
        """Check if a ticker symbol is in the map.

        Args:
            symbol: Ticker symbol to check.

        Returns:
            True if the symbol has been mapped.
        """
        return symbol in self._symbol_to_id

    def has_instrument_id(self, instrument_id: int) -> bool:
        """Check if an instrument_id is in the map.

        Args:
            instrument_id: Instrument ID to check.

        Returns:
            True if the instrument_id has been mapped.
        """
        return instrument_id in self._id_to_symbol

    @property
    def symbol_count(self) -> int:
        """Number of mapped symbols.

        Returns:
            Count of symbols in the map.
        """
        return len(self._id_to_symbol)

    def all_symbols(self) -> list[str]:
        """Return all mapped ticker symbols.

        Returns:
            List of all ticker symbols in the map.
        """
        return list(self._symbol_to_id.keys())

    def clear(self) -> None:
        """Clear all mappings (for session reset)."""
        self._id_to_symbol.clear()
        self._symbol_to_id.clear()
