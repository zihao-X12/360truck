from datetime import datetime

from sqlalchemy import CHAR, BigInteger, Column, Date, DateTime, Integer, Numeric, String, Text, UniqueConstraint

from config.database import Base


class TruckOwner(Base):
    __tablename__ = 'truck_owner'
    __table_args__ = {'comment': '大货车归属主体表'}

    owner_id = Column(BigInteger, primary_key=True, autoincrement=True)
    owner_type = Column(String(20), nullable=False)
    owner_name = Column(String(100), nullable=False)
    credit_code = Column(String(32), unique=True)
    id_card_no = Column(String(32), unique=True)
    dept_id = Column(BigInteger, nullable=False)
    contact_name = Column(String(50))
    contact_phone = Column(String(30))
    address = Column(String(255))
    status = Column(CHAR(1), nullable=False, server_default='0')
    remark = Column(String(500))
    create_by = Column(String(64), server_default="''")
    create_time = Column(DateTime, default=datetime.now)
    update_by = Column(String(64), server_default="''")
    update_time = Column(DateTime)
    del_flag = Column(CHAR(1), nullable=False, server_default='0')


class TruckVehicle(Base):
    __tablename__ = 'truck_vehicle'
    __table_args__ = (
        UniqueConstraint('plate_no', 'plate_color', name='uk_truck_vehicle_plate'),
        {'comment': '大货车车辆档案表'},
    )

    vehicle_id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_name = Column(String(100))
    plate_no = Column(String(20), nullable=False)
    plate_color = Column(String(20), nullable=False)
    vehicle_type = Column(String(30))
    vehicle_brand = Column(String(100))
    vin = Column(String(32), unique=True)
    rated_load = Column(Numeric(10, 2))
    source_type = Column(String(20))
    motor_owner_name = Column(String(100))
    driver_name = Column(String(50))
    driver_phone = Column(String(30))
    affiliated_company = Column(String(100))
    insurance_status = Column(String(100))
    insurance_info = Column(String(255))
    owner_id = Column(BigInteger)
    owner_type = Column(String(20))
    dept_id = Column(BigInteger, nullable=False)
    photo_file_id = Column(String(36))
    vehicle_status = Column(String(20), nullable=False, server_default='normal')
    supervision_flag = Column(CHAR(1), nullable=False, server_default='0')
    warning_level = Column(String(20))
    missing_device_count = Column(Integer, nullable=False, server_default='0')
    remark = Column(String(500))
    create_by = Column(String(64), server_default="''")
    create_time = Column(DateTime, default=datetime.now)
    update_by = Column(String(64), server_default="''")
    update_time = Column(DateTime)
    del_flag = Column(CHAR(1), nullable=False, server_default='0')


class TruckVehicleDevice(Base):
    __tablename__ = 'truck_vehicle_device'
    __table_args__ = (UniqueConstraint('vehicle_id', 'device_type', name='uk_truck_vehicle_device'),)

    device_id = Column(BigInteger, primary_key=True, autoincrement=True)
    vehicle_id = Column(BigInteger, nullable=False)
    device_type = Column(String(30), nullable=False)
    product_name = Column(String(100))
    brand = Column(String(100))
    install_date = Column(Date)
    status = Column(CHAR(1), nullable=False, server_default='0')
    remark = Column(String(500))
    create_by = Column(String(64), server_default="''")
    create_time = Column(DateTime, default=datetime.now)
    update_by = Column(String(64), server_default="''")
    update_time = Column(DateTime)


class TruckVehicleOwnerHistory(Base):
    __tablename__ = 'truck_vehicle_owner_history'

    history_id = Column(BigInteger, primary_key=True, autoincrement=True)
    vehicle_id = Column(BigInteger, nullable=False)
    old_owner_id = Column(BigInteger)
    new_owner_id = Column(BigInteger)
    old_dept_id = Column(BigInteger)
    new_dept_id = Column(BigInteger)
    change_reason = Column(String(255))
    change_time = Column(DateTime, nullable=False, default=datetime.now)
    change_by = Column(String(64), nullable=False, server_default="''")


class TruckWarningRule(Base):
    __tablename__ = 'truck_warning_rule'

    rule_id = Column(BigInteger, primary_key=True, autoincrement=True)
    rule_name = Column(String(100), nullable=False, unique=True)
    required_device_types = Column(Text)
    level_one_threshold = Column(Integer, nullable=False, server_default='2')
    level_two_threshold = Column(Integer, nullable=False, server_default='1')
    status = Column(CHAR(1), nullable=False, server_default='0')
    create_by = Column(String(64), server_default="''")
    create_time = Column(DateTime, default=datetime.now)
    update_by = Column(String(64), server_default="''")
    update_time = Column(DateTime)
    remark = Column(String(500))
