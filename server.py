#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LONG AI MCP server — 把 LONG AI 的 OpenAI 兼容网关包成 MCP 工具。

三个 tool：
  list_models          列出当前可用的模型（含价格倍率，若网关返回）
  chat                 发一次对话请求（支持任意 OpenAI 兼容模型）
  check_compatibility  用 4 个请求快速体检当前 base_url 是否真的兼容

环境变量：
  LONGAI_API_KEY   必填，形如 sk-xxx
  LONGAI_BASE_URL  可选，默认 https://ai.dijinlong.com/v1
"""

import json
import os
import time
import urllib.error
import urllib.request

from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get("LONGAI_BASE_URL", "https://ai.dijinlong.com/v1").rstrip("/")
API_KEY = os.environ.get("LONGAI_API_KEY", "")
TIMEOUT = int(os.environ.get("LONGAI_TIMEOUT", "120"))

mcp = FastMCP("longai")


def _request(path: str, payload=None, method=None, timeout=TIMEOUT):
    """直接打 HTTP，不走 SDK，方便把状态码和错误体原样带回来。"""
    url = f"{BASE_URL}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method=method or ("POST" if data else "GET"))
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            return resp.status, body, time.time() - started
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        return e.code, body, time.time() - started
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}", time.time() - started


@mcp.tool()
def list_models() -> str:
    """列出网关当前上架的模型 id。切模型、确认某个模型是否可用时先跑这个。"""
    status, body, ms = _request("/models")
    if status != 200:
        return f"HTTP {status} ({ms:.0f}ms)\n{body[:800]}"
    try:
        data = json.loads(body)
    except Exception:
        return body[:800]
    ids = [m.get("id") for m in data.get("data", []) if m.get("id")]
    return json.dumps({"count": len(ids), "models": ids}, ensure_ascii=False, indent=2)


@mcp.tool()
def chat(model: str, messages: list[dict], temperature: float = 0.7, max_tokens: int = 1024) -> str:
    """发一次非流式对话请求。messages 用 OpenAI 格式：[{"role":"user","content":"..."}]。

    返回值里带 usage，方便核对计费。
    """
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    status, body, ms = _request("/chat/completions", payload)
    if status != 200:
        return f"HTTP {status} ({ms:.0f}ms)\n{body[:800]}"
    try:
        data = json.loads(body)
    except Exception:
        return body[:800]
    choices = data.get("choices") or [{}]
    content = (choices[0].get("message") or {}).get("content", "")
    return json.dumps({
        "content": content,
        "model": data.get("model"),
        "usage": data.get("usage"),
        "latency_ms": round(ms),
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def check_compatibility(model: str = "gpt-4o-mini") -> str:
    """4 个请求体检：鉴权/模型清单、非流式、流式 [DONE]、错误体形状。

    接一个新网关、或者怀疑中转层吞了字段时跑这个。
    """
    lines = []

    status, body, ms = _request("/models")
    ok1 = status == 200
    count = ""
    if ok1:
        try:
            count = f"，models={len(json.loads(body).get('data', []))}"
        except Exception:
            pass
    lines.append(f"1. GET /models            {status}  {ms:.0f}ms{count}")

    payload = {"model": model, "messages": [{"role": "user", "content": "ping"}]}
    status, body, ms = _request("/chat/completions", payload)
    usage = ""
    if status == 200:
        try:
            usage = f"  usage={json.loads(body).get('usage')}"
        except Exception:
            pass
    lines.append(f"2. POST chat (no stream)  {status}  {ms:.0f}ms{usage}")

    stream_payload = dict(payload, stream=True)
    status, body, ms = _request("/chat/completions", stream_payload)
    has_done = "[DONE]" in body
    lines.append(f"3. POST chat (stream)     {status}  {ms:.0f}ms  [DONE]={'yes' if has_done else 'NO'}")

    status, body, ms = _request("/chat/completions",
                                {"model": "model-that-does-not-exist-xyz",
                                 "messages": [{"role": "user", "content": "x"}]})
    wrapped = status == 200 and '"error"' in body[:200]
    lines.append(f"4. POST unknown model     {status}  {ms:.0f}ms  "
                 f"{'200 里包 error（最容易踩）' if wrapped else '错误形状正常'}")

    passed = ok1 and has_done and not wrapped
    lines.append("-" * 46)
    lines.append("PASS" if passed else "FAIL（看上面哪一项）")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
