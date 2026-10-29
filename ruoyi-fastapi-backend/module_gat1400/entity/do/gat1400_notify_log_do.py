from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text

from config.database import Base


class Gat1400NotifyLog(Base):
    __tablename__ = 'gat1400_notify_log'
    __table_args__ = {'comment': 'GA/T1400通知原始报文日志表'}

    notify_log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    notification_id = Column(String(64))
    subscribe_id = Column(String(64))
    trigger_time = Column(DateTime)
    parse_status = Column(String(20), nullable=False, server_default='success')
    record_count = Column(Integer, nullable=False, server_default='0')
    error_message = Column(String(500), server_default="''")
    raw_body = Column(Text)
    create_time = Column(DateTime, default=datetime.now)
