from datetime import datetime

from sqlalchemy import CHAR, BigInteger, Column, DateTime, Integer, String

from config.database import Base


class Gat1400Connect(Base):
    __tablename__ = 'gat1400_connect'
    __table_args__ = {'comment': 'GA/T1400对接状态表（单行）'}

    connect_id = Column(BigInteger, primary_key=True, autoincrement=True)
    register_status = Column(String(20), nullable=False, server_default='unregistered')
    fail_count = Column(Integer, nullable=False, server_default='0')
    last_register_time = Column(DateTime)
    last_keepalive_time = Column(DateTime)
    keepalive_count = Column(BigInteger, nullable=False, server_default='0')
    error_message = Column(String(500), server_default="''")
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime)
    del_flag = Column(CHAR(1), nullable=False, server_default='0')
