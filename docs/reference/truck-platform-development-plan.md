# 县域大货车基础信息管理平台开发计划

## 1. 阶段目标

本阶段目标是完成系统设计与开发准备，明确 MVP 范围、模块边界、数据模型、接口清单、前端页面、权限方案、测试策略和实施顺序，为后续编码提供可执行依据。

当前代码基于 `RuoYi-Vue3-FastAPI`，通用后台能力已经具备。开发重点不是重建基础平台，而是在现有框架上新增“大货车管理”业务域，并复用已有用户、角色、菜单、部门、字典、日志、文件、代码生成、Excel 工具和数据权限能力。

## 2. MVP 范围

### 2.0 已确认开发准备条件

1. 数据库选择：MySQL 8 优先，PostgreSQL 作为兼容目标。
2. 真实 Excel 台账：根目录已有 `工程车排查表.xlsx`，当前包含 `Sheet1`、`Sheet2`、`Sheet3`。
3. 组织架构：松阳大队下设 6 个中队：西屏中队、古市中队、江南中队、象溪中队、大东坝中队、玉岩中队。
4. 预设角色：
   - 大队管理员：同时承担系统管理员能力，拥有全量数据和系统配置权限。
   - 中队管理员：仅管理本中队辖区数据。
   - 领导权限：只读查看看板、查询和导出，不允许新增、修改、删除。
5. 车辆照片：复用现有文件管理模块。
6. 导入错误反馈：按真实校验错误逐行反馈，错误信息需明确到字段和值。
7. README：不需要保留原始上游项目说明，以当前“大货车管理平台”说明为准。

### 2.1 本期必须交付

1. 业务字典配置
   - 车辆类型
   - 车牌颜色
   - 车辆状态
   - 来源标识
   - 归属主体类型
   - 安全设备类型
   - 预警等级

2. 辖区主体管理
   - 运输企业管理
   - 个人车主管理
   - 主体关联所属中队部门
   - 主体详情展示名下车辆

3. 车辆档案管理
   - 车辆基础信息 CRUD
   - 车牌号 + 车牌颜色唯一校验
   - VIN 自动大写和 17 位校验
   - 工地名称、车辆品牌、机动车所有人、驾驶员、挂靠公司、保险信息维护
   - 车辆照片上传
   - 车辆归属主体关联
   - 车辆安全设备增删改
   - 车辆归属变更历史记录

4. Excel 导入导出
   - 导入模板下载
   - Excel 批量导入，单次上限 500 行
   - 逐行校验与错误行下载
   - 车辆列表按筛选条件导出

5. 首页数据看板
   - 车辆总数、本地车辆数、外地车辆数
   - 按中队统计车辆数、企业数、个人车主数
   - 安全设备覆盖率
   - 重点监管预警数

6. 重点监管预警
   - 基于“应安装设备清单”计算缺装项
   - 自动生成预警等级
   - 预警车辆列表查询和导出

7. 权限与审计
   - 菜单和按钮权限
   - 按部门 `dept_id` 做数据范围隔离
   - 复用操作日志和登录日志

### 2.2 本期不做

1. 移动端 App / 小程序业务改造
2. 外部公安或运管平台数据对接
3. GPS / 北斗轨迹监控
4. 年检、保险到期提醒
5. 大屏投放版
6. 工作流审批

## 3. 技术设计

### 3.1 后端模块划分

新增后端模块：`ruoyi-fastapi-backend/module_truck/`

建议结构：

```text
module_truck/
├── controller/
│   ├── dashboard_controller.py
│   ├── owner_controller.py
│   ├── vehicle_controller.py
│   └── warning_controller.py
├── dao/
│   ├── owner_dao.py
│   ├── vehicle_dao.py
│   └── warning_dao.py
├── entity/
│   ├── do/
│   │   └── truck_do.py
│   └── vo/
│       ├── dashboard_vo.py
│       ├── owner_vo.py
│       ├── vehicle_vo.py
│       └── warning_vo.py
└── service/
    ├── dashboard_service.py
    ├── owner_service.py
    ├── vehicle_import_service.py
    ├── vehicle_service.py
    └── warning_service.py
```

