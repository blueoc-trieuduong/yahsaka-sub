import uuid

from sqlmodel import Session

from app.models.items import ItemCreate
from app.models.models import Item


class ItemServices:
    def create_item(
        *, session: Session, item_in: ItemCreate, owner_id: uuid.UUID
    ) -> Item:
        db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
        return db_item
