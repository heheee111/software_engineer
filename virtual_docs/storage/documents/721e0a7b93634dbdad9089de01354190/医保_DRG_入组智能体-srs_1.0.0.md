# 软件需求规格说明书（SRS）

**遵循 IEEE 830 标准**

| 项目 | 内容 |
|------|------|
| 文档版本 | 1.0 |
| 生成时间 | 2026-06-05 23:32:29 |
| 项目名称 | 医保 DRG 入组智能体 |
| 作者 | Administrator |

---

## 1. 引言

### 1.1 目的
本文档旨在完整描述医保 DRG 入组智能体系统的功能和非功能需求，作为后续设计、实现和测试的依据。该系统通过解析电子病历文本，基于 DRG 分组规则（教学样本）自动完成 MDC → ADRG → DRG 的入组推理，并支持大模型润色入组说明，为教学演示和 DRG 分组流程理解提供支撑。

### 1.2 范围
系统范围涵盖：电子病历字段解析、规则驱动的 DRG 分组引擎、可选的大模型（通义千问 / OpenAI 兼容）说明润色、Web 交互界面、以及配套的文档自动生成与测试用例生成功能。当前规则文件为教学样本，非国家医保局正式发布的全量分组方案。

### 1.3 定义、缩写词与术语
- **DRG**: Diagnosis Related Groups，疾病诊断相关分组
- **MDC**: Major Diagnostic Category，主要诊断大类
- **ADRG**: Adjacent Diagnosis Related Groups，核心疾病诊断相关组
- **MCC**: Major Complication or Comorbidity，严重合并症或并发症
- **CC**: Complication or Comorbidity，一般合并症或并发症
- **ICD-10**: 国际疾病分类第10版
- **EMR**: Electronic Medical Record，电子病历

### 1.4 参考文献
- 《按病组（DRG）付费分组方案（2.0版）》
- IEEE Std 830-1998, Recommended Practice for Software Requirements Specifications
- OpenAI API 文档 / 阿里云百炼 DashScope API 文档

### 1.5 文档概述
本文档第2章给出系统综合描述，第3章阐述分析模型，第4章详列功能需求，第5章说明非功能需求。

---

## 2. 综合描述

### 2.1 产品视角
本系统为独立运作的 Web 应用，由 Python FastAPI 后端 + 静态 HTML/CSS/JS 前端构成。后端通过 RESTful API 对外暴露服务，前端通过 AJAX 调用。可选依赖 OpenAI 兼容 API（阿里云百炼 DashScope 或 OpenAI）进行大模型增强。

### 2.2 产品功能
1. 电子病历解析：从中文病历文本中提取主要诊断、次要诊断、主要手术的 ICD 编码
2. DRG 规则入组：依据规则 JSON 进行 MDC → ADRG → DRG 分组推理
3. 大模型增强：调用 LLM 对入组推理结果进行自然语言润色说明
4. 文档生成：自动生成 SRS、概要设计、测试报告
5. 测试用例生成：基于规则文件自动生成测试场景

### 2.3 用户特征
目标用户为教学场景下的教师和学生，以及医保 DRG 分组方案的学习者。用户需具备基本的 ICD-10 编码知识和 DRG 分组概念。

### 2.4 约束条件
- 规则文件为教学样本，不可用于实际医保结算
- 大模型增强需要有效的 API Key（DashScope 或 OpenAI）
- 系统运行在 Python 3.10+ 环境

### 2.5 假设与依赖
- 输入病历文本遵循约定格式（「主要诊断：」「主要手术：」等字段标记）
- ICD 编码格式为字母开头（诊断）或数字开头（手术操作）
- 规则 JSON 结构与 sample_rules.json 保持一致

---

## 3. 分析模型

### 3.1 用例图描述
**UC-1**: 课件实例入组 —— 用户粘贴 slide6 病历，系统输出 BB11 DRG 分组
**UC-2**: 无 MCC 入组 —— 相同主诊断+手术，但无次要诊断 → BB15
**UC-3**: 大模型润色 —— 用户勾选「允许大模型」，系统调用 LLM 生成自然语言说明
**UC-4**: 文档生成 —— 用户在 Web 界面点击生成 SRS / 设计文档 / 测试报告
**UC-5**: 测试用例管理 —— 生成、执行、导出测试用例

### 3.2 数据流图
```
病历文本 → EMR 解析 (emr_parser) → GroupingInput
  → GroupingEngine.group() → GroupingResult
  → (可选) LLM 润色 → 最终说明文本
  → JSON 响应 → Web 前端渲染
```

### 3.3 状态转换图
DRG 入组状态流转：
INPUT_RECEIVED → PARSING → MDC_MATCHED → ADRG_MATCHED
  → CC_MCC_EVALUATED → DRG_FINALIZED → NARRATIVE_GENERATED
异常路径：PARSING_FAILED / MDC_UNKNOWN / ADRG_UNKNOWN → ERROR_RESPONSE

---

