from . import core as _core

for _k, _v in _core.__dict__.items():
    if _k.startswith("__"):
        continue
    globals()[_k] = _v

del _k, _v, _core

import math
import random


ATTENDANCE_SESSION_STATUS_SET = {"open", "closed"}
ATTENDANCE_RECORD_STATUS_SET = {"pending_confirm", "present", "suspected", "rejected"}


def _attendance_now():
    return datetime.now()


def _attendance_now_text():
    return _attendance_now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_flag(value, default=False):
    if value in (None, ""):
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}


def _normalize_attendance_code():
    return str((uuid.uuid4().hex[:6]).upper())


def _normalize_attendance_text(value, field_name, max_len=255, allow_empty=True):
    text = str(value or "").strip()
    if not text and not allow_empty:
        raise BizError(f"{field_name} required", 400)
    if len(text) > int(max_len):
        raise BizError(f"{field_name} too long", 400)
    return text


def _normalize_positive_minutes(value, field_name, min_value=1, max_value=180, default_value=15):
    if value in (None, ""):
        return int(default_value)
    num = _to_int_or_none(value)
    if num is None:
        raise BizError(f"invalid {field_name}", 400)
    num = int(num)
    if num < int(min_value) or num > int(max_value):
        raise BizError(f"invalid {field_name}", 400)
    return num


def _normalize_lat_lng(lat, lng):
    lat_val = _safe_float(lat)
    lng_val = _safe_float(lng)
    if lat_val is None or lng_val is None:
        return None, None
    if lat_val < -90 or lat_val > 90 or lng_val < -180 or lng_val > 180:
        raise BizError("invalid location", 400)
    return round(lat_val, 7), round(lng_val, 7)


def _haversine_meters(lat1, lng1, lat2, lng2):
    if None in (lat1, lng1, lat2, lng2):
        return None
    r = 6371000.0
    p1 = math.radians(float(lat1))
    p2 = math.radians(float(lat2))
    dlat = p2 - p1
    dlng = math.radians(float(lng2) - float(lng1))
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 2)


def _get_course_attendance_row(course_id):
    rows = query(
        """
        SELECT id,
               name,
               class_name AS className,
               teacher_user_name AS teacherUserName,
               status
        FROM course
        WHERE id=%s
        LIMIT 1
        """,
        (int(course_id),),
    )
    return rows[0] if rows else None


def _can_manage_attendance_course(current_user, course_row):
    role = str((current_user or {}).get("role") or "").strip().lower()
    username = str((current_user or {}).get("username") or "").strip()
    teacher_user = str((course_row or {}).get("teacherUserName") or "").strip()
    return role == "admin" or (username and username == teacher_user)


def _is_active_course_member(course_id, user_name):
    rows = query(
        """
        SELECT id
        FROM course_member
        WHERE course_id=%s
          AND student_user_name=%s
          AND status='active'
        LIMIT 1
        """,
        (int(course_id), str(user_name or "").strip()),
    )
    return bool(rows)


def _is_course_member_or_manager(course_id, user_name, current_user=None):
    current_user = current_user or {}
    if _can_manage_attendance_course(current_user, _get_course_attendance_row(course_id) or {}):
        return True
    return _is_active_course_member(course_id, user_name)


def _find_lab_row(lab_id=None, lab_name=""):
    lid = _to_int_or_none(lab_id)
    name = str(lab_name or "").strip()
    if lid:
        rows = query("SELECT id, name FROM lab WHERE id=%s LIMIT 1", (int(lid),))
        return rows[0] if rows else None
    if name:
        rows = query("SELECT id, name FROM lab WHERE name=%s LIMIT 1", (name,))
        return rows[0] if rows else None
    return None


def _fetch_attendance_session_row(session_id):
    rows = query(
        """
        SELECT id,
               course_id AS courseId,
               course_name AS courseName,
               teacher_user_name AS teacherUserName,
               lab_id AS labId,
               lab_name AS labName,
               attendance_code AS attendanceCode,
               code_expires_at AS codeExpiresAt,
               recheck_code AS recheckCode,
               recheck_started_at AS recheckStartedAt,
               recheck_expires_at AS recheckExpiresAt,
               status,
               start_at AS startAt,
               end_at AS endAt,
               geo_lat AS geoLat,
               geo_lng AS geoLng,
               geo_radius_meter AS geoRadiusMeter,
               require_location AS requireLocation,
               require_device_binding AS requireDeviceBinding,
               require_seat_code AS requireSeatCode,
               allowed_network_hint AS allowedNetworkHint,
               seat_code_prefix AS seatCodePrefix,
               anti_cheat_mode AS antiCheatMode,
               note,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM attendance_session
        WHERE id=%s
        LIMIT 1
        """,
        (int(session_id),),
    )
    return rows[0] if rows else None


