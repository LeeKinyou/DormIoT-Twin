from dormiot.config import Settings


class TestSettings:
    def test_field_types(self):
        s = Settings()
        assert isinstance(s.simulation_node_count, int)
        assert isinstance(s.simulation_report_interval_ms, int)
        assert isinstance(s.power_threshold_illegal, float)
        assert isinstance(s.smoke_threshold_critical, float)
        assert isinstance(s.openai_api_key, str)
        assert isinstance(s.openai_base_url, str)
        assert isinstance(s.openai_model, str)

    def test_default_values(self):
        s = Settings()
        assert s.simulation_node_count == 6
        # openai_base_url 和 openai_model 可能被 .env 覆盖，只验证类型
        assert isinstance(s.openai_base_url, str)
        assert len(s.openai_base_url) > 0
        assert isinstance(s.openai_model, str)
        assert len(s.openai_model) > 0

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("DORMIOT_SIMULATION_NODE_COUNT", "100")
        monkeypatch.setenv("DORMIOT_OPENAI_MODEL", "gpt-4o")
        s = Settings()
        assert s.simulation_node_count == 100
        assert s.openai_model == "gpt-4o"
