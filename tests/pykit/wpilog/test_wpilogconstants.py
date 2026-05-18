"""Unit tests for wpilogconstants module."""

import json
from lib_6107.pykit.wpilog import wpilogconstants


def test_constants_extrahheader_is_pykit():
    """Verify extraHeader constant has correct value."""
    assert wpilogconstants.extraHeader == "PyKit"


def test_constants_entry_metadata_is_valid_json():
    """Verify entryMetadata is valid JSON with PyKit source."""
    data = json.loads(wpilogconstants.entryMetadata)
    assert data["source"] == "PyKit"


def test_constants_entry_metadata_units_has_placeholder():
    """Verify entryMetadataUnits contains unit placeholder."""
    assert "$UNITSTR" in wpilogconstants.entryMetadataUnits


def test_constants_entry_metadata_units_substitution():
    """Verify entryMetadataUnits substitution works."""
    metadata = wpilogconstants.entryMetadataUnits.replace("$UNITSTR", "m/s")
    data = json.loads(metadata)
    assert data["unit"] == "m/s"

