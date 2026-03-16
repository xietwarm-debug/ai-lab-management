from . import core as _core

for _k, _v in _core.__dict__.items():
    if _k.startswith("__"):
        continue
    globals()[_k] = _v

del _k, _v, _core


def _safe_stats_query(sql, params=None):
    try:
        return query(sql, params or ())
    except Exception as e:
        print(f"[warn] report center query failed: {e}")
        return []


def _query_one(sql, params=None):
    rows = _safe_stats_query(sql, params)
    return (rows or [{}])[0] or {}


def _to_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _to_float(value, digits=2):
    try:
        num = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    if num != num or num == float("inf") or num == float("-inf"):
        return 0.0
    return round(num, int(digits))


def _rate(numerator, denominator, digits=4):
    den = _to_float(denominator, digits=6)
    if den <= 0:
        return 0.0
    return round(_to_float(numerator, digits=6) / den, int(digits))


def _percent(rate_value):
    return f"{round(_to_float(rate_value, digits=6) * 100, 2):.2f}%"


def _build_in_placeholders(items):
    arr = [x for x in (items or []) if x is not None]
    if not arr:
        return "", []
    return ",".join(["%s"] * len(arr)), arr


def _normalize_report_range(start_raw, end_raw, default_days=30, max_days=366):
    start_text = str(start_raw or "").strip()
    end_text = str(end_raw or "").strip()
    start_date = _parse_date_yyyy_mm_dd(start_text)
    end_date = _parse_date_yyyy_mm_dd(end_text)

    if start_text and not start_date:
        raise BizError("invalid startDate", 400)
    if end_text and not end_date:
        raise BizError("invalid endDate", 400)

    if not start_date and not end_date:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=int(default_days) - 1)
    elif start_date and not end_date:
        end_date = start_date + timedelta(days=int(default_days) - 1)
    elif end_date and not start_date:
        start_date = end_date - timedelta(days=int(default_days) - 1)

    if start_date > end_date:
        raise BizError("startDate must be <= endDate", 400)
    days = (end_date - start_date).days + 1
    if days > int(max_days):
        raise BizError("date range too large", 400)
    return start_date, end_date


