# 大华适配专网平台 GA/T 1400 对接设计方案

> 版本：v0.3　日期：2026-08-12　状态：评审中（新增大华官方《公安视频图像信息数据库对接协议 V1.2》要点，多数联调未知项已消除）
>
> 依据标准：GA/T 1400.2—2017《公安视频图像信息应用系统 第2部分：应用平台技术要求》、GA/T 1400.4—2017《第4部分：接口协议要求》、GA/T 1400.3—2017《第3部分：数据库技术要求》（纸质版扫描件，位于项目外 `D:\develop\新建文件夹\`，已提取为 `_part2.txt / _part3.txt / _part4.txt`）

---

## 1. 背景与目标

松阳大队大货车管理平台需要与**大华适配专网平台**（外部上级平台）通过 GA/T 1400 协议对接：

- **角色**：我方为订阅方（发起主动注册），大华平台为被订阅方（视图库）。
- **对接方式**：我方主动注册到大华平台 → 提交订阅 → 大华平台实时推送**过车记录**到我方回调地址 → 我方解析、落库、与现有大货车档案联动。
- **协议版本**：GA/T 1400.4—2017 原版（无 2019 修改单的 HTTPS/签名要求）。
- **网络**：双方均部署在公安网侧，互通无边界问题；我方回调地址需能被大华平台访问。

**业务价值**：将大华平台汇聚的卡口过车数据接入平台，可按车牌匹配现有大货车档案，实现车辆轨迹追踪、重点车辆过车提醒、预警联动等。

---

## 2. 协议要点（GA/T 1400.4—2017）

### 2.1 接口清单（本方案用到的部分）

| 功能 | URI | 方法 | 请求体 | 响应体 |
| --- | --- | --- | --- | --- |
| 注册 | `/VIID/System/Register` | POST | `{"RegisterObject":{"DeviceID":"20位设备ID"}}` | `ResponseStatus` |
| 注销 | `/VIID/System/UnRegister` | POST | `{"UnRegisterObject":{"DeviceID":"..."}}` | `ResponseStatus` |
| 保活 | `/VIID/System/Keepalive` | POST | `{"KeepaliveObject":{"DeviceID":"..."}}` | `ResponseStatus` |
| 校时 | `/VIID/System/Time` | GET | 无 | `SystemTime` |
| 批量订阅 | `/VIID/Subscribes` | POST | `{"SubscribeList":{"SubscribeObject":{...}}}` | `ResponseStatusList` |
| 取消订阅 | `/VIID/Subscribes/{SubscribeID}` | PUT | `Subscribe`（OperateType=1） | `ResponseStatus` |
| 通知接收 | `/VIID/SubscribeNotifications` | POST | `{"SubscribeNotificationList":{"SubscribeNotificationObject":{...}}}` | `ResponseStatusList` |

- Content-Type：`application/*+JSON`（大华实际为 `application/json`）。
- 所有请求（含回调通知的响应）均走 **HTTP 摘要认证**（RFC 2617）：首次请求返回 401 + `WWW-Authenticate` 挑战，带 `Authorization` 重发。服务端 nonce 超过 3600s 应重置（客户端需处理 nonce 过期重认证）。

### 2.2 时序与容错规则（标准原文 5.1.1、5.3.5）

1. **注册失败**：延迟 300s 内随机时间后重新注册。
2. **保活**：注册成功后 90s 内无任何交互消息即心跳保活（大华平台通行做法为每分钟一次，可配置）。
3. **通知重传（对方平台行为，我方要适配）**：对方推送通知后 5s 未收到我方响应 → 重传；连续 3 次失败 → 对方缓存并重新注册后补传。**我方回调必须快速响应 200，落库等耗时操作异步化**。
4. **补传去重**：对方缓存补传可能重复，我方按 `MotorVehicleID` 全局唯一去重。

### 2.3 订阅对象（表 A.21，附录 C.19）

| 字段 | 说明 | 我方取值 |
| --- | --- | --- |
| SubscribeID | 订阅标识（对方生成，我方生成格式：12位机构代码+`03`+`yyyyMMddHHmmss`+5位流水） | 自动生成 |
| Title | 订阅标题 | "松阳大队大货车管理平台订阅过车记录" |
| SubscribeDetail | **订阅类别，可多个用逗号分隔** | `13`（自动采集的车辆信息=过车记录）；如需事件可加 `1,2`（案事件目录/内容）、`8`（单个卡口记录） |
| ResourceURI | 订阅资源路径：卡口ID、设备ID、采集内容ID、行政区编号、目标视图库ID等 | **已确认**：填订阅资源 ID（20 位数字，示例 `33110000005030000001`） |
| ApplicantName / ApplicantOrg | 申请人 / 申请单位 | 配置项 |
| BeginTime / EndTime | 订阅有效期 | 当前时间 ~ +N 天（到期自动续订） |
| ReceiveAddr | **我方回调地址** | `http://{我方IP}:{端口}/VIID/SubscribeNotifications` |
| ReportInterval | 信息上报间隔（秒，≤0 不限制） | 0 |
| OperateType | 0=订阅 1=取消订阅 | 0 |

> **DeviceID 编码规则**（GA/T 1400.1 DE01195，`DeviceIDType` string(20)）：20 位数字 = 8 位中心编码 + 2 位行业编码 + 2 位类型编码 + 8 位序号。对方下发的资源 ID 示例 `33110000005030000001` 即按此规则（`33110000 | 00 | 50 | 30000001`）。我方自定义 DeviceID 照此格式生成（见第 7 章配置）。

### 2.4 通知对象（表 A.22，附录 C.20）

`SubscribeNotification`：`NotificationID`、`SubscribeID`、`Title`、`TriggerTime`、`InfoIDs`（信息标识集合，分号分隔）+ 各数据集（`PersonObjectList`、`FaceObjectList`、**`MotorVehicleObjectList`** 等）。

**过车记录即 `MotorVehicle` 对象**（表 A.12，71 个字段），本方案落库核心字段：

| 字段 | 说明 | 备注 |
| --- | --- | --- |
| MotorVehicleID | 车辆全局唯一标识 | **去重主键** |
| InfoKind | 信息分类（0自动/1人工） | |
| DeviceID / TollgateID | 设备编码 / 关联卡口编号 | |
| PlateNo / PlateClass / PlateColor | 车牌号 / 号牌种类 / 车牌颜色 | 匹配现有档案用 |
| VehicleClass / VehicleColor | 车辆类型 / 车身颜色 | |
| PassTime | 经过时刻（过车时间） | |
| NameOfPassedRoad | 经过道路名称 | |
| LaneNo / Speed / Direction | 车道号 / 行驶速度 / 行驶方向 | |
| HasPlate / IsSuspicious | 有无车牌 / 是否可疑车 | |
| StorageUrl1~5 | 近景/车牌/远景/合成图/缩略图照片地址 | URI 命名规则，需下载存储或代理展示 |
| SubImageList | 子图像列表 | |

### 2.5 应答状态对象（表 A.28）

`ResponseStatus`：`RequestURL`、`StatusCode`（**0=OK**，1~9 为各类错误）、`StatusString`、`Id`（POST 创建成功后返回新 ID）、`LocalTime`（可用于校时）。

### 2.6 大华平台报文差异要点（来源：大华官方《公安视频图像信息数据库对接协议 V1.2》）

> 该文档随开源项目 nanguantong/gat-1400 下载，已存 `docs/gat1400-ref/大华公安视频图像信息数据库协议_v1.2.pdf`（文本版 `dahuaprotocol.txt`），是联调与开发的第一参照物。

**认证与注册**
- 摘要认证：Digest + **MD5**、`realm="myrealm"`、`qop="auth"`；用户名/口令由对方**口头或文件分配**（流程同 RFC 2617：401 挑战 → 带 Authorization 重发）。
- 注册成功后**每次请求必须带请求头 `User-Identify`，值 = DeviceID**（大华特有要求，标准未提）。
- 注册有效期一般 **5 分钟**，期间任何成功请求都会触发保活重置。

**报文结构（与大华实际一致的 JSON 命名）**
- 对象体：`{"RegisterObject":{"DeviceID":"..."}}`、`{"UnRegisterObject":{...}}`、保活示例为 `{"DeviceID":"..."}`（**大华文档保活示例无 KeepaliveObject 包装，联调时以带包装先试，两种都做兼容**）。
- 列表体统一为 `XxxListObject: { XxxObject: [ ... ] }` 结构：`SubscribeListObject/SubscribeObject[]`、`MotorVehicleListObject/MotorVehicleObject[]`、`SubscribeNotificationListObject/SubscribeNotificationObject[]`、`ResponseStatusListObject/ResponseStatusObject[]`（**ResponseStatusObject 在注册等场景可能是对象而非数组，解析必须双兼容**）。
- 子图像：`SubImageList: { SubImageInfoObject: [...] }`。

**字段与格式**
- **时间格式统一 `yyyyMMddHHmmss`**（如 `20171220204451`），订阅 BeginTime/EndTime、TriggerTime、PassTime 均如此。
- 请求/响应 UTF-8；`Content-Type: application/json;charset=utf-8`；`Accept` 同。
- 批量订阅示例：`SubscribeDetail="13"`、`Title="过车"`、`ResourceURI="00330102015030000004"`（对方文档示例为 19 位，我方按对方下发的 20 位资源 ID 填写）。
- `MotorVehicleID` 为 38 位字符串（`330101010012100000010220171018080608022060269899`），表字段 VARCHAR(64) 已留足。
- `StorageUrl1~5` 示例为相对路径（`9527/upload/122/...`），真实部署可能给完整 URL 或平台内路径，联调需确认拼接规则。

**接口差异**
- 大华文档将校时 `GET /VIID/System/Time` 描述为 POST（标准为 GET），联调时两者都兼容。
- 取消订阅：`PUT /VIID/Subscribes/<SubscribeID>`，消息体 `{"SubscribeObject":{"SubscribeCancelOrg":"省公安厅","SubscribeCancelPerson":"admin","CancelTime":"...","CancelReason":"..."}}`。

---

## 3. 总体架构

### 3.1 部署拓扑

```
┌───────────────────────────── 公安网 ─────────────────────────────┐
│                                                                  │
│  大华适配专网平台（视图库）                                          │
│   ┌──────────┐   注册/保活/订阅(摘要认证)    ┌──────────────┐      │
│   │  大华平台  │ ─────────────────────────→ │  我方接入服务  │      │
│   │  :8080   │                              │  (nginx)      │      │
│   └──────────┘   通知推送(摘要认证)          │  :12580       │      │
│       │            POST /VIID/SubscribeNotifications           │
│       └────────────────────────────────────────────────→       │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 两种部署形态对比

| 维度 | A. 嵌入现有后端（推荐） | B. 独立接入进程 |
| --- | --- | --- |
| 部署位置 | 现有 FastAPI 服务内新增 `module_gat1400`，nginx 把 `/VIID/*` 转发到后端 | 独立 Python 进程（同代码仓库，独立入口/端口） |
| 复用 | 配置、日志、Redis、APScheduler、SQLAlchemy、传输加密基建全部复用 | 需自建配置/日志/Redis 客户端 |
| 数据落库 | 直接写库（同事务） | 需内网 HTTP 推送或共享 DB |
| 安全隔离 | `/VIID/*` 需在 PreAuth 白名单 + 传输加密中间件排除 | 天然隔离，不触碰现有安全策略 |
| 运维 | 一个进程 | 两个进程 |
| 适用 | 平台本身就在公安网，同网部署 | 平台不在公安网 / 要求严格解耦 |

**推荐方案 A**：用户已确认平台部署在公安网，与外部视图库同网，嵌入可最大化复用现有基建，数据直落库最简洁。若后续有解耦需求，可平滑拆分为方案 B（协议层与业务层接口不变）。

---

## 4. 模块设计（方案 A：module_gat1400）

沿用项目现有四层结构（controller / service / dao / entity）：

```
ruoyi-fastapi-backend/module_gat1400/
├── controller/
│   ├── gat1400_connect_controller.py   # 对接状态管理：连接/重连/注销、状态查询（管理端）
│   ├── gat1400_subscribe_controller.py # 订阅管理：创建订阅、取消订阅、订阅列表
│   ├── pass_record_controller.py       # 过车记录查询、导出（业务端）
│   └── viid_notify_controller.py       # ★ 回调接收 POST /VIID/SubscribeNotifications（白名单放行）
├── service/
│   ├── gat1400_session_service.py      # 注册→保活→注销状态机、摘要认证 HTTP 客户端
│   ├── gat1400_subscribe_service.py    # 订阅/续订/取消、订阅状态持久化
│   ├── gat1400_notify_service.py       # 通知接收→解析→异步落库→去重
│   └── pass_record_service.py          # 过车记录查询/导出/与车辆档案联动
├── dao/
│   ├── gat1400_subscribe_dao.py
│   ├── gat1400_notify_log_dao.py
│   └── pass_record_dao.py
└── entity/
    ├── do/
    │   ├── gat1400_connect_do.py       # gat1400_connect 对接状态表
    │   ├── gat1400_subscribe_do.py     # gat1400_subscribe 订阅配置表
    │   ├── gat1400_notify_log_do.py    # gat1400_notify_log 原始报文日志表
    │   └── pass_record_do.py           # truck_pass_record 过车记录表
    └── vo/
        ├── subscribe_vo.py             # 订阅入参/出参（驼峰）
        └── pass_record_vo.py           # 过车记录查询出参
```

### 4.1 关键实现点

1. **摘要认证 HTTP 客户端**（`common/http_digest_client.py` 或 service 内部实现）：
   - 用 `httpx`（项目已依赖）实现 RFC 2617 Digest（MD5、realm/qop 取服务端 `WWW-Authenticate` 挑战值，按大华文档），自动处理 401 挑战 → 计算 `Authorization` → 重发；nonce 过期（3600s）自动重认证。
   - **注册成功后所有请求自动带 `User-Identify` 头（值=DeviceID）**（大华要求）。
   - 参考开源实现：`haoxianrui/gat1400`（Java，已对接大华平台成功）的摘要算法与报文格式、`nanguantong/gat-1400`（C++，MIT）的 `gat1400_viid.cpp` 会话实现，作为协议蓝本对照。
2. **注册保活状态机**（`gat1400_session_service`）：
   - 状态：`UNREGISTERED → REGISTERING → ONLINE → (失败回退) / OFFLINE`。
   - 注册失败按 300s 内随机延迟重试（指数退避封顶）。
   - APScheduler 定时任务保活（默认 60s 间隔，可配置；标准要求 90s 内无交互即保活）。
   - 状态落 `gat1400_connect` 表 + Redis 缓存，管理端可查看在线状态/最后保活时间。
3. **回调接收**（`viid_notify_controller`）：
   - 路由注册时加入 `PreAuth` 白名单（`exclude_routes`），传输加密中间件排除 `/VIID/*`（对方按 2017 原版明文+摘要认证访问）。
   - 校验摘要认证 → 解析 `SubscribeNotificationList` → **同步快速返回 `ResponseStatus(0=OK)`**，落库通过 `asyncio.create_task` 异步执行（注意：FastAPI 主进程内异步任务需挂到事件循环，或用独立 task 队列 + Redis Stream 消费者，与现有 `LogAggregatorService` 同模式）。
   - 摘要认证校验失败返回 401，让对方重传。
4. **过车记录落库与去重**：
   - 解析 `MotorVehicleObjectList`，逐条按 `MotorVehicleID` 唯一键 upsert（`INSERT ... ON DUPLICATE KEY UPDATE` / PG `ON CONFLICT`，兼容双数据库，与项目 SQL 风格一致）。
   - 原始报文全量存 `gat1400_notify_log`（JSON 文本），便于排查对方字段差异。
5. **与现有档案联动**：
   - `pass_record_service` 按 `PlateNo + PlateColor` 关联 `truck_vehicle`（车牌+颜色唯一键），展示"是否为本平台车辆、所属中队/主体"。
   - 预留扩展点：重点车辆过车提醒（后续需求，可在落库后触发）。
6. **照片处理**：`StorageUrl1~5` 为对方平台的图片 URI，公安网内可访问。一期只存 URL 并在前端 `<img>` 直接展示（对方需允许跨域或走我方 nginx 反代 `/gat1400/proxy-image`）；二期再做下载归档到自有文件模块。

---

## 5. 数据库设计

### 5.1 `truck_pass_record` 过车记录表

```sql
CREATE TABLE `truck_pass_record` (
  `id`             BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
  `motor_vehicle_id` VARCHAR(64) NOT NULL COMMENT '车辆全局唯一标识(去重键)',
  `info_kind`      TINYINT      DEFAULT NULL COMMENT '信息分类 0自动 1人工',
  `device_id`      VARCHAR(32)  DEFAULT NULL COMMENT '设备编码',
  `tollgate_id`    VARCHAR(32)  DEFAULT NULL COMMENT '关联卡口编号',
  `plate_no`       VARCHAR(32)  DEFAULT NULL COMMENT '车牌号',
  `plate_class`    VARCHAR(8)   DEFAULT NULL COMMENT '号牌种类',
  `plate_color`    VARCHAR(8)   DEFAULT NULL COMMENT '车牌颜色',
  `vehicle_class`  VARCHAR(8)   DEFAULT NULL COMMENT '车辆类型',
  `vehicle_color`  VARCHAR(8)   DEFAULT NULL COMMENT '车身颜色',
  `pass_time`      DATETIME     DEFAULT NULL COMMENT '过车时间',
  `name_of_passed_road` VARCHAR(64) DEFAULT NULL COMMENT '经过道路名称',
  `lane_no`        INT          DEFAULT NULL COMMENT '车道号',
  `speed`          INT          DEFAULT NULL COMMENT '行驶速度km/h',
  `direction`      VARCHAR(8)   DEFAULT NULL COMMENT '行驶方向',
  `has_plate`      TINYINT      DEFAULT NULL COMMENT '有无车牌',
  `is_suspicious`  TINYINT      DEFAULT NULL COMMENT '是否可疑车',
  `storage_url1`   VARCHAR(256) DEFAULT NULL COMMENT '近景照片URL',
  `storage_url2`   VARCHAR(256) DEFAULT NULL COMMENT '车牌照片URL',
  `storage_url3`   VARCHAR(256) DEFAULT NULL COMMENT '远景照片URL',
  `plate_reliability` VARCHAR(3) DEFAULT NULL COMMENT '号牌识别可信度',
  `raw_json`       JSON         DEFAULT NULL COMMENT '原始报文(便于排查)',
  `vehicle_id`     BIGINT       DEFAULT NULL COMMENT '关联本平台车辆档案ID(可为空)',
  `create_by`      VARCHAR(64)  DEFAULT '' COMMENT '创建者',
  `create_time`    DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`      VARCHAR(64)  DEFAULT '' COMMENT '更新者',
  `update_time`    DATETIME     DEFAULT NULL COMMENT '更新时间',
  `del_flag`       CHAR(1)      DEFAULT '0' COMMENT '删除标志 0正常 2删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_motor_vehicle_id` (`motor_vehicle_id`),
  KEY `idx_plate_no` (`plate_no`, `plate_color`),
  KEY `idx_pass_time` (`pass_time`),
  KEY `idx_device_id` (`device_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='GA/T1400过车记录表';
```

> 量级评估：单卡口过车约数千条/天，全区 6 中队规模日增量预计 ≤ 10 万条。**建议**：① 仅订阅本辖区卡口（ResourceURI 按行政区划限制）；② 保留周期可配置，超期记录定时归档/清理（后续迭代）。

### 5.2 `gat1400_subscribe` 订阅配置表

`id`、`subscribe_id`、`title`、`subscribe_detail`、`resource_uri`、`applicant_name`、`applicant_org`、`begin_time`、`end_time`、`receive_addr`、`operate_type`、`subscribe_status`、`cancel_reason`、`create_time`、`update_time`。

### 5.3 `gat1400_connect` 对接状态表（单行）

`device_id`（我方 20 位设备ID）、`platform_addr`（大华平台地址）、`register_status`、`last_register_time`、`last_keepalive_time`、`keepalive_count`、`error_message`、`update_time`。

### 5.4 `gat1400_notify_log` 通知原始日志表

`id`、`notification_id`、`subscribe_id`、`trigger_time`、`raw_body`（JSON）、`parse_status`（成功/失败/部分失败）、`record_count`、`create_time`。**此表是联调阶段排查对方字段差异的第一抓手，必做。**

---

## 6. 关键流程

### 6.1 注册保活状态机

```
启动 → 读配置 → REGISTERING（POST Register）
   ├─ 401 → 摘要认证重发 → 200(StatusCode=0) → ONLINE，启动保活定时器（60s）
   ├─ 失败 → 300s内随机延迟重试（指数退避，≤300s）
   └─ ONLINE 期间 Keepalive 失败连续 3 次 → OFFLINE → 重新注册（标准要求链路问题后重注册）
注销：应用停止/手动操作时 POST UnRegister → UNREGISTERED
```

### 6.2 订阅流程

1. 首次启动（或订阅配置变化）：`POST /VIID/Subscribes` 提交订阅，`OperateType=0`。
2. 成功后存 `gat1400_subscribe`，`SubscribeID` 来自 ResponseStatus.Id。
3. 定时检查 `EndTime`，到期前自动续订（新订阅，重新生成 SubscribeID）。
4. 取消订阅：`PUT /VIID/Subscribes/{SubscribeID}`，写入取消单位/人/时间/原因。
5. 我方收到通知后校验 `SubscribeID` 在有效订阅表内，否则拒绝并告警。

### 6.3 通知接收流程

```
大华平台 POST /VIID/SubscribeNotifications（摘要认证）
→ 认证通过（401则让对方重传）
→ 解析 SubscribeNotificationList
→ 同步：校验、拆出 MotorVehicleObjectList 数据量
→ 立即返回 ResponseStatus(0)         ← 200 必须快速（对方5s超时重传）
→ 异步：逐条 upsert truck_pass_record（按 MotorVehicleID 去重）
        → 写 gat1400_notify_log（原始报文+解析结果）
        → 匹配 truck_vehicle 回填 vehicle_id
        → 统计接收量写入 Redis 计数（监控用）
```

---

## 7. 配置设计

对接参数入 `sys_config` 字典表（管理端可改，重启后生效）或 `.env`（部署期固定），建议：

| 配置键 | 说明 | 默认 |
| --- | --- | --- |
| `gat1400.platform.addr` | 大华平台地址 `http://ip:port` | - |
| `gat1400.device.id` | 我方 20 位设备 ID（**可自定义**，按 DE01195 规则生成：中心编码8+行业2+类型2+序号8） | 建议 `33112400 00 50 30000001`（中心编码取松阳县 331124 扩展，类型编码 50 与对方资源 ID 一致） |
| `gat1400.auth.username / password` | 摘要认证账号（**对方分配**） | - |
| `gat1400.subscribe.detail` | 订阅类别 | `13` |
| `gat1400.subscribe.resource_uri` | 订阅资源 ID（20 位，已确认） | `33110000005030000001` |
| `gat1400.subscribe.applicant` | 申请人/申请单位 | - |
| `gat1400.subscribe.days` | 订阅有效期（天），到期自动续订 | `30` |
| `gat1400.keepalive.interval` | 保活间隔（秒） | `60` |
| `gat1400.receive.addr` | 我方回调地址（对方可访问） | `http://{内网IP}/VIID/SubscribeNotifications` |
| `gat1400.notify.async` | 通知落库是否异步 | `true` |
| `gat1400.record.retention_days` | 过车记录保留天数 | `90` |

---

## 8. 前端设计（新增 2 个页面）

1. **过车记录页** `views/truck/pass-record/index.vue`：
   - 查询条件：车牌号、过车时间范围、卡口/设备、是否本平台车辆。
   - 列表：车牌（点击跳车辆档案）、车牌颜色、车型、过车时间、道路、车道/车速、照片缩略图（点击放大）。
   - 列配置 + 导出（复用 `RightToolbar` / `download` 基建）。
   - 权限点：`truck:passrecord:query / export`，菜单挂到 truck 组，领导只读角色自然继承只读。
2. **对接状态页** `views/system/gat1400/index.vue`（或并入系统监控）：
   - 注册状态、最后保活时间、保活次数、订阅列表及有效期、今日接收量（Redis 计数）。
   - 操作：手动重连、手动注销、创建/取消订阅（仅大队管理员权限）。

---

## 9. 安全与运维

1. **摘要认证**：账号口令由对方分配，存配置不进代码；日志脱敏（复用现有 `LogSanitizeUtil`）。
2. **回调入口**：`/VIID/*` 在 PreAuth 白名单 + 传输加密排除，但**加签名校验**——仅接受摘要认证通过且请求方 IP 在大华平台网段白名单内的通知（nginx `allow/deny` + 应用层双保险）。
3. **幂等**：`MotorVehicleID` 唯一键保证补传/重传幂等。
4. **监控告警**：保活失败、注册失败、通知量突降（如 15 分钟为 0）、解析失败率升高 → 复用 `sys_oper_log` + 定时任务扫描，页面可见。
5. **数据保留**：过车记录保留周期可配置，定期清理，避免公安网存储压力。
6. **公安网离线部署**：若公安网不能访问外网，部署时需提前下载 `httpx` 等依赖离线包（wheel 目录），与项目现有离线部署方式保持一致。

---

## 10. 测试与联调计划

1. **Mock 大华平台**（`ruoyi-fastapi-test` 新增）：实现 401 摘要认证挑战 + Register/Keepalive/Subscribes 响应 + 主动 POST 通知（MotorVehicle 样例报文），用于本地回归。
2. **单元测试**（`tests/gat1400/`）：
   - 摘要认证头计算（对照 RFC 2617 向量/参考 Java 实现）。
   - 通知解析：合法/非法/缺字段报文 → 落库正确性。
   - 去重：同 MotorVehicleID 重复推送只留一条。
   - 数据映射：MotorVehicle → truck_pass_record 字段映射、车牌规范化（复用现有规则）。
3. **E2E**：Mock 平台推送 → 过车记录页展示 → 与车辆档案联动。
4. **联调阶段（关键里程碑）**：与大华平台方确认——设备 ID 登记、账号下发、**订阅类别与 ResourceURI 支持范围**、回调地址要求、真实报文样例 → 按样例校准字段映射。
5. **性能验证**：模拟 500 条/批通知，验证回调响应时间（<5s 硬指标）与落库吞吐。

---

## 11. 实施计划

| 阶段 | 内容 | 预估 |
| --- | --- | --- |
| P1 | 摘要认证客户端 + 注册/保活/注销状态机 + 配置 | 2~3 天 |
| P2 | 订阅/续订/取消 + 回调接收 + 通知解析落库 + 去重 | 2~3 天 |
| P3 | 过车记录查询/导出 API + 前端页面 + 对接状态页 | 2~3 天 |
| P4 | Mock 平台 + 单元测试 + E2E + 文档 | 2 天 |
| P5 | **与大华平台真实联调**（校准字段、订阅范围、保活节奏） | 3~5 天（取决于对方） |

总计约 2 周（不含联调等待时间）。

---

## 12. 风险与待确认事项

| # | 事项 | 影响 | 建议 |
| --- | --- | --- | --- |
| 1 | ~~DeviceID 申请~~ → **已确认可自定义**（按 DE01195 规则生成即可）；**摘要认证账号/口令**是否由对方分配仍未确认 | 认证环节 | 联调前向对方确认账号下发方式 |
| 2 | ~~订阅类别/ResourceURI~~ → **已确认支持类别 `13`**，ResourceURI 填订阅资源 ID（示例 `33110000005030000001`） | 基本解除 | 仍需对方提供《对接文档》与真实报文样例，校准字段大小写/时间格式 |
| 3 | 过车记录**日增量**与保留策略 | 存储与查询性能 | 联调期实测量级后定保留周期 |
| 4 | `StorageUrl` 照片跨域访问 | 前端展示 | 联调时验证；不通则加 nginx 代理 |
| 5 | 对方是否按 2017 原版（明文+摘要认证）而非修改单（HTTPS） | 影响安全配置 | 以对方对接文档为准，若要求 HTTPS 需补证书 |
| 6 | 通知量大时的回调超时（5s 硬指标） | 对方重传风暴 | 落库强制异步 + 消费队列削峰 |
| 7 | 公安网离线环境依赖安装 | 部署 | 提前准备离线 wheel 包 |

---

## 13. 参考

- 标准原文：`_part2.txt`（平台要求）、`_part3.txt`（对象定义，附录 A/B/C）、`_part4.txt`（接口协议，第 5/7/9 章及附录 A/B）
- **大华官方《公安视频图像信息数据库对接协议 V1.2》**：`docs/gat1400-ref/大华公安视频图像信息数据库协议_v1.2.pdf`（文本版 `dahuaprotocol.txt`，含全部接口示例报文，对接第一参照物）
- 开源参考实现（协议蓝本）：
  - `haoxianrui/gat1400`（Java/SpringBoot，已成功对接大华视频专网平台）：https://github.com/haoxianrui/gat1400
  - `nanguantong/gat-1400`（C++，MIT License，50★，2018~2020 年维护，`doc/` 目录附带大华协议文档与 4 份国标 PDF）：https://github.com/nanguantong/gat-1400
