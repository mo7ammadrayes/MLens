from backend.database.models import Base
from backend.database.session import engine

Base.metadata.create_all(engine)

