# 中软模型网关

给桌面端用的公司网关：**复用 MES 账号登录**、模型别名路由、OpenAI 兼容流式转发（含工具调用），厂商 Key 只留在这台服务器上。

上游可以是多个厂商：每个别名在目录表里绑定**唯一**的「供应商 + Key + 真实模型」，客户端只能看到遮罩后的 Key（前 8 位 + `*****` + 后 4 位），完整 Key 永不下发、不入库。没有目录表时退回单上游的旧配置。SQLite 存储，除 FastAPI/httpx/uvicorn 外无其它依赖。

网关代码与 MES 在同一个仓库（`zr-aicoding/gateway/`），但**部署上完全独立**：服务器放在 `/www/wwwroot/DSH-MOM/gateway/`，独立进程、独立数据库、独立 systemd 单元，不改动 MES 的 `backend/` 与 `frontend/` 任何文件。

## 登录模型

登录不再由网关自己存密码，而是转发给同机 MES：

```
桌面端 --POST /api/login--> 网关 --POST http://127.0.0.1:8009/api/auth/login--> MES
```

- 账号、密码、bcrypt 哈希全部留在 MES（`erp.db`），网关不落任何密码。
- MES 返回 401 时网关回同样的 401 `invalid_credentials`，不区分"账号不存在"和"密码错误"。
- MES 不可达或返回 5xx 时网关回 502 `login_unavailable`，桌面端提示稍后重试。
- 校验通过后网关签发自己的不透明令牌（256 位随机数，库里只存 SHA-256 摘要），有效期与桌面端本地会话一致。
- 网关登录会在 MES 侧留下一条普通登录审计，与 Web 端登录一致。

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `ZR_GATEWAY_CATALOG` | 空 | 目录表文件路径（见下节）。设置后忽略下面的单上游变量 |
| `ZR_GATEWAY_ADMIN_TOKEN` | 空 | 管理员令牌，至少 16 位；设置后开放 `/v1/admin/usage/models`，不设则该路由不存在（404） |
| `ZR_GATEWAY_UPSTREAM_BASE_URL` | `https://api.deepseek.com` | 单上游模式的上游地址，可带路径（如 `https://api.deepseek.com/v1`）；只允许 HTTPS，回环地址可用 HTTP |
| `ZR_GATEWAY_UPSTREAM_KEY` | 单上游模式必填 | 上游 Key；也可以改用 `ZR_GATEWAY_UPSTREAM_KEY_FILE` 指向一个 600 权限的文件 |
| `ZR_GATEWAY_MODEL_MAP` | `standard=deepseek-chat,deep=deepseek-reasoner` | 单上游模式的 `别名=真实模型名`，逗号分隔。别名必须与桌面端 `GATEWAY_MODELS`（`standard`、`deep`）一致 |
| `ZR_GATEWAY_MES_BASE_URL` | `http://127.0.0.1:8009` | MES 后端地址，只用于登录校验；保持回环，不要指向公网域名 |
| `ZR_GATEWAY_MES_TIMEOUT_SECONDS` | `10` | 登录校验超时 |
| `ZR_GATEWAY_DB` | `gateway.sqlite3` | 会话与用量流水（不含账号） |
| `ZR_GATEWAY_TOKEN_TTL_SECONDS` | `604800`（7 天） | 令牌有效期，与桌面端本地会话一致 |
| `ZR_GATEWAY_UPSTREAM_TIMEOUT_SECONDS` | `600` | 无输出超时；长任务需要放宽 |
| `ZR_GATEWAY_FORCE_USAGE` | `1` | 流式请求强制 `stream_options.include_usage`，否则拿不到 usage |
| `ZR_GATEWAY_HOST` / `ZR_GATEWAY_PORT` | `127.0.0.1` / `8787` | 监听地址。对外交给 nginx，不要直接暴露 |
| `ZR_GATEWAY_LOG_LEVEL` | `INFO` | 日志级别 |

**不要用 `http://<公网 IP>` 暴露**：桌面端只接受 HTTPS 的网关地址，令牌在明文 HTTP 下等于裸奔。

## 供应商 / Key / 模型目录

一个别名只绑定一个供应商、一把 Key、一个真实模型。这张表在启动时校验，任何一处不一致（别名重复、供应商不存在、用途非法、Key 缺失）都会让网关**拒绝启动**，不会带病运行。

`/etc/zr-gateway/catalog.json`（600 权限）：

```json
{
  "providers": [
    {
      "id": "deepseek-official",
      "displayName": "DeepSeek 官方",
      "baseUrl": "https://api.deepseek.com",
      "keyFile": "/etc/zr-gateway/upstream.key"
    }
  ],
  "models": [
    { "alias": "standard", "displayName": "标准", "provider": "deepseek-official", "model": "deepseek-v4-flash", "purpose": "llm" },
    { "alias": "deep", "displayName": "深度", "provider": "deepseek-official", "model": "deepseek-reasoner", "purpose": "llm" }
  ]
}
```

