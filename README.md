# 医保 DRG 入组智能体系统

## 项目概述

本项目实现了一个**教学演示用途**的医保 DRG（Diagnosis Related Groups，疾病诊断相关分组）智能入组系统。系统接收中文电子病历（EMR）文本，自动提取 ICD-10 诊断编码和手术操作编码，通过规则引擎完成 MDC（主要诊断大类）→ ADRG（核心疾病诊断相关分组）→ DRG 的完整分组链路，并可选择接入大语言模型（LLM）生成自然语言的分组推理说明。

此外，系统还集成了**软件文档自动生成**、**测试用例自动生成与执行**、**虚拟文档版本库**以及 **Web 可视化界面**。

> ⚠️ **教学用途声明**：样本规则文件仅供教学演示，覆盖范围有限，**不可用于实际医保结算**。实际 DRG 分组应以国家医保局正式发布的 CHS-DRG 分组方案为准。

## 核心机制：DRG 分组四阶段规则链

DRG 分组采用确定性顺序规则匹配算法，分四个阶段推进：

```
电子病历文本 → 编码提取 → MDC 分组 → ADRG 分组 → MCC/CC 判定 → DRG 精细分组 → 结果
```

### 第一阶段：ICD 编码提取（`emr_parser.py`）

从自由文本 EMR 中按行定位并提取结构化编码：

- 匹配以「主要诊断」「次要诊断」「主要手术」为行首的文本块
- 使用正则表达式提取 ICD-10 编码（模式：`[A-TV-Z][0-9]{2}(?:\.[0-9A-Z*+]+)?`）和手术编码（模式：`[0-9]{2}\.[0-9A-Za-z*+]+`）
- 输出结构化的 `ParsedEMR` 对象，包含主诊断、次诊断列表、主手术编码

### 第二阶段：MDC 分组（主要诊断大类）

引擎按 `mdc_rules[]` 列表顺序逐条匹配：

- 每条规则包含一组 `match_principal_icd` 正则模式，匹配主诊断编码
- **首次匹配即生效**，返回对应的 MDC 编码与名称（如 MDCB 神经系统疾病）
- 末尾设有兜底规则（`^.*` → MDCR），确保无输入被遗漏

### 第三阶段：ADRG 分组（核心疾病诊断相关分组）

在已确定的 MDC 范围内进行两路分流：

- **手术路径**（存在手术编码）：先匹配该 MDC 下的特定手术 ADRG 规则（如 BB1 神经系统复杂手术），若无匹配则落入该 MDC 的**手术兜底 ADRG**（如 BS9）
- **内科路径**（无手术编码）：先匹配内科 ADRG 规则，再落入**内科兜底 ADRG**（如 BM0）

每条 ADRG 规则通过 `supports_complication_layer` 字段标识是否参与后续 MCC/CC 分层。

### 第四阶段：MCC/CC 判定与 DRG 精细分组

- 遍历次要诊断列表，分别与 `mcc_list[]`（严重合并症/并发症，如 J96 呼吸衰竭）和 `cc_list[]`（一般合并症/并发症，如 I10 高血压病）进行正则匹配
- 通过 `mcc_exclusions_by_principal[]` 实现主诊断级联排除——若主诊断命中特定排除规则，对应的次要诊断将不被计入 MCC
- 根据 ADRG 查 `drg_fine_map{}` 获取三级 DRG 映射（伴 MCC / 伴 CC / 无 MCC 无 CC），选择对应层级
- 若 ADRG 无精细映射，则按统一规则追加后缀：`1`（伴 MCC）、`3`（伴 CC）、`5`（无伴）

### 示例：A01.002+G01* 伤寒性脑膜炎

```
输入：
  主要诊断：A01.002+G01*（伤寒性脑膜炎）
  次要诊断：J96.0（急性呼吸衰竭）
  主要手术：38.1000x002（动脉内膜剥脱术）

分组链路：
  A01.002+G01* → 匹配 mdc-b-neuro → MDCB 神经系统疾病
  38.1000x002 → 匹配 adrg-bb1  → BB1 神经系统复杂手术
  J96.0      → 命中 MCC 列表   → 合并 MCC
  BB1 + MCC  → 查精细映射表    → BB11
```

