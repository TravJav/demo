from sqlalchemy.orm import Session

from app.models import LineItem


class LineItemRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, line_item: LineItem) -> LineItem:
        self.db.add(line_item)
        return line_item