def _format_attendance_session(row, include_secret=False):
    item = dict(row or {})
    code_expires_at = _to_datetime(item.get("codeExpiresAt"))
    recheck_expires_at = _to_datetime(item.get("recheckExpiresAt"))
    now_dt = _attendance_now()
    out = {
        "id": int(item.get("id") or 0),
        "courseId": int(item.get("courseId") or 0),
        "courseName": str(item.get("courseName") or "").strip(),
        "teacherUserName": str(item.get("teacherUserName") or "").strip(),
        "labId": _to_int_or_none(item.get("labId")),
        "labName": str(item.get("labName") or "").strip(),
        "status": str(item.get("status") or "").strip() or "open",
        "startAt": _to_text_time(item.get("startAt")),
        "endAt": _to_text_time(item.get("endAt")),
        "codeExpiresAt": _to_text_time(item.get("codeExpiresAt")),
        "recheckStartedAt": _to_text_time(item.get("recheckStartedAt")),
        "recheckExpiresAt": _to_text_time(item.get("recheckExpiresAt")),
        "geoLat": _safe_float(item.get("geoLat")),
        "geoLng": _safe_float(item.get("geoLng")),
        "geoRadiusMeter": int(item.get("geoRadiusMeter") or 0),
        "requireLocation": bool(int(item.get("requireLocation") or 0) == 1),
        "requireDeviceBinding": bool(int(item.get("requireDeviceBinding") or 0) == 1),
        "requireSeatCode": bool(int(item.get("requireSeatCode") or 0) == 1),
        "allowedNetworkHint": str(item.get("allowedNetworkHint") or "").strip(),
        "seatCodePrefix": str(item.get("seatCodePrefix") or "").strip(),
        "antiCheatMode": str(item.get("antiCheatMode") or "").strip(),
        "note": str(item.get("note") or "").strip(),
        "createdAt": _to_text_time(item.get("createdAt")),
        "updatedAt": _to_text_time(item.get("updatedAt")),
        "codeExpired": bool(code_expires_at == datetime.min or code_expires_at <= now_dt),
        "recheckActive": bool(recheck_expires_at != datetime.min and recheck_expires_at > now_dt),
    }
    if include_secret:
        out["attendanceCode"] = str(item.get("attendanceCode") or "").strip()
        out["recheckCode"] = str(item.get("recheckCode") or "").strip()
    return out


def _format_attendance_record(row):
    item = row or {}
    return {
        "id": int(item.get("id") or 0),
        "sessionId": int(item.get("sessionId") or 0),
        "courseId": int(item.get("courseId") or 0),
        "studentUserName": str(item.get("studentUserName") or "").strip(),
        "studentDisplayName": str(item.get("studentDisplayName") or "").strip(),
        "deviceId": str(item.get("deviceId") or "").strip(),
        "deviceName": str(item.get("deviceName") or "").strip(),
        "networkName": str(item.get("networkName") or "").strip(),
        "seatCode": str(item.get("seatCode") or "").strip(),
        "status": str(item.get("status") or "").strip() or "pending_confirm",
        "latitude": _safe_float(item.get("latitude")),
        "longitude": _safe_float(item.get("longitude")),
        "distanceMeter": _safe_float(item.get("distanceMeter")),
        "suspicionLevel": int(item.get("suspicionLevel") or 0),
        "suspicionReason": str(item.get("suspicionReason") or "").strip(),
        "firstCheckinAt": _to_text_time(item.get("firstCheckinAt")),
        "finalCheckinAt": _to_text_time(item.get("finalCheckinAt")),
        "recheckRequired": bool(int(item.get("recheckRequired") or 0) == 1),
        "recheckCompletedAt": _to_text_time(item.get("recheckCompletedAt")),
        "createdAt": _to_text_time(item.get("createdAt")),
        "updatedAt": _to_text_time(item.get("updatedAt")),
    }


def _fetch_attendance_records(session_id):
    rows = query(
        """
        SELECT id,
               session_id AS sessionId,
               course_id AS courseId,
               student_user_name AS studentUserName,
               student_display_name AS studentDisplayName,
               device_id AS deviceId,
               device_name AS deviceName,
               network_name AS networkName,
               seat_code AS seatCode,
               status,
               latitude,
               longitude,
               distance_meter AS distanceMeter,
               suspicion_level AS suspicionLevel,
               suspicion_reason AS suspicionReason,
               first_checkin_at AS firstCheckinAt,
               final_checkin_at AS finalCheckinAt,
               recheck_required AS recheckRequired,
               recheck_completed_at AS recheckCompletedAt,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM attendance_record
        WHERE session_id=%s
        ORDER BY id DESC
        """,
        (int(session_id),),
    )
    return [_format_attendance_record(row) for row in rows]


def _attendance_summary(records):
    summary = {"total": 0, "present": 0, "suspected": 0, "pendingConfirm": 0, "rejected": 0, "recheckPending": 0}
    for row in records or []:
        summary["total"] += 1
        status = str((row or {}).get("status") or "").strip()
        if status == "present":
            summary["present"] += 1
        elif status == "suspected":
            summary["suspected"] += 1
        elif status == "rejected":
            summary["rejected"] += 1
        else:
            summary["pendingConfirm"] += 1
        if row.get("recheckRequired") and not row.get("recheckCompletedAt"):
            summary["recheckPending"] += 1
    return summary


def _resolve_attendance_display_name(user_name):
    profile = get_user_profile_row_by_username(user_name)
    if not profile:
        return str(user_name or "").strip()
    nickname = str(profile.get("nickname") or "").strip()
    username = str(profile.get("username") or "").strip()
    return nickname or username


