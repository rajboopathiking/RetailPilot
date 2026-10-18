"""
test_app.py — Verification and Test Suite for app.py

Validates:
1. REST API endpoints (GET /, GET /health)
2. Universal Tool via HTTP REST (POST /calculate)
3. LangServe LCEL chain via HTTP (POST /agent/invoke)
4. FastMCP tool discovery & execution (calculate, agent_chain_runner, get_system_metrics)
5. In-process LangChain chain execution through MCP
6. Automatic FastAPI Depends() resolution inside MCP
"""

import asyncio
from fastapi.testclient import TestClient
from app import app, nexus


def test_http_endpoints():
    print("\n--- 1. Testing HTTP REST Endpoints ---")
    with TestClient(app) as client:
        # A. Test Root endpoint (API Only)
        res_root = client.get("/")
        assert res_root.status_code == 200, f"Root failed: {res_root.text}"
        print("✅ GET /:", res_root.json()["service"])

        # B. Test Health endpoint (API Only)
        res_health = client.get("/health")
        assert res_health.status_code == 200, f"Health failed: {res_health.text}"
        print("✅ GET /health:", res_health.json())

        # C. Test Universal Tool via HTTP REST (POST /calculate)
        res_calc = client.post(
            "/calculate",
            json={"operation": "multiply", "a": 7, "b": 6},
        )
        assert res_calc.status_code == 200, f"Calculate failed: {res_calc.text}"
        calc_data = res_calc.json()
        assert calc_data["result"] == 42.0
        assert calc_data["context"]["framework"] == "UnifiedNexus + LangServe"
        print("✅ POST /calculate (REST):", calc_data)

        # D. Test LangServe LCEL chain via HTTP REST (POST /agent/invoke)
        res_ls = client.post(
            "/agent/invoke",
            json={"input": {"input": "Hello from LangServe HTTP Client"}},
        )
        assert res_ls.status_code == 200, f"LangServe invoke failed: {res_ls.text}"
        ls_data = res_ls.json()
        print("✅ POST /agent/invoke (LangServe):", ls_data["output"])

        # E. Test FastMCP SSE endpoint status
        res_mcp = client.get("/mcp")
        # FastMCP responds with 400/406 when accessed without MCP SSE protocol headers
        assert res_mcp.status_code in (400, 406), f"MCP mount check failed: {res_mcp.status_code}"
        print("✅ GET /mcp (FastMCP Mount): Responding as expected (Status:", res_mcp.status_code, ")")


async def test_mcp_tools():
    print("\n--- 2. Testing FastMCP Tools (AI Agent Layer) ---")
    # A. List registered MCP tools
    tools = await nexus.mcp.list_tools()
    tool_names = [t.name for t in tools]
    print("✅ Discovered MCP Tools:", tool_names)
    assert "calculate" in tool_names, "Universal tool 'calculate' missing from MCP"
    assert "agent_chain_runner" in tool_names, "MCP tool 'agent_chain_runner' missing"
    assert "get_system_metrics" in tool_names, "MCP tool 'get_system_metrics' missing"
    assert "root" not in tool_names, "'root' was marked @api_only and should NOT be in MCP"
    assert "health_check" not in tool_names, "'health_check' was marked @api_only and should NOT be in MCP"

    # B. Test Universal Tool via MCP (with auto-resolved Depends)
    calc_tool = await nexus.mcp.get_tool("calculate")
    calc_res = await calc_tool.run({
        "req": {"operation": "add", "a": 55.5, "b": 44.5}
    })
    print("✅ MCP Tool 'calculate' Result:", calc_res.structured_content)
    assert calc_res.structured_content["result"] == 100.0
    assert calc_res.structured_content["context"]["framework"] == "UnifiedNexus + LangServe"

    # C. Test MCP-only Tool that invokes LangChain chain in-process
    chain_tool = await nexus.mcp.get_tool("agent_chain_runner")
    chain_res = await chain_tool.run({
        "query": "Autonomous Agent Tool Invocation"
    })
    print("✅ MCP Tool 'agent_chain_runner' (In-Process LangChain):", chain_res.structured_content)
    assert "LangServe Processed" in chain_res.structured_content["agent_response"]
    assert chain_res.structured_content["in_process"] is True

    # D. Test MCP-only Metrics Tool
    metrics_tool = await nexus.mcp.get_tool("get_system_metrics")
    metrics_res = await metrics_tool.run({})
    print("✅ MCP Tool 'get_system_metrics':", metrics_res.structured_content)
    assert metrics_res.structured_content["status"] == "optimal"


if __name__ == "__main__":
    test_http_endpoints()
    asyncio.run(test_mcp_tools())
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!\n")
