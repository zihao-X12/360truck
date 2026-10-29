-- M10 GA/T1400 订阅、通知日志、过车记录表（MySQL 8）
START TRANSACTION;

-- 订阅配置表
CREATE TABLE IF NOT EXISTS `gat1400_subscribe` (
  `subscribe_id`       VARCHAR(64)  NOT NULL COMMENT '订阅标识（平台返回ID）',
  `title`              VARCHAR(256) NOT NULL COMMENT '订阅标题',
  `subscribe_detail`   VARCHAR(128) NOT NULL COMMENT '订阅类别，多个用逗号分隔',
  `resource_uri`       VARCHAR(256) NOT NULL COMMENT '订阅资源路径',
  `applicant_name`     VARCHAR(64)  DEFAULT '' COMMENT '申请人',
  `applicant_org`      VARCHAR(128) DEFAULT '' COMMENT '申请单位',
  `begin_time`         DATETIME     NOT NULL COMMENT '订阅开始时间',
  `end_time`           DATETIME     NOT NULL COMMENT '订阅结束时间',
  `receive_addr`       VARCHAR(256) NOT NULL COMMENT '信息接收地址',
  `operate_type`       CHAR(1)      NOT NULL DEFAULT '0' COMMENT '操作类型 0订阅 1取消订阅',
  `subscribe_status`   CHAR(1)      NOT NULL DEFAULT '0' COMMENT '订阅状态 0订阅中 1已取消 2到期',
  `cancel_org`         VARCHAR(128) DEFAULT '' COMMENT '订阅取消单位',
  `cancel_person`      VARCHAR(32)  DEFAULT '' COMMENT '订阅取消人',
  `cancel_time`        DATETIME     DEFAULT NULL COMMENT '取消时间',
  `cancel_reason`      VARCHAR(64)  DEFAULT '' COMMENT '取消原因',
  `create_by`          VARCHAR(64)  DEFAULT '' COMMENT '创建者',
  `create_time`        DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`          VARCHAR(64)  DEFAULT '' COMMENT '更新者',
  `update_time`        DATETIME     DEFAULT NULL COMMENT '更新时间',
  `del_flag`           CHAR(1)      NOT NULL DEFAULT '0' COMMENT '删除标志 0正常 2删除',
  PRIMARY KEY (`subscribe_id`),
  KEY `idx_subscribe_end_time` (`end_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='GA/T1400订阅配置表';

-- 通知原始报文日志表
CREATE TABLE IF NOT EXISTS `gat1400_notify_log` (
  `notify_log_id`    BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
  `notification_id`  VARCHAR(64)  DEFAULT '' COMMENT '通知标识',
  `subscribe_id`     VARCHAR(64)  DEFAULT '' COMMENT '订阅标识',
  `trigger_time`     DATETIME     DEFAULT NULL COMMENT '触发时间',
  `parse_status`     VARCHAR(20)  NOT NULL DEFAULT 'success' COMMENT '解析状态 success/subscribe_mismatch/no_vehicle_data',
  `record_count`     INT          NOT NULL DEFAULT 0 COMMENT '本次落库过车记录数',
  `error_message`    VARCHAR(500) DEFAULT '' COMMENT '错误信息',
  `raw_body`         TEXT         COMMENT '原始报文JSON',
  `create_time`      DATETIME     DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`notify_log_id`),
  KEY `idx_notification_id` (`notification_id`),
  KEY `idx_subscribe_id` (`subscribe_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='GA/T1400通知原始报文日志表';

-- 过车记录表
CREATE TABLE IF NOT EXISTS `truck_pass_record` (
  `record_id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
  `motor_vehicle_id`   VARCHAR(64)  NOT NULL COMMENT '车辆全局唯一标识（去重键）',
  `info_kind`          TINYINT      DEFAULT NULL COMMENT '信息分类 0自动 1人工',
  `device_id`          VARCHAR(64)  DEFAULT NULL COMMENT '设备编码',
  `tollgate_id`        VARCHAR(64)  DEFAULT NULL COMMENT '关联卡口编号',
  `plate_no`           VARCHAR(32)  DEFAULT NULL COMMENT '车牌号',
  `plate_class`        VARCHAR(16)  DEFAULT NULL COMMENT '号牌种类',
  `plate_color`        VARCHAR(16)  DEFAULT NULL COMMENT '车牌颜色（GA/T1400色号，联调校准）',
  `vehicle_class`      VARCHAR(16)  DEFAULT NULL COMMENT '车辆类型',
  `vehicle_color`      VARCHAR(16)  DEFAULT NULL COMMENT '车身颜色',
  `pass_time`          DATETIME     DEFAULT NULL COMMENT '过车时间',
  `name_of_passed_road` VARCHAR(64) DEFAULT NULL COMMENT '经过道路名称',
  `lane_no`            INT          DEFAULT NULL COMMENT '车道号',
  `speed`              INT          DEFAULT NULL COMMENT '行驶速度km/h',
  `direction`          VARCHAR(16)  DEFAULT NULL COMMENT '行驶方向',
  `has_plate`          CHAR(1)      DEFAULT NULL COMMENT '有无车牌',
  `is_suspicious`      CHAR(1)      DEFAULT NULL COMMENT '是否可疑车',
  `storage_url1`       VARCHAR(512) DEFAULT NULL COMMENT '近景照片URL',
  `storage_url2`       VARCHAR(512) DEFAULT NULL COMMENT '车牌照片URL',
  `storage_url3`       VARCHAR(512) DEFAULT NULL COMMENT '远景照片URL',
  `storage_url4`       VARCHAR(512) DEFAULT NULL COMMENT '合成图URL',
  `storage_url5`       VARCHAR(512) DEFAULT NULL COMMENT '缩略图URL',
  `plate_reliability`  VARCHAR(8)   DEFAULT NULL COMMENT '号牌识别可信度',
  `raw_json`           JSON         DEFAULT NULL COMMENT '原始报文（便于联调排查）',
  `vehicle_id`         BIGINT       DEFAULT NULL COMMENT '匹配到的本平台车辆档案ID',
  `create_time`        DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_time`        DATETIME     DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`record_id`),
  UNIQUE KEY `uk_motor_vehicle_id` (`motor_vehicle_id`),
  KEY `idx_plate_no` (`plate_no`),
  KEY `idx_pass_time` (`pass_time`),
  KEY `idx_device_id` (`device_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='GA/T1400过车记录表';

COMMIT;