路由注册继续复用 `common.router.auto_register_routers(app)`，controller 中使用 `APIRouterPro`。

### 3.2 前端模块划分

新增 Web 管理端目录：

```text
ruoyi-fastapi-frontend/src/
├── api/truck/
│   ├── dashboard.js
│   ├── owner.js
│   ├── vehicle.js
│   └── warning.js
└── views/truck/
    ├── dashboard/index.vue
    ├── owner/index.vue
    ├── vehicle/index.vue
    ├── vehicle/detail.vue
    └── warning/index.vue
```

首页固定使用业务看板 `src/views/truck/dashboard/index.vue`，不再保留上游示例首页。

### 3.3 权限设计

新增顶级菜单：`大货车管理`

建议权限标识：

| 功能 | 权限标识 |
| --- | --- |
| 看板查询 | `truck:dashboard:list` |
| 主体查询 | `truck:owner:query` |
| 主体新增 | `truck:owner:add` |
| 主体修改 | `truck:owner:edit` |
| 主体删除 | `truck:owner:remove` |
| 主体导出 | `truck:owner:export` |
| 车辆查询 | `truck:vehicle:query` |
| 车辆新增 | `truck:vehicle:add` |
| 车辆修改 | `truck:vehicle:edit` |
| 车辆删除 | `truck:vehicle:remove` |
| 车辆导入 | `truck:vehicle:import` |
| 车辆导出 | `truck:vehicle:export` |
| 预警查询 | `truck:warning:query` |
| 预警重算 | `truck:warning:recalculate` |
| 预警导出 | `truck:warning:export` |

数据权限以业务表 `dept_id` 字段为隔离键，后端接口通过 `DataScopeDependency(TruckVehicle)`、`DataScopeDependency(TruckOwner)` 等方式复用现有数据范围机制。

## 4. 数据库设计草案

### 4.1 `truck_owner` 归属主体表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| owner_id | bigint | 主键 |
| owner_type | varchar(20) | `enterprise` / `individual` |
| owner_name | varchar(100) | 企业名称或个人姓名 |
| credit_code | varchar(32) | 统一社会信用代码 |
| id_card_no | varchar(32) | 身份证号 |
| dept_id | bigint | 所属中队部门 |
| contact_name | varchar(50) | 联系人 |
| contact_phone | varchar(30) | 联系电话 |
| address | varchar(255) | 地址 |
| status | char(1) | 状态 |
| remark | varchar(500) | 备注 |
| create_by/create_time/update_by/update_time | - | 审计字段 |
| del_flag | char(1) | 删除标志 |

关键约束：

1. 企业主体校验 `credit_code` 唯一。
2. 个人主体校验 `id_card_no` 唯一。
3. 删除主体前检查是否仍有关联车辆。

### 4.2 `truck_vehicle` 车辆档案表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| vehicle_id | bigint | 主键 |
| project_name | varchar(100) | 工地名称 |
| plate_no | varchar(20) | 车牌号 |
| plate_color | varchar(20) | 车牌颜色 |
| vehicle_type | varchar(30) | 车辆类型 |
| vehicle_brand | varchar(100) | 车辆品牌 |
| vin | varchar(32) | 车架号 |
| rated_load | decimal(10,2) | 核定载重 |
| source_type | varchar(20) | 本地 / 外地 |
| motor_owner_name | varchar(100) | 机动车所有人，保留台账原始字段 |
| driver_name | varchar(50) | 驾驶员 |
| driver_phone | varchar(30) | 驾驶员联系电话 |
| affiliated_company | varchar(100) | 挂靠公司 |
| insurance_status | varchar(100) | 保险情况，保留台账原始字段 |
| insurance_info | varchar(255) | 保险公司及金额 |
| owner_id | bigint | 当前归属主体 |
| owner_type | varchar(20) | 冗余主体类型，便于查询 |
| dept_id | bigint | 当前所属中队 |
| photo_file_id | bigint | 车辆照片文件 ID |
| vehicle_status | varchar(20) | 正常 / 报废 / 转出 / 停运 |
| supervision_flag | char(1) | 是否重点监管 |
| warning_level | varchar(20) | 当前预警等级 |
| missing_device_count | int | 缺装设备数量 |
| remark | varchar(500) | 备注 |
| create_by/create_time/update_by/update_time | - | 审计字段 |
| del_flag | char(1) | 删除标志 |

