from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sprintalis_api.core.database import get_db
from sprintalis_api.authentication.dependencies import get_current_user
from sprintalis_api.authentication.models import User
from sprintalis_api.workspaces import service
from sprintalis_api.workspaces.dependencies import (
    get_workspace_or_404,
    require_membership,
)
from sprintalis_api.workspaces.models import Workspace, WorkspaceMember
from sprintalis_api.workspaces.schemas import (
    WorkspaceCreateRequest,
    WorkspaceResponse,
    WorkspaceListResponse,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    workspace = await service.create_workspace(
        db, name=payload.name, created_by=current_user.id
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
