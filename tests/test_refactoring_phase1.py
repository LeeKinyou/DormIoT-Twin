"""
阶段一测试：架构断舍离 - 依赖清理与文件删除
"""
import pytest
import subprocess
import sys
from pathlib import Path


def test_docker_compose_deleted():
    """测试 docker-compose.yml 是否已删除"""
    assert not Path("docker-compose.yml").exists(), "docker-compose.yml 应该被删除"


def test_gateway_directory_deleted():
    """测试 gateway 目录是否已删除"""
    assert not Path("src/dormiot/gateway").exists(), "src/dormiot/gateway 目录应该被删除"


def test_storage_directory_deleted():
    """测试 storage 目录是否已删除"""
    assert not Path("src/dormiot/storage").exists(), "src/dormiot/storage 目录应该被删除"


def test_pyproject_toml_updated():
    """测试 pyproject.toml 是否已更新依赖"""
    with open("pyproject.toml", "r", encoding="utf-8") as f:
        content = f.read()

    # 检查旧依赖是否已移除
    assert "paho-mqtt" not in content, "paho-mqtt 依赖应该被移除"
    assert "redis" not in content, "redis 依赖应该被移除"
    assert "sqlalchemy" not in content, "sqlalchemy 依赖应该被移除"
    assert "pymysql" not in content, "pymysql 依赖应该被移除"

    # 检查新依赖是否已添加
    assert "pandas" in content, "pandas 依赖应该被添加"
    assert "numpy" in content, "numpy 依赖应该被添加"
    assert "langchain" in content, "langchain 依赖应该被添加"
    assert "langchain-openai" in content, "langchain-openai 依赖应该被添加"


def test_gateway_module_imports_removed():
    """测试 gateway 模块导入是否已从主代码中移除"""
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    assert "from dormiot.gateway" not in content, "app.py 中不应再导入 gateway 模块"
    assert "import dormiot.gateway" not in content, "app.py 中不应再导入 gateway 模块"


def test_storage_module_imports_removed():
    """测试 storage 模块导入是否已从主代码中移除"""
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    assert "from dormiot.storage" not in content, "app.py 中不应再导入 storage 模块"
    assert "import dormiot.storage" not in content, "app.py 中不应再导入 storage 模块"


def test_remaining_modules_can_be_imported():
    """测试剩余模块是否可以正常导入"""
    # 这些模块应该仍然存在且可以导入
    try:
        import dormiot.schemas
        import dormiot.simulation
        import dormiot.ui
        import dormiot.config
    except ImportError as e:
        pytest.fail(f"剩余模块导入失败: {e}")


def test_new_dependencies_can_be_imported():
    """测试新依赖是否可以正常导入"""
    try:
        import pandas
        import numpy
        import langchain
        import langchain_openai
    except ImportError as e:
        pytest.fail(f"新依赖导入失败: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])