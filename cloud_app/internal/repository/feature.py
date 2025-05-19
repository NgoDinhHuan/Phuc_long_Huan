from sqlalchemy.orm import Session
from cloud_app.internal.model import Feature


def get_feature_by_name(session: Session, name: str):
    res = session.query(Feature).filter(Feature.name == name).first()
    return res