关键约束：

1. `plate_no + plate_color` 唯一。
2. `vin` 保存前转大写，长度校验 17 位。
3. 车辆转出、报废后保留历史数据，业务上限制继续编辑。

### 4.3 `truck_vehicle_device` 安全设备表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| device_id | bigint | 主键 |
| vehicle_id | bigint | 车辆 ID |
| device_type | varchar(30) | 设备类型 |
| product_name | varchar(100) | 产品名称 |
| brand | varchar(100) | 品牌 |
| install_date | date | 安装日期 |
| status | char(1) | 状态 |
| remark | varchar(500) | 备注 |
| create_by/create_time/update_by/update_time | - | 审计字段 |

建议约束：同一车辆同一设备类型默认只保留一条有效记录，除非后续明确需要多套同类设备。

### 4.4 `truck_vehicle_owner_history` 归属历史表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| history_id | bigint | 主键 |
| vehicle_id | bigint | 车辆 ID |
| old_owner_id/new_owner_id | bigint | 变更前后主体 |
| old_dept_id/new_dept_id | bigint | 变更前后中队 |
| change_reason | varchar(255) | 变更原因 |
| change_time | datetime | 变更时间 |
| change_by | varchar(64) | 操作人 |

### 4.5 `truck_warning_rule` 预警规则表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| rule_id | bigint | 主键 |
| rule_name | varchar(100) | 规则名称 |
| required_device_types | json/text | 应安装设备类型列表 |
| level_one_threshold | int | 一级预警阈值（默认 2 = 缺装全部应装设备） |
| level_two_threshold | int | 二级预警阈值（默认 2，与一级相同表示只保留一级预警） |
| status | char(1) | 状态 |
| create_by/create_time/update_by/update_time | - | 审计字段 |

MVP 可先不做复杂规则界面，先基于字典中的安全设备类型和固定阈值计算；后续再开放规则配置。

### 4.6 真实 Excel 台账字段映射

已读取 `工程车排查表.xlsx`：

1. `Sheet1` 第 1 行包含表头，第 2 行为样例数据。
2. `Sheet2` 当前为空表。
3. `Sheet3` 当前为空表。

`Sheet1` 表头：

| Excel 字段 | 建议映射 | 处理方式 |
| --- | --- | --- |
| 工地名称 | `truck_vehicle.project_name` | 可为空 |
| 车牌 | `truck_vehicle.plate_no` | 必填，导入时去空格并转大写 |
| 车辆类型 | `truck_vehicle.vehicle_type` | 字典项，不存在时提示或允许作为待维护字典 |
| 车辆品牌 | `truck_vehicle.vehicle_brand` | 可为空 |
| 保险情况 | `truck_vehicle.insurance_status` | 原样保留，可为空 |
| 机动车所有人 | `truck_vehicle.motor_owner_name`，必要时同步生成 `truck_owner` | 可为空 |
| 联系电话 | 主体联系电话 | Sheet1 有两个同名字段，需按位置区分 |
| 驾驶员 | `truck_vehicle.driver_name` | 可为空 |
| 联系电话 | `truck_vehicle.driver_phone` | Sheet1 有两个同名字段，需按位置区分 |
| 挂靠公司 | `truck_vehicle.affiliated_company`，必要时同步生成企业主体 | “无”按无挂靠处理 |
| 保险公司及金额 | `truck_vehicle.insurance_info` | 原样保留 |
| 是否安装刹辅系统 | `truck_vehicle_device.device_type=brake_assist` | 值为“是”时生成设备记录 |
| 360 | `truck_vehicle_device.device_type=panoramic_360` | 值为“是”或非空时生成设备记录 |
| 辖区中队 | `truck_vehicle.dept_id` | 按部门名称匹配，匹配失败逐行报错 |
| 是否本地车辆 | `truck_vehicle.source_type` | “是/本地”映射本地，“否/外地”映射外地，空值保留为空并提示可补全 |

