import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib.util
spec = importlib.util.spec_from_file_location("ps_mcp", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ps-mcp.py"))
ps_mcp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ps_mcp)

mcp = ps_mcp.mcp

if __name__ == "__main__":
    mcp.run(transport="sse")