from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
LAB_API_DIR = ROOT_DIR / "lab-api"
if str(LAB_API_DIR) not in sys.path:
    sys.path.insert(0, str(LAB_API_DIR))

from modular.core import execute, query, rebuild_knowledge_document_chunks  # noqa: E402


OUTPUT_DIR = ROOT_DIR / "generated" / "knowledge-seed"
NOW_TEXT = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
UPLOADER_NAME = "seed-script"


DOCUMENTS = [
    {
        "filename": "01-lab-reservation-spec.md",
        "title": "实验室预约规范",
        "category": "rule",
        "scopeRole": "all",
        "status": "active",
        "sourceUrl": "",
        "content": """# 实验室预约规范

## 一、适用范围
本规范适用于计算机实验室、物联网实验室、数据管理实验室等公共教学实验空间的预约、审批、签到和违约处理。

## 二、开放时间
1. 实验室常规开放时段为每日 08:00-22:00。
2. 法定节假日是否开放，以管理员公告为准。
3. 晚间时段如需使用高功耗设备，必须在预约备注中说明用途。

## 三、预约规则
1. 学生和教师均可发起预约。
2. 单次预约最长不超过 4 小时，跨天预约默认不予受理。
3. 预约最早可提前 30 天提交，最晚应在使用前 30 分钟完成申请。
4. 课程教学、考试、学校统一活动优先级高于个人预约。
5. 高峰时段或热门实验室预约，需经管理员审批后方可生效。

## 四、审核与变更
1. 管理员应在 24 小时内完成审批。
2. 若预约信息不完整、用途不明确或与已有任务冲突，管理员可驳回并要求补充说明。
3. 预约通过后如需改期，应至少提前 2 小时在系统内取消或重新申请。
4. 因课程调整导致冲突时，系统保留优先调度权。

## 五、签到与离场
1. 使用人到场后应在 15 分钟内完成签到。
2. 结束使用后，应关闭设备电源、整理桌面并完成离场确认。
3. 发现设备异常、耗材不足、安全隐患时，应立即在系统提交报修或异常记录。

## 六、违约处理
1. 无故爽约 2 次以上，系统将限制其 7 天内预约权限。
2. 预约通过后超过 30 分钟未签到，管理员可释放该时段资源。
3. 擅自转借实验室、超时占用或造成设备损坏的，按实验室管理制度追责。

## 七、补充说明
1. 需要外接私有设备时，应确认接口、电源和网络接入符合安全要求。
2. 涉及敏感数据处理的实验，须提前说明数据来源与保密措施。
3. 对本规范有疑问，可咨询值班教师或实验室管理员。
""",
    },
    {
        "filename": "02-equipment-operation-manual.md",
        "title": "设备操作手册",
        "category": "manual",
        "scopeRole": "all",
        "status": "active",
        "sourceUrl": "",
        "content": """# 设备操作手册

## 一、适用设备
本手册适用于实验室台式主机、显示器、投影仪、交换机、打印机、UPS 和常用外设。

## 二、开机前检查
1. 检查设备编号、摆放位置和外观是否正常。
2. 确认电源线、网线、视频线连接牢固，无破损、松动或私拉乱接。
3. 检查桌面是否干燥整洁，严禁设备附近摆放饮料和易燃品。
4. 若设备贴有“维修中”“停用”标签，禁止擅自启动。

## 三、主机与显示器操作
1. 先开启插排或稳压供电，再开启显示器和主机。
2. 登录系统后仅安装经批准的软件，不得关闭安全防护程序。
3. 使用结束后先关闭业务软件，再执行系统正常关机。
4. 关机完成后关闭显示器和外接电源，不得直接切断主机电源。

## 四、投影仪与多媒体设备
1. 投影仪开启后应等待设备预热完成再切换信号源。
2. 使用无线投屏前，应确认网络和账号已授权。
3. 投影结束后使用遥控器或中控正常关机，待风扇停止转动后再断电。
4. 音箱、功放音量应从低到高逐步调整，避免啸叫和瞬时冲击。

## 五、网络与机柜设备
1. 非管理员不得调整交换机、路由器、AP 和机柜布线。
2. 需要临时接入新设备时，须先登记 MAC 地址、用途和接入时长。
3. 发现网络抖动、端口异常闪烁或设备过热，应及时拍照并报修。

## 六、打印与外设
1. 打印机缺纸、卡纸或提示维护时，应按提示处理，不得强行拉扯纸张。
2. 扫码枪、读卡器、键鼠等外设使用后须归位，避免接口长期受力。
3. 便携设备如备用笔记本、转接器、移动硬盘应按借用流程登记。

## 七、异常处理
1. 出现异响、异味、冒烟、黑屏、反复重启等情况，应立即断开电源并停止使用。
2. 不得自行拆机、刷 BIOS、重装核心驱动或更换配件。
3. 通过系统提交报修时，应填写设备编号、故障现象、发生时间和影响范围。

## 八、维护建议
1. 公共设备每月进行一次除尘和线缆检查。
2. 高负载设备应关注散热、风扇噪音和硬盘健康状态。
3. 超过保修期或频繁故障的设备，应纳入重点巡检和更新评估清单。
""",
    },
    {
        "filename": "03-lab-safety-policy.md",
        "title": "实验室安全制度",
        "category": "safety",
        "scopeRole": "all",
        "status": "active",
        "sourceUrl": "",
        "content": """# 实验室安全制度

## 一、基本要求
1. 进入实验室人员应遵守学校安全管理规定，服从值班教师和管理员安排。
2. 严禁携带易燃、易爆、腐蚀性物品进入实验室。
3. 实验室内禁止吸烟、打闹、大声喧哗和私接大功率电器。

## 二、用电安全
1. 电源插座、UPS、配电箱周边不得堆放杂物。
2. 发现插头过热、线路老化、插排焦黑等情况，应立即停用并上报。
3. 非授权人员不得操作配电开关、机柜电源和中控系统。

## 三、设备安全
1. 设备必须按编号固定使用，不得擅自拆装、调换位置或带离实验室。
2. 服务器、核心交换机、存储设备等关键资产应由管理员专人负责。
3. 新增硬件接入前，应完成安全检查和资产登记。

## 四、数据与网络安全
1. 涉及教学资料、账号、实验数据的设备，应启用口令保护和必要的访问控制。
2. 禁止私自接入未知 U 盘、移动硬盘或来源不明的软件。
3. 发现病毒、勒索软件、异常外联或账号泄露迹象，应立即上报并隔离设备。

## 五、消防与应急
1. 熟悉灭火器、消防通道、紧急断电开关和应急联系电话位置。
2. 遇到冒烟、起火、强烈焦味等情况，应先断电、再报警、后组织疏散。
3. 夜间值班发现重大异常时，应同时通知管理员、值班教师和学校保卫部门。

## 六、卫生与环境
1. 实验结束后应恢复桌椅、线缆、设备摆放，保持地面干净整洁。
2. 机房内温湿度应保持在适宜范围，空调和通风设备须按要求运行。
3. 纸箱、泡沫、废旧耗材不得长期堆放在机房角落或配电区域。

## 七、责任追究
1. 因违规操作导致设备损坏、数据丢失或安全事故的，将按学校规定追责。
2. 对隐瞒故障、不及时上报安全隐患的人员，视情节限制实验室使用权限。
3. 对主动排查风险、及时上报重大隐患的个人，可纳入安全管理正向评价。
""",
    },
    {
        "filename": "04-duty-workflow.md",
        "title": "实验室值班流程",
        "category": "rule",
        "scopeRole": "all",
        "status": "active",
        "sourceUrl": "",
        "content": """# 实验室值班流程

## 一、值班目标
值班教师和管理员负责保障实验室日常开放、预约核验、设备巡查、异常上报和闭馆检查。

## 二、到岗准备
1. 值班人员应至少提前 10 分钟到岗。
2. 打开后台查看当日预约、待审批事项、报修工单和高风险告警。
3. 核对实验室门禁、空调、照明、多媒体设备是否处于可用状态。

## 三、开放前检查
1. 检查实验室卫生、桌椅摆放、设备外观及线缆连接。
2. 随机抽查主机、显示器、网络和投影设备的启动情况。
3. 确认灭火器、应急照明、疏散通道无异常遮挡。

## 四、开放中管理
1. 按预约名单核验使用人身份和预约信息。
2. 指导首次使用人员按规范操作设备，提醒注意用电和数据安全。
3. 巡查过程中重点关注异常噪音、黑屏、断网、过热、插排过载等问题。
4. 对临时借用设备、外接设备和耗材领用进行登记。

## 五、异常处置
1. 发现设备故障时，先隔离故障设备并挂出停用标识。
2. 若影响当前教学或实验，应协调备用设备或调整座位。
3. 重大异常需在 10 分钟内完成电话通知，并在系统提交事件记录。

## 六、闭馆流程
1. 核对预约结束情况，提醒使用人完成离场和卫生恢复。
2. 检查门窗、照明、空调、多媒体设备是否关闭。
3. 复核是否有未归位设备、未处理工单或需交接的风险事项。
4. 在值班记录中填写当日情况、异常摘要和后续跟进建议。

## 七、交接要求
1. 跨班次值班须进行口头和书面交接。
2. 对未完成报修、待审批预约、临时管控设备，应明确责任人和截止时间。
3. 值班记录应至少保留 6 个月，便于追溯和复盘。
""",
    },
    {
        "filename": "05-repair-guide.md",
        "title": "设备报修指引",
        "category": "repair",
        "scopeRole": "all",
        "status": "active",
        "sourceUrl": "",
        "content": """# 设备报修指引

## 一、适用场景
当实验室设备出现硬件故障、软件异常、网络中断、外设损坏、环境设施问题时，应通过系统提交报修。

## 二、报修前确认
1. 先确认设备编号、所属实验室和当前使用状态。
2. 简单检查电源、网线、显示线、插座和外接设备连接情况。
3. 如设备正处于“维修中”或“停用”状态，无需重复提交同类工单。

## 三、工单填写要求
1. 标题应概括故障现象，例如“B305-HOST-012 无法开机”。
2. 描述中至少包含故障时间、现象表现、影响范围、是否可复现。
3. 若有报错提示、告警灯、异味、异响或照片截图，应一并上传或记录。
4. 涉及课程中断、整间实验室不可用等情况，应标记为紧急。

## 四、处理时效
1. 一般问题应在 1 个工作日内响应。
2. 紧急问题应在 30 分钟内联系处理，必要时启动现场处置。
3. 需要外送维修或采购配件的，应在工单中说明预计恢复时间。

## 五、常见问题分类
1. 开机异常：无法启动、反复重启、蓝屏、黑屏。
2. 外设异常：键盘失灵、鼠标漂移、打印机卡纸、投影无信号。
3. 网络异常：无法上网、端口不通、无线 AP 掉线、访问内网服务失败。
4. 环境异常：空调故障、照明损坏、门禁失灵、摄像头离线。

## 六、报修后的配合事项
1. 保持故障现场，非维修人员不要继续尝试拆机或更改配置。
2. 若故障设备影响授课，应及时申请备用设备或临时调换工位。
3. 维修完成后，应验证问题是否解决，并在系统确认关闭工单。

## 七、升级与复盘
1. 同一设备 30 天内重复报修两次以上，应纳入重点关注清单。
2. 对批量性故障、频繁网络波动或存在安全隐患的问题，应形成专项复盘。
3. 维修记录将作为设备保养、调拨、报废和更新采购的重要依据。
""",
    },
]


