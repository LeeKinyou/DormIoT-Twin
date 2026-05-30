from dormiot.schemas.device import DeviceStatus
from dormiot.simulation.state_machine import DeviceStateMachine


class TestDeviceStateMachine:
    def test_initial_state_is_normal(self):
        sm = DeviceStateMachine()
        assert sm.state == DeviceStatus.NORMAL

    def test_normal_to_warning(self):
        sm = DeviceStateMachine()
        sm.update_signals(warning=True)
        sm.tick()
        assert sm.state == DeviceStatus.WARNING

    def test_normal_to_alarm(self):
        sm = DeviceStateMachine()
        sm.update_signals(alarm=True)
        sm.tick()
        assert sm.state == DeviceStatus.ALARM

    def test_warning_to_alarm(self):
        sm = DeviceStateMachine()
        sm.update_signals(warning=True)
        sm.tick()
        assert sm.state == DeviceStatus.WARNING
        sm.update_signals(alarm=True)
        sm.tick()
        assert sm.state == DeviceStatus.ALARM

    def test_warning_to_normal(self):
        sm = DeviceStateMachine()
        sm.update_signals(warning=True)
        sm.tick()
        assert sm.state == DeviceStatus.WARNING
        sm.update_signals(warning=False, alarm=False)
        sm.tick()
        assert sm.state == DeviceStatus.NORMAL

    def test_alarm_to_normal(self):
        sm = DeviceStateMachine()
        sm.update_signals(alarm=True)
        sm.tick()
        assert sm.state == DeviceStatus.ALARM
        sm.update_signals(alarm=False)
        sm.tick()
        assert sm.state == DeviceStatus.NORMAL

    def test_force_state(self):
        sm = DeviceStateMachine()
        sm.force_state(DeviceStatus.ALARM)
        assert sm.state == DeviceStatus.ALARM

    def test_reset(self):
        sm = DeviceStateMachine()
        sm.force_state(DeviceStatus.ALARM)
        sm.reset()
        assert sm.state == DeviceStatus.NORMAL

    def test_stays_normal_without_signal(self):
        sm = DeviceStateMachine()
        sm.tick()
        assert sm.state == DeviceStatus.NORMAL
        sm.tick()
        assert sm.state == DeviceStatus.NORMAL
