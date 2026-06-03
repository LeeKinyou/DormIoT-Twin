"""
阶段五测试：AI 安全专家研判模块
"""
import pytest
from unittest.mock import patch, MagicMock


class TestAIDiagnoser:
    """测试 AI 诊断器"""

    def test_import_diagnoser(self):
        """测试诊断器模块可以导入"""
        from dormiot.ai_diagnoser import AIDiagnoser
        assert AIDiagnoser is not None

    def test_singleton_pattern(self):
        """测试诊断器是单例"""
        from dormiot.ai_diagnoser import AIDiagnoser
        d1 = AIDiagnoser()
        d2 = AIDiagnoser()
        assert d1 is d2

    def test_analyze_power_array_returns_string(self):
        """测试 analyze_power_array 返回字符串"""
        from dormiot.ai_diagnoser import AIDiagnoser
        diagnoser = AIDiagnoser()
        # Mock LLM 调用
        with patch.object(diagnoser, '_call_llm', return_value="测试诊断结果"):
            result = diagnoser.analyze_power_array([50.0, 55.0, 1850.0], room_id="101")
        assert isinstance(result, str)

    def test_analyze_power_array_empty_returns_default(self):
        """测试空功率数组返回默认消息"""
        from dormiot.ai_diagnoser import AIDiagnoser
        diagnoser = AIDiagnoser()
        result = diagnoser.analyze_power_array([], room_id="101")
        assert "无数据" in result or "数据不足" in result

    def test_analyze_power_array_short_returns_default(self):
        """测试过短的功率数组返回默认消息"""
        from dormiot.ai_diagnoser import AIDiagnoser
        diagnoser = AIDiagnoser()
        result = diagnoser.analyze_power_array([50.0], room_id="101")
        assert "数据不足" in result or "无数据" in result

    def test_build_prompt_contains_power_data(self):
        """测试 prompt 包含功率数据"""
        from dormiot.ai_diagnoser import AIDiagnoser
        diagnoser = AIDiagnoser()
        power_array = [50.0, 55.0, 1850.0, 1860.0, 1840.0]
        prompt = diagnoser.build_prompt(power_array, room_id="101")
        assert "50.0" in prompt
        assert "1850.0" in prompt
        assert "101" in prompt

    def test_build_prompt_mentions_spike(self):
        """测试 prompt 识别尖峰特征"""
        from dormiot.ai_diagnoser import AIDiagnoser
        diagnoser = AIDiagnoser()
        # 尖峰特征：突然升高
        power_array = [50.0, 52.0, 55.0, 1850.0, 1860.0]
        prompt = diagnoser.build_prompt(power_array, room_id="101")
        assert "尖峰" in prompt or "飙升" in prompt or "spike" in prompt.lower()

    def test_build_prompt_mentions_square_wave(self):
        """测试 prompt 识别方波特征"""
        from dormiot.ai_diagnoser import AIDiagnoser
        diagnoser = AIDiagnoser()
        # 方波特征：高低交替
        power_array = [
            1250.0, 1260.0, 1240.0, 1250.0, 1255.0,  # 高电平
            80.0, 85.0, 78.0, 82.0, 80.0,             # 低电平
        ]
        prompt = diagnoser.build_prompt(power_array, room_id="101")
        assert "方波" in prompt or "交替" in prompt or "square" in prompt.lower()

    def test_build_prompt_mentions_sustained_high(self):
        """测试 prompt 识别持续高频特征"""
        from dormiot.ai_diagnoser import AIDiagnoser
        diagnoser = AIDiagnoser()
        # 持续高频
        power_array = [1850.0, 1860.0, 1840.0, 1855.0, 1845.0, 1852.0, 1848.0]
        prompt = diagnoser.build_prompt(power_array, room_id="101")
        assert "持续" in prompt or "高频" in prompt or "sustained" in prompt.lower()

    def test_classify_waveform_spike(self):
        """测试波形分类：尖峰"""
        from dormiot.ai_diagnoser import AIDiagnoser
        diagnoser = AIDiagnoser()
        power_array = [50.0, 52.0, 55.0, 1850.0, 1860.0]
        waveform_type = diagnoser.classify_waveform(power_array)
        assert waveform_type in ["尖峰", "spike"]

    def test_classify_waveform_square(self):
        """测试波形分类：方波"""
        from dormiot.ai_diagnoser import AIDiagnoser
        diagnoser = AIDiagnoser()
        power_array = [
            1250.0, 1260.0, 1240.0, 1250.0, 1255.0,
            80.0, 85.0, 78.0, 82.0, 80.0,
        ]
        waveform_type = diagnoser.classify_waveform(power_array)
        assert waveform_type in ["方波", "square"]

    def test_classify_waveform_sustained(self):
        """测试波形分类：持续高频"""
        from dormiot.ai_diagnoser import AIDiagnoser
        diagnoser = AIDiagnoser()
        power_array = [1850.0, 1860.0, 1840.0, 1855.0, 1845.0, 1852.0, 1848.0]
        waveform_type = diagnoser.classify_waveform(power_array)
        assert waveform_type in ["持续高频", "sustained"]

    def test_classify_waveform_normal(self):
        """测试波形分类：正常"""
        from dormiot.ai_diagnoser import AIDiagnoser
        diagnoser = AIDiagnoser()
        power_array = [50.0, 52.0, 48.0, 51.0, 53.0]
        waveform_type = diagnoser.classify_waveform(power_array)
        assert waveform_type in ["正常", "normal"]

    @patch('dormiot.ai_diagnoser.ChatOpenAI')
    def test_call_llm_invokes_model(self, mock_chat_cls):
        """测试 _call_llm 调用大模型"""
        from dormiot.ai_diagnoser import AIDiagnoser
        mock_instance = MagicMock()
        mock_instance.invoke.return_value.content = "疑似热得快"
        mock_chat_cls.return_value = mock_instance

        diagnoser = AIDiagnoser()
        result = diagnoser._call_llm("测试 prompt")
        assert result == "疑似热得快"

    @patch('dormiot.ai_diagnoser.ChatOpenAI')
    def test_call_llm_handles_error(self, mock_chat_cls):
        """测试 _call_llm 处理异常"""
        from dormiot.ai_diagnoser import AIDiagnoser
        mock_instance = MagicMock()
        mock_instance.invoke.side_effect = Exception("API 超时")
        mock_chat_cls.return_value = mock_instance

        diagnoser = AIDiagnoser()
        diagnoser.reset()  # 重置单例以使用新的 mock
        result = diagnoser._call_llm("测试 prompt")
        assert "失败" in result

    @patch('dormiot.ai_diagnoser.ChatOpenAI')
    def test_analyze_integration(self, mock_chat_cls):
        """测试完整分析流程（集成测试）"""
        from dormiot.ai_diagnoser import AIDiagnoser
        mock_instance = MagicMock()
        mock_instance.invoke.return_value.content = "疑似使用热得快/吹风机等大功率电阻设备，建议立即断电检查"
        mock_chat_cls.return_value = mock_instance

        diagnoser = AIDiagnoser()
        diagnoser.reset()  # 重置单例以使用新的 mock
        power_array = [50.0, 52.0, 55.0, 1850.0, 1860.0, 1840.0, 1855.0]
        result = diagnoser.analyze_power_array(power_array, room_id="101")
        assert "热得快" in result
        mock_instance.invoke.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
