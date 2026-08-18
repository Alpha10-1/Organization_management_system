import uuid

from tests.test_department_kpis import _create_user


def test_create_skill_entry(admin_client):
    user = _create_user(admin_client)
    resp = admin_client.post(
        "/skills/",
        json={"user_id": user["id"], "name": "Python", "category": "skill", "proficiency_level": "advanced"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "Python"
    assert body["proficiency_level"] == "advanced"


def test_create_certification_entry(admin_client):
    user = _create_user(admin_client)
    resp = admin_client.post(
        "/skills/",
        json={
            "user_id": user["id"],
            "name": "CPA",
            "category": "certification",
            "issued_date": "2022-01-01",
            "expiry_date": "2026-12-31",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["category"] == "certification"


def test_create_skill_rejects_invalid_category(admin_client):
    user = _create_user(admin_client)
    resp = admin_client.post("/skills/", json={"user_id": user["id"], "name": "X", "category": "hobby"})
    assert resp.status_code == 400


def test_create_skill_rejects_invalid_proficiency(admin_client):
    user = _create_user(admin_client)
    resp = admin_client.post(
        "/skills/", json={"user_id": user["id"], "name": "X", "proficiency_level": "godlike"}
    )
    assert resp.status_code == 400


def test_create_skill_rejects_unknown_user(admin_client):
    resp = admin_client.post("/skills/", json={"user_id": 999999, "name": "X"})
    assert resp.status_code == 404


def test_list_skills_filters_by_user(admin_client):
    user_a = _create_user(admin_client)
    user_b = _create_user(admin_client)
    admin_client.post("/skills/", json={"user_id": user_a["id"], "name": "Excel"})
    admin_client.post("/skills/", json={"user_id": user_b["id"], "name": "SQL"})

    resp = admin_client.get(f"/skills/?user_id={user_a['id']}")
    results = resp.json()
    assert len(results) == 1
    assert results[0]["name"] == "Excel"


def test_skills_expiring_within_days(admin_client):
    user = _create_user(admin_client)
    admin_client.post(
        "/skills/",
        json={
            "user_id": user["id"],
            "name": "Soon-to-expire cert",
            "category": "certification",
            "expiry_date": "2026-08-20",
        },
    )
    admin_client.post(
        "/skills/",
        json={
            "user_id": user["id"],
            "name": "Far-future cert",
            "category": "certification",
            "expiry_date": "2030-01-01",
        },
    )

    resp = admin_client.get("/skills/?expiring_within_days=30")
    names = {s["name"] for s in resp.json()}
    assert "Soon-to-expire cert" in names
    assert "Far-future cert" not in names


def test_skills_matrix_groups_by_user(admin_client):
    user = _create_user(admin_client)
    admin_client.post("/skills/", json={"user_id": user["id"], "name": "Audit sampling"})

    resp = admin_client.get("/skills/matrix")
    assert resp.status_code == 200, resp.text
    entry = next(e for e in resp.json() if e["user_id"] == user["id"])
    assert any(s["name"] == "Audit sampling" for s in entry["skills"])


def test_skills_matrix_filters_by_department(admin_client):
    from tests.test_department_kpis import _create_department

    dept = _create_department(admin_client)
    in_dept_user = _create_user(admin_client, department_id=dept["id"])
    _create_user(admin_client)  # not in dept

    resp = admin_client.get(f"/skills/matrix?department_id={dept['id']}")
    user_ids = {e["user_id"] for e in resp.json()}
    assert in_dept_user["id"] in user_ids


def test_skills_matrix_name_filter_only_returns_matches(admin_client):
    user = _create_user(admin_client)
    admin_client.post("/skills/", json={"user_id": user["id"], "name": "Tableau"})

    resp = admin_client.get("/skills/matrix?name=Tableau")
    entries = resp.json()
    assert all(e["skills"] for e in entries)
    assert any(s["name"] == "Tableau" for e in entries for s in e["skills"])


def test_update_and_delete_skill(admin_client):
    user = _create_user(admin_client)
    skill = admin_client.post("/skills/", json={"user_id": user["id"], "name": "Draft skill"}).json()

    resp = admin_client.put(f"/skills/{skill['id']}", json={"proficiency_level": "expert"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["proficiency_level"] == "expert"

    resp = admin_client.delete(f"/skills/{skill['id']}")
    assert resp.status_code == 200

    resp = admin_client.get(f"/skills/{skill['id']}")
    assert resp.status_code == 404
