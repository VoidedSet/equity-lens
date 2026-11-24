"""Canonical company registry and alias normalization for EquityLens AI."""

from typing import Any, Dict, Optional, Tuple

_UNSET: Any = object()

CANONICAL_COMPANIES: Tuple[str, ...] = (
    "IHCL",
    "CHALET",
    "LEMONTREE",
    "EIH",
    "JUNIPER",
)

COMPANY_NAMES: Dict[str, str] = {
    "IHCL": "Indian Hotels Company Ltd",
    "CHALET": "Chalet Hotels Ltd",
    "LEMONTREE": "Lemon Tree Hotels Ltd",
    "EIH": "EIH Ltd (Oberoi Group)",
    "JUNIPER": "Juniper Hotels Ltd",
}

COMPANY_FOLDER_MAP: Dict[str, str] = {
    "Indian_Hotels": "IHCL",
    "Chalet_Hotels": "CHALET",
    "Lemon_Tree_Hotels": "LEMONTREE",
    "EIH_Limited": "EIH",
    "Juniper_Hotels": "JUNIPER",
}

COMPANY_ALIASES: Dict[str, str] = {
    # IHCL
    "ihcl": "IHCL",
    "indhotel": "IHCL",
    "indian_hotels": "IHCL",
    "indian hotels": "IHCL",
    "indian hotels company": "IHCL",
    "indian hotels company ltd": "IHCL",
    "taj": "IHCL",
    "taj hotels": "IHCL",
    # Chalet Hotels
    "chalet": "CHALET",
    "chalet_hotels": "CHALET",
    "chalet hotels": "CHALET",
    "chalet hotels ltd": "CHALET",
    # Lemon Tree Hotels
    "lemontree": "LEMONTREE",
    "lemon_tree": "LEMONTREE",
    "lemon tree": "LEMONTREE",
    "lemon_tree_hotels": "LEMONTREE",
    "lemon tree hotels": "LEMONTREE",
    "lemon tree hotels ltd": "LEMONTREE",
    # EIH
    "eih": "EIH",
    "eihotel": "EIH",
    "eih_limited": "EIH",
    "eih limited": "EIH",
    "eih ltd": "EIH",
    "oberoi": "EIH",
    "oberoi group": "EIH",
    # Juniper Hotels (ITCHOTELS in legacy extracted_json holds Juniper filings)
    "juniper": "JUNIPER",
    "juniperhotels": "JUNIPER",
    "juniper_hotels": "JUNIPER",
    "juniper hotels": "JUNIPER",
    "juniper hotels ltd": "JUNIPER",
    "itchotels": "JUNIPER",
    "itc hotels": "JUNIPER",
    "itc_hotels": "JUNIPER",
}


def normalize_company_id(value: str, default: Any = _UNSET) -> Optional[str]:
    """Resolve any company code, folder name, or alias to its canonical company ID."""
    if not isinstance(value, str):
        if default is not _UNSET:
            return default
        raise ValueError(f"Company identifier must be a string, got {type(value).__name__}")

    cleaned = value.strip()
    if not cleaned:
        if default is not _UNSET:
            return default
        raise ValueError("Company identifier cannot be empty")

    key = cleaned.lower().replace("-", " ")
    key_collapsed = " ".join(key.split())

    for candidate in (key, key_collapsed, key_collapsed.replace(" ", "_"), key_collapsed.replace("_", "")):
        if candidate in COMPANY_ALIASES:
            return COMPANY_ALIASES[candidate]

    if default is not _UNSET:
        return default
    raise ValueError(f"Unknown company identifier: {value!r}")