def write_document_files() -> list[dict]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    docs = []
    for item in DOCUMENTS:
        file_path = OUTPUT_DIR / item["filename"]
        file_path.write_text(item["content"].strip() + "\n", encoding="utf-8")
        doc = dict(item)
        doc["sourceUrl"] = file_path.as_posix()
        docs.append(doc)
    return docs


def upsert_document(doc: dict) -> tuple[str, int]:
    existing_rows = query(
        "SELECT id FROM knowledge_document WHERE title=%s LIMIT 1",
        (doc["title"],),
    )
    if existing_rows:
        doc_id = int(existing_rows[0]["id"])
        execute(
            """
            UPDATE knowledge_document
            SET category=%s,
                scope_role=%s,
                status=%s,
                source_type='text',
                source_url=%s,
                source_content=%s,
                uploader_name=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (
                doc["category"],
                doc["scopeRole"],
                doc["status"],
                doc["sourceUrl"],
                doc["content"],
                UPLOADER_NAME,
                NOW_TEXT,
                doc_id,
            ),
        )
        action = "updated"
    else:
        execute(
            """
            INSERT INTO knowledge_document (
                title, category, scope_role, status, source_type, source_url,
                summary, keywords, source_content, chunk_count, last_indexed_at,
                uploader_id, uploader_name, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, 'text', %s, '', '', %s, 0, NULL, NULL, %s, %s, %s)
            """,
            (
                doc["title"],
                doc["category"],
                doc["scopeRole"],
                doc["status"],
                doc["sourceUrl"],
                doc["content"],
                UPLOADER_NAME,
                NOW_TEXT,
                NOW_TEXT,
            ),
        )
        inserted_rows = query(
            "SELECT id FROM knowledge_document WHERE title=%s ORDER BY id DESC LIMIT 1",
            (doc["title"],),
        )
        doc_id = int(inserted_rows[0]["id"])
        action = "created"
    rebuild_knowledge_document_chunks(doc_id)
    return action, doc_id


def main() -> int:
    docs = write_document_files()
    results = []
    for doc in docs:
        action, doc_id = upsert_document(doc)
        results.append((action, doc_id, doc["title"], doc["sourceUrl"]))

    print("Knowledge seed import finished:")
    for action, doc_id, title, source_url in results:
        print(f"- {action:<7} #{doc_id:<3} {title} -> {source_url}")
    print(f"Total documents processed: {len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
