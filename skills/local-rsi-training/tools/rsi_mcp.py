#!/usr/bin/env python3
"""rsi_mcp.py — drive the mlx-lm-lora MCP server on the Mac via stdio JSON-RPC.

Runs ON the Mac (the cron driver calls it through ~/bin/mac-ssh, or run it
from any shell on the Mac directly). Spawns the MCP server, does the
initialize handshake, calls ONE tool, prints the JSON result, exits.

Usage:
  python3 rsi_mcp.py list-tools
  python3 rsi_mcp.py check_training_config '{"config_path": "..."}'
  python3 rsi_mcp.py training_status '{}'

Exit codes: 0 = tool call succeeded; 3 = the tool itself returned an
isError result; 2 = protocol/transport/timeout error. (Audit fix
2026-10-23: previously isError results were printed as success with
exit 0, reads had no timeout, and the server path was hardcoded.)

Env: RSI_MCP_SERVER overrides the server binary path;
RSI_MCP_TIMEOUT (seconds, default 300) bounds each RPC wait.
"""
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

SERVER = os.environ.get(
    "RSI_MCP_SERVER",
    str(Path.home() / "mlx-lm-lora" / ".venv" / "bin" / "mlx-lm-lora-mcp"))
TIMEOUT = float(os.environ.get("RSI_MCP_TIMEOUT", "300"))

# A leaked PYTHONPATH (e.g. from the Hermes runtime) makes `import mcp` resolve
# a foreign site-packages build and the server exits with "needs the mcp
# package". The venv is self-sufficient — strip it for the child.
SERVER_ENV = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}


class RpcTimeout(Exception):
    pass


def rpc(proc, msg_id, method, params, timeout=TIMEOUT):
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": msg_id,
                                 "method": method, "params": params}) + "\n")
    proc.stdin.flush()
    box = {}

    def reader():
        try:
            while True:
                line = proc.stdout.readline()
                if not line:
                    box["error"] = RuntimeError("MCP server closed stdout")
                    return
                msg = json.loads(line)
                if msg.get("id") == msg_id:
                    box["msg"] = msg
                    return
        except Exception as e:  # surfaced to the caller below
            box["error"] = e

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise RpcTimeout(f"no response to {method} within {timeout:.0f}s")
    if "error" in box:
        raise box["error"]
    return box["msg"]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    tool = sys.argv[1]
    try:
        args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    except json.JSONDecodeError as e:
        print(json.dumps({"transport_error": f"bad arguments JSON: {e}"}))
        return 2

    if not Path(SERVER).exists():
        print(json.dumps({"transport_error": f"MCP server not found: {SERVER}"}))
        return 2

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
            if "error" in res:
                print(json.dumps(res["error"]))
                return 2
            names = [t["name"] for t in res["result"]["tools"]]
            print(json.dumps({"tools": names}, indent=2))
            return 0

        res = rpc(proc, 2, "tools/call", {"name": tool, "arguments": args})
        if "error" in res:
            print(json.dumps(res["error"]))
            return 2
        result = res.get("result", {})
        if result.get("isError"):
            # The tool ran and reported failure — that is NOT success.
            print(json.dumps(result, indent=2))
            return 3
        print(json.dumps(result, indent=2))
        return 0
    except RpcTimeout as e:
        print(json.dumps({"transport_error": str(e)}))
        return 2
    except Exception as e:  # transport failure — report, don't fake a result
        print(json.dumps({"transport_error": str(e)}))
        return 2
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