导入策略：

1. 优先按表头识别字段。
2. 对未来出现的无表头 Sheet，支持按 `Sheet1` 的固定列顺序导入；当前 `Sheet2`、`Sheet3` 为空，不作为导入数据源。
3. 同名“联系电话”按列位置区分：第一个为主体联系电话，第二个为驾驶员联系电话。
4. 导入错误必须真实反馈，例如：车牌为空、车牌重复、辖区中队不存在、车辆类型未配置、电话号码格式异常、是否本地车辆取值无法识别。
5. 对主体生成采用保守策略：只有机动车所有人或挂靠公司字段明确且可识别时才自动创建主体；否则车辆保留原始字段，提示后续人工补全归属主体。
6. 主体按规范化后的主体名称和主体类型跨中队唯一归集，不把上报中队作为匹配条件；主体保留首次上报中队，车辆分别保留各自的上报中队。主体管理中的车辆数量和车辆列表按当前用户的数据权限统计和展示。

## 5. 接口清单

### 5.1 主体管理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/truck/owner/list` | 主体分页列表 |
| GET | `/truck/owner/options` | 主体下拉搜索 |
| GET | `/truck/owner/{owner_id}` | 主体详情 |
| POST | `/truck/owner` | 新增主体 |
| PUT | `/truck/owner` | 修改主体 |
| DELETE | `/truck/owner/{owner_ids}` | 删除主体 |
| GET | `/truck/owner/export` | 主体导出 |

### 5.2 车辆档案

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/truck/vehicle/list` | 车辆分页列表 |
| GET | `/truck/vehicle/{vehicle_id}` | 车辆详情 |
| POST | `/truck/vehicle` | 新增车辆 |
| PUT | `/truck/vehicle` | 修改车辆 |
| DELETE | `/truck/vehicle/{vehicle_ids}` | 删除车辆 |
| GET | `/truck/vehicle/export` | 车辆导出 |
| GET | `/truck/vehicle/import-template` | 导入模板下载 |
| POST | `/truck/vehicle/import` | Excel 导入 |
| GET | `/truck/vehicle/import-error/{batch_id}` | 错误行下载 |

### 5.3 看板和预警

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/truck/dashboard/summary` | 顶部统计 |
| GET | `/truck/dashboard/dept-stat` | 中队统计 |
| GET | `/truck/dashboard/device-coverage` | 设备覆盖率 |
| GET | `/truck/warning/list` | 预警车辆列表 |
| POST | `/truck/warning/recalculate` | 手动重算预警 |
| POST | `/truck/warning/export` | 预警导出 |
| GET | `/truck/vehicle/dept-options` | 分管中队选项树（含大队父节点，前端递归剔除大队） |

### 5.4 GA/T1400 对接（M9-M12 新增）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/gat1400/connect/status` | 对接状态查询 |
| POST | `/gat1400/connect/register` | 手动注册 |
| POST | `/gat1400/connect/keepalive` | 手动保活 |
| POST | `/gat1400/connect/unregister` | 手动注销 |
| GET | `/gat1400/config` | 对接配置查询 |
| PUT | `/gat1400/config` | 对接配置保存（密码加密存储、回显脱敏） |
| GET | `/gat1400/subscribe/list` | 订阅列表 |
| POST | `/gat1400/subscribe/create` | 创建订阅 |
| PUT | `/gat1400/subscribe/cancel/{subscribe_id}` | 取消订阅 |
| POST | `/VIID/SubscribeNotifications` | 接收大华平台过车记录推送 |
| GET | `/truck/passrecord/list` | 过车记录查询（按车辆分管中队隔离） |
| POST | `/truck/passrecord/export` | 过车记录导出 |

> 接口清单已与实现核对（共 29 条 truck / gat1400 路由）。GA/T1400 详细协议与设计见
> [`gat1400-integration-design.md`](gat1400-integration-design.md)。