def _upsert_device_binding(cur, user_name, device_id, device_name):
    now_text = _attendance_now_text()
    ip = get_client_ip()
    cur.execute(
        """
        INSERT INTO attendance_device_binding (
            user_name, device_id, device_name, bind_status, risk_level,
            last_ip, note, first_seen_at, last_seen_at
        )
        VALUES (%s, %s, %s, 'active', 0, %s, '', %s, %s)
        ON DUPLICATE KEY UPDATE
            device_name=VALUES(device_name),
            last_ip=VALUES(last_ip),
            last_seen_at=VALUES(last_seen_at)
        """,
        (user_name, device_id, device_name, ip, now_text, now_text),
    )


def _attendance_device_risk_with_cur(cur, user_name, device_id):
    reasons = []
    cur.execute(
        """
        SELECT user_name AS userName
        FROM attendance_device_binding
        WHERE device_id=%s
          AND user_name<>%s
          AND bind_status='active'
        LIMIT 5
        """,
        (device_id, user_name),
    )
    other_users = [str((row or {}).get("userName") or "").strip() for row in (cur.fetchall() or []) if str((row or {}).get("userName") or "").strip()]
    if other_users:
        reasons.append("shared_device")
    cur.execute(
        """
        SELECT device_id AS deviceId
        FROM attendance_device_binding
        WHERE user_name=%s
          AND device_id<>%s
          AND bind_status='active'
        ORDER BY last_seen_at DESC
        LIMIT 1
        """,
        (user_name, device_id),
    )
    if cur.fetchone():
        reasons.append("device_changed")
    return reasons


def _assert_can_manage_attendance(session_row, current_user):
    if not session_row:
        raise BizError("attendance session not found", 404)
    course_row = _get_course_attendance_row(session_row.get("courseId"))
    if not course_row:
        raise BizError("course not found", 404)
    if not _can_manage_attendance_course(current_user, course_row):
        raise BizError("forbidden", 403)
    return course_row


@app.get("/teacher/attendance/sessions")
@auth_required(roles=["teacher", "admin"])
def teacher_list_attendance_sessions():
    current_user = g.current_user or {}
    current_role = str(current_user.get("role") or "").strip().lower()
    current_name = str(current_user.get("username") or "").strip()
    course_id = _to_int_or_none(request.args.get("courseId"))
    status = str(request.args.get("status") or "").strip().lower()

    where_sql = " WHERE 1=1"
    params = []
    if current_role != "admin":
        where_sql += " AND teacher_user_name=%s"
        params.append(current_name)
    if course_id:
        where_sql += " AND course_id=%s"
        params.append(int(course_id))
    if status:
        if status not in ATTENDANCE_SESSION_STATUS_SET:
            raise BizError("invalid status", 400)
        where_sql += " AND status=%s"
        params.append(status)

    rows = query(
        """
        SELECT id,
               course_id AS courseId,
               course_name AS courseName,
               teacher_user_name AS teacherUserName,
               lab_id AS labId,
               lab_name AS labName,
               attendance_code AS attendanceCode,
               code_expires_at AS codeExpiresAt,
               recheck_code AS recheckCode,
               recheck_started_at AS recheckStartedAt,
               recheck_expires_at AS recheckExpiresAt,
               status,
               start_at AS startAt,
               end_at AS endAt,
               geo_lat AS geoLat,
               geo_lng AS geoLng,
               geo_radius_meter AS geoRadiusMeter,
               require_location AS requireLocation,
               require_device_binding AS requireDeviceBinding,
               require_seat_code AS requireSeatCode,
               allowed_network_hint AS allowedNetworkHint,
               seat_code_prefix AS seatCodePrefix,
               anti_cheat_mode AS antiCheatMode,
               note,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM attendance_session
        """
        + where_sql
        + """
        ORDER BY id DESC
        LIMIT 100
        """,
        tuple(params),
    )
    data = []
    for row in rows:
        item = _format_attendance_session(row, include_secret=True)
        records = _fetch_attendance_records(item["id"])
        item["summary"] = _attendance_summary(records)
        data.append(item)
    return jsonify({"ok": True, "data": data})


