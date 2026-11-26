"""Unit tests for lib_6107.dashboard.elastic_setup."""

import json
from unittest.mock import MagicMock

import pytest
from lib_6107.dashboard.elastic_setup import ELASTIC_LAYOUT_FILE, ELASTIC_LAYOUT_PORT, ElasticDashboardServer

MODULE = "lib_6107.dashboard.elastic_setup"


@pytest.fixture
def deploy(tmp_path, monkeypatch):
    monkeypatch.setattr(f"{MODULE}.get_deploy_directory", lambda: str(tmp_path))
    return tmp_path


@pytest.fixture
def web_server(monkeypatch):
    server = MagicMock()
    monkeypatch.setattr(f"{MODULE}.WebServer.get_instance", lambda: server)
    return server


def test_start_missing_file_returns_none(deploy, web_server):
    srv = ElasticDashboardServer()
    assert srv.start() is None
    web_server.start.assert_not_called()


def test_start_invalid_json_returns_none(deploy, web_server):
    (deploy / ELASTIC_LAYOUT_FILE).write_text("{not json")
    assert ElasticDashboardServer().start() is None
    web_server.start.assert_not_called()


def test_start_valid_layout_starts_server_once(deploy, web_server):
    (deploy / ELASTIC_LAYOUT_FILE).write_text(json.dumps({"tabs": []}))
    srv = ElasticDashboardServer()
    assert srv.start() is web_server
    assert srv.start() is web_server
    web_server.start.assert_called_once_with(ELASTIC_LAYOUT_PORT, str(deploy))


def test_start_server_failure_returns_none(deploy, web_server):
    (deploy / ELASTIC_LAYOUT_FILE).write_text("{}")
    web_server.start.side_effect = RuntimeError("port busy")
    srv = ElasticDashboardServer()
    assert srv.start() is None
    assert srv._elastic_layout_server is None


def test_stop_without_server_is_noop():
    ElasticDashboardServer().stop()


def test_stop_stops_server_and_clears(deploy, web_server):
    (deploy / ELASTIC_LAYOUT_FILE).write_text("{}")
    srv = ElasticDashboardServer()
    srv.start()
    srv.stop()
    web_server.stop.assert_called_once_with(ELASTIC_LAYOUT_PORT)
    assert srv._elastic_layout_server is None


def test_stop_swallows_errors(deploy, web_server):
    (deploy / ELASTIC_LAYOUT_FILE).write_text("{}")
    web_server.stop.side_effect = RuntimeError("fail")
    srv = ElasticDashboardServer()
    srv.start()
    srv.stop()
    assert srv._elastic_layout_server is None


@pytest.mark.parametrize("sim", [True, False])
def test_validate_settings_file(monkeypatch, sim):
    monkeypatch.setattr(f"{MODULE}.RobotBase.is_simulation", staticmethod(lambda: sim))
    assert ElasticDashboardServer().validate_settings_file() is None
