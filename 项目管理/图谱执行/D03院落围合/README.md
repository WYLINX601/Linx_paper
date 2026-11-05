# D03六项外部合成表达执行工具

维护主源为[[研究成果/〔合成试例〕D03院落围合图谱试例/案例模型.json]]；模型v1.1，范围固定为A—D与E外部例，不是通用同步器。当前数据库及页面状态见案例入口。

## 已实测职责

- `legacy_compile.py`保留A—D核心规则；`compile_model.py`扩展E并校验源／属性／几何，`analyze.py`对实际读回做六项分析。
- `run_graph.py`通过原SSH-backed MCP限定替换D03V01；`--mode preflight`核旧模型、EXPLAIN与拒绝测试；`--mode write`仅在预检模型、载荷、五模块摘要和旧库不变时写；`--mode verify`只读核验。它的预检基线是扩展前v1.0，不应拿它自动再迭代任意模型。
- 受信本地执行器从冻结源重编译新载荷及独立绑定；事务DELETE前核全量等值、原生类型、结构白名单及旧图，提交后逐项读回。这不是Cypher自行认证源文件，不防可任意写库的恶意管理员；没有跨Paper／数据库原子事务。
- `verify_current.py`下载当前正式模型、执行阶段及扩展前逻辑快照到academic scratch，然后执行只读复核。可直接通过profile Python运行，输出实际证据目录；不会重写Paper或数据库。
- `build_review.py --workspace WORKSPACE`从`db/D03-readback.json`、核验和分析记录生成离线HTML；要求`candidates/`下有精确模型和D03详细表、`tests/results.json`、`generated/queries.json`等已核材料，不接受未经数据库读回的伪快照。模板与构建器是派生工具，HTML不作维护主源。
- `preflight.py`只是新执行器参数转发入口，旧create-only程序已保存历史，不适用于v1.1。

## 当前只读核验

使用本机profile Python运行本目录`verify_current.py`。依赖的实际版本见`requirements-tested.txt`；本轮已安装Shapely和markdown-it-py，未改外部数据库插件。启动MCP时探测`gds.version()`会报告未安装GDS；本任务不使用GDS，核心Cypher与读回核验通过，不以此宣称GDS可用。

## 恢复与再次实施

本轮初始工作目录的冻结源、预检／写入阶段与读回摘要保存于案例包和[[archive/2026-10-30-D03六项外部范围扩展/README.md]]。再次替换必须是新授权下的新工作区、当前旧图、完整快照和更新的固定案例预检；不得复用本轮write命令盲重试。发生超时先对照执行阶段、模型摘要和实际数据库，只读确认，再决定恢复。逻辑快照不是二进制dump，也不代表恢复已演练。

本地参数测试与冻结静态审查在归档中保留，不将它们冒充任意院落或真实用途验证。内部构架、室内完整网络、时序与感知继续不纳入。
