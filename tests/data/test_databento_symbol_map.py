"""Tests for DatabentoSymbolMap (Sprint 12)."""

from dataclasses import dataclass

from argus.data.databento_symbol_map import DatabentoSymbolMap


@dataclass
class MockSymbolMappingMsg:
    """Mock SymbolMappingMsg for testing without databento package."""

    instrument_id: int = 0
    stype_in_symbol: str = ""


class TestDatabentoSymbolMap:
    """Tests for the DatabentoSymbolMap class."""

    def test_empty_map_returns_none_for_lookups(self) -> None:
        """Empty map returns None for all lookups."""
        symbol_map = DatabentoSymbolMap()
        assert symbol_map.get_symbol(12345) is None
        assert symbol_map.get_instrument_id("AAPL") is None

    def test_add_mapping_creates_bidirectional_mapping(self) -> None:
        """add_mapping() creates both id→symbol and symbol→id mappings."""
        symbol_map = DatabentoSymbolMap()
        symbol_map.add_mapping(12345, "AAPL")
        assert symbol_map.get_symbol(12345) == "AAPL"
        assert symbol_map.get_instrument_id("AAPL") == 12345

    def test_get_symbol_returns_correct_symbol(self) -> None:
        """get_symbol() returns the correct ticker for a mapped id."""
        symbol_map = DatabentoSymbolMap()
        symbol_map.add_mapping(100, "TSLA")
        symbol_map.add_mapping(200, "NVDA")
        assert symbol_map.get_symbol(100) == "TSLA"
        assert symbol_map.get_symbol(200) == "NVDA"

    def test_get_instrument_id_returns_correct_id(self) -> None:
        """get_instrument_id() returns the correct id for a mapped symbol."""
        symbol_map = DatabentoSymbolMap()
        symbol_map.add_mapping(100, "TSLA")
        symbol_map.add_mapping(200, "NVDA")
        assert symbol_map.get_instrument_id("TSLA") == 100
        assert symbol_map.get_instrument_id("NVDA") == 200

    def test_has_symbol_returns_true_for_mapped_symbol(self) -> None:
        """has_symbol() returns True for mapped symbols."""
        symbol_map = DatabentoSymbolMap()
        symbol_map.add_mapping(100, "AAPL")
        assert symbol_map.has_symbol("AAPL") is True
        assert symbol_map.has_symbol("TSLA") is False

    def test_has_instrument_id_returns_true_for_mapped_id(self) -> None:
        """has_instrument_id() returns True for mapped instrument_ids."""
        symbol_map = DatabentoSymbolMap()
        symbol_map.add_mapping(100, "AAPL")
        assert symbol_map.has_instrument_id(100) is True
        assert symbol_map.has_instrument_id(999) is False

    def test_symbol_count_reflects_current_state(self) -> None:
        """symbol_count property reflects the current number of mappings."""
        symbol_map = DatabentoSymbolMap()
        assert symbol_map.symbol_count == 0
        symbol_map.add_mapping(100, "AAPL")
        assert symbol_map.symbol_count == 1
        symbol_map.add_mapping(200, "TSLA")
        assert symbol_map.symbol_count == 2

    def test_all_symbols_returns_list_of_all_symbols(self) -> None:
        """all_symbols() returns a list of all mapped symbols."""
        symbol_map = DatabentoSymbolMap()
        symbol_map.add_mapping(100, "AAPL")
        symbol_map.add_mapping(200, "TSLA")
        symbol_map.add_mapping(300, "NVDA")
        symbols = symbol_map.all_symbols()
        assert len(symbols) == 3
        assert set(symbols) == {"AAPL", "TSLA", "NVDA"}

    def test_on_symbol_mapping_processes_msg_correctly(self) -> None:
        """on_symbol_mapping() processes SymbolMappingMsg correctly."""
        symbol_map = DatabentoSymbolMap()
        msg = MockSymbolMappingMsg(instrument_id=12345, stype_in_symbol="AAPL")
        symbol_map.on_symbol_mapping(msg)
        assert symbol_map.get_symbol(12345) == "AAPL"
        assert symbol_map.get_instrument_id("AAPL") == 12345

    def test_remapping_logs_and_updates_correctly(self) -> None:
        """Remapping same instrument_id to different symbol updates correctly."""
        symbol_map = DatabentoSymbolMap()
        # Initial mapping
        symbol_map.add_mapping(100, "OLD_SYMBOL")
        assert symbol_map.get_symbol(100) == "OLD_SYMBOL"
        assert symbol_map.get_instrument_id("OLD_SYMBOL") == 100

        # Remap via on_symbol_mapping (simulating corporate action / symbol change)
        msg = MockSymbolMappingMsg(instrument_id=100, stype_in_symbol="NEW_SYMBOL")
        symbol_map.on_symbol_mapping(msg)

        # New mapping should be in effect
        assert symbol_map.get_symbol(100) == "NEW_SYMBOL"
        assert symbol_map.get_instrument_id("NEW_SYMBOL") == 100
        # Old symbol should be removed
        assert symbol_map.get_instrument_id("OLD_SYMBOL") is None

    def test_empty_symbol_in_mapping_message_is_ignored(self) -> None:
        """Empty symbol in SymbolMappingMsg is ignored with warning."""
        symbol_map = DatabentoSymbolMap()
        msg = MockSymbolMappingMsg(instrument_id=100, stype_in_symbol="")
        symbol_map.on_symbol_mapping(msg)
        # Should not create any mapping
        assert symbol_map.get_symbol(100) is None
        assert symbol_map.symbol_count == 0

    def test_multiple_symbols_can_be_mapped_simultaneously(self) -> None:
        """Multiple symbols can be mapped in sequence."""
        symbol_map = DatabentoSymbolMap()
        symbols = [("AAPL", 100), ("TSLA", 200), ("NVDA", 300), ("AMD", 400)]
        for symbol, inst_id in symbols:
            symbol_map.add_mapping(inst_id, symbol)

        assert symbol_map.symbol_count == 4
        for symbol, inst_id in symbols:
            assert symbol_map.get_symbol(inst_id) == symbol
            assert symbol_map.get_instrument_id(symbol) == inst_id

    def test_clear_removes_all_mappings(self) -> None:
        """clear() removes all mappings."""
        symbol_map = DatabentoSymbolMap()
        symbol_map.add_mapping(100, "AAPL")
        symbol_map.add_mapping(200, "TSLA")
        assert symbol_map.symbol_count == 2

        symbol_map.clear()

        assert symbol_map.symbol_count == 0
        assert symbol_map.get_symbol(100) is None
        assert symbol_map.get_instrument_id("AAPL") is None

    def test_large_number_of_mappings_works_correctly(self) -> None:
        """Large number of mappings (1000+) works correctly."""
        symbol_map = DatabentoSymbolMap()

        # Add 1000 mappings
        for i in range(1000):
            symbol_map.add_mapping(i, f"SYM{i:04d}")

        assert symbol_map.symbol_count == 1000

        # Verify random samples
        assert symbol_map.get_symbol(0) == "SYM0000"
        assert symbol_map.get_symbol(500) == "SYM0500"
        assert symbol_map.get_symbol(999) == "SYM0999"
        assert symbol_map.get_instrument_id("SYM0000") == 0
        assert symbol_map.get_instrument_id("SYM0500") == 500
        assert symbol_map.get_instrument_id("SYM0999") == 999

    def test_on_symbol_mapping_with_mock_symbol_mapping_msg(self) -> None:
        """on_symbol_mapping() works with mock SymbolMappingMsg object."""
        symbol_map = DatabentoSymbolMap()

        # Simulate multiple mapping messages arriving at session start
        msgs = [
            MockSymbolMappingMsg(instrument_id=1001, stype_in_symbol="AAPL"),
            MockSymbolMappingMsg(instrument_id=1002, stype_in_symbol="MSFT"),
            MockSymbolMappingMsg(instrument_id=1003, stype_in_symbol="GOOGL"),
        ]

        for msg in msgs:
            symbol_map.on_symbol_mapping(msg)

        assert symbol_map.symbol_count == 3
        assert symbol_map.get_symbol(1001) == "AAPL"
        assert symbol_map.get_symbol(1002) == "MSFT"
        assert symbol_map.get_symbol(1003) == "GOOGL"
