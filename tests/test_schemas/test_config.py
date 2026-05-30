from dormiot.config import Settings


class TestSettings:
    def test_field_types(self):
        s = Settings()
        assert isinstance(s.mqtt_broker_port, int)
        assert isinstance(s.redis_port, int)
        assert isinstance(s.mysql_port, int)
        assert isinstance(s.simulation_node_count, int)
        assert isinstance(s.power_threshold_illegal, float)
        assert isinstance(s.smoke_threshold_critical, float)

    def test_mysql_url_format(self):
        s = Settings()
        assert s.mysql_url.startswith("mysql+pymysql://")
        assert f":{s.mysql_port}/" in s.mysql_url
        assert s.mysql_database in s.mysql_url

    def test_redis_url_format(self):
        s = Settings()
        assert s.redis_url.startswith("redis://")
        assert f":{s.redis_port}/" in s.redis_url

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("DORMIOT_MQTT_BROKER_HOST", "192.168.1.100")
        monkeypatch.setenv("DORMIOT_SIMULATION_NODE_COUNT", "100")
        s = Settings()
        assert s.mqtt_broker_host == "192.168.1.100"
        assert s.simulation_node_count == 100

    def test_mysql_url_encoding(self, monkeypatch):
        monkeypatch.setenv("DORMIOT_MYSQL_PASSWORD", "p@ss:word/123")
        monkeypatch.setenv("DORMIOT_MYSQL_USER", "test@user")
        s = Settings()
        assert "%40" in s.mysql_url
        assert "%3A" in s.mysql_url
        assert "%2F" in s.mysql_url

    def test_redis_url_with_password(self, monkeypatch):
        monkeypatch.setenv("DORMIOT_REDIS_PASSWORD", "r@edis:pwd")
        s = Settings()
        assert "%40" in s.redis_url
        assert "%3A" in s.redis_url
