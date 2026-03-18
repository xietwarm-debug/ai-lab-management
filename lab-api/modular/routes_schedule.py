from . import core as _core

for _k, _v in _core.__dict__.items():
    if _k.startswith("__"):
        continue
    globals()[_k] = _v

del _k, _v, _core

_WEEKDAY_ALIAS = {
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "日": 7,
    "天": 7,
    "周一": 1,
    "周二": 2,
    "周三": 3,
    "周四": 4,
    "周五": 5,
    "周六": 6,
    "周日": 7,
    "周天": 7,
    "星期一": 1,
    "星期二": 2,
    "星期三": 3,
    "星期四": 4,
    "星期五": 5,
    "星期六": 6,
    "星期日": 7,
    "星期天": 7,
}


def _parse_date_text(raw_value, field_name="date", required=True):
    text = str(raw_value or "").strip()
    if not text:
        if required:
            raise BizError(f"{field_name} required", 400)
        return ""
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%Y-%m-%d")
    except Exception:
        raise BizError(f"invalid {field_name}", 400)


def _normalize_week_day(raw_value):
    if raw_value in (None, ""):
        return None
    text = str(raw_value or "").strip()
    if text in _WEEKDAY_ALIAS:
        return int(_WEEKDAY_ALIAS[text])
    text = text.replace("星期", "").replace("周", "").strip()
    if text in _WEEKDAY_ALIAS:
        return int(_WEEKDAY_ALIAS[text])
    num = _to_int_or_none(text)
    if num is None:
        return None
    num = int(num)
    return num if 1 <= num <= 7 else None


def _normalize_week_type(raw_value, fallback="all"):
    text = str(raw_value or "").strip().lower()
    if text in {"all", "odd", "even"}:
        return text
    if text in {"单", "单周"}:
        return "odd"
    if text in {"双", "双周"}:
        return "even"
    return str(fallback or "all")


def _normalize_period_range(raw_start, raw_end, raw_text=""):
    start = _to_int_or_none(raw_start)
    end = _to_int_or_none(raw_end)
    text = str(raw_text or "").strip()
    if start is None and end is None and text:
        m = re.search(r"(\d{1,2})\s*[-~到至]\s*(\d{1,2})", text)
        if m:
            start = _to_int_or_none(m.group(1))
            end = _to_int_or_none(m.group(2))
        else:
            m1 = re.search(r"(\d{1,2})", text)
            if m1:
                start = _to_int_or_none(m1.group(1))
                end = start
    if start is None and end is not None:
        start = end
    if end is None and start is not None:
        end = start
    if start is None or end is None:
        return None, None
    start = int(start)
    end = int(end)
    if start <= 0 or end <= 0:
        return None, None
    if start > end:
        start, end = end, start
    return start, end


def _normalize_time_slot_list(raw_text):
    text = str(raw_text or "").strip()
    if not text:
        return []
    parts = re.split(r"[,，;；\n\r]+", text)
    slots = []
    seen = set()
    for part in parts:
        raw = str(part or "").strip()
        if not raw:
            continue
        canonical = _canonicalize_slot_text(raw)
        start_m, end_m = _slot_to_minutes(canonical)
        if start_m is None or end_m is None:
            continue
        if canonical in seen:
            continue
        seen.add(canonical)
        slots.append(canonical)
    return slots


def _build_slot_period_index_map(period_map):
    out = {}
    for idx, cfg in (period_map or {}).items():
        n = int(_to_int_or_none(idx) or 0)
        if n <= 0:
            continue
        start_text = str((cfg or {}).get("startTime") or "").strip()
        end_text = str((cfg or {}).get("endTime") or "").strip()
        if not start_text or not end_text:
            continue
        canonical = _canonicalize_slot_text(f"{start_text}-{end_text}")
        if canonical:
            out[canonical] = n
    return out


def _time_range_from_period(period_map, period_start, period_end):
    s = int(_to_int_or_none(period_start) or 0)
    e = int(_to_int_or_none(period_end) or 0)
    if s <= 0 or e <= 0:
        return ""
    if s > e:
        s, e = e, s
    slots = []
    for idx in range(s, e + 1):
        cfg = (period_map or {}).get(idx) or {}
        start_text = str(cfg.get("startTime") or "").strip()
        end_text = str(cfg.get("endTime") or "").strip()
        if not start_text or not end_text:
            continue
        canonical = _canonicalize_slot_text(f"{start_text}-{end_text}")
        if canonical:
            slots.append(canonical)
    return ",".join(slots)


def _resolve_period_range_from_time_range(raw_time_range, period_map):
    slots = _normalize_time_slot_list(raw_time_range)
    if not slots:
        return None, None, ""
    slot_map = _build_slot_period_index_map(period_map)
    idxs = []
    for slot in slots:
        period_idx = int(_to_int_or_none(slot_map.get(slot)) or 0)
        if period_idx <= 0:
            return None, None, ",".join(slots)
        idxs.append(period_idx)
    idxs = sorted(set(idxs))
    if not idxs:
        return None, None, ",".join(slots)
    period_start = idxs[0]
    period_end = idxs[-1]
    expected = list(range(period_start, period_end + 1))
    if idxs != expected:
        return None, None, ",".join(slots)
    return period_start, period_end, ",".join(slots)


def _normalize_week_range(raw_start, raw_end, raw_text=""):
    start = _to_int_or_none(raw_start)
    end = _to_int_or_none(raw_end)
    text = str(raw_text or "").strip()
    if start is None and end is None and text:
        m = re.search(r"(\d{1,2})\s*[-~到至]\s*(\d{1,2})", text)
        if m:
            start = _to_int_or_none(m.group(1))
            end = _to_int_or_none(m.group(2))
        else:
            m1 = re.search(r"(\d{1,2})", text)
            if m1:
                start = _to_int_or_none(m1.group(1))
                end = start
    if start is None and end is not None:
        start = end
    if end is None and start is not None:
        end = start
    if start is None or end is None:
        return None, None
    start = max(1, int(start))
    end = max(1, int(end))
    if start > end:
        start, end = end, start
    return start, end


