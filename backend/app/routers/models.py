import time
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.models.orm import ModelEndpoint
from app.schemas.schemas import ModelEndpointCreate, ModelEndpointOut, ModelTestRequest, ModelTestResponse
from app.routers.auth import get_current_user, get_current_workspace_id
from app.services.auth import encrypt_api_key, decrypt_api_key, mask_api_key
from app.services.llm_client import call_llm

router = APIRouter(prefix="/model-endpoints", tags=["models"])


def _to_out(m: ModelEndpoint) -> ModelEndpointOut:
    masked = mask_api_key(decrypt_api_key(m.api_key_encrypted))
    return ModelEndpointOut(
        id=m.id, name=m.name, provider=m.provider,
        base_url=m.base_url, model_name=m.model_name,
        api_key_masked=masked, system_prompt=m.system_prompt,
        temperature=m.temperature, max_tokens=m.max_tokens,
        created_at=m.created_at,
    )


@router.get("", response_model=list[ModelEndpointOut])
async def list_endpoints(
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    result = await db.execute(
        select(ModelEndpoint)
        .where(ModelEndpoint.workspace_id == UUID(workspace_id))
        .order_by(ModelEndpoint.created_at.desc())
    )
    return [_to_out(m) for m in result.scalars().all()]


@router.post("", response_model=ModelEndpointOut, status_code=201)
async def create_endpoint(
    data: ModelEndpointCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
):
    endpoint = ModelEndpoint(
        workspace_id=UUID(workspace_id),
        name=data.name,
        provider=data.provider,
        base_url=data.base_url,
        model_name=data.model_name,
        api_key_encrypted=encrypt_api_key(data.api_key),
        system_prompt=data.system_prompt,
        temperature=data.temperature,
        max_tokens=data.max_tokens,
    )
    db.add(endpoint)
    await db.commit()
    await db.refresh(endpoint)
    return _to_out(endpoint)


@router.post("/{endpoint_id}/test", response_model=ModelTestResponse)
async def test_endpoint(
    endpoint_id: UUID,
    body: ModelTestRequest,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    endpoint = await db.get(ModelEndpoint, endpoint_id)
    if not endpoint or str(endpoint.workspace_id) != workspace_id:
        raise HTTPException(404, "Model endpoint not found")

    response = await call_llm(body.prompt, endpoint)

    if response.error:
        return ModelTestResponse(success=False, output=None, latency_ms=response.latency_ms, error=response.error)

    return ModelTestResponse(
        success=True,
        output=response.content,
        latency_ms=response.latency_ms,
        error=None,
    )


@router.delete("/{endpoint_id}", status_code=204)
async def delete_endpoint(
    endpoint_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    endpoint = await db.get(ModelEndpoint, endpoint_id)
    if not endpoint or str(endpoint.workspace_id) != workspace_id:
        raise HTTPException(404, "Not found")
    await db.delete(endpoint)
    await db.commit()
