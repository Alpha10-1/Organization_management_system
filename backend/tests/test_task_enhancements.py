from tests.test_new_features import _create_client
from tests.test_projects import _create_project


# --- Subtasks --------------------------------------------------------------


def test_subtask_links_to_parent(admin_client):
    parent = admin_client.post("/tasks/", json={"title": "Parent checklist"}).json()
    child = admin_client.post(
        "/tasks/", json={"title": "Sub-item", "parent_task_id": parent["id"]}
    ).json()
    assert child["parent_task_id"] == parent["id"]

    listed = admin_client.get(f"/tasks/?parent_task_id={parent['id']}").json()
    assert len(listed) == 1
    assert listed[0]["id"] == child["id"]


def test_subtask_rejects_unknown_parent(admin_client):
    resp = admin_client.post("/tasks/", json={"title": "Orphan", "parent_task_id": 999999})
    assert resp.status_code == 404


def test_task_cannot_be_its_own_parent(admin_client):
    task = admin_client.post("/tasks/", json={"title": "Self ref"}).json()
    resp = admin_client.put(f"/tasks/{task['id']}", json={"parent_task_id": task["id"]})
    assert resp.status_code == 400


def test_task_detail_rolls_up_subtasks(admin_client):
    parent = admin_client.post("/tasks/", json={"title": "Parent with subtasks"}).json()
    child_a = admin_client.post(
        "/tasks/", json={"title": "Sub A", "parent_task_id": parent["id"]}
    ).json()
    admin_client.post("/tasks/", json={"title": "Sub B", "parent_task_id": parent["id"]})
    admin_client.put(f"/tasks/{child_a['id']}", json={"status": "done"})

    detail = admin_client.get(f"/tasks/{parent['id']}/detail").json()
    assert detail["subtask_count"] == 2
    assert detail["open_subtask_count"] == 1


# --- Dependencies ------------------------------------------------------


def test_add_and_list_task_dependency(admin_client):
    blocker = admin_client.post("/tasks/", json={"title": "Prep fieldwork"}).json()
    blocked = admin_client.post("/tasks/", json={"title": "Issue report"}).json()

    resp = admin_client.post(
        f"/tasks/{blocked['id']}/dependencies", json={"depends_on_task_id": blocker["id"]}
    )
    assert resp.status_code == 200, resp.text

    detail = admin_client.get(f"/tasks/{blocked['id']}/detail").json()
    assert detail["blocked_by"] == [blocker["id"]]
    assert detail["is_blocked"] is True

    blocker_detail = admin_client.get(f"/tasks/{blocker['id']}/detail").json()
    assert blocker_detail["blocks"] == [blocked["id"]]


def test_task_cannot_depend_on_itself(admin_client):
    task = admin_client.post("/tasks/", json={"title": "Self dependency"}).json()
    resp = admin_client.post(f"/tasks/{task['id']}/dependencies", json={"depends_on_task_id": task["id"]})
    assert resp.status_code == 400


def test_task_dependency_rejects_duplicate(admin_client):
    a = admin_client.post("/tasks/", json={"title": "Task A"}).json()
    b = admin_client.post("/tasks/", json={"title": "Task B"}).json()
    admin_client.post(f"/tasks/{a['id']}/dependencies", json={"depends_on_task_id": b["id"]})

    resp = admin_client.post(f"/tasks/{a['id']}/dependencies", json={"depends_on_task_id": b["id"]})
    assert resp.status_code == 400


def test_task_dependency_rejects_cycle(admin_client):
    a = admin_client.post("/tasks/", json={"title": "Cycle A"}).json()
    b = admin_client.post("/tasks/", json={"title": "Cycle B"}).json()
    c = admin_client.post("/tasks/", json={"title": "Cycle C"}).json()

    admin_client.post(f"/tasks/{a['id']}/dependencies", json={"depends_on_task_id": b["id"]})
    admin_client.post(f"/tasks/{b['id']}/dependencies", json={"depends_on_task_id": c["id"]})

    # c -> a would close the loop a -> b -> c -> a
    resp = admin_client.post(f"/tasks/{c['id']}/dependencies", json={"depends_on_task_id": a["id"]})
    assert resp.status_code == 400


def test_blocked_task_cannot_be_marked_done(admin_client):
    blocker = admin_client.post("/tasks/", json={"title": "Must finish first"}).json()
    blocked = admin_client.post("/tasks/", json={"title": "Waits on blocker"}).json()
    admin_client.post(f"/tasks/{blocked['id']}/dependencies", json={"depends_on_task_id": blocker["id"]})

    resp = admin_client.put(f"/tasks/{blocked['id']}", json={"status": "done"})
    assert resp.status_code == 400

    admin_client.put(f"/tasks/{blocker['id']}", json={"status": "done"})
    resp = admin_client.put(f"/tasks/{blocked['id']}", json={"status": "done"})
    assert resp.status_code == 200


def test_delete_task_dependency(admin_client):
    a = admin_client.post("/tasks/", json={"title": "Dep A"}).json()
    b = admin_client.post("/tasks/", json={"title": "Dep B"}).json()
    dep = admin_client.post(f"/tasks/{a['id']}/dependencies", json={"depends_on_task_id": b["id"]}).json()

    resp = admin_client.delete(f"/tasks/{a['id']}/dependencies/{dep['id']}")
    assert resp.status_code == 200

    detail = admin_client.get(f"/tasks/{a['id']}/detail").json()
    assert detail["blocked_by"] == []


# --- Recurring tasks -----------------------------------------------------


def test_recurring_task_requires_due_date(admin_client):
    resp = admin_client.post(
        "/tasks/", json={"title": "Monthly close", "recurrence_rule": "monthly"}
    )
    assert resp.status_code == 400