## 系统架构

```
                    CLI (cli.py)
                       │
        ┌──────────────┼──────────────┐
        │              │              │
  Web 前端           FastAPI       虚拟文档服务
  (index.html)    (drg_web/app.py)  (virtual_docs/server.py)
        │              │              │
     AJAX 调用      DRGAgent           │
        │              │              │
        └──────→  DRGAgent ←──────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   emr_parser     engine.py     OpenAI SDK
   (文本解析)     (规则匹配)     (LLM增强)
        │             │
        │    sample_rules.json
        │
   docgen.py   testgen.py   virtual_docs.py
   (文档生成)  (测试生成)    (文档版本库)
```

## 模块说明

### 核心模块

| 模块 | 路径 | 职责 |
|------|------|------|
| 编码解析器 | `drg_agent/emr_parser.py` | 从 EMR 文本提取 ICD-10 及手术编码 |
| 分组引擎 | `drg_agent/engine.py` | 加载规则 JSON，执行四阶段分组 |
| 智能体 | `drg_agent/agent.py` | 编排解析→分组→LLM增强主流程 |
| 命令行入口 | `drg_agent/cli.py` | argparse 包装，支持文件/stdin 输入 |
| 规则文件 | `drg_agent/rules/sample_rules.json` | 教学用 MDC/ADRG/MCC/CC/DRG 规则 |

### 辅助模块

| 模块 | 路径 | 职责 |
|------|------|------|
| 文档生成器 | `drg_agent/docgen.py` | 基于模板生成 SRS/设计文档/测试报告，可选 LLM 增强 |
| 测试生成器 | `drg_agent/testgen.py` | 生成 14 组测试用例，执行回归验证 |
| 虚拟文档库 | `drg_agent/virtual_docs.py` | 文件型文档版本管理，支持语义化版本号 |

### 服务模块

| 模块 | 路径 | 职责 |
|------|------|------|
| Web API | `drg_web/app.py` | FastAPI 后端，暴露 20+ REST 接口 |
| Web 前端 | `drg_web/static/index.html` | 三页签 SPA：DRG 分组、文档生成、测试管理 |
| 虚拟文档服务 | `virtual_docs/server.py` | 独立 FastAPI 微服务，监听 8766 端口 |

## LLM 增强：环境变量自适应

LLM 为可选增强层，无 API Key 时自动降级为结构化文本输出。环境变量按以下优先级解析：

```
显式传入参数 > OPENAI_API_KEY > DASHSCOPE_API_KEY > DEEPSEEK_API_KEY
```

| 环境变量 | 说明 |
|----------|------|
| `DASHSCOPE_API_KEY` | 阿里云百炼 DashScope（默认 base_url 自动填充，模型 `qwen3-max`） |
| `OPENAI_API_KEY` + `OPENAI_BASE_URL` | 通用 OpenAI 兼容接口 |
| `DEEPSEEK_API_KEY` | DeepSeek API（base_url 自动填充，模型 `deepseek-chat`） |
| `OPENAI_MODEL` | 显式指定模型名称 |
| `DASHSCOPE_ENABLE_THINKING` | 开启 DashScope 深度思考模式 |

## 快速开始

### 环境要求

- Python 3.10+
- 依赖项：`openai>=1.40.0`、`fastapi`、`uvicorn`、`python-dotenv`（可选）

### 安装

```bash
pip install -r requirements.txt
```

### 命令行使用

```bash
# 从文件读取 EMR
python -m drg_agent.cli examples/case5_emr.txt

# 指定自定义规则文件
python -m drg_agent.cli examples/slide6_emr.txt --rules my_rules.json

# 从标准输入
echo "主要诊断：J15.0（肺炎）" | python -m drg_agent.cli
```

### Web 界面启动

```bash
# 启动 Web 服务（默认 127.0.0.1:8848）
python -m drg_web

# 独立启动虚拟文档服务
python virtual_docs/server.py
```

