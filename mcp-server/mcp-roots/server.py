from fastmcp import FastMCP
import os

mcp = FastMCP("MCP Roots Server")


@mcp.tool()
def read_file(filepath: str) -> str:
    abs_path = os.path.abspath(filepath)
    allowed = False
    for root in roots_list:
        if root.startswith("file://"):
            root_path = root.replace("file://", "")
            if abs_path.startswith(root_path):
                allowed = True
                break
    if not allowed:
        return f"❌ Access denied: {abs_path} is not within the allowed roots_list."
    with open(filepath, 'r') as f:
        content = f.read()
    return f"✅ File content: {content[:100]}..."


@mcp.tool()
def list_files(directory: str) -> str:
    """List directory files - restricted by client roots"""
    try:
        files = os.listdir(directory)
        return f"✅ Directory content: {files}"
    except Exception as e:
        return f"❌ List failed: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
