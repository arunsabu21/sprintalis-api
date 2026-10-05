import uuid
import pytest
from sqlalchemy import select
from sprintalis_api.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def create_workspace(client, user, name: str) -> str:
    resp = await client.post(
        "/api/v1/workspaces",
        json={"name": name},
        headers=auth_header(user["access_token"]),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def error_detail(resp) -> dict:
    body = resp.json()
    return body.get("detail", body)


async def test_owner_can_delete_workspace(client, registered_user):
    workspace_id = await create_workspace(client, registered_user, "Delete Me")

    resp = await client.delete(
        f"/api/v1/workspaces/{workspace_id}",
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.status_code == 204
    assert resp.content == b""


async def test_deleted_workspace_returns_404_on_get(client, registered_user):
    workspace_id = await create_workspace(client, registered_user, "Gone After Delete")
    await client.delete(
        f"/api/v1/workspaces/{workspace_id}",
        headers=auth_header(registered_user["access_token"]),
    )

    resp = await client.get(
        f"/api/v1/workspaces/{workspace_id}",
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.status_code == 404


async def test_deleted_workspace_excluded_from_list(client, registered_user):
    keep_id = await create_workspace(client, registered_user, "Keep Me")
    delete_id = await create_workspace(client, registered_user, "Remove Me")
    await client.delete(
        f"/api/v1/workspaces/{delete_id}",
        headers=auth_header(registered_user["access_token"]),
    )

    resp = await client.get(
        "/api/v1/workspaces",
        headers=auth_header(registered_user["access_token"]),
    )
    ids = [w["id"] for w in resp.json()["workspaces"]]
    assert keep_id in ids
    assert delete_id not in ids


async def test_delete_only_affects_target_workspace(client, registered_user):
    target_id = await create_workspace(client, registered_user, "Target")
    other_id = await create_workspace(client, registered_user, "Bystander")

    await client.delete(
        f"/api/v1/workspaces/{target_id}",
        headers=auth_header(registered_user["access_token"]),
    )

    resp = await client.get(
        f"/api/v1/workspaces/{other_id}",
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.status_code == 200


async def test_delete_twice_returns_404(client, registered_user):
    workspace_id = await create_workspace(client, registered_user, "Double Delete")
    headers = auth_header(registered_user["access_token"])

    first = await client.delete(f"/api/v1/workspaces/{workspace_id}", headers=headers)
    second = await client.delete(f"/api/v1/workspaces/{workspace_id}", headers=headers)

    assert first.status_code == 204
    assert second.status_code == 404


async def test_delete_is_soft_and_records_deleter(client, registered_user, db_session):
    workspace_id = await create_workspace(client, registered_user, "Soft Delete Check")
    await client.delete(
        f"/api/v1/workspaces/{workspace_id}",
        headers=auth_header(registered_user["access_token"]),
    )

    workspace = await db_session.scalar(
        select(Workspace)
        .where(Workspace.id == uuid.UUID(workspace_id))
        .execution_options(populate_existing=True)
    )
    assert workspace is not None
    assert workspace.deleted_at is not None
    assert str(workspace.deleted_by) == registered_user["user"]["id"]


async def test_deleted_slug_stays_reserved(client, registered_user):
    first_id = await create_workspace(client, registered_user, "Reserved Slug")
    await client.delete(
        f"/api/v1/workspaces/{first_id}",
        headers=auth_header(registered_user["access_token"]),
    )

    resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Reserved Slug"},
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.status_code == 201
    assert resp.json()["slug"] == "reserved-slug-1"


async def test_delete_workspace_no_auth_fails(client, registered_user):
    workspace_id = await create_workspace(client, registered_user, "No Auth Delete")

    resp = await client.delete(f"/api/v1/workspaces/{workspace_id}")
    assert resp.status_code == 401


async def test_delete_nonexistent_workspace_returns_404(client, registered_user):
    resp = await client.delete(
        f"/api/v1/workspaces/{uuid.uuid7()}",
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.status_code == 404


async def test_delete_workspace_malformed_uuid_returns_422(client, registered_user):
    resp = await client.delete(
        "/api/v1/workspaces/not-a-uuid",
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.status_code == 422
