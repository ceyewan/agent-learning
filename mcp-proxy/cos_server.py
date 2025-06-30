#!/usr/bin/env python3
"""
Cos MCP Server using fastmcp
Provides cosine function calculation
"""

import math
from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("cos-server")


@mcp.tool()
def calculate_cos(angle: float, unit: str = "radians") -> float:
    """
    Calculate the cosine of an angle.

    Args:
        angle: The angle value
        unit: The unit of the angle ("radians" or "degrees")

    Returns:
        The cosine of the angle
    """
    if unit.lower() == "degrees":
        angle = math.radians(angle)
    elif unit.lower() != "radians":
        raise ValueError("Unit must be 'radians' or 'degrees'")

    return math.cos(angle)


@mcp.tool()
def cos_table(start: float, end: float, step: float = 1.0, unit: str = "degrees") -> list:
    """
    Generate a table of cosine values for a range of angles.

    Args:
        start: Starting angle
        end: Ending angle
        step: Step size between angles
        unit: The unit of angles ("radians" or "degrees")

    Returns:
        List of dictionaries containing angle and cosine value pairs
    """
    result = []
    current = start

    while current <= end:
        # Calculate cosine directly
        angle_rad = math.radians(
            current) if unit.lower() == "degrees" else current
        cos_value = math.cos(angle_rad)
        result.append({
            "angle": current,
            "unit": unit,
            "cos": round(cos_value, 6)
        })
        current += step

    return result


if __name__ == "__main__":
    # 使用标准的 stdio 传输
    mcp.run()  # 默认使用 stdio
