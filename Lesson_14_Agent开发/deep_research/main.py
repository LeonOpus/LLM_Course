"""
主程序 - Deep Research Agent 入口

提供简洁的 API 接口，用于执行深度研究任务。
"""

import os
import json
import time
from datetime import datetime
from typing import Optional, Callable

from .orchestrator import Orchestrator, ResearchState
from .workers import search_worker_factory, WorkerFactory
from .config import AGENT_CONFIG, OUTPUT_CONFIG


# ==================== 控制台输出格式化 ====================

class ConsoleReporter:
    """控制台进度报告器"""

    # ANSI 颜色码
    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "red": "\033[91m",
    }

    STAGE_ICONS = {
        "decomposing": "🔍",
        "decomposed": "📋",
        "dispatching": "🚀",
        "worker_started": "👷",
        "worker_completed": "✅",
        "worker_failed": "❌",
        "synthesizing": "📝",
        "synthesized": "📄",
        "quality_checking": "🔎",
        "quality_checked": "📊",
        "completed": "🎉",
        "failed": "💥",
        "revision_needed": "🔄",
        # 迭代优化相关
        "iteration_start": "🔄",
        "iteration_evaluated": "📈",
        "iteration_continue": "🔧",
        "iteration_end": "✓",
        "quality_passed": "✅",
        "analyzing_gaps": "🔍",
        "gaps_analyzed": "📋",
        "dispatching_supplementary": "🚀",
        "supplementary_worker_started": "👷",
        "supplementary_worker_completed": "✅",
        "supplementary_worker_failed": "❌",
        "refining_report": "✏️",
        "report_refined": "📄",
        "no_supplementary_tasks": "ℹ️",
    }

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.start_time = time.time()

    def _color(self, text: str, color: str) -> str:
        """添加颜色"""
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def _elapsed(self) -> str:
        """获取已用时间"""
        elapsed = time.time() - self.start_time
        return f"[{elapsed:.1f}s]"

    def report(self, stage: str, data: dict):
        """报告进度"""
        if not self.verbose:
            return

        icon = self.STAGE_ICONS.get(stage, "📌")
        elapsed = self._elapsed()

        if stage == "decomposing":
            print(f"\n{icon} {self._color('正在分析任务...', 'cyan')}")

        elif stage == "decomposed":
            count = data.get("subtask_count", 0)
            print(f"{icon} {self._color(f'任务拆解完成，共 {count} 个子任务', 'green')}")
            for st in data.get("subtasks", []):
                print(f"   • {st['name']}")

        elif stage == "dispatching":
            count = data.get("worker_count", 0)
            print(f"\n{icon} {self._color(f'正在分发 {count} 个 Workers...', 'cyan')}")

        elif stage == "worker_started":
            name = data.get("task_name", "")
            print(f"   {icon} {self._color(f'[开始] {name}', 'dim')}")

        elif stage == "worker_completed":
            name = data.get("task_name", "")
            print(f"   {icon} {self._color(f'[完成] {name}', 'green')} {elapsed}")

        elif stage == "worker_failed":
            name = data.get("task_name", "")
            error = data.get("error", "")
            print(f"   {icon} {self._color(f'[失败] {name}: {error}', 'red')}")

        elif stage == "synthesizing":
            print(f"\n{icon} {self._color('正在生成研究报告...', 'cyan')}")

        elif stage == "synthesized":
            length = data.get("report_length", 0)
            print(f"{icon} {self._color(f'报告生成完成 ({length} 字符)', 'green')}")

        elif stage == "quality_checking":
            print(f"\n{icon} {self._color('正在进行质量检查...', 'cyan')}")

        elif stage == "quality_checked":
            score = data.get("score", 0)
            color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
            print(f"{icon} 质量评分: {self._color(f'{score}分', color)}")

        elif stage == "completed":
            duration = data.get("duration", 0)
            score = data.get("quality_score", 0)
            iterations = data.get("iterations", 1)
            print(f"\n{icon} {self._color('研究完成!', 'bold')}")
            print(f"   ⏱️  总耗时: {duration:.1f} 秒")
            print(f"   📊 质量评分: {score} 分")
            print(f"   🔄 迭代次数: {iterations} 次")

        elif stage == "failed":
            error = data.get("error", "")
            print(f"\n{icon} {self._color(f'研究失败: {error}', 'red')}")

        # ========== 迭代优化相关事件 ==========
        elif stage == "iteration_start":
            iteration = data.get("iteration", 1)
            max_iter = data.get("max_iterations", 5)
            print(f"\n{icon} {self._color(f'━━━ 第 {iteration}/{max_iter} 次迭代 ━━━', 'magenta')}")

        elif stage == "iteration_evaluated":
            iteration = data.get("iteration", 1)
            score = data.get("score", 0)
            threshold = data.get("threshold", 80)
            passed = data.get("passed", False)
            status = "通过" if passed else "未通过"
            color = "green" if passed else "yellow"
            print(f"   {icon} 质量评分: {self._color(f'{score}分', color)} (阈值:{threshold}) [{status}]")

        elif stage == "quality_passed":
            score = data.get("score", 0)
            print(f"\n{icon} {self._color(f'质量检查通过！最终评分: {score}分', 'green')}")

        elif stage == "iteration_continue":
            reason = data.get("reason", "")
            print(f"   {icon} {self._color(f'继续优化: {reason}', 'yellow')}")

        elif stage == "analyzing_gaps":
            print(f"   {icon} {self._color('正在分析报告差距...', 'cyan')}")

        elif stage == "gaps_analyzed":
            gap_count = data.get("gap_count", 0)
            task_count = data.get("task_count", 0)
            print(f"   {icon} 识别到 {gap_count} 个差距，生成 {task_count} 个补充任务")

        elif stage == "dispatching_supplementary":
            task_count = data.get("task_count", 0)
            print(f"   {icon} {self._color(f'分发 {task_count} 个补充研究任务...', 'cyan')}")

        elif stage == "supplementary_worker_started":
            name = data.get("task_name", "")
            print(f"      {icon} {self._color(f'[补充] {name}', 'dim')}")

        elif stage == "supplementary_worker_completed":
            name = data.get("task_name", "")
            print(f"      {icon} {self._color(f'[完成] {name}', 'green')} {elapsed}")

        elif stage == "supplementary_worker_failed":
            name = data.get("task_name", "")
            error = data.get("error", "")
            print(f"      {icon} {self._color(f'[失败] {name}: {error}', 'red')}")

        elif stage == "refining_report":
            print(f"   {icon} {self._color('正在修订报告...', 'cyan')}")

        elif stage == "report_refined":
            length = data.get("new_length", 0)
            print(f"   {icon} {self._color(f'报告修订完成 ({length} 字符)', 'green')}")

        elif stage == "no_supplementary_tasks":
            print(f"   {icon} {self._color('无需补充研究', 'dim')}")

        elif stage == "iteration_end":
            pass  # 静默结束


