from concurrent.futures import ThreadPoolExecutor
from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from app.utils import neo4j_client as module


@pytest.fixture
def driver(monkeypatch: pytest.MonkeyPatch) -> Iterator[MagicMock]:
    module.close_neo4j_client()
    monkeypatch.setenv("NEO4J_URI", "neo4j+s://example.databases.neo4j.io")
    monkeypatch.setenv("NEO4J_USER", "test")
    monkeypatch.setenv("NEO4J_PASSWORD", "test-only")
    monkeypatch.setenv("POLYMERGE_REQUIRE_NEO4J_TLS", "true")
    factory = MagicMock()
    monkeypatch.setattr(module.GraphDatabase, "driver", factory)
    yield factory
    module.close_neo4j_client()


def test_concurrent_requests_share_one_bounded_driver_and_restart_closes_it(driver: MagicMock) -> None:
    with ThreadPoolExecutor(max_workers=8) as pool:
        clients = list(pool.map(lambda _: module.get_neo4j_client(), range(24)))
    assert all(client is clients[0] for client in clients)
    assert driver.call_count == 1
    assert driver.call_args.kwargs["max_connection_pool_size"] == 10
    assert driver.call_args.kwargs["connection_acquisition_timeout"] == 5
    module.close_neo4j_client()
    driver.return_value.close.assert_called_once()
    assert module.get_neo4j_client() is not clients[0]
    assert driver.call_count == 2


@pytest.mark.parametrize("uri", ["bolt://example:7687", "neo4j://example", "neo4j+ssc://example", "neo4j+s://user:secret@example"])
def test_cloud_graph_rejects_insecure_or_embedded_credentials(driver: MagicMock, uri: str) -> None:
    with pytest.raises(module.Neo4jConnectionError, match="certificate-verified"):
        module.Neo4jClient(uri=uri)
    driver.assert_not_called()


def test_graph_reads_are_parameterized_and_time_bounded(driver: MagicMock) -> None:
    client = module.get_neo4j_client()
    client.query("RETURN $value AS value", value="untrusted")
    run = driver.return_value.session.return_value.__enter__.return_value.run
    query = run.call_args.args[0]
    assert query.text == "RETURN $value AS value"
    assert query.timeout == 30
    assert run.call_args.kwargs == {"value": "untrusted"}