## 6. 开发里程碑

### M0：开发准备，0.5-1 天

1. 使用 MySQL 8 作为首选开发数据库，PostgreSQL 作为兼容目标。
2. 确认是否使用 Alembic 作为本项目主迁移方式。
3. 初始化业务菜单、权限标识、字典类型。
4. 明确 MVP 不改移动端。
5. 准备测试账号和部门数据：松阳大队、6 个中队、大队管理员、中队管理员、领导只读账号。
6. 基于 `工程车排查表.xlsx` 固化导入字段映射和错误反馈格式。

验收标准：

1. 能启动后端和 Web 前端。
2. 管理员可看到“大货车管理”菜单占位。
3. 业务字典类型可在字典管理中维护。

#### M0 实施记录（2026-07-27）

1. 开发数据库继续使用项目 `.env.dev` 已配置的 MySQL 连接；PostgreSQL 保持兼容目标。
2. 仓库存在 Alembic 配置，但尚无已维护的版本迁移记录。为避免对既有数据库生成不可靠的基线迁移，M0 采用可重复执行的初始化脚本：`ruoyi-fastapi-backend/sql/truck-platform-init.mysql.sql` 与 `ruoyi-fastapi-backend/sql/truck-platform-init.pg.sql`。M1 新增 SQLAlchemy 模型时，以这两份脚本为当前业务表基线；后续结构变更再补充 Alembic 版本迁移。
3. 初始化脚本已包含主体、车辆、设备、归属历史和预警规则表，以及 7 类业务字典和“大货车管理/业务看板”菜单。
4. 组织架构已确认：松阳大队下设西屏、古市、江南、象溪、大东坝、玉岩 6 个中队。测试账号、领导导出权限、保险情况枚举和本地车辆空值规则仍待业务确认，因此尚未写入用户数据。

### M1：数据模型与后端基础 CRUD，2-3 天

1. 建表：主体、车辆、设备、归属历史。
2. 新增 `module_truck` 基础结构。
3. 完成主体 CRUD 和车辆 CRUD。
4. 完成车牌唯一、VIN、主体关联、删除保护等核心校验。
5. 接入操作日志和权限依赖。

验收标准：

1. Swagger 可访问主体和车辆接口。
2. 后端单元测试覆盖新增、修改、删除保护、数据权限过滤。

### M2：Web 管理端主体和车辆页面，3-4 天

1. 新增 `src/api/truck/*`。
2. 新增主体管理页面。
3. 新增车辆档案页面和详情页。
4. 车辆表单支持主体搜索、部门自动带出、设备增行、车辆照片上传。
5. 按钮权限接入 `v-hasPermi`。

验收标准：

1. 管理员可完整新增主体、车辆、设备。
2. 中队录入员只能看到本中队数据。
3. 车辆详情可展示主体、照片、设备、归属历史。

### M3：Excel 导入导出，2-3 天

1. 扩展车辆导入模板。
2. 实现 Excel 解析、行级校验、批量入库。
3. 支持错误行导出。
4. 实现车辆列表导出。

验收标准：

1. 500 行以内导入可在 30 秒内完成。
2. 重复车牌、VIN 格式错误、主体不存在等错误能明确反馈。
3. 导入和手工录入使用同一套核心校验规则。

#### M3 实施记录（2026-07-28）

1. 已实现车辆导入模板下载、筛选导出、Excel 批量导入和错误明细下载接口。
2. 导入同时兼容真实台账 15 列格式和扩展模板；重复“联系电话”按列位置区分，原台账缺少车牌颜色时默认按黄牌处理。
3. 单次导入限制 500 行，校验覆盖车牌、VIN、中队、车辆类型、车牌颜色、手机号、本地/外地取值、设备取值及文件内重复数据。
4. 有效行正常入库，失败行按工作表和原始行号生成带“错误信息”列的 Excel，错误文件在 Redis 中保留 30 分钟。
5. 车辆导出包含辖区中队、刹辅系统、360 全景影像、重点监管和预警字段；无数据时仍保留完整表头。
6. Web 车辆档案页已接入模板下载、批量导入、错误明细下载和按筛选条件导出，按钮权限已写入 MySQL/PostgreSQL 初始化脚本。