@app.post("/teacher/attendance/sessions")
@auth_required(roles=["teacher", "admin"])
def teacher_create_attendance_session():
    payload = request.get_json(force=True) or {}
    current_user = g.current_user or {}
    teacher_user = str(current_user.get("username") or "").strip()

    course_id = _to_int_or_none(payload.get("courseId"))
    if not course_id or int(course_id) <= 0:
        raise BizError("courseId required", 400)
    course_row = _get_course_attendance_row(course_id)
    if not course_row or str(course_row.get("status") or "").strip() == "deleted":
        raise BizError("course not found", 404)
    if not _can_manage_attendance_course(current_user, course_row):
        raise BizError("forbidden", 403)

    duration_minutes = _normalize_positive_minutes(payload.get("durationMinutes"), "durationMinutes", min_value=5, max_value=240, default_value=15)
    radius_meter = _normalize_positive_minutes(payload.get("geoRadiusMeter"), "geoRadiusMeter", min_value=20, max_value=2000, default_value=150)
    seat_code_prefix = _normalize_attendance_text(payload.get("seatCodePrefix"), "seatCodePrefix", 32, allow_empty=True).upper()
    note = _normalize_attendance_text(payload.get("note"), "note", 255, allow_empty=True)
    network_hint = _normalize_attendance_text(payload.get("allowedNetworkHint"), "allowedNetworkHint", 128, allow_empty=True)
    lab_row = _find_lab_row(payload.get("labId"), payload.get("labName"))
    geo_lat, geo_lng = _normalize_lat_lng(payload.get("geoLat"), payload.get("geoLng"))
    now_dt = _attendance_now()
    start_at = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    end_at = (now_dt + timedelta(minutes=duration_minutes)).strftime("%Y-%m-%d %H:%M:%S")
    code_expires_at = (now_dt + timedelta(seconds=20)).strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            """
            INSERT INTO attendance_session (
                course_id, course_name, teacher_user_name, lab_id, lab_name,
                attendance_code, code_expires_at, status, start_at, end_at,
                geo_lat, geo_lng, geo_radius_meter, require_location,
                require_device_binding, require_seat_code, allowed_network_hint,
                seat_code_prefix, anti_cheat_mode, note, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'open', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                int(course_id),
                str(course_row.get("name") or "").strip(),
                teacher_user,
                _to_int_or_none((lab_row or {}).get("id")),
                str((lab_row or {}).get("name") or payload.get("labName") or "").strip(),
                _normalize_attendance_code(),
                code_expires_at,
                start_at,
                end_at,
                geo_lat,
                geo_lng,
                int(radius_meter),
                1 if _normalize_flag(payload.get("requireLocation"), True) else 0,
                1 if _normalize_flag(payload.get("requireDeviceBinding"), True) else 0,
                1 if _normalize_flag(payload.get("requireSeatCode"), True) else 0,
                network_hint,
                seat_code_prefix,
                "dynamic_geo_device_seat_recheck",
                note,
                _attendance_now_text(),
                _attendance_now_text(),
            ),
        )
        return int(cur.lastrowid or 0)

    session_id = run_in_transaction(_tx)
    row = _fetch_attendance_session_row(session_id)
    audit_log(
        "teacher.attendance.session.create",
        target_type="attendance_session",
        target_id=session_id,
        detail={"courseId": int(course_id), "labName": str((lab_row or {}).get("name") or payload.get("labName") or "").strip()},
        actor={"id": current_user.get("id"), "username": teacher_user, "role": current_user.get("role")},
    )
    return jsonify({"ok": True, "data": _format_attendance_session(row, include_secret=True)})


@app.get("/teacher/attendance/sessions/<int:session_id>")
@auth_required(roles=["teacher", "admin"])
def teacher_get_attendance_session_detail(session_id):
    current_user = g.current_user or {}
    row = _fetch_attendance_session_row(session_id)
    _assert_can_manage_attendance(row, current_user)
    records = _fetch_attendance_records(session_id)
    return jsonify({"ok": True, "data": {"session": _format_attendance_session(row, include_secret=True), "records": records, "summary": _attendance_summary(records)}})


@app.post("/teacher/attendance/sessions/<int:session_id>/refresh-code")
@auth_required(roles=["teacher", "admin"])
def teacher_refresh_attendance_code(session_id):
    current_user = g.current_user or {}
    session_row = _fetch_attendance_session_row(session_id)
    _assert_can_manage_attendance(session_row, current_user)

    now_dt = _attendance_now()
    code_val = _normalize_attendance_code()
    expire_at = (now_dt + timedelta(seconds=20)).strftime("%Y-%m-%d %H:%M:%S")
    execute(
        """
        UPDATE attendance_session
        SET attendance_code=%s,
            code_expires_at=%s,
            updated_at=%s
        WHERE id=%s
        """,
        (code_val, expire_at, _attendance_now_text(), int(session_id)),
    )
    row = _fetch_attendance_session_row(session_id)
    audit_log(
        "teacher.attendance.session.refresh_code",
        target_type="attendance_session",
        target_id=session_id,
        actor={"id": current_user.get("id"), "username": current_user.get("username"), "role": current_user.get("role")},
    )
    return jsonify({"ok": True, "data": _format_attendance_session(row, include_secret=True)})


@app.post("/teacher/attendance/sessions/<int:session_id>/start-recheck")
@auth_required(roles=["teacher", "admin"])
def teacher_start_attendance_recheck(session_id):
    payload = request.get_json(force=True) or {}
    current_user = g.current_user or {}
    session_row = _fetch_attendance_session_row(session_id)
    _assert_can_manage_attendance(session_row, current_user)
    window_seconds = _normalize_positive_minutes(payload.get("windowSeconds"), "windowSeconds", min_value=30, max_value=300, default_value=60)
    ratio = _safe_float(payload.get("ratio"))
    if ratio is None:
        ratio = 0.3
    ratio = max(0.1, min(float(ratio), 1.0))

    now_dt = _attendance_now()
    recheck_code = _normalize_attendance_code()

    def _tx(cur):
        cur.execute(
            """
            SELECT id
            FROM attendance_record
            WHERE session_id=%s
              AND status IN ('present', 'suspected')
            ORDER BY id ASC
            """,
            (int(session_id),),
        )
        rows = cur.fetchall() or []
        record_ids = [int((row or {}).get("id") or 0) for row in rows if int((row or {}).get("id") or 0) > 0]
        if not record_ids:
            raise BizError("no records for recheck", 409)
        sample_count = max(1, int(math.ceil(len(record_ids) * ratio)))
        chosen = random.sample(record_ids, min(sample_count, len(record_ids)))
        expire_text = (now_dt + timedelta(seconds=window_seconds)).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            """
            UPDATE attendance_session
            SET recheck_code=%s,
                recheck_started_at=%s,
                recheck_expires_at=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (recheck_code, _attendance_now_text(), expire_text, _attendance_now_text(), int(session_id)),
        )
        cur.execute("UPDATE attendance_record SET recheck_required=0, updated_at=%s WHERE session_id=%s", (_attendance_now_text(), int(session_id)))
        if chosen:
            placeholders = ",".join(["%s"] * len(chosen))
            cur.execute(
                f"UPDATE attendance_record SET recheck_required=1, updated_at=%s WHERE id IN ({placeholders})",
                tuple([_attendance_now_text()] + chosen),
            )
        for rid in chosen:
            cur.execute(
                """
                INSERT INTO attendance_recheck_log (
                    session_id, record_id, student_user_name, action_type, code_value, seat_code, created_at
                )
                SELECT session_id, id, student_user_name, 'issued', %s, seat_code, %s
                FROM attendance_record
                WHERE id=%s
                LIMIT 1
                """,
                (recheck_code, _attendance_now_text(), int(rid)),
            )
        return chosen

    chosen_ids = run_in_transaction(_tx)
    row = _fetch_attendance_session_row(session_id)
    audit_log(
        "teacher.attendance.session.start_recheck",
        target_type="attendance_session",
        target_id=session_id,
        detail={"targetCount": len(chosen_ids)},
        actor={"id": current_user.get("id"), "username": current_user.get("username"), "role": current_user.get("role")},
    )
    return jsonify({"ok": True, "data": {"session": _format_attendance_session(row, include_secret=True), "targetRecordIds": chosen_ids}})