def test_completing_recurring_task_spawns_next_occurrence(admin_client):
    task = admin_client.post(
        "/tasks/",
        json={
            "title": "Monthly close",
            "due_date": "2026-01-31T00:00:00",
            "recurrence_rule": "monthly",
        },
    ).json()

    resp = admin_client.put(f"/tasks/{task['id']}", json={"status": "done"})
    assert resp.status_code == 200, resp.text

    listed = admin_client.get("/tasks/?status=open").json()
    clones = [t for t in listed if t["title"] == "Monthly close" and t["id"] != task["id"]]
    assert len(clones) == 1
    assert clones[0]["recurrence_parent_id"] == task["id"]
    assert clones[0]["due_date"] > task["due_date"]


def test_recurring_task_stops_after_end_date(admin_client):
    task = admin_client.post(
        "/tasks/",
        json={
            "title": "Weekly review",
            "due_date": "2026-01-01T00:00:00",
            "recurrence_rule": "weekly",
            "recurrence_end_date": "2026-01-05T00:00:00",
        },
    ).json()

    admin_client.put(f"/tasks/{task['id']}", json={"status": "done"})

    listed = admin_client.get("/tasks/?status=open").json()
    clones = [t for t in listed if t["title"] == "Weekly review"]
    assert clones == []


# --- Milestones ------------------------------------------------------------


def test_create_and_list_milestone(admin_client):
    client = _create_client(admin_client, email="milestone-client@example.com")
    project = _create_project(admin_client, client["id"])

    resp = admin_client.post(
        "/milestones/", json={"project_id": project["id"], "name": "Fieldwork complete"}
    )
    assert resp.status_code == 200, resp.text
    milestone = resp.json()
    assert milestone["status"] == "pending"

    listed = admin_client.get(f"/milestones/?project_id={project['id']}").json()
    assert any(m["id"] == milestone["id"] for m in listed)


def test_milestone_rejects_unknown_project(admin_client):
    resp = admin_client.post("/milestones/", json={"project_id": 999999, "name": "Ghost"})
    assert resp.status_code == 404


def test_milestone_achieved_sets_timestamp(admin_client):
    client = _create_client(admin_client, email="milestone-achieve@example.com")
    project = _create_project(admin_client, client["id"])
    milestone = admin_client.post(
        "/milestones/", json={"project_id": project["id"], "name": "Draft report issued"}
    ).json()

    resp = admin_client.put(f"/milestones/{milestone['id']}", json={"status": "achieved"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "achieved"
    assert body["achieved_at"] is not None


def test_delete_milestone(admin_client):
    client = _create_client(admin_client, email="milestone-delete@example.com")
    project = _create_project(admin_client, client["id"])
    milestone = admin_client.post(
        "/milestones/", json={"project_id": project["id"], "name": "To be removed"}
    ).json()

    resp = admin_client.delete(f"/milestones/{milestone['id']}")
    assert resp.status_code == 200

    listed = admin_client.get(f"/milestones/?project_id={project['id']}").json()
    assert all(m["id"] != milestone["id"] for m in listed)


# --- Task templates ------------------------------------------------------


def test_create_template_and_apply_to_project(admin_client):
    client = _create_client(admin_client, email="template-client@example.com")
    project = _create_project(admin_client, client["id"], start_date="2026-02-01T00:00:00")

    resp = admin_client.post(
        "/task-templates/",
        json={
            "name": "Audit Kickoff Checklist",
            "engagement_type": "audit",
            "items": [
                {"title": "Send engagement letter", "relative_due_days": 0, "order_index": 0},
                {"title": "Schedule kickoff call", "relative_due_days": 3, "order_index": 1},
                {"title": "Request PBC list", "relative_due_days": 7, "order_index": 2},
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    template = resp.json()
    assert len(template["items"]) == 3

    resp = admin_client.post(
        f"/task-templates/{template['id']}/apply", json={"project_id": project["id"]}
    )
    assert resp.status_code == 200, resp.text
    created_tasks = resp.json()
    assert len(created_tasks) == 3
    assert {t["title"] for t in created_tasks} == {
        "Send engagement letter",
        "Schedule kickoff call",
        "Request PBC list",
    }
    for task in created_tasks:
        assert task["project_id"] == project["id"]
        assert task["client_id"] == client["id"]

    listed = admin_client.get(f"/tasks/?project_id={project['id']}").json()
    assert len(listed) == 3


def test_apply_template_rejects_unknown_project(admin_client):
    template = admin_client.post(
        "/task-templates/",
        json={"name": "Generic checklist", "items": [{"title": "Step 1"}]},
    ).json()

    resp = admin_client.post(
        f"/task-templates/{template['id']}/apply", json={"project_id": 999999}
    )
    assert resp.status_code == 404


def test_apply_empty_template_rejected(admin_client):
    client = _create_client(admin_client, email="empty-template@example.com")
    project = _create_project(admin_client, client["id"])
    template = admin_client.post("/task-templates/", json={"name": "Empty template", "items": []}).json()

    resp = admin_client.post(
        f"/task-templates/{template['id']}/apply", json={"project_id": project["id"]}
    )
    assert resp.status_code == 400


def test_list_templates_filters_by_engagement_type(admin_client):
    admin_client.post("/task-templates/", json={"name": "Audit list", "engagement_type": "audit", "items": []})
    admin_client.post("/task-templates/", json={"name": "Tax list", "engagement_type": "tax", "items": []})

    audit_only = admin_client.get("/task-templates/?engagement_type=audit").json()
    assert all(t["engagement_type"] == "audit" for t in audit_only)
    assert any(t["name"] == "Audit list" for t in audit_only)
