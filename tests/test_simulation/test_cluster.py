from dormiot.schemas.device import DeviceStatus
from dormiot.simulation.cluster import ClusterConfig, SimulationCluster


class TestSimulationCluster:
    def test_default_device_count(self):
        cluster = SimulationCluster()
        # 4 栋楼 × 6 间 = 24
        assert cluster.device_count == 24

    def test_custom_config(self):
        config = ClusterConfig(buildings={"1": ["101", "102"]})
        cluster = SimulationCluster(config)
        assert cluster.device_count == 2

    def test_generate_all(self):
        cluster = SimulationCluster()
        reports = cluster.generate_all()
        assert len(reports) == cluster.device_count
        for report in reports:
            assert report.device_id.startswith("MOCK_METER_")

    def test_get_device(self):
        cluster = SimulationCluster()
        device = cluster.get_device("MOCK_METER_BLDG5_RM401")
        assert device is not None
        assert device.device_id == "MOCK_METER_BLDG5_RM401"

    def test_get_device_not_found(self):
        cluster = SimulationCluster()
        assert cluster.get_device("NONEXISTENT") is None

    def test_inject_anomaly(self):
        cluster = SimulationCluster()
        result = cluster.inject_anomaly("MOCK_METER_BLDG5_RM401", DeviceStatus.ALARM)
        assert result is True
        device = cluster.get_device("MOCK_METER_BLDG5_RM401")
        assert device.state == DeviceStatus.ALARM

    def test_inject_anomaly_not_found(self):
        cluster = SimulationCluster()
        result = cluster.inject_anomaly("NONEXISTENT", DeviceStatus.ALARM)
        assert result is False

    def test_reset_all(self):
        cluster = SimulationCluster()
        cluster.inject_anomaly("MOCK_METER_BLDG5_RM401", DeviceStatus.ALARM)
        cluster.inject_anomaly("MOCK_METER_BLDG6_RM402", DeviceStatus.WARNING)
        cluster.reset_all()
        for device in cluster.devices.values():
            assert device.state == DeviceStatus.NORMAL

    def test_device_ids_unique(self):
        cluster = SimulationCluster()
        ids = [d.device_id for d in cluster.devices.values()]
        assert len(ids) == len(set(ids))
