import pytest
from sprintalis_api.core.config import settings

LIMIT = 2


@pytest.fixture(autouse=True)
def small_workspace_limit(monkeypatch):
    monkeypatch.setattr(settings, "max_owned_workspaces", LIMIT)


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def create(client, user, name: str):
    return await client.post(
        "/api/v1/workspaces",
        json={"name": name},
        headers=auth_header(user["access_token"]),
    )


def error_detail(resp) -> dict:
    body = resp.json()
    return body.get("detail", body)


async def test_can_create_up_to_limit(client, registered_user):
    for i in range(LIMIT):
        resp = await create(client, registered_user, f"Within Limit {i}")
        assert resp.status_code == 201


async def test_creating_past_limit_returns_403(client, registered_user):
    for i in range(LIMIT):
        await create(client, registered_user, f"Fill {i}")

    resp = await create(client, registered_user, "One Too Many")

    assert resp.status_code == 403
    assert error_detail(resp)["code"] == "WORKSPACE_LIMIT_REACHED"


async def test_rejected_create_leaves_no_workspace_behind(client, registered_user):
    for i in range(LIMIT):
        await create(client, registered_user, f"Fill {i}")
    await create(client, registered_user, "Rejected")

    resp = await client.get(
        "/api/v1/workspaces",
        headers=auth_header(registered_user["access_token"]),
    )
    names = [w["name"] for w in resp.json()["workspaces"]]
    assert len(names) == LIMIT
    assert "Rejected" not in names


async def test_deleting_a_workspace_frees_a_slot(client, registered_user):
    created = []
    for i in range(LIMIT):
        resp = await create(client, registered_user, f"Slot {i}")
        created.append(resp.json()["id"])

    blocked = await create(client, registered_user, "Blocked")
    assert blocked.status_code == 403

    await client.delete(
        f"/api/v1/workspaces/{created[0]}",
        headers=auth_header(registered_user["access_token"]),
    )

    resp = await create(client, registered_user, "After Delete")
    assert resp.status_code == 201


async def test_limit_is_per_user(client, registered_user, second_user):
    for i in range(LIMIT):
        await create(client, registered_user, f"User A {i}")

    resp = await create(client, second_user, "User B First")

    assert resp.status_code == 201
