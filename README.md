# LONG AI MCP Server

把 [LONG AI](https://ai.dijinlong.com) 的 OpenAI 兼容网关包成一个 MCP server，让 Claude Desktop / Cursor / Cline 这类客户端可以直接:

- 列模型 (`list_models`)
- 跑一次对话并看 `usage` (`chat`)
- 体检任意 OpenAI 兼容网关是否真的兼容 (`check_compatibility`)

同时它也是个**可复用的 MCP 客户端脚手架**——代码里没有 SDK 依赖、没有 `openai` 包，所有请求都是标准库直打 HTTP，改两行就能指向你自己的网关。

## 为什么不是又一个 chat wrapper

大多数 "LLM MCP server" 只做一件事:把 prompt 转发出去。这个多做两件事:

1. **把 `usage` 原样带回来**。MCP 让模型自己调模型,很容易忽略计费;`usage` 出现在工具返回值里,调用方就能看见 token 消耗。
2. **`check_compatibility`**。中转型网关在中转过程中会静默丢语义(丢 `tools`、流里没有 `[DONE]`、不存在的模型返回 200 + error)。这个 tool 用 4 个请求把这几件事变成一行 `FAIL`,而不是线上故障。

## 安装

```bash
pip install "mcp>=1.2"
git clone https://github.com/Dijinlong/longai-mcp-server.git
cd longai-mcp-server
```

## 配置

Claude Desktop (`claude_desktop_config.json`) 或 Cursor (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "longai": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"],
      "env": {
        "LONGAI_API_KEY": "sk-your-key",
        "LONGAI_BASE_URL": "https://ai.dijinlong.com/v1"
      }
    }
  }
}
```

`LONGAI_BASE_URL` 换成任何 OpenAI 兼容地址都能用,包括官方 `https://api.openai.com/v1`——这时它就是一把通用的"兼容性探针"。

## 工具说明

| Tool | 参数 | 作用 |
|---|---|---|
| `list_models` | — | 返回网关当前上架的模型 id 列表,用来确认模型名对不对 |
| `chat` | `model`, `messages`, `temperature`, `max_tokens` | 发一次非流式请求,返回正文 + `usage` + 耗时 |
| `check_compatibility` | `model`(默认 `gpt-4o-mini`) | 4 项体检:鉴权/清单、非流式、流式 `[DONE]`、错误体形状 |

## 输出示例

```text
1. GET /models            200  182ms, models=77
2. POST chat (no stream)  200  940ms  usage={'prompt_tokens': 12, 'completion_tokens': 3, 'total_tokens': 15}
3. POST chat (stream)     200  310ms  [DONE]=yes
4. POST unknown model     404  96ms   错误形状正常
----------------------------------------------
PASS
```

## 安全提示

- key 只从环境变量读,不写进配置文件、不打日志。
- `chat` 不落盘任何 prompt 内容。
- 这个 server 只做转发与探针,不缓存请求、不代理第三方密钥。

## License

MIT
