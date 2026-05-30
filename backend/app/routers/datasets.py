import csv
import io
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.db import get_db
from app.models.orm import Dataset, DatasetRow
from app.schemas.schemas import DatasetCreate, DatasetOut, DatasetRowCreate, DatasetRowOut, DatasetRowsBulkCreate
from app.routers.auth import get_current_user, get_current_workspace_id

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetOut])
async def list_datasets(
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    result = await db.execute(
        select(Dataset)
        .where(Dataset.workspace_id == UUID(workspace_id))
        .order_by(Dataset.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=DatasetOut, status_code=201)
async def create_dataset(
    data: DatasetCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
):
    dataset = Dataset(
        workspace_id=UUID(workspace_id),
        name=data.name,
        description=data.description,
        type=data.type,
        created_by=user.id,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.get("/{dataset_id}", response_model=DatasetOut)
async def get_dataset(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    d = await db.get(Dataset, dataset_id)
    if not d or str(d.workspace_id) != workspace_id:
        raise HTTPException(404, "Dataset not found")
    return d


@router.get("/{dataset_id}/rows", response_model=list[DatasetRowOut])
async def list_rows(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    d = await db.get(Dataset, dataset_id)
    if not d or str(d.workspace_id) != workspace_id:
        raise HTTPException(404, "Dataset not found")

    result = await db.execute(
        select(DatasetRow)
        .where(DatasetRow.dataset_id == dataset_id)
        .order_by(DatasetRow.created_at.asc())
        .limit(limit).offset(offset)
    )
    return result.scalars().all()


@router.post("/{dataset_id}/rows", response_model=list[DatasetRowOut], status_code=201)
async def add_rows(
    dataset_id: UUID,
    body: DatasetRowsBulkCreate,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    d = await db.get(Dataset, dataset_id)
    if not d or str(d.workspace_id) != workspace_id:
        raise HTTPException(404, "Dataset not found")

    rows = [
        DatasetRow(
            dataset_id=dataset_id,
            input_prompt=r.input_prompt,
            expected_output=r.expected_output,
            context=r.context,
            tags=r.tags,
        )
        for r in body.rows
    ]
    db.add_all(rows)

    # Update row_count
    d.row_count += len(rows)
    await db.commit()
    return rows


@router.post("/{dataset_id}/upload", status_code=201)
async def upload_csv(
    dataset_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    """
    Upload a CSV or JSONL file to populate a dataset.

    CSV columns (auto-detected): input_prompt, expected_output, context, tags
    JSONL: one JSON object per line with same keys.
    """
    d = await db.get(Dataset, dataset_id)
    if not d or str(d.workspace_id) != workspace_id:
        raise HTTPException(404, "Dataset not found")

    content = await file.read()
    filename = file.filename or ""
    rows_created = []

    try:
        if filename.endswith(".jsonl"):
            for line in content.decode("utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                rows_created.append(DatasetRow(
                    dataset_id=dataset_id,
                    input_prompt=obj.get("input_prompt") or obj.get("prompt", ""),
                    expected_output=obj.get("expected_output") or obj.get("expected"),
                    context=obj.get("context"),
                    tags=obj.get("tags", []),
                ))
        else:
            # CSV (default)
            reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
            for row in reader:
                input_prompt = row.get("input_prompt") or row.get("prompt") or row.get("question", "")
                if not input_prompt:
                    continue
                rows_created.append(DatasetRow(
                    dataset_id=dataset_id,
                    input_prompt=input_prompt,
                    expected_output=row.get("expected_output") or row.get("expected") or row.get("answer"),
                    context=row.get("context"),
                    tags=[t.strip() for t in (row.get("tags") or "").split(",") if t.strip()],
                ))
    except Exception as e:
        raise HTTPException(400, f"Failed to parse file: {str(e)}")

    if not rows_created:
        raise HTTPException(400, "No valid rows found in file. Check column names.")

    db.add_all(rows_created)
    d.row_count += len(rows_created)
    await db.commit()

    return {"rows_created": len(rows_created), "dataset_id": str(dataset_id)}


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    d = await db.get(Dataset, dataset_id)
    if not d or str(d.workspace_id) != workspace_id:
        raise HTTPException(404, "Not found")
    await db.delete(d)
    await db.commit()