def _build_report_payload(start_date, end_date):
    now_dt = datetime.now()
    now_text = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    start_text = start_date.strftime("%Y-%m-%d")
    end_text = end_date.strftime("%Y-%m-%d")
    next_text = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")
    days = (end_date - start_date).days + 1
    start_ts = f"{start_text} 00:00:00"
    end_ts = f"{next_text} 00:00:00"

    slot_sql = "CASE WHEN r.time IS NULL OR TRIM(r.time)='' THEN 0 ELSE LENGTH(r.time)-LENGTH(REPLACE(r.time, ',', ''))+1 END"
    slots_per_day = len(DEFAULT_RESERVATION_SLOTS) if isinstance(DEFAULT_RESERVATION_SLOTS, (list, tuple)) and DEFAULT_RESERVATION_SLOTS else 10

    reservation_summary = _query_one(
        f"""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN r.status='pending' THEN 1 ELSE 0 END) AS pendingCnt,
               SUM(CASE WHEN r.status='approved' THEN 1 ELSE 0 END) AS approvedCnt,
               SUM(CASE WHEN r.status='rejected' THEN 1 ELSE 0 END) AS rejectedCnt,
               SUM(CASE WHEN r.status='cancelled' THEN 1 ELSE 0 END) AS cancelledCnt,
               COUNT(DISTINCT r.user_name) AS uniqueUsers,
               SUM({slot_sql}) AS totalSlots,
               SUM(CASE WHEN r.status='approved' THEN {slot_sql} ELSE 0 END) AS approvedSlots
        FROM reservation r
        WHERE r.date >= %s AND r.date <= %s
        """,
        (start_text, end_text),
    )
    reservation_top_rows = _safe_stats_query(
        """
        SELECT COALESCE(NULLIF(TRIM(lab_name), ''), '未命名实验室') AS labName,
               COUNT(*) AS totalCnt
        FROM reservation
        WHERE date >= %s AND date <= %s
        GROUP BY COALESCE(NULLIF(TRIM(lab_name), ''), '未命名实验室')
        ORDER BY totalCnt DESC
        LIMIT 10
        """,
        (start_text, end_text),
    )
    reservation_top = [{"labName": str(x.get("labName") or ""), "total": _to_int(x.get("totalCnt"))} for x in reservation_top_rows]

    lab_rows = _safe_stats_query("SELECT id, name FROM lab ORDER BY id ASC")
    approved_rows = _safe_stats_query(
        f"""
        SELECT COALESCE(NULLIF(TRIM(r.lab_name), ''), '未命名实验室') AS labName,
               SUM({slot_sql}) AS approvedSlots
        FROM reservation r
        WHERE r.status='approved' AND r.date >= %s AND r.date <= %s
        GROUP BY COALESCE(NULLIF(TRIM(r.lab_name), ''), '未命名实验室')
        """,
        (start_text, end_text),
    )
    approved_map = {str(x.get("labName") or "").strip() or "未命名实验室": _to_int(x.get("approvedSlots")) for x in approved_rows}
    lab_util_rows = []
    total_used_slots = 0
    for lab in lab_rows:
        lab_name = str(lab.get("name") or "").strip() or "未命名实验室"
        used_slots = _to_int(approved_map.get(lab_name))
        total_used_slots += used_slots
        available_slots = int(days) * int(slots_per_day)
        lab_util_rows.append(
            {
                "labId": _to_int(lab.get("id")),
                "labName": lab_name,
                "approvedSlots": used_slots,
                "availableSlots": available_slots,
                "utilizationRate": _rate(used_slots, available_slots),
            }
        )
    lab_util_rows.sort(key=lambda x: (_to_float(x.get("utilizationRate"), digits=6), _to_int(x.get("approvedSlots"))), reverse=True)
    total_labs = len(lab_rows)
    total_available_slots = int(total_labs) * int(days) * int(slots_per_day)

    equipment_summary = _query_one(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN status='in_service' THEN 1 ELSE 0 END) AS inServiceCnt,
               SUM(CASE WHEN status='repairing' THEN 1 ELSE 0 END) AS repairingCnt,
               SUM(CASE WHEN status='scrapped' THEN 1 ELSE 0 END) AS scrappedCnt
        FROM equipment
        """
    )
    equipment_repair = _query_one(
        """
        SELECT COUNT(*) AS orderCnt,
               COUNT(DISTINCT CASE WHEN equipment_id IS NOT NULL THEN equipment_id END) AS affectedCnt
        FROM repair_work_order
        WHERE submitted_at >= %s AND submitted_at < %s
        """,
        (start_ts, end_ts),
    )
    issue_rows = _safe_stats_query(
        """
        SELECT issue_type AS issueType, COUNT(*) AS cnt
        FROM repair_work_order
        WHERE submitted_at >= %s AND submitted_at < %s
        GROUP BY issue_type
        ORDER BY cnt DESC
        LIMIT 8
        """,
        (start_ts, end_ts),
    )
    issue_types = [{"issueType": str(x.get("issueType") or "other"), "count": _to_int(x.get("cnt"))} for x in issue_rows]

    repair_eff = _query_one(
        """
        SELECT COUNT(*) AS totalCnt,
               SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completedCnt,
               AVG(CASE WHEN accepted_at IS NOT NULL THEN TIMESTAMPDIFF(MINUTE, submitted_at, accepted_at) END) AS avgResponseMins,
               AVG(CASE WHEN completed_at IS NOT NULL THEN TIMESTAMPDIFF(MINUTE, submitted_at, completed_at) END) AS avgCompleteMins,
               SUM(CASE WHEN completed_at IS NOT NULL AND TIMESTAMPDIFF(HOUR, submitted_at, completed_at) <= 24 THEN 1 ELSE 0 END) AS within24hCnt
        FROM repair_work_order
        WHERE submitted_at >= %s AND submitted_at < %s
        """,
        (start_ts, end_ts),
    )

    task_rows = _safe_stats_query(
        """
        SELECT t.id AS taskId, t.course_id AS courseId, t.title, c.name AS courseName
        FROM experiment_task t
        LEFT JOIN course c ON c.id=t.course_id
        WHERE t.status<>'deleted' AND t.created_at >= %s AND t.created_at < %s
        ORDER BY t.id DESC
        LIMIT 1000
        """,
        (start_ts, end_ts),
    )
    task_ids = [_to_int(x.get("taskId")) for x in task_rows if _to_int(x.get("taskId")) > 0]
    course_ids = [_to_int(x.get("courseId")) for x in task_rows if _to_int(x.get("courseId")) > 0]
    member_map = {}
    if course_ids:
        placeholders, params = _build_in_placeholders(sorted(set(course_ids)))
        if placeholders:
            member_rows = _safe_stats_query(
                f"""
                SELECT course_id AS courseId, COUNT(*) AS cnt
                FROM course_member
                WHERE status='active' AND course_id IN ({placeholders})
                GROUP BY course_id
                """,
                tuple(params),
            )
            member_map = {_to_int(x.get("courseId")): _to_int(x.get("cnt")) for x in member_rows}
    submit_map = {}
    if task_ids:
        placeholders, params = _build_in_placeholders(sorted(set(task_ids)))
        if placeholders:
            submit_rows = _safe_stats_query(
                f"""
                SELECT task_id AS taskId, COUNT(DISTINCT student_user_name) AS cnt
                FROM experiment_task_submission
                WHERE status='active' AND task_id IN ({placeholders})
                GROUP BY task_id
                """,
                tuple(params),
            )
            submit_map = {_to_int(x.get("taskId")): _to_int(x.get("cnt")) for x in submit_rows}
    expected_total = 0
    submitted_total = 0
    for row in task_rows:
        expected = _to_int(member_map.get(_to_int(row.get("courseId"))))
        submitted = min(_to_int(submit_map.get(_to_int(row.get("taskId")))), expected) if expected > 0 else 0
        expected_total += expected
        submitted_total += submitted

    role_rows = _safe_stats_query("SELECT role, COUNT(*) AS cnt FROM user GROUP BY role")
    role_total = {str(x.get("role") or "unknown"): _to_int(x.get("cnt")) for x in role_rows}
    login_users = {str(x.get("username") or "").strip() for x in _safe_stats_query("SELECT username FROM user WHERE last_login_at IS NOT NULL AND last_login_at >= %s AND last_login_at < %s", (start_ts, end_ts))}
    reservation_users = {str(x.get("username") or "").strip() for x in _safe_stats_query("SELECT DISTINCT user_name AS username FROM reservation WHERE created_at >= %s AND created_at < %s", (start_ts, end_ts))}
    repair_users = {str(x.get("username") or "").strip() for x in _safe_stats_query("SELECT DISTINCT submitter_name AS username FROM repair_work_order WHERE submitted_at >= %s AND submitted_at < %s", (start_ts, end_ts))}
    submission_users = {str(x.get("username") or "").strip() for x in _safe_stats_query("SELECT DISTINCT student_user_name AS username FROM experiment_task_submission WHERE status='active' AND created_at >= %s AND created_at < %s", (start_ts, end_ts))}
    active_users = {x for x in (login_users | reservation_users | repair_users | submission_users) if x}

    active_role = {}
    if active_users:
        placeholders, params = _build_in_placeholders(sorted(active_users))
        if placeholders:
            active_role_rows = _safe_stats_query(f"SELECT role, COUNT(*) AS cnt FROM user WHERE username IN ({placeholders}) GROUP BY role", tuple(params))
            active_role = {str(x.get("role") or "unknown"): _to_int(x.get("cnt")) for x in active_role_rows}

    audience_total = _to_int(_query_one("SELECT COUNT(*) AS cnt FROM user WHERE is_active=1 AND is_frozen=0").get("cnt"))
    published_rows = _safe_stats_query(
        """
        SELECT id, title, COALESCE(publish_at, created_at) AS publishAt
        FROM announcement
        WHERE COALESCE(publish_at, created_at) >= %s
          AND COALESCE(publish_at, created_at) < %s
          AND COALESCE(publish_at, created_at) <= %s
        ORDER BY COALESCE(publish_at, created_at) DESC
        LIMIT 300
        """,
        (start_ts, end_ts, now_text),
    )
    announcement_ids = [_to_int(x.get("id")) for x in published_rows if _to_int(x.get("id")) > 0]
    read_map = {}
    unique_readers = 0
    if announcement_ids:
        placeholders, params = _build_in_placeholders(sorted(set(announcement_ids)))
        if placeholders:
            read_rows = _safe_stats_query(
                f"""
                SELECT announcement_id AS announcementId,
                       COUNT(DISTINCT user_name) AS readUsers,
                       COUNT(*) AS readRecords
                FROM announcement_read_state
                WHERE announcement_id IN ({placeholders})
                GROUP BY announcement_id
                """,
                tuple(params),
            )
            read_map = {_to_int(x.get("announcementId")): {"readUsers": _to_int(x.get("readUsers")), "readRecords": _to_int(x.get("readRecords"))} for x in read_rows}
            unique_readers = _to_int(_query_one(f"SELECT COUNT(DISTINCT user_name) AS cnt FROM announcement_read_state WHERE announcement_id IN ({placeholders})", tuple(params)).get("cnt"))

    return {
        "generatedAt": now_text,
        "range": {"startDate": start_text, "endDate": end_text, "days": int(days)},
        "reservation": {
            "summary": {
                "total": _to_int(reservation_summary.get("total")),
                "pending": _to_int(reservation_summary.get("pendingCnt")),
                "approved": _to_int(reservation_summary.get("approvedCnt")),
                "rejected": _to_int(reservation_summary.get("rejectedCnt")),
                "cancelled": _to_int(reservation_summary.get("cancelledCnt")),
                "uniqueUsers": _to_int(reservation_summary.get("uniqueUsers")),
                "totalSlots": _to_int(reservation_summary.get("totalSlots")),
                "approvedSlots": _to_int(reservation_summary.get("approvedSlots")),
            },
            "topLabs": reservation_top,
        },
        "labUtilization": {
            "summary": {
                "totalLabs": int(total_labs),
                "slotsPerDay": int(slots_per_day),
                "totalAvailableSlots": int(total_available_slots),
                "totalUsedSlots": int(total_used_slots),
                "overallRate": _rate(total_used_slots, total_available_slots),
            },
            "labs": lab_util_rows[:20],
        },
        "equipmentFailure": {
            "summary": {
                "equipmentTotal": _to_int(equipment_summary.get("total")),
                "inService": _to_int(equipment_summary.get("inServiceCnt")),
                "repairing": _to_int(equipment_summary.get("repairingCnt")),
                "scrapped": _to_int(equipment_summary.get("scrappedCnt")),
                "repairOrders": _to_int(equipment_repair.get("orderCnt")),
                "affectedEquipments": _to_int(equipment_repair.get("affectedCnt")),
                "orderFailureRate": _rate(_to_int(equipment_repair.get("orderCnt")), _to_int(equipment_summary.get("total"))),
                "affectedFailureRate": _rate(_to_int(equipment_repair.get("affectedCnt")), _to_int(equipment_summary.get("total"))),
            },
            "byIssueType": issue_types,
        },
        "repairEfficiency": {
            "summary": {
                "total": _to_int(repair_eff.get("totalCnt")),
                "completed": _to_int(repair_eff.get("completedCnt")),
                "completionRate": _rate(_to_int(repair_eff.get("completedCnt")), _to_int(repair_eff.get("totalCnt"))),
                "avgResponseMinutes": _to_float(repair_eff.get("avgResponseMins")),
                "avgCompleteMinutes": _to_float(repair_eff.get("avgCompleteMins")),
                "within24hCount": _to_int(repair_eff.get("within24hCnt")),
                "within24hRate": _rate(_to_int(repair_eff.get("within24hCnt")), _to_int(repair_eff.get("completedCnt"))),
            }
        },
        "courseTaskCompletion": {
            "summary": {
                "taskCount": len(task_rows),
                "courseCount": len(set(course_ids)),
                "expectedSubmissions": int(expected_total),
                "submittedSubmissions": int(submitted_total),
                "completionRate": _rate(submitted_total, expected_total),
            }
        },
        "userActivity": {
            "summary": {
                "totalUsers": int(sum(_to_int(v) for v in role_total.values())),
                "activeUsers": int(len(active_users)),
                "activityRate": _rate(len(active_users), sum(_to_int(v) for v in role_total.values())),
                "loginActiveUsers": len([x for x in login_users if x]),
                "reservationActiveUsers": len([x for x in reservation_users if x]),
                "repairActiveUsers": len([x for x in repair_users if x]),
                "submissionActiveUsers": len([x for x in submission_users if x]),
            },
            "byRole": [
                {"role": role, "total": _to_int(role_total.get(role)), "active": _to_int(active_role.get(role)), "activityRate": _rate(_to_int(active_role.get(role)), _to_int(role_total.get(role)))}
                for role in sorted(set(role_total.keys()) | set(active_role.keys()))
            ],
        },
        "announcementReach": {
            "summary": {
                "publishedCount": len(published_rows),
                "activeAudienceUsers": int(audience_total),
                "totalReadRecords": int(sum(_to_int((read_map.get(_to_int(x.get('id'))) or {}).get("readRecords")) for x in published_rows)),
                "uniqueReaders": int(unique_readers),
                "reachRate": _rate(unique_readers, audience_total),
            },
            "items": [
                {
                    "announcementId": _to_int(x.get("id")),
                    "title": str(x.get("title") or ""),
                    "publishAt": _to_text_time(x.get("publishAt")),
                    "readUsers": _to_int((read_map.get(_to_int(x.get("id"))) or {}).get("readUsers")),
                    "readRate": _rate(_to_int((read_map.get(_to_int(x.get("id"))) or {}).get("readUsers")), audience_total),
                }
                for x in published_rows[:30]
            ],
        },
    }


def _build_export_rows(payload):
    data = payload if isinstance(payload, dict) else {}
    rows = []
    range_info = data.get("range") if isinstance(data.get("range"), dict) else {}
    rows.append(
        [
            "数据报表中心",
            f"{range_info.get('startDate') or '-'} ~ {range_info.get('endDate') or '-'}",
            f"生成时间 {data.get('generatedAt') or '-'}",
        ]
    )
    rows.append([])

    reservation = data.get("reservation") if isinstance(data.get("reservation"), dict) else {}
    reservation_summary = reservation.get("summary") if isinstance(reservation.get("summary"), dict) else {}
    rows.append(["预约统计报表", "指标", "值"])
    rows.append(["", "预约总数", _to_int(reservation_summary.get("total"))])
    rows.append(["", "待审批", _to_int(reservation_summary.get("pending"))])
    rows.append(["", "已通过", _to_int(reservation_summary.get("approved"))])
    rows.append(["", "已驳回", _to_int(reservation_summary.get("rejected"))])
    rows.append(["", "已取消", _to_int(reservation_summary.get("cancelled"))])
    rows.append(["", "预约用户数", _to_int(reservation_summary.get("uniqueUsers"))])
    rows.append(["", "预约时段数", _to_int(reservation_summary.get("totalSlots"))])
    rows.append(["", "已通过时段数", _to_int(reservation_summary.get("approvedSlots"))])
    rows.append([])
    rows.append(["预约统计报表-实验室分布", "实验室", "预约总数"])
    for item in reservation.get("topLabs") or []:
        rows.append(["", str((item or {}).get("labName") or ""), _to_int((item or {}).get("total"))])
    rows.append([])

    lab_util = data.get("labUtilization") if isinstance(data.get("labUtilization"), dict) else {}
    lab_summary = lab_util.get("summary") if isinstance(lab_util.get("summary"), dict) else {}
    rows.append(["实验室利用率报表", "指标", "值"])
    rows.append(["", "实验室总数", _to_int(lab_summary.get("totalLabs"))])
    rows.append(["", "总可用时段", _to_int(lab_summary.get("totalAvailableSlots"))])
    rows.append(["", "总已用时段", _to_int(lab_summary.get("totalUsedSlots"))])
    rows.append(["", "整体利用率", _percent(lab_summary.get("overallRate"))])
    rows.append([])

    equipment = data.get("equipmentFailure") if isinstance(data.get("equipmentFailure"), dict) else {}
    equipment_summary = equipment.get("summary") if isinstance(equipment.get("summary"), dict) else {}
    rows.append(["设备故障率报表", "指标", "值"])
    rows.append(["", "设备总数", _to_int(equipment_summary.get("equipmentTotal"))])
    rows.append(["", "报修工单数", _to_int(equipment_summary.get("repairOrders"))])
    rows.append(["", "受影响设备数", _to_int(equipment_summary.get("affectedEquipments"))])
    rows.append(["", "工单故障率", _percent(equipment_summary.get("orderFailureRate"))])
    rows.append(["", "设备故障率", _percent(equipment_summary.get("affectedFailureRate"))])
    rows.append([])

    repair = data.get("repairEfficiency") if isinstance(data.get("repairEfficiency"), dict) else {}
    repair_summary = repair.get("summary") if isinstance(repair.get("summary"), dict) else {}
    rows.append(["报修效率报表", "指标", "值"])
    rows.append(["", "工单总数", _to_int(repair_summary.get("total"))])
    rows.append(["", "已完成", _to_int(repair_summary.get("completed"))])
    rows.append(["", "完成率", _percent(repair_summary.get("completionRate"))])
    rows.append(["", "平均响应时长(分钟)", _to_float(repair_summary.get("avgResponseMinutes"))])
    rows.append(["", "平均闭环时长(分钟)", _to_float(repair_summary.get("avgCompleteMinutes"))])
    rows.append(["", "24小时内完成率", _percent(repair_summary.get("within24hRate"))])
    rows.append([])

    task = data.get("courseTaskCompletion") if isinstance(data.get("courseTaskCompletion"), dict) else {}
    task_summary = task.get("summary") if isinstance(task.get("summary"), dict) else {}
    rows.append(["课程任务完成率报表", "指标", "值"])
    rows.append(["", "任务数", _to_int(task_summary.get("taskCount"))])
    rows.append(["", "课程数", _to_int(task_summary.get("courseCount"))])
    rows.append(["", "应交次数", _to_int(task_summary.get("expectedSubmissions"))])
    rows.append(["", "已交次数", _to_int(task_summary.get("submittedSubmissions"))])
    rows.append(["", "完成率", _percent(task_summary.get("completionRate"))])
    rows.append([])

    user = data.get("userActivity") if isinstance(data.get("userActivity"), dict) else {}
    user_summary = user.get("summary") if isinstance(user.get("summary"), dict) else {}
    rows.append(["用户活跃度报表", "指标", "值"])
    rows.append(["", "用户总数", _to_int(user_summary.get("totalUsers"))])
    rows.append(["", "活跃用户数", _to_int(user_summary.get("activeUsers"))])
    rows.append(["", "活跃率", _percent(user_summary.get("activityRate"))])
    rows.append([])

    announcement = data.get("announcementReach") if isinstance(data.get("announcementReach"), dict) else {}
    announcement_summary = announcement.get("summary") if isinstance(announcement.get("summary"), dict) else {}
    rows.append(["公告触达报表", "指标", "值"])
    rows.append(["", "发布公告数", _to_int(announcement_summary.get("publishedCount"))])
    rows.append(["", "可触达用户数", _to_int(announcement_summary.get("activeAudienceUsers"))])
    rows.append(["", "阅读用户数", _to_int(announcement_summary.get("uniqueReaders"))])
    rows.append(["", "触达率", _percent(announcement_summary.get("reachRate"))])
    rows.append([])
    rows.append(["公告触达报表-公告明细", "公告标题", "发布时间", "阅读用户数", "触达率"])
    for item in announcement.get("items") or []:
        rows.append(
            [
                "",
                str((item or {}).get("title") or ""),
                str((item or {}).get("publishAt") or ""),
                _to_int((item or {}).get("readUsers")),
                _percent((item or {}).get("readRate")),
            ]
        )
    return rows


def _rows_to_excel_html(rows):
    def _escape_html(value):
        text = str(value or "")
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    parts = [
        "<html><head><meta charset='utf-8' />",
        "<style>table{border-collapse:collapse;font-size:12px;}td{border:1px solid #94a3b8;padding:6px 8px;}</style>",
        "</head><body><table>",
    ]
    for row in rows or []:
        if not row:
            parts.append("<tr><td></td></tr>")
            continue
        parts.append("<tr>")
        for cell in row:
            parts.append(f"<td>{_escape_html(cell)}</td>")
        parts.append("</tr>")
    parts.append("</table></body></html>")
    return "".join(parts)


@app.get("/admin/reports/center")
@auth_required(roles=["admin"])
def admin_report_center():
    try:
        start_date, end_date = _normalize_report_range(request.args.get("startDate"), request.args.get("endDate"))
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    return jsonify({"ok": True, "data": _build_report_payload(start_date, end_date)})


@app.get("/admin/reports/center/export")
@auth_required(roles=["admin"])
def export_admin_report_center():
    try:
        start_date, end_date = _normalize_report_range(request.args.get("startDate"), request.args.get("endDate"))
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    payload = _build_report_payload(start_date, end_date)
    rows = _build_export_rows(payload)
    file_tag = f"{payload.get('range', {}).get('startDate', '')}_{payload.get('range', {}).get('endDate', '')}".strip("_") or datetime.now().strftime("%Y%m%d")
    export_format = str(request.args.get("format") or "csv").strip().lower()

    if export_format in {"excel", "xls", "xlsx"}:
        return (
            _rows_to_excel_html(rows),
            200,
            {
                "Content-Type": "application/vnd.ms-excel; charset=utf-8",
                "Content-Disposition": f"attachment; filename=admin_report_center_{file_tag}.xls",
            },
        )

    output = io.StringIO()
    writer = csv.writer(output)
    for row in rows:
        writer.writerow(list(row or []))
    return (
        "\ufeff" + output.getvalue(),
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f"attachment; filename=admin_report_center_{file_tag}.csv",
        },
    )


def _overview_count(sql, params=None):
    rows = query(sql, params or ())
    return int((rows[0] or {}).get("cnt") or 0) if rows else 0


def _overview_state_time(read_state, notice_type):
    state = read_state if isinstance(read_state, dict) else {}
    return _to_datetime(state.get(notice_type))


def _overview_since_clause(column_name, since_dt):
    if not column_name or since_dt == datetime.min:
        return "", []
    return f" AND {column_name} > %s", [since_dt.strftime("%Y-%m-%d %H:%M:%S")]


def _count_overview_reservation_unread(user_name, read_state):
    user = str(user_name or "").strip()
    if not user:
        return 0
    since_dt = _overview_state_time(read_state, "reservation")
    since_sql, since_params = _overview_since_clause("created_at", since_dt)
    return _overview_count(
        "SELECT COUNT(*) AS cnt FROM reservation WHERE user_name=%s" + since_sql,
        tuple([user] + since_params),
    )


def _count_overview_repair_unread(user_name, role, read_state):
    since_dt = _overview_state_time(read_state, "repair")
    since_sql, since_params = _overview_since_clause("COALESCE(updated_at, submitted_at)", since_dt)
    params = list(since_params)
    if str(role or "").strip().lower() == "admin":
        sql = "SELECT COUNT(*) AS cnt FROM repair_work_order WHERE 1=1" + since_sql
    else:
        user = str(user_name or "").strip()
        if not user:
            return 0
        sql = "SELECT COUNT(*) AS cnt FROM repair_work_order WHERE submitter_name=%s" + since_sql
        params = [user] + params
    return _overview_count(sql, tuple(params))


def _count_overview_sensor_alarm_unread(role, read_state):
    if str(role or "").strip().lower() != "admin":
        return 0
    since_dt = _overview_state_time(read_state, "sensor_alarm")
    since_sql, since_params = _overview_since_clause("created_at", since_dt)
    return _overview_count(
        "SELECT COUNT(*) AS cnt FROM lab_sensor_alarm WHERE 1=1" + since_sql,
        tuple(since_params),
    )


def _count_overview_lostfound_unread(user_name, read_state):
    user = str(user_name or "").strip()
    if not user:
        return 0
    since_dt = _overview_state_time(read_state, "lostfound")
    since_sql, since_params = _overview_since_clause("COALESCE(claim_reviewed_at, claim_apply_at, created_at)", since_dt)
    owner_count = _overview_count(
        "SELECT COUNT(*) AS cnt FROM lost_found WHERE owner=%s" + since_sql,
        tuple([user] + since_params),
    )
    claimant_count = _overview_count(
        "SELECT COUNT(*) AS cnt FROM lost_found WHERE claim_apply_user=%s AND owner<>%s" + since_sql,
        tuple([user, user] + since_params),
    )
    return owner_count + claimant_count


def _count_overview_course_task_unread(user_name, read_state):
    user = str(user_name or "").strip()
    if not user:
        return 0
    since_dt = _overview_state_time(read_state, "course_task")
    since_sql, since_params = _overview_since_clause("created_at", since_dt)
    return _overview_count(
        "SELECT COUNT(*) AS cnt FROM course_task_notice WHERE to_user_name=%s AND status='active'" + since_sql,
        tuple([user] + since_params),
    )


def _count_overview_asset_borrow_unread(user_name, role, read_state):
    since_dt = _overview_state_time(read_state, "asset_borrow")
    user = str(user_name or "").strip()
    role_text = str(role or "").strip().lower()
    if role_text == "admin":
        if since_dt == datetime.min:
            return _overview_count(
                """
                SELECT COUNT(*) AS cnt
                FROM equipment_borrow_request
                WHERE status='pending'
                   OR (status='approved' AND returned_at IS NULL AND expected_return_at IS NOT NULL AND expected_return_at < %s)
                """,
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),),
            )
        since_text = since_dt.strftime("%Y-%m-%d %H:%M:%S")
        return _overview_count(
            """
            SELECT COUNT(*) AS cnt
            FROM equipment_borrow_request
            WHERE (
                    status='pending'
                    OR (status='approved' AND returned_at IS NULL AND expected_return_at IS NOT NULL AND expected_return_at < %s)
                  )
              AND created_at > %s
            """,
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), since_text),
        )

    if not user:
        return 0

    if since_dt == datetime.min:
        request_count = _overview_count(
            """
            SELECT COUNT(*) AS cnt
            FROM equipment_borrow_request
            WHERE applicant_user_name=%s
            """,
            (user,),
        )
        remind_count = _overview_count(
            """
            SELECT COUNT(*) AS cnt
            FROM equipment_borrow_reminder_log l
            INNER JOIN equipment_borrow_request r ON r.id=l.request_id
            WHERE r.applicant_user_name=%s
            """,
            (user,),
        )
        return request_count + remind_count

    since_text = since_dt.strftime("%Y-%m-%d %H:%M:%S")
    request_count = _overview_count(
        """
        SELECT COUNT(*) AS cnt
        FROM equipment_borrow_request
        WHERE applicant_user_name=%s
          AND (
                CASE status
                    WHEN 'pending' THEN created_at
                    WHEN 'approved' THEN COALESCE(approved_at, updated_at, created_at)
                    WHEN 'rejected' THEN COALESCE(updated_at, created_at)
                    WHEN 'returned' THEN COALESCE(returned_at, updated_at, created_at)
                    ELSE COALESCE(updated_at, created_at)
                END
              ) > %s
        """,
        (user, since_text),
    )
    remind_count = _overview_count(
        """
        SELECT COUNT(*) AS cnt
        FROM equipment_borrow_reminder_log l
        INNER JOIN equipment_borrow_request r ON r.id=l.request_id
        WHERE r.applicant_user_name=%s
          AND l.created_at > %s
        """,
        (user, since_text),
    )
    return request_count + remind_count


def _count_overview_notifications(user_name, role):
    read_state = get_notification_read_state(user_name)
    return {
        "reservation": _count_overview_reservation_unread(user_name, read_state),
        "repair": _count_overview_repair_unread(user_name, role, read_state),
        "sensor_alarm": _count_overview_sensor_alarm_unread(role, read_state),
        "lostfound": _count_overview_lostfound_unread(user_name, read_state),
        "course_task": _count_overview_course_task_unread(user_name, read_state),
        "asset_borrow": _count_overview_asset_borrow_unread(user_name, role, read_state),
    }


def _count_overview_teacher_pending_reviews(user_name):
    user = str(user_name or "").strip()
    if not user:
        return 0
    return _overview_count(
        """
        SELECT COUNT(*) AS cnt
        FROM experiment_task_submission s
        INNER JOIN experiment_task t ON t.id=s.task_id
        INNER JOIN course c ON c.id=s.course_id
        WHERE (s.review_status='pending' OR s.review_status IS NULL OR s.review_status='')
          AND (t.teacher_user_name=%s OR c.teacher_user_name=%s)
        """,
        (user, user),
    )


def _build_admin_overview(current_user):
    user_name = str((current_user or {}).get("username") or "").strip()
    unread_map = _count_overview_notifications(user_name, "admin")
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "role": "admin",
        "lastUpdated": last_updated,
        "metrics": {
            "labCount": _overview_count("SELECT COUNT(*) AS cnt FROM lab"),
            "labFreeCount": _overview_count(
                """
                SELECT COUNT(*) AS cnt
                FROM lab
                WHERE LOWER(COALESCE(status, '')) IN ('free', 'available', 'idle')
                """
            ),
            "pendingCount": _overview_count("SELECT COUNT(*) AS cnt FROM reservation WHERE status='pending'"),
            "borrowPendingCount": _overview_count("SELECT COUNT(*) AS cnt FROM equipment_borrow_request WHERE status='pending'"),
            "borrowOverdueCount": _overview_count(
                """
                SELECT COUNT(*) AS cnt
                FROM equipment_borrow_request
                WHERE status='approved'
                  AND returned_at IS NULL
                  AND expected_return_at IS NOT NULL
                  AND expected_return_at < %s
                """,
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),),
            ),
            "lostOpenCount": _overview_count("SELECT COUNT(*) AS cnt FROM lost_found WHERE status='open'"),
            "claimPendingCount": _overview_count(
                """
                SELECT COUNT(*) AS cnt
                FROM lost_found
                WHERE item_type='found'
                  AND status='open'
                  AND claim_apply_status='pending'
                """
            ),
            "repairPendingCount": _overview_count(
                "SELECT COUNT(*) AS cnt FROM repair_work_order WHERE status IN ('submitted','accepted','processing')"
            ),
            "adminUnreadCount": sum(int(v or 0) for v in unread_map.values()),
            "userCount": _overview_count("SELECT COUNT(*) AS cnt FROM user"),
        },
        "meta": {
            "unreadByType": unread_map,
        },
    }


def _build_member_overview(current_user):
    user_name = str((current_user or {}).get("username") or "").strip()
    role = str((current_user or {}).get("role") or "").strip().lower()
    unread_map = _count_overview_notifications(user_name, role)
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    repair_total = _overview_count("SELECT COUNT(*) AS cnt FROM repair_work_order WHERE submitter_name=%s", (user_name,))
    data = {
        "role": role,
        "lastUpdated": last_updated,
        "metrics": {
            "studentReservationCount": _overview_count("SELECT COUNT(*) AS cnt FROM reservation WHERE user_name=%s", (user_name,)),
            "studentPendingReservationCount": _overview_count(
                "SELECT COUNT(*) AS cnt FROM reservation WHERE user_name=%s AND status='pending'",
                (user_name,),
            ),
            "studentBorrowPendingCount": _overview_count(
                "SELECT COUNT(*) AS cnt FROM equipment_borrow_request WHERE applicant_user_name=%s AND status='pending'",
                (user_name,),
            ),
            "studentRepairCount": repair_total,
            "studentRepairActiveCount": _overview_count(
                """
                SELECT COUNT(*) AS cnt
                FROM repair_work_order
                WHERE submitter_name=%s
                  AND status IN ('submitted','accepted','processing')
                """,
                (user_name,),
            ),
            "studentUnreadCount": sum(int(v or 0) for v in unread_map.values()),
            "teacherPendingReviewCount": 0,
        },
        "meta": {
            "unreadByType": unread_map,
        },
    }
    if role == "teacher":
        data["metrics"]["teacherPendingReviewCount"] = _count_overview_teacher_pending_reviews(user_name)
    return data


def _build_workbench_overview(current_user):
    role = str((current_user or {}).get("role") or "").strip().lower()
    if role == "admin":
        return _build_admin_overview(current_user)
    if role in {"teacher", "student"}:
        return _build_member_overview(current_user)
    raise BizError("forbidden", 403)


@app.get("/overview")
@auth_required()
def get_workbench_overview():
    current_user = g.current_user or {}
    return jsonify({"ok": True, "data": _build_workbench_overview(current_user)})


@app.get("/overview/me")
@auth_required()
def get_my_workbench_overview():
    current_user = g.current_user or {}
    return jsonify({"ok": True, "data": _build_workbench_overview(current_user)})