### M4：看板与预警，3-4 天

1. 完成统计 API。
2. 完成业务看板页面。
3. 完成预警计算服务。
4. 完成预警列表和导出。

验收标准：

1. 看板统计和车辆列表数据一致。
2. 缺装设备预警规则可正确计算。
3. 点击中队或预警数可下钻到车辆列表。

完成情况（2026-07-28）：

1. 已完成看板汇总、中队统计和安全设备覆盖率 API，所有查询统一接入车辆或主体数据权限。
2. 首页已改为业务看板，支持本地/外地车辆、中队车辆及一级/二级预警下钻。
3. 已预置“刹车辅助系统 + 360 全景影像”必装规则。**当前口径（M14 调整后）**：
   应安装设备 2 项，缺装 2 项（一项都没装）为一级预警，缺 1 项不预警，设备齐全无预警。
   阈值机制保留两级能力，恢复分级只需调低 `level_two_threshold`。
4. 已完成预警重算、分页查询、真实缺失设备展示和按筛选条件导出，并同步 MySQL/PostgreSQL 初始化脚本及当前 MySQL 菜单权限。
5. 三辆临时车辆端到端验证通过并已清理；Ruff、11 项后端单元测试、Vite 生产构建以及 375px/756px 浏览器布局检查均通过。

### M5：测试、联调与交付准备，2-3 天

1. 补充后端 pytest。
2. 补充关键 Playwright E2E 用例。
3. 补充初始化 SQL 和部署说明。
4. 进行权限、导入、看板、预警回归测试。
5. 整理验收清单。

验收标准：

1. 后端测试通过。
2. 前端生产构建通过。
3. 核心业务流程 E2E 通过。
4. 交付文档包含部署、初始化、账号、字典、常见问题。

完成情况（2026-07-28）：

1. 后端业务测试扩展到 18 项，覆盖主体删除保护、唯一校验、车辆规则、Excel、看板聚合、预警和部门数据权限。
2. 新增 2 项 Playwright 业务 E2E，覆盖首页统计组件、一级预警下钻及 375px 移动视口横向溢出检查。
3. 新增西屏中队管理员和领导验收账号，MySQL/PostgreSQL 初始化及 M5 增量脚本已同步。
4. 三角色真实权限回归通过：管理员和领导可读全量，中队管理员仅访问西屏数据；中队预警重算不会更新其他中队，领导写接口返回 403。
5. README 已改为本项目交付说明，并新增部署初始化、测试脚本、账号权限、常见问题和验收清单。
6. Ruff、18 项后端测试、2 项 Playwright E2E、PowerShell 脚本语法检查和 Vite 生产构建均通过；PostgreSQL 已完成脚本兼容同步，尚未连接独立 PostgreSQL 实例执行回归。

### M6：归属与数据范围业务规则定稿（2026-10-15）

系统已运行后经业务确认，`truck_owner.dept_id` 与 `truck_vehicle.dept_id` 的语义需要显式定稿，
因为多数大货车为挂靠性质，车辆分管与主体登记地天然可以不同。定稿规则如下。

#### 规则 1：车辆分管中队由车辆自身决定

- `truck_vehicle.dept_id` 表示**分管中队**，即这辆车由哪个中队负责管理，取自主管中队的上报录入。
- 该字段**不由所属主体推导**，主体变更时不级联修改车辆分管中队。

#### 规则 2：主体是车辆的归集维度，允许跨中队

- `truck_owner.dept_id` 表示**主体登记归属中队**，仅用于登记统计与主体列表筛选，**不决定车辆分管**。
- 一辆挂靠车可以「主体登记在西屏、车辆由古市分管」，这是正常业务形态。
- 同一主体名下车辆可以分布在多个中队；车辆列表按 `ownerId` 查询时跨中队展示，
  并返回每辆车的分管中队名称（`deptName`）以便识别。

#### 规则 3：主体档案跨中队可见

