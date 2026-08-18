from tests.test_department_kpis import _create_department, _create_user


def _create_onboarding_template(admin_client, **overrides):
    payload = {
        "name": "New Hire Onboarding",
        "trigger_event": "onboarding",
        "items": [
            {"title": "Set up laptop", "relative_due_days": 0},
            {"title": "Complete compliance training", "relative_due_days": 5},
            {"title": "Meet the team", "relative_due_days": 1},
        ],
    }
    payload.update(overrides)
    resp = admin_client.post("/task-templates/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_create_onboarding_template(admin_client):
    template = _create_onboarding_template(admin_client)
    assert template["trigger_event"] == "onboarding"
    assert len(template["items"]) == 3


def test_create_template_rejects_invalid_trigger_event(admin_client):
    resp = admin_client.post(
        "/task-templates/", json={"name": "Bad trigger", "trigger_event": "vacation", "items": []}
    )
    assert resp.status_code == 400


def test_department_scoped_template(admin_client):
    department = _create_department(admin_client)
    template = _create_onboarding_template(admin_client, name="Tax Onboarding", department_id=department["id"])

    resp = admin_client.get(f"/task-templates/?department_id={department['id']}")
    names = {t["name"] for t in resp.json()}
    assert "Tax Onboarding" in names


def test_apply_onboarding_template_to_user_creates_tasks(admin_client):
    template = _create_onboarding_template(admin_client)
    new_hire = _create_user(admin_client)

    resp = admin_client.post(
        f"/task-templates/{template['id']}/apply-to-user",
        json={"user_email": new_hire["email"], "anchor_date": "2026-09-01T00:00:00"},
    )
    assert resp.status_code == 200, resp.text
    tasks = resp.json()
    assert len(tasks) == 3
    assert all(t["assigned_to_email"] == new_hire["email"] for t in tasks)
    assert all(t["project_id"] is None for t in tasks)

    laptop_task = next(t for t in tasks if t["title"] == "Set up laptop")
    assert laptop_task["due_date"].startswith("2026-09-01")

    training_task = next(t for t in tasks if t["title"] == "Complete compliance training")
    assert training_task["due_date"].startswith("2026-09-06")


def test_apply_offboarding_template_to_user(admin_client):
    template = _create_onboarding_template(
        admin_client,
        name="Departure Checklist",
        trigger_event="offboarding",
        items=[{"title": "Revoke system access", "relative_due_days": 0}],
    )
    departing_user = _create_user(admin_client)

    resp = admin_client.post(
        f"/task-templates/{template['id']}/apply-to-user", json={"user_email": departing_user["email"]}
    )
    assert resp.status_code == 200, resp.text
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Revoke system access"


def test_apply_template_to_unknown_user_fails(admin_client):
    template = _create_onboarding_template(admin_client)
    resp = admin_client.post(
        f"/task-templates/{template['id']}/apply-to-user", json={"user_email": "ghost@example.com"}
    )
    assert resp.status_code == 404


def test_apply_unknown_template_to_user_fails(admin_client):
    new_hire = _create_user(admin_client)
    resp = admin_client.post(
        "/task-templates/999999/apply-to-user", json={"user_email": new_hire["email"]}
    )
    assert resp.status_code == 404


def test_apply_empty_template_fails(admin_client):
    template = _create_onboarding_template(admin_client, name="Empty Template", items=[])
    new_hire = _create_user(admin_client)

    resp = admin_client.post(
        f"/task-templates/{template['id']}/apply-to-user", json={"user_email": new_hire["email"]}
    )
    assert resp.status_code == 400
