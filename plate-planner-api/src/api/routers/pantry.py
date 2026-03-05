from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database import session, models
from src.schemas.pantry import PantryResponse, PantryItemResponse, AddPantryItemsRequest
from src.auth import security

router = APIRouter(prefix="/pantry", tags=["pantry"])


def _get_items(user_id, db: Session) -> PantryResponse:
    rows = (
        db.query(models.UserPantryItem)
        .filter(models.UserPantryItem.user_id == user_id)
        .order_by(models.UserPantryItem.item_name)
        .all()
    )
    return PantryResponse(
        items=[PantryItemResponse(name=r.item_name, created_at=r.created_at) for r in rows]
    )


@router.get("", response_model=PantryResponse, summary="Get current user's pantry")
def get_pantry(
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db),
):
    return _get_items(current_user.id, db)


@router.post(
    "/items",
    response_model=PantryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add one or more items to pantry (idempotent)",
)
def add_pantry_items(
    request: AddPantryItemsRequest,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db),
):
    for raw in request.items:
        name = raw.lower().strip()
        if not name:
            continue
        exists = (
            db.query(models.UserPantryItem)
            .filter(
                models.UserPantryItem.user_id == current_user.id,
                models.UserPantryItem.item_name == name,
            )
            .first()
        )
        if not exists:
            db.add(models.UserPantryItem(user_id=current_user.id, item_name=name))
    db.commit()
    return _get_items(current_user.id, db)


@router.delete(
    "/items/{item_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an item from pantry",
)
def delete_pantry_item(
    item_name: str,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db),
):
    deleted = (
        db.query(models.UserPantryItem)
        .filter(
            models.UserPantryItem.user_id == current_user.id,
            models.UserPantryItem.item_name == item_name.lower().strip(),
        )
        .delete()
    )
    db.commit()
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not in pantry")


@router.put(
    "",
    response_model=PantryResponse,
    summary="Replace entire pantry with a new list",
)
def replace_pantry(
    request: AddPantryItemsRequest,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db),
):
    db.query(models.UserPantryItem).filter(
        models.UserPantryItem.user_id == current_user.id
    ).delete()
    unique_names = {n.lower().strip() for n in request.items if n.strip()}
    for name in unique_names:
        db.add(models.UserPantryItem(user_id=current_user.id, item_name=name))
    db.commit()
    return _get_items(current_user.id, db)
