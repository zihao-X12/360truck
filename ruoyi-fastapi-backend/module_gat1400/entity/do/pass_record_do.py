from datetime import datetime

from sqlalchemy import CHAR, JSON, BigInteger, Column, DateTime, Integer, String

from config.database import Base


class TruckPassRecord(Base):
    __tablename__ = 'truck_pass_record'
    __table_args__ = {'comment': 'GA/T1400过车记录表'}

    record_id = Column(BigInteger, primary_key=True, autoincrement=True)
    motor_vehicle_id = Column(String(64), nullable=False, unique=True)
    info_kind = Column(Integer)
    device_id = Column(String(64))
    tollgate_id = Column(String(64))
    plate_no = Column(String(32))
    plate_class = Column(String(16))
    plate_color = Column(String(16))
    vehicle_class = Column(String(16))
    vehicle_color = Column(String(16))
    pass_time = Column(DateTime)
    name_of_passed_road = Column(String(64))
    lane_no = Column(Integer)
    speed = Column(Integer)
    direction = Column(String(16))
    has_plate = Column(CHAR(1))
    is_suspicious = Column(CHAR(1))
    storage_url1 = Column(String(512))
    storage_url2 = Column(String(512))
    storage_url3 = Column(String(512))
    storage_url4 = Column(String(512))
    storage_url5 = Column(String(512))
    plate_reliability = Column(String(8))
    raw_json = Column(JSON)
    vehicle_id = Column(BigInteger)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime)
