import json
import sys
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from pydantic import BaseModel, Field
from colorama import init, Fore, Style
from mcp.server import FastMCP
import logging

# 初始化颜色支持
init()

logger = logging.getLogger(__name__)
mcp = FastMCP("顺序思考", debug=True)


class ThoughtData(BaseModel):
    thought: str = Field(..., description="Your current thinking step")
    thoughtNumber: int = Field(..., description="Current thought number", gt=0)
    totalThoughts: int = Field(..., description="Estimated total thoughts needed", gt=0)
    nextThoughtNeeded: bool = Field(..., description="Whether another thought step is needed")
    isRevision: Optional[bool] = Field(None, description="Whether this revises previous thinking")
    revisesThought: Optional[int] = Field(None, description="Which thought is being reconsidered", gt=0)
    branchFromThought: Optional[int] = Field(None, description="Branching point thought number", gt=0)
    branchId: Optional[str] = Field(None, description="Branch identifier")
    needsMoreThoughts: Optional[bool] = Field(None, description="If more thoughts are needed")


class SequentialThinkingServer:
    def __init__(self):
        self.thought_history: List[ThoughtData] = []
        self.branches: Dict[str, List[ThoughtData]] = {}

    def format_thought(self, thought_data: ThoughtData) -> str:
        prefix = ""
        context = ""

        if thought_data.isRevision:
            prefix = f"{Fore.YELLOW}🔄 Revision{Style.RESET_ALL}"
            context = f" (revising thought {thought_data.revisesThought})"
        elif thought_data.branchFromThought:
            prefix = f"{Fore.GREEN}🌿 Branch{Style.RESET_ALL}"
            context = f" (from thought {thought_data.branchFromThought}, ID: {thought_data.branchId})"
        else:
            prefix = f"{Fore.BLUE}💭 Thought{Style.RESET_ALL}"
            context = ""

        header = f"{prefix} {thought_data.thoughtNumber}/{thought_data.totalThoughts}{context}"
        # 计算显示长度时需要去除ANSI颜色控制字符
        ansi_escape_free = header.replace('\033[34m', '').replace('\033[32m', '').replace('\033[33m', '').replace(
            '\033[0m', '')
        max_length = max(len(ansi_escape_free), len(thought_data.thought))
        border = "─" * (max_length + 4)

        return f"""
┌{border}┐
│ {header} │
├{border}┤
│ {thought_data.thought.ljust(max_length + 2)} │
└{border}┘"""

    def process_thought(self, thought_data: ThoughtData) -> Dict[str, Any]:
        try:
            # 调整总思考步骤数，如果当前步骤超过了预估总数
            if thought_data.thoughtNumber > thought_data.totalThoughts:
                thought_data.totalThoughts = thought_data.thoughtNumber

            self.thought_history.append(thought_data)

            # 处理分支思考
            if thought_data.branchFromThought and thought_data.branchId:
                if thought_data.branchId not in self.branches:
                    self.branches[thought_data.branchId] = []
                self.branches[thought_data.branchId].append(thought_data)

            # 在控制台显示格式化的思考
            formatted_thought = self.format_thought(thought_data)
            logger.info(formatted_thought)

            return {
                "thoughtNumber": thought_data.thoughtNumber,
                "totalThoughts": thought_data.totalThoughts,
                "nextThoughtNeeded": thought_data.nextThoughtNeeded,
                "branches": list(self.branches.keys()),
                "thoughtHistoryLength": len(self.thought_history)
            }
        except Exception as error:
            logger.error(f"Error processing thought: {error}")
            return {
                "error": str(error),
                "status": "failed"
            }


# 创建全局思考服务器实例
thinking_server = SequentialThinkingServer()


@mcp.tool(
    description="""A detailed tool for dynamic and reflective problem-solving through thoughts.
This tool helps analyze problems through a flexible thinking process that can adapt and evolve.
Each thought can build on, question, or revise previous insights as understanding deepens.

When to use this tool:
- Breaking down complex problems into steps
- Planning and design with room for revision
- Analysis that might need course correction
- Problems where the full scope might not be clear initially
- Problems that require a multi-step solution
- Tasks that need to maintain context over multiple steps
- Situations where irrelevant information needs to be filtered out

Key features:
- You can adjust total_thoughts up or down as you progress
- You can question or revise previous thoughts
- You can add more thoughts even after reaching what seemed like the end
- You can express uncertainty and explore alternative approaches
- Not every thought needs to build linearly - you can branch or backtrack
- Generates a solution hypothesis
- Verifies the hypothesis based on the Chain of Thought steps
- Repeats the process until satisfied
- Provides a correct answer

You should:
1. Start with an initial estimate of needed thoughts, but be ready to adjust
2. Feel free to question or revise previous thoughts
3. Don't hesitate to add more thoughts if needed, even at the "end"
4. Express uncertainty when present
5. Mark thoughts that revise previous thinking or branch into new paths
6. Ignore information that is irrelevant to the current step
7. Generate a solution hypothesis when appropriate
8. Verify the hypothesis based on the Chain of Thought steps
9. Repeat the process until satisfied with the solution
10. Provide a single, ideally correct answer as the final output
11. Only set next_thought_needed to false when truly done and a satisfactory answer is reached"""
)
async def sequential_thinking(thought_data: ThoughtData):
    """
    进行顺序思考，这是一种动态且反思性的问题解决工具，可以通过思考步骤来分析和解决问题。
    每个思考步骤可以基于先前的洞察力进行构建、质疑或修改，随着对问题理解的加深而演变。

    参数:
        thought_data: 包含当前思考步骤的所有信息
    返回:
        包含思考状态信息的JSON对象
    """
    return thinking_server.process_thought(thought_data)


if __name__ == "__main__":
    mcp.run(transport='sse')
