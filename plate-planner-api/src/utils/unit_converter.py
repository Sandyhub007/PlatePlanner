"""Unit Conversion Utility for Shopping Lists - Phase 3

Handles conversion between different units (volume, weight, count).
Uses pint library for accurate conversions.
"""

from __future__ import annotations

from typing import Optional, Tuple

# Try to import pint, fallback to simple conversion if unavailable
try:
    from pint import UnitRegistry, UndefinedUnitError, DimensionalityError
    ureg = UnitRegistry()
    Q_ = ureg.Quantity
    PINT_AVAILABLE = True
except (ImportError, AttributeError):
    PINT_AVAILABLE = False
    # Fallback: simple conversion factors
    pass


# Common unit aliases for ingredients
UNIT_ALIASES = {
    # Volume
    "cup": "cup",
    "cups": "cup",
    "c": "cup",
    "liter": "liter",
    "liters": "liter",
    "l": "liter",
    "litre": "liter",
    "litres": "liter",
    "ml": "milliliter",
    "milliliter": "milliliter",
    "milliliters": "milliliter",
    "millilitre": "milliliter",
    "millilitres": "milliliter",
    "fl oz": "fluid_ounce",
    "fluid ounce": "fluid_ounce",
    "fluid ounces": "fluid_ounce",
    "tbsp": "tablespoon",
    "tablespoon": "tablespoon",
    "tablespoons": "tablespoon",
    "tsp": "teaspoon",
    "teaspoon": "teaspoon",
    "teaspoons": "teaspoon",
    "pint": "pint",
    "pints": "pint",
    "pt": "pint",
    "quart": "quart",
    "quarts": "qt",
    "qt": "quart",
    "gallon": "gallon",
    "gallons": "gallon",
    "gal": "gallon",
    
    # Weight
    "gram": "gram",
    "grams": "gram",
    "g": "gram",
    "kilogram": "kilogram",
    "kilograms": "kilogram",
    "kg": "kilogram",
    "pound": "pound",
    "pounds": "pound",
    "lb": "pound",
    "lbs": "pound",
    "ounce": "ounce",
    "ounces": "ounce",
    "oz": "ounce",
    
    # Count (no conversion, just normalization)
    "item": "item",
    "items": "item",
    "piece": "item",
    "pieces": "item",
    "pc": "item",
    "pcs": "item",
    "each": "item",
    "ea": "item",
    "clove": "item",
    "cloves": "item",
    "stalk": "item",
    "stalks": "item",
    "head": "item",
    "heads": "item",
    "bunch": "item",
    "bunches": "item",
}


def normalize_unit(unit: str) -> str:
    """
    Normalize unit name to standard form.
    
    Args:
        unit: Unit string (e.g., "cups", "ml", "lbs")
    
    Returns:
        Normalized unit name
    """
    if not unit:
        return "item"
    
    unit_lower = unit.strip().lower()
    return UNIT_ALIASES.get(unit_lower, unit_lower)


def can_convert_units(unit1: str, unit2: str) -> bool:
    """
    Check if two units can be converted (same dimension).
    
    Args:
        unit1: First unit
        unit2: Second unit
    
    Returns:
        True if units are compatible
    """
    if not PINT_AVAILABLE:
        # Simple fallback: check if same category
        norm1 = normalize_unit(unit1)
        norm2 = normalize_unit(unit2)
        
        volume_units = {"cup", "liter", "milliliter", "fluid_ounce", "tablespoon", "teaspoon", "pint", "quart", "gallon"}
        weight_units = {"gram", "kilogram", "pound", "ounce"}
        
        if norm1 == "item" or norm2 == "item":
            return norm1 == norm2
        
        if norm1 in volume_units and norm2 in volume_units:
            return True
        if norm1 in weight_units and norm2 in weight_units:
            return True
        
        return False
    
    try:
        norm1 = normalize_unit(unit1)
        norm2 = normalize_unit(unit2)
        
        # Count units can't be converted to weight/volume
        if norm1 == "item" or norm2 == "item":
            return norm1 == norm2
        
        # Try to create quantities and check dimensionality
        q1 = Q_(1, norm1)
        q2 = Q_(1, norm2)
        
        return q1.dimensionality == q2.dimensionality
    except (UndefinedUnitError, DimensionalityError, ValueError, AttributeError):
        return False


