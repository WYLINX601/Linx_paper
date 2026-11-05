# Hermes 学术助手使用说明

更新：2026-10-29。学术助手已迁到 Mac，桌面选择 **This device → 学术助手**。模型配置为 `openai-codex / gpt-6.1-sol`；历史会话保留原有单会话模型选择。Paper、Zotero 与 Obsidian 在本机访问，只有 Neo4j 仍连接 Linux。

## 本地入口

- 档案：`/Users/wangyuelin/.hermes/profiles/academic`。
- CLI：`/Users/wangyuelin/.local/bin/hermes -p academic`。
- 运行工作区：直接使用 `/Users/wangyuelin/Desktop/Obsidian/Paper`；19条既有会话已同步执行目录，原有消息保留。旧workspace完整归档并原位保留，见[工作区迁移记录](工作区迁移记录.md)。
- 启动时先运行档案 `bin/mac-paper status` 和 `bin/mac-paper context`，读取最新项目规则与入口。
- `mac-paper` 保留原CLI，用本地文件操作替代SSH；`mac-run -- COMMAND ARG...` 也在本机执行。`--target` 仅允许 `local` / `localhost`。
- Python：档案下 `runtime/venv/bin/python`；文档渲染：`bin/soffice`，使用本机正式 LibreOffice 与中文字体配置。

旧附件内联预览可能仍引用Linux绝对路径，使用[本地文件索引](历史会话本地文件索引.md)访问迁移后的原文件。

旧会话中的 `/home/linx/.hermes/profiles/academic` 路径只作历史记录，当前对应本机档案路径。原始消息没有批量替换；会话执行目录已迁移。正式成果直接写回Paper，不另建研究库副本。

## 文件与服务

`mac-paper read` 提供 SHA-256；覆盖必须使用刚读到的 `--expected-sha256`，新建使用 `--expect-missing`。写入前保存可恢复副本到 Paper 的 `.hermes-academic-backups/`，写完回读核对。冲突须重新读取合并。工具自身逐文件加锁，Obsidian等编辑器不参与此锁，因此仍需避免同时编辑。

Zotero MCP直接运行本机兼容启动文件，保留条目键、页码与PyMuPDF回退标识。Obsidian MCP直连 `http://127.0.0.1:27123/mcp/`；密钥仅放受限配置，Zotero/Obsidian须处于可用状态。

Neo4j经SSH连接 `linx-HP-EliteDesk-880-G6-Tower-PC` 并启动原MCP，数据库仍在Linux。Linux离线不影响本地Paper、Zotero和Obsidian；此时图谱查询不可用。MCP仍有写工具，数据库变更必须遵守项目授权与可恢复规则。本次迁移仅执行只读查询。

33项技能保留，只有 `academic-workspace` 自动加载全文；本轮没有精简技能。转录及部分外部服务仍需各自凭证，不因文件迁移而宣称已接通。保留最新多模型协作配置，但OpenRouter等能力是否可用取决于Mac已有凭证。

验收与尚未完成事项见[验收清单](验收清单.md)，恢复方式见[恢复说明](恢复说明.md)，技能迁移见[技能迁移清单](技能迁移清单.md)。旧部署说明保存在[Linux历史记录](历史配置/2026-10-26-Linux/README.md)，其中路径与服务状态不是当前使用入口。

## Excalidraw 原生 CLI（2026-11-02）

已安装完整的 `obsidian-excalidraw-cli` 配套技能与辅助脚本，当前学术档案可加载；Paper 库原生连接、创建、读回和 PNG 导出已经实测。详见[Excalidraw CLI 使用说明](ExcalidrawCLI使用说明.md)，其中保留版本、来源提交、命令、验收路径及未验证范围。本次不改变既有研究图，也不新增额外 MCP 或 API 密钥。
