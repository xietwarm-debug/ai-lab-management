from . import core as _core
import random

for _k, _v in _core.__dict__.items():
    if _k.startswith("__"):
        continue
    globals()[_k] = _v

del _k, _v, _core

_LAB_SENSOR_LOCK = Lock()
_LAB_SENSOR_CACHE = {}
_SENSOR_CACHE_TTL_SECONDS = 8
_SENSOR_ALARM_COOLDOWN_SECONDS = 120


def _module_level(value, warning_low=None, warning_high=None, alarm_low=None, alarm_high=None):
    level = "normal"
    if alarm_low is not None and value < alarm_low:
        return "alarm"
    if alarm_high is not None and value > alarm_high:
        return "alarm"
    if warning_low is not None and value < warning_low:
        return "warning"
    if warning_high is not None and value > warning_high:
        return "warning"
    return level


def _level_rank(level):
    if level == "alarm":
        return 2
    if level == "warning":
        return 1
    return 0


def _overall_level(levels):
    max_level = "normal"
    for lv in levels:
        if _level_rank(lv) > _level_rank(max_level):
            max_level = lv
    return max_level


def _simulate_sensor_readings(capacity):
    safe_capacity = max(1, int(capacity or 1))
    temperature = round(random.uniform(21.0, 31.5), 1)
    humidity = round(random.uniform(38.0, 68.0), 1)
    smoke_ppm = round(random.uniform(2.0, 45.0), 1)
    voltage = round(random.uniform(214.0, 232.0), 1)
    current_amp = round(random.uniform(1.0, 10.5), 2)
    people_count = random.randint(0, safe_capacity)

    # Inject occasional anomalies for warning/alarm simulation.
    if random.random() < 0.16:
        temperature = round(random.uniform(35.0, 44.5), 1)
    if random.random() < 0.09:
        smoke_ppm = round(random.uniform(90.0, 220.0), 1)
    if random.random() < 0.1:
        voltage = round(random.uniform(176.0, 198.0), 1) if random.random() < 0.5 else round(random.uniform(246.0, 268.0), 1)
    if random.random() < 0.08:
        current_amp = round(random.uniform(18.0, 34.0), 2)
    if random.random() < 0.12:
        people_count = random.randint(safe_capacity + 1, safe_capacity + 18)

    return {
        "temperatureC": temperature,
        "humidityPct": humidity,
        "smokePpm": smoke_ppm,
        "voltageV": voltage,
        "currentA": current_amp,
        "peopleCount": int(people_count),
    }


def _build_sensor_payload(lab_row):
    lab_id = int(lab_row.get("id") or 0)
    lab_name = str(lab_row.get("name") or "").strip() or f"LAB-{lab_id}"
    capacity = max(0, int(_to_int_or_none(lab_row.get("capacity")) or 0))
    readings = _simulate_sensor_readings(capacity if capacity > 0 else 40)

    module_levels = {
        "temperature": _module_level(readings["temperatureC"], warning_high=35.0, alarm_high=39.0),
        "humidity": _module_level(readings["humidityPct"], warning_low=30.0, warning_high=75.0, alarm_low=20.0, alarm_high=85.0),
        "smoke": _module_level(readings["smokePpm"], warning_high=80.0, alarm_high=120.0),
        "voltage": _module_level(readings["voltageV"], warning_low=205.0, warning_high=245.0, alarm_low=195.0, alarm_high=255.0),
        "current": _module_level(readings["currentA"], warning_high=16.0, alarm_high=24.0),
        "people": _module_level(
            float(readings["peopleCount"]),
            warning_high=float(max(capacity, 1)),
            alarm_high=float(max(int(capacity * 1.3), capacity + 1)),
        ),
    }

    alerts = []
    if module_levels["temperature"] != "normal":
        alerts.append(
            {
                "code": "temp_high",
                "level": module_levels["temperature"],
                "message": f"实验室温度偏高（{readings['temperatureC']}°C）",
                "metric": {"temperatureC": readings["temperatureC"]},
            }
        )
    if module_levels["smoke"] != "normal":
        alerts.append(
            {
                "code": "smoke_detected",
                "level": module_levels["smoke"],
                "message": f"检测到烟雾浓度异常（{readings['smokePpm']} ppm）",
                "metric": {"smokePpm": readings["smokePpm"]},
            }
        )
    if module_levels["voltage"] != "normal":
        alerts.append(
            {
                "code": "voltage_fault",
                "level": module_levels["voltage"],
                "message": f"电压异常（{readings['voltageV']} V）",
                "metric": {"voltageV": readings["voltageV"]},
            }
        )
    if module_levels["current"] != "normal":
        alerts.append(
            {
                "code": "current_overload",
                "level": module_levels["current"],
                "message": f"电流异常（{readings['currentA']} A）",
                "metric": {"currentA": readings["currentA"]},
            }
        )
    if module_levels["people"] != "normal":
        alerts.append(
            {
                "code": "people_overcrowded",
                "level": module_levels["people"],
                "message": f"人数偏高（{readings['peopleCount']} 人）",
                "metric": {"peopleCount": readings["peopleCount"], "capacity": capacity},
            }
        )

    return {
        "labId": lab_id,
        "labName": lab_name,
        "capacity": capacity,
        "collectedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "readings": readings,
        "statusByModule": module_levels,
        "level": _overall_level(module_levels.values()),
        "alerts": alerts,
    }


