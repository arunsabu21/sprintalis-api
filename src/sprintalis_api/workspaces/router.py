from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sprintalis_api.core.database import get_db
from sprintalis_api.authentication.dependencies import get_current_user
from sprintalis_api.authentication.models import User
from sprintalis_api.workspaces import service
from sprintalis_api.workspaces.dependencies import (
    get_workspace_or_404,
    require_membership,
    require_owner,
)
from sprintalis_api.workspaces.models import Workspace, WorkspaceMember
from sprintalis_api.workspaces.schemas import (
    WorkspaceCreateRequest,
    WorkspaceResponse,
    WorkspaceListResponse,
    WorkspaceUpdateRequest,
)

from sprintalis_api.core.exceptions import WorkspaceLimitReachedError

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        workspace = await service.create_workspace(
            db, name=payload.name, created_by=current_user.id
        )
    except WorkspaceLimitReachedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "WORKSPACE_LIMIT_REACHED",
                "message": "Workspace limit reached.",
            },
        )

    return WorkspaceResponse.model_validate(workspace)


@router.get("", response_model=WorkspaceListResponse)
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    workspaces = await service.list_workspaces_for_user(db, current_user.id)

    return WorkspaceListResponse(
        workspaces=[WorkspaceResponse.model_validate(w) for w in workspaces]
    )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace: Workspace = Depends(get_workspace_or_404),
    membership: WorkspaceMember = Depends(require_membership),
):
    return WorkspaceResponse.model_validate(workspace)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace: Workspace = Depends(get_workspace_or_404),
    membership: WorkspaceMember = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> None:
    deleted = await service.delete_workspace(
        db, workspace.id, deleted_by=membership.user_id
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKSPACE_NOT_FOUND", "message": "Workspace not found."},
        )


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def rename_workspace(
    payload: WorkspaceUpdateRequest,
    workspace: Workspace = Depends(get_workspace_or_404),
    membership: WorkspaceMember = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    workspace = await service.rename_workspace(
        db,
        workspace_id=workspace.id,
        name=payload.name,
    )

    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKSPACE_NOT_FOUND", "message": "Workspace not found."},
        )

    return WorkspaceResponse.model_validate(workspace)
