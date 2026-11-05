window.ARCH_STYLE_SCHEMA = {
  "schema_version": "0.1",
  "status": "candidate",
  "created": "2026-10-08",
  "purpose": "服务建筑风貌特征提取、类型与组合分析的组织框架；尚未通过实采验证。",
  "core_classes": [
    {
      "id": "object",
      "label": "对象实例",
      "includes": [
        "place",
        "building",
        "component"
      ],
      "description": "位置背景、建筑及其有编号的构件实例。"
    },
    {
      "id": "feature_definition",
      "label": "特征定义",
      "description": "字段含义、适用对象、取值方式、单位与规则版本。"
    },
    {
      "id": "record",
      "label": "特征与分类记录",
      "description": "特定对象的观察、量测、分类或解释，连同时间、方法、证据与复核。"
    },
    {
      "id": "type_definition",
      "label": "类型定义",
      "description": "明确尺度、判别规则与允许变体；整体建筑类型需另外制定。"
    },
    {
      "id": "source",
      "label": "证据来源",
      "description": "原始或派生影像、模型、点云、量测、调查与文献。"
    },
    {
      "id": "analysis",
      "label": "分析结果",
      "description": "跨实例的频次、参数分布、组合和差异，保留分析范围及依据。"
    }
  ],
  "relations": [
    {
      "id": "located_in",
      "label": "位于",
      "from": "building",
      "to": "place",
      "definition": "建筑与位置背景关联，不用于村域形态分析。"
    },
    {
      "id": "has_component",
      "label": "包含",
      "from": "building",
      "to": "component",
      "definition": "建筑与有独立编号的构件实例组成关系。"
    },
    {
      "id": "about",
      "label": "针对",
      "from": "record",
      "to": "building/component",
      "definition": "每条记录只有一个明确对象。"
    },
    {
      "id": "uses_feature",
      "label": "记录字段",
      "from": "record",
      "to": "feature_definition",
      "definition": "引用字段定义与版本。"
    },
    {
      "id": "assigns_type",
      "label": "判读为",
      "from": "classification_record",
      "to": "type_definition",
      "definition": "类型判断保留独立记录、判别依据及复核状态。"
    },
    {
      "id": "supported_by",
      "label": "依据",
      "from": "record",
      "to": "source",
      "definition": "来源落实到记录，并保存照片区域、模型部位或页码等定位。"
    },
    {
      "id": "aggregates",
      "label": "汇总",
      "from": "analysis",
      "to": "record",
      "definition": "分析结果保留有效记录、对象范围、缺失与反例。"
    },
    {
      "id": "spatial_relation",
      "label": "位置或组合关系",
      "from": "object",
      "to": "object",
      "definition": "通过关系记录保存具体对象、方法与证据；不得凭图的连线推断因果。"
    }
  ],
  "feature_definitions": [
    {
      "id": "roof_form",
      "label": "屋顶形式",
      "applicable_to": [
        "roof"
      ],
      "value_kind": "type",
      "unit": null,
      "definition": "依据主屋面数量、坡向与屋脊组织判读；观察不足时保留未知。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "roof_pitch",
      "label": "屋面坡度",
      "applicable_to": [
        "roof"
      ],
      "value_kind": "number",
      "unit": "°",
      "definition": "指定一个屋面的测量剖面，记录高差、水平投影、端点及几何质量。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "eaves_depth",
      "label": "出檐深度",
      "applicable_to": [
        "roof"
      ],
      "value_kind": "number",
      "unit": "m",
      "definition": "明确墙面基准与檐口投影端点，记录所用模型版本。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "gable_form",
      "label": "山墙形式",
      "applicable_to": [
        "gable"
      ],
      "value_kind": "type",
      "unit": null,
      "definition": "记录可见轮廓及其与屋顶的对应关系，不据外观推断隐蔽构造。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "storeys",
      "label": "可见层数",
      "applicable_to": [
        "building"
      ],
      "value_kind": "number",
      "unit": "层",
      "definition": "结合立面和现场证据计数，不由门窗排列推定内部层数。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "window_form",
      "label": "窗形式",
      "applicable_to": [
        "window"
      ],
      "value_kind": "type",
      "unit": null,
      "definition": "按轮廓、分格和开启构成判读；材料另设字段。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "window_width",
      "label": "窗宽",
      "applicable_to": [
        "window"
      ],
      "value_kind": "number",
      "unit": "m",
      "definition": "说明量取窗洞还是窗框外缘，并保存端点。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "window_height",
      "label": "窗高",
      "applicable_to": [
        "window"
      ],
      "value_kind": "number",
      "unit": "m",
      "definition": "与窗宽使用相同边界定义，保存端点。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "surface_material",
      "label": "可见表面材料",
      "applicable_to": [
        "roof",
        "gable",
        "wall",
        "door",
        "window"
      ],
      "value_kind": "text",
      "unit": null,
      "definition": "只描述观察到的表面；承重结构与历史原材需另有证据。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "surface_color",
      "label": "当前表面色彩",
      "applicable_to": [
        "roof",
        "gable",
        "wall",
        "door",
        "window",
        "decoration"
      ],
      "value_kind": "text",
      "unit": null,
      "definition": "注明拍摄、纹理处理与标定条件；首版不把显示色当历史原色。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "decoration",
      "label": "装饰形式",
      "applicable_to": [
        "gable",
        "door",
        "window",
        "decoration"
      ],
      "value_kind": "text",
      "unit": null,
      "definition": "记录具体部位、轮廓和组合，文化寓意另以解释记录保存。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "visible_construction",
      "label": "可见构造",
      "applicable_to": [
        "gable",
        "wall",
        "door",
        "window"
      ],
      "value_kind": "text",
      "unit": null,
      "definition": "记录可见连接与分段，未见部分不得外推。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "arrangement",
      "label": "构件排列与组合",
      "applicable_to": [
        "building",
        "gable",
        "wall"
      ],
      "value_kind": "text",
      "unit": null,
      "definition": "说明所对照的构件实例、方位与排列；组合规律须跨建筑分析。",
      "version": "candidate-0.1",
      "status": "candidate"
    }
  ],
  "type_definitions": [
    {
      "id": "TYPE_ROOF_DUAL",
      "label": "双坡屋顶",
      "scope": "roof",
      "criterion": "示例规则：两个主要坡面沿屋脊相接；附属屋面单独记录。须由多视角核验。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "TYPE_ROOF_HIP",
      "label": "四坡屋顶",
      "scope": "roof",
      "criterion": "示例规则：建筑四侧主要屋面共同围合；主屋面与附属坡面区分。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "TYPE_WINDOW_RECT",
      "label": "矩形窗",
      "scope": "window",
      "criterion": "示例规则：窗洞外轮廓为矩形；窗框材质与内部分格另行记录。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "TYPE_GABLE_LINEAR",
      "label": "直线轮廓山墙",
      "scope": "gable",
      "criterion": "示例规则：可见顶部轮廓由直线段构成；仅为演示分类名称，须按对象研究修订。",
      "version": "candidate-0.1",
      "status": "candidate"
    }
  ],
  "record_contract": {
    "required": [
      "id",
      "subject_id",
      "feature_id",
      "kind",
      "value",
      "unit",
      "observed_at",
      "method",
      "observation_status",
      "review_status",
      "evidence",
      "notes"
    ],
    "kinds": [
      "observation",
      "measurement",
      "classification",
      "interpretation",
      "relation"
    ],
    "observation_statuses": {
      "observed": "已观察",
      "confirmed_absent": "确认不存在",
      "not_observed": "未观察",
      "uncertain": "无法判断"
    },
    "review_statuses": {
      "pending": "待复核",
      "checked": "已复核",
      "disputed": "有分歧"
    },
    "value_rules": "分类取值为 {type_id: 类型编号}；数值为数字；文本为字符串；未知为null；缺失不可填0。",
    "evidence_rule": "已观察/已判断的记录至少一条来源及定位。文献、量测、观察与解释分别建记录。",
    "time_rule": "observed_at表示观察或调查时点；历史所指时期可另在historical_period保存，不能互相替代。",
    "ratio_rule": "比例类后续增加分子、分母、计算范围及量取依据后才纳入统计。",
    "record_version_rule": "修订不覆盖原始证据；可用supersedes_record_id和revision_reason标注替代关系。"
  },
  "quality_rules": [
    "建筑整体类型不能用单一屋顶或窗型替代。",
    "同栋多张照片不是多个独立建筑样本。",
    "争议或待复核值保留状态，不自动合并为已确认结果。",
    "演示数据和研究数据分开；演示不进入研究统计。",
    "分析结果只由明确范围的有效记录形成，保留缺失、分母和反例。",
    "未知和确认不存在分开；缺少照片或模型时不生成虚构证据。"
  ],
  "references": [
    {
      "label": "申程程：皖北乡村建筑风貌特征识别及优化策略",
      "pages": "31—33、65—67",
      "role": "要素拆解与构件变体",
      "note": "原PDF封面为2024年5月，文件名2025；正式书目须核准。"
    },
    {
      "label": "汤茗喆：基于数字信息模型的传统村落建筑风貌保护更新方法研究",
      "pages": "25—30、60—77",
      "role": "实例、类型、参数与组合",
      "note": "原PDF封面与答辩页为2021年12月；Zotero日期2024。"
    },
    {
      "label": "郭锐、齐文娟、陈勇：基于多源数据融合与知识图谱的历史建筑数字化保护方法研究",
      "pages": "18—19",
      "role": "多源资料关联",
      "note": "其设备配置、精度与效率结论不直接迁移。"
    }
  ]
};
window.ARCH_STYLE_DATA = {
  "meta": {
    "schema_version": "0.1",
    "title": "建筑风貌知识图谱基础框架",
    "mode": "demo",
    "description": "三个虚构建筑用于演示查看关系、记录、缺失和分歧；不是景宁样本或论文发现。",
    "created": "2026-10-08"
  },
  "places": [
    {
      "id": "DEMO_PLACE",
      "label": "示例村落（虚构）",
      "identity_status": "demo",
      "notes": "仅演示位置关联，不对应真实村落。"
    }
  ],
  "buildings": [
    {
      "id": "DEMO_BUILDING_A",
      "label": "示例民居甲",
      "place_id": "DEMO_PLACE",
      "identity_status": "demo",
      "notes": "虚构演示对象；未关联真实影像、三维模型或现场调查。"
    },
    {
      "id": "DEMO_BUILDING_B",
      "label": "示例民居乙",
      "place_id": "DEMO_PLACE",
      "identity_status": "demo",
      "notes": "虚构演示对象；未关联真实影像、三维模型或现场调查。"
    },
    {
      "id": "DEMO_BUILDING_C",
      "label": "示例民居丙",
      "place_id": "DEMO_PLACE",
      "identity_status": "demo",
      "notes": "虚构演示对象；未关联真实影像、三维模型或现场调查。"
    }
  ],
  "components": [
    {
      "id": "DEMO_ROOF_A",
      "label": "甲·屋顶",
      "kind": "roof",
      "building_id": "DEMO_BUILDING_A",
      "position": "演示位置，待实际记录",
      "identity_status": "demo",
      "notes": "演示构件实例；与真实对象编号无对应关系。"
    },
    {
      "id": "DEMO_GABLE_A",
      "label": "甲·山墙",
      "kind": "gable",
      "building_id": "DEMO_BUILDING_A",
      "position": "演示位置，待实际记录",
      "identity_status": "demo",
      "notes": "演示构件实例；与真实对象编号无对应关系。"
    },
    {
      "id": "DEMO_WINDOW_A",
      "label": "甲·窗01",
      "kind": "window",
      "building_id": "DEMO_BUILDING_A",
      "position": "演示位置，待实际记录",
      "identity_status": "demo",
      "notes": "演示构件实例；与真实对象编号无对应关系。"
    },
    {
      "id": "DEMO_ROOF_B",
      "label": "乙·屋顶",
      "kind": "roof",
      "building_id": "DEMO_BUILDING_B",
      "position": "演示位置，待实际记录",
      "identity_status": "demo",
      "notes": "演示构件实例；与真实对象编号无对应关系。"
    },
    {
      "id": "DEMO_GABLE_B",
      "label": "乙·山墙",
      "kind": "gable",
      "building_id": "DEMO_BUILDING_B",
      "position": "演示位置，待实际记录",
      "identity_status": "demo",
      "notes": "演示构件实例；与真实对象编号无对应关系。"
    },
    {
      "id": "DEMO_WINDOW_B",
      "label": "乙·窗01",
      "kind": "window",
      "building_id": "DEMO_BUILDING_B",
      "position": "演示位置，待实际记录",
      "identity_status": "demo",
      "notes": "演示构件实例；与真实对象编号无对应关系。"
    },
    {
      "id": "DEMO_ROOF_C",
      "label": "丙·屋顶",
      "kind": "roof",
      "building_id": "DEMO_BUILDING_C",
      "position": "演示位置，待实际记录",
      "identity_status": "demo",
      "notes": "演示构件实例；与真实对象编号无对应关系。"
    },
    {
      "id": "DEMO_GABLE_C",
      "label": "丙·山墙",
      "kind": "gable",
      "building_id": "DEMO_BUILDING_C",
      "position": "演示位置，待实际记录",
      "identity_status": "demo",
      "notes": "演示构件实例；与真实对象编号无对应关系。"
    },
    {
      "id": "DEMO_WINDOW_C",
      "label": "丙·窗01",
      "kind": "window",
      "building_id": "DEMO_BUILDING_C",
      "position": "演示位置，待实际记录",
      "identity_status": "demo",
      "notes": "演示构件实例；与真实对象编号无对应关系。"
    }
  ],
  "feature_definitions": [
    {
      "id": "roof_form",
      "label": "屋顶形式",
      "applicable_to": [
        "roof"
      ],
      "value_kind": "type",
      "unit": null,
      "definition": "依据主屋面数量、坡向与屋脊组织判读；观察不足时保留未知。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "roof_pitch",
      "label": "屋面坡度",
      "applicable_to": [
        "roof"
      ],
      "value_kind": "number",
      "unit": "°",
      "definition": "指定一个屋面的测量剖面，记录高差、水平投影、端点及几何质量。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "eaves_depth",
      "label": "出檐深度",
      "applicable_to": [
        "roof"
      ],
      "value_kind": "number",
      "unit": "m",
      "definition": "明确墙面基准与檐口投影端点，记录所用模型版本。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "gable_form",
      "label": "山墙形式",
      "applicable_to": [
        "gable"
      ],
      "value_kind": "type",
      "unit": null,
      "definition": "记录可见轮廓及其与屋顶的对应关系，不据外观推断隐蔽构造。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "storeys",
      "label": "可见层数",
      "applicable_to": [
        "building"
      ],
      "value_kind": "number",
      "unit": "层",
      "definition": "结合立面和现场证据计数，不由门窗排列推定内部层数。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "window_form",
      "label": "窗形式",
      "applicable_to": [
        "window"
      ],
      "value_kind": "type",
      "unit": null,
      "definition": "按轮廓、分格和开启构成判读；材料另设字段。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "window_width",
      "label": "窗宽",
      "applicable_to": [
        "window"
      ],
      "value_kind": "number",
      "unit": "m",
      "definition": "说明量取窗洞还是窗框外缘，并保存端点。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "window_height",
      "label": "窗高",
      "applicable_to": [
        "window"
      ],
      "value_kind": "number",
      "unit": "m",
      "definition": "与窗宽使用相同边界定义，保存端点。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "surface_material",
      "label": "可见表面材料",
      "applicable_to": [
        "roof",
        "gable",
        "wall",
        "door",
        "window"
      ],
      "value_kind": "text",
      "unit": null,
      "definition": "只描述观察到的表面；承重结构与历史原材需另有证据。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "surface_color",
      "label": "当前表面色彩",
      "applicable_to": [
        "roof",
        "gable",
        "wall",
        "door",
        "window",
        "decoration"
      ],
      "value_kind": "text",
      "unit": null,
      "definition": "注明拍摄、纹理处理与标定条件；首版不把显示色当历史原色。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "decoration",
      "label": "装饰形式",
      "applicable_to": [
        "gable",
        "door",
        "window",
        "decoration"
      ],
      "value_kind": "text",
      "unit": null,
      "definition": "记录具体部位、轮廓和组合，文化寓意另以解释记录保存。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "visible_construction",
      "label": "可见构造",
      "applicable_to": [
        "gable",
        "wall",
        "door",
        "window"
      ],
      "value_kind": "text",
      "unit": null,
      "definition": "记录可见连接与分段，未见部分不得外推。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "arrangement",
      "label": "构件排列与组合",
      "applicable_to": [
        "building",
        "gable",
        "wall"
      ],
      "value_kind": "text",
      "unit": null,
      "definition": "说明所对照的构件实例、方位与排列；组合规律须跨建筑分析。",
      "version": "candidate-0.1",
      "status": "candidate"
    }
  ],
  "type_definitions": [
    {
      "id": "TYPE_ROOF_DUAL",
      "label": "双坡屋顶",
      "scope": "roof",
      "criterion": "示例规则：两个主要坡面沿屋脊相接；附属屋面单独记录。须由多视角核验。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "TYPE_ROOF_HIP",
      "label": "四坡屋顶",
      "scope": "roof",
      "criterion": "示例规则：建筑四侧主要屋面共同围合；主屋面与附属坡面区分。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "TYPE_WINDOW_RECT",
      "label": "矩形窗",
      "scope": "window",
      "criterion": "示例规则：窗洞外轮廓为矩形；窗框材质与内部分格另行记录。",
      "version": "candidate-0.1",
      "status": "candidate"
    },
    {
      "id": "TYPE_GABLE_LINEAR",
      "label": "直线轮廓山墙",
      "scope": "gable",
      "criterion": "示例规则：可见顶部轮廓由直线段构成；仅为演示分类名称，须按对象研究修订。",
      "version": "candidate-0.1",
      "status": "candidate"
    }
  ],
  "sources": [
    {
      "id": "DEMO_SOURCE_A_IMAGE",
      "label": "甲·照片占位",
      "kind": "image",
      "uri": null,
      "version": null,
      "captured_at": null,
      "is_demo": true,
      "notes": "尚无真实文件；只演示证据定位字段。"
    },
    {
      "id": "DEMO_SOURCE_A_MODEL",
      "label": "甲·模型占位",
      "kind": "model",
      "uri": null,
      "version": null,
      "captured_at": null,
      "is_demo": true,
      "notes": "尚无真实文件；只演示证据定位字段。"
    },
    {
      "id": "DEMO_SOURCE_A_FIELD_NOTE",
      "label": "甲·调查记录占位",
      "kind": "field_note",
      "uri": null,
      "version": null,
      "captured_at": null,
      "is_demo": true,
      "notes": "尚无真实文件；只演示证据定位字段。"
    },
    {
      "id": "DEMO_SOURCE_B_IMAGE",
      "label": "乙·照片占位",
      "kind": "image",
      "uri": null,
      "version": null,
      "captured_at": null,
      "is_demo": true,
      "notes": "尚无真实文件；只演示证据定位字段。"
    },
    {
      "id": "DEMO_SOURCE_B_MODEL",
      "label": "乙·模型占位",
      "kind": "model",
      "uri": null,
      "version": null,
      "captured_at": null,
      "is_demo": true,
      "notes": "尚无真实文件；只演示证据定位字段。"
    },
    {
      "id": "DEMO_SOURCE_B_FIELD_NOTE",
      "label": "乙·调查记录占位",
      "kind": "field_note",
      "uri": null,
      "version": null,
      "captured_at": null,
      "is_demo": true,
      "notes": "尚无真实文件；只演示证据定位字段。"
    },
    {
      "id": "DEMO_SOURCE_C_IMAGE",
      "label": "丙·照片占位",
      "kind": "image",
      "uri": null,
      "version": null,
      "captured_at": null,
      "is_demo": true,
      "notes": "尚无真实文件；只演示证据定位字段。"
    },
    {
      "id": "DEMO_SOURCE_C_MODEL",
      "label": "丙·模型占位",
      "kind": "model",
      "uri": null,
      "version": null,
      "captured_at": null,
      "is_demo": true,
      "notes": "尚无真实文件；只演示证据定位字段。"
    },
    {
      "id": "DEMO_SOURCE_C_FIELD_NOTE",
      "label": "丙·调查记录占位",
      "kind": "field_note",
      "uri": null,
      "version": null,
      "captured_at": null,
      "is_demo": true,
      "notes": "尚无真实文件；只演示证据定位字段。"
    }
  ],
  "records": [
    {
      "id": "DEMO_RECORD_A_ROOF_TYPE",
      "subject_id": "DEMO_ROOF_A",
      "feature_id": "roof_form",
      "kind": "classification",
      "value": {
        "type_id": "TYPE_ROOF_DUAL"
      },
      "unit": null,
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例人工观察",
        "tool": null,
        "version": null
      },
      "observation_status": "observed",
      "review_status": "pending",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_A_IMAGE",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "仅为虚构演示；数值和分类不可引用为研究结果。"
    },
    {
      "id": "DEMO_RECORD_A_PITCH",
      "subject_id": "DEMO_ROOF_A",
      "feature_id": "roof_pitch",
      "kind": "measurement",
      "value": 26.5,
      "unit": "°",
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例模型量测",
        "tool": null,
        "version": null
      },
      "observation_status": "observed",
      "review_status": "pending",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_A_MODEL",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "仅为虚构演示；数值和分类不可引用为研究结果。"
    },
    {
      "id": "DEMO_RECORD_A_WINDOW_TYPE",
      "subject_id": "DEMO_WINDOW_A",
      "feature_id": "window_form",
      "kind": "classification",
      "value": {
        "type_id": "TYPE_WINDOW_RECT"
      },
      "unit": null,
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例人工观察",
        "tool": null,
        "version": null
      },
      "observation_status": "observed",
      "review_status": "pending",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_A_IMAGE",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "仅为虚构演示；数值和分类不可引用为研究结果。"
    },
    {
      "id": "DEMO_RECORD_A_WINDOW_WIDTH",
      "subject_id": "DEMO_WINDOW_A",
      "feature_id": "window_width",
      "kind": "measurement",
      "value": 1.2,
      "unit": "m",
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例模型量测",
        "tool": null,
        "version": null
      },
      "observation_status": "observed",
      "review_status": "pending",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_A_MODEL",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "仅为虚构演示；数值和分类不可引用为研究结果。"
    },
    {
      "id": "DEMO_RECORD_A_MATERIAL",
      "subject_id": "DEMO_WINDOW_A",
      "feature_id": "surface_material",
      "kind": "observation",
      "value": "木质表面",
      "unit": null,
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例人工观察",
        "tool": null,
        "version": null
      },
      "observation_status": "observed",
      "review_status": "pending",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_A_IMAGE",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "仅为虚构演示；数值和分类不可引用为研究结果。"
    },
    {
      "id": "DEMO_RECORD_A_GABLE",
      "subject_id": "DEMO_GABLE_A",
      "feature_id": "gable_form",
      "kind": "classification",
      "value": {
        "type_id": "TYPE_GABLE_LINEAR"
      },
      "unit": null,
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例人工观察",
        "tool": null,
        "version": null
      },
      "observation_status": "observed",
      "review_status": "pending",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_A_IMAGE",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "仅为虚构演示；数值和分类不可引用为研究结果。"
    },
    {
      "id": "DEMO_RECORD_B_ROOF_TYPE",
      "subject_id": "DEMO_ROOF_B",
      "feature_id": "roof_form",
      "kind": "classification",
      "value": {
        "type_id": "TYPE_ROOF_HIP"
      },
      "unit": null,
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例人工观察",
        "tool": null,
        "version": null
      },
      "observation_status": "observed",
      "review_status": "pending",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_B_IMAGE",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "仅为虚构演示；数值和分类不可引用为研究结果。"
    },
    {
      "id": "DEMO_RECORD_B_PITCH",
      "subject_id": "DEMO_ROOF_B",
      "feature_id": "roof_pitch",
      "kind": "measurement",
      "value": null,
      "unit": "°",
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例模型量测",
        "tool": null,
        "version": null
      },
      "observation_status": "not_observed",
      "review_status": "pending",
      "evidence": [],
      "notes": "演示缺失：假定屋面被遮挡，未获得可用几何；不填0。"
    },
    {
      "id": "DEMO_RECORD_B_WINDOW_TYPE",
      "subject_id": "DEMO_WINDOW_B",
      "feature_id": "window_form",
      "kind": "classification",
      "value": {
        "type_id": "TYPE_WINDOW_RECT"
      },
      "unit": null,
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例人工观察",
        "tool": null,
        "version": null
      },
      "observation_status": "observed",
      "review_status": "pending",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_B_IMAGE",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "仅为虚构演示；数值和分类不可引用为研究结果。"
    },
    {
      "id": "DEMO_RECORD_B_WINDOW_WIDTH",
      "subject_id": "DEMO_WINDOW_B",
      "feature_id": "window_width",
      "kind": "measurement",
      "value": 0.95,
      "unit": "m",
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例模型量测",
        "tool": null,
        "version": null
      },
      "observation_status": "observed",
      "review_status": "pending",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_B_MODEL",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "仅为虚构演示；数值和分类不可引用为研究结果。"
    },
    {
      "id": "DEMO_RECORD_B_MATERIAL",
      "subject_id": "DEMO_WINDOW_B",
      "feature_id": "surface_material",
      "kind": "observation",
      "value": "金属表面",
      "unit": null,
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例人工观察",
        "tool": null,
        "version": null
      },
      "observation_status": "observed",
      "review_status": "pending",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_B_IMAGE",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "仅为虚构演示；数值和分类不可引用为研究结果。"
    },
    {
      "id": "DEMO_RECORD_B_GABLE",
      "subject_id": "DEMO_GABLE_B",
      "feature_id": "gable_form",
      "kind": "classification",
      "value": null,
      "unit": null,
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例人工观察",
        "tool": null,
        "version": null
      },
      "observation_status": "uncertain",
      "review_status": "pending",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_B_IMAGE",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "演示不确定：可见轮廓不足，不能完成类型判断。"
    },
    {
      "id": "DEMO_RECORD_C_ROOF_TYPE_1",
      "subject_id": "DEMO_ROOF_C",
      "feature_id": "roof_form",
      "kind": "classification",
      "value": {
        "type_id": "TYPE_ROOF_DUAL"
      },
      "unit": null,
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例人工观察",
        "tool": null,
        "version": null
      },
      "observation_status": "observed",
      "review_status": "disputed",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_C_IMAGE",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "演示分歧记录之一，不能自动采用。"
    },
    {
      "id": "DEMO_RECORD_C_ROOF_TYPE_2",
      "subject_id": "DEMO_ROOF_C",
      "feature_id": "roof_form",
      "kind": "classification",
      "value": {
        "type_id": "TYPE_ROOF_HIP"
      },
      "unit": null,
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例人工观察",
        "tool": null,
        "version": null
      },
      "observation_status": "observed",
      "review_status": "disputed",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_C_FIELD_NOTE",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "演示分歧记录之二，与另一来源同时保留。"
    },
    {
      "id": "DEMO_RECORD_C_PITCH",
      "subject_id": "DEMO_ROOF_C",
      "feature_id": "roof_pitch",
      "kind": "measurement",
      "value": 28.0,
      "unit": "°",
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例模型量测",
        "tool": null,
        "version": null
      },
      "observation_status": "observed",
      "review_status": "pending",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_C_MODEL",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "仅为虚构演示；数值和分类不可引用为研究结果。"
    },
    {
      "id": "DEMO_RECORD_C_WINDOW_TYPE",
      "subject_id": "DEMO_WINDOW_C",
      "feature_id": "window_form",
      "kind": "classification",
      "value": {
        "type_id": "TYPE_WINDOW_RECT"
      },
      "unit": null,
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例人工观察",
        "tool": null,
        "version": null
      },
      "observation_status": "observed",
      "review_status": "pending",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_C_IMAGE",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "仅为虚构演示；数值和分类不可引用为研究结果。"
    },
    {
      "id": "DEMO_RECORD_C_WINDOW_WIDTH",
      "subject_id": "DEMO_WINDOW_C",
      "feature_id": "window_width",
      "kind": "measurement",
      "value": 1.15,
      "unit": "m",
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例模型量测",
        "tool": null,
        "version": null
      },
      "observation_status": "observed",
      "review_status": "pending",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_C_MODEL",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "仅为虚构演示；数值和分类不可引用为研究结果。"
    },
    {
      "id": "DEMO_RECORD_C_MATERIAL",
      "subject_id": "DEMO_WINDOW_C",
      "feature_id": "surface_material",
      "kind": "observation",
      "value": "木质表面",
      "unit": null,
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例人工观察",
        "tool": null,
        "version": null
      },
      "observation_status": "observed",
      "review_status": "pending",
      "evidence": [
        {
          "source_id": "DEMO_SOURCE_C_IMAGE",
          "locator": {
            "description": "演示定位占位：对应构件部位，尚无真实文件",
            "page": null,
            "figure": null,
            "region": null,
            "model_part": null
          }
        }
      ],
      "notes": "仅为虚构演示；数值和分类不可引用为研究结果。"
    },
    {
      "id": "DEMO_RECORD_C_GABLE",
      "subject_id": "DEMO_GABLE_C",
      "feature_id": "gable_form",
      "kind": "classification",
      "value": null,
      "unit": null,
      "observed_at": null,
      "historical_period": null,
      "method": {
        "label": "示例人工观察",
        "tool": null,
        "version": null
      },
      "observation_status": "not_observed",
      "review_status": "pending",
      "evidence": [],
      "notes": "演示未观察：缺少山墙影像。"
    }
  ],
  "relations": [],
  "analyses": []
};