def _normalize_schedule_import_items(raw_items, period_map=None):
    items = raw_items if isinstance(raw_items, list) else []
    pmap = period_map if isinstance(period_map, dict) else _get_period_config_map()
    out = []
    errors = []
    for idx, raw in enumerate(items, start=1):
        row = raw if isinstance(raw, dict) else {}
        course_name = str(row.get("courseName") or row.get("name") or "").strip()
        if not course_name:
            errors.append({"row": idx, "reason": "courseName required"})
            continue
        week_day = _normalize_week_day(row.get("weekDay") or row.get("weekday") or row.get("dayOfWeek"))
        if week_day is None:
            errors.append({"row": idx, "reason": "invalid weekDay"})
            continue
        period_start, period_end = _normalize_period_range(
            row.get("periodStart"),
            row.get("periodEnd"),
            row.get("periodRange") or row.get("periodText") or row.get("period"),
        )
        raw_time_range = row.get("timeRange") or row.get("time") or row.get("timeSlots")
        resolved_time_range = ",".join(_normalize_time_slot_list(raw_time_range))
        if not period_start or not period_end:
            period_start, period_end, by_time_range = _resolve_period_range_from_time_range(raw_time_range, pmap)
            if by_time_range and not resolved_time_range:
                resolved_time_range = by_time_range
        if not period_start or not period_end:
            errors.append({"row": idx, "reason": "invalid period/time range"})
            continue
        if not resolved_time_range:
            resolved_time_range = _time_range_from_period(pmap, period_start, period_end)
        week_start, week_end = _normalize_week_range(
            row.get("weekStart"),
            row.get("weekEnd"),
            row.get("weekRange") or row.get("weekText") or row.get("weeks"),
        )
        if not week_start or not week_end:
            errors.append({"row": idx, "reason": "invalid week range"})
            continue
        week_type = _normalize_week_type(row.get("weekType") or row.get("weekMode") or "", "all")
        week_text = str(row.get("weekRange") or row.get("weekText") or row.get("weeks") or "").strip()
        if week_type == "all" and "单" in week_text:
            week_type = "odd"
        if week_type == "all" and "双" in week_text:
            week_type = "even"
        out.append(
            {
                "rowNo": int(_to_int_or_none(row.get("rowNo")) or idx),
                "courseName": course_name,
                "teacherName": str(row.get("teacherName") or row.get("teacher") or "").strip(),
                "className": str(row.get("className") or row.get("majorClass") or row.get("clazz") or "").strip(),
                "labId": _to_int_or_none(row.get("labId")),
                "labName": str(row.get("labName") or row.get("lab") or row.get("room") or "").strip(),
                "weekDay": int(week_day),
                "periodStart": int(period_start),
                "periodEnd": int(period_end),
                "timeRange": str(resolved_time_range or "").strip(),
                "weekStart": int(week_start),
                "weekEnd": int(week_end),
                "weekType": week_type,
                "note": str(row.get("note") or row.get("remark") or "").strip(),
            }
        )
    return out, errors


def _get_period_config_map():
    rows = query(
        """
        SELECT period_index AS periodIndex,
               period_name AS periodName,
               TIME_FORMAT(start_time, '%%H:%%i') AS startTime,
               TIME_FORMAT(end_time, '%%H:%%i') AS endTime
        FROM class_period_configs
        WHERE status='active'
        ORDER BY sort_order ASC, period_index ASC
        """
    )
    out = {}
    for row in rows or []:
        idx = int(_to_int_or_none((row or {}).get("periodIndex")) or 0)
        if idx <= 0:
            continue
        out[idx] = {
            "periodName": str((row or {}).get("periodName") or f"第{idx}节").strip(),
            "startTime": str((row or {}).get("startTime") or "").strip(),
            "endTime": str((row or {}).get("endTime") or "").strip(),
        }
    if out:
        return out
    for item in PERIOD_SLOT_ITEMS:
        idx = int(_to_int_or_none(item.get("index")) or 0)
        if idx <= 0:
            continue
        start_time, end_time = "", ""
        time_text = str(item.get("time") or "").strip()
        if "-" in time_text:
            arr = [x.strip() for x in time_text.split("-", 1)]
            if len(arr) >= 2:
                start_time, end_time = arr[0], arr[1]
        out[idx] = {"periodName": str(item.get("label") or f"第{idx}节"), "startTime": start_time, "endTime": end_time}
    return out


def _period_label(period_map, period_start, period_end):
    s = int(_to_int_or_none(period_start) or 0)
    e = int(_to_int_or_none(period_end) or 0)
    if s <= 0 or e <= 0:
        return ""
    start_time = str(((period_map.get(s) or {}).get("startTime")) or "").strip()
    end_time = str(((period_map.get(e) or {}).get("endTime")) or "").strip()
    if start_time and end_time:
        return f"{s}-{e}节 {start_time}-{end_time}"
    return f"{s}-{e}节"


def _resolve_template_row(template_id=None, only_active=False):
    tpl_id = _to_int_or_none(template_id)
    if tpl_id and int(tpl_id) > 0:
        rows = query(
            """
            SELECT id,
                   term_name AS termName,
                   semester_start_date AS semesterStartDate,
                   semester_weeks AS semesterWeeks,
                   source_type AS sourceType,
                   status,
                   reminder_lead_minutes AS reminderLeadMinutes
            FROM course_schedule_templates
            WHERE id=%s
            LIMIT 1
            """,
            (int(tpl_id),),
        )
        return rows[0] if rows else None
    where = "status='active'" if only_active else "status IN ('active','draft')"
    rows = query(
        f"""
        SELECT id,
               term_name AS termName,
               semester_start_date AS semesterStartDate,
               semester_weeks AS semesterWeeks,
               source_type AS sourceType,
               status,
               reminder_lead_minutes AS reminderLeadMinutes
        FROM course_schedule_templates
        WHERE {where}
        ORDER BY CASE WHEN status='active' THEN 0 ELSE 1 END, id DESC
        LIMIT 1
        """
    )
    return rows[0] if rows else None


