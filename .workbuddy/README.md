# WorkBuddy 自动化部署（本工程）

部署规则写在本目录，**不要**去 WorkBuddy 配置中心填主机/路径/私钥。

聊天里选中本工作区后，引擎只读这里的规则。

## 文件

| 文件 | 是否提交 | 内容 |
|------|----------|------|
| `deploy.yaml` | ✅ 可提交 | 主机、远端目录、入口 URL、重启命令、构建策略等 |
| `deploy.local.yaml` | ❌ 勿提交（已 gitignore） | 本机 SSH 私钥路径 `ssh.key_path` |

有 `deploy.yaml`（及本机 `deploy.local.yaml` 私钥）即视为本工程可部署。

## deploy.local.yaml 示例

```yaml
version: 1
ssh:
  key_path: "C:/Users/你/.ssh/id_ed25519"
```

私钥须位于用户 HOME 下（如 `~/.ssh/`）。**禁止**把 `key_path` 写进可提交的 `deploy.yaml`。

## 怎么用

1. 编辑本目录 `deploy.yaml`（团队共享的远端与构建约定）。
2. 本机复制/新建 `deploy.local.yaml`，填自己的私钥路径。
3. 打开 WorkBuddy，工作区选本工程，说「部署到预发」并确认。
