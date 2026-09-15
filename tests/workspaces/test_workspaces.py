import uuid
import pytest
from sqlalchemy import select
from sprintalis_api.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_create_workspace_success(client, registered_user):
    resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Acme Engineering"},
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Acme Engineering"
    assert body["slug"] == "acme-engineering"
    assert "id" in body
    assert "created_at" in body


async def test_get_workspace_after_create(client, registered_user):
    create_resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Get Test Workspace"},
        headers=auth_header(registered_user["access_token"]),
    )
    workspace_id = create_resp.json()["id"]

    get_resp = await client.get(
        f"/api/v1/workspaces/{workspace_id}",
        headers=auth_header(registered_user["access_token"]),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == workspace_id


async def test_create_workspace_no_auth_fails(client):
    resp = await client.post("/api/v1/workspaces", json={"name": "No Auth"})
    assert resp.status_code == 401


async def test_create_workspace_garbage_token_fails(client):
    resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Garbage Token"},
        headers=auth_header("not.a.real.token"),
    )
    assert resp.status_code == 401


async def test_creator_becomes_owner(client, registered_user, db_session):
    resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Owner Test"},
        headers=auth_header(registered_user["access_token"]),
    )
    workspace_id = uuid.UUID(resp.json()["id"])
    user_id = uuid.UUID(registered_user["user"]["id"])

    membership = await db_session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    assert membership is not None
    assert membership.role == WorkspaceRole.OWNER


async def test_workspace_and_membership_created_atomically(
    client, registered_user, db_session
):
    resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Atomic Test"},
        headers=auth_header(registered_user["access_token"]),
    )
    workspace_id = uuid.UUID(resp.json()["id"])

    workspace = await db_session.get(Workspace, workspace_id)
    membership = await db_session.scalar(
        select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
    )

    assert workspace is not None
    assert membership is not None


async def test_client_cannot_set_created_by(
    client, registered_user, second_user, db_session
):
    resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Injection Test", "created_by": second_user["user"]["id"]},
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.status_code == 201
    workspace_id = uuid.UUID(resp.json()["id"])

    workspace = await db_session.get(Workspace, workspace_id)
    assert str(workspace.created_by) == registered_user["user"]["id"]


async def test_client_cannot_set_role(client, registered_user, db_session):
    resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Role Injection Test", "role": "ADMIN"},
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.status_code == 201
    workspace_id = uuid.UUID(resp.json()["id"])
    user_id = uuid.UUID(registered_user["user"]["id"])

    membership = await db_session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    assert membership.role == WorkspaceRole.OWNER


async def test_duplicate_name_generates_unique_slug(client, registered_user):
    resp1 = await client.post(
        "/api/v1/workspaces",
        json={"name": "Duplicate Name"},
        headers=auth_header(registered_user["access_token"]),
    )
    resp2 = await client.post(
        "/api/v1/workspaces",
        json={"name": "Duplicate Name"},
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["slug"] != resp2.json()["slug"]


async def test_slug_strips_special_characters(client, registered_user):
    resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Acme & Co. #1"},
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.status_code == 201
    slug = resp.json()["slug"]
    assert all(c.isalnum() or c == "-" for c in slug)


async def test_list_returns_only_own_workspaces(client, registered_user, second_user):
    await client.post(
        "/api/v1/workspaces",
        json={"name": "User A Workspace 1"},
        headers=auth_header(registered_user["access_token"]),
    )
    await client.post(
        "/api/v1/workspaces",
        json={"name": "User A Workspace 2"},
        headers=auth_header(registered_user["access_token"]),
    )
    await client.post(
        "/api/v1/workspaces",
        json={"name": "User B Workspace"},
        headers=auth_header(second_user["access_token"]),
    )

    resp = await client.get(
        "/api/v1/workspaces",
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.status_code == 200
    names = [w["name"] for w in resp.json()["workspaces"]]
    assert "User A Workspace 1" in names
    assert "User A Workspace 2" in names
    assert "User B Workspace" not in names


async def test_list_empty_for_new_user(client, second_user):
    resp = await client.get(
        "/api/v1/workspaces",
        headers=auth_header(second_user["access_token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["workspaces"] == []


async def test_list_no_auth_fails(client):
    resp = await client.get("/api/v1/workspaces")
    assert resp.status_code == 401


async def test_non_member_cannot_get_workspace(client, registered_user, second_user):
    create_resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Private Workspace"},
        headers=auth_header(registered_user["access_token"]),
    )
    workspace_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/workspaces/{workspace_id}",
        headers=auth_header(second_user["access_token"]),
    )
    assert resp.status_code == 404


async def test_get_nonexistent_workspace_returns_404(client, registered_user):
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/workspaces/{fake_id}",
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.status_code == 404


async def test_get_workspace_malformed_uuid_returns_422(client, registered_user):
    resp = await client.get(
        "/api/v1/workspaces/not-a-uuid",
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.status_code == 422


async def test_get_workspace_no_auth_fails(client, registered_user):
    create_resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "No Auth Get Test"},
        headers=auth_header(registered_user["access_token"]),
    )
    workspace_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/workspaces/{workspace_id}")
    assert resp.status_code == 401


async def test_get_workspace_response_excludes_member_data(client, registered_user):
    create_resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Shape Test"},
        headers=auth_header(registered_user["access_token"]),
    )
    workspace_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/workspaces/{workspace_id}",
        headers=auth_header(registered_user["access_token"]),
    )
    body = resp.json()
    assert set(body.keys()) == {"id", "name", "slug", "created_at", "updated_at"}


async def test_duplicate_membership_rejected_at_db_level(
    client, registered_user, db_session
):
    create_resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Constraint Test"},
        headers=auth_header(registered_user["access_token"]),
    )
    workspace_id = uuid.UUID(create_resp.json()["id"])
    user_id = uuid.UUID(registered_user["user"]["id"])

    duplicate = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=user_id,
        role=WorkspaceRole.MEMBER,
    )
    db_session.add(duplicate)

    with pytest.raises(Exception):  # IntegrityError from the unique constraint
        await db_session.commit()

    await db_session.rollback()


async def test_patch_workspace_not_allowed(client, registered_user):
    create_resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Method Test"},
        headers=auth_header(registered_user["access_token"]),
    )
    workspace_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        json={"name": "Renamed"},
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.status_code == 405


async def test_delete_workspace_not_allowed(client, registered_user):
    create_resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Delete Method Test"},
        headers=auth_header(registered_user["access_token"]),
    )
    workspace_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/workspaces/{workspace_id}",
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.status_code == 405


async def test_members_endpoint_not_found(client, registered_user):
    create_resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Members Route Test"},
        headers=auth_header(registered_user["access_token"]),
    )
    workspace_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=auth_header(registered_user["access_token"]),
    )
    assert resp.status_code == 404
