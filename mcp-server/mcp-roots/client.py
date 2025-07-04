import asyncio
import os
from fastmcp import Client

# Create test environment
os.makedirs("/tmp/allowed_area", exist_ok=True)
os.makedirs("/tmp/restricted_area", exist_ok=True)

with open("/tmp/allowed_area/public.txt", "w") as f:
    f.write("This is a public file allowed to access.")
with open("/tmp/restricted_area/private.txt", "w") as f:
    f.write("This is a restricted private file.")


async def test_with_roots():
    """Test with roots restriction"""
    print("🔒 Client specifies roots to restrict server access:")
    print("-" * 50)

    # Client only allows server to access /tmp/allowed_area
    roots = ["file:///tmp/allowed_area"]

    async with Client("server.py", roots=roots) as client:
        test_cases = [
            ("/tmp/allowed_area/public.txt", "✅ Should succeed"),
            ("/tmp/restricted_area/private.txt", "❌ Should be denied"),
            ("/etc/passwd", "❌ Should be denied")
        ]

        for filepath, expected in test_cases:
            print(f"\nTest path: {filepath} ({expected})")
            result = await client.call_tool("read_file", {"filepath": filepath})
            print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_with_roots())