def _alarm_for_notify(alert):
    if not alert or str(alert.get("level") or "") != "alarm":
        return False
    return str(alert.get("code") or "") in {"temp_high", "smoke_detected", "voltage_fault"}


def _save_sensor_alarm_if_needed(lab_id, lab_name, alert):
    alarm_code = str(alert.get("code") or "").strip()
    if not alarm_code:
        return False

    latest = query(
        """
        SELECT id, created_at AS createdAt
        FROM lab_sensor_alarm
        WHERE lab_id=%s AND alarm_code=%s
        ORDER BY id DESC
        LIMIT 1
        """,
        (lab_id, alarm_code),
    )
    if latest:
        latest_at = _to_datetime((latest[0] or {}).get("createdAt"))
        if latest_at and (datetime.now() - latest_at).total_seconds() < _SENSOR_ALARM_COOLDOWN_SECONDS:
            return False

    message = str(alert.get("message") or "").strip()[:255]
    level = str(alert.get("level") or "alarm").strip() or "alarm"
    metric_json = json.dumps(alert.get("metric") or {}, ensure_ascii=False)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_id = execute_insert(
        """
        INSERT INTO lab_sensor_alarm (lab_id, lab_name, alarm_code, level, message, metric_json, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (lab_id, lab_name, alarm_code, level, message, metric_json, created_at),
    )
    audit_log(
        "admin.lab.sensor_alarm",
        target_type="lab",
        target_id=lab_id,
        detail={"alarmId": int(new_id or 0), "code": alarm_code, "level": level, "message": message},
    )
    return True


def _resolve_sensor_payload(lab_row, force=False):
    lab_id = int(lab_row.get("id") or 0)
    now = datetime.now()
    with _LAB_SENSOR_LOCK:
        cached = _LAB_SENSOR_CACHE.get(lab_id)
        if (
            not force
            and cached
            and (now - cached.get("updatedAt", now)).total_seconds() < _SENSOR_CACHE_TTL_SECONDS
            and cached.get("payload")
        ):
            payload = cached["payload"]
        else:
            payload = _build_sensor_payload(lab_row)
            _LAB_SENSOR_CACHE[lab_id] = {"updatedAt": now, "payload": payload}
    return payload

@app.get("/lostfound")
@auth_required()
def list_lost_found():
    status = request.args.get("status", "").strip()
    item_type = request.args.get("type", "").strip()
    owner = request.args.get("owner", "").strip()
    keyword = request.args.get("keyword", "").strip()
    student_id = request.args.get("studentId", "").strip()
    student_name = request.args.get("studentName", "").strip()
    student_class = request.args.get("studentClass", "").strip()
    claim_apply_status = request.args.get("claimApplyStatus", "").strip()
    claim_apply_user = request.args.get("claimApplyUser", "").strip()

    sql = """
        SELECT id, title, item_type AS type, description, location,
               contact, status, owner, created_at AS createdAt,
               image_url AS imageUrl,
               claim_student_id AS claimStudentId,
               claim_name AS claimName,
               claim_class AS claimClass,
               claim_apply_status AS claimApplyStatus,
               claim_apply_user AS claimApplyUser,
               claim_apply_reason AS claimApplyReason,
               claim_apply_student_id AS claimApplyStudentId,
               claim_apply_name AS claimApplyName,
               claim_apply_class AS claimApplyClass,
               claim_apply_at AS claimApplyAt,
               claim_reviewed_by AS claimReviewedBy,
               claim_reviewed_at AS claimReviewedAt,
               claim_review_note AS claimReviewNote
        FROM lost_found
        WHERE 1=1
    """
    params = []

    if status:
        sql += " AND status=%s"
        params.append(status)
    if item_type:
        sql += " AND item_type=%s"
        params.append(item_type)
    if owner:
        sql += " AND owner=%s"
        params.append(owner)
    if keyword:
        sql += """
            AND (
                title LIKE %s
                OR description LIKE %s
                OR location LIKE %s
                OR contact LIKE %s
                OR owner LIKE %s
                OR claim_student_id LIKE %s
                OR claim_name LIKE %s
                OR claim_class LIKE %s
                OR claim_apply_user LIKE %s
                OR claim_apply_student_id LIKE %s
                OR claim_apply_name LIKE %s
                OR claim_apply_class LIKE %s
            )
        """
        kw = f"%{keyword}%"
        params.extend([kw] * 12)
    if student_id:
        sql += " AND claim_student_id LIKE %s"
        params.append(f"%{student_id}%")
    if student_name:
        sql += " AND claim_name LIKE %s"
        params.append(f"%{student_name}%")
    if student_class:
        sql += " AND claim_class LIKE %s"
        params.append(f"%{student_class}%")
    if claim_apply_status:
        if claim_apply_status == "none":
            sql += " AND (claim_apply_status='' OR claim_apply_status IS NULL)"
        else:
            sql += " AND claim_apply_status=%s"
            params.append(claim_apply_status)
    if claim_apply_user:
        sql += " AND claim_apply_user=%s"
        params.append(claim_apply_user)

    sql += " ORDER BY id DESC"
    rows = query(sql, params)
    for row in rows:
        row["claimApplyAt"] = _to_text_time(row.get("claimApplyAt"))
        row["claimReviewedAt"] = _to_text_time(row.get("claimReviewedAt"))
    return jsonify(rows)


@app.post("/lostfound")
@auth_required()
def create_lost_found():
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    item_type = (data.get("type") or "").strip()  # lost/found
    description = (data.get("description") or "").strip()
    location = (data.get("location") or "").strip()
    contact = (data.get("contact") or "").strip()
    owner = (g.current_user.get("username") or "").strip()
    image_url = (data.get("imageUrl") or "").strip()

    if not title or item_type not in ("lost", "found"):
        return jsonify({"ok": False, "msg": "params error"}), 400

    created_at = datetime.now().isoformat(timespec="seconds")
    new_id = execute_insert(
        """
        INSERT INTO lost_found (title, item_type, description, location, contact, status, owner, created_at, image_url)
        VALUES (%s,%s,%s,%s,%s,'open',%s,%s,%s)
        """,
        (title, item_type, description, location, contact, owner, created_at, image_url),
    )
    return jsonify({"ok": True, "data": {"id": new_id}})


def _lostfound_ai_tokens(*parts):
    merged = " ".join([str(x or "").strip().lower() for x in parts if str(x or "").strip()])
    merged = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", " ", merged)
    tokens = []
    for part in merged.split():
        if not part:
            continue
        if re.search(r"[\u4e00-\u9fff]", part):
            if len(part) <= 4:
                tokens.append(part)
            for idx in range(max(0, len(part) - 1)):
                tokens.append(part[idx : idx + 2])
        else:
            if len(part) >= 2:
                tokens.append(part)
    dedup = []
    seen = set()
    for token in tokens:
        text = str(token or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        dedup.append(text)
        if len(dedup) >= 30:
            break
    return dedup


def _lostfound_ai_match_reason(source_row, candidate_row):
    source_tokens = set(_lostfound_ai_tokens(source_row.get("title"), source_row.get("description")))
    candidate_tokens = set(_lostfound_ai_tokens(candidate_row.get("title"), candidate_row.get("description")))
    overlap = sorted(list(source_tokens & candidate_tokens), key=lambda x: (-len(x), x))
    union_size = max(1, len(source_tokens | candidate_tokens))
    score = round(len(overlap) / float(union_size) * 100, 1)

    reasons = []
    source_location = str(source_row.get("location") or "").strip()
    candidate_location = str(candidate_row.get("location") or "").strip()
    if source_location and candidate_location:
        if source_location == candidate_location or source_location in candidate_location or candidate_location in source_location:
            score += 12
            reasons.append("地点信息相近")
    if overlap:
        reasons.append("共同关键词：" + "、".join(overlap[:3]))
    if source_row.get("imageUrl") and candidate_row.get("imageUrl"):
        score += 6
        reasons.append("双方都提供了图片线索")

    if str(source_row.get("title") or "").strip() and str(candidate_row.get("title") or "").strip():
        if str(source_row.get("title")).strip() in str(candidate_row.get("title")).strip() or str(candidate_row.get("title")).strip() in str(source_row.get("title")).strip():
            score += 10
            reasons.append("标题描述高度接近")

    score = max(0.0, min(99.0, score))
    return score, reasons[:3]


@app.post("/lostfound/ai-match")
@auth_required()
def lostfound_ai_match():
    payload = request.get_json(force=True) or {}
    item_id = _to_int_or_none(payload.get("itemId"))
    source_row = None

    if item_id:
        rows = query(
            """
            SELECT id, title, item_type AS type, description, location, image_url AS imageUrl, status
            FROM lost_found
            WHERE id=%s
            LIMIT 1
            """,
            (int(item_id),),
        )
        source_row = (rows or [None])[0]
        if not source_row:
            raise BizError("lostfound item not found", 404)
    else:
        source_type = str(payload.get("type") or "").strip().lower()
        if source_type not in {"lost", "found"}:
            raise BizError("type required", 400)
        source_row = {
            "id": 0,
            "title": str(payload.get("title") or "").strip(),
            "type": source_type,
            "description": str(payload.get("description") or "").strip(),
            "location": str(payload.get("location") or "").strip(),
            "imageUrl": str(payload.get("imageUrl") or "").strip(),
            "status": "open",
        }

    if not str(source_row.get("title") or "").strip() and not str(source_row.get("description") or "").strip() and not str(source_row.get("imageUrl") or "").strip():
        raise BizError("title or description or image required", 400)

    source_type = str(source_row.get("type") or "").strip().lower()
    target_type = "found" if source_type == "lost" else "lost"
    rows = query(
        """
        SELECT id, title, item_type AS type, description, location, contact, status, owner, created_at AS createdAt, image_url AS imageUrl
        FROM lost_found
        WHERE item_type=%s AND status='open'
        ORDER BY id DESC
        LIMIT 80
        """,
        (target_type,),
    )

    candidates = []
    for row in rows or []:
        if item_id and int(row.get("id") or 0) == int(item_id):
            continue
        score, reasons = _lostfound_ai_match_reason(source_row, row)
        if score < 18 and not reasons:
            continue
        candidates.append(
            {
                "id": int(row.get("id") or 0),
                "title": str(row.get("title") or "").strip(),
                "type": str(row.get("type") or "").strip(),
                "description": str(row.get("description") or "").strip(),
                "location": str(row.get("location") or "").strip(),
                "contact": str(row.get("contact") or "").strip(),
                "owner": str(row.get("owner") or "").strip(),
                "createdAt": _to_text_time(row.get("createdAt")),
                "imageUrl": str(row.get("imageUrl") or "").strip(),
                "matchScore": score,
                "reasons": reasons,
            }
        )

    candidates.sort(key=lambda item: (-float(item.get("matchScore") or 0), -int(item.get("id") or 0)))
    summary = (
        f"已为{ '失物' if source_type == 'lost' else '拾到物品' }匹配 {len(candidates[:8])} 条候选记录。"
        if candidates
        else "未找到高相似候选，建议补充更明确的颜色、品牌、时间地点或上传图片后再试。"
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "sourceType": source_type,
                "targetType": target_type,
                "summary": summary,
                "candidates": candidates[:8],
            },
        }
    )


@app.post("/lostfound/<int:lid>/delete")
@auth_required()
def delete_lost_found(lid):
    current_user = g.current_user or {}
    operator = (current_user.get("username") or "").strip()
    role = (current_user.get("role") or "").strip()
    if not operator:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401

    try:
        def _tx(cur):
            cur.execute(
                """
                SELECT id, owner, title, item_type AS type, status
                FROM lost_found
                WHERE id=%s
                LIMIT 1
                FOR UPDATE
                """,
                (lid,),
            )
            row = cur.fetchone()
            if not row:
                raise BizError("not found", 404)

            owner = str(row.get("owner") or "").strip()
            is_admin = role == "admin"
            if not is_admin and owner != operator:
                raise BizError("forbidden", 403)

            cur.execute("DELETE FROM lost_found WHERE id=%s", (lid,))
            if int(cur.rowcount or 0) != 1:
                raise BizError("not found", 404)
            return {
                "title": row.get("title") or "",
                "type": row.get("type") or "",
                "status": row.get("status") or "",
                "owner": owner,
            }

        deleted = run_in_transaction(_tx)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    audit_log(
        "lostfound.delete",
        target_type="lostfound",
        target_id=lid,
        detail={
            "title": deleted.get("title") or "",
            "type": deleted.get("type") or "",
            "status": deleted.get("status") or "",
            "owner": deleted.get("owner") or "",
        },
    )
    return jsonify({"ok": True})


@app.post("/lostfound/<int:lid>/claim-apply")
@auth_required()
def apply_lost_found_claim(lid):
    data = request.get_json(force=True) or {}
    applicant = (g.current_user.get("username") or "").strip()
    claim_student_id = (data.get("claimStudentId") or "").strip()
    claim_name = (data.get("claimName") or "").strip()
    claim_class = (data.get("claimClass") or "").strip()
    claim_reason = (data.get("claimReason") or "").strip()
    if not applicant:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401
    if not claim_student_id or not claim_name or not claim_class:
        return jsonify({"ok": False, "msg": "claim info required"}), 400

    try:
        def _tx(cur):
            cur.execute(
                """
                SELECT id, title, item_type AS type, status, owner,
                       claim_apply_status AS claimApplyStatus,
                       claim_apply_user AS claimApplyUser
                FROM lost_found
                WHERE id=%s
                LIMIT 1
                FOR UPDATE
                """,
                (lid,),
            )
            row = cur.fetchone()
            if not row:
                raise BizError("not found", 404)
            if row["type"] != "found":
                raise BizError("only found item can be claimed", 400)
            if row["status"] != "open":
                raise BizError("item already closed", 409)
            if (row.get("owner") or "").strip() == applicant:
                raise BizError("owner cannot claim own item", 403)
            if row.get("claimApplyStatus") == "approved":
                raise BizError("claim already approved", 409)
            pending_user = (row.get("claimApplyUser") or "").strip()
            if row.get("claimApplyStatus") == "pending" and pending_user and pending_user != applicant:
                raise BizError("another claim is pending", 409)

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                """
                UPDATE lost_found
                SET claim_apply_status='pending',
                    claim_apply_user=%s,
                    claim_apply_reason=%s,
                    claim_apply_student_id=%s,
                    claim_apply_name=%s,
                    claim_apply_class=%s,
                    claim_apply_at=%s,
                    claim_reviewed_by='',
                    claim_reviewed_at=NULL,
                    claim_review_note=''
                WHERE id=%s
                """,
                (applicant, claim_reason, claim_student_id, claim_name, claim_class, now, lid),
            )
            return {"title": row.get("title") or "", "owner": row.get("owner") or ""}

        result = run_in_transaction(_tx)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    audit_log(
        "user.lostfound.claim_apply",
        target_type="lostfound",
        target_id=lid,
        detail={
            "claimUser": applicant,
            "claimStudentId": claim_student_id,
            "claimName": claim_name,
            "claimClass": claim_class,
            "claimReason": claim_reason,
        },
    )
    return jsonify({"ok": True, "data": result})


@app.post("/lostfound/<int:lid>/claim-review")
@auth_required(roles=["admin"])
def review_lost_found_claim(lid):
    data = request.get_json(force=True) or {}
    action = (data.get("action") or "").strip()  # approve/reject
    note = (data.get("note") or "").strip()
    reviewer = (g.current_user.get("username") or "").strip()
    if action not in ("approve", "reject"):
        return jsonify({"ok": False, "msg": "invalid action"}), 400

    try:
        def _tx(cur):
            cur.execute(
                """
                SELECT id, title, item_type AS type, status,
                       claim_apply_status AS claimApplyStatus,
                       claim_apply_user AS claimApplyUser,
                       claim_apply_student_id AS claimApplyStudentId,
                       claim_apply_name AS claimApplyName,
                       claim_apply_class AS claimApplyClass
                FROM lost_found
                WHERE id=%s
                LIMIT 1
                FOR UPDATE
                """,
                (lid,),
            )
            row = cur.fetchone()
            if not row:
                raise BizError("not found", 404)
            if row["type"] != "found":
                raise BizError("only found item has claim review", 400)
            if row.get("claimApplyStatus") != "pending":
                raise BizError("no pending claim", 409)

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if action == "approve":
                if not row.get("claimApplyStudentId") or not row.get("claimApplyName") or not row.get("claimApplyClass"):
                    raise BizError("claim info required", 400)
                cur.execute(
                    """
                    UPDATE lost_found
                    SET status='closed',
                        claim_student_id=claim_apply_student_id,
                        claim_name=claim_apply_name,
                        claim_class=claim_apply_class,
                        claim_apply_status='approved',
                        claim_reviewed_by=%s,
                        claim_reviewed_at=%s,
                        claim_review_note=%s,
                        created_at=%s
                    WHERE id=%s
                    """,
                    (reviewer, now, note, now, lid),
                )
            else:
                cur.execute(
                    """
                    UPDATE lost_found
                    SET claim_apply_status='rejected',
                        claim_reviewed_by=%s,
                        claim_reviewed_at=%s,
                        claim_review_note=%s
                    WHERE id=%s
                    """,
                    (reviewer, now, note, lid),
                )
            return {
                "title": row.get("title") or "",
                "claimUser": row.get("claimApplyUser") or "",
            }

        result = run_in_transaction(_tx)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    audit_log(
        "admin.lostfound.claim_review",
        target_type="lostfound",
        target_id=lid,
        detail={"action": action, "note": note},
    )
    return jsonify({"ok": True, "data": result})


@app.post("/lostfound/<int:lid>/status")
@auth_required(roles=["admin"])
def update_lost_found_status(lid):
    data = request.get_json(force=True) or {}
    status = (data.get("status") or "").strip()  # open/closed
    claim_student_id = (data.get("claimStudentId") or "").strip()
    claim_name = (data.get("claimName") or "").strip()
    claim_class = (data.get("claimClass") or "").strip()

    if status not in ("open", "closed"):
        return jsonify({"ok": False, "msg": "invalid status"}), 400
    if status == "closed" and (not claim_student_id or not claim_name or not claim_class):
        return jsonify({"ok": False, "msg": "claim info required"}), 400

    row = query("SELECT id FROM lost_found WHERE id=%s LIMIT 1", (lid,))
    if not row:
        return jsonify({"ok": False, "msg": "not found"}), 404

    status_time = datetime.now().isoformat(timespec="seconds")
    execute(
        """
        UPDATE lost_found
        SET status=%s,
            claim_student_id=%s,
            claim_name=%s,
            claim_class=%s,
            claim_apply_status=CASE WHEN %s='open' THEN '' ELSE claim_apply_status END,
            claim_apply_user=CASE WHEN %s='open' THEN '' ELSE claim_apply_user END,
            claim_apply_reason=CASE WHEN %s='open' THEN '' ELSE claim_apply_reason END,
            claim_apply_student_id=CASE WHEN %s='open' THEN '' ELSE claim_apply_student_id END,
            claim_apply_name=CASE WHEN %s='open' THEN '' ELSE claim_apply_name END,
            claim_apply_class=CASE WHEN %s='open' THEN '' ELSE claim_apply_class END,
            claim_apply_at=CASE WHEN %s='open' THEN NULL ELSE claim_apply_at END,
            claim_reviewed_by=CASE WHEN %s='open' THEN '' ELSE claim_reviewed_by END,
            claim_reviewed_at=CASE WHEN %s='open' THEN NULL ELSE claim_reviewed_at END,
            claim_review_note=CASE WHEN %s='open' THEN '' ELSE claim_review_note END,
            created_at=CASE WHEN %s='closed' THEN %s ELSE created_at END
        WHERE id=%s
        """,
        (
            status,
            claim_student_id,
            claim_name,
            claim_class,
            status,
            status,
            status,
            status,
            status,
            status,
            status,
            status,
            status,
            status,
            status,
            status_time,
            lid,
        ),
    )
    audit_log(
        "admin.lostfound.status",
        target_type="lostfound",
        target_id=lid,
        detail={
            "status": status,
            "claimStudentId": claim_student_id,
            "claimName": claim_name,
            "claimClass": claim_class,
        },
    )
    return jsonify({"ok": True})


@app.post("/upload")
@auth_required()
def upload():
    if "file" not in request.files:
        return jsonify({"ok": False, "msg": "file required"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"ok": False, "msg": "filename required"}), 400

    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        return jsonify({"ok": False, "msg": "invalid file type"}), 400

    name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, name)
    f.save(path)
    return jsonify({"ok": True, "data": {"url": f"/uploads/{name}"}})


@app.get("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.get("/labs")
@auth_required()
def get_labs():
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        rows = query(
            """
            SELECT id, name, status, capacity,
                   device_count AS deviceCount,
                   description, image_url AS imageUrl
            FROM lab
            ORDER BY id DESC
            """
        )
        return jsonify({"ok": True, "data": rows, "meta": {"keyword": "", "count": len(rows)}})

    rows = query(
        """
        SELECT id, name, status, capacity,
               device_count AS deviceCount,
               description, image_url AS imageUrl
        FROM lab
        WHERE name LIKE %s
        ORDER BY id DESC
        """,
        (f"%{keyword}%",),
    )
    return jsonify({"ok": True, "data": rows, "meta": {"keyword": keyword, "count": len(rows)}})


@app.get("/labs/sensor-status")
@auth_required(roles=["admin"])
def get_lab_sensor_status():
    lab_id_raw = request.args.get("labId", "").strip()
    force_raw = request.args.get("force", "").strip().lower()
    force_refresh = force_raw in ("1", "true", "yes", "on")
    lab_id = _to_int_or_none(lab_id_raw)
    if lab_id_raw and lab_id is None:
        return jsonify({"ok": False, "msg": "invalid labId"}), 400

    if lab_id:
        labs = query("SELECT id, name, capacity FROM lab WHERE id=%s LIMIT 1", (lab_id,))
        if not labs:
            return jsonify({"ok": False, "msg": "lab not found"}), 404
    else:
        labs = query("SELECT id, name, capacity FROM lab ORDER BY id ASC")

    rows = []
    inserted_count = 0
    for lab in labs:
        payload = _resolve_sensor_payload(lab, force=force_refresh)
        rows.append(payload)
        for alert in payload.get("alerts") or []:
            if not _alarm_for_notify(alert):
                continue
            if _save_sensor_alarm_if_needed(payload["labId"], payload["labName"], alert):
                inserted_count += 1

    if lab_id:
        return jsonify({"ok": True, "data": rows[0], "meta": {"insertedAlarms": inserted_count}})
    return jsonify({"ok": True, "data": rows, "meta": {"insertedAlarms": inserted_count}})


@app.post("/labs/<int:lid>")
@auth_required(roles=["admin"], permissions=[PERMISSION_SCHEDULE_MANAGER, PERMISSION_ASSET_MANAGER])
def update_lab(lid):
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    status = (data.get("status") or "").strip()
    description = (data.get("description") or "").strip()
    image_url = (data.get("imageUrl") or "").strip()
    capacity_raw = _to_int_or_none(data.get("capacity"))
    device_count_raw = _to_int_or_none(data.get("deviceCount"))

    if not name:
        return jsonify({"ok": False, "msg": "name required"}), 400
    if status not in ("free", "busy"):
        return jsonify({"ok": False, "msg": "invalid status"}), 400
    if data.get("capacity") not in (None, "") and capacity_raw is None:
        return jsonify({"ok": False, "msg": "invalid capacity"}), 400
    if data.get("deviceCount") not in (None, "") and device_count_raw is None:
        return jsonify({"ok": False, "msg": "invalid deviceCount"}), 400

    capacity = max(0, int(capacity_raw or 0))
    device_count = max(0, int(device_count_raw or 0))

    row = query("SELECT id FROM lab WHERE id=%s LIMIT 1", (lid,))
    if not row:
        return jsonify({"ok": False, "msg": "lab not found"}), 404

    execute(
        """
        UPDATE lab
        SET name=%s, status=%s, capacity=%s, device_count=%s, description=%s, image_url=%s
        WHERE id=%s
        """,
        (name, status, capacity, device_count, description, image_url, lid),
    )
    audit_log(
        "admin.lab.update",
        target_type="lab",
        target_id=lid,
        detail={
            "name": name,
            "status": status,
            "capacity": capacity,
            "deviceCount": device_count,
            "description": description,
            "imageUrl": image_url,
        },
    )
    return jsonify({"ok": True})


@app.post("/labs")
@auth_required(roles=["admin"], permissions=[PERMISSION_SCHEDULE_MANAGER, PERMISSION_ASSET_MANAGER])
def create_lab():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    status = (data.get("status") or "free").strip()
    description = (data.get("description") or "").strip()
    image_url = (data.get("imageUrl") or "").strip()
    capacity = _to_int_or_none(data.get("capacity"))
    device_count = _to_int_or_none(data.get("deviceCount"))

    if not name:
        return jsonify({"ok": False, "msg": "name required"}), 400
    if status not in ("free", "busy"):
        return jsonify({"ok": False, "msg": "invalid status"}), 400
    if data.get("capacity") not in (None, "") and capacity is None:
        return jsonify({"ok": False, "msg": "invalid capacity"}), 400
    if data.get("deviceCount") not in (None, "") and device_count is None:
        return jsonify({"ok": False, "msg": "invalid deviceCount"}), 400

    capacity = max(0, int(capacity or 0))
    device_count = max(0, int(device_count or 0))

    dup = query("SELECT id FROM lab WHERE name=%s LIMIT 1", (name,))
    if dup:
        return jsonify({"ok": False, "msg": "lab name exists"}), 409

    new_id = execute_insert(
        """
        INSERT INTO lab (name, status, capacity, device_count, description, image_url)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (name, status, capacity, device_count, description, image_url),
    )
    audit_log(
        "admin.lab.create",
        target_type="lab",
        target_id=new_id,
        detail={
            "name": name,
            "status": status,
            "capacity": capacity,
            "deviceCount": device_count,
            "description": description,
            "imageUrl": image_url,
        },
    )
    return jsonify({"ok": True, "data": {"id": new_id}})


@app.post("/labs/<int:lid>/delete")
@auth_required(roles=["admin"], permissions=[PERMISSION_SCHEDULE_MANAGER, PERMISSION_ASSET_MANAGER])
def delete_lab(lid):
    row = query("SELECT id, name FROM lab WHERE id=%s LIMIT 1", (lid,))
    if not row:
        return jsonify({"ok": False, "msg": "lab not found"}), 404
    lab_name = row[0]["name"]

    ref = query(
        """
        SELECT COUNT(*) AS cnt
        FROM reservation
        WHERE lab_id=%s OR lab_name=%s
        """,
        (lid, lab_name),
    )
    ref_count = int((ref[0] or {}).get("cnt") or 0) if ref else 0
    if ref_count > 0:
        return jsonify({"ok": False, "msg": "lab has reservation history, cannot delete"}), 409

    execute("DELETE FROM lab WHERE id=%s", (lid,))
    audit_log(
        "admin.lab.delete",
        target_type="lab",
        target_id=lid,
        detail={"name": lab_name},
    )
    return jsonify({"ok": True})


def create_reservation_internal(user_name, date, time_range, reason="", lab_id=None, lab_name=""):
    user = str(user_name or "").strip()
    date_text = str(date or "").strip()
    time_text = str(time_range or "").strip()
    reason_text = str(reason or "").strip()
    lab_id_val = _to_int_or_none(lab_id)
    lab_name_val = str(lab_name or "").strip()

    if not user:
        raise BizError("user required", 400)
    if not date_text or not time_text:
        raise BizError("params error", 400)

    if lab_id_val:
        lab_rows = query("SELECT id, name FROM lab WHERE id=%s LIMIT 1", (lab_id_val,))
    elif lab_name_val:
        lab_rows = query("SELECT id, name FROM lab WHERE name=%s LIMIT 1", (lab_name_val,))
    else:
        raise BizError("lab required", 400)

    if not lab_rows:
        raise BizError("lab not found", 404)

    resolved_lab_id = int(lab_rows[0]["id"])
    resolved_lab_name = str(lab_rows[0]["name"] or "").strip()
    if not resolved_lab_name:
        raise BizError("lab not found", 404)

    schedule_error = validate_reservation_schedule(
        date_text,
        time_text,
        lab_id=resolved_lab_id,
        lab_name=resolved_lab_name,
    )
    if schedule_error:
        raise BizError(schedule_error, 400)

    review_decision = resolve_reservation_review_policy(
        lab_id=resolved_lab_id,
        lab_name=resolved_lab_name,
        date_text=date_text,
        time_range=time_text,
    )
    init_status = str(review_decision.get("status") or "pending").strip() or "pending"
    review_role = str(review_decision.get("reviewRole") or "").strip().lower()
    review_policy = str(review_decision.get("reviewPolicy") or "").strip().lower()

    created_at = datetime.now().isoformat(timespec="seconds")

    def _tx(cur):
        lock_key = _reservation_lock_key(resolved_lab_name, date_text)
        if not _acquire_named_lock(cur, lock_key):
            raise BizError("reservation busy, try again", 409)
        try:
            if has_approved_conflict_with_cur(cur, resolved_lab_name, date_text, time_text):
                raise BizError("reservation conflict with approved", 409)
            cur.execute(
                """
                INSERT INTO reservation (
                    lab_id, lab_name, user_name, date, time, reason, status, reject_reason, created_at, review_role, review_policy
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,'',%s,%s,%s)
                """,
                (
                    resolved_lab_id,
                    resolved_lab_name,
                    user,
                    date_text,
                    time_text,
                    reason_text,
                    init_status,
                    created_at,
                    review_role,
                    review_policy,
                ),
            )
            return cur.lastrowid
        finally:
            _release_named_lock(cur, lock_key)

    try:
        new_id = run_in_transaction(_tx)
    except BizError as e:
        msg_text = str(e.msg or "").strip().lower()
        if int(e.status or 0) == 409 and "conflict" in msg_text:
            plans = []
            try:
                plans = build_reservation_plans(
                    user_name=user,
                    lab_id_or_name=resolved_lab_id,
                    preferred_date=date_text,
                    preferred_time=time_text,
                    days=7,
                    k=3,
                )
            except Exception:
                plans = []
            if plans:
                reply = _agent_build_plan_options_text(plans, prefix="该时段冲突，我给你3个可选方案：")
                err = BizError("conflict", 409)
                err.data = {"reply": reply, "plans": plans}
                audit_log(
                    "reservation.plan.generated",
                    target_type="reservation_plan",
                    detail={
                        "labId": resolved_lab_id,
                        "labName": resolved_lab_name,
                        "preferredDate": date_text,
                        "preferredTime": time_text,
                        "planCount": len(plans),
                    },
                    actor={"username": user},
                )
                raise err
        raise
    return {
        "id": int(new_id),
        "labId": resolved_lab_id,
        "labName": resolved_lab_name,
        "date": date_text,
        "time": time_text,
        "reason": reason_text,
        "status": init_status,
        "reviewRole": review_role,
        "reviewPolicy": review_policy,
        "approvalRequired": bool(review_decision.get("approvalRequired")),
    }