- 主体的可见性 = 登记归属本中队 **或** 本中队分管了该主体名下的车辆
  （`TruckOwnerDao.get_list` 的 `or_(owner_scope, linked_vehicle_visible)`）。
- 「名下车辆」数量与明细均为该主体**跨中队的全部在管车辆**，不按当前用户车辆权限收窄。
- 车辆本身的查询、修改、删除、导出仍严格按车辆分管中队隔离，不因规则 3 放宽。

#### 规则 4：看板按中队统计统一口径

- `dept-stat` 中每行的车辆数与企业数/个人数**均按「车辆分管中队」归集**，保证同一行两个数字可对齐。
- 主体总量卡片仍按 `owner_id` 去重统计，不受中队归集影响。

#### 规则 5：个人车辆不强制建主体

- 个体车可以只填写 `truck_vehicle.motor_owner_name` 完成建档，`owner_id` 允许为空。
- 需要归集时再补建 `owner_type='individual'` 的主体并关联；批量导入沿用
  `_resolve_or_create_owner` 的保守策略（字段明确且可识别时才自动创建）。

#### 本次同步的代码与界面

1. `TruckOwnerService.get_list` 的「名下车辆」计数不再传入车辆数据权限。
2. `TruckVehicleService.get_list` 补充 `deptName`，并将车辆列表列名改为「分管中队」。
3. **按 `ownerId` 查询车辆时不再拼接车辆数据权限**（由 `TruckVehicleDao.get_list` 判断），
   使「名下车辆」与明细口径一致；跨中队读取前先校验主体可见性，避免借 `ownerId` 越权。
4. `TruckDashboardDao.get_dept_owner_counts` 改为按车辆分管中队归集主体。
5. 主体列表/表单、车辆表单的字段标签明确为「登记归属中队」「分管中队」，并加说明提示。
6. 新增单元测试 `test_owner_vehicle_count_covers_all_squads`、`tests/truck/test_vehicle_list_scope.py`。

#### 顺带修复的既有缺陷

1. **部门选项树一直不可用**：`/truck/vehicle/dept-options` 原先只返回 6 个中队、不返回它们的父节点
   「松阳大队」，而前端用 `handleTree` 组装树；父节点缺失时 `handleTree` 返回空数组，
   导致树形选择器实际没有任何可选中队，选中队后只显示部门 ID。
   现改为连同大队节点一起返回，并在前端 `filterTruckSquads` 中递归剔除大队节点
   （大队不承担车辆分管，不可作为选项）。车辆新增页的分管中队默认值改为空，强制显式选择。
2. **软删占用唯一键**：`truck_owner.credit_code` / `id_card_no`、`truck_vehicle.(plate_no, plate_color)` / `vin`
   都是不含 `del_flag` 的唯一索引，软删后身份字段仍被占用，重建同一主体或车辆会报
   `Duplicate entry`。**已在 M13 修复**（见下）。
3. **PostgreSQL 迁移脚本补齐并真机验证**：原先 `m4`、`m6`、`m7`、`m8` 只有 MySQL 版本，
   PostgreSQL 升级路径自 m4 起断裂。已补齐 4 份 `.pg.sql`，并修复 `init.pg.sql` 写入
   PostgreSQL 模板中不存在的 `sys_dept.remark`、`m12.pg.sql` 误用 `ON CONFLICT (config_key)`
   两处既有错误。在 PostgreSQL 14.24 上完成「基础模板 + `init` + `m4`~`m12`」共 11 个脚本
   的完整演练，全部成功且二次执行幂等。

### M13：软删释放唯一键（2026-10-15）

**问题**：软删除只置 `del_flag='2'`，保留 `credit_code` / `id_card_no` / `plate_no` / `vin`，
唯一索引不含 `del_flag`，导致「删掉的东西建不回来」。

**处置**：

1. 软删主体时清空 `credit_code` 与 `id_card_no`（`TruckOwnerDao.delete`）。
2. 软删车辆时清空 `plate_no` 与 `vin`（`TruckVehicleDao.soft_delete`）。
3. `truck_vehicle.plate_no` 由 `NOT NULL` 改为可空（已删除的车辆没有有效车牌）。
4. 新增增量脚本 `sql/truck-platform-m13.mysql.sql` 与 `.pg.sql`，调整列定义并清理历史遗留，
   可重复执行；已在 MySQL 真机连续执行两次验证幂等。

