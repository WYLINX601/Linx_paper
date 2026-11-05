---
type: archive-entry
status: immutable-pre-extension-snapshot
created: 2026-10-31
---

# V01后续扩展前的恢复材料

本包保留V01-unified-2.0在D04—D06扩展前的主源、执行工具、三表三图及52节点／259关系逻辑快照；当前入口是[[研究成果/〔合成试例〕虚拟民居单体试验V01/README.md|统一V01]]。旧D01／D03最初合并的96／320基线仍在前次归档，本包不覆盖它。

- [模型原件](originals/model.json)和[全库逻辑快照](db/before/graph.json)保留旧身份、属性、关系及原生数值类型；[快照摘要](db/before/summary.json)保留指纹。
- [清单](manifest.json)给出逐文件SHA-256与原Paper来源。Markdown、HTML和原生图加.snapshot后缀，仅避免被当作现行维护页；字节未重写，恢复时按来源路径去除该后缀。
- 这不是数据库二进制备份，也未在活动库实演恢复。恢复须另获授权、检查当前版本、单独限定事务并完整核验；文件恢复继续使用最新SHA与保护写入。不能直接重跑原合并事务。
- 不含账户凭据或私人聊天；原始论文和真实资料未改动。
