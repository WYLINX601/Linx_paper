# 第二次独立只读复核

结论：F01—F04均已关闭。本次范围内未发现新增阻断。

- status: approved_within_read_only_scope
- blocking: false
- 新增 findings: 空数组
- 只读冻结根：/Users/wangyuelin/.hermes/profiles/academic/cache/scratch/prototype-next-ozht7hck/review2-fixed
- 测试与交付根：/Users/wangyuelin/.hermes/profiles/academic/cache/scratch/prototype-next-ozht7hck/review2-output

## 完整性与基线

清单 27 项在测试前及测试后全部通过 SHA-256 校验；manifest 自身、文件清单及全部冻结文件字节前后一致，无新增未列文件。

主源 candidate/model.json SHA-256：
34d8c27da739f94eac856b7c975959de17558c1acbd00c6415e49261baa1387a

manifest.json SHA-256：
1c3addbe116537b9eb025ce4923a65b747cdf5f325c1482e300c48e3c7ce031c

重编译 payload 与冻结 payload 全值相同；重新分析与冻结 analysis 全值相同。当前源模型55对象，投影56节点（包括SOURCE）、285关系；非新增投影身份52，加B03/CG01/ST01/TP01四个新对象。Building对象只有3，不是56栋建筑。D06恰为T01—T05五项。

## 逐项关闭判断

### F01：关闭（原P1阻断）

独立重建五区域旧反例，砖恰覆盖I08洞口。扣洞后砖为零净面积，仅进入zeroNetSurfaceRegions诊断，不进入材料面积表、D04-T06组合或D06材料数。灰泥约30.96 m²、completeMaterialCount=1，归入single-material-complete-domain。编译后分析和保持rawModel不变的实际LPG分析均通过。

真正双材料正例：砖9.6 m²、灰泥21.36 m²，二者均为正净面积，材料数2，归入multiple-materials-complete-domain。洞口内零面积unknown及mixed均不扩大未知净域，unknownAreaM2=0，仍为known。另以正净面积unknown作对照：未知面积约30.96 m²，材料数不补值，联合有效单元数为0。

源码：tools/d04.py:387-426；tools/d06.py:63-71。

### F02：关闭（原P2）

删除实际C01.geometryJson立即报Missing actual geometry C01；实际radius改为1.0且保留旧边界缓存时报Boundary cache differs from source geometry，均不继续发布围合结果。

补充正例：保持SOURCE.rawModelJson不变，仅更新实际C01几何和对应实际边界缓存，分析可重算；C01贡献从约0.02 m变为0.88 m，围合实体边界长度约18.58 m，净实体比例0.6616809116809117。说明修复不是单纯拒绝所有改变，而确实使用实际geometry。

源码：tools/projection.py:13-24；tools/analyze.py:28-29、56-66。

### F03：关闭（原P2）

独立加入旧反例EXTRA同角色INTERFACE_OF边，projection与analyze均拒绝Unexpected readback relationship set；重复实际边拒绝Duplicate readback identity。额外、重复、缺失实际对象/关系及身份字段异常也均拒绝，不静默丢弃。

实际关系recordStatus/evidenceIds被重建到status/evidence，实际节点evidence亦被重建；删除实际关系元数据不会回填rawModel旧值。实际D04关系status或evidence变化会触发participant source boundary拒绝。

源码：tools/projection.py:7-37；tools/d04.py:258-269；tools/d06.py:42-47。

### F04：关闭（原P2）

逐对象真实解析JSON指针：B03=/nodes/51/geometry，CG01=/nodes/52/geometry，ST01=/nodes/53/geometry，TP01=/nodes/54/geometry；均落到自身geometry，geometrySourceVersion均为V01-unified-2.1。

四对象各做错指W03、过期版本、缺指针、缺版本，在编译与实际LPG分析两条路径分别执行，共32个预期拒绝场景，全部拒绝。另有4个正确指针/版本解析场景。编译缺字段有时先由Source covers nonexistent property拒绝，不错误宣称所有拒绝均来自同一分支。

源码：tools/projection.py:40-65；tools/compile_model.py:183-186。

## 其他相关回归

- 实际W10材料改变为灰泥/砖后，各6.4 m²，D06材料数2，rawModel保持不变，确认材料由LPG重算。
- 实际facadeRecords缺失、实际立面来源版本过期均拒绝。
- 核读run_graph.py写前与写后保护：冻结载荷等值、原生类型、身份/端点/命名空间、旧图快照比较、阶段防盲重试、提交前重编译、写后完整身份/属性/标签/端点/类型核验及分析顺序。
- 仅AST提取binding/native_type/verify_exact/preserve_original_geometry纯函数；执行正例及属性、等值异原生类型、额外/重复/缺失关系、额外节点、端点、类型、标签、C01几何变化等反例。未导入run_graph或mcp_client，未调用MCP或执行Cypher。
- 独立公式核对墙毛面积与洞口面积、街宽、实体边界比例及两点地表坡比；不受支持的同点路面高差仍为unknown。

## 测试计数语义

包内test_review_fixes.py：unittest报告11个测试方法，全部OK；其中一个方法含8个新对象来源subTest，不把subTest再加到方法数。

独立independent_review.py：85个命名场景，85通过、0失败。其中64个是预期拒绝场景。每场景可含多个断言；编译和LPG路径分开记场景。这不是断言数、数据库执行数或真实样本数；两套存在覆盖重叠，不相加宣称为96个独立无重复测试。哈希核验另记，不混入85场景。

## 证据文件

- findings.json：结构化结论、关闭证据、实际核查文件、全部独立场景ID及限制。
- independent_review.py / independent-results.json / independent-tests.log：独立复现代码与85场景结果。
- bundled-tests.log：原包11方法执行日志。
- hash-before.json / hash-after.json：27项及manifest自身的前后哈希证据。
- mutated-model.json：独立测试最后留存的变异输入，仅在输出根，不是主源或修订实现。

## 边界与限制

- 仅授权冻结根内资料及本轮输出；未访问Paper、数据库、配置、凭据、MCP、Zotero或网络。未修改冻结实现、技能或记忆。项目模块只从冻结tools导入；Python标准库及现有Shapely运行依赖不作为冻结外项目输入。Python均使用academic/runtime/venv/bin/python -B。
- 内存LPG记录来自冻结payload及明确变异，不是真实数据库快照；未运行run_graph.main、connected、snapshot或任何Cypher，未验证数据库实际写入、约束索引、事务并发、真实写前保护执行或恢复。
- run_graph写前保护仅作源码审阅及binding纯函数检查；写后verify_exact与几何保留函数仅AST提取后在内存运行。纯函数通过不等于数据库写前写后链实际验收。
- 本包没有前轮原始模型或previous-findings中所引originals文档。本轮按previous-findings重建已记录反例，不把旧报告断言当成新证据；无法独立重做旧模型身份/几何逐值保留比较或重新核对缺席的文献原件。
- 52旧投影身份加4新对象等于56（含SOURCE）由当前包结构验证；当前源模型有55个对象，其中Building为3。不是56栋建筑，也不声称本轮有可供独立比较的旧52身份原始快照。
- 未验收浏览器、三表三图或完整展示产物；未做真实民居、真实统计、民族/地域专属性、因果或方法优越性验证。固定原型不代表真实有效性。
- 不要求任意曲墙曲街泛化，不扩展D02内部构架、D07或D08；结论仅适用于本冻结包、已列反例与限定合成原型，不是形式证明或全部输入空间覆盖。
