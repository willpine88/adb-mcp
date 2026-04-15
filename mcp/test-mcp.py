from mcp.server.fastmcp import FastMCP
mcp = FastMCP('test-server')

@mcp.tool()
def test_ping():
    return 'pong from test server'

mcp.run(transport='stdio')
