import uuid
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sprintalis_api.core.database import get_db
from sprintalis_api.authentication.dependencies import get_current_user
from sprintalis_api.authentication.models import User
from sprintalis_api.workspaces.models import Workspace, WorkspaceMember
from sprintalis_api.workspaces.repository import (
    WorkspaceRepository,
    WorkspaceMemberRepository,
)


async def get_workspace_or_404(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    workspace = await WorkspaceRepository(db).get_by_id(workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )

    return workspace


async def require_membership(
    workspace: Workspace = Depends(get_workspace_or_404),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceMember:
    membership = await WorkspaceMemberRepository(db).get_membership(
        workspace.id, current_user.id
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )

    return membership
