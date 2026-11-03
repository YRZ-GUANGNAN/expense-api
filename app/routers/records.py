from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import current_user
from app.db import db_conn
from app.schemas import RecordIn

router = APIRouter()


@router.get("/records")
def list_records(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    user: dict = Depends(current_user),
):
    offset = (page - 1) * size

    with db_conn() as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, item, amount, created_at FROM records "
            "WHERE user_id = %s ORDER BY id DESC LIMIT %s OFFSET %s",
            (user["user_id"], size, offset),
        )
        items = cursor.fetchall()

        cursor.execute(
            "SELECT COUNT(*) AS c FROM records WHERE user_id = %s",
            (user["user_id"],),
        )
        total = cursor.fetchone()["c"]

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
    }


@router.post("/records")
def add_record(record: RecordIn, user: dict = Depends(current_user)):
    with db_conn() as conn, conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO records (item, amount, user_id) VALUES (%s, %s, %s)",
            (record.item, record.amount, user["user_id"]),
        )
        conn.commit()
        new_id = cursor.lastrowid

    return {"ok": True, "id": new_id}


@router.get("/summary")
def summary(user: dict = Depends(current_user)):
    with db_conn() as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) AS count, IFNULL(SUM(amount), 0) AS total "
            "FROM records WHERE user_id = %s",
            (user["user_id"],),
        )
        result = cursor.fetchone()

    return result


@router.delete("/records/{record_id}")
def delete_record(record_id: int, user: dict = Depends(current_user)):
    with db_conn() as conn, conn.cursor() as cursor:
        cursor.execute(
            "DELETE FROM records WHERE id = %s AND user_id = %s",
            (record_id, user["user_id"]),
        )
        conn.commit()
        deleted = cursor.rowcount

    if deleted == 0:
        raise HTTPException(status_code=404, detail="该记录不存在")

    return {"ok": True, "message": f"成功删除 id 为 {record_id} 的记录"}


@router.put("/records/{record_id}")
def update_record(record_id: int, record: RecordIn, user: dict = Depends(current_user)):
    with db_conn() as conn, conn.cursor() as cursor:
        cursor.execute(
            "UPDATE records SET item = %s, amount = %s WHERE id = %s AND user_id = %s",
            (record.item, record.amount, record_id, user["user_id"]),
        )
        conn.commit()
        updated = cursor.rowcount

    if updated == 0:
        raise HTTPException(status_code=404, detail="该记录不存在或不属于你")

    return {"ok": True, "id": record_id}
