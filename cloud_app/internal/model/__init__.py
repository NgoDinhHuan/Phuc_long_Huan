from sqlalchemy import BigInteger, Column, JSON, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Feature(Base):
    __tablename__ = 'pg_features'
    id = Column(BigInteger, primary_key=True)
    name = Column(Text, nullable=False, comment='Name of feature')
    description = Column(Text, comment='feature description')
    config_map = Column(JSON)
