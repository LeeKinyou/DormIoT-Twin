"""AI 安全专家研判模块

使用 LangChain + OpenAI 兼容 API 分析功率波形，给出安防研判。
"""
from __future__ import annotations

import threading
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from dormiot.config import settings


class AIDiagnoser:
    """AI 波形诊断器（线程安全单例）"""

    _instance: AIDiagnoser | None = None
    _lock = threading.Lock()

    def __new__(cls) -> AIDiagnoser:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._llm: ChatOpenAI | None = None

    def reset(self) -> None:
        """重置诊断器状态（用于测试）"""
        self._llm = None

    def _get_llm(self) -> ChatOpenAI:
        """懒加载 LLM 实例"""
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key or "sk-placeholder",
                base_url=settings.openai_base_url,
                temperature=0.3,
                max_tokens=200,
            )
        return self._llm

    def classify_waveform(self, power_array: list[float]) -> str:
        """对波形进行分类

        Args:
            power_array: 功率值数组

        Returns:
            波形类型："尖峰" / "方波" / "持续高频" / "正常"
        """
        if len(power_array) < 3:
            return "正常"

        # 计算统计特征
        avg = sum(power_array) / len(power_array)
        max_power = max(power_array)
        min_power = min(power_array)
        power_range = max_power - min_power

        # 检测尖峰：突然从低到高
        has_low_start = any(p < 200 for p in power_array[:3])
        has_high_end = any(p > 1000 for p in power_array[-3:])
        if has_low_start and has_high_end and power_range > 800:
            return "尖峰"

        # 检测方波：高低交替，范围大
        if power_range > 500:
            high_count = sum(1 for p in power_array if p > 600)
            low_count = sum(1 for p in power_array if p <= 600)
            if high_count > 0 and low_count > 0:
                # 检查是否有交替模式
                transitions = 0
                for i in range(1, len(power_array)):
                    prev_high = power_array[i - 1] > 600
                    curr_high = power_array[i] > 600
                    if prev_high != curr_high:
                        transitions += 1
                if transitions >= 2:
                    return "方波"

        # 检测高低交替模式（简化方波检测）
        high_count = sum(1 for p in power_array if p > 600)
        low_count = sum(1 for p in power_array if p <= 200)
        if high_count > 0 and low_count > 0 and power_range > 500:
            return "方波"

        # 检测持续高频：功率持续偏高
        if avg > 1000 and min_power > 500:
            return "持续高频"

        return "正常"

    def build_prompt(self, power_array: list[float], room_id: str) -> str:
        """构建 LLM 分析 Prompt

        Args:
            power_array: 功率值数组
            room_id: 房间号

        Returns:
            完整的 prompt 字符串
        """
        waveform_type = self.classify_waveform(power_array)
        power_str = ", ".join(f"{p:.1f}" for p in power_array[-10:])

        # 将中文类型映射到 prompt 描述
        type_desc = {
            "尖峰": "尖峰（突然飙升）",
            "方波": "方波（高低交替）",
            "持续高频": "持续高频",
            "正常": "正常波动",
        }.get(waveform_type, waveform_type)

        return (
            f"你是一个物联网数字孪生安防专家。以下是宿舍 {room_id} 过去10秒的真实电能波形数据（瓦特）：\n"
            f"[{power_str}]\n\n"
            f"该波形呈现{type_desc}特征。\n"
            f"请在 50 字内给出专业的安防研判，指出疑似何种违章电器，并给出处理建议。"
        )

    def analyze_power_array(
        self, power_array: list[float], room_id: str
    ) -> str:
        """分析功率数组，返回 AI 研判结果

        Args:
            power_array: 功率值数组
            room_id: 房间号

        Returns:
            AI 研判结果字符串
        """
        if len(power_array) < 3:
            return "数据不足，无法研判"

        prompt = self.build_prompt(power_array, room_id)
        return self._call_llm(prompt)

    def _call_llm(self, prompt: str) -> str:
        """调用大模型

        Args:
            prompt: 用户 prompt

        Returns:
            大模型返回的文本
        """
        try:
            llm = self._get_llm()
            messages = [
                SystemMessage(content="你是一个专业的物联网数字孪生安防专家。"),
                HumanMessage(content=prompt),
            ]
            response = llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            return f"AI 调用失败: {e}"
