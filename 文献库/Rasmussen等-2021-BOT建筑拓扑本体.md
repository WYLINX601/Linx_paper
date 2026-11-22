---
wiki_id: paper-jvmypxt2
title: 'BOT: The building topology ontology of the W3C linked building data group'
authors:
- Mads Holten Rasmussen
- Maxime Lefrançois
- Georg Ferdinand Schneider
- Pieter Pauwels
year: 2021
type: paper-reading
paper_id: zotero:JVMYPXT2
zotero_item: PNZ3865Z
zotero_attachment: 6XP3U4GG
doi: 10.3233/SW-200385
venue: Semantic Web 12(1):143–161
source_locations:
- /Users/wangyuelin/Zotero/storage/6XP3U4GG/Rasmussen et al - 2021 - BOT Building
  Topology Ontology.pdf
reading_status: 局部精读
read_scope: 身份据英文原版：Semantic Web 12 (2021), 143–161，DOI 10.3233/SW-200385。本轮定向核读PDF2、7—10、15—18；视觉核看PDF8图2。先前JVMYPXT2/NTIMIAZZ是翻译附件，不据其文件名定年份；本次依据既有PNZ3865Z/6XP3U4GG英文原版。两条目对应同篇报告，不计两篇。
topics:
- 知识建模
- 建筑遗产
contribution_primary: 框架模型型
contribution_secondary: []
classification_status: 定向阅读暂定
reference_value: 核心参考（本轮R4/R5限定命题）
card_schema: nature-paper-card-1.2.0-paper.1
analytical_lens: theory-framework
locator_mode: page-grounded
context_verification: paper-only
created: '2026-11-16'
updated: '2026-11-16'
research_context: 2026-11-16读取context/PROJECT_CONTEXT.md；R4/R5综述，不改变研究范围
support_artifacts: []
zotero_related_items:
- JVMYPXT2
source_sha256: b858353daf53c95102e45609d638f5e90039cabaa2bee7520f2b929d649b634d
---

# BOT: The building topology ontology of the W3C linked building data group

> 来源覆盖：局部正文，见01节
> 提取可靠性：正文文字与指定原页图像核对，未全图审查
> 定位模式：page-grounded；PDF页序按实际附件
> 主要分析视角：theory-framework
> 辅助分析视角：无
> 外部核验：paper-only
> 卡片完成度：Partial（局部精读，不代表全文审查）
## 01 文献信息与阅读范围

身份据英文原版：Semantic Web 12 (2021), 143–161，DOI 10.3233/SW-200385。本轮定向核读PDF2、7—10、15—18；视觉核看PDF8图2。先前JVMYPXT2/NTIMIAZZ是翻译附件，不据其文件名定年份；本次依据既有PNZ3865Z/6XP3U4GG英文原版。两条目对应同篇报告，不计两篇。

## 02 一句话概括

[Paper: PDF p. 7] BOT以轻量拓扑本体连接建筑区域、构件及界面，细分专业知识通过外部本体组合，而非纳入一个包罗所有信息的模型。

## 03 研究问题、对象与尺度

[Paper: PDF p. 7] 对象是建筑组成的拓扑关系及跨工具信息交换；能力问题覆盖区域组成、包含、邻接、构件、界面及几何链接。

## 04 研究背景与学术脉络

[Paper: PDF p. 7] 作者从关联建筑数据的互操作需求出发，以重用词汇和分模块表达回应单一复杂模型的局限。本次未重核完整历史综述。

## 05 核心难点与已有不足

[Paper: PDF p. 7] 核心难点是既保持模型轻量，又让区域、构件和专业信息可连接。不是试图自动解决全部建筑语义。

## 06 核心思路与学术贡献

[Paper: PDF p. 8, 图2] 本文v0.3.1以Zone、Element、Interface为三个主类，并规定类、关系与公理；主要贡献为框架模型型。

## 07 理论依据与研究路径

[Paper: PDF p. 7] 社区能力问题→概念与关系→专业词汇连接→导出与查询评估。能力问题在这里用于限定可回答范围。

## 08 核心分析环节、框架与判据

[Paper: PDF p. 9] containsZone、adjacentZone、intersectsZone分别表达包含、邻接、相交；[Paper: PDF p. 10] Interface用于描述具体接触关系并承载附加信息，几何编码格式不属于BOT自身范围。

## 09 关键定义、公式与符号

[Paper: PDF p. 10] containsZone与containsElement的属性链可支持跨层包含推理。此为形式公理，不等于由点云自动识别实体或关系。

## 10 材料、分析设计与主张—证据链

[Paper: PDF p. 15] 评估使用Duplex、RTC、AU三个BIM模型；[Paper: PDF p. 16] 比较导出体量并测试查询；[Paper: PDF p. 17, 表2] 查询性能与所用推理机制相关。本轮不复算表值。

## 11 主要成果的准确解释

[Paper: PDF p. 16] 导出较小的文件也只包含原模型信息子集；因此不能把大小差异解释为无损压缩性能。[Paper: PDF p. 17] 结果支持既定查询应用，不证明遗产保护效果。

## 12 作者明确承认的局限

[Paper: PDF p. 16] 导出插件尚未覆盖全部可导出的关系和属性，属性单位及几何过程信息亦有限制。[Paper: PDF p. 18] 更细拓扑和工具支持仍在未来工作中。

## 13 阅读者分析、反例与待核问题

[Analysis] 本次为局部精读，不评价全部对齐文件或各推理机制的正确性。英文原版与翻译附件分开，采用期刊2021年，不将在线/文件名2020年当另一研究。

## 14 可积累的知识

[Analysis] 可积累的是能力问题与表示承诺对应、轻量核心加专业模块、表达范围与查询能力共同验收的思路。

## 15 对本研究的潜在用途与迁移条件

[Analysis] 可用于R4的语义框架评述及R5的验证层次比较；研究背景为2026-11-16读取的项目context。不直接替代BOT双基准或修改案例JSON。

## 16 后续问题与候选研究设想

未请求研究设想，本次不展开。
