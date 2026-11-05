# Mac 学术 Hermes 迁移独立审查

检查时间：2026-10-27。只读核对 live `~/.hermes/profiles/academic`、迁移快照及本地 Hermes 源码；仅在本临时目录保存审查结果。未修改受审文件，未调用模型、网络或外部服务。主会话和 runtime agent 仍在完成登录、桌面接入与 LibreOffice，因此这三项不作为本次审查的完成结论。

## 发现

### P2：迁移未覆盖历史会话引用的图像与长输出文件

- 位置：`/private/tmp/academic-mac-migration/snapshot.py:7` 的快照白名单复制 `image_cache`，却未包含实际使用的 `cache/images` 和 `cache/terminal-output`；`deploy.py:8-11` 也未导入这些目录。
- 现证据：live `state.db` 的 messages.id=154、157、158、231、260、261、262 含 9 个 `MEDIA:/home/linx/.hermes/profiles/academic/cache/images/img_*.png` 引用；messages.id=13、132、196 含两个长输出日志引用。迁移快照与 Mac 对应位置均无这些 11 个文件。日志内容在消息中明确被截断；id=196 的接续摘要仍指向长输出日志作为后续资料入口。
- 影响：保留 282 条消息的数据库并不等于保留其证据附件；旧图像和完整工具输出无法从 Mac 当前迁移包回读，旧研究任务接续需要重新取源或回 Linux 找文件。原 PDF/Zotero 主源是否仍在、Linux 缓存是否仍存在，本审查未联网验证，不能断言证据永久丢失。
- 建议：在宣布完整迁移前，从 Linux 只读盘点消息实际引用的缓存文件，迁移仍存在者并记录 SHA-256 与原路径到本地路径映射。对已被清理者逐项标记缺失及可重建来源。保留历史消息原文，另加迁移说明或附件映射；不要全局改写对话。无须复制浏览器登录态或整个 cache。
- 机器可查证据：`history-file-reference-check.json`。

### P2：已迁移工作脚本仍调用 Linux 绝对路径

- 位置：`/Users/wangyuelin/.hermes/profiles/academic/workspace/task-goal-review/extract_definition_contexts.py:22`。
- 代码仍执行 `/home/linx/.hermes/profiles/academic/bin/mac-run`，而目标 Mac 上的本地桥为 `/Users/wangyuelin/.hermes/profiles/academic/bin/mac-run`。脚本服务于当前工作副本中的两篇 PDF 定义提取；运行会在创建输出目录后因找不到旧桥而失败。
- 建议：将可执行程序通过当前 profile 的工具路径解析，或改为本机 `/usr/bin/osascript` 调用；不改 PDF 主源路径及证据归属。已有提取 JSON 与其他工作文件已在迁移清单内，本发现针对可重新执行能力。

## 已核实且未发现重大问题的部分

- **旧 system_prompt 接续**：5 个非空提示词仍保存 Linux 路径与旧 SOUL，这本身是保留历史快照。源码 `agent/conversation_loop.py:817-840,959-982` 会读取存储提示词并比较运行 cwd；目录漂移会走 `:898-923` 重建并持久化当前提示。以源码原函数进行隔离离线判断，5 个旧提示词的 cwd 均解析为 `/home/linx/.hermes/profiles/academic/workspace`，在配置的 Mac cwd 下均返回 `reuse=false`。第 6 个 Bot Chat 提示词为空，走新建路径。不存在仅因保留旧提示就必然继续使用旧系统指令的证据。测试记录：`prompt-resume-check.json`。这项离线判断不等于桌面真实续聊验收；桌面接入后仍应检查实际请求提示词和工具 cwd。
- **会话元数据**：6 个迁移会话的 sessions.cwd 原本全部为 NULL；model_config 未发现 Linux cwd，state_meta 未发现 Linux cwd/terminal 冻结策略。projects.db 的 projects、project_folders、discovered_repos 原本为空，目前也为空。因此 deploy 的 replace(cwd) 在这些行上实际无影响，但未发现遗漏的非空 Linux cwd。
- **文本与工作文件完整性**：源/目标 messages 均 282 行，system_prompts 均 5 行；已有 `history-integrity.json` 记录逐行相同。独立对 source-manifest 逐文件比对，没有发现 workspace、assets、memories 或 skill 资源内容缺失；有意适配文件有差异。缺失清单除缓存盲区外主要为 requirements 文本、运行锁和 Linux LO registry 资源；runtime agent 正在以正式 Mac LO 替代后者，不按附件丢失计。
- **配置边界**：live `config.yaml:9-12` 为 local backend + Mac workspace；Zotero 本地启动，Obsidian 127.0.0.1:27123；Neo4j 通过 `:83-99` 的显式 SSH 启动 Linux 服务。SOUL、academic-workspace、workspace/HERMES.md 和运行记忆都已明确 Mac 主源与 Neo4j 留 Linux。未发现整个 profile、工作区或 skills 指向旧 Linux 的符号链接。
- **Paper 写入桥**：`bin/mac-paper:59-79` 拒绝绝对路径、上跳和越界软链接；`:195-290` 保留 expected SHA-256、每文件锁、备份、原子发布和读回。`:238-242` 明确普通编辑器不参与锁，因此不是与 Obsidian 的完整 OS CAS，这一限制在 skill:26 已披露。未发现这次 local 适配删除原有冲突保护。
- **凭证与权限**：profile 根目录 0700，config、.env、state.db 均 0600；审查未读取或输出 .env 内容。未发现为本次迁移复制默认 profile 私人会话的证据。默认配置/登录是否最终独立由主会话验收；本审查没有运行可能刷新凭证或触发服务的命令。

## 追加：旧附件绝对路径的桌面解析

源码确认，仅把文件补到 Mac `cache` 仍不足以让旧消息内联图片原位打开：`apps/desktop/src/lib/media.ts:112-150` 把消息原绝对路径传给本地 IPC 或 `/api/fs/read-data-url`；`:311-320` 的 `filePathFromMediaPath` 只解码 file URL，不重定位前缀。`apps/desktop/electron/local-read-path.ts:1-29` 是 Windows/WSL 路径桥，Mac 不做 Linux 到 Mac 转换；`electron/main.ts:16379-16395` 接着按该路径读文件，缺失即返回 missing file。未发现可配置的迁移路径别名。

主会话已反馈正在补迁 `cache/images`、`cache/terminal-output`、`cache/scratch`，保留 Linux 备份，修复工作脚本并保留原文件；这些修复由主会话实施，本报告不代为宣称已验收。

建议保持历史消息数据库原文，通过独立旧路径→本地路径、SHA-256 的映射与附件索引提供可回读入口，并明确旧消息内联预览仍有路径限制。若验收目标要求原位预览，需要在媒体只读解析层引入精确映射并完成桌面真实点击测试；建立 `/home` 全局软链接会扩大兼容范围并让旧命令误以为仍处 Linux，不建议采用。仅放置一个 JSON 映射不会被当前 UI 自动采用。

## 验收边界

本次未做真实模型续聊、桌面渲染、Zotero/Obsidian/Neo4j 联网验收，也未验证 Linux 缓存存续。结论可支持修复上述两项明确遗漏；不支持把“静态与离线核对通过”宣称为全部功能验收通过。
