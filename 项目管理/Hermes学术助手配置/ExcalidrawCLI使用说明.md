# Obsidian Excalidraw CLI 使用说明

配置与实测日期：2026-11-02。适用本机 Paper 库；这是工具配置记录，不是研究结论或图谱成果。

## 当前可用入口

本机原生 CLI `/usr/local/bin/obsidian` 已可连接运行中的 Paper 库。实测 Obsidian 1.12.7、Excalidraw 2.29.1、Node.js v22.23.1；插件原生状态返回 `ready: true`、`nativeCLI: true`、`converter: true`。

用户指定的仓库提供技能、文档与无依赖 Node 辅助脚本，不是另一个全局 npm 绘图程序。本次未安装独立 Excalidraw+ CLI，未引入 API 密钥、端口转发或额外 MCP。

- 上游：<https://github.com/zsviczian/obsidian-excalidraw-cli>
- 安装来源提交：`41306ec5369a11c8cae877ba71c9baa461b6ead6`。
- 完整工具包：`/Users/wangyuelin/.hermes/profiles/academic/skills/obsidian-excalidraw-cli`。
- Hermes 当前学术档案已能通过 `skill_view` 加载技能 `obsidian-excalidraw-cli`；不是全局自动加载或模型设置修改。
- Paper 独立私有请求／回执目录：`/Users/wangyuelin/.hermes/profiles/academic/state/obsidian-excalidraw-cli/Paper`。记录可能包含图中文字，不放入研究库或 Git。

## 直接在终端使用

保持 Obsidian 运行。`vault=Paper` 必须放在插件命令之前，不依赖当前打开的库或画布。

```sh
# 检查连接
obsidian vault=Paper obsidian-excalidraw-plugin:status

# 查看命令及创建参数
obsidian vault=Paper obsidian-excalidraw-plugin:help
obsidian vault=Paper obsidian-excalidraw-plugin:schema action=create

# 只读列出图纸
obsidian vault=Paper obsidian-excalidraw-plugin:list limit=50

# 读回本次测试图（不修改、不打开）
obsidian vault=Paper obsidian-excalidraw-plugin:read path="项目管理/工具验收/ExcalidrawCLI/CLI连通性验收.excalidraw.md" source=disk detail=elements

# 完整只读诊断
node /Users/wangyuelin/.hermes/profiles/academic/skills/obsidian-excalidraw-cli/scripts/doctor.mjs --vault Paper
```

如果新终端找不到 `obsidian`，用 `/usr/local/bin/obsidian` 替代；本次未修改 shell 启动文件。

## 交给学术助手

可以直接提出“用 Obsidian Excalidraw 在 Paper 中画一张……，保留原生可编辑图并导出 PNG”。助手先加载技能，检查运行状态和实际 schema，再确认图源与输出路径。正式研究图按根 AGENTS.md 归位，不默认放在本次工具验收目录。

创建图用原生 `create`，它不覆盖既有图。只读检查用 `read source=disk`，并跟随分页直到完成。原生编辑需要 live read、实际元素 ID、明确 view、最新 expectedRevision 与唯一 requestId；对既有 Paper 图的变更仍须遵守本库备份、最新 SHA 与保护写回规则，不因安装 CLI 而绕过。不得手工修改压缩的 Excalidraw Markdown。

大请求使用库内可见 JSON 文件并通过 `input=` 传入；文件创建和覆盖走 `mac-paper`。执行前读相应 schema。写入后检查 `ok`、`mutation`、`persistence`，不能只看进程退出码。超时先用原 requestId 查 `result` 并读回，不直接重复写入。不要默认运行 `script trusted=true`。

## 本次实际验收

- 安装后逐文件 SHA-256 对比：33 个上游文件一致；另有本地技能接续说明，和上游内容区分维护。
- `npm run check`：语法检查及 25 项离线测试通过；离线测试不冒充真实桌面结果。
- 真实 Paper 原生创建：`ok=true`、`mutation=applied`、`persistence=saved`。
- 完整磁盘读回：2 个矩形、2 个绑定文字、1 条箭头；共 5 个原生元素，箭头两端绑定正确。
- 原生导出：与磁盘读回相同 revision，PNG 为 480×100，12,281 字节；已核对文件签名和字节数。
- PNG 已实际视觉检查：Start／Finish 清楚，矩形与箭头完整，无明显遮挡、重叠或裁切。
- live read 返回独立 view、`dirty=false`，同样包含 5 个原生元素；没有执行 apply 编辑既有图。
- GUI 截图未显示本次测试图，而是已有画布，因此不宣称已完成测试图的桌面可见性验收或手工拖动测试；原生保存、live read 与 PNG 检查分别成立。

[原生可编辑验收图](../工具验收/ExcalidrawCLI/CLI连通性验收.excalidraw.md) · [PNG预览](../工具验收/ExcalidrawCLI/CLI连通性验收.png) · [结构化验收记录](../工具验收/ExcalidrawCLI/验收记录.json)

本次仅新增工具验收材料及配置说明，不改正文、研究路线、案例 JSON 或 Neo4j。高级脚本、SVG 转原生、复杂图库、中文字体及既有图的修改未包含在本次验收中，使用时另行实测。
