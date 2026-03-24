# ~/Desktop/rento/src/first-draft/setup_db.py

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from ..database import Base

# Import all models so SQLAlchemy registers every table before create_all
from ..models import (
    User,
    ObjectivePreferences,
    SubjectivePreferences,
    NegotiationPreferences,
    NotificationPreferences,
    NeighborInfo,
    Apartment,
    Match,
    Vote,
    Message,
    Agent1Log,
    Agent2Log,
    Agent3Log,
    Notification,
)

engine_url = os.environ.get("DATABASE_URL")
if not engine_url:
    raise RuntimeError("Set DATABASE_URL before running setup_db.py")

from sqlalchemy import create_engine
engine = create_engine(engine_url)
Base.metadata.create_all(engine)

print("Tables created:")
for table in Base.metadata.sorted_tables:
    print(f"  {table.name}")