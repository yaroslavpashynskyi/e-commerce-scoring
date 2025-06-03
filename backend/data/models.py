import datetime
import json
import logging
from peewee import Model, CharField, TextField, FloatField, BooleanField, DateTimeField
from backend.data.database import db

logger = logging.getLogger(__name__)

class BaseModel(Model):
    """Базова модель для всіх Peewee-моделей."""
    class Meta:
        database = db

class Product(BaseModel):
    """
    Сутність товару.

    Атрибути:
      id             – первинний ключ (із Prozorro API),
      identifier     – текст у дужках (код товару),
      title          – назва (нижній регістр),
      price          – ціна (з Hotline або None),
      characteristics– JSON-рядок зі списком характеристик,
      suitable       – чи відповідає «must-have» вимогам,
      created_at     – час створення запису.
    """
    id = CharField(primary_key=True)
    identifier = CharField()
    title = TextField()
    price = FloatField(null=True)
    characteristics = TextField()
    suitable = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)

    def to_dict(self) -> dict:
        """Повертає словник для JSON-відповіді."""
        return {
            'id': self.id,
            'identifier': self.identifier,
            'title': self.title,
            'price': self.price,
            'characteristics': json.loads(self.characteristics),
        }