**设计取舍（与早期建议不同，需注意）**：早期建议「把唯一约束改为包含 `del_flag` 的组合索引」，
该方案实际**不可行**——`(credit_code, del_flag)` 在 `del_flag='0'` 时仍无法阻止两条
`del_flag='0'` 的相同信用代码，唯一性保障反而变弱。最终采用**软删时置空身份字段**：
MySQL 唯一索引允许多个 NULL，身份标识可安全复用，而主体名称、车辆其余档案与操作日志
仍保留完整审计痕迹。

**验证**：真机实测「创建 → 软删 → 用同一信用代码 / 同一车牌+车架号重建」均成功；
新增 `tests/truck/test_soft_delete_unique_key.py` 直接断言 UPDATE 的 SET 子句，
无需数据库即可锁定行为（此前该缺陷无测试覆盖，因为原有测试把 DAO 的 delete 整体 mock 掉了）。


## 7. 测试计划

### 7.1 后端单元测试

重点覆盖：

1. 主体新增、修改、删除保护。
2. 车辆新增、修改、车牌唯一校验。
3. VIN 自动大写和长度校验。
4. 设备新增、删除、预警重算。
5. 数据权限过滤。
6. Excel 导入行级校验。

建议目录：

```text
ruoyi-fastapi-backend/tests/truck/
├── test_owner.py
├── test_vehicle.py
├── test_vehicle_import.py
├── test_warning.py
└── test_dashboard.py
```

### 7.2 前端 / E2E 测试

建议补充：

1. 登录后进入大货车管理菜单。
2. 新增企业主体。
3. 新增个人车主。
4. 新增车辆并关联主体。
5. 新增安全设备。
6. 中队账号看不到其他中队车辆。
7. 导入错误 Excel 后可下载错误行。
8. 看板统计展示正常。

## 8. 风险与处理

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| PRD 字段与实际台账字段不一致 | 返工数据模型 | M0 阶段拿 1 份真实 Excel 台账做字段核对 |
| 数据权限实现不彻底 | 中队越权查看数据 | 所有业务主表保留 `dept_id` 并统一接入 `DataScopeDependency` |
| Excel 导入校验分散 | 手工录入和导入规则不一致 | 将核心校验放在 `VehicleService`，导入服务复用 |
| 预警规则后续变化 | 看板和列表逻辑返工 | MVP 先抽象为独立 `WarningService` |
| 菜单 SQL 与迁移脚本不同步 | 部署后页面不可见 | 同步维护初始化 SQL 和 Alembic 迁移 |
| README 已有未提交改动 | 容易混入无关变更 | 后续开发只修改业务相关文件，提交前单独核对 diff |

## 9. 开发准备清单

1. 数据库选择：已确认 MySQL 8 优先，PostgreSQL 作为兼容目标。
2. 真实 Excel 台账：已确认根目录存在 `工程车排查表.xlsx`，需按实际字段导入。
3. 组织架构：已确认松阳大队及西屏、古市、江南、象溪、大东坝、玉岩 6 个中队。
4. 预设角色：已确认大队管理员（系统管理员）、中队管理员、领导权限。
5. 车辆照片：已确认复用现有文件管理模块。
6. 导入错误反馈：已确认根据真实错误信息逐行反馈。
7. README：已确认不需要保留原始上游项目说明。
8. 待确认：领导权限是否允许导出、`保险情况` 的业务枚举值、`是否本地车辆` 空值是否允许导入。

## 10. 推荐执行顺序

1. 先做数据库设计和业务字典。
2. 再做主体和车辆后端 CRUD。
3. 然后做前端主体、车辆页面。
4. 接着做 Excel 导入导出。
5. 最后做看板、预警和 E2E 测试。

这个顺序能先稳定核心数据链路，再补批量导入和统计能力，避免看板和预警建立在未定型的数据模型之上。