def _calc_week_no(semester_start_date, target_date):
    if not semester_start_date or not target_date:
        return 0
    try:
        start_dt = datetime.strptime(str(semester_start_date), "%Y-%m-%d").date()
        date_dt = datetime.strptime(str(target_date), "%Y-%m-%d").date()
    except Exception:
        return 0
    diff = (date_dt - start_dt).days
    return 0 if diff < 0 else int(diff // 7) + 1


def _match_item_on_day(item, week_no, week_day):
    if int(_to_int_or_none((item or {}).get("weekDay")) or 0) != int(week_day or 0):
        return False
    week_start = int(_to_int_or_none((item or {}).get("weekStart")) or 1)
    week_end = int(_to_int_or_none((item or {}).get("weekEnd")) or 20)
    if int(week_no or 0) < week_start or int(week_no or 0) > week_end:
        return False
    week_type = str((item or {}).get("weekType") or "all").strip().lower()
    if week_type == "odd" and int(week_no or 0) % 2 == 0:
        return False
    if week_type == "even" and int(week_no or 0) % 2 != 0:
        return False
    return True


def _build_occurrence_time(date_text, period_start, period_end, period_map):
    d = _parse_date_text(date_text, "date", required=True)
    s = int(_to_int_or_none(period_start) or 0)
    e = int(_to_int_or_none(period_end) or 0)
    start_time = str(((period_map.get(s) or {}).get("startTime")) or "").strip()
    end_time = str(((period_map.get(e) or {}).get("endTime")) or "").strip()
    if not start_time or not end_time:
        return "", ""
    if len(start_time) == 5:
        start_time = f"{start_time}:00"
    if len(end_time) == 5:
        end_time = f"{end_time}:00"
    return f"{d} {start_time}", f"{d} {end_time}"


def _daterange(start_date, end_date):
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    if end < start:
        start, end = end, start
    out = []
    cur = start
    while cur <= end:
        out.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return out


def _resolve_lab_ref_with_cur(cur, raw_lab_id, raw_lab_name):
    lab_id = _to_int_or_none(raw_lab_id)
    lab_name = str(raw_lab_name or "").strip()
    if lab_id and int(lab_id) > 0:
        cur.execute("SELECT id, name FROM lab WHERE id=%s LIMIT 1", (int(lab_id),))
        row = cur.fetchone() or {}
        if row:
            return int(row.get("id") or 0), str(row.get("name") or "").strip()
        return None, lab_name
    if lab_name:
        cur.execute("SELECT id, name FROM lab WHERE name=%s LIMIT 1", (lab_name,))
        row = cur.fetchone() or {}
        if row:
            return int(row.get("id") or 0), str(row.get("name") or "").strip()
    return None, lab_name


def _ensure_reminders_for_range(start_date, end_date, template_row=None):
    start = _parse_date_text(start_date, "startDate", required=True)
    end = _parse_date_text(end_date, "endDate", required=True)
    tpl = template_row or _resolve_template_row(only_active=True)
    if not tpl:
        return {"created": 0, "templateId": 0}
    template_id = int(_to_int_or_none((tpl or {}).get("id")) or 0)
    if template_id <= 0:
        return {"created": 0, "templateId": 0}

    semester_start = str((tpl or {}).get("semesterStartDate") or "").strip()
    semester_weeks = int(_to_int_or_none((tpl or {}).get("semesterWeeks")) or 20)
    lead_minutes = int(_to_int_or_none((tpl or {}).get("reminderLeadMinutes")) or 20)
    lead_minutes = max(0, min(180, lead_minutes))
    period_map = _get_period_config_map()
    items = query(
        """
        SELECT id,
               course_name AS courseName,
               teacher_name AS teacherName,
               class_name AS className,
               lab_id AS labId,
               lab_name AS labName,
               week_day AS weekDay,
               period_start AS periodStart,
               period_end AS periodEnd,
               week_start AS weekStart,
               week_end AS weekEnd,
               week_type AS weekType
        FROM course_schedule_items
        WHERE template_id=%s
          AND status='active'
        ORDER BY week_day ASC, period_start ASC, id ASC
        """,
        (template_id,),
    )
    if not items:
        return {"created": 0, "templateId": template_id}

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    days = _daterange(start, end)
    created = 0

    def _tx(cur):
        nonlocal created
        for day_text in days:
            day_dt = datetime.strptime(day_text, "%Y-%m-%d").date()
            week_day = int(day_dt.isoweekday())
            week_no = _calc_week_no(semester_start, day_text)
            if week_no <= 0:
                continue
            if semester_weeks > 0 and week_no > semester_weeks:
                continue
            for item in items:
                if not _match_item_on_day(item, week_no, week_day):
                    continue
                start_at, end_at = _build_occurrence_time(day_text, item.get("periodStart"), item.get("periodEnd"), period_map)
                remind_at = ""
                if start_at:
                    try:
                        remind_at = (
                            datetime.strptime(start_at, "%Y-%m-%d %H:%M:%S") - timedelta(minutes=lead_minutes)
                        ).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        remind_at = ""
                cur.execute(
                    """
                    INSERT IGNORE INTO door_open_reminders (
                        template_id, schedule_item_id, lab_id, lab_name,
                        course_name, teacher_name, class_name,
                        occurrence_date, week_no, week_day, period_start, period_end,
                        start_at, end_at, remind_at,
                        remind_status, door_status, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        'pending', 'pending', %s, %s
                    )
                    """,
                    (
                        template_id,
                        int(_to_int_or_none(item.get("id")) or 0),
                        _to_int_or_none(item.get("labId")),
                        str(item.get("labName") or "").strip(),
                        str(item.get("courseName") or "").strip(),
                        str(item.get("teacherName") or "").strip(),
                        str(item.get("className") or "").strip(),
                        day_text,
                        week_no,
                        week_day,
                        int(_to_int_or_none(item.get("periodStart")) or 0),
                        int(_to_int_or_none(item.get("periodEnd")) or 0),
                        start_at or None,
                        end_at or None,
                        remind_at or None,
                        now_text,
                        now_text,
                    ),
                )
                created += int(cur.rowcount or 0)
        return created

    run_in_transaction(_tx)
    return {"created": int(created), "templateId": template_id}


def _refresh_reminder_runtime_status(start_date, end_date):
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute(
        """
        UPDATE door_open_reminders
        SET remind_status='sent',
            remind_sent_at=COALESCE(remind_sent_at, %s),
            updated_at=%s
        WHERE occurrence_date BETWEEN %s AND %s
          AND door_status='pending'
          AND remind_status='pending'
          AND remind_at IS NOT NULL
          AND remind_at<=%s
        """,
        (now_text, now_text, start_date, end_date, now_text),
    )
    execute(
        """
        UPDATE door_open_reminders
        SET remind_status='expired',
            updated_at=%s
        WHERE occurrence_date BETWEEN %s AND %s
          AND door_status='pending'
          AND remind_status IN ('pending', 'sent')
          AND end_at IS NOT NULL
          AND end_at<%s
        """,
        (now_text, start_date, end_date, now_text),
    )


def _format_reminder_row(row, period_map):
    data = row or {}
    period_start = int(_to_int_or_none(data.get("periodStart")) or 0)
    period_end = int(_to_int_or_none(data.get("periodEnd")) or 0)
    return {
        "id": int(_to_int_or_none(data.get("id")) or 0),
        "templateId": int(_to_int_or_none(data.get("templateId")) or 0),
        "scheduleItemId": int(_to_int_or_none(data.get("scheduleItemId")) or 0),
        "labId": _to_int_or_none(data.get("labId")),
        "labName": str(data.get("labName") or "").strip(),
        "courseName": str(data.get("courseName") or "").strip(),
        "teacherName": str(data.get("teacherName") or "").strip(),
        "className": str(data.get("className") or "").strip(),
        "occurrenceDate": str(data.get("occurrenceDate") or "").strip(),
        "weekNo": int(_to_int_or_none(data.get("weekNo")) or 0),
        "weekDay": int(_to_int_or_none(data.get("weekDay")) or 0),
        "periodStart": period_start,
        "periodEnd": period_end,
        "periodText": _period_label(period_map, period_start, period_end),
        "startAt": _to_text_time(data.get("startAt")),
        "endAt": _to_text_time(data.get("endAt")),
        "remindAt": _to_text_time(data.get("remindAt")),
        "remindStatus": str(data.get("remindStatus") or "").strip(),
        "doorStatus": str(data.get("doorStatus") or "").strip(),
        "remindSentAt": _to_text_time(data.get("remindSentAt")),
        "handledBy": str(data.get("handledBy") or "").strip(),
        "handledAt": _to_text_time(data.get("handledAt")),
        "handleNote": str(data.get("handleNote") or "").strip(),
    }


def _query_reminders_by_range(start_date, end_date):
    period_map = _get_period_config_map()
    rows = query(
        """
        SELECT id,
               template_id AS templateId,
               schedule_item_id AS scheduleItemId,
               lab_id AS labId,
               lab_name AS labName,
               course_name AS courseName,
               teacher_name AS teacherName,
               class_name AS className,
               occurrence_date AS occurrenceDate,
               week_no AS weekNo,
               week_day AS weekDay,
               period_start AS periodStart,
               period_end AS periodEnd,
               start_at AS startAt,
               end_at AS endAt,
               remind_at AS remindAt,
               remind_status AS remindStatus,
               door_status AS doorStatus,
               remind_sent_at AS remindSentAt,
               handled_by AS handledBy,
               handled_at AS handledAt,
               handle_note AS handleNote
        FROM door_open_reminders
        WHERE occurrence_date BETWEEN %s AND %s
        ORDER BY occurrence_date ASC, period_start ASC, lab_name ASC, id ASC
        """,
        (start_date, end_date),
    )
    return [_format_reminder_row(row, period_map) for row in (rows or [])]


@app.get("/admin/class-period-configs")
@auth_required(roles=["admin"], permissions=[PERMISSION_SCHEDULE_MANAGER])
def admin_list_class_period_configs():
    rows = query(
        """
        SELECT id,
               period_index AS periodIndex,
               period_name AS periodName,
               TIME_FORMAT(start_time, '%%H:%%i') AS startTime,
               TIME_FORMAT(end_time, '%%H:%%i') AS endTime,
               sort_order AS sortOrder,
               status
        FROM class_period_configs
        ORDER BY sort_order ASC, period_index ASC
        """
    )
    return jsonify({"ok": True, "data": rows})


@app.get("/admin/schedule/templates")
@auth_required(roles=["admin"], permissions=[PERMISSION_SCHEDULE_MANAGER])
def admin_list_schedule_templates():
    rows = query(
        """
        SELECT t.id,
               t.term_name AS termName,
               t.semester_start_date AS semesterStartDate,
               t.semester_weeks AS semesterWeeks,
               t.source_type AS sourceType,
               t.status,
               t.reminder_lead_minutes AS reminderLeadMinutes,
               t.created_by AS createdBy,
               t.updated_by AS updatedBy,
               t.created_at AS createdAt,
               t.updated_at AS updatedAt,
               (
                 SELECT COUNT(*)
                 FROM course_schedule_items i
                 WHERE i.template_id=t.id
                   AND i.status='active'
               ) AS itemCount
        FROM course_schedule_templates t
        ORDER BY CASE WHEN t.status='active' THEN 0 ELSE 1 END, t.id DESC
        """
    )
    data = []
    for row in rows or []:
        data.append(
            {
                "id": int(_to_int_or_none((row or {}).get("id")) or 0),
                "termName": str((row or {}).get("termName") or "").strip(),
                "semesterStartDate": str((row or {}).get("semesterStartDate") or "").strip(),
                "semesterWeeks": int(_to_int_or_none((row or {}).get("semesterWeeks")) or 0),
                "sourceType": str((row or {}).get("sourceType") or "").strip(),
                "status": str((row or {}).get("status") or "").strip(),
                "reminderLeadMinutes": int(_to_int_or_none((row or {}).get("reminderLeadMinutes")) or 20),
                "createdBy": str((row or {}).get("createdBy") or "").strip(),
                "updatedBy": str((row or {}).get("updatedBy") or "").strip(),
                "createdAt": _to_text_time((row or {}).get("createdAt")),
                "updatedAt": _to_text_time((row or {}).get("updatedAt")),
                "itemCount": int(_to_int_or_none((row or {}).get("itemCount")) or 0),
            }
        )
    return jsonify({"ok": True, "data": data})


@app.get("/admin/schedule/templates/<int:template_id>")
@auth_required(roles=["admin"], permissions=[PERMISSION_SCHEDULE_MANAGER])
def admin_get_schedule_template_detail(template_id):
    tpl = _resolve_template_row(template_id=template_id)
    if not tpl:
        raise BizError("template not found", 404)
    rows = query(
        """
        SELECT id,
               course_name AS courseName,
               teacher_name AS teacherName,
               class_name AS className,
               lab_id AS labId,
               lab_name AS labName,
               week_day AS weekDay,
               period_start AS periodStart,
               period_end AS periodEnd,
               time_range AS timeRange,
               week_start AS weekStart,
               week_end AS weekEnd,
               week_type AS weekType,
               note,
               source_row_no AS rowNo
        FROM course_schedule_items
        WHERE template_id=%s
          AND status='active'
        ORDER BY week_day ASC, period_start ASC, id ASC
        """,
        (int(template_id),),
    )
    items = []
    for row in rows or []:
        items.append(
            {
                "id": int(_to_int_or_none((row or {}).get("id")) or 0),
                "courseName": str((row or {}).get("courseName") or "").strip(),
                "teacherName": str((row or {}).get("teacherName") or "").strip(),
                "className": str((row or {}).get("className") or "").strip(),
                "labId": _to_int_or_none((row or {}).get("labId")),
                "labName": str((row or {}).get("labName") or "").strip(),
                "weekDay": int(_to_int_or_none((row or {}).get("weekDay")) or 1),
                "periodStart": int(_to_int_or_none((row or {}).get("periodStart")) or 0),
                "periodEnd": int(_to_int_or_none((row or {}).get("periodEnd")) or 0),
                "timeRange": str((row or {}).get("timeRange") or "").strip(),
                "weekStart": int(_to_int_or_none((row or {}).get("weekStart")) or 1),
                "weekEnd": int(_to_int_or_none((row or {}).get("weekEnd")) or 1),
                "weekType": str((row or {}).get("weekType") or "all").strip(),
                "note": str((row or {}).get("note") or "").strip(),
                "rowNo": int(_to_int_or_none((row or {}).get("rowNo")) or 0),
            }
        )
    return jsonify(
        {
            "ok": True,
            "data": {
                "template": {
                    "id": int(_to_int_or_none((tpl or {}).get("id")) or 0),
                    "termName": str((tpl or {}).get("termName") or "").strip(),
                    "semesterStartDate": str((tpl or {}).get("semesterStartDate") or "").strip(),
                    "semesterWeeks": int(_to_int_or_none((tpl or {}).get("semesterWeeks")) or 20),
                    "sourceType": str((tpl or {}).get("sourceType") or "manual").strip(),
                    "status": str((tpl or {}).get("status") or "").strip(),
                    "reminderLeadMinutes": int(_to_int_or_none((tpl or {}).get("reminderLeadMinutes")) or 20),
                    "itemCount": len(items),
                },
                "items": items,
            },
        }
    )


@app.post("/admin/schedule/templates/<int:template_id>/activate")
@auth_required(roles=["admin"], permissions=[PERMISSION_SCHEDULE_MANAGER])
def admin_activate_schedule_template(template_id):
    actor = g.current_user or {}
    operator = str(actor.get("username") or "").strip()
    rows = query("SELECT id FROM course_schedule_templates WHERE id=%s LIMIT 1", (template_id,))
    if not rows:
        raise BizError("template not found", 404)
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute("UPDATE course_schedule_templates SET status='inactive', updated_at=%s WHERE status='active'", (now_text,))
        cur.execute(
            """
            UPDATE course_schedule_templates
            SET status='active', updated_by=%s, updated_at=%s
            WHERE id=%s
            """,
            (operator, now_text, template_id),
        )
        return int(cur.rowcount or 0)

    changed = run_in_transaction(_tx)
    audit_log(
        "admin.schedule.template.activate",
        target_type="course_schedule_templates",
        target_id=template_id,
        detail={"changed": int(changed)},
        actor={"id": actor.get("id"), "username": operator, "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": {"id": int(template_id), "activated": int(changed) > 0}})


@app.post("/admin/schedule/templates/<int:template_id>/delete")
@auth_required(roles=["admin"], permissions=[PERMISSION_SCHEDULE_MANAGER])
def admin_delete_schedule_template(template_id):
    actor = g.current_user or {}
    operator = str(actor.get("username") or "").strip()
    rows = query(
        """
        SELECT id,
               status,
               term_name AS termName
        FROM course_schedule_templates
        WHERE id=%s
        LIMIT 1
        """,
        (template_id,),
    )
    if not rows:
        raise BizError("template not found", 404)
    row = rows[0] or {}
    old_status = str(row.get("status") or "").strip().lower()
    term_name = str(row.get("termName") or "").strip()
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute("DELETE FROM door_open_reminders WHERE template_id=%s", (template_id,))
        deleted_reminders = int(cur.rowcount or 0)
        cur.execute("DELETE FROM course_schedule_items WHERE template_id=%s", (template_id,))
        deleted_items = int(cur.rowcount or 0)
        cur.execute("DELETE FROM course_schedule_templates WHERE id=%s", (template_id,))
        if int(cur.rowcount or 0) <= 0:
            raise BizError("template not found", 404)

        activated_id = 0
        if old_status == "active":
            cur.execute(
                """
                SELECT id
                FROM course_schedule_templates
                ORDER BY id DESC
                LIMIT 1
                """
            )
            next_row = cur.fetchone() or {}
            next_id = int(_to_int_or_none(next_row.get("id")) or 0)
            if next_id > 0:
                cur.execute(
                    """
                    UPDATE course_schedule_templates
                    SET status='inactive', updated_by=%s, updated_at=%s
                    WHERE status='active'
                    """,
                    (operator, now_text),
                )
                cur.execute(
                    """
                    UPDATE course_schedule_templates
                    SET status='active', updated_by=%s, updated_at=%s
                    WHERE id=%s
                    """,
                    (operator, now_text, next_id),
                )
                activated_id = next_id
        return {
            "deletedItems": deleted_items,
            "deletedReminders": deleted_reminders,
            "fallbackActivatedTemplateId": activated_id,
        }

    result = run_in_transaction(_tx)
    audit_log(
        "admin.schedule.template.delete",
        target_type="course_schedule_templates",
        target_id=template_id,
        detail={
            "termName": term_name,
            "oldStatus": old_status,
            "deletedItems": int((result or {}).get("deletedItems") or 0),
            "deletedReminders": int((result or {}).get("deletedReminders") or 0),
            "fallbackActivatedTemplateId": int((result or {}).get("fallbackActivatedTemplateId") or 0),
        },
        actor={"id": actor.get("id"), "username": operator, "role": actor.get("role")},
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "id": int(template_id),
                "deletedItems": int((result or {}).get("deletedItems") or 0),
                "deletedReminders": int((result or {}).get("deletedReminders") or 0),
                "fallbackActivatedTemplateId": int((result or {}).get("fallbackActivatedTemplateId") or 0),
            },
        }
    )


