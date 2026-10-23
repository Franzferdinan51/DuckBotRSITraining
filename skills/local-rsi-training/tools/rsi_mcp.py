#!/usr/bin/env python3
"""rsi_mcp.py — drive the mlx-lm-lora MCP server on the Mac via stdio JSON-RPC.

Runs ON the Mac (the cron driver calls it through ~/bin/mac-ssh, or run it
from any shell on the Mac directly). Spawns the MCP server, does the
initialize handshake, calls ONE tool, prints the JSON result, exits.

Usage:
  python3 rsi_mcp.py list-tools
  python3 rsi_mcp.py check_training_config '{"config_path": "..."}'
  python3 rsi_mcp.py training_status '{}'

Exit code 0 = tool call returned; 2 = protocol/transport error.
"""
import json
import os
import subprocess
import sys

SERVER = "/Users/duckets/mlx-lm-lora/.venv/bin/mlx-lm-lora-mcp"

# A leaked PYTHONPATH (e.g. from the Hermes runtime) makes `import mcp` resolve
# a foreign site-packages build and the server exits with "needs the mcp
# package". The venv is self-sufficient — strip it for the child.
SERVER_ENV = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}


def rpc(proc, msg_id, method, params):
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": msg_id,
                                 "method": method, "params": params}) + "\n")
    proc.stdin.flush()
    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("MCP server closed stdout")
        msg = json.loads(line)
        if msg.get("id") == msg_id:
            return msg


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    tool = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}

    proc = subprocess.Popen([SERVER], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, text=True,
                            env=SERVER_ENV)
    try:
        init = rpc(proc, 1, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "rsi-driver", "version": "1.0"}})
        if "error" in init:
            print(json.dumps(init["error"]))
            return 2
        proc.stdin.write(json.dumps({
            "jsonrpc": "2.0", "method": "notifications/initialized",
            "params": {}}) + "\n")
        proc.stdin.flush()

        if tool == "list-tools":
            res = rpc(proc, 2, "tools/list", {})
            names = [t["name"] for t in res["result"]["tools"]]
            print(json.dumps({"tools": names}, indent=2))
            return 0

        res = rpc(proc, 2, "tools/call", {"name": tool, "arguments": args})
        if "error" in res:
            print(json.dumps(res["error"]))
            return 2
        print(json.dumps(res["result"], indent=2))
        return 0
    except Exception as e:  # transport failure — report, don't fake a result
        print(json.dumps({"transport_error": str(e)}))
        return 2
    finally:
        proc.terminate()


if __name__ == "__main__":
    sys.exit(main())