# ==================== Deep Research Agent ====================

class DeepResearchAgent:
    """
    Deep Research Agent - 深度研究智能体

    基于 Orchestrator-Workers 架构的深度研究系统。

    使用示例:
        agent = DeepResearchAgent()
        report = agent.research("2024年电动汽车市场分析报告")
        print(report)
    """

    def __init__(
        self,
        verbose: bool = True,
        save_output: bool = True,
        output_dir: str = None,
    ):
        """
        初始化 Deep Research Agent

        参数:
            verbose: 是否显示详细进度信息
            save_output: 是否保存输出文件
            output_dir: 输出目录路径
        """
        self.verbose = verbose
        self.save_output = save_output
        self.output_dir = output_dir or OUTPUT_CONFIG["output_dir"]
        self.reporter = ConsoleReporter(verbose=verbose)

    def research(
        self,
        task: str,
        max_workers: int = None,
        callback: Callable[[str, dict], None] = None,
    ) -> str:
        """
        执行深度研究任务

        参数:
            task: 研究任务描述
            max_workers: 最大并行 Worker 数（可选）
            callback: 自定义进度回调函数（可选）

        返回:
            str: 研究报告（Markdown 格式）
        """
        # 打印欢迎信息
        if self.verbose:
            self._print_header(task)

        # 创建进度回调
        def on_progress(stage: str, data: dict):
            self.reporter.report(stage, data)
            if callback:
                callback(stage, data)

        # 创建 Orchestrator
        orchestrator = Orchestrator(
            worker_factory=search_worker_factory,
            max_workers=max_workers or AGENT_CONFIG["max_workers"],
            on_progress=on_progress,
        )

        # 执行研究
        state = orchestrator.run(task)

        # 保存输出
        if self.save_output and state.status == "completed":
            self._save_output(state)

        # 打印结果
        if self.verbose:
            self._print_footer(state)

        return state.final_report

    def research_stream(
        self,
        task: str,
        max_workers: int = None,
    ):
        """
        流式执行深度研究任务（生成器模式）

        参数:
            task: 研究任务描述
            max_workers: 最大并行 Worker 数

        Yields:
            tuple: (stage, data) 进度信息
        """
        progress_events = []

        def collect_progress(stage: str, data: dict):
            progress_events.append((stage, data))

        # 创建 Orchestrator
        orchestrator = Orchestrator(
            worker_factory=search_worker_factory,
            max_workers=max_workers or AGENT_CONFIG["max_workers"],
            on_progress=collect_progress,
        )

        # 执行研究
        state = orchestrator.run(task)

        # 输出所有进度事件
        for stage, data in progress_events:
            yield ("progress", {"stage": stage, "data": data})

        # 输出最终结果
        yield ("result", {
            "report": state.final_report,
            "quality_score": state.quality_score,
            "status": state.status,
            "duration": state.end_time - state.start_time,
        })

    def _print_header(self, task: str):
        """打印研究开始信息"""
        print("\n" + "=" * 60)
        print("🔬 Deep Research Agent")
        print("=" * 60)
        print(f"\n📋 研究任务: {task}")
        print(f"📅 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 60)

    def _print_footer(self, state: ResearchState):
        """打印研究结束信息"""
        print("\n" + "=" * 60)
        if state.status == "completed":
            print("✅ 研究报告已生成")
            if self.save_output:
                print(f"📁 输出目录: {self.output_dir}")
        else:
            print(f"❌ 研究失败: {state.error_msg}")
        print("=" * 60 + "\n")

    def _save_output(self, state: ResearchState):
        """保存输出文件"""
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"research_{timestamp}"

        # 保存 Markdown 报告
        md_path = os.path.join(self.output_dir, f"{base_name}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(state.final_report)

        # 保存 JSON 元数据
        json_path = os.path.join(self.output_dir, f"{base_name}_meta.json")
        meta = {
            "original_task": state.original_task,
            "status": state.status,
            "quality_score": state.quality_score,
            "duration": state.end_time - state.start_time,
            "timestamp": timestamp,
            "task_plan": {
                "understanding": state.task_plan.task_understanding if state.task_plan else {},
                "subtask_count": len(state.task_plan.subtasks) if state.task_plan else 0,
                "report_structure": state.task_plan.report_structure if state.task_plan else {},
            },
            "worker_results_count": len(state.worker_results),
            # 迭代优化信息
            "iteration_count": state.iteration_count,
            "iteration_history": [
                {
                    "iteration": record.iteration,
                    "quality_score": record.quality_score,
                    "report_length": len(record.report),
                    "gap_count": len(record.gap_analysis.get("missing_aspects", [])) if record.gap_analysis else 0,
                    "supplementary_task_count": len(record.supplementary_results),
                }
                for record in state.iteration_history
            ],
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)


# ==================== CLI 入口 ====================

def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Deep Research Agent - 深度研究智能体",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m deep_research "2024年电动汽车市场分析报告"
  python -m deep_research "人工智能在医疗领域的应用" --workers 4
  python -m deep_research "区块链技术发展趋势" --quiet --output ./reports
        """,
    )

    parser.add_argument(
        "task",
        type=str,
        help="研究任务描述",
    )

    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=None,
        help="最大并行 Worker 数",
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="输出目录路径",
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="安静模式（不显示进度信息）",
    )

    parser.add_argument(
        "--no-save",
        action="store_true",
        help="不保存输出文件",
    )

    args = parser.parse_args()

    # 创建 Agent 并执行研究
    agent = DeepResearchAgent(
        verbose=not args.quiet,
        save_output=not args.no_save,
        output_dir=args.output,
    )

    report = agent.research(
        task=args.task,
        max_workers=args.workers,
    )

    # 输出报告（如果是安静模式）
    if args.quiet:
        print(report)


if __name__ == "__main__":
    main()