def convert_quantity(
    quantity: float,
    from_unit: str,
    to_unit: str
) -> Optional[float]:
    """
    Convert quantity from one unit to another.
    
    Args:
        quantity: Quantity value
        from_unit: Source unit
        to_unit: Target unit
    
    Returns:
        Converted quantity, or None if conversion not possible
    """
    if not PINT_AVAILABLE:
        # Simple fallback: basic conversion factors
        return _simple_convert(quantity, from_unit, to_unit)
    
    try:
        norm_from = normalize_unit(from_unit)
        norm_to = normalize_unit(to_unit)
        
        # Count units: no conversion, just return same value
        if norm_from == "item" or norm_to == "item":
            if norm_from == norm_to:
                return quantity
            return None
        
        # Create quantities and convert
        q = Q_(quantity, norm_from)
        converted = q.to(norm_to)
        
        return float(converted.magnitude)
    except (UndefinedUnitError, DimensionalityError, ValueError, AttributeError):
        # Fallback to simple conversion
        return _simple_convert(quantity, from_unit, to_unit)


def _simple_convert(quantity: float, from_unit: str, to_unit: str) -> Optional[float]:
    """Simple conversion using basic factors (fallback when pint unavailable)"""
    norm_from = normalize_unit(from_unit)
    norm_to = normalize_unit(to_unit)
    
    if norm_from == norm_to:
        return quantity
    
    # Volume conversions (to cups as base)
    volume_to_cups = {
        "cup": 1.0,
        "milliliter": 0.00422675,
        "liter": 4.22675,
        "fluid_ounce": 0.125,
        "tablespoon": 0.0625,
        "teaspoon": 0.0208333,
        "pint": 2.0,
        "quart": 4.0,
        "gallon": 16.0,
    }
    
    # Weight conversions (to pounds as base)
    weight_to_pounds = {
        "pound": 1.0,
        "ounce": 0.0625,
        "gram": 0.00220462,
        "kilogram": 2.20462,
    }
    
    # Try volume conversion
    if norm_from in volume_to_cups and norm_to in volume_to_cups:
        cups = quantity * volume_to_cups[norm_from]
        return cups / volume_to_cups[norm_to]
    
    # Try weight conversion
    if norm_from in weight_to_pounds and norm_to in weight_to_pounds:
        pounds = quantity * weight_to_pounds[norm_from]
        return pounds / weight_to_pounds[norm_to]
    
    return None


def find_best_unit(quantities: list[Tuple[float, str]]) -> str:
    """
    Find the best unit to represent a list of quantities.
    
    Prefers:
    1. Most common unit
    2. Most precise unit (smaller base unit)
    3. Most readable unit
    
    Args:
        quantities: List of (quantity, unit) tuples
    
    Returns:
        Best unit name
    """
    if not quantities:
        return "item"
    
    # Count occurrences of each unit
    unit_counts: dict[str, int] = {}
    for _, unit in quantities:
        norm_unit = normalize_unit(unit)
        unit_counts[norm_unit] = unit_counts.get(norm_unit, 0) + 1
    
    # If all same unit, return it
    if len(unit_counts) == 1:
        return list(unit_counts.keys())[0]
    
    # Group by dimension
    volume_units = {"cup", "liter", "milliliter", "fluid_ounce", "tablespoon", "teaspoon", "pint", "quart", "gallon"}
    weight_units = {"gram", "kilogram", "pound", "ounce"}
    
    # Find most common unit per dimension
    volume_units_present = {u: c for u, c in unit_counts.items() if u in volume_units}
    weight_units_present = {u: c for u, c in unit_counts.items() if u in weight_units}
    
    if volume_units_present:
        # Prefer cups for volume (most common in recipes)
        if "cup" in volume_units_present:
            return "cup"
        return max(volume_units_present.items(), key=lambda x: x[1])[0]
    
    if weight_units_present:
        # Prefer pounds for weight (most common in US)
        if "pound" in weight_units_present:
            return "pound"
        return max(weight_units_present.items(), key=lambda x: x[1])[0]
    
    # Default to most common unit
    return max(unit_counts.items(), key=lambda x: x[1])[0]


def consolidate_quantities(
    quantities: list[Tuple[float, str]]
) -> Tuple[float, str]:
    """
    Consolidate multiple quantities with different units into one.
    
    Args:
        quantities: List of (quantity, unit) tuples
    
    Returns:
        Tuple of (total_quantity, best_unit)
    """
    if not quantities:
        return (0.0, "item")
    
    if len(quantities) == 1:
        qty, unit = quantities[0]
        return (qty, normalize_unit(unit))
    
    # Find best unit to convert everything to
    best_unit = find_best_unit(quantities)
    
    # Convert all to best unit and sum
    total = 0.0
    for qty, unit in quantities:
        if can_convert_units(unit, best_unit):
            converted = convert_quantity(qty, unit, best_unit)
            if converted is not None:
                total += converted
        elif normalize_unit(unit) == normalize_unit(best_unit):
            # Same unit, just add
            total += qty
    
    return (round(total, 2), best_unit)

