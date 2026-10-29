from datetime import datetime

from sqlalchemy import CHAR, Column, DateTime, String

from config.database import Base


class Gat1400Subscribe(Base):
    __tablename__ = 'gat1400_subscribe'
    __table_args__ = {'comment': 'GA/T1400订阅配置表'}

    subscribe_id = Column(String(64), primary_key=True)
    title = Column(String(256), nullable=False)
    subscribe_detail = Column(String(128), nullable=False)
    resource_uri = Column(String(256), nullable=False)
    applicant_name = Column(String(64))
    applicant_org = Column(String(128))
    begin_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    receive_addr = Column(String(256), nullable=False)
    operate_type = Column(CHAR(1), nullable=False, server_default='0')
    subscribe_status = Column(CHAR(1), nullable=False, server_default='0')
    cancel_org = Column(String(128))
    cancel_person = Column(String(32))
    cancel_time = Column(DateTime)
    cancel_reason = Column(String(64))
    create_by = Column(String(64), server_default="''")
    create_time = Column(DateTime, default=datetime.now)
    update_by = Column(String(64), server_default="''")
    update_time = Column(DateTime)
    del_flag = Column(CHAR(1), nullable=False, server_default='0')
