# AI Tutor Main Solver

基于 `kimi-agent-sdk` 实现的多轮对话AI助教系统。

## 架构设计

### 双模式架构

```
┌─────────────────────────────────────────────────────────────┐
│                      MainSolver                            │
├─────────────────────────────────────────────────────────────┤
│  初始问题 (First Question)        追问 (Follow-up)          │
│        │                              │                     │
│        ▼                              ▼                     │
│  ┌──────────────┐              ┌──────────────┐             │
│  │ 复杂多Agent │              │ 单Agent会话  │             │
│  │ 分析流程   │              │ 保持上下文   │             │
│  └──────────────┘              └──────────────┘             │
│        │                              │                     │
│        └──────────────┬───────────────┘                     │
│                       ▼                                     │
│              ┌─────────────────┐                           │
│              │ 统一格式化输出  │                           │
│              └─────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

## 设计理念

### 初始问题：多Agent深度分析
- 使用多个专门Agent（InvestigateAgent, NoteAgent, SolveAgent等）
- 进行知识检索、分析、代码生成、可视化等复杂操作
- 适合解决复杂的、需要多步骤分析的学习问题

### 追问：单Agent对话保持上下文
- 使用 `kimi-agent-sdk` 的 `Session` API
- 保持对话上下文，支持多轮连续交流
- 适合简单的追问、澄清、深入讨论

## 快速开始

### 安装依赖

```bash
# 安装 kimi-agent-sdk
pip install kimi-agent-sdk

# 其他依赖
pip install python-dotenv
```

### 配置环境变量

创建 `.env` 文件：

```bash
KIMI_API_KEY=your-api-key-here
KIMI_BASE_URL=https://api.moonshot.ai/v1  # 可选，默认使用Moonshot API
```

### 基本使用

```python
import asyncio
from main_solver import MainSolver

async def main():
    # 初始化Solver
    solver = MainSolver(kb_name="ai_textbook")
    await solver.ainit()
    
    # 第一轮：复杂问题，使用多Agent分析
    result = await solver.solve(
        question="请用同一个生活化的例子给我串讲解释正态分布、t分布、卡方分布和F分布",
    )
    print("=== 初始回答 ===")
    print(result['formatted_solution'])
    
    # 第二轮及以后：追问，使用单Agent保持上下文
    follow_result = await solver.chat("刚才提到的t分布和自由度有什么关系？")
    print("\n=== 追问回答 ===")
    print(follow_result['response'])
    
    # 保存对话历史
    solver.save_history("./conversation_history.json")
    
    # 清理资源
    await solver.close()

asyncio.run(main())
```

## API文档

### MainSolver 类

#### 初始化

```python
solver = MainSolver(
    kb_name="ai_textbook",           # 知识库名称
    output_base_dir="./output",      # 输出目录
    model="kimi-k2-thinking-turbo",  # 模型名称
    config_path=None,                  # 配置文件路径（可选）
)
await solver.ainit()
```

#### solve() - 解决初始问题

```python
result = await solver.solve(
    question="问题内容",
    verbose=True,  # 是否打印详细信息
)

# 返回结果包含:
# - formatted_solution: 格式化的解答
# - output_dir: 输出目录
# - metadata: 元数据
```

#### chat() - 追问对话

```python
result = await solver.chat(
    question="追问内容",
    stream=True,   # 是否流式输出
    yolo=True,     # 是否自动批准工具调用
)

# 返回结果包含:
# - response: 助手回答
# - session_id: 会话ID
```

#### 其他方法

```python
# 保存/加载对话历史
solver.save_history("./history.json")
solver.load_history("./history.json")

# 获取对话历史列表
history = solver.get_history()

# 恢复之前的会话
success = await solver.resume_session(session_id)

# 关闭资源
await solver.close()
```

## 运行示例

项目包含完整的示例脚本：

```bash
# 运行所有演示
python example.py

# 或使用UV
uv run example.py
```

示例包含：
1. **单个问题解答** - 演示基本使用
2. **多轮对话** - 演示初始问题 + 追问
3. **恢复会话** - 演示会话持久化

## 技术依赖

- `kimi-agent-sdk`: Kimi Agent SDK for Python
- `DeepTutor`: 复用其Agent架构（可选，用于初始复杂分析）
- `python-dotenv`: 环境变量管理
- Python 3.10+

## 项目结构

```
My-AI-Turtor/
├── main_solver.py          # 主Solver类（核心实现）
├── example.py              # 使用示例和演示
├── requirements.txt        # Python依赖
└── README.md              # 本文档
```

## 许可证

MIT License
