"""Shopping List Router - Phase 3 Week 3

API endpoints for shopping list generation and management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from src.database import session, models
from src.schemas import shopping_list as schemas
from src.auth import security
from src.services import shopping_list_service

router = APIRouter(
    prefix="/shopping-lists",
    tags=["shopping-lists"],
)


@router.post("/generate", response_model=schemas.ShoppingList, status_code=status.HTTP_201_CREATED)
def generate_shopping_list(
    request: schemas.ShoppingListGenerateRequest,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    """
    Generate a shopping list from a meal plan.
    
    Extracts all ingredients from recipes in the meal plan, consolidates duplicates,
    categorizes ingredients, and estimates prices.
    """
    try:
        shopping_list = shopping_list_service.generate_shopping_list(
            db=db,
            user_id=current_user.id,
            request=request,
        )
        return shopping_list
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate shopping list: {str(exc)}"
        ) from exc


@router.get("/", response_model=schemas.ShoppingListPagination)
def get_my_shopping_lists(
    status: Optional[str] = Query(None, description="Filter by status (active, completed, archived)"),
    limit: int = Query(10, ge=1, le=100, description="Number of lists to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    """Get all shopping lists for the current user with pagination."""
    try:
        lists, total = shopping_list_service.get_user_shopping_lists(
            db=db,
            user_id=current_user.id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        # Convert to summary schemas
        summaries = [
            schemas.ShoppingListSummary(
                id=list_obj.id,
                name=list_obj.name,
                status=list_obj.status,
                total_items=list_obj.total_items,
                purchased_items=list_obj.purchased_items,
                total_estimated_cost=list_obj.total_estimated_cost,
                created_at=list_obj.created_at,
            )
            for list_obj in lists
        ]
        
        return schemas.ShoppingListPagination(
            items=summaries,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve shopping lists: {str(exc)}"
        ) from exc


@router.get("/{list_id}", response_model=schemas.ShoppingListWithCategories)
def get_shopping_list(
    list_id: UUID,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    """
    Get a shopping list by ID with items grouped by category.
    
    Returns the shopping list with items organized by category for easy browsing.
    """
    try:
        shopping_list = shopping_list_service.get_shopping_list(
            db=db,
            user_id=current_user.id,
            list_id=list_id
        )
        
        if not shopping_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shopping list not found"
            )
        
        # Group items by category
        items_by_category: dict[str, List[schemas.ShoppingListItem]] = {}
        for item in shopping_list.items:
            category = item.category or "Other"
            if category not in items_by_category:
                items_by_category[category] = []
            items_by_category[category].append(
                schemas.ShoppingListItem.model_validate(item)
            )
        
        return schemas.ShoppingListWithCategories(
            id=shopping_list.id,
            user_id=shopping_list.user_id,
            plan_id=shopping_list.plan_id,
            name=shopping_list.name,
            status=shopping_list.status,
            total_estimated_cost=shopping_list.total_estimated_cost,
            total_items=shopping_list.total_items,
            purchased_items=shopping_list.purchased_items,
            created_at=shopping_list.created_at,
            updated_at=shopping_list.updated_at,
            completed_at=shopping_list.completed_at,
            items_by_category=items_by_category,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve shopping list: {str(exc)}"
        ) from exc


@router.post("/{list_id}/items", response_model=schemas.ShoppingListItem, status_code=status.HTTP_201_CREATED)
def add_manual_item(
    list_id: UUID,
    item_data: schemas.ShoppingListItemCreate,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    """Add a manual item to an existing shopping list."""
    try:
        item = shopping_list_service.add_manual_item(
            db=db,
            user_id=current_user.id,
            list_id=list_id,
            item_data=item_data
        )
        return item
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add item: {str(exc)}"
        ) from exc


@router.put("/{list_id}/items/{item_id}", response_model=schemas.ShoppingListItem)
def update_shopping_list_item(
    list_id: UUID,
    item_id: UUID,
    updates: schemas.ShoppingListItemUpdate,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    """
    Update a shopping list item.
    
    Can update quantity, unit, category, notes, and purchase status.
    """
    try:
        item = shopping_list_service.update_shopping_list_item(
            db=db,
            user_id=current_user.id,
            list_id=list_id,
            item_id=item_id,
            updates=updates
        )
        return item
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update item: {str(exc)}"
        ) from exc


@router.delete("/{list_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shopping_list_item(
    list_id: UUID,
    item_id: UUID,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    """Delete an item from a shopping list."""
    try:
        shopping_list_service.delete_shopping_list_item(
            db=db,
            user_id=current_user.id,
            list_id=list_id,
            item_id=item_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete item: {str(exc)}"
        ) from exc


@router.post("/{list_id}/complete", response_model=schemas.ShoppingList)
def complete_shopping_list(
    list_id: UUID,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    """
    Mark all items in a shopping list as purchased and mark list as completed.
    
    This is useful when you've finished shopping and want to track the list as complete.
    """
    try:
        shopping_list = shopping_list_service.complete_shopping_list(
            db=db,
            user_id=current_user.id,
            list_id=list_id
        )
        return shopping_list
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete shopping list: {str(exc)}"
        ) from exc


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shopping_list(
    list_id: UUID,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    """Delete an entire shopping list and all its items."""
    try:
        shopping_list_service.delete_shopping_list(
            db=db,
            user_id=current_user.id,
            list_id=list_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete shopping list: {str(exc)}"
        ) from exc












