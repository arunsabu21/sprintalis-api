import uuid
import pytest


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def create_workspace(client, user, name: str) -> dict:
    resp = await client.post(
        "/api/v1/workspaces",
        json={"name": name},
        headers=auth_header(user["access_token"]),
    )
    assert resp.status_code == 201
    return resp.json()


async def rename(client, user, workspace_id: str, payload: dict):
    return await client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        json=payload,
        headers=auth_header(user["access_token"]),
    )


async def test_owner_can_rename_workspace(client, registered_user):
    workspace = await create_workspace(client, registered_user, "Old Name")
    resp = await rename(client, registered_user, workspace["id"], {"name": "New Name"})

    assert resp.status_code == 200
    assert resp.json()["id"] == workspace["id"]
    assert resp.json()["name"] == "New Name"


async def test_rename_persists(client, registered_user):
    workspace = await create_workspace(client, registered_user, "Before Rename")
    await rename(client, registered_user, workspace["id"], {"name": "After Rename"})

    resp = await client.get(
        f"/api/v1/workspaces/{workspace['id']}",
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.json()["name"] == "After Rename"


async def test_rename_keeps_slug_unchanged(client, registered_user):
    workspace = await create_workspace(client, registered_user, "Stable Slug")
    resp = await rename(
        client, registered_user, workspace["id"], {"name": "Totally Different"}
    )

    assert resp.json()["slug"] == workspace["slug"]


async def test_rename_updates_updated_at(client, registered_user):
    workspace = await create_workspace(client, registered_user, "Timestamp Test")
    resp = await rename(
        client, registered_user, workspace["id"], {"name": "Timestamp Renamed"}
    )

    assert resp.json()["updated_at"] != workspace["updated_at"]
    assert resp.json()["created_at"] == workspace["created_at"]


async def test_rename_trims_whitespace(client, registered_user):
    workspace = await create_workspace(client, registered_user, "Trim Test")
    resp = await rename(
        client, registered_user, workspace["id"], {"name": "  Trimmed  "}
    )

    assert resp.status_code == 200
    assert resp.json()["name"] == "Trimmed"


async def test_rename_to_same_name_succeeds(client, registered_user):
    workspace = await create_workspace(client, registered_user, "Same Name")

    resp = await rename(client, registered_user, workspace["id"], {"name": "Same Name"})

    assert resp.status_code == 200


async def test_client_cannot_change_slug_via_rename(client, registered_user):
    workspace = await create_workspace(client, registered_user, "Slug Injection")

    resp = await rename(
        client,
        registered_user,
        workspace["id"],
        {"name": "Slug Injection Renamed", "slug": "hacked-slug"},
    )

    assert resp.status_code == 200
    assert resp.json()["slug"] == workspace["slug"]


async def test_rename_response_shape(client, registered_user):
    workspace = await create_workspace(client, registered_user, "Shape Rename")

    resp = await rename(
        client, registered_user, workspace["id"], {"name": "Shape Renamed"}
    )

    assert set(resp.json().keys()) == {"id", "name", "slug", "created_at", "updated_at"}


@pytest.mark.parametrize("bad_name", ["", "   ", "!!!", "x" * 256])
async def test_rename_invalid_name_returns_422(client, registered_user, bad_name):
    workspace = await create_workspace(client, registered_user, "Valid Name")

    resp = await rename(client, registered_user, workspace["id"], {"name": bad_name})

    assert resp.status_code == 422


async def test_rename_missing_name_returns_422(client, registered_user):
    workspace = await create_workspace(client, registered_user, "Missing Name")

    resp = await rename(client, registered_user, workspace["id"], {})

    assert resp.status_code == 422


async def test_non_member_cannot_rename_workspace(client, registered_user, second_user):
    workspace = await create_workspace(client, registered_user, "Not Yours To Rename")

    resp = await rename(client, second_user, workspace["id"], {"name": "Stolen"})
    assert resp.status_code == 404

    unchanged = await client.get(
        f"/api/v1/workspaces/{workspace['id']}",
        headers=auth_header(registered_user["access_token"]),
    )
    assert unchanged.json()["name"] == "Not Yours To Rename"


async def test_rename_workspace_no_auth_fails(client, registered_user):
    workspace = await create_workspace(client, registered_user, "No Auth Rename")

    resp = await client.patch(
        f"/api/v1/workspaces/{workspace['id']}", json={"name": "Nope"}
    )
    assert resp.status_code == 401


async def test_rename_nonexistent_workspace_returns_404(client, registered_user):
    resp = await rename(client, registered_user, str(uuid.uuid4()), {"name": "Ghost"})
    assert resp.status_code == 404


async def test_rename_malformed_uuid_returns_422(client, registered_user):
    resp = await rename(client, registered_user, "not-a-uuid", {"name": "Bad Id"})
    assert resp.status_code == 422


async def test_rename_deleted_workspace_returns_404(client, registered_user):
    workspace = await create_workspace(client, registered_user, "Deleted Then Renamed")
    await client.delete(
        f"/api/v1/workspaces/{workspace['id']}",
        headers=auth_header(registered_user["access_token"]),
    )

    resp = await rename(client, registered_user, workspace["id"], {"name": "Zombie"})

    assert resp.status_code == 404
