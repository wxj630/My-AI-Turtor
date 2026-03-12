#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Tutor - 基于 kimi-cli 自定义 Agent 的多轮对话 AI 助教

使用方式:
    方法1 - 命令行:
        kimi --agent-file ./agents/ai_tutor.yaml

    方法2 - Python SDK:
        from ai_tutor import AITutor
        tutor = AITutor()
        await tutor.solve("问题")

架构:
    主 Agent (ai_tutor) - 协调所有子 Agent
    ├── InvestigateAgent - 知识检索与调研
    ├── NoteAgent - 笔记整理与分析
    ├── ManagerAgent - 解题规划
    ├── SolveAgent - 逐步求解
    └── ResponseAgent - 响应生成
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Kimi Agent SDK
from kimi_agent_sdk import Session, prompt, TextPart, ApprovalRequest
from kaos.path import KaosPath

from dotenv import load_dotenv


class AITutor:
    """
    AI Tutor - 多轮对话 AI 助教

    使用 kimi-cli 自定义 Agent 系统，支持:
    1. 初始复杂问题 - 多 Agent 协作分析
    2. 追问对话 - Session 保持上下文
    """

    def __init__(
        self,
        agent_file: str | Path = "./agents/ai_tutor.yaml",
        output_dir: str = "./output",
        model: str = "ark-code-latest",
    ):
        """
        初始化 AI Tutor

        Args:
            agent_file: Agent 配置文件路径
            output_dir: 输出目录
            model: 使用的模型
        """
        self.agent_file = Path(agent_file)
        self.output_dir = Path(output_dir)
        self.model = model

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Session 管理
        self._session: Optional[Session] = None
        self._session_id: Optional[str] = None

        # 对话历史
        self._conversation_history: list[dict] = []

        # 当前问题上下文
        self._current_question: Optional[str] = None
        self._current_solution: Optional[str] = None

        print(f"🎓 AI Tutor 初始化完成")
        print(f"   Agent 配置: {self.agent_file}")
        print(f"   输出目录: {self.output_dir}")

    async def solve(
        self,
        question: str,
        verbose: bool = True,
        stream: bool = True,
    ) -> dict[str, Any]:
        """
        解决初始复杂问题（使用多 Agent 分析）

        通过 kimi-cli 的 Agent 系统，调用 InvestigateAgent, NoteAgent,
        ManagerAgent, SolveAgent 等多个子 Agent 协作完成复杂分析。

        Args:
            question: 用户问题
            verbose: 是否打印详细信息
            stream: 是否流式输出

        Returns:
            dict 包含：
            - question: 原始问题
            - solution: 解答内容
            - output_dir: 输出目录
            - metadata: 元数据
        """
        self._current_question = question

        # 关闭旧的 session（如果有）
        if self._session is not None:
            await self._session.close()
            self._session = None
            self._session_id = None

        # 创建新的 session，使用 Agent 文件
        work_dir = KaosPath(str(self.output_dir))

        print(f"🔍 启动多 Agent 分析流程...")
        print(f"   问题: {question[:80]}{'...' if len(question) > 80 else ''}")

        # 使用 Session 运行 Agent 分析
        self._session = await Session.create(
            work_dir=work_dir,
            model=self.model,
            agent_file=self.agent_file,
            yolo=True,  # 自动批准工具调用
        )

        self._session_id = self._session.id

        # 构建带有系统上下文的初始提示
        initial_prompt = f"""请作为 AI 助教，解决以下学习问题。

## 用户问题
{question}

## 要求
1. 首先使用 InvestigateAgent 调研相关知识
2. 然后使用 NoteAgent 整理笔记
3. 使用 ManagerAgent 制定解题计划
4. 使用 SolveAgent 逐步求解
5. 最后生成完整的解答

请开始分析。"""

        # 运行分析流程
        full_response = ""
        async for msg in self._session.prompt(initial_prompt):
            # print(type(msg))
            if isinstance(msg, TextPart):
                full_response += msg.text
                if stream:
                    print(msg.text, end="", flush=True)
            elif isinstance(msg, ApprovalRequest):
                msg.resolve("approve")

        if stream:
            print()  # 换行

        # 保存解答
        self._current_solution = full_response
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_subdir = self.output_dir / f"solve_{timestamp}"
        output_subdir.mkdir(parents=True, exist_ok=True)

        # 保存结果到文件
        solution_file = output_subdir / "solution.md"
        with open(solution_file, "w", encoding="utf-8") as f:
            f.write(full_response)

        # 保存元数据
        metadata = {
            "question": question,
            "timestamp": timestamp,
            "session_id": self._session_id,
            "output_dir": str(output_subdir),
        }
        metadata_file = output_subdir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 分析完成")
        print(f"   解答保存到: {solution_file}")

        # 记录到对话历史
        self._conversation_history.append(
            {
                "role": "user",
                "content": question,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self._conversation_history.append(
            {
                "role": "assistant",
                "content": full_response,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return {
            "question": question,
            "solution": full_response,
            "output_dir": str(output_subdir),
            "solution_file": str(solution_file),
            "session_id": self._session_id,
            "metadata": metadata,
        }

    async def chat(
        self,
        question: str,
        stream: bool = True,
    ) -> dict[str, Any]:
        """
        多轮对话追问

        在初始问题解答后，使用此方法进行追问。
        复用已有的 Session 保持对话上下文。

        Args:
            question: 追问问题
            stream: 是否流式输出

        Returns:
            dict 包含：
            - response: 助手回答
            - session_id: 会话 ID
        """
        if self._session is None:
            raise RuntimeError(
                "Session not initialized. "
                "Please call solve() first to start a new session."
            )

        # 记录用户问题
        self._conversation_history.append(
            {
                "role": "user",
                "content": question,
                "timestamp": datetime.now().isoformat(),
            }
        )

        print(f"💬 追问: {question}")

        # 使用 Session 发送问题并获取回复
        full_response = ""
        async for msg in self._session.prompt(question):
            # print(type(msg))
            if isinstance(msg, TextPart):
                full_response += msg.text
                if stream:
                    print(msg.text, end="", flush=True)
            elif isinstance(msg, ApprovalRequest):
                msg.resolve("approve")

        if stream:
            print()  # 换行

        # 记录助手回复
        self._conversation_history.append(
            {
                "role": "assistant",
                "content": full_response,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return {
            "response": full_response,
            "session_id": self._session_id,
        }

    async def close(self) -> None:
        """
        关闭 Tutor，清理资源
        """
        if self._session is not None:
            await self._session.close()
            self._session = None
            self._session_id = None
            print("✅ Session 已关闭")

    def save_history(self, filepath: str) -> None:
        """
        保存对话历史到文件

        Args:
            filepath: 文件路径
        """
        data = {
            "history": self._conversation_history,
            "current_question": self._current_question,
            "current_solution": self._current_solution,
            "session_id": self._session_id,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ 对话历史已保存: {filepath}")

    def load_history(self, filepath: str) -> None:
        """
        从文件加载对话历史

        Args:
            filepath: 文件路径
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._conversation_history = data.get("history", [])
        self._current_question = data.get("current_question")
        self._current_solution = data.get("current_solution")

        print(f"✅ 对话历史已加载: {filepath}")


async def main():
    """
    示例用法
    """
    # 检查环境变量
    if not os.getenv("KIMI_API_KEY"):
        print("⚠️ 警告: 未设置 KIMI_API_KEY 环境变量")
        return

    # 创建 AI Tutor
    tutor = AITutor(
        agent_file="./agents/ai_tutor.yaml",
        output_dir="./output",
    )

    try:
        # 第一轮：复杂问题
        result = await tutor.solve(
            question="我是一个本科生，请用同一个生活化的例子给我串讲解释正态分布t分布卡方分布F分布和他们的关系，给出代码实现和可视化",
            stream=True,
        )

        print("\n" + "=" * 60)
        print("初始问题解答完成")
        print("=" * 60)

        # 第二轮：追问
        follow_up = "刚才提到的t分布和自由度有什么关系？"
        print(f"\n追问: {follow_up}")

        follow_result = await tutor.chat(follow_up, stream=True)

        print("\n" + "=" * 60)
        print("追问回答完成")
        print("=" * 60)

        # 继续追问
        while True:
            follow_up = input("\n请输入追问（或输入 'exit' 结束）：")
            if follow_up.lower() == "exit":
                break

            follow_result = await tutor.chat(follow_up, stream=True)

        # 保存历史
        tutor.save_history("./conversation_history.json")

    finally:
        await tutor.close()


if __name__ == "__main__":
    load_dotenv()  # 加载环境变量
    asyncio.run(main())
