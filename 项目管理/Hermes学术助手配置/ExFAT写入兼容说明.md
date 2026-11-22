# ExFAT写入兼容说明

更新：2026-11-16。用户在获知新建过程不具有完整文件原子可见性后，授权适配写入工具。适用当前academic档案的`bin/mac-paper`，不改磁盘格式、唯一主库或其他档案。

## 已实现

`write`和`upload`新增`--create-mode recoverable`。默认仍为`atomic`，不自动降级。兼容模式只改变新文件创建；覆盖既有文件仍要求最新SHA、保存原件备份、替换及回读。

```sh
mac-paper upload /absolute/candidate.md '研究成果/现有成果包/候选.md' --expect-missing --create-mode recoverable
mac-paper read '研究成果/现有成果包/候选.md'
mac-paper recoveries '研究成果/现有成果包/候选.md'
```

以上路径为示例，不是要求创建的新目录。使用实际任务路径；父目录须先存在。写入前后不要同时在其他编辑器保存同一目标。

新文件写入顺序：

1. 保留原路径校验和逐目标锁，核对目标不存在。
2. 在`.hermes-academic-backups/recovery/<目标路径哈希>/<操作ID>/`保存完整`payload.bin`并核验；写入`record.json`后才创建目标。
3. 以`O_CREAT | O_EXCL`独占创建目标，拒绝同名目标；循环处理短写入，fsync后回读完整字节。
4. 更新恢复记录为`verified`并返回`publication_mode: recoverable-exclusive-create`、`complete_file_atomic_visibility: false`。

恢复记录和完整待写副本不会自动清理，可能占用额外空间。已验证记录只证明当时读回成功，不说明该文件后来未被编辑。记录不得升级为研究验证。

## 中断与恢复

`recoveries RELATIVE_PATH`只查询该目标的记录，最多返回最近20条，并给出总数及截断标记；不重放、不删除、不自动修复。

- `prepared`：写前记录已落盘，目标可能不存在、部分写入或已经完整；进程终止可能使状态来不及更新。
- `interrupted`：工具捕获写入／回读异常；目标可能是部分内容。不能据此直接删除。
- `conflict`：独占创建时发现竞争者目标；工具不覆盖它。
- `verified`：当次完整回读一致。

恢复时先读当前目标。文本用`read`；二进制用`download`，检查内容与SHA。再根据返回的**精确**payload路径核对其SHA是否等于记录中的SHA。需要恢复时，将payload作为`upload`源：目标存在则带当前`--expected-sha256`，确实不存在才带`--expect-missing --create-mode recoverable`。恢复覆盖本身会备份当前目标。不要扫描无关备份或猜测旧哈希；不要盲目重新运行整批上传。

## 保留的限制

- 新文件可在写完前被其他程序看到；断电、拔盘或强制终止可能留下部分内容。恢复副本和日志不能等同于文件系统事务或物理断电保证。
- 桥接器锁不约束Obsidian及其他编辑器；既有文件覆盖仍是乐观SHA比较，不是与所有编辑器之间的操作系统CAS。
- 本次不自动修改所有调用方。当前ExFAT主库新建文件应显式带兼容参数；不带参数仍保留原来的硬链接原子发布要求。
- 全库旧路径检查问题独立存在，本次不声称`paper-maintain check`全库通过。

## 实际验收

- [回归测试脚本](工具验证/test_mac_paper_recoverable.py)：12项隔离测试通过，涵盖正常新建、二进制上传下载、同名拒绝、过期SHA、备份恢复、短写入、创建竞争、并发、路径约束、恢复目录软链接拒绝、空文件与默认模式不降级。
- 中断测试通过注入写入异常产生实际部分文件，再从保留payload经最新SHA覆盖恢复；不是拔盘或断电试验。
- [验证记录](工具验证/mac-paper-exfat验证.json)：绑定实际工具SHA，保留隔离测试与真实ExFAT交付的区别。
- 真实ExFAT操作：R1正文候选及支撑材料共7个交付目标完成上传和逐个下载回读；既有成果README覆盖前备份，正文、大纲、研究问题JSON、原证据记录和主题页五个受保护主源哈希未变。

测试运行：使用academic档案的`runtime/venv/bin/python`执行上述脚本。测试在academic scratch下建隔离根并清理，不向真实Paper写入探针。

## 工具回退

修改前的脚本在`/Users/wangyuelin/.hermes/profiles/academic/backups/mac-paper-exfat-20261116/mac-paper.before`，SHA-256为`38e2c11f475b052f4ec3e5296fbd3b6ae79de3d542f18498d79ea6596bb42926`。回退前检查是否有后续修改；回退会恢复原子新建模式在当前ExFAT卷上的限制，不会撤销已经写入的R1文件或清理恢复记录。
