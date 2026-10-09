import pytest
from fastapi import HTTPException
from sprintalis_api.workspaces.models import WorkspaceMember, WorkspaceRole
from sprintalis_api.workspaces.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    has_permission,
    require_permission,
)


def test_every_role_has_an_explicit_entry():
    assert set(ROLE_PERMISSIONS) == set(WorkspaceRole)


@pytest.mark.parametrize("permission", list(Permission))
def test_owner_has_every_permission(permission):
    assert has_permission(WorkspaceRole.OWNER, permission) is True


@pytest.mark.parametrize("role", [WorkspaceRole.ADMIN, WorkspaceRole.MEMBER])
@pytest.mark.parametrize(
    "permission", [Permission.WORKSPACE_RENAME, Permission.WORKSPACE_DELETE]
)
def test_only_owner_can_rename_or_delete_workspace(role, permission):
    assert has_permission(role, permission) is False


def test_unknown_role_is_denied():
    assert has_permission("NOT_A_ROLE", Permission.WORKSPACE_DELETE) is False


@pytest.mark.parametrize("role", [WorkspaceRole.ADMIN, WorkspaceRole.MEMBER])
async def test_dependency_denies_role_without_permission(role):
    dependency = require_permission(Permission.WORKSPACE_DELETE)
    membership = WorkspaceMember(role=role)

    with pytest.raises(HTTPException) as exc_info:
        await dependency(membership=membership)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "WORKSPACE_PERMISSION_DENIED"


async def test_dependency_allows_owner():
    dependency = require_permission(Permission.WORKSPACE_DELETE)
    membership = WorkspaceMember(role=WorkspaceRole.OWNER)

    assert await dependency(membership=membership) is membership
