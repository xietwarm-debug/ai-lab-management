from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pymysql


ROOT_DIR = Path(__file__).resolve().parents[1]
LAB_API_DIR = ROOT_DIR / "lab-api"
if str(LAB_API_DIR) not in sys.path:
    sys.path.insert(0, str(LAB_API_DIR))

from modular.core import DB  # noqa: E402


SEED_MARKER = "答辩演示"
SEED_SOURCE = "demo_seed"

TIME_BLOCKS = [
    "08:00-08:40,08:45-09:35",
    "10:25-11:05,11:10-11:50",
    "14:30-15:10,15:15-15:55",
    "16:05-16:45,16:50-17:30",
    "19:00-19:40,19:45-20:25",
]


def dt_text(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def date_text(value: datetime) -> str:
    return value.strftime("%Y-%m-%d")


def build_course_code(index: int) -> str:
    return f"88{index:04d}"


def fetch_users(cur, role: str) -> list[dict]:
    cur.execute(
        """
        SELECT id, username, role
        FROM user
        WHERE role=%s
          AND COALESCE(is_active, 1)=1
          AND COALESCE(is_frozen, 0)=0
        ORDER BY id ASC
        """,
        (role,),
    )
    return list(cur.fetchall())


def fetch_labs(cur) -> list[dict]:
    cur.execute(
        """
        SELECT id, name, status, capacity
        FROM lab
        ORDER BY id ASC
        """
    )
    return list(cur.fetchall())


def fetch_equipment_by_lab(cur) -> dict[int, list[dict]]:
    cur.execute(
        """
        SELECT
            e.id,
            e.asset_code,
            COALESCE(NULLIF(e.name, ''), e.asset_code, CONCAT('设备-', e.id)) AS equipment_name,
            e.lab_id,
            COALESCE(NULLIF(e.lab_name, ''), l.name) AS lab_name,
            e.status
        FROM equipment e
        LEFT JOIN lab l ON l.id=e.lab_id
        WHERE e.lab_id IS NOT NULL
          AND COALESCE(NULLIF(e.lab_name, ''), l.name) IS NOT NULL
          AND COALESCE(NULLIF(e.lab_name, ''), l.name) <> ''
          AND e.status IN ('in_service', 'active', 'repairing')
        ORDER BY e.lab_id ASC, e.id ASC
        """
    )
    grouped: dict[int, list[dict]] = defaultdict(list)
    for row in cur.fetchall():
        grouped[int(row["lab_id"])].append(row)
    return grouped


def cleanup_existing_demo_rows(cur) -> None:
    like_value = f"%{SEED_MARKER}%"
    cur.execute("DELETE FROM course_member WHERE course_id IN (SELECT id FROM course WHERE description LIKE %s)", (like_value,))
    cur.execute("DELETE FROM course WHERE description LIKE %s", (like_value,))
    cur.execute("DELETE FROM reservation WHERE reason LIKE %s OR source=%s", (like_value, SEED_SOURCE))
    cur.execute("DELETE FROM announcement WHERE content LIKE %s", (like_value,))
    cur.execute("DELETE FROM lost_found WHERE description LIKE %s", (like_value,))
    cur.execute("DELETE FROM repair_work_order WHERE description LIKE %s OR order_no LIKE 'DEMO%%'", (like_value,))
    cur.execute("DELETE FROM audit_log WHERE detail_json LIKE %s", (like_value,))


def insert_announcements(cur, admin_user: dict, now: datetime) -> int:
    rows = [
        {
            "title": "本周实验室答辩联调安排",
            "content": "本周开放 C105、C205、C406 三间实验室用于系统答辩联调与演示彩排。\n\n[答辩演示]",
            "offset_days": -2,
            "pinned": 1,
        },
        {
            "title": "设备巡检结果通报",
            "content": "高性能计算与数据管理实验室已完成巡检，发现的风扇异响和显示器闪烁问题已进入处理流程。\n\n[答辩演示]",
            "offset_days": -1,
            "pinned": 0,
        },
        {
            "title": "预约审批时效提醒",
            "content": "本周起实验室预约审批统一在 2 小时内完成，临近答辩的预约请优先处理。\n\n[答辩演示]",
            "offset_days": 0,
            "pinned": 0,
        },
        {
            "title": "周末系统演示预排通知",
            "content": "周末将进行系统集中演示预排，请相关教师和学生提前确认实验室与设备状态。\n\n[答辩演示]",
            "offset_days": 1,
            "pinned": 0,
        },
    ]

    inserted = 0
    for item in rows:
        publish_at = now + timedelta(days=item["offset_days"], hours=9 - now.hour)
        created_at = publish_at - timedelta(hours=1)
        status = "scheduled" if publish_at > now else "published"
        pinned_at = dt_text(created_at) if item["pinned"] else None
        cur.execute(
            """
            INSERT INTO announcement (
                title, content, publisher_id, publisher_name,
                created_at, publish_at, updated_at, is_pinned, pinned_at,
                status, category, audience_type
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                item["title"],
                item["content"],
                int(admin_user["id"]),
                str(admin_user["username"]),
                dt_text(created_at),
                dt_text(publish_at),
                dt_text(created_at),
                int(item["pinned"]),
                pinned_at,
                status,
                "notice",
                "all",
            ),
        )
        inserted += 1
    return inserted


def insert_reservations(cur, labs: list[dict], students: list[dict], teacher_user: dict, now: datetime) -> int:
    lab_refs = labs[:6]
    student_cycle = students[:10]
    rows = [
        (-6, 0, 0, "approved", "数据库课程阶段验收"),
        (-6, 1, 1, "pending", "虚拟化平台联调演练"),
        (-5, 2, 2, "approved", "网络架构实训小组彩排"),
        (-5, 3, 3, "rejected", "与已排课程时间冲突"),
        (-4, 4, 1, "approved", "设备资产盘点演示"),
        (-4, 5, 4, "cancelled", "学生临时调整时间"),
        (-3, 6, 0, "approved", "答辩场景流程回放"),
        (-3, 7, 2, "pending", "安全演练课程补录"),
        (-2, 8, 3, "approved", "实验室安全培训"),
        (-2, 9, 4, "approved", "运维日志分析上机"),
        (-1, 1, 1, "pending", "教师现场答疑预排"),
        (-1, 2, 2, "rejected", "审批老师要求调整用途说明"),
        (0, 3, 3, "pending", "毕业设计答辩彩排"),
        (0, 4, 0, "approved", "服务器巡检汇报演示"),
        (1, 5, 1, "pending", "系统功能录屏补采"),
        (1, 6, 2, "approved", "实验室开放日接待"),
        (2, 7, 4, "approved", "学生项目联调"),
        (3, 8, 0, "cancelled", "申请人重复提交后撤销"),
    ]

    inserted = 0
    for index, (created_day_offset, reservation_day_offset, lab_index, status, reason_text) in enumerate(rows, start=1):
        user = teacher_user if index in {6, 11, 16} else student_cycle[(index - 1) % len(student_cycle)]
        lab = lab_refs[lab_index % len(lab_refs)]
        created_at = now + timedelta(days=created_day_offset, hours=(index % 6) - 3)
        reservation_date = now + timedelta(days=reservation_day_offset)
        reject_reason = ""
        admin_note = ""
        if status == "rejected":
            reject_reason = reason_text
            admin_note = "请重新选择时段后提交"
        elif status == "cancelled":
            admin_note = "用户主动撤销"
        elif status == "approved":
            admin_note = "场地与设备已预留"

        cur.execute(
            """
            INSERT INTO reservation (
                lab_id, lab_name, user_name, date, time, reason, status,
                reject_reason, admin_note, created_at, source, ai_session_id,
                review_role, review_policy
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s)
            """,
            (
                int(lab["id"]),
                str(lab["name"]),
                str(user["username"]),
                date_text(reservation_date),
                TIME_BLOCKS[index % len(TIME_BLOCKS)],
                f"{reason_text}（{SEED_MARKER}）",
                status,
                reject_reason,
                admin_note,
                dt_text(created_at),
                SEED_SOURCE,
                "admin",
                "admin",
            ),
        )
        inserted += 1
    return inserted


def insert_lost_found(cur, students: list[dict], now: datetime) -> int:
    owner_a = students[0]
    owner_b = students[1]
    claimant = students[2]
    rows = [
        {
            "title": "黑色校园卡",
            "item_type": "found",
            "location": "C406 数据管理实验室前排",
            "contact": "实验室值班台",
            "owner": owner_a["username"],
            "status": "open",
            "claim_status": "pending",
            "claim_user": claimant["username"],
            "claim_reason": "姓名与学号信息一致",
            "created_at": now - timedelta(days=1, hours=3),
            "claim_at": now - timedelta(hours=8),
        },
        {
            "title": "银色 U 盘",
            "item_type": "lost",
            "location": "C205 网络架构实验室",
            "contact": owner_b["username"],
            "owner": owner_b["username"],
            "status": "open",
            "claim_status": "",
            "claim_user": "",
            "claim_reason": "",
            "created_at": now - timedelta(days=2, hours=2),
            "claim_at": None,
        },
        {
            "title": "蓝牙鼠标",
            "item_type": "found",
            "location": "C105 智能运维实验室讲台",
            "contact": owner_a["username"],
            "owner": owner_a["username"],
            "status": "closed",
            "claim_status": "approved",
            "claim_user": claimant["username"],
            "claim_reason": "经核验后已领回",
            "created_at": now - timedelta(days=4, hours=1),
            "claim_at": now - timedelta(days=3, hours=5),
        },
    ]

    inserted = 0
    for item in rows:
        claim_user = str(item["claim_user"] or "").strip()
        claim_student_id = claim_user if claim_user.isdigit() else ""
        cur.execute(
            """
            INSERT INTO lost_found (
                title, item_type, description, location, contact, status, owner, created_at, image_url,
                claim_apply_status, claim_apply_user, claim_apply_reason, claim_apply_student_id,
                claim_apply_name, claim_apply_class, claim_apply_at, claim_reviewed_by, claim_reviewed_at, claim_review_note
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '',
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s)
            """,
            (
                item["title"],
                item["item_type"],
                f"物品登记信息用于系统答辩展示。（{SEED_MARKER}）",
                item["location"],
                item["contact"],
                item["status"],
                item["owner"],
                dt_text(item["created_at"]),
                item["claim_status"],
                claim_user,
                item["claim_reason"],
                claim_student_id,
                claim_user,
                "计科 2201",
                dt_text(item["claim_at"]) if item["claim_at"] else None,
                "admin1" if item["claim_status"] in {"approved"} else "",
                dt_text(item["claim_at"] + timedelta(hours=2)) if item["claim_status"] == "approved" and item["claim_at"] else None,
                "已完成核验" if item["claim_status"] == "approved" else "",
            ),
        )
        inserted += 1
    return inserted


def insert_repairs(
    cur,
    equipment_by_lab: dict[int, list[dict]],
    labs: list[dict],
    students: list[dict],
    admin_user: dict,
    now: datetime,
) -> int:
    lab_map = {int(item["id"]): item for item in labs}
    preferred_lab_ids = [int(item["id"]) for item in labs[:6]]
    equipment_rows: list[dict] = []
    for lab_id in preferred_lab_ids:
        if equipment_by_lab.get(lab_id):
            equipment_rows.append(equipment_by_lab[lab_id][0])
    if not equipment_rows:
        raise RuntimeError("no equipment available for repair demo seed")

    rows = [
        ("computer", "submitted", "主机无法开机，开机后风扇异响"),
        ("network", "accepted", "交换机端口闪断，课程签到网络不稳定"),
        ("lighting", "processing", "投影区域照明频闪，影响演示拍摄"),
        ("computer", "completed", "学生机蓝屏，已更换内存并回归测试"),
        ("other", "submitted", "实验台插座接触不良，需要检修"),
        ("network", "completed", "无线网络覆盖不稳定，已调整 AP 参数"),
    ]

    inserted = 0
    for index, (issue_type, status, description_text) in enumerate(rows, start=1):
        equipment = equipment_rows[(index - 1) % len(equipment_rows)]
        submitter = students[(index - 1) % len(students)]
        base_time = now - timedelta(days=3 - min(index, 3), hours=index)
        submitted_at = base_time
        accepted_at = submitted_at + timedelta(hours=2) if status in {"accepted", "processing", "completed"} else None
        processing_at = accepted_at + timedelta(hours=4) if status in {"processing", "completed"} and accepted_at else None
        completed_at = processing_at + timedelta(hours=5) if status == "completed" and processing_at else None
        followup_score = 5 if status == "completed" else None
        followup_comment = "处理及时，设备已恢复可用" if status == "completed" else ""
        followup_at = completed_at + timedelta(hours=2) if status == "completed" and completed_at else None
        updated_at = completed_at or processing_at or accepted_at or submitted_at
        lab_id = int(equipment["lab_id"])
        lab_name = str(equipment["lab_name"] or lab_map.get(lab_id, {}).get("name") or "")

        cur.execute(
            """
            INSERT INTO repair_work_order (
                order_no, equipment_id, asset_code, equipment_name, lab_id, lab_name,
                issue_type, description, attachment_url, status,
                submitter_id, submitter_name, assignee_id, assignee_name,
                submitted_at, accepted_at, processing_at, completed_at,
                followup_score, followup_comment, followup_at, created_at, updated_at,
                ai_issue_type, ai_priority, ai_suggestions, ai_confidence
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, '', %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            """,
            (
                f"DEMO20260419{index:02d}",
                int(equipment["id"]),
                str(equipment["asset_code"] or ""),
                str(equipment["equipment_name"] or ""),
                lab_id,
                lab_name,
                issue_type,
                f"{description_text}（{SEED_MARKER}）",
                status,
                int(submitter["id"]),
                str(submitter["username"]),
                int(admin_user["id"]) if status in {"accepted", "processing", "completed"} else None,
                str(admin_user["username"]) if status in {"accepted", "processing", "completed"} else "",
                dt_text(submitted_at),
                dt_text(accepted_at) if accepted_at else None,
                dt_text(processing_at) if processing_at else None,
                dt_text(completed_at) if completed_at else None,
                followup_score,
                followup_comment,
                dt_text(followup_at) if followup_at else None,
                dt_text(submitted_at),
                dt_text(updated_at),
                issue_type,
                "P1" if status in {"submitted", "accepted"} else "P2",
                "先排查供电和网络链路，再复测终端稳定性",
                0.91 if status in {"processing", "completed"} else 0.84,
            ),
        )
        inserted += 1
    return inserted


def insert_courses_and_members(cur, teacher_user: dict, students: list[dict], now: datetime) -> tuple[int, int]:
    courses = [
        ("实验室运维实战", "enabled", "计科 2201"),
        ("数据中心资产管理", "enabled", "计科 2202"),
        ("网络安全攻防演练", "enabled", "网工 2201"),
    ]

    course_ids: list[int] = []
    for index, (name, status, class_name) in enumerate(courses, start=1):
        created_at = now - timedelta(days=10 - index)
        cur.execute(
            """
            INSERT INTO course (
                name, description, teacher_id, teacher_user_name, status,
                created_at, updated_at, class_name, course_code
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                name,
                f"{name}课程用于系统答辩演示场景联调。（{SEED_MARKER}）",
                int(teacher_user["id"]),
                str(teacher_user["username"]),
                status,
                dt_text(created_at),
                dt_text(created_at),
                class_name,
                build_course_code(index),
            ),
        )
        course_ids.append(int(cur.lastrowid))

    member_count = 0
    member_students = students[:9]
    for index, course_id in enumerate(course_ids):
        for student in member_students[index * 3 : (index + 1) * 3]:
            joined_at = now - timedelta(days=7 - index, hours=index + 1)
            cur.execute(
                """
                INSERT INTO course_member (
                    course_id, student_id, student_user_name, student_display_name,
                    status, joined_at, updated_at
                )
                VALUES (%s, %s, %s, %s, 'active', %s, %s)
                """,
                (
                    int(course_id),
                    int(student["id"]),
                    str(student["username"]),
                    str(student["username"]),
                    dt_text(joined_at),
                    dt_text(joined_at),
                ),
            )
            member_count += 1
    return len(course_ids), member_count


def insert_audit_logs(cur, admin_user: dict, now: datetime) -> int:
    rows = [
        ("admin.announcement.publish", "announcement", "demo-announcement", {"tag": SEED_MARKER, "scene": "announcement"}),
        ("reservation.create", "reservation", "demo-reservation", {"tag": SEED_MARKER, "scene": "reservation"}),
        ("repair.create", "repair", "demo-repair", {"tag": SEED_MARKER, "scene": "repair"}),
        ("teacher.course.create", "course", "demo-course", {"tag": SEED_MARKER, "scene": "course"}),
    ]
    inserted = 0
    for index, (action, target_type, target_id, detail) in enumerate(rows, start=1):
        created_at = now - timedelta(minutes=15 - index * 2)
        cur.execute(
            """
            INSERT INTO audit_log (
                operator_id, operator_name, operator_role, action,
                target_type, target_id, detail_json, ip, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                int(admin_user["id"]),
                str(admin_user["username"]),
                "admin",
                action,
                target_type,
                target_id,
                str(detail),
                "127.0.0.1",
                dt_text(created_at),
            ),
        )
        inserted += 1
    return inserted


def seed_demo_data() -> dict:
    conn = pymysql.connect(**DB)
    now = datetime.now().replace(microsecond=0)
    try:
        conn.begin()
        with conn.cursor() as cur:
            students = fetch_users(cur, "student")
            admins = fetch_users(cur, "admin")
            teachers = fetch_users(cur, "teacher")
            labs = fetch_labs(cur)
            equipment_by_lab = fetch_equipment_by_lab(cur)

            if not students:
                raise RuntimeError("no student users found")
            if not admins:
                raise RuntimeError("no admin users found")
            if not teachers:
                raise RuntimeError("no teacher users found")
            if len(labs) < 3:
                raise RuntimeError("not enough labs found")

            admin_user = admins[0]
            teacher_user = teachers[0]

            cleanup_existing_demo_rows(cur)

            summary = {
                "announcements": insert_announcements(cur, admin_user, now),
                "reservations": insert_reservations(cur, labs, students, teacher_user, now),
                "lost_found": insert_lost_found(cur, students, now),
                "repairs": insert_repairs(cur, equipment_by_lab, labs, students, admin_user, now),
            }
            course_count, member_count = insert_courses_and_members(cur, teacher_user, students, now)
            summary["courses"] = course_count
            summary["course_members"] = member_count
            summary["audit_logs"] = insert_audit_logs(cur, admin_user, now)

        conn.commit()
        return summary
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> int:
    summary = seed_demo_data()
    print("Defense demo seed completed:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
