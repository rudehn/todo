from datetime import date, timedelta


def _oil_change(due: str = "2026-08-01") -> dict:
    return {
        "title": "Oil change",
        "notes": "0W-20 full synthetic, 4.4 qt\nFilter: Toyota 04152-YZZA6",
        "category": "Car",
        "due_date": due,
        "remind_days_before": 7,
        "recurrence": {"interval": 6, "unit": "month", "mode": "completion"},
        "checklist": [
            {"text": "Buy oil and filter"},
            {"text": "Reset maintenance light"},
        ],
    }


async def test_create_and_get_task(client):
    resp = await client.post("/api/tasks", json=_oil_change())
    assert resp.status_code == 201
    task = resp.json()
    assert task["title"] == "Oil change"
    assert task["category"] == "car"  # normalized to lowercase
    assert task["recurrence"] == {"interval": 6, "unit": "month", "mode": "completion"}
    assert task["series_id"] == task["id"]
    assert [i["text"] for i in task["checklist"]] == [
        "Buy oil and filter",
        "Reset maintenance light",
    ]

    got = (await client.get(f"/api/tasks/{task['id']}")).json()
    assert got == task


async def test_recurring_task_requires_due_date(client):
    body = _oil_change()
    body["due_date"] = None
    resp = await client.post("/api/tasks", json=body)
    assert resp.status_code == 422


async def test_list_orders_by_due_date_and_filters_category(client):
    await client.post("/api/tasks", json={"title": "Someday", "due_date": None})
    await client.post(
        "/api/tasks", json={"title": "Later", "due_date": "2026-09-01"}
    )
    await client.post(
        "/api/tasks",
        json={"title": "Soon", "due_date": "2026-07-20", "category": "House"},
    )

    titles = [t["title"] for t in (await client.get("/api/tasks")).json()]
    assert titles == ["Soon", "Later", "Someday"]

    house = (await client.get("/api/tasks", params={"category": "house"})).json()
    assert [t["title"] for t in house] == ["Soon"]

    cats = (await client.get("/api/tasks/categories")).json()
    assert cats == ["house"]


async def test_update_replaces_fields_and_checklist(client):
    task = (await client.post("/api/tasks", json=_oil_change())).json()
    body = _oil_change()
    body["title"] = "Oil & filter change"
    body["recurrence"] = None
    body["checklist"] = [{"text": "Only step", "done": True}]
    updated = (
        await client.put(f"/api/tasks/{task['id']}", json=body)
    ).json()
    assert updated["title"] == "Oil & filter change"
    assert updated["recurrence"] is None
    assert [(i["text"], i["done"]) for i in updated["checklist"]] == [
        ("Only step", True)
    ]


async def test_complete_recurring_spawns_next_occurrence(client):
    task = (await client.post("/api/tasks", json=_oil_change())).json()
    resp = await client.post(f"/api/tasks/{task['id']}/complete")
    assert resp.status_code == 200
    body = resp.json()
    assert body["completed"]["completed_at"] is not None

    nxt = body["next"]
    assert nxt is not None
    assert nxt["id"] != task["id"]
    assert nxt["series_id"] == task["id"]
    # completion mode: 6 months from today
    today = date.today()
    got_due = date.fromisoformat(nxt["due_date"])
    assert timedelta(days=175) < (got_due - today) < timedelta(days=190)
    # checklist copied with done reset
    assert all(not i["done"] for i in nxt["checklist"])

    # Completing again conflicts.
    assert (await client.post(f"/api/tasks/{task['id']}/complete")).status_code == 409

    # History of the new occurrence shows the completed one.
    history = (await client.get(f"/api/tasks/{nxt['id']}/history")).json()
    assert [t["id"] for t in history] == [task["id"]]


async def test_complete_non_recurring_has_no_next(client):
    task = (
        await client.post("/api/tasks", json={"title": "Fix fence", "due_date": None})
    ).json()
    body = (await client.post(f"/api/tasks/{task['id']}/complete")).json()
    assert body["next"] is None
    open_titles = [t["title"] for t in (await client.get("/api/tasks")).json()]
    assert open_titles == []


async def test_reopen_recurring_removes_spawned_occurrence(client):
    task = (await client.post("/api/tasks", json=_oil_change())).json()
    spawned = (await client.post(f"/api/tasks/{task['id']}/complete")).json()["next"]

    resp = await client.post(f"/api/tasks/{task['id']}/reopen")
    assert resp.status_code == 200
    assert resp.json()["completed_at"] is None

    # The auto-spawned next occurrence is gone; the original is open again.
    assert (await client.get(f"/api/tasks/{spawned['id']}")).status_code == 404
    open_ids = [t["id"] for t in (await client.get("/api/tasks")).json()]
    assert open_ids == [task["id"]]


async def test_toggle_checklist_item(client):
    task = (await client.post("/api/tasks", json=_oil_change())).json()
    item = task["checklist"][0]
    updated = (
        await client.patch(
            f"/api/tasks/{task['id']}/checklist/{item['id']}", json={"done": True}
        )
    ).json()
    assert updated["checklist"][0]["done"] is True

    resp = await client.patch(
        f"/api/tasks/{task['id']}/checklist/99999", json={"done": True}
    )
    assert resp.status_code == 404


async def test_delete_task(client):
    task = (await client.post("/api/tasks", json=_oil_change())).json()
    assert (await client.delete(f"/api/tasks/{task['id']}")).status_code == 204
    assert (await client.get(f"/api/tasks/{task['id']}")).status_code == 404