@app.post("/admin/schedule/import")
@auth_required(roles=["admin"], permissions=[PERMISSION_SCHEDULE_MANAGER])
def admin_import_schedule():
    payload = request.get_json(force=True) or {}
    template_payload = payload.get("template") if isinstance(payload.get("template"), dict) else {}
    period_map = _get_period_config_map()
    items, item_errors = _normalize_schedule_import_items(payload.get("items"), period_map=period_map)
    if not items:
        raise BizError("items required", 400)

    actor = g.current_user or {}
    operator = str(actor.get("username") or "").strip()
    template_id = _to_int_or_none(template_payload.get("id") or payload.get("templateId"))
    term_name = str(template_payload.get("termName") or payload.get("termName") or "").strip()[:64]
    start_date = _parse_date_text(
        template_payload.get("semesterStartDate") or payload.get("semesterStartDate"),
        "semesterStartDate",
        required=True,
    )
    semester_weeks = max(1, min(30, int(_to_int_or_none(template_payload.get("semesterWeeks") or payload.get("semesterWeeks")) or 20)))
    lead_minutes = max(
        0,
        min(180, int(_to_int_or_none(template_payload.get("reminderLeadMinutes") or payload.get("reminderLeadMinutes")) or 20)),
    )
    source_type = str(template_payload.get("sourceType") or payload.get("sourceType") or "manual").strip().lower()
    if source_type not in {"manual", "excel"}:
        source_type = "manual"
    mode = str(payload.get("mode") or "replace").strip().lower()
    if mode not in {"replace", "append"}:
        mode = "replace"
    activate = bool(payload.get("activate", True))
    raw_payload = json.dumps(payload.get("raw") if payload.get("raw") is not None else payload, ensure_ascii=False)[:200000]
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        if template_id and int(template_id) > 0:
            cur.execute("SELECT id FROM course_schedule_templates WHERE id=%s LIMIT 1", (int(template_id),))
            if not (cur.fetchone() or {}):
                raise BizError("template not found", 404)
            cur.execute(
                """
                UPDATE course_schedule_templates
                SET term_name=%s,
                    semester_start_date=%s,
                    semester_weeks=%s,
                    source_type=%s,
                    raw_payload=%s,
                    reminder_lead_minutes=%s,
                    updated_by=%s,
                    updated_at=%s
                WHERE id=%s
                """,
                (
                    term_name,
                    start_date,
                    semester_weeks,
                    source_type,
                    raw_payload,
                    lead_minutes,
                    operator,
                    now_text,
                    int(template_id),
                ),
            )
            tpl_id = int(template_id)
        else:
            cur.execute(
                """
                INSERT INTO course_schedule_templates (
                    term_name, semester_start_date, semester_weeks, source_type,
                    raw_payload, status, reminder_lead_minutes,
                    created_by, updated_by, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    term_name,
                    start_date,
                    semester_weeks,
                    source_type,
                    raw_payload,
                    "active" if activate else "draft",
                    lead_minutes,
                    operator,
                    operator,
                    now_text,
                    now_text,
                ),
            )
            tpl_id = int(cur.lastrowid or 0)

        if activate:
            cur.execute(
                """
                UPDATE course_schedule_templates
                SET status='inactive', updated_by=%s, updated_at=%s
                WHERE id<>%s AND status='active'
                """,
                (operator, now_text, tpl_id),
            )
            cur.execute(
                """
                UPDATE course_schedule_templates
                SET status='active', updated_by=%s, updated_at=%s
                WHERE id=%s
                """,
                (operator, now_text, tpl_id),
            )
        elif not template_id:
            cur.execute(
                "UPDATE course_schedule_templates SET status='draft', updated_by=%s, updated_at=%s WHERE id=%s",
                (operator, now_text, tpl_id),
            )

        if mode == "replace":
            cur.execute("DELETE FROM door_open_reminders WHERE template_id=%s", (tpl_id,))
            cur.execute("DELETE FROM course_schedule_items WHERE template_id=%s", (tpl_id,))

        inserted = 0
        for item in items:
            lab_id, lab_name = _resolve_lab_ref_with_cur(cur, item.get("labId"), item.get("labName"))
            cur.execute(
                """
                INSERT INTO course_schedule_items (
                    template_id,
                    course_name, teacher_name, class_name,
                    lab_id, lab_name,
                    week_day, period_start, period_end, time_range,
                    week_start, week_end, week_type,
                    note, source_row_no, status,
                    created_at, updated_at
                ) VALUES (
                    %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, 'active',
                    %s, %s
                )
                """,
                (
                    tpl_id,
                    item.get("courseName"),
                    item.get("teacherName"),
                    item.get("className"),
                    lab_id,
                    lab_name,
                    int(item.get("weekDay") or 1),
                    int(item.get("periodStart") or 1),
                    int(item.get("periodEnd") or 1),
                    str(item.get("timeRange") or "").strip(),
                    int(item.get("weekStart") or 1),
                    int(item.get("weekEnd") or 20),
                    item.get("weekType") or "all",
                    item.get("note") or "",
                    int(item.get("rowNo") or 0),
                    now_text,
                    now_text,
                ),
            )
            inserted += int(cur.rowcount or 0)
        return {"templateId": tpl_id, "inserted": inserted}

    result = run_in_transaction(_tx)
    active_template = _resolve_template_row(template_id=result.get("templateId"))
    if active_template and str(active_template.get("status") or "").strip() == "active":
        today = datetime.now().strftime("%Y-%m-%d")
        preview_end = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        _ensure_reminders_for_range(today, preview_end, active_template)

    audit_log(
        "admin.schedule.import",
        target_type="course_schedule_templates",
        target_id=result.get("templateId"),
        detail={
            "mode": mode,
            "activate": activate,
            "sourceType": source_type,
            "inserted": int((result or {}).get("inserted") or 0),
            "itemInputCount": len(items),
            "errorCount": len(item_errors),
        },
        actor={"id": actor.get("id"), "username": operator, "role": actor.get("role")},
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "templateId": int((result or {}).get("templateId") or 0),
                "inserted": int((result or {}).get("inserted") or 0),
                "errors": item_errors[:100],
            },
        }
    )


@app.get("/admin/door-reminders/today")
@auth_required(roles=["admin"], permissions=[PERMISSION_SCHEDULE_MANAGER])
def admin_today_door_reminders():
    date_text = _parse_date_text(request.args.get("date"), "date", required=False) or datetime.now().strftime("%Y-%m-%d")
    tpl = _resolve_template_row(only_active=True)
    _ensure_reminders_for_range(date_text, date_text, tpl)
    _refresh_reminder_runtime_status(date_text, date_text)
    rows = _query_reminders_by_range(date_text, date_text)
    return jsonify({"ok": True, "data": {"date": date_text, "list": rows}})


@app.get("/admin/door-reminders/week")
@auth_required(roles=["admin"], permissions=[PERMISSION_SCHEDULE_MANAGER])
def admin_week_door_reminders():
    anchor = _parse_date_text(request.args.get("date"), "date", required=False) or datetime.now().strftime("%Y-%m-%d")
    anchor_dt = datetime.strptime(anchor, "%Y-%m-%d").date()
    start = anchor_dt.strftime("%Y-%m-%d")
    end = (anchor_dt + timedelta(days=6)).strftime("%Y-%m-%d")
    tpl = _resolve_template_row(only_active=True)
    _ensure_reminders_for_range(start, end, tpl)
    _refresh_reminder_runtime_status(start, end)
    rows = _query_reminders_by_range(start, end)
    return jsonify({"ok": True, "data": {"startDate": start, "endDate": end, "list": rows}})


@app.get("/admin/door-reminders/records")
@auth_required(roles=["admin"], permissions=[PERMISSION_SCHEDULE_MANAGER])
def admin_door_reminder_records():
    end = _parse_date_text(request.args.get("endDate"), "endDate", required=False) or datetime.now().strftime("%Y-%m-%d")
    start = _parse_date_text(request.args.get("startDate"), "startDate", required=False)
    if not start:
        start = (datetime.strptime(end, "%Y-%m-%d") - timedelta(days=30)).strftime("%Y-%m-%d")
    remind_status = str(request.args.get("remindStatus") or "").strip()
    door_status = str(request.args.get("doorStatus") or "").strip()
    page = max(1, int(_to_int_or_none(request.args.get("page")) or 1))
    page_size = max(1, min(100, int(_to_int_or_none(request.args.get("pageSize")) or 30)))
    where = ["occurrence_date BETWEEN %s AND %s"]
    params = [start, end]
    if remind_status:
        where.append("remind_status=%s")
        params.append(remind_status)
    if door_status:
        where.append("door_status=%s")
        params.append(door_status)
    total_rows = query(f"SELECT COUNT(*) AS cnt FROM door_open_reminders WHERE {' AND '.join(where)}", tuple(params))
    total = int(_to_int_or_none((total_rows[0] if total_rows else {}).get("cnt")) or 0)
    offset = (page - 1) * page_size
    period_map = _get_period_config_map()
    rows = query(
        f"""
        SELECT id,
               template_id AS templateId,
               schedule_item_id AS scheduleItemId,
               lab_id AS labId,
               lab_name AS labName,
               course_name AS courseName,
               teacher_name AS teacherName,
               class_name AS className,
               occurrence_date AS occurrenceDate,
               week_no AS weekNo,
               week_day AS weekDay,
               period_start AS periodStart,
               period_end AS periodEnd,
               start_at AS startAt,
               end_at AS endAt,
               remind_at AS remindAt,
               remind_status AS remindStatus,
               door_status AS doorStatus,
               remind_sent_at AS remindSentAt,
               handled_by AS handledBy,
               handled_at AS handledAt,
               handle_note AS handleNote
        FROM door_open_reminders
        WHERE {' AND '.join(where)}
        ORDER BY occurrence_date DESC, period_start DESC, id DESC
        LIMIT %s OFFSET %s
        """,
        tuple(list(params) + [page_size, offset]),
    )
    data = [_format_reminder_row(row, period_map) for row in (rows or [])]
    return jsonify({"ok": True, "data": data, "meta": {"total": total, "page": page, "pageSize": page_size}})


def _update_reminder_group(reminder_id, target_door_status, target_remind_status, note_text, actor_name):
    rows = query(
        """
        SELECT id,
               occurrence_date AS occurrenceDate,
               lab_id AS labId,
               lab_name AS labName,
               period_start AS periodStart,
               period_end AS periodEnd,
               door_status AS doorStatus
        FROM door_open_reminders
        WHERE id=%s
        LIMIT 1
        """,
        (reminder_id,),
    )
    if not rows:
        raise BizError("reminder not found", 404)
    row = rows[0] or {}
    if str(row.get("doorStatus") or "").strip() in {"opened", "ignored"}:
        return {"changed": 0, "targetIds": [int(reminder_id)]}

    occurrence_date = str(row.get("occurrenceDate") or "").strip()
    lab_id = _to_int_or_none(row.get("labId"))
    lab_name = str(row.get("labName") or "").strip()
    period_start = int(_to_int_or_none(row.get("periodStart")) or 0)
    period_end = int(_to_int_or_none(row.get("periodEnd")) or 0)
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        if lab_id and int(lab_id) > 0:
            cur.execute(
                """
                SELECT id FROM door_open_reminders
                WHERE occurrence_date=%s
                  AND lab_id=%s
                  AND period_start=%s
                  AND period_end=%s
                  AND door_status='pending'
                """,
                (occurrence_date, int(lab_id), period_start, period_end),
            )
        else:
            cur.execute(
                """
                SELECT id FROM door_open_reminders
                WHERE occurrence_date=%s
                  AND lab_name=%s
                  AND period_start=%s
                  AND period_end=%s
                  AND door_status='pending'
                """,
                (occurrence_date, lab_name, period_start, period_end),
            )
        target_rows = cur.fetchall() or []
        target_ids = [int(_to_int_or_none((x or {}).get("id")) or 0) for x in target_rows if int(_to_int_or_none((x or {}).get("id")) or 0) > 0]
        if not target_ids:
            return {"changed": 0, "targetIds": [int(reminder_id)]}
        placeholders = ",".join(["%s"] * len(target_ids))
        cur.execute(
            f"""
            UPDATE door_open_reminders
            SET door_status=%s,
                remind_status=%s,
                handled_by=%s,
                handled_at=%s,
                handle_note=%s,
                updated_at=%s
            WHERE id IN ({placeholders})
            """,
            tuple([target_door_status, target_remind_status, actor_name, now_text, note_text, now_text] + target_ids),
        )
        return {"changed": int(cur.rowcount or 0), "targetIds": target_ids}

    return run_in_transaction(_tx)


@app.post("/admin/door-reminders/<int:reminder_id>/confirm-open")
@auth_required(roles=["admin"], permissions=[PERMISSION_SCHEDULE_MANAGER])
def admin_confirm_open_door(reminder_id):
    payload = request.get_json(force=True) or {}
    actor = g.current_user or {}
    operator = str(actor.get("username") or "").strip()
    note_text = str(payload.get("note") or "管理员已确认开门").strip()[:255]
    result = _update_reminder_group(reminder_id, "opened", "confirmed", note_text, operator)
    audit_log(
        "admin.door_reminder.confirm_open",
        target_type="door_open_reminders",
        target_id=reminder_id,
        detail={"changed": int((result or {}).get("changed") or 0), "targetIds": (result or {}).get("targetIds") or []},
        actor={"id": actor.get("id"), "username": operator, "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": result})


@app.post("/admin/door-reminders/<int:reminder_id>/ignore")
@auth_required(roles=["admin"], permissions=[PERMISSION_SCHEDULE_MANAGER])
def admin_ignore_open_door(reminder_id):
    payload = request.get_json(force=True) or {}
    actor = g.current_user or {}
    operator = str(actor.get("username") or "").strip()
    note_text = str(payload.get("note") or "管理员已忽略").strip()[:255]
    result = _update_reminder_group(reminder_id, "ignored", "ignored", note_text, operator)
    audit_log(
        "admin.door_reminder.ignore",
        target_type="door_open_reminders",
        target_id=reminder_id,
        detail={"changed": int((result or {}).get("changed") or 0), "targetIds": (result or {}).get("targetIds") or []},
        actor={"id": actor.get("id"), "username": operator, "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": result})


def _query_lab_schedule_for_day(lab_id, date_text, template_row=None):
    tpl = template_row or _resolve_template_row(only_active=True)
    if not tpl:
        return {"template": None, "items": []}
    template_id = int(_to_int_or_none((tpl or {}).get("id")) or 0)
    if template_id <= 0:
        return {"template": tpl, "items": []}
    week_no = _calc_week_no(str((tpl or {}).get("semesterStartDate") or ""), date_text)
    week_day = datetime.strptime(date_text, "%Y-%m-%d").date().isoweekday()
    if week_no <= 0:
        return {"template": tpl, "items": []}
    rows = query(
        """
        SELECT id,
               course_name AS courseName,
               teacher_name AS teacherName,
               class_name AS className,
               lab_id AS labId,
               lab_name AS labName,
               week_day AS weekDay,
               period_start AS periodStart,
               period_end AS periodEnd,
               time_range AS timeRange,
               week_start AS weekStart,
               week_end AS weekEnd,
               week_type AS weekType,
               note
        FROM course_schedule_items
        WHERE template_id=%s
          AND status='active'
          AND lab_id=%s
        ORDER BY period_start ASC, id ASC
        """,
        (template_id, lab_id),
    )
    period_map = _get_period_config_map()
    out = []
    for row in rows or []:
        if not _match_item_on_day(row, week_no, week_day):
            continue
        period_start = int(_to_int_or_none((row or {}).get("periodStart")) or 0)
        period_end = int(_to_int_or_none((row or {}).get("periodEnd")) or 0)
        start_at, end_at = _build_occurrence_time(date_text, period_start, period_end, period_map)
        time_range = str((row or {}).get("timeRange") or "").strip()
        if not time_range:
            time_range = _time_range_from_period(period_map, period_start, period_end)
        out.append(
            {
                "id": int(_to_int_or_none((row or {}).get("id")) or 0),
                "courseName": str((row or {}).get("courseName") or "").strip(),
                "teacherName": str((row or {}).get("teacherName") or "").strip(),
                "className": str((row or {}).get("className") or "").strip(),
                "labId": _to_int_or_none((row or {}).get("labId")),
                "labName": str((row or {}).get("labName") or "").strip(),
                "weekNo": int(week_no),
                "weekDay": int(week_day),
                "periodStart": period_start,
                "periodEnd": period_end,
                "timeRange": time_range,
                "periodText": _period_label(period_map, period_start, period_end),
                "startAt": start_at,
                "endAt": end_at,
                "weekType": str((row or {}).get("weekType") or "all").strip(),
                "note": str((row or {}).get("note") or "").strip(),
            }
        )
    return {"template": tpl, "items": out}


@app.get("/admin/labs/<int:lab_id>/schedule/day")
@auth_required(roles=["admin"], permissions=[PERMISSION_SCHEDULE_MANAGER])
def admin_get_lab_schedule_day(lab_id):
    date_text = _parse_date_text(request.args.get("date"), "date", required=False) or datetime.now().strftime("%Y-%m-%d")
    lab_rows = query("SELECT id, name FROM lab WHERE id=%s LIMIT 1", (lab_id,))
    if not lab_rows:
        raise BizError("lab not found", 404)
    tpl = _resolve_template_row(only_active=True)
    _ensure_reminders_for_range(date_text, date_text, tpl)
    result = _query_lab_schedule_for_day(lab_id, date_text, tpl)
    return jsonify(
        {
            "ok": True,
            "data": {
                "date": date_text,
                "lab": {"id": int(lab_id), "name": str((lab_rows[0] or {}).get("name") or "").strip()},
                "template": result.get("template"),
                "list": result.get("items") or [],
            },
        }
    )


@app.get("/admin/labs/<int:lab_id>/schedule/week")
@auth_required(roles=["admin"], permissions=[PERMISSION_SCHEDULE_MANAGER])
def admin_get_lab_schedule_week(lab_id):
    date_text = _parse_date_text(request.args.get("date"), "date", required=False) or datetime.now().strftime("%Y-%m-%d")
    anchor = datetime.strptime(date_text, "%Y-%m-%d").date()
    start_dt = anchor - timedelta(days=anchor.isoweekday() - 1)
    start = start_dt.strftime("%Y-%m-%d")
    end = (start_dt + timedelta(days=6)).strftime("%Y-%m-%d")
    lab_rows = query("SELECT id, name FROM lab WHERE id=%s LIMIT 1", (lab_id,))
    if not lab_rows:
        raise BizError("lab not found", 404)
    tpl = _resolve_template_row(only_active=True)
    _ensure_reminders_for_range(start, end, tpl)
    days = []
    for i in range(7):
        day_text = (start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
        day_result = _query_lab_schedule_for_day(lab_id, day_text, tpl)
        days.append({"date": day_text, "weekDay": int((start_dt + timedelta(days=i)).isoweekday()), "list": day_result.get("items") or []})
    return jsonify(
        {
            "ok": True,
            "data": {
                "startDate": start,
                "endDate": end,
                "lab": {"id": int(lab_id), "name": str((lab_rows[0] or {}).get("name") or "").strip()},
                "template": tpl,
                "days": days,
            },
        }
    )