- `id` / `alias`：字母数字开头，可含 `._-`，最长 64 位，全局唯一。
- `provider`：必须命中 `providers[].id`；`model`：真实上游模型名。
- `purpose`：`llm` 或 `code`，默认 `llm`。
- Key 只能来自 `keyEnv`（环境变量名）或 `keyFile`（600 权限文件），**目录表里不允许写明文 Key**。
- 客户端（登录响应、`/v1/catalog`、用量接口）只会看到 `keyHint`，例如 `sk-fc6ef*****d460`；少于 16 位的 Key 会被拒绝启动，避免遮罩后仍可还原。
- Key 变更后重启网关即可，不用重新打包桌面端。

## 用量归属

每个请求按所选别名记下 `provider_id`、`key_hint`、真实模型与用途，因此「哪个模型用了哪把 Key」由网关说了算，不靠前端猜测。默认统计最近 30 天。

## 安装

服务器上与 MES 同一台，但单独放在 `/www/wwwroot/DSH-MOM`（`DSH-MOM` 目录下只放网关，不碰 MES 的 `zr-aicoding` 目录）：

```bash
mkdir -p /www/wwwroot/DSH-MOM
# 把仓库里的 gateway/ 整个上传到 /www/wwwroot/DSH-MOM/gateway
cd /www/wwwroot/DSH-MOM/gateway
python3 -m venv .venv
.venv/bin/pip install -e .
install -d -m 700 /etc/zr-gateway /var/lib/zr-gateway
printf '%s' 'sk-真实上游Key' > /etc/zr-gateway/upstream.key
chmod 600 /etc/zr-gateway/upstream.key
# 目录表：provider 的 keyFile 指向上面的文件；管理员令牌写进 gateway.env
install -m 600 /dev/null /etc/zr-gateway/catalog.json
cat > /etc/zr-gateway/gateway.env <<'EOF'
ZR_GATEWAY_CATALOG=/etc/zr-gateway/catalog.json
ZR_GATEWAY_ADMIN_TOKEN=请换成至少16位的随机串
EOF
chmod 600 /etc/zr-gateway/gateway.env
# 按上一节的格式把 catalog.json 填完整，校验通过再启动：
.venv/bin/python -c 'from zr_gateway.config import load_settings; load_settings()'
```

systemd 单元见 [deploy/systemd/zr-gateway.service](../deploy/systemd/zr-gateway.service)。把 `deploy/systemd/zr-gateway.service` 上传到 `/www/wwwroot/DSH-MOM/zr-gateway.service`，然后安装：

```bash
cp /www/wwwroot/DSH-MOM/zr-gateway.service /etc/systemd/system/zr-gateway.service
systemctl daemon-reload
systemctl enable --now zr-gateway
systemctl status zr-gateway --no-pager
curl -s http://127.0.0.1:8787/healthz
```

单元以 MES 的 venv 兜底：优先用 `/www/wwwroot/DSH-MOM/gateway/.venv`，没有则退回 MES 的 `/www/wwwroot/zr-aicoding/backend/.venv`，再退回系统 `python3`；启动失败只影响网关，不会拖住 `zr-aicoding-api`。

## 宝塔：域名 + 免费证书

1. **DNS**：给网关准备一个子域名（如 `ai.example.com`），A 记录指向 `175.178.238.31`。
2. **宝塔 → 网站 → 添加站点**：填该域名，不建数据库、不选 PHP，根目录随意（不会用到）。
3. **站点设置 → SSL → Let's Encrypt**：申请免费证书，开启"强制 HTTPS"。
4. **配置文件**里加上反代（宝塔"反向代理"面板也能做，关键是关缓冲）：

```nginx
location / {
    proxy_pass http://127.0.0.1:8787;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 900s;
}
```

只反代这一个站点，不要动 MES 现有的 `:8090` 站点和 `config.yaml` 里已有的域名配置。

5. 打包桌面端时把 `https://ai.example.com` 写进 `DEFAULT_GATEWAY_BASE_URL`，或运行时设 `ZR_MODEL_GATEWAY_URL`。桌面端只接受 HTTPS 源站、不接受带路径/端口的 HTTP。

验证证书与转发：

```bash
curl -s https://ai.example.com/healthz
```

## 强制下线

会话表在网关自己的库，删行即失效：

```bash
cd /www/wwwroot/DSH-MOM/gateway
ZR_GATEWAY_DB=/var/lib/zr-gateway/gateway.sqlite3 .venv/bin/python -m zr_gateway.admin revoke 用户名
```

