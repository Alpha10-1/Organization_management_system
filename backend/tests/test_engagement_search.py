from tests.test_new_features import _create_client
from tests.test_projects import _create_project


def test_search_matches_known_phrase_in_project_notes(admin_client):
    client = _create_client(admin_client, email="search-phrase@example.com")
    project = _create_project(
        admin_client,
        client["id"],
        close_out_notes="During fieldwork we identified a going concern issue related to liquidity.",
    )

    resp = admin_client.get("/search/engagements?q=show me every engagement where we flagged a going concern issue")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "going concern" in body["phrases"]
    ids = [r["project_id"] for r in body["results"]]
    assert project["id"] in ids
    matched = next(r for r in body["results"] if r["project_id"] == project["id"])
    assert "going concern" in matched["matched_terms"]
    assert any("close_out_notes" in s for s in matched["snippets"])


def test_search_matches_client_notes(admin_client):
    client = _create_client(admin_client, email="search-clientnote@example.com")
    project = _create_project(admin_client, client["id"])

    resp = admin_client.post(f"/clients/{client['id']}/notes", json={"body": "Flagged a related party transaction with the CFO's spouse's company."})
    assert resp.status_code == 200, resp.text

    resp = admin_client.get("/search/engagements?q=related party transaction")
    assert resp.status_code == 200, resp.text
    ids = [r["project_id"] for r in resp.json()["results"]]
    assert project["id"] in ids


def test_search_matches_activity_log(admin_client):
    client = _create_client(admin_client, email="search-activity@example.com")
    project = _create_project(admin_client, client["id"])

    # Editing the project generates an activity log entry via log_activity.
    resp = admin_client.put(
        f"/projects/{project['id']}",
        json={"description": "Noted a significant deficiency in revenue recognition controls."},
    )
    assert resp.status_code == 200, resp.text

    resp = admin_client.get("/search/engagements?q=significant deficiency")
    assert resp.status_code == 200, resp.text
    ids = [r["project_id"] for r in resp.json()["results"]]
    assert project["id"] in ids


def test_search_ranks_more_matching_terms_higher(admin_client):
    client = _create_client(admin_client, email="search-rank@example.com")
    strong = _create_project(
        admin_client,
        client["id"],
        name="Strong Match Engagement",
        close_out_notes="Going concern issue and a related party transaction were both noted.",
    )
    weak = _create_project(
        admin_client,
        client["id"],
        name="Weak Match Engagement",
        close_out_notes="A related party transaction was noted.",
    )

    resp = admin_client.get("/search/engagements?q=going concern related party transaction")
    assert resp.status_code == 200, resp.text
    results = resp.json()["results"]
    ids = [r["project_id"] for r in results]
    assert ids.index(strong["id"]) < ids.index(weak["id"])


def test_search_no_matches_returns_empty_results(admin_client):
    resp = admin_client.get("/search/engagements?q=zzz nonexistent gibberish term")
    assert resp.status_code == 200, resp.text
    assert resp.json()["results"] == []


def test_search_ignores_stopword_only_query(admin_client):
    client = _create_client(admin_client, email="search-stopwords@example.com")
    _create_project(admin_client, client["id"], close_out_notes="Something noteworthy happened.")

    resp = admin_client.get("/search/engagements?q=show me every engagement")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["terms"] == []
    assert body["phrases"] == []
    assert body["results"] == []