启动后访问 `http://127.0.0.1:8848`，可见三个功能页签：
1. **DRG 分组**：输入 EMR → 查看 MDC/ADRG/DRG 摘要卡片与完整推理叙述
2. **文档生成**：选择文档类型（SRS/设计/测试报告）→ 预览 → 编辑 → 提交虚拟文档库
3. **测试管理**：生成测试用例 → 筛选 → 执行 → 导出结果

## REST API 概览

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/group` | POST | 提交 EMR 文本，获取 DRG 分组结果 |
| `/api/example-emr` | GET | 加载示例 EMR |
| `/api/health` | GET | 健康检查 |
| `/api/docs/srs` | POST | 生成 SRS 需求规格说明书 |
| `/api/docs/design` | POST | 生成概要设计文档 |
| `/api/docs/test-report` | POST | 生成测试报告 |
| `/api/docs/templates[/{name}]` | GET/POST/DELETE | 文档模板管理 |
| `/api/docs/preview` | POST | 文档预览与行级修订 |
| `/api/docs/ai-generate` | POST | AI 自由文档生成 |
| `/api/virtual-docs[/{doc_id}]` | GET/POST/PUT | 虚拟文档增删查改 |
| `/api/tests/generate` | POST | 生成测试用例 |
| `/api/tests/execute` | POST | 执行测试套件 |
| `/api/tests/list` | GET | 列出测试用例 |
| `/api/tests/export` | GET | 导出测试结果为 JSON |

## 项目结构

```
software_engineer/
├── drg_agent/                    # 核心引擎包
│   ├── __init__.py
│   ├── agent.py                  # DRGAgent 编排层
│   ├── engine.py                 # 分组规则引擎
│   ├── emr_parser.py             # EMR 文本解析器
│   ├── cli.py                    # 命令行入口
│   ├── docgen.py                 # 文档自动生成
│   ├── testgen.py                # 测试用例生成与执行
│   ├── virtual_docs.py           # 虚拟文档版本库
│   ├── rules/
│   │   └── sample_rules.json     # 教学样本规则（MDC/ADRG/MCC/CC/DRG 映射）
│   └── templates/
│       ├── srs_default.json      # SRS 默认模板
│       ├── design_default.json   # 设计文档默认模板
│       └── test_report_default.json # 测试报告默认模板
├── drg_web/                      # Web 服务
│   ├── __init__.py
│   ├── __main__.py               # python -m drg_web 入口
│   ├── app.py                    # FastAPI 应用（20+ 端点）
│   └── static/
│       ├── index.html            # 三页签 SPA 前端
│       └── styles.css            # 样式
├── virtual_docs/                 # 独立虚拟文档服务
│   ├── server.py                 # FastAPI 微服务（端口 8766）
│   └── storage/                  # 文档持久化存储
│       ├── documents/            # Markdown 内容文件
│       └── metadata/             # 版本元数据 JSON
├── examples/                     # 示例 EMR 文本
│   ├── case5_emr.txt
│   └── slide6_emr.txt
├── tests/                        # 测试套件
│   ├── conftest.py
│   ├── test_engine.py            # 引擎单元测试（5 组）
│   ├── test_emr.py               # 端到端集成测试
│   └── test_virtual_docs.py      # 虚拟文档库测试
└── requirements.txt
```

## 设计原则

1. **规则驱动**：所有 DRG 分组逻辑由 `sample_rules.json` 驱动，引擎零硬编码医学知识。规则更新无需修改代码，仅替换 JSON 文件即可。
2. **优雅降级**：每个 LLM 依赖点均有 try/except 兜底。无 API Key 时系统以纯规则/模板方式运行，功能完整可用。LLM 是增强层而非依赖项。
3. **确定性优先**：分组链路采用首次匹配策略，同一输入始终产生同一输出，结果可复现、可审计。
4. **全覆盖兜底**：每个 MDC 均设有手术兜底 ADRG 和内科兜底 ADRG，确保所有编码均能产生分组结果，不存在未处理路径。
5. **关注点分离**：解析（emr_parser）、规则匹配（engine）、编排（agent）、文档生成（docgen）、测试（testgen）、持久化（virtual_docs）模块各司其职，无跨层耦合。
