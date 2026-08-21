from datetime import date as date_type, timedelta

from tests.test_new_features import _create_client
from tests.test_projects import _create_project
from tests.test_time_entries import _create_time_entry


def _next_or_same_friday(from_date: date_type) -> date_type:
    d = from_date
    while d.weekday() != 4:
        d += timedelta(days=1)
    return d


def test_no_anomalies_for_ordinary_entries(admin_client):
    client = _create_client(admin_client, email="anomaly-clean@example.com")
    project = _create_project(admin_client, client["id"])
    _create_time_entry(admin_client, project["id"], hours="2.5", entry_date=str(date_type.today()))

    resp = admin_client.get(f"/time-entries/anomalies?project_id={project['id']}")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_late_logged_entry_is_flagged(admin_client):
    client = _create_client(admin_client, email="anomaly-late@example.com")
    project = _create_project(admin_client, client["id"])

    stale_date = date_type.today() - timedelta(days=30)
    entry = _create_time_entry(admin_client, project["id"], hours="3.0", entry_date=str(stale_date))

    resp = admin_client.get(f"/time-entries/anomalies?project_id={project['id']}")
    assert resp.status_code == 200, resp.text
    findings = resp.json()
    assert len(findings) == 1
    assert findings[0]["time_entry_id"] == entry["id"]
    assert "late_logged" in findings[0]["flags"]


def test_friday_large_block_is_flagged(admin_client):
    client = _create_client(admin_client, email="anomaly-friday@example.com")
    project = _create_project(admin_client, client["id"])

    friday = _next_or_same_friday(date_type.today())
    entry = _create_time_entry(admin_client, project["id"], hours="7.0", entry_date=str(friday))

    resp = admin_client.get(f"/time-entries/anomalies?project_id={project['id']}")
    findings = resp.json()
    matches = [f for f in findings if f["time_entry_id"] == entry["id"]]
    assert len(matches) == 1
    assert "friday_large_block" in matches[0]["flags"]


def test_small_friday_entry_not_flagged(admin_client):
    client = _create_client(admin_client, email="anomaly-friday-small@example.com")
    project = _create_project(admin_client, client["id"])

    friday = _next_or_same_friday(date_type.today())
    _create_time_entry(admin_client, project["id"], hours="1.5", entry_date=str(friday))

    resp = admin_client.get(f"/time-entries/anomalies?project_id={project['id']}")
    assert resp.json() == []


def test_duplicate_entries_are_flagged(admin_client):
    client = _create_client(admin_client, email="anomaly-dupe@example.com")
    project = _create_project(admin_client, client["id"])
    same_date = str(date_type.today())

    e1 = _create_time_entry(admin_client, project["id"], hours="3.25", entry_date=same_date)
    e2 = _create_time_entry(admin_client, project["id"], hours="3.25", entry_date=same_date)

    resp = admin_client.get(f"/time-entries/anomalies?project_id={project['id']}")
    findings = {f["time_entry_id"]: f for f in resp.json()}
    assert e1["id"] in findings
    assert e2["id"] in findings
    assert "possible_duplicate" in findings[e1["id"]]["flags"]
    assert "possible_duplicate" in findings[e2["id"]]["flags"]


def test_round_number_repeat_pattern_is_flagged(admin_client):
    client = _create_client(admin_client, email="anomaly-round@example.com")
    project = _create_project(admin_client, client["id"])

    entry_ids = []
    for i in range(3):
        e = _create_time_entry(
            admin_client, project["id"], hours="8.00", entry_date=str(date_type.today() - timedelta(days=i * 3))
        )
        entry_ids.append(e["id"])

    resp = admin_client.get(f"/time-entries/anomalies?project_id={project['id']}")
    findings = {f["time_entry_id"]: f for f in resp.json()}
    for eid in entry_ids:
        assert "round_number_pattern" in findings[eid]["flags"]


def test_two_round_entries_below_threshold_not_flagged_for_that_rule(admin_client):
    client = _create_client(admin_client, email="anomaly-round-few@example.com")
    project = _create_project(admin_client, client["id"])

    # Pick a non-Friday date so this doesn't collide with the
    # friday_large_block rule (8h qualifies for that one too).
    base = date_type.today()
    while base.weekday() == 4:
        base -= timedelta(days=1)

    e1 = _create_time_entry(admin_client, project["id"], hours="8.00", entry_date=str(base))
    e2 = _create_time_entry(admin_client, project["id"], hours="8.00", entry_date=str(base - timedelta(days=3)))

    resp = admin_client.get(f"/time-entries/anomalies?project_id={project['id']}")
    findings = {f["time_entry_id"]: f for f in resp.json()}
    # Below ROUND_REPEAT_THRESHOLD (3), so no round_number_pattern flag --
    # and nothing else about these two entries should trigger a flag.
    assert e1["id"] not in findings
    assert e2["id"] not in findings


def test_anomalies_scoped_to_project(admin_client):
    client = _create_client(admin_client, email="anomaly-scope@example.com")
    project_a = _create_project(admin_client, client["id"], name="Engagement A")
    project_b = _create_project(admin_client, client["id"], name="Engagement B")

    stale_date = date_type.today() - timedelta(days=30)
    entry_a = _create_time_entry(admin_client, project_a["id"], hours="3.0", entry_date=str(stale_date))
    _create_time_entry(admin_client, project_b["id"], hours="3.0", entry_date=str(stale_date))

    resp = admin_client.get(f"/time-entries/anomalies?project_id={project_a['id']}")
    findings = resp.json()
    assert len(findings) == 1
    assert findings[0]["time_entry_id"] == entry_a["id"]


def test_non_admin_limited_to_own_entries(staff_client, admin_client):
    client = _create_client(admin_client, email="anomaly-staff-scope@example.com")
    project = _create_project(admin_client, client["id"])

    stale_date = date_type.today() - timedelta(days=30)
    # Logged by admin, not staff.
    _create_time_entry(admin_client, project["id"], hours="3.0", entry_date=str(stale_date))

    resp = staff_client.get(f"/time-entries/anomalies?project_id={project['id']}")
    assert resp.status_code == 200, resp.text
    # Staff is forced to their own entries regardless of user_email filter,
    # so admin's flagged entry should not appear.
    assert resp.json() == []


def test_firm_wide_report_visible_to_any_authenticated_user(staff_client, admin_client):
    """Unrestricted for any authenticated user, matching every other
    firm-wide report in this file -- not gated to admins."""
    client = _create_client(admin_client, email="anomaly-report@example.com")
    project = _create_project(admin_client, client["id"])
    stale_date = date_type.today() - timedelta(days=30)
    entry = _create_time_entry(admin_client, project["id"], hours="3.0", entry_date=str(stale_date))

    resp = staff_client.get("/reports/time-entry-anomalies")
    assert resp.status_code == 200, resp.text
    ids = [f["time_entry_id"] for f in resp.json()]
    assert entry["id"] in ids
