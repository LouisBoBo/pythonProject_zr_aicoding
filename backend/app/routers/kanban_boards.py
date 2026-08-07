from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import KanbanBoard, User
from app.schemas import (
    KanbanBoardCreate,
    KanbanBoardListResponse,
    KanbanBoardResponse,
    KanbanBoardStatusUpdate,
    KanbanBoardUpdate,
)

router = APIRouter(prefix="/api/kanban-boards", tags=["kanban-boards"])

VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"active", "archived"},
    "active": {"archived"},
    "archived": {"active"},
}


def _get_kanban_board_or_404(board_id: int, db: Session) -> KanbanBoard:
    board = db.query(KanbanBoard).filter(KanbanBoard.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="看板不存在")
    return board


@router.get("", response_model=KanbanBoardListResponse)
def list_kanban_boards(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: str | None = Query(None),
    category: str | None = Query(None),
    production_line: str | None = Query(None),
    board_code: str | None = Query(None),
    board_name: str | None = Query(None),
    search: str | None = Query(None),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(KanbanBoard)
    if status:
        query = query.filter(KanbanBoard.status == status)
    if category:
        query = query.filter(KanbanBoard.category == category)
    if production_line:
        query = query.filter(KanbanBoard.production_line.ilike(f"%{production_line}%"))
    if board_code:
        query = query.filter(KanbanBoard.board_code.ilike(f"%{board_code}%"))
    if board_name:
        query = query.filter(KanbanBoard.board_name.ilike(f"%{board_name}%"))
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (KanbanBoard.board_code.ilike(pattern))
            | (KanbanBoard.board_name.ilike(pattern))
            | (KanbanBoard.description.ilike(pattern))
        )
    query = query.order_by(KanbanBoard.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return KanbanBoardListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{board_id}", response_model=KanbanBoardResponse)
def get_kanban_board(
    board_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_kanban_board_or_404(board_id, db)


@router.post("", response_model=KanbanBoardResponse, status_code=201)
def create_kanban_board(
    payload: KanbanBoardCreate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(KanbanBoard).filter(KanbanBoard.board_code == payload.board_code).first()
    if existing:
        raise HTTPException(status_code=409, detail="看板编码已存在")

    board = KanbanBoard(
        board_code=payload.board_code,
        board_name=payload.board_name,
        category=payload.category,
        production_line=payload.production_line,
        owner=payload.owner,
        description=payload.description,
        refresh_interval=payload.refresh_interval,
        remark=payload.remark,
    )
    db.add(board)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="看板编码已存在") from None
    db.refresh(board)
    return board


@router.put("/{board_id}", response_model=KanbanBoardResponse)
def update_kanban_board(
    board_id: int,
    payload: KanbanBoardUpdate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    board = _get_kanban_board_or_404(board_id, db)
    update_data = payload.model_dump(exclude_unset=True)

    if "board_code" in update_data and update_data["board_code"] != board.board_code:
        duplicate = (
            db.query(KanbanBoard)
            .filter(KanbanBoard.board_code == update_data["board_code"], KanbanBoard.id != board_id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="看板编码已存在")

    for field, value in update_data.items():
        setattr(board, field, value)
    board.updated_at = datetime.utcnow()

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="看板编码已存在") from None
    db.refresh(board)
    return board


@router.patch("/{board_id}/status", response_model=KanbanBoardResponse)
def update_kanban_board_status(
    board_id: int,
    payload: KanbanBoardStatusUpdate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    board = _get_kanban_board_or_404(board_id, db)
    allowed = VALID_STATUS_TRANSITIONS.get(board.status, set())
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"无法从 {board.status} 流转到 {payload.status}")

    board.status = payload.status
    board.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(board)
    return board


@router.delete("/{board_id}", status_code=204)
def delete_kanban_board(
    board_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    board = _get_kanban_board_or_404(board_id, db)
    db.delete(board)
    db.commit()
