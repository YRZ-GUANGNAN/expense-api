from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.models import Record
from app.schemas import PageOut, RecordIn

router = APIRouter()


@router.get("/records", response_model=PageOut)
def list_records(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * size

    items = db.execute(
        select(Record)
        .where(Record.user_id == user["user_id"])
        .order_by(Record.id.desc())
        .limit(size)
        .offset(offset)
    ).scalars().all()

    total = db.execute(
        select(func.count())
        .select_from(Record)
        .where(Record.user_id == user["user_id"])
    ).scalar_one()

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
    }


@router.post("/records")
def add_record(
    record: RecordIn,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    new_record = Record(
        item=record.item,
        amount=record.amount,
        user_id=user["user_id"],
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return {"ok": True, "id": new_record.id}


@router.get("/summary")
def summary(
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    count, total = db.execute(
        select(
            func.count().label("count"),
            func.coalesce(func.sum(Record.amount), 0).label("total"),
        )
        .select_from(Record)
        .where(Record.user_id == user["user_id"])
    ).one()
    return {"count": count, "total": total}


@router.delete("/records/{record_id}")
def delete_record(
    record_id: int,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    obj = db.execute(
        select(Record).where(
            Record.id == record_id,
            Record.user_id == user["user_id"],
        )
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404, detail="该记录不存在")

    db.delete(obj)
    db.commit()
    return {"ok": True, "message": f"成功删除 id 为 {record_id} 的记录"}


@router.put("/records/{record_id}")
def update_record(
    record_id: int,
    record: RecordIn,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    obj = db.execute(
        select(Record).where(
            Record.id == record_id,
            Record.user_id == user["user_id"],
        )
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404, detail="该记录不存在或不属于你")

    obj.item = record.item
    obj.amount = record.amount
    db.commit()
    return {"ok": True, "id": record_id}
