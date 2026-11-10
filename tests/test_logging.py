# request logging middleware emits one structured line per request


def test_request_log_has_structured_fields(client, caplog):
    caplog.set_level("INFO")
    resp = client.get("/")
    assert resp.status_code == 200

    records = [r for r in caplog.records if getattr(r, "request_id", None)]
    assert records, "expected a request log record"

    record = records[0]
    assert record.method == "GET"
    assert record.path == "/"
    assert record.status_code == 200
    assert isinstance(record.duration_ms, (int, float))
    assert record.client_ip
    assert record.request_id
