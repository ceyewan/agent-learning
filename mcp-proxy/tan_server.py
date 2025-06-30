#!/usr/bin/env python3
"""
Tan MCP Server using fastmcp
Provides tangent function calculation
"""

import math
from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("tan-server")


@mcp.tool()
def calculate_tan(angle: float, unit: str = "radians") -> float:
    """
    Calculate the tangent of an angle.

    Args:
        angle: The angle value
        unit: The unit of the angle ("radians" or "degrees")

    Returns:
        The tangent of the angle
    """
    if unit.lower() == "degrees":
        angle = math.radians(angle)
    elif unit.lower() != "radians":
        raise ValueError("Unit must be 'radians' or 'degrees'")

    # Check for values where tan is undefined (90°, 270°, etc.)
    cos_val = math.cos(angle)
    if abs(cos_val) < 1e-10:  # Close to zero
        raise ValueError(f"Tangent is undefined for angle {angle} {unit}")

    return math.tan(angle)


@mcp.tool()
def tan_table(start: float, end: float, step: float = 1.0, unit: str = "degrees") -> list:
    """
    Generate a table of tangent values for a range of angles.

    Args:
        start: Starting angle
        end: Ending angle
        step: Step size between angles
        unit: The unit of angles ("radians" or "degrees")

    Returns:
        List of dictionaries containing angle and tangent value pairs
    """
    result = []
    current = start

    while current <= end:
        try:
            # Calculate tangent directly
            angle_rad = math.radians(
                current) if unit.lower() == "degrees" else current

            # Check for undefined values
            cos_val = math.cos(angle_rad)
            if abs(cos_val) < 1e-10:
                tan_value = "undefined"
            else:
                tan_value = round(math.tan(angle_rad), 6)

            result.append({
                "angle": current,
                "unit": unit,
                "tan": tan_value
            })
        except ValueError:
            result.append({
                "angle": current,
                "unit": unit,
                "tan": "undefined"
            })

        current += step

    return result


if __name__ == "__main__":
    # 使用标准的 stdio 传输
    mcp.run()  # 默认使用 stdio
