from sqlalchemy import Column, String, ForeignKey, JSON, Enum, DateTime
from sqlalchemy.sql import func

class Function(Base):
    __tablename__ = "functions"
    
    uid = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    grid_uid = Column(String, ForeignKey("grids.uid"), nullable=False)
    script_path = Column(String, nullable=False)
    artifactory_url = Column(String)
    resource_requirements = Column(JSON, nullable=False)
    docker_image = Column(String, default="default")
    status = Column(Enum(FunctionStatus), default=FunctionStatus.PENDING)
    created_at = Column(DateTime, default=func.utcnow())
    updated_at = Column(DateTime, default=func.utcnow(), onupdate=func.utcnow())
    started_at = Column(DateTime)
    ended_at = Column(DateTime) 