@app.post("/teacher/attendance/sessions/<int:session_id>/close")
@auth_required(roles=["teacher", "admin"])
def teacher_close_attendance_session(session_id):
    current_user = g.current_user or {}
    session_row = _fetch_attendance_session_row(session_id)
    _assert_can_manage_attendance(session_row, current_user)
    now_text = _attendance_now_text()

    def _tx(cur):
        cur.execute(
            """
            UPDATE attendance_session
            SET status='closed',
                end_at=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (now_text, now_text, int(session_id)),
        )
        cur.execute(
            """
            UPDATE attendance_record
            SET status=CASE
                    WHEN recheck_required=1 AND recheck_completed_at IS NULL AND status='present' THEN 'suspected'
                    ELSE status
                END,
                suspicion_level=CASE
                    WHEN recheck_required=1 AND recheck_completed_at IS NULL THEN GREATEST(suspicion_level, 1)
                    ELSE suspicion_level
                END,
                suspicion_reason=CASE
                    WHEN recheck_required=1 AND recheck_completed_at IS NULL AND COALESCE(suspicion_reason, '')='' THEN 'recheck_not_completed'
                    ELSE suspicion_reason
                END,
                updated_at=%s
            WHERE session_id=%s
            """,
            (now_text, int(session_id)),
        )

    run_in_transaction(_tx)
    records = _fetch_attendance_records(session_id)
    audit_log(
        "teacher.attendance.session.close",
        target_type="attendance_session",
        target_id=session_id,
        detail=_attendance_summary(records),
        actor={"id": current_user.get("id"), "username": current_user.get("username"), "role": current_user.get("role")},
    )
    return jsonify({"ok": True, "data": {"session": _format_attendance_session(_fetch_attendance_session_row(session_id), include_secret=True), "summary": _attendance_summary(records)}})


@app.post("/teacher/attendance/records/<int:record_id>/resolve")
@auth_required(roles=["teacher", "admin"])
def teacher_resolve_attendance_record(record_id):
    payload = request.get_json(force=True) or {}
    next_status = str(payload.get("status") or "").strip().lower()
    if next_status not in {"present", "suspected", "rejected"}:
        raise BizError("invalid status", 400)
    note = _normalize_attendance_text(payload.get("note"), "note", 255, allow_empty=True)
    current_user = g.current_user or {}

    def _tx(cur):
        cur.execute(
            """
            SELECT r.id,
                   r.session_id AS sessionId
            FROM attendance_record r
            WHERE r.id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(record_id),),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("attendance record not found", 404)
        session_row = _fetch_attendance_session_row(row.get("sessionId"))
        _assert_can_manage_attendance(session_row, current_user)
        cur.execute(
            """
            UPDATE attendance_record
            SET status=%s,
                suspicion_reason=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (next_status, note, _attendance_now_text(), int(record_id)),
        )
        cur.execute(
            """
            SELECT id,
                   session_id AS sessionId,
                   course_id AS courseId,
                   student_user_name AS studentUserName,
                   student_display_name AS studentDisplayName,
                   device_id AS deviceId,
                   device_name AS deviceName,
                   network_name AS networkName,
                   seat_code AS seatCode,
                   status,
                   latitude,
                   longitude,
                   distance_meter AS distanceMeter,
                   suspicion_level AS suspicionLevel,
                   suspicion_reason AS suspicionReason,
                   first_checkin_at AS firstCheckinAt,
                   final_checkin_at AS finalCheckinAt,
                   recheck_required AS recheckRequired,
                   recheck_completed_at AS recheckCompletedAt,
                   created_at AS createdAt,
                   updated_at AS updatedAt
            FROM attendance_record
            WHERE id=%s
            LIMIT 1
            """,
            (int(record_id),),
        )
        return _format_attendance_record(cur.fetchone())

    updated_row = run_in_transaction(_tx)
    audit_log(
        "teacher.attendance.record.resolve",
        target_type="attendance_record",
        target_id=record_id,
        detail={"status": next_status},
        actor={"id": current_user.get("id"), "username": current_user.get("username"), "role": current_user.get("role")},
    )
    return jsonify({"ok": True, "data": updated_row})


@app.get("/attendance/active-sessions")
@auth_required(roles=["student"])
def list_my_active_attendance_sessions():
    current_user = g.current_user or {}
    current_name = str(current_user.get("username") or "").strip()
    if not current_name:
        raise BizError("unauthorized", 401)
    rows = query(
        """
        SELECT s.id,
               s.course_id AS courseId,
               s.course_name AS courseName,
               s.teacher_user_name AS teacherUserName,
               s.lab_id AS labId,
               s.lab_name AS labName,
               s.attendance_code AS attendanceCode,
               s.code_expires_at AS codeExpiresAt,
               s.recheck_code AS recheckCode,
               s.recheck_started_at AS recheckStartedAt,
               s.recheck_expires_at AS recheckExpiresAt,
               s.status,
               s.start_at AS startAt,
               s.end_at AS endAt,
               s.geo_lat AS geoLat,
               s.geo_lng AS geoLng,
               s.geo_radius_meter AS geoRadiusMeter,
               s.require_location AS requireLocation,
               s.require_device_binding AS requireDeviceBinding,
               s.require_seat_code AS requireSeatCode,
               s.allowed_network_hint AS allowedNetworkHint,
               s.seat_code_prefix AS seatCodePrefix,
               s.anti_cheat_mode AS antiCheatMode,
               s.note,
               s.created_at AS createdAt,
               s.updated_at AS updatedAt
        FROM attendance_session s
        INNER JOIN course_member cm ON cm.course_id=s.course_id
        WHERE cm.student_user_name=%s
          AND cm.status='active'
          AND s.status='open'
        ORDER BY s.id DESC
        LIMIT 20
        """,
        (current_name,),
    )
    data = []
    for row in rows:
        item = _format_attendance_session(row, include_secret=False)
        record_rows = query(
            """
            SELECT id,
                   session_id AS sessionId,
                   course_id AS courseId,
                   student_user_name AS studentUserName,
                   student_display_name AS studentDisplayName,
                   device_id AS deviceId,
                   device_name AS deviceName,
                   network_name AS networkName,
                   seat_code AS seatCode,
                   status,
                   latitude,
                   longitude,
                   distance_meter AS distanceMeter,
                   suspicion_level AS suspicionLevel,
                   suspicion_reason AS suspicionReason,
                   first_checkin_at AS firstCheckinAt,
                   final_checkin_at AS finalCheckinAt,
                   recheck_required AS recheckRequired,
                   recheck_completed_at AS recheckCompletedAt,
                   created_at AS createdAt,
                   updated_at AS updatedAt
            FROM attendance_record
            WHERE session_id=%s
              AND student_user_name=%s
            LIMIT 1
            """,
            (item["id"], current_name),
        )
        item["myRecord"] = _format_attendance_record(record_rows[0]) if record_rows else None
        data.append(item)
    return jsonify({"ok": True, "data": data})


@app.get("/attendance/sessions/<int:session_id>/me")
@auth_required(roles=["student"])
def get_my_attendance_session_detail(session_id):
    current_user = g.current_user or {}
    current_name = str(current_user.get("username") or "").strip()
    row = _fetch_attendance_session_row(session_id)
    if not row:
        raise BizError("attendance session not found", 404)
    if not _is_active_course_member(row.get("courseId"), current_name):
        raise BizError("forbidden", 403)
    record_rows = query(
        """
        SELECT id,
               session_id AS sessionId,
               course_id AS courseId,
               student_user_name AS studentUserName,
               student_display_name AS studentDisplayName,
               device_id AS deviceId,
               device_name AS deviceName,
               network_name AS networkName,
               seat_code AS seatCode,
               status,
               latitude,
               longitude,
               distance_meter AS distanceMeter,
               suspicion_level AS suspicionLevel,
               suspicion_reason AS suspicionReason,
               first_checkin_at AS firstCheckinAt,
               final_checkin_at AS finalCheckinAt,
               recheck_required AS recheckRequired,
               recheck_completed_at AS recheckCompletedAt,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM attendance_record
        WHERE session_id=%s
          AND student_user_name=%s
        LIMIT 1
        """,
        (int(session_id), current_name),
    )
    return jsonify({"ok": True, "data": {"session": _format_attendance_session(row, include_secret=False), "record": _format_attendance_record(record_rows[0]) if record_rows else None}})


@app.post("/attendance/sessions/<int:session_id>/check-in")
@auth_required(roles=["student"])
def student_attendance_check_in(session_id):
    payload = request.get_json(force=True) or {}
    current_user = g.current_user or {}
    current_name = str(current_user.get("username") or "").strip()
    if not current_name:
        raise BizError("unauthorized", 401)
    session_row = _fetch_attendance_session_row(session_id)
    if not session_row:
        raise BizError("attendance session not found", 404)
    if str(session_row.get("status") or "").strip() != "open":
        raise BizError("attendance session closed", 409)
    if not _is_active_course_member(session_row.get("courseId"), current_name):
        raise BizError("forbidden", 403)

    attendance_code = _normalize_attendance_text(payload.get("attendanceCode"), "attendanceCode", 32, allow_empty=False).upper()
    real_code = str(session_row.get("attendanceCode") or "").strip().upper()
    if attendance_code != real_code:
        raise BizError("invalid attendanceCode", 400)
    code_expires_at = _to_datetime(session_row.get("codeExpiresAt"))
    if code_expires_at == datetime.min or code_expires_at <= _attendance_now():
        raise BizError("attendanceCode expired", 409)

    need_device = bool(int(session_row.get("requireDeviceBinding") or 0) == 1)
    need_seat = bool(int(session_row.get("requireSeatCode") or 0) == 1)
    need_location = bool(int(session_row.get("requireLocation") or 0) == 1)

    device_id = _normalize_attendance_text(payload.get("deviceId"), "deviceId", 128, allow_empty=not need_device)
    device_name = _normalize_attendance_text(payload.get("deviceName"), "deviceName", 128, allow_empty=True)
    seat_code = _normalize_attendance_text(payload.get("seatCode"), "seatCode", 64, allow_empty=not need_seat).upper()
    if need_seat and not seat_code:
        raise BizError("seatCode required", 400)
    seat_prefix = str(session_row.get("seatCodePrefix") or "").strip().upper()
    if seat_prefix and seat_code and not seat_code.startswith(seat_prefix):
        raise BizError("invalid seatCode", 400)

    network_name = _normalize_attendance_text(payload.get("networkName"), "networkName", 128, allow_empty=True)
    lat_val, lng_val = _normalize_lat_lng(payload.get("latitude"), payload.get("longitude"))
    if need_location and (_safe_float(session_row.get("geoLat")) is not None) and lat_val is None:
        raise BizError("location required", 400)

    target_lat = _safe_float(session_row.get("geoLat"))
    target_lng = _safe_float(session_row.get("geoLng"))
    distance = _haversine_meters(target_lat, target_lng, lat_val, lng_val)
    distance_limit = int(session_row.get("geoRadiusMeter") or 0)
    suspicion_reasons = []
    if distance is not None and distance_limit > 0:
        if distance > distance_limit + 30:
            raise BizError("outside attendance area", 409)
        if distance > distance_limit:
            suspicion_reasons.append("geo_edge")
    hint = str(session_row.get("allowedNetworkHint") or "").strip().lower()
    if hint and network_name and hint not in network_name.lower():
        suspicion_reasons.append("network_mismatch")

    display_name = _resolve_attendance_display_name(current_name)
    now_text = _attendance_now_text()

    def _tx(cur):
        device_risks = []
        if need_device:
            if not device_id:
                raise BizError("deviceId required", 400)
            _upsert_device_binding(cur, current_name, device_id, device_name)
            device_risks = _attendance_device_risk_with_cur(cur, current_name, device_id)

        all_reasons = list(suspicion_reasons)
        for item in device_risks:
            if item not in all_reasons:
                all_reasons.append(item)
        status = "present" if not all_reasons else "suspected"

        cur.execute(
            """
            SELECT id
            FROM attendance_record
            WHERE session_id=%s
              AND student_user_name=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(session_id), current_name),
        )
        existing = cur.fetchone()
        if existing:
            record_id = int(existing.get("id") or 0)
            cur.execute(
                """
                UPDATE attendance_record
                SET device_id=%s,
                    device_name=%s,
                    network_name=%s,
                    seat_code=%s,
                    status=%s,
                    latitude=%s,
                    longitude=%s,
                    distance_meter=%s,
                    suspicion_level=%s,
                    suspicion_reason=%s,
                    final_checkin_at=%s,
                    updated_at=%s
                WHERE id=%s
                """,
                (
                    device_id,
                    device_name,
                    network_name,
                    seat_code,
                    status,
                    lat_val,
                    lng_val,
                    distance,
                    len(all_reasons),
                    ",".join(all_reasons),
                    now_text,
                    now_text,
                    record_id,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO attendance_record (
                    session_id, course_id, student_user_name, student_display_name,
                    device_id, device_name, network_name, seat_code, status,
                    latitude, longitude, distance_meter, suspicion_level, suspicion_reason,
                    first_checkin_at, final_checkin_at, recheck_required, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s)
                """,
                (
                    int(session_id),
                    int(session_row.get("courseId") or 0),
                    current_name,
                    display_name,
                    device_id,
                    device_name,
                    network_name,
                    seat_code,
                    status,
                    lat_val,
                    lng_val,
                    distance,
                    len(all_reasons),
                    ",".join(all_reasons),
                    now_text,
                    now_text,
                    now_text,
                    now_text,
                ),
            )
            record_id = int(cur.lastrowid or 0)
        cur.execute(
            """
            SELECT id,
                   session_id AS sessionId,
                   course_id AS courseId,
                   student_user_name AS studentUserName,
                   student_display_name AS studentDisplayName,
                   device_id AS deviceId,
                   device_name AS deviceName,
                   network_name AS networkName,
                   seat_code AS seatCode,
                   status,
                   latitude,
                   longitude,
                   distance_meter AS distanceMeter,
                   suspicion_level AS suspicionLevel,
                   suspicion_reason AS suspicionReason,
                   first_checkin_at AS firstCheckinAt,
                   final_checkin_at AS finalCheckinAt,
                   recheck_required AS recheckRequired,
                   recheck_completed_at AS recheckCompletedAt,
                   created_at AS createdAt,
                   updated_at AS updatedAt
            FROM attendance_record
            WHERE id=%s
            LIMIT 1
            """,
            (record_id,),
        )
        return _format_attendance_record(cur.fetchone())

    record = run_in_transaction(_tx)
    audit_log(
        "student.attendance.check_in",
        target_type="attendance_session",
        target_id=session_id,
        detail={"status": record.get("status"), "distanceMeter": record.get("distanceMeter"), "suspicionReason": record.get("suspicionReason")},
        actor={"id": current_user.get("id"), "username": current_name, "role": current_user.get("role")},
    )
    return jsonify({"ok": True, "data": {"session": _format_attendance_session(session_row, include_secret=False), "record": record}})


@app.post("/attendance/sessions/<int:session_id>/recheck")
@auth_required(roles=["student"])
def student_attendance_recheck(session_id):
    payload = request.get_json(force=True) or {}
    current_user = g.current_user or {}
    current_name = str(current_user.get("username") or "").strip()
    session_row = _fetch_attendance_session_row(session_id)
    if not session_row:
        raise BizError("attendance session not found", 404)
    if not _is_active_course_member(session_row.get("courseId"), current_name):
        raise BizError("forbidden", 403)

    recheck_code = _normalize_attendance_text(payload.get("recheckCode"), "recheckCode", 32, allow_empty=False).upper()
    real_code = str(session_row.get("recheckCode") or "").strip().upper()
    if not real_code or recheck_code != real_code:
        raise BizError("invalid recheckCode", 400)
    recheck_expires_at = _to_datetime(session_row.get("recheckExpiresAt"))
    if recheck_expires_at == datetime.min or recheck_expires_at <= _attendance_now():
        raise BizError("recheckCode expired", 409)

    seat_code = _normalize_attendance_text(payload.get("seatCode"), "seatCode", 64, allow_empty=not bool(int(session_row.get("requireSeatCode") or 0) == 1)).upper()
    seat_prefix = str(session_row.get("seatCodePrefix") or "").strip().upper()
    if seat_prefix and seat_code and not seat_code.startswith(seat_prefix):
        raise BizError("invalid seatCode", 400)
    device_id = _normalize_attendance_text(payload.get("deviceId"), "deviceId", 128, allow_empty=True)
    now_text = _attendance_now_text()

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   device_id AS deviceId,
                   status,
                   suspicion_reason AS suspicionReason
            FROM attendance_record
            WHERE session_id=%s
              AND student_user_name=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(session_id), current_name),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("attendance record not found", 404)
        reasons = [x for x in str(row.get("suspicionReason") or "").split(",") if str(x or "").strip()]
        if device_id and str(row.get("deviceId") or "").strip() and device_id != str(row.get("deviceId") or "").strip():
            if "recheck_device_changed" not in reasons:
                reasons.append("recheck_device_changed")
        next_status = "present" if not reasons else str(row.get("status") or "present").strip()
        cur.execute(
            """
            UPDATE attendance_record
            SET seat_code=CASE WHEN %s<>'' THEN %s ELSE seat_code END,
                status=%s,
                suspicion_level=%s,
                suspicion_reason=%s,
                recheck_completed_at=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (seat_code, seat_code, next_status, len(reasons), ",".join(reasons), now_text, now_text, int(row.get("id") or 0)),
        )
        cur.execute(
            """
            INSERT INTO attendance_recheck_log (
                session_id, record_id, student_user_name, action_type, code_value, seat_code, created_at
            )
            VALUES (%s, %s, %s, 'confirmed', %s, %s, %s)
            """,
            (int(session_id), int(row.get("id") or 0), current_name, recheck_code, seat_code, now_text),
        )
        cur.execute(
            """
            SELECT id,
                   session_id AS sessionId,
                   course_id AS courseId,
                   student_user_name AS studentUserName,
                   student_display_name AS studentDisplayName,
                   device_id AS deviceId,
                   device_name AS deviceName,
                   network_name AS networkName,
                   seat_code AS seatCode,
                   status,
                   latitude,
                   longitude,
                   distance_meter AS distanceMeter,
                   suspicion_level AS suspicionLevel,
                   suspicion_reason AS suspicionReason,
                   first_checkin_at AS firstCheckinAt,
                   final_checkin_at AS finalCheckinAt,
                   recheck_required AS recheckRequired,
                   recheck_completed_at AS recheckCompletedAt,
                   created_at AS createdAt,
                   updated_at AS updatedAt
            FROM attendance_record
            WHERE id=%s
            LIMIT 1
            """,
            (int(row.get("id") or 0),),
        )
        return _format_attendance_record(cur.fetchone())

    record = run_in_transaction(_tx)
    audit_log(
        "student.attendance.recheck",
        target_type="attendance_session",
        target_id=session_id,
        detail={"recordId": record.get("id")},
        actor={"id": current_user.get("id"), "username": current_name, "role": current_user.get("role")},
    )
    return jsonify({"ok": True, "data": {"session": _format_attendance_session(session_row, include_secret=False), "record": record}})