MES 里改密码或停用账号**不会**自动踢掉已签发的网关令牌，最长要等 7 天过期；需要立刻生效就执行上面的命令。

## 联调

```bash
curl -s https://ai.example.com/api/login \
  -H 'content-type: application/json' \
  -d '{"enterprise":"jiangxi","username":"admin","password":"***"}'

curl -N https://ai.example.com/v1/chat/completions \
  -H "authorization: Bearer <token>" \
  -H 'content-type: application/json' \
  -d '{"model":"deep","stream":true,"messages":[{"role":"user","content":"统计本月订单量"}]}'

curl -s https://ai.example.com/v1/catalog -H "authorization: Bearer <token>"
curl -s https://ai.example.com/v1/usage/models -H "authorization: Bearer <token>"
curl -s https://ai.example.com/v1/admin/usage/models -H "authorization: Bearer <管理员令牌>"
```

`model` 只能填别名；网关按目录表换成真实模型名，并用该别名绑定的供应商 Key 转发。响应是原样的 OpenAI SSE，`reasoning_content`、`tool_calls` 分片、`finish_reason`、末尾 `usage` 都不重组。

本地起个不花钱的上游调试：

```bash
export ZR_GATEWAY_UPSTREAM_BASE_URL=http://127.0.0.1:9999
export ZR_GATEWAY_UPSTREAM_KEY=sk-fake
export ZR_GATEWAY_MES_BASE_URL=http://127.0.0.1:8009   # 需要有 MES 在跑
```

跑测试（不依赖 MES 与上游，全部用假实现）：

```bash
cd gateway
.venv/bin/python -m pytest -q
```

## 接口

| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| `POST` | `/api/login` | 无 | 账号密码交给 MES 校验，返回 `token` / `expiresAt` / `user` / `models`（含遮罩 Key） |
| `POST` | `/v1/chat/completions` | `Authorization: Bearer <token>` | OpenAI 兼容，流式或非流式 |
| `GET` | `/v1/models` | 同上 | 返回可用别名 |
| `GET` | `/v1/catalog` | 同上 | 供应商、别名、用途与 `keyHint`，供模型选择与用量页展示 |
| `GET` | `/v1/usage/models` | 同上 | 只统计调用者本人：按供应商 / Key / 模型聚合次数与 token |
| `GET` | `/v1/admin/usage/models` | `Authorization: Bearer <ZR_GATEWAY_ADMIN_TOKEN>` | 全公司聚合，可用 `username` / `enterprise` 过滤；未设管理员令牌时 404 |
| `GET` | `/healthz` | 无 | 存活检查 |

用量接口接受 `start` / `end`（Unix 秒，左闭右开），默认最近 30 天；`start >= end` 返回 400 `invalid_window`。

错误体是 OpenAI 结构 `{"error":{"message","type","code"}}`，并带 `x-request-id`；上游原文与 Key 只进服务端日志，不回给客户端。

| 状态码 | 场景 |
| --- | --- |
| 400 | 请求体不是 JSON / 账号密码为空 / 企业编码非法 / 统计窗口非法 |
| 401 | 账号密码错误、未登录、令牌过期或被撤销、管理员令牌错误 |
| 403 | 模型别名不在授权范围 |
| 429 | 上游限流 |
| 502 | MES 登录服务不可用、上游不可达、上游鉴权失败或连续两次 5xx |

## 数据与运维

SQLite 两张表：

- `sessions`：令牌的 SHA-256 摘要、用户名、企业编码、过期时间；明文令牌只在登录响应里出现一次，撤销即删行
- `usage_records`：每个请求的 `request_id`、用户名、别名、真实模型、供应商 id、遮罩 Key、用途、token 数、状态（`ok` / `aborted` / `upstream_error`）、耗时。旧库启动时自动补 `provider_id` / `key_hint` / `purpose` 三列，历史行保持空值

备份直接复制 `gateway.sqlite3*`（WAL 模式，连 `-wal`/`-shm` 一起复制，或先 `sqlite3 gateway.sqlite3 ".backup snapshot.sqlite3"`）。

日志：`journalctl -u zr-gateway -f`。`request_id` 同时出现在响应头、网关日志和 MES 登录审计里，方便对账。

## 尚未实现

- 配额强制与扣费：`usage_records` 已记录 token 数，但没有余额扣减和拦截
- 令牌续期：长任务超过 7 天会中断，目前只能重新登录
- 灰度与故障转移：目录表支持多供应商，但没有按权重分流或自动切换
- 按套餐下发模型清单：登录响应已带 `models[]`，但还没有按用户/企业裁剪
