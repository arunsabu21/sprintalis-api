import enum
from fastapi import Depends, HTTPException, status
from sprintalis_api.workspaces.dependencies import require_membership
from sprintalis_api.workspaces.models import WorkspaceMember, WorkspaceRole


class Permission(str, enum.Enum):
    WORKSPACE_RENAME = "workspace:rename"
    WORKSPACE_DELETE = "workspace:delete"


ROLE_PERMISSIONS: dict[WorkspaceRole, frozenset[Permission]] = {
    WorkspaceRole.OWNER: frozenset(Permission),
    WorkspaceRole.ADMIN: frozenset(),
    WorkspaceRole.MEMBER: frozenset(),
}


def has_permission(role: WorkspaceRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def require_permission(permission: Permission):
    async def dependency(
        membership: WorkspaceMember = Depends(require_membership),
    ) -> WorkspaceMember:
        if not has_permission(membership.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "WORKSPACE_PERMISSION_DENIED",
                    "message": "You don't have permission to do this.",
                },
            )
        return membership

    return dependency