## 4. 功能需求

### FR-001: 电子病历解析
**优先级**: P0
**描述**: 系统应能从中文电子病历文本中解析出主要诊断编码、次要诊断编码列表和主要手术操作编码。
**输入**: 中文病历文本（含「主要诊断：」「次要诊断：」「主要手术：」等标记）
**输出**: ParsedEMR 数据结构

### FR-002: MDC 分组
**优先级**: P0
**描述**: 系统应基于主要诊断 ICD-10 编码，按规则文件中 mdc_rules 的 match_principal_icd 匹配 MDC 大类。
**输入**: 主要诊断 ICD 编码
**输出**: MDC 编码与名称

### FR-003: ADRG 分组
**优先级**: P0
**描述**: 在确定 MDC 后，根据主要手术编码（或内科路径）匹配 adrg_rules / adrg_medical_rules / adrg_medical_fallback。
**输入**: MDC 编码 + 主要诊断 + 主要手术
**输出**: ADRG 编码与名称

### FR-004: MCC/CC 判定
**优先级**: P1
**描述**: 遍历次要诊断列表，匹配 mcc_list 和 cc_list，同时应用主诊断排除表，判定 MCC/CC 命中情况。

### FR-005: DRG 细分
**优先级**: P1
**描述**: 结合 MCC/CC 命中情况，将 ADRG 细分为最终 DRG（如 BB11 / BB13 / BB15）。

### FR-006: 大模型润色（可选）
**优先级**: P2
**描述**: 当配置了 API Key 时，调用 LLM 对入组推理结果进行自然语言润色，生成更可读的说明文本。

### FR-012: SRS 文档自动生成
**优先级**: P2
**描述**: 系统应基于项目配置和运行数据，自动生成符合 IEEE 830 标准的软件需求规格说明书。

### FR-013: 设计文档自动生成
**优先级**: P2
**描述**: 系统应自动生成概要设计文档，包含架构设计、接口设计、数据库设计、类设计等内容。

### FR-014: 测试报告自动生成
**优先级**: P2
**描述**: 系统应基于测试用例执行结果，自动生成测试报告。

### FR-015: 文档模板管理
**优先级**: P3
**描述**: 系统应支持用户自定义或修改文档生成模板（JSON 格式存储，支持 CRUD）。

### FR-016: 文档预览与手动修订
**优先级**: P2
**描述**: 文档生成后，用户应能够预览内容并进行手动修订，修订完成后重新生成最终版本。

### FR-017: 测试用例自动生成
**优先级**: P2
**描述**: 系统应基于 DRG 入组规则文件，自动生成覆盖正常入组、边界情况和异常处理的测试用例集。

### FR-018: 测试用例分类
**优先级**: P2
**描述**: 系统应按功能模块和优先级对测试用例进行分类组织。

### FR-019: 测试用例执行
**优先级**: P2
**描述**: 系统应支持自动执行测试用例，并与预期结果进行比对。

### FR-020: 测试用例导出
**优先级**: P3
**描述**: 系统应支持将测试用例导出为 JSON 格式，便于外部测试工具集成。


---

## 5. 非功能需求

### 5.1 性能需求
- 单次 DRG 入组请求响应时间应在 2 秒以内（不含 LLM 调用）
- LLM 增强请求额外超时设置为 30 秒
- Web 界面应支持至少 10 个并发用户

### 5.2 安全性需求
- LLM API Key 通过环境变量注入，不硬编码在代码中
- 输入病历文本不持久化存储（会话级别处理）
- CORS 配置在演示环境允许所有来源

### 5.3 可用性需求
- Web 界面提供中文本地化
- 示例病历一键加载
- 错误信息清晰可读，包含具体原因和解决建议

### 5.4 可维护性需求
- 模块化设计：emr_parser / engine / agent 解耦
- 规则 JSON 独立于代码，支持热替换
- 完整单元测试覆盖核心入组路径

### 5.5 可移植性需求
- 纯 Python 实现，跨平台（Windows / Linux / macOS）
- 依赖通过在 requirements.txt 中声明
- 前端仅使用标准 HTML/CSS/JS，无框架依赖

---

## 附录

### A. 规则文件摘要
{
  "rules_version": "broad-heuristic-2.0-style",
  "rules_desc": "教学用广覆盖启发式规则：按 ICD-10 章/段推断 MDC，手术码前缀+兜底；非国家医保局正式发布稿，不用于实际结算",
  "mdc_count": 27,
  "adrg_count": 30,
  "mcc_count": 5,
  "cc_count": 5
}

### B. 项目模块清单
- drg_agent.agent (DRGAgent — 编排层)
- drg_agent.engine (GroupingEngine — 规则分组引擎)
- drg_agent.emr_parser (parse_emr_text — 病历解析)
- drg_agent.docgen (文档自动生成)
- drg_agent.testgen (测试用例生成)
- drg_web.app (FastAPI Web 服务)
- virtual_docs.server (虚拟文档存储)

