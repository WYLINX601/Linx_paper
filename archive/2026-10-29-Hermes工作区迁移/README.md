---
wiki_id: hermes-workspace-archive-20261029
type: archive
status: archived
created: '2026-10-29'
updated: '2026-10-29'
summary: 切换Paper工作目录前的Hermes旧工作区完整快照。
---

# Hermes 旧工作区完整快照

`旧工作区完整快照.tar.gz` 保存原 `~/.hermes/profiles/academic/workspace/` 的所有内容，归档顶层为 `workspace/`。共18,162个普通文件、20,067个条目；内部的旧方案、副本、快照与执行脚本仍为迁移当时状态，不替代Paper现行研究主源。

- 压缩包字节数：6,365,107,191。
- SHA-256：`2dfdeab36eae32e89c1f38db3a346b84fbc8de289c3c8f54849472fe8655014d`。
- 已逐文件核对内容哈希及符号链接目标，包括硬链接实际内容。
- 保留原目录，历史绝对路径继续可用；本次没有删除原件。
- 完整对话数据库快照在Paper隐藏备份目录，活动对话继续由Hermes原academic档案保存。

包含HERMES.md，以及academic-role-revision、d01-direct-20261029、d01-neo4j、d01-review、d01-unit-analysis、dynamic-research、structure-migration、task-goal-review、topic-artifact-links、wiki-design、wiki-migration等原目录，含依赖与历史图源。目录相互引用原样保存；旧绝对路径未批量改写，历史脚本须复核后再运行。

恢复时解压到独立空目录，不能将完整旧工作区覆盖到现行Paper。包较大，已排除Git普通提交；它仍是本机库内的实际文件。迁移与回退见[[项目管理/Hermes学术助手配置/工作区迁移记录.md]]。
