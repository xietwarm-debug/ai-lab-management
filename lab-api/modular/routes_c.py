from . import core as _core

for _k, _v in _core.__dict__.items():
    if _k.startswith("__"):
        continue
    globals()[_k] = _v

del _k, _v, _core


def _get_active_reservation_priority_rule():
    rows = query(
        """
        SELECT id,
               status,
               teacher_weight AS teacherWeight,
               student_weight AS studentWeight,
               admin_weight AS adminWeight,
               teaching_weight AS teachingWeight,
               research_weight AS researchWeight,
               default_weight AS defaultWeight,
               violation_penalty AS violationPenalty,
               wait_hour_bonus AS waitHourBonus,
               wait_hour_bonus_cap AS waitHourBonusCap,
               updated_by AS updatedBy,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM reservation_priority_rule
        WHERE status='active'
        ORDER BY id DESC
        LIMIT 1
        """
    )
    return rows[0] if rows else {
        "teacherWeight": 30,
        "studentWeight": 10,
        "adminWeight": 20,
        "teachingWeight": 25,
        "researchWeight": 15,
        "defaultWeight": 5,
        "violationPenalty": 15,
        "waitHourBonus": 1.0,
        "waitHourBonusCap": 48,
    }


def _serialize_reservation_priority_rule(row):
    item = row or {}
    return {
        "id": int(item.get("id") or 0),
        "teacherWeight": int(item.get("teacherWeight") or 30),
        "studentWeight": int(item.get("studentWeight") or 10),
        "adminWeight": int(item.get("adminWeight") or 20),
        "teachingWeight": int(item.get("teachingWeight") or 25),
        "researchWeight": int(item.get("researchWeight") or 15),
        "defaultWeight": int(item.get("defaultWeight") or 5),
        "violationPenalty": int(item.get("violationPenalty") or 15),
        "waitHourBonus": float(item.get("waitHourBonus") or 1.0),
        "waitHourBonusCap": int(item.get("waitHourBonusCap") or 48),
        "updatedBy": str(item.get("updatedBy") or "").strip(),
        "createdAt": _to_text_time(item.get("createdAt")),
        "updatedAt": _to_text_time(item.get("updatedAt")),
    }


def _normalize_reservation_priority_rule_payload(payload):
    rule = _serialize_reservation_priority_rule(payload or {})
    normalized = {}
    for key in ("teacherWeight", "studentWeight", "adminWeight", "teachingWeight", "researchWeight", "defaultWeight", "violationPenalty", "waitHourBonusCap"):
        val = _to_int_or_none((payload or {}).get(key))
        if val is None:
            normalized[key] = rule[key]
        else:
            normalized[key] = max(0, min(int(val), 999))
    try:
        wait_hour_bonus = float((payload or {}).get("waitHourBonus"))
    except (TypeError, ValueError):
        wait_hour_bonus = rule["waitHourBonus"]
    normalized["waitHourBonus"] = max(0.0, min(wait_hour_bonus, 20.0))
    return normalized


def _reservation_priority_reason_tag(reason):
    text = str(reason or "").strip().lower()
    if any(x in text for x in ["教学", "课程", "上课", "实验课", "class", "teach"]):
        return "teaching"
    if any(x in text for x in ["科研", "研究", "项目", "research"]):
        return "research"
    return "default"


def _build_reservation_waitlist_priority(user_name, user_role="", reason="", created_at=None, rule=None):
    rule = _serialize_reservation_priority_rule(rule or _get_active_reservation_priority_rule())
    role = str(user_role or "").strip().lower()
    if not role:
        profile = get_user_profile_row_by_username(user_name) or {}
        role = str(profile.get("role") or "").strip().lower()
    role_score = int(rule.get("studentWeight") or 10)
    if role == "teacher":
        role_score = int(rule.get("teacherWeight") or 30)
    elif role == "admin":
        role_score = int(rule.get("adminWeight") or 20)
    reason_tag = _reservation_priority_reason_tag(reason)
    purpose_score = int(rule.get("defaultWeight") or 5)
    if reason_tag == "teaching":
        purpose_score = int(rule.get("teachingWeight") or 25)
    elif reason_tag == "research":
        purpose_score = int(rule.get("researchWeight") or 15)
    violation_count = int(_reservation_user_violation_count(user_name) or 0)
    wait_bonus = 0.0
    created_dt = _to_datetime(created_at)
    if created_dt != datetime.min:
        waited_hours = max(0.0, (datetime.now() - created_dt).total_seconds() / 3600.0)
        waited_hours = min(waited_hours, float(rule.get("waitHourBonusCap") or 48))
        wait_bonus = round(waited_hours * float(rule.get("waitHourBonus") or 1.0), 2)
    score = round(float(role_score + purpose_score + wait_bonus - (violation_count * int(rule.get("violationPenalty") or 15))), 2)
    return {
        "score": score,
        "breakdown": {
            "role": role,
            "roleScore": role_score,
            "reasonTag": reason_tag,
            "purposeScore": purpose_score,
            "violationCount": violation_count,
            "violationPenalty": int(rule.get("violationPenalty") or 15),
            "waitBonus": wait_bonus,
        },
    }


def _try_promote_waitlist(lab_id, lab_name, date_text, time_text, actor=None):
    safe_lab_name = str(lab_name or "").strip()
    if not safe_lab_name or not date_text or not time_text:
        return None
    rows = query(
        """
        SELECT id,
               lab_id AS labId,
               lab_name AS labName,
               user_name AS userName,
               user_role AS userRole,
               reason,
               created_at AS createdAt
        FROM reservation_waitlist
        WHERE status='waiting'
          AND lab_name=%s
          AND date=%s
          AND time=%s
        ORDER BY priority_score DESC, id ASC
        LIMIT 1
        """,
        (safe_lab_name, date_text, time_text),
    )
    if not rows:
        return None
    candidate = rows[0] or {}
    try:
        from . import routes_b as _routes_b

        created = _routes_b.create_reservation_internal(
            user_name=str(candidate.get("userName") or "").strip(),
            lab_name=safe_lab_name,
            date=date_text,
            time_range=time_text,
            reason=str(candidate.get("reason") or "").strip(),
        )
    except BizError:
        return None

    execute(
        """
        UPDATE reservation_waitlist
        SET status='promoted',
            promoted_reservation_id=%s,
            promoted_at=%s,
            updated_at=%s
        WHERE id=%s
        """,
        (int(created.get("id") or 0), _to_text_time(datetime.now()), _to_text_time(datetime.now()), int(candidate.get("id") or 0)),
    )
    audit_log(
        "reservation.waitlist.promote",
        target_type="reservation_waitlist",
        target_id=candidate.get("id"),
        detail={"reservationId": created.get("id"), "labName": safe_lab_name, "date": date_text, "time": time_text},
        actor=actor,
    )
    return {"waitlistId": int(candidate.get("id") or 0), "reservationId": int(created.get("id") or 0)}

@app.post("/reservations")
@auth_required()
def create_reservation():
    data = request.get_json(force=True) or {}

    required = ["labName", "date", "time"]
    missing = [k for k in required if not str(data.get(k, "")).strip()]
    if missing:
        return jsonify({"ok": False, "msg": f"missing: {', '.join(missing)}"}), 400

    lab_name = data["labName"].strip()
    user_name = (g.current_user.get("username") or "").strip()
    date = data["date"].strip()
    time_range = data["time"].strip()
    reason = (data.get("reason") or "").strip()
    try:
        # create_reservation_internal is defined in routes_b after module split.
        from . import routes_b as _routes_b

        created = _routes_b.create_reservation_internal(
            user_name=user_name,
            lab_name=lab_name,
            date=date,
            time_range=time_range,
            reason=reason,
        )
    except BizError as e:
        conflict_data = getattr(e, "data", None)
        if int(e.status or 0) == 409 and isinstance(conflict_data, dict) and isinstance(conflict_data.get("plans"), list):
            plans = _agent_normalize_plan_items(conflict_data.get("plans"))
            reply = str(conflict_data.get("reply") or "").strip() or _agent_build_plan_options_text(plans)
            return jsonify({"code": 409, "msg": "conflict", "data": {"reply": reply, "plans": plans, "waitlistRecommended": True, "waitlistSlot": {"labName": lab_name, "date": date, "time": time_range, "reason": reason}}}), 409
        return jsonify({"ok": False, "msg": e.msg}), e.status

    return jsonify(
        {
            "ok": True,
            "data": {
                "id": created["id"],
                "status": created.get("status") or "pending",
                "approvalRequired": bool(created.get("approvalRequired")),
                "reviewRole": created.get("reviewRole") or "",
                "reviewPolicy": created.get("reviewPolicy") or "",
            },
        }
    )


@app.post("/reservations/<int:rid>/cancel")
@auth_required()
def cancel_reservation(rid):
    user = (g.current_user.get("username") or "").strip()
    if not user:
        return jsonify({"ok": False, "msg": "user required"}), 400

    row = query("SELECT id, user_name AS user, status, lab_id AS labId, lab_name AS labName, date, time FROM reservation WHERE id=%s LIMIT 1", (rid,))
    if not row:
        return jsonify({"ok": False, "msg": "reservation not found"}), 404
    if row[0]["user"] != user:
        return jsonify({"ok": False, "msg": "forbidden"}), 403

    if row[0]["status"] in ("rejected", "cancelled"):
        return jsonify({"ok": True})

    execute("UPDATE reservation SET status='cancelled' WHERE id=%s", (rid,))
    if str(row[0].get("status") or "").strip() == "approved":
        _try_promote_waitlist(row[0].get("labId"), row[0].get("labName"), row[0].get("date"), row[0].get("time"), actor={"id": g.current_user.get("id"), "username": user, "role": g.current_user.get("role")})
    return jsonify({"ok": True})


@app.post("/reservations/<int:rid>/delete")
@auth_required()
def delete_reservation_record(rid):
    user = (g.current_user.get("username") or "").strip()
    if not user:
        return jsonify({"ok": False, "msg": "user required"}), 400

    try:
        def _tx(cur):
            cur.execute(
                """
                SELECT id, user_name AS user, status
                FROM reservation
                WHERE id=%s
                LIMIT 1
                FOR UPDATE
                """,
                (rid,),
            )
            row = cur.fetchone()
            if not row:
                raise BizError("reservation not found", 404)
            if str(row.get("user") or "").strip() != user:
                raise BizError("forbidden", 403)
            status = str(row.get("status") or "").strip()
            if status in ("pending", "approved"):
                raise BizError("active reservation cannot be deleted, cancel it first", 409)

            cur.execute("DELETE FROM reservation WHERE id=%s", (rid,))
            if int(cur.rowcount or 0) != 1:
                raise BizError("reservation not found", 404)
            return status

        old_status = str(run_in_transaction(_tx) or "")
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    audit_log(
        "user.reservation.delete",
        target_type="reservation",
        target_id=rid,
        detail={"status": old_status},
    )
    return jsonify({"ok": True})


@app.post("/reservations/<int:rid>/reschedule")
@auth_required()
def reschedule_reservation(rid):
    data = request.get_json(force=True) or {}
    user = (g.current_user.get("username") or "").strip()
    date = (data.get("date") or "").strip()
    time_range = (data.get("time") or "").strip()
    if not user or not date or not time_range:
        return jsonify({"ok": False, "msg": "params error"}), 400

    try:
        updated = _reschedule_reservation_internal(
            rid=rid,
            date=date,
            time_range=time_range,
            operator_user=user,
            is_admin=False,
        )
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    return jsonify(
        {
            "ok": True,
            "data": {
                "id": int(updated.get("id") or 0),
                "status": str(updated.get("status") or ""),
                "reviewRole": str(updated.get("reviewRole") or ""),
                "reviewPolicy": str(updated.get("reviewPolicy") or ""),
            },
        }
    )


@app.post("/reservations/<int:rid>/admin-cancel")
@auth_required(roles=["admin"])
def admin_cancel_reservation(rid):
    row = query("SELECT id, status, lab_id AS labId, lab_name AS labName, date, time FROM reservation WHERE id=%s LIMIT 1", (rid,))
    if not row:
        return jsonify({"ok": False, "msg": "reservation not found"}), 404

    execute("UPDATE reservation SET status='cancelled' WHERE id=%s", (rid,))
    audit_log("admin.reservation.cancel", target_type="reservation", target_id=rid)
    if str(row[0].get("status") or "").strip() == "approved":
        _try_promote_waitlist(row[0].get("labId"), row[0].get("labName"), row[0].get("date"), row[0].get("time"), actor={"id": g.current_user.get("id"), "username": g.current_user.get("username"), "role": g.current_user.get("role")})
    return jsonify({"ok": True})


@app.post("/reservations/<int:rid>/admin-reschedule")
@auth_required(roles=["admin"])
def admin_reschedule_reservation(rid):
    data = request.get_json(force=True) or {}
    date = (data.get("date") or "").strip()
    time_range = (data.get("time") or "").strip()
    if not date or not time_range:
        return jsonify({"ok": False, "msg": "params error"}), 400

    try:
        updated = _reschedule_reservation_internal(
            rid=rid,
            date=date,
            time_range=time_range,
            operator_user=(g.current_user.get("username") or "").strip(),
            is_admin=True,
        )
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    audit_log(
        "admin.reservation.reschedule",
        target_type="reservation",
        target_id=rid,
        detail={"date": date, "time": time_range, "status": updated.get("status"), "reviewRole": updated.get("reviewRole")},
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "id": int(updated.get("id") or 0),
                "status": str(updated.get("status") or ""),
                "reviewRole": str(updated.get("reviewRole") or ""),
                "reviewPolicy": str(updated.get("reviewPolicy") or ""),
            },
        }
    )


@app.post("/reservations/batch")
@auth_required(roles=["admin", "teacher"])
def batch_reservations():
    data = request.get_json(force=True) or {}
    action = (data.get("action") or "").strip()  # approve/cancel
    ids = data.get("ids") or []
    actor_role = str((g.current_user or {}).get("role") or "").strip().lower()
    if action not in ("approve", "cancel") or not isinstance(ids, list):
        return jsonify({"ok": False, "msg": "params error"}), 400

    clean_ids = []
    for rid in ids:
        try:
            n = int(rid)
        except (TypeError, ValueError):
            continue
        if n > 0:
            clean_ids.append(n)

    if not clean_ids:
        return jsonify({"ok": True, "data": {"count": 0}})

    if action == "cancel" and actor_role != "admin":
        return jsonify({"ok": False, "msg": "forbidden"}), 403

    if action == "approve":
        approved_ids = []
        conflict_ids = []
        invalid_status_ids = []
        invalid_schedule_ids = []
        not_found_ids = []
        busy_ids = []
        forbidden_ids = []

        def _tx(cur):
            for rid in clean_ids:
                cur.execute(
                    """
                    SELECT id, lab_id AS labId, lab_name AS labName, date, time, status, review_role AS reviewRole
                    FROM reservation
                    WHERE id=%s
                    LIMIT 1
                    FOR UPDATE
                    """,
                    (rid,),
                )
                row = cur.fetchone()
                if not row:
                    not_found_ids.append(rid)
                    continue
                if row["status"] != "pending":
                    invalid_status_ids.append(rid)
                    continue
                if not can_review_reservation(actor_role, row.get("reviewRole")):
                    forbidden_ids.append(rid)
                    continue

                schedule_error = validate_reservation_schedule(
                    row["date"],
                    row["time"],
                    lab_id=_to_int_or_none(row.get("labId")),
                    lab_name=row.get("labName"),
                )
                if schedule_error:
                    invalid_schedule_ids.append(rid)
                    continue

                lock_key = _reservation_lock_key(row["labName"], row["date"])
                if not _acquire_named_lock(cur, lock_key):
                    busy_ids.append(rid)
                    continue
                try:
                    if has_approved_conflict_with_cur(cur, row["labName"], row["date"], row["time"], exclude_id=rid):
                        conflict_ids.append(rid)
                        continue
                    cur.execute(
                        """
                        UPDATE reservation
                        SET status='approved', reject_reason=''
                        WHERE id=%s AND status='pending'
                        """,
                        (rid,),
                    )
                    if cur.rowcount == 1:
                        approved_ids.append(rid)
                    else:
                        invalid_status_ids.append(rid)
                finally:
                    _release_named_lock(cur, lock_key)

        run_in_transaction(_tx)

        audit_log(
            "admin.reservation.batch_approve",
            target_type="reservation",
            detail={
                "requested": _compact_ids(clean_ids),
                "approved": _compact_ids(approved_ids),
                "conflict": _compact_ids(conflict_ids),
                "invalidStatus": _compact_ids(invalid_status_ids),
                "invalidSchedule": _compact_ids(invalid_schedule_ids),
                "notFound": _compact_ids(not_found_ids),
                "busy": _compact_ids(busy_ids),
                "forbidden": _compact_ids(forbidden_ids),
            },
        )
        return jsonify(
            {
                "ok": True,
                "data": {
                    "count": len(approved_ids),
                    "approvedIds": approved_ids,
                    "conflictIds": conflict_ids,
                    "invalidStatusIds": invalid_status_ids,
                    "invalidScheduleIds": invalid_schedule_ids,
                    "notFoundIds": not_found_ids,
                    "busyIds": busy_ids,
                    "forbiddenIds": forbidden_ids,
                },
            }
        )
    else:
        placeholders = ",".join(["%s"] * len(clean_ids))

        def _tx(cur):
            cur.execute(f"UPDATE reservation SET status='cancelled' WHERE id IN ({placeholders})", clean_ids)
            return cur.rowcount

        affected = run_in_transaction(_tx)
        audit_log(
            "admin.reservation.batch_cancel",
            target_type="reservation",
            detail={"cancelled": _compact_ids(clean_ids)},
        )

    return jsonify({"ok": True, "data": {"count": int(affected or 0)}})


@app.get("/reservations")
@auth_required()
def list_reservations():
    status = request.args.get("status", "").strip()
    user = request.args.get("user", "").strip()
    user_keyword = request.args.get("userKeyword", "").strip()
    lab_name = request.args.get("labName", "").strip()
    lab_keyword = request.args.get("labKeyword", "").strip()
    date = request.args.get("date", "").strip()
    date_from = request.args.get("dateFrom", "").strip()
    date_to = request.args.get("dateTo", "").strip()
    page_raw = request.args.get("page", "").strip()
    page_size_raw = request.args.get("pageSize", "").strip()
    current_user = g.current_user or {}
    current_username = str(current_user.get("username") or "").strip()
    current_role = str(current_user.get("role") or "").strip().lower()
    is_admin = current_role == "admin"
    can_review = current_role == "teacher"
    can_manage_all = is_admin or can_review
    use_pagination = bool(page_raw or page_size_raw)
    is_lab_calendar_query = bool(lab_name and date and status)

    # non-admin/non-reviewer: user filter can only query self
    if not can_manage_all and user and user != current_user.get("username"):
        return jsonify({"ok": False, "msg": "forbidden"}), 403
    if not can_manage_all and user_keyword:
        return jsonify({"ok": False, "msg": "forbidden"}), 403

    # teacher: keep personal reservation queries available, but approval queues
    # should only expose reservations assigned to teacher review.
    if can_review and not is_admin:
        if user and user != current_username:
            return jsonify({"ok": False, "msg": "forbidden"}), 403

    # regular users default to own data unless this is a lab calendar query
    if not can_manage_all and not user:
        if not (lab_name and date and status):
            user = current_user.get("username")

    where_sql = " WHERE 1=1"
    params = []

    if status:
        if "," in status:
            parts = [s.strip() for s in status.split(",") if s.strip()]
            if parts:
                where_sql += " AND status IN (" + ",".join(["%s"] * len(parts)) + ")"
                params.extend(parts)
        else:
            where_sql += " AND status=%s"
            params.append(status)

    if user:
        where_sql += " AND user_name=%s"
        params.append(user)
    elif user_keyword:
        where_sql += " AND user_name LIKE %s"
        params.append(f"%{user_keyword}%")

    if lab_name:
        where_sql += " AND lab_name=%s"
        params.append(lab_name)
    elif lab_keyword:
        where_sql += " AND lab_name LIKE %s"
        params.append(f"%{lab_keyword}%")

    if date:
        where_sql += " AND date=%s"
        params.append(date)
    else:
        date_from_dt = _parse_date_yyyy_mm_dd(date_from)
        date_to_dt = _parse_date_yyyy_mm_dd(date_to)
        if date_from and not date_from_dt:
            return jsonify({"ok": False, "msg": "invalid dateFrom"}), 400
        if date_to and not date_to_dt:
            return jsonify({"ok": False, "msg": "invalid dateTo"}), 400
        if date_from_dt and date_to_dt and date_from_dt > date_to_dt:
            return jsonify({"ok": False, "msg": "dateFrom must be <= dateTo"}), 400
        if date_from_dt:
            where_sql += " AND date >= %s"
            params.append(date_from_dt.strftime("%Y-%m-%d"))
        if date_to_dt:
            where_sql += " AND date <= %s"
            params.append(date_to_dt.strftime("%Y-%m-%d"))

    if can_review and not is_admin and not user and not is_lab_calendar_query:
        where_sql += " AND review_role='teacher'"

    base_sql = """
        SELECT r.id,
               r.lab_id AS labId,
               r.lab_name AS labName,
               r.user_name AS user,
               r.date,
               r.time,
               r.reason,
               r.status,
               r.reject_reason AS rejectReason,
               r.admin_note AS adminNote,
               r.review_role AS reviewRole,
               r.review_policy AS reviewPolicy,
               r.created_at AS createdAt,
               u.role AS reserverRole,
               u.nickname AS reserverNickname,
               u.student_no AS studentNo,
               u.job_no AS jobNo
        FROM reservation r
        LEFT JOIN user u ON u.username=r.user_name
    """

    if not use_pagination:
        rows = query(base_sql + where_sql + " ORDER BY id DESC", params)
        rows = [serialize_reservation_record_for_actor(row, actor=current_user) for row in rows]
        return jsonify(rows)

    try:
        page = int(page_raw or "1")
    except ValueError:
        page = 1
    try:
        page_size = int(page_size_raw or "20")
    except ValueError:
        page_size = 20
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    count_rows = query("SELECT COUNT(*) AS cnt FROM reservation" + where_sql, params)
    total = int((count_rows[0] or {}).get("cnt") or 0) if count_rows else 0

    list_sql = base_sql + where_sql + " ORDER BY id DESC LIMIT %s OFFSET %s"
    list_params = list(params) + [page_size, offset]
    rows = query(list_sql, list_params)
    rows = [serialize_reservation_record_for_actor(row, actor=current_user) for row in rows]

    return jsonify(
        {
            "ok": True,
            "data": rows,
            "meta": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "hasMore": (offset + len(rows)) < total,
            },
        }
    )


@app.get("/reservations/<int:rid>")
@auth_required()
def get_reservation(rid):
    row = query(
        """
        SELECT r.id,
               r.lab_id AS labId,
               r.lab_name AS labName,
               r.user_name AS user,
               r.date,
               r.time,
               r.reason,
               r.status,
               r.reject_reason AS rejectReason,
               r.admin_note AS adminNote,
               r.review_role AS reviewRole,
               r.review_policy AS reviewPolicy,
               r.created_at AS createdAt,
               u.role AS reserverRole,
               u.nickname AS reserverNickname,
               u.student_no AS studentNo,
               u.job_no AS jobNo
        FROM reservation r
        LEFT JOIN user u ON u.username=r.user_name
        WHERE r.id=%s
        LIMIT 1
        """,
        (rid,),
    )
    if not row:
        return jsonify({"ok": False, "msg": "reservation not found"}), 404
    current_user = g.current_user or {}
    role = str(current_user.get("role") or "").strip().lower()
    if role != "admin" and row[0].get("user") != current_user.get("username"):
        return jsonify({"ok": False, "msg": "forbidden"}), 403
    return jsonify({"ok": True, "data": serialize_reservation_record_for_actor(row[0], actor=current_user)})


def _reservation_user_violation_count(user_name):
    user = str(user_name or "").strip()
    if not user:
        return 0
    rows = query(
        """
        SELECT (
                   SELECT COUNT(*)
                   FROM reservation r
                   WHERE r.user_name=%s
                     AND r.status='rejected'
               ) + (
                   SELECT COUNT(*)
                   FROM lost_found lf
                   WHERE lf.claim_apply_user=%s
                     AND lf.claim_apply_status='rejected'
               ) + (
                   SELECT COUNT(*)
                   FROM equipment_borrow_request br
                   WHERE br.applicant_user_name=%s
                     AND (
                         (br.status='approved' AND br.returned_at IS NULL AND br.expected_return_at IS NOT NULL AND br.expected_return_at < NOW())
                         OR
                         (br.status='returned' AND br.returned_at IS NOT NULL AND br.expected_return_at IS NOT NULL AND br.returned_at > br.expected_return_at)
                     )
               ) AS cnt
        """,
        (user, user, user),
    )
    return int((rows[0] or {}).get("cnt") or 0) if rows else 0


def _build_reservation_ai_suggestion_payload(reservation_row):
    row = reservation_row or {}
    lab_id = _to_int_or_none(row.get("labId"))
    lab_name = str(row.get("labName") or "").strip()
    user_name = str(row.get("user") or "").strip()
    date_text = str(row.get("date") or "").strip()
    time_text = str(row.get("time") or "").strip()
    reason_text = str(row.get("reason") or "").strip()
    status = str(row.get("status") or "").strip().lower()
    created_at_text = _to_text_time(row.get("createdAt"))
    created_dt = _to_datetime(created_at_text)
    age_hours = 0.0
    if created_dt != datetime.min:
        age_hours = max(0.0, round((datetime.now() - created_dt).total_seconds() / 3600.0, 2))

    reasons = []
    risks = []
    next_actions = []
    score = 88
    decision = "approve"

    if status != "pending":
        decision = "review"
        score = 40
        risks.append(f"当前记录状态为 {status or '-'}，不属于待审批。")

    schedule_error = validate_reservation_schedule(date_text, time_text, lab_id=lab_id, lab_name=lab_name)
    if schedule_error:
        decision = "reject"
        score -= 48
        risks.append(f"预约规则校验未通过：{schedule_error}。")
        next_actions.append("建议先驳回，并引导申请人修改日期或时间段后重提。")
    else:
        reasons.append("当前预约时间符合系统预约规则。")

    review_policy = resolve_reservation_review_policy(lab_id=lab_id, lab_name=lab_name, date_text=date_text, time_range=time_text)
    if bool(review_policy.get("approvalRequired")):
        reviewer = "教师" if str(review_policy.get("reviewRole") or "").strip() == "teacher" else "管理员"
        reasons.append(f"该时段按规则需要{reviewer}审批。")
        if str(review_policy.get("reviewPolicy") or "").strip() == "peak_admin":
            score -= 6
            risks.append("命中了高峰审批策略，建议确认资源负载后再放行。")
    else:
        reasons.append("该时段按规则可自动通过。")
        score += 4

    if lab_name and date_text and time_text and has_approved_conflict(lab_name, date_text, time_text, exclude_id=_to_int_or_none(row.get("id"))):
        decision = "reject"
        score -= 50
        risks.append("同实验室同时间段已存在已通过预约，存在硬冲突。")
        next_actions.append("建议改为驳回或要求改期。")

    violation_count = _reservation_user_violation_count(user_name)
    if violation_count > 0:
        score -= min(24, violation_count * 6)
        risks.append(f"申请人存在 {violation_count} 条历史违规/异常记录。")
        if decision == "approve":
            decision = "review"
            next_actions.append("建议补充核查申请人历史记录后再审批。")
    else:
        reasons.append("申请人近期无明显违规记录。")

    if not reason_text:
        score -= 12
        risks.append("本次申请未填写用途说明。")
        if decision == "approve":
            decision = "review"
            next_actions.append("建议先补充用途说明。")
    else:
        reasons.append("申请用途已填写。")

    if age_hours >= 24:
        reasons.append(f"该申请已等待约 {age_hours:.1f} 小时，处理优先级较高。")
        score += 4

    score = max(0, min(99, int(round(score))))
    if decision == "approve":
        summary = f"建议通过，综合分 {score}。规则可通过，且当前未发现硬性冲突。"
    elif decision == "reject":
        summary = f"建议驳回，综合分 {score}。当前存在规则或时段冲突风险。"
    else:
        summary = f"建议转人工重点复核，综合分 {score}。本单仍有不确定项。"

    alternatives = []
    if decision == "reject" and lab_name and date_text and time_text:
        try:
            alternatives = build_reservation_plans(
                user_name=user_name,
                lab_id_or_name=lab_id or lab_name,
                preferred_date=date_text,
                preferred_time=time_text,
                days=7,
                k=3,
            )
        except Exception:
            alternatives = []
    alternatives = _agent_normalize_plan_items(alternatives)

    if not next_actions:
        if decision == "approve":
            next_actions.append("可直接审批通过。")
        elif decision == "reject":
            next_actions.append("建议驳回并附上原因说明。")
        else:
            next_actions.append("建议先补充备注，再决定是否通过。")

    return {
        "decision": decision,
        "score": score,
        "summary": summary,
        "reasons": reasons[:5],
        "risks": risks[:5],
        "nextActions": next_actions[:4],
        "metrics": {
            "violationCount": violation_count,
            "ageHours": age_hours,
            "approvalRequired": bool(review_policy.get("approvalRequired")),
            "reviewRole": str(review_policy.get("reviewRole") or "").strip(),
            "reviewPolicy": str(review_policy.get("reviewPolicy") or "").strip(),
        },
        "alternatives": alternatives[:3],
    }


@app.get("/reservations/<int:rid>/ai-suggestion")
@auth_required(roles=["admin"])
def get_reservation_ai_suggestion(rid):
    rows = query(
        """
        SELECT id,
               lab_id AS labId,
               lab_name AS labName,
               user_name AS user,
               date,
               time,
               reason,
               status,
               reject_reason AS rejectReason,
               admin_note AS adminNote,
               review_role AS reviewRole,
               review_policy AS reviewPolicy,
               created_at AS createdAt
        FROM reservation
        WHERE id=%s
        LIMIT 1
        """,
        (rid,),
    )
    if not rows:
        return jsonify({"ok": False, "msg": "reservation not found"}), 404
    row = rows[0] or {}
    suggestion = _build_reservation_ai_suggestion_payload(row)
    current_user = g.current_user or {}
    audit_log(
        "reservation.ai_suggestion",
        target_type="reservation",
        target_id=rid,
        detail={
            "decision": suggestion.get("decision"),
            "score": suggestion.get("score"),
            "reviewRole": row.get("reviewRole"),
        },
        actor={"id": current_user.get("id"), "username": current_user.get("username"), "role": current_user.get("role")},
    )
    return jsonify({"ok": True, "data": {"reservation": row, "suggestion": suggestion}})


@app.get("/reservations/export")
@auth_required(roles=["admin"])
def export_reservations():
    status = request.args.get("status", "").strip()
    lab_name = request.args.get("labName", "").strip()
    lab_keyword = request.args.get("labKeyword", "").strip()
    user = request.args.get("user", "").strip()
    user_keyword = request.args.get("userKeyword", "").strip()
    date = request.args.get("date", "").strip()
    date_from = request.args.get("dateFrom", "").strip()
    date_to = request.args.get("dateTo", "").strip()
    sql = """
        SELECT id, lab_name, user_name, date, time, reason, status,
               reject_reason, admin_note, created_at
        FROM reservation
        WHERE 1=1
    """
    params = []
    if status:
        sql += " AND status=%s"
        params.append(status)
    if lab_name:
        sql += " AND lab_name=%s"
        params.append(lab_name)
    elif lab_keyword:
        sql += " AND lab_name LIKE %s"
        params.append(f"%{lab_keyword}%")
    if user:
        sql += " AND user_name=%s"
        params.append(user)
    elif user_keyword:
        sql += " AND user_name LIKE %s"
        params.append(f"%{user_keyword}%")
    if date:
        sql += " AND date=%s"
        params.append(date)
    else:
        date_from_dt = _parse_date_yyyy_mm_dd(date_from)
        date_to_dt = _parse_date_yyyy_mm_dd(date_to)
        if date_from and not date_from_dt:
            return jsonify({"ok": False, "msg": "invalid dateFrom"}), 400
        if date_to and not date_to_dt:
            return jsonify({"ok": False, "msg": "invalid dateTo"}), 400
        if date_from_dt and date_to_dt and date_from_dt > date_to_dt:
            return jsonify({"ok": False, "msg": "dateFrom must be <= dateTo"}), 400
        if date_from_dt:
            sql += " AND date >= %s"
            params.append(date_from_dt.strftime("%Y-%m-%d"))
        if date_to_dt:
            sql += " AND date <= %s"
            params.append(date_to_dt.strftime("%Y-%m-%d"))
    sql += " ORDER BY id DESC"
    rows = query(sql, params)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "lab_name", "user_name", "date", "time",
        "reason", "status", "reject_reason", "admin_note", "created_at"
    ])
    for r in rows:
        writer.writerow([
            r.get("id"), r.get("lab_name"), r.get("user_name"), r.get("date"), r.get("time"),
            r.get("reason"), r.get("status"), r.get("reject_reason"), r.get("admin_note"), r.get("created_at")
        ])
    csv_data = output.getvalue()
    return (csv_data, 200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": "attachment; filename=reservations.csv"
    })


@app.get("/notifications")
@auth_required()
def notifications():
    user = (g.current_user.get("username") or "").strip()
    role = (g.current_user.get("role") or "").strip()
    type_filter = request.args.get("type", "").strip()
    if not user:
        return jsonify({"ok": True, "data": [], "meta": {"count": 0, "role": role, "types": []}})

    allowed_types = {"reservation", "lostfound", "repair", "sensor_alarm", "course_task", "asset_borrow"}
    types = set()
    if type_filter:
        for part in type_filter.split(","):
            p = part.strip()
            if p in allowed_types:
                types.add(p)
    else:
        types = set(allowed_types)

    notices = []

    if "reservation" in types:
        reservation_rows = query(
            """
            SELECT id, lab_name AS labName, status, reject_reason AS rejectReason,
                   admin_note AS adminNote, created_at AS createdAt
            FROM reservation
            WHERE user_name=%s
            ORDER BY id DESC
            LIMIT 100
            """,
            (user,),
        )
        for r in reservation_rows:
            status = r.get("status") or ""
            if status == "approved":
                msg = "Reservation approved"
            elif status == "rejected":
                msg = f"Reservation rejected: {r.get('rejectReason') or ''}"
            elif status == "cancelled":
                msg = "Reservation cancelled"
            elif status == "pending":
                msg = "Reservation pending review"
            else:
                msg = f"Reservation status: {status}"

            note = (r.get("adminNote") or "").strip()
            if note:
                msg = f"{msg} (note: {note})"
            notices.append(
                {
                    "id": f"reservation-{r.get('id')}",
                    "type": "reservation",
                    "labName": r.get("labName"),
                    "status": status,
                    "message": msg,
                    "createdAt": _to_text_time(r.get("createdAt")),
                    "_sortAt": _to_datetime(r.get("createdAt")),
                }
            )

    if "repair" in types:
        repair_sql = """
            SELECT id,
                   order_no AS orderNo,
                   lab_name AS labName,
                   equipment_name AS equipmentName,
                   asset_code AS assetCode,
                   issue_type AS issueType,
                   description,
                   attachment_url AS attachmentUrl,
                   status,
                   submitter_name AS submitterName,
                   assignee_name AS assigneeName,
                   submitted_at AS submittedAt,
                   accepted_at AS acceptedAt,
                   processing_at AS processingAt,
                   completed_at AS completedAt,
                   updated_at AS updatedAt
            FROM repair_work_order
        """
        params = []
        if role == "admin":
            repair_sql += " ORDER BY updated_at DESC, id DESC LIMIT 200"
        else:
            repair_sql += " WHERE submitter_name=%s ORDER BY updated_at DESC, id DESC LIMIT 200"
            params.append(user)
        repair_rows = query(repair_sql, params)

        for r in repair_rows:
            status = str(r.get("status") or "").strip() or "submitted"
            order_no = str(r.get("orderNo") or "").strip() or f"#{r.get('id')}"
            assignee = str(r.get("assigneeName") or "").strip()
            submitter = str(r.get("submitterName") or "").strip() or "user"
            equipment_name = (
                str(r.get("equipmentName") or "").strip()
                or str(r.get("assetCode") or "").strip()
                or "equipment"
            )
            desc = str(r.get("description") or "").strip()
            if status == "accepted":
                msg = (
                    f"Work order {order_no} accepted, assignee: {assignee or '-'}"
                    if role == "admin"
                    else f"Your work order {order_no} has been accepted, assignee: {assignee or '-'}"
                )
                created_raw = r.get("acceptedAt") or r.get("updatedAt")
            elif status == "processing":
                msg = (
                    f"Work order {order_no} is being processed, assignee: {assignee or '-'}"
                    if role == "admin"
                    else f"Your work order {order_no} is being processed, assignee: {assignee or '-'}"
                )
                created_raw = r.get("processingAt") or r.get("updatedAt")
            elif status == "completed":
                msg = (
                    f"Work order {order_no} completed, assignee: {assignee or '-'}"
                    if role == "admin"
                    else f"Your work order {order_no} is completed, please submit follow-up feedback"
                )
                created_raw = r.get("completedAt") or r.get("updatedAt")
            else:
                msg = (
                    f"{submitter} submitted work order {order_no}: {equipment_name}"
                    if role == "admin"
                    else f"You submitted work order {order_no}: {equipment_name}"
                )
                created_raw = r.get("submittedAt") or r.get("updatedAt")

            if desc:
                msg = f"{msg} ({desc[:80]}{'...' if len(desc) > 80 else ''})"

            notices.append(
                {
                    "id": f"repair-{r.get('id')}",
                    "type": "repair",
                    "labName": r.get("labName") or "lab",
                    "status": status,
                    "message": msg,
                    "attachmentUrl": r.get("attachmentUrl") or "",
                    "orderNo": order_no,
                    "assigneeName": assignee,
                    "createdAt": _to_text_time(created_raw),
                    "_sortAt": _to_datetime(r.get("updatedAt") or created_raw),
                }
            )

    if "sensor_alarm" in types and role == "admin":
        sensor_alarm_rows = query(
            """
            SELECT id,
                   lab_id AS labId,
                   lab_name AS labName,
                   alarm_code AS alarmCode,
                   level,
                   message,
                   created_at AS createdAt
            FROM lab_sensor_alarm
            ORDER BY id DESC
            LIMIT 200
            """
        )
        for r in sensor_alarm_rows:
            level = str(r.get("level") or "alarm").strip() or "alarm"
            msg = str(r.get("message") or "").strip() or "Lab sensor alarm"
            notices.append(
                {
                    "id": f"sensor-alarm-{r.get('id')}",
                    "type": "sensor_alarm",
                    "labName": r.get("labName") or "lab",
                    "status": level,
                    "message": msg,
                    "alarmCode": str(r.get("alarmCode") or ""),
                    "createdAt": _to_text_time(r.get("createdAt")),
                    "_sortAt": _to_datetime(r.get("createdAt")),
                }
            )

    if "lostfound" in types:
        lost_found_rows = query(
            """
            SELECT id, title, item_type AS type, status, owner,
                   claim_student_id AS claimStudentId,
                   claim_name AS claimName,
                   claim_class AS claimClass,
                   claim_apply_status AS claimApplyStatus,
                   claim_apply_user AS claimApplyUser,
                   claim_apply_name AS claimApplyName,
                   claim_apply_reason AS claimApplyReason,
                   claim_apply_at AS claimApplyAt,
                   claim_reviewed_at AS claimReviewedAt,
                   claim_review_note AS claimReviewNote,
                   created_at AS createdAt
            FROM lost_found
            WHERE owner=%s OR claim_apply_user=%s
            ORDER BY id DESC
            LIMIT 100
            """,
            (user, user),
        )
        for r in lost_found_rows:
            title = str(r.get("title") or "").strip() or "Lost&Found"
            row_type = str(r.get("type") or "").strip()
            owner = str(r.get("owner") or "").strip()
            row_status = str(r.get("status") or "").strip() or "open"
            claim_apply_status = str(r.get("claimApplyStatus") or "").strip()
            claim_apply_user = str(r.get("claimApplyUser") or "").strip()

            if owner == user:
                if row_type == "found" and claim_apply_status in {"pending", "approved", "rejected"}:
                    if claim_apply_status == "pending":
                        who = str(r.get("claimApplyName") or claim_apply_user or "user").strip()
                        msg = f"Your found item \"{title}\" has a pending claim from {who}"
                        status = "claim_pending"
                        at = r.get("claimApplyAt") or r.get("createdAt")
                    elif claim_apply_status == "approved":
                        msg = f"Your found item \"{title}\" claim approved"
                        status = "claim_approved"
                        at = r.get("claimReviewedAt") or r.get("createdAt")
                    else:
                        note = str(r.get("claimReviewNote") or "").strip()
                        msg = f"Your found item \"{title}\" claim rejected"
                        if note:
                            msg = f"{msg} (reason: {note})"
                        status = "claim_rejected"
                        at = r.get("claimReviewedAt") or r.get("createdAt")
                else:
                    scope = "found" if row_type == "found" else "lost"
                    msg = f"Your {scope} item \"{title}\" status: {row_status}"
                    status = row_status
                    at = r.get("createdAt")
                notices.append(
                    {
                        "id": f"lostfound-owner-{r.get('id')}-{status}",
                        "type": "lostfound",
                        "labName": title,
                        "status": status,
                        "message": msg,
                        "createdAt": _to_text_time(at),
                        "_sortAt": _to_datetime(at),
                    }
                )

            if claim_apply_user == user and owner != user:
                if claim_apply_status == "pending":
                    msg = f"Your claim for \"{title}\" is pending review"
                    status = "claim_pending"
                    at = r.get("claimApplyAt") or r.get("createdAt")
                elif claim_apply_status == "approved":
                    msg = f"Your claim for \"{title}\" is approved"
                    status = "claim_approved"
                    at = r.get("claimReviewedAt") or r.get("createdAt")
                elif claim_apply_status == "rejected":
                    note = str(r.get("claimReviewNote") or "").strip()
                    msg = f"Your claim for \"{title}\" is rejected"
                    if note:
                        msg = f"{msg} (reason: {note})"
                    status = "claim_rejected"
                    at = r.get("claimReviewedAt") or r.get("createdAt")
                else:
                    msg = f"Your claim for \"{title}\" is being processed"
                    status = "claim_pending"
                    at = r.get("claimApplyAt") or r.get("createdAt")
                notices.append(
                    {
                        "id": f"lostfound-claimant-{r.get('id')}-{status}",
                        "type": "lostfound",
                        "labName": title,
                        "status": status,
                        "message": msg,
                        "createdAt": _to_text_time(at),
                        "_sortAt": _to_datetime(at),
                    }
                )

    if "course_task" in types:
        course_task_rows = query(
            """
            SELECT id,
                   course_id AS courseId,
                   task_id AS taskId,
                   message,
                   created_at AS createdAt
            FROM course_task_notice
            WHERE to_user_name=%s
              AND status='active'
            ORDER BY id DESC
            LIMIT 200
            """,
            (user,),
        )
        for r in course_task_rows:
            created_at = r.get("createdAt")
            notices.append(
                {
                    "id": f"course-task-{r.get('id')}",
                    "type": "course_task",
                    "labName": "课程作业提醒",
                    "status": "course_pending",
                    "message": str(r.get("message") or "").strip() or "你有实验任务尚未提交，请尽快处理",
                    "courseId": int(r.get("courseId") or 0),
                    "taskId": int(r.get("taskId") or 0),
                    "createdAt": _to_text_time(created_at),
                    "_sortAt": _to_datetime(created_at),
                }
            )

    if "asset_borrow" in types:
        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            from . import routes_assets as _routes_assets

            if role == "admin":
                _routes_assets.borrow_ensure_auto_reminders(include_all=True)
            else:
                _routes_assets.borrow_ensure_auto_reminders(user_name=user, include_all=False)
        except Exception:
            pass

        if role == "admin":
            admin_rows = query(
                """
                SELECT id,
                       equipment_name AS equipmentName,
                       equipment_asset_code AS equipmentAssetCode,
                       applicant_user_name AS applicantUserName,
                       applicant_name AS applicantName,
                       expected_return_at AS expectedReturnAt,
                       status,
                       risk_flag AS riskFlag,
                       risk_reason AS riskReason,
                       created_at AS createdAt
                FROM equipment_borrow_request
                WHERE status='pending'
                   OR (status='approved' AND returned_at IS NULL AND expected_return_at IS NOT NULL AND expected_return_at < %s)
                ORDER BY id DESC
                LIMIT 200
                """,
                (now_text,),
            )
            for row in admin_rows:
                req_id = int(row.get("id") or 0)
                status = str(row.get("status") or "").strip()
                equipment_text = (
                    str(row.get("equipmentName") or "").strip()
                    or str(row.get("equipmentAssetCode") or "").strip()
                    or "设备"
                )
                applicant_text = str(row.get("applicantName") or "").strip() or str(row.get("applicantUserName") or "").strip() or "-"
                risk_flag = int(row.get("riskFlag") or 0) == 1
                risk_reason = str(row.get("riskReason") or "").strip()
                expected_return_at = _to_text_time(row.get("expectedReturnAt"))
                if status == "approved":
                    msg = f"借用逾期未归还：{equipment_text}（申请人：{applicant_text}）"
                    if expected_return_at:
                        msg = f"{msg}，应还时间：{expected_return_at}"
                    notice_status = "overdue"
                else:
                    msg = f"新的资产借用申请：{equipment_text}（申请人：{applicant_text}）"
                    if risk_flag:
                        msg = f"{msg} ⚠ 该用户有逾期历史"
                        if risk_reason:
                            msg = f"{msg}（{risk_reason}）"
                    notice_status = "pending"
                created_at = _to_text_time(row.get("createdAt"))
                notices.append(
                    {
                        "id": f"borrow-request-{req_id}-{notice_status}",
                        "type": "asset_borrow",
                        "labName": equipment_text,
                        "status": notice_status,
                        "message": msg,
                        "requestId": req_id,
                        "createdAt": created_at,
                        "_sortAt": _to_datetime(created_at),
                    }
                )
        else:
            user_rows = query(
                """
                SELECT id,
                       equipment_name AS equipmentName,
                       equipment_asset_code AS equipmentAssetCode,
                       expected_return_at AS expectedReturnAt,
                       status,
                       reject_reason AS rejectReason,
                       admin_note AS adminNote,
                       created_at AS createdAt,
                       approved_at AS approvedAt,
                       returned_at AS returnedAt,
                       updated_at AS updatedAt
                FROM equipment_borrow_request
                WHERE applicant_user_name=%s
                ORDER BY id DESC
                LIMIT 200
                """,
                (user,),
            )
            now_dt = datetime.now()
            for row in user_rows:
                req_id = int(row.get("id") or 0)
                status = str(row.get("status") or "").strip()
                equipment_text = (
                    str(row.get("equipmentName") or "").strip()
                    or str(row.get("equipmentAssetCode") or "").strip()
                    or "设备"
                )
                expected_dt = _to_datetime(row.get("expectedReturnAt"))
                is_overdue = bool(status == "approved" and expected_dt != datetime.min and expected_dt < now_dt)
                if status == "pending":
                    msg = f"{equipment_text} 借用申请待审批。"
                    notice_status = "pending"
                    sort_raw = row.get("createdAt")
                elif status == "approved":
                    if is_overdue:
                        msg = f"{equipment_text} 借用已逾期，请尽快归还。"
                        notice_status = "overdue"
                    else:
                        msg = f"{equipment_text} 借用申请已通过，请按时归还。"
                        notice_status = "approved"
                    sort_raw = row.get("approvedAt") or row.get("updatedAt") or row.get("createdAt")
                elif status == "rejected":
                    reason = str(row.get("rejectReason") or "").strip()
                    msg = f"{equipment_text} 借用申请已驳回。"
                    if reason:
                        msg = f"{msg} 原因：{reason}"
                    notice_status = "rejected"
                    sort_raw = row.get("updatedAt") or row.get("createdAt")
                elif status == "returned":
                    msg = f"{equipment_text} 已登记归还。"
                    notice_status = "returned"
                    sort_raw = row.get("returnedAt") or row.get("updatedAt") or row.get("createdAt")
                else:
                    msg = f"{equipment_text} 借用状态：{status or '-'}"
                    notice_status = status or "info"
                    sort_raw = row.get("updatedAt") or row.get("createdAt")
                admin_note = str(row.get("adminNote") or "").strip()
                if admin_note:
                    msg = f"{msg} 备注：{admin_note}"
                created_at = _to_text_time(sort_raw)
                notices.append(
                    {
                        "id": f"borrow-request-{req_id}-{notice_status}",
                        "type": "asset_borrow",
                        "labName": equipment_text,
                        "status": notice_status,
                        "message": msg,
                        "requestId": req_id,
                        "createdAt": created_at,
                        "_sortAt": _to_datetime(created_at),
                    }
                )

            remind_rows = query(
                """
                SELECT l.id,
                       l.request_id AS requestId,
                       l.remind_type AS remindType,
                       l.message,
                       l.created_at AS createdAt,
                       r.equipment_name AS equipmentName,
                       r.equipment_asset_code AS equipmentAssetCode
                FROM equipment_borrow_reminder_log l
                INNER JOIN equipment_borrow_request r ON r.id=l.request_id
                WHERE r.applicant_user_name=%s
                ORDER BY l.id DESC
                LIMIT 200
                """,
                (user,),
            )
            for row in remind_rows:
                req_id = int(row.get("requestId") or 0)
                log_id = int(row.get("id") or 0)
                remind_type = str(row.get("remindType") or "").strip() or "manual"
                equipment_text = (
                    str(row.get("equipmentName") or "").strip()
                    or str(row.get("equipmentAssetCode") or "").strip()
                    or "设备"
                )
                msg = str(row.get("message") or "").strip() or f"{equipment_text} 请记得归还。"
                if remind_type == "auto":
                    msg = f"系统提醒：{msg}"
                else:
                    msg = f"管理员提醒：{msg}"
                created_at = _to_text_time(row.get("createdAt"))
                notices.append(
                    {
                        "id": f"borrow-remind-{req_id}-{log_id}",
                        "type": "asset_borrow",
                        "labName": equipment_text,
                        "status": "reminder",
                        "message": msg,
                        "requestId": req_id,
                        "createdAt": created_at,
                        "_sortAt": _to_datetime(created_at),
                    }
                )

    notices.sort(key=lambda x: x.get("_sortAt", datetime.min), reverse=True)
    for n in notices:
        n.pop("_sortAt", None)
    result = notices[:100]
    return jsonify({
        "ok": True,
        "data": result,
        "meta": {
            "count": len(result),
            "role": role,
            "types": sorted(types),
        },
    })


@app.get("/notifications/read-state")
@auth_required()
def get_notifications_read_state():
    user = (g.current_user.get("username") or "").strip()
    if not user:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401
    state = get_notification_read_state(user)
    return jsonify({"ok": True, "data": state})


@app.post("/notifications/read-state")
@auth_required()
def update_notifications_read_state():
    user = (g.current_user.get("username") or "").strip()
    if not user:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401

    payload = request.get_json(force=True) or {}
    patch = {}

    read_state_payload = payload.get("readState")
    if isinstance(read_state_payload, dict):
        for raw_type, raw_time in read_state_payload.items():
            notice_type = str(raw_type or "").strip()
            read_at = str(raw_time or "").strip()
            if not notice_type or not read_at:
                continue
            patch[notice_type] = read_at
    else:
        notice_type = str(payload.get("type") or "").strip()
        read_at = str(payload.get("lastReadAt") or "").strip()
        if notice_type and read_at:
            patch[notice_type] = read_at

    if not patch:
        return jsonify({"ok": False, "msg": "readState required"}), 400

    try:
        state = update_notification_read_state(user, patch)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    actor = g.current_user or {}
    audit_log(
        "user.notification.read_state.update",
        target_type="notification",
        target_id=user,
        detail={"types": sorted([x for x in patch.keys() if x in NOTIFICATION_TYPE_SET])},
        actor={
            "id": actor.get("id"),
            "username": actor.get("username"),
            "role": actor.get("role"),
        },
    )
    return jsonify({"ok": True, "data": state})


@app.post("/feedback")
@auth_required()
def submit_feedback():
    payload = request.get_json(force=True) or {}
    feedback_type = str(payload.get("type") or "").strip().lower() or "issue"
    content = str(payload.get("content") or "").strip()
    contact = str(payload.get("contact") or "").strip()
    source = str(payload.get("source") or "").strip().lower() or "app"
    allowed_types = {"issue", "suggestion", "consult", "other"}

    if feedback_type not in allowed_types:
        return jsonify({"ok": False, "msg": "invalid type"}), 400
    if len(content) < 5:
        return jsonify({"ok": False, "msg": "content too short"}), 400
    if len(content) > 2000:
        return jsonify({"ok": False, "msg": "content too long"}), 400
    if len(contact) > 120:
        contact = contact[:120]
    if len(source) > 32:
        source = source[:32]

    actor = g.current_user or {}
    user_name = str(actor.get("username") or "").strip()
    user_role = str(actor.get("role") or "").strip().lower()
    if not user_name:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    feedback_id = execute_insert(
        """
        INSERT INTO user_feedback (
            user_name, user_role, feedback_type, content, contact, source, status, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, 'submitted', %s, %s)
        """,
        (user_name, user_role, feedback_type, content, contact, source, now_text, now_text),
    )

    audit_log(
        "user.feedback.submit",
        target_type="user_feedback",
        target_id=feedback_id,
        detail={
            "type": feedback_type,
            "source": source,
            "contactProvided": bool(contact),
            "contentPreview": content[:120],
        },
        actor={
            "id": actor.get("id"),
            "username": actor.get("username"),
            "role": actor.get("role"),
        },
    )
    return jsonify({"ok": True, "data": {"id": int(feedback_id or 0), "createdAt": now_text}})


@app.get("/announcements")
@auth_required()
def get_announcements():
    limit_raw = request.args.get("limit", "").strip()
    try:
        limit = int(limit_raw or "20")
    except ValueError:
        limit = 20
    limit = max(1, min(limit, 100))
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = query(
        """
        SELECT id,
               title,
               content,
               publisher_id AS publisherId,
               publisher_name AS publisherName,
               created_at AS createdAt,
               publish_at AS publishAt,
               updated_at AS updatedAt,
               is_pinned AS isPinned,
               pinned_at AS pinnedAt
        FROM announcement
        WHERE COALESCE(publish_at, created_at) <= %s
        ORDER BY is_pinned DESC,
                 COALESCE(pinned_at, '1970-01-01 00:00:00') DESC,
                 COALESCE(publish_at, created_at) DESC,
                 id DESC
        LIMIT %s
        """,
        (now_text, limit),
    )

    data = []
    for row in rows:
        publish_at_text = _to_text_time(row.get("publishAt") or row.get("createdAt"))
        status = "scheduled" if _to_datetime(publish_at_text) > datetime.now() else "published"
        data.append(
            {
                "id": row.get("id"),
                "title": row.get("title") or "",
                "content": row.get("content") or "",
                "publisherId": row.get("publisherId"),
                "publisherName": row.get("publisherName") or "",
                "createdAt": _to_text_time(row.get("createdAt")),
                "publishAt": publish_at_text,
                "updatedAt": _to_text_time(row.get("updatedAt") or row.get("createdAt")),
                "isPinned": int(row.get("isPinned") or 0) == 1,
                "pinnedAt": _to_text_time(row.get("pinnedAt")),
                "status": status,
                "type": "announcement",
            }
        )
    return jsonify({"ok": True, "data": data})


def _normalize_announcement_title(value):
    text = str(value or "").strip()
    if not text:
        raise BizError("title required", 400)
    if len(text) > 120:
        raise BizError("title too long", 400)
    return text


def _normalize_announcement_content(value):
    text = str(value or "").strip()
    if not text:
        raise BizError("content required", 400)
    if len(text) > 5000:
        raise BizError("content too long", 400)
    return text


def _normalize_announcement_publish_at(value, default_now=False):
    text = str(value or "").strip()
    if not text:
        if default_now:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        raise BizError("publishAt required", 400)
    dt = _to_datetime(text)
    if dt == datetime.min:
        raise BizError("invalid publishAt", 400)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _normalize_announcement_is_pinned(value, default=0):
    if value is None:
        return int(default or 0)
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if int(value) != 0 else 0
    text = str(value or "").strip().lower()
    if text in ("1", "true", "yes", "y", "on"):
        return 1
    if text in ("0", "false", "no", "n", "off", ""):
        return 0
    raise BizError("invalid isPinned", 400)


def _build_announcement_ai_draft(title_hint="", content_hint="", publish_at="", is_pinned=False):
    title_text = str(title_hint or "").strip()
    content_text = str(content_hint or "").strip()
    publish_text = str(publish_at or "").strip()
    compact = f"{title_text} {content_text}".strip().lower()

    scene = "general"
    if any(token in compact for token in ("停课", "补课", "课程", "实验")):
        scene = "course"
    elif any(token in compact for token in ("维修", "报修", "设备", "机房")):
        scene = "maintenance"
    elif any(token in compact for token in ("安全", "告警", "消防", "门禁")):
        scene = "safety"

    title_map = {
        "course": "实验课程安排通知",
        "maintenance": "实验室设备维护通知",
        "safety": "实验室安全提醒",
        "general": "实验室管理通知",
    }
    summary_map = {
        "course": "面向师生说明课程安排、时间节点和提交要求。",
        "maintenance": "面向使用人员说明维护范围、影响时段和应对方式。",
        "safety": "强调安全要求、现场秩序和应急处理方式。",
        "general": "面向全体用户的常规运营通知。",
    }
    body_map = {
        "course": [
            "请相关班级同学提前查看课程安排，按要求完成实验准备。",
            "如涉及补交、改期或分组调整，请在课前与任课教师沟通确认。",
        ],
        "maintenance": [
            "相关实验室或设备将在指定时段维护，请提前调整预约与上机安排。",
            "如遇紧急教学需求，请联系管理员协调备用场地或替代设备。",
        ],
        "safety": [
            "请严格遵守实验室用电、门禁和现场安全规定，避免聚集与违规操作。",
            "如发现异常告警或安全隐患，请第一时间上报管理员并保持现场可追溯。",
        ],
        "general": [
            "请各位师生关注最新安排，合理规划预约、课程和实验时间。",
            "如有特殊情况，请通过系统消息或管理员渠道及时反馈。",
        ],
    }

    final_title = title_text or title_map.get(scene, "实验室管理通知")
    lines = ["各位老师、同学："]
    if content_text:
        lines.append(content_text)
    else:
        lines.extend(body_map.get(scene, body_map["general"]))
    lines.append("请收到通知后互相转告，并按要求执行。")
    if publish_text:
        lines.append(f"计划发布时间：{publish_text}")
    if is_pinned:
        lines.append("该通知建议置顶展示，便于近期集中查看。")

    return {
        "title": final_title[:120],
        "content": "\n".join([x for x in lines if x])[:5000],
        "summary": summary_map.get(scene, summary_map["general"]),
        "publishAtSuggestion": publish_text or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "isPinnedSuggestion": bool(is_pinned),
        "scene": scene,
    }


def _fetch_announcement_row(announcement_id):
    rows = query(
        """
        SELECT id,
               title,
               content,
               publisher_id AS publisherId,
               publisher_name AS publisherName,
               created_at AS createdAt,
               publish_at AS publishAt,
               updated_at AS updatedAt,
               is_pinned AS isPinned,
               pinned_at AS pinnedAt
        FROM announcement
        WHERE id=%s
        LIMIT 1
        """,
        (announcement_id,),
    )
    return rows[0] if rows else None


def _format_announcement_payload(row):
    row = row or {}
    created_at_text = _to_text_time(row.get("createdAt"))
    publish_at_text = _to_text_time(row.get("publishAt") or row.get("createdAt"))
    updated_at_text = _to_text_time(row.get("updatedAt") or row.get("createdAt"))
    pinned_at_text = _to_text_time(row.get("pinnedAt"))
    status = "scheduled" if _to_datetime(publish_at_text) > datetime.now() else "published"
    return {
        "id": row.get("id"),
        "title": row.get("title") or "",
        "content": row.get("content") or "",
        "publisherId": row.get("publisherId"),
        "publisherName": row.get("publisherName") or "",
        "createdAt": created_at_text,
        "publishAt": publish_at_text,
        "updatedAt": updated_at_text,
        "isPinned": int(row.get("isPinned") or 0) == 1,
        "pinnedAt": pinned_at_text,
        "status": status,
        "type": "announcement",
    }


@app.post("/announcements/ai-draft")
@auth_required(roles=["admin"])
def announcement_ai_draft():
    payload = request.get_json(force=True) or {}
    draft = _build_announcement_ai_draft(
        title_hint=payload.get("titleHint"),
        content_hint=payload.get("contentHint"),
        publish_at=payload.get("publishAt"),
        is_pinned=_normalize_announcement_is_pinned(payload.get("isPinned"), default=0) == 1,
    )
    current_user = g.current_user or {}
    audit_log(
        "announcement.ai_draft",
        target_type="announcement",
        detail={"scene": draft.get("scene"), "isPinned": bool(draft.get("isPinnedSuggestion"))},
        actor={"id": current_user.get("id"), "username": current_user.get("username"), "role": current_user.get("role")},
    )
    return jsonify({"ok": True, "data": draft})


@app.post("/announcements")
@auth_required(roles=["admin"])
def publish_announcement():
    payload = request.get_json(force=True) or {}
    try:
        title = _normalize_announcement_title(payload.get("title"))
        content = _normalize_announcement_content(payload.get("content"))
        publish_at = _normalize_announcement_publish_at(payload.get("publishAt"), default_now=True)
        is_pinned = _normalize_announcement_is_pinned(payload.get("isPinned"), default=0)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    current_user = g.current_user or {}
    publisher_id = _to_int_or_none(current_user.get("id"))
    publisher_name = str(current_user.get("username") or "").strip()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pinned_at = created_at if is_pinned == 1 else None

    new_id = execute_insert(
        """
        INSERT INTO announcement (
            title, content, publisher_id, publisher_name,
            created_at, publish_at, updated_at, is_pinned, pinned_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (title, content, publisher_id, publisher_name, created_at, publish_at, created_at, is_pinned, pinned_at),
    )
    created_row = _fetch_announcement_row(new_id)
    data = _format_announcement_payload(created_row)

    audit_log(
        "admin.announcement.schedule" if data.get("status") == "scheduled" else "admin.announcement.publish",
        target_type="announcement",
        target_id=new_id,
        detail={"title": title, "publishAt": data.get("publishAt"), "isPinned": data.get("isPinned")},
    )

    if not data.get("publisherName"):
        data["publisherName"] = publisher_name
    return jsonify({"ok": True, "data": data})


@app.get("/admin/announcements")
@auth_required(roles=["admin"])
def admin_list_announcements():
    limit_raw = request.args.get("limit", "").strip()
    status = request.args.get("status", "all").strip().lower()
    if status not in ("all", "published", "scheduled"):
        return jsonify({"ok": False, "msg": "invalid status"}), 400
    try:
        limit = int(limit_raw or "50")
    except ValueError:
        limit = 50
    limit = max(1, min(limit, 200))

    where_sql = ""
    params = []
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if status == "published":
        where_sql = " WHERE COALESCE(publish_at, created_at) <= %s"
        params.append(now_text)
    elif status == "scheduled":
        where_sql = " WHERE COALESCE(publish_at, created_at) > %s"
        params.append(now_text)

    rows = query(
        """
        SELECT id,
               title,
               content,
               publisher_id AS publisherId,
               publisher_name AS publisherName,
               created_at AS createdAt,
               publish_at AS publishAt,
               updated_at AS updatedAt,
               is_pinned AS isPinned,
               pinned_at AS pinnedAt
        FROM announcement
        """
        + where_sql
        + """
        ORDER BY is_pinned DESC,
                 COALESCE(pinned_at, '1970-01-01 00:00:00') DESC,
                 COALESCE(publish_at, created_at) DESC,
                 id DESC
        LIMIT %s
        """,
        tuple(params + [limit]),
    )
    data = [_format_announcement_payload(row) for row in rows]
    return jsonify({"ok": True, "data": data})


@app.put("/announcements/<int:announcement_id>")
@auth_required(roles=["admin"])
def update_announcement(announcement_id):
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "msg": "params error"}), 400

    editable_fields = ("title", "content", "publishAt", "isPinned")
    touched_fields = [k for k in editable_fields if k in payload]
    if not touched_fields:
        return jsonify({"ok": False, "msg": "no changes"}), 400

    existing = _fetch_announcement_row(announcement_id)
    if not existing:
        return jsonify({"ok": False, "msg": "announcement not found"}), 404

    try:
        next_title = _normalize_announcement_title(payload.get("title")) if "title" in payload else str(existing.get("title") or "")
        next_content = (
            _normalize_announcement_content(payload.get("content")) if "content" in payload else str(existing.get("content") or "")
        )
        next_publish_at = (
            _normalize_announcement_publish_at(payload.get("publishAt"), default_now=True)
            if "publishAt" in payload
            else _to_text_time(existing.get("publishAt") or existing.get("createdAt"))
        )
        next_is_pinned = (
            _normalize_announcement_is_pinned(payload.get("isPinned"), default=int(existing.get("isPinned") or 0))
            if "isPinned" in payload
            else int(existing.get("isPinned") or 0)
        )
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    old_is_pinned = int(existing.get("isPinned") or 0)
    old_pinned_at = _to_text_time(existing.get("pinnedAt"))
    if next_is_pinned == 1:
        next_pinned_at = old_pinned_at if old_is_pinned == 1 and old_pinned_at else now_text
    else:
        next_pinned_at = None

    execute(
        """
        UPDATE announcement
        SET title=%s,
            content=%s,
            publish_at=%s,
            is_pinned=%s,
            pinned_at=%s,
            updated_at=%s
        WHERE id=%s
        """,
        (next_title, next_content, next_publish_at, next_is_pinned, next_pinned_at, now_text, announcement_id),
    )
    updated_row = _fetch_announcement_row(announcement_id)
    data = _format_announcement_payload(updated_row)

    audit_log(
        "admin.announcement.update",
        target_type="announcement",
        target_id=announcement_id,
        detail={
            "fields": touched_fields,
            "title": data.get("title"),
            "publishAt": data.get("publishAt"),
            "isPinned": data.get("isPinned"),
            "status": data.get("status"),
        },
    )
    return jsonify({"ok": True, "data": data})


@app.post("/announcements/<int:announcement_id>/pin")
@auth_required(roles=["admin"])
def pin_announcement(announcement_id):
    payload = request.get_json(silent=True) or {}
    existing = _fetch_announcement_row(announcement_id)
    if not existing:
        return jsonify({"ok": False, "msg": "announcement not found"}), 404

    try:
        pinned = _normalize_announcement_is_pinned(payload.get("pinned"), default=1)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    old_is_pinned = int(existing.get("isPinned") or 0)
    old_pinned_at = _to_text_time(existing.get("pinnedAt"))
    if pinned == 1:
        pinned_at = old_pinned_at if old_is_pinned == 1 and old_pinned_at else now_text
    else:
        pinned_at = None

    execute(
        """
        UPDATE announcement
        SET is_pinned=%s,
            pinned_at=%s,
            updated_at=%s
        WHERE id=%s
        """,
        (pinned, pinned_at, now_text, announcement_id),
    )
    updated_row = _fetch_announcement_row(announcement_id)
    data = _format_announcement_payload(updated_row)

    audit_log(
        "admin.announcement.pin" if pinned == 1 else "admin.announcement.unpin",
        target_type="announcement",
        target_id=announcement_id,
        detail={"pinned": pinned == 1, "title": data.get("title")},
    )
    return jsonify({"ok": True, "data": data})


@app.delete("/announcements/<int:announcement_id>")
@auth_required(roles=["admin"])
def delete_announcement(announcement_id):
    row = _fetch_announcement_row(announcement_id)
    if not row:
        return jsonify({"ok": False, "msg": "announcement not found"}), 404

    execute("DELETE FROM announcement WHERE id=%s", (announcement_id,))
    audit_log(
        "admin.announcement.delete",
        target_type="announcement",
        target_id=announcement_id,
        detail={"title": row.get("title") or ""},
    )
    return jsonify({"ok": True})


@app.get("/admin/reservations/<int:rid>/alternatives")
@auth_required(roles=["admin"])
def admin_reservation_alternatives(rid):
    days = _to_int_or_none(request.args.get("days")) or 7
    k = _to_int_or_none(request.args.get("k")) or 3
    days = max(1, min(int(days), 30))
    k = max(1, min(int(k), 20))

    rows = query(
        """
        SELECT id,
               lab_id AS labId,
               lab_name AS labName,
               user_name AS userName,
               date,
               time
        FROM reservation
        WHERE id=%s
        LIMIT 1
        """,
        (rid,),
    )
    if not rows:
        return jsonify({"ok": False, "msg": "reservation not found"}), 404

    row = rows[0] or {}
    plans = build_reservation_plans(
        user_name=str(row.get("userName") or "").strip(),
        lab_id_or_name=_to_int_or_none(row.get("labId")) or str(row.get("labName") or "").strip(),
        preferred_date=str(row.get("date") or "").strip(),
        preferred_time=str(row.get("time") or "").strip(),
        days=days,
        k=k,
    )

    audit_log(
        "admin.reservation.alternatives",
        target_type="reservation",
        target_id=rid,
        detail={
            "labId": _to_int_or_none(row.get("labId")),
            "labName": str(row.get("labName") or "").strip(),
            "date": str(row.get("date") or "").strip(),
            "time": str(row.get("time") or "").strip(),
            "planCount": len(plans),
        },
        actor={"id": g.current_user.get("id"), "username": g.current_user.get("username"), "role": g.current_user.get("role")},
    )

    return jsonify(
        {
            "ok": True,
            "data": {
                "reservation": {
                    "id": int(row.get("id") or 0),
                    "labId": _to_int_or_none(row.get("labId")),
                    "labName": str(row.get("labName") or "").strip(),
                    "date": str(row.get("date") or "").strip(),
                    "time": str(row.get("time") or "").strip(),
                },
                "plans": plans,
            },
        }
    )


@app.post("/reservations/waitlist")
@auth_required()
def create_reservation_waitlist():
    payload = request.get_json(force=True) or {}
    current_user = g.current_user or {}
    user_name = str(current_user.get("username") or "").strip()
    user_role = str(current_user.get("role") or "").strip().lower()
    lab_name = str(payload.get("labName") or "").strip()
    date_text = str(payload.get("date") or "").strip()
    time_text = str(payload.get("time") or "").strip()
    reason = str(payload.get("reason") or "").strip()
    source_reservation_id = _to_int_or_none(payload.get("sourceReservationId"))
    lab_id = _to_int_or_none(payload.get("labId"))
    if not user_name or not lab_name or not date_text or not time_text:
        raise BizError("params error", 400)
    if not has_approved_conflict(lab_name, date_text, time_text):
        raise BizError("slot is available, create reservation directly", 409)

    priority = _build_reservation_waitlist_priority(user_name, user_role=user_role, reason=reason, created_at=_to_text_time(datetime.now()))

    def _tx(cur):
        cur.execute(
            """
            SELECT id
            FROM reservation_waitlist
            WHERE user_name=%s
              AND lab_name=%s
              AND date=%s
              AND time=%s
              AND status='waiting'
            LIMIT 1
            FOR UPDATE
            """,
            (user_name, lab_name, date_text, time_text),
        )
        existing = cur.fetchone()
        if existing:
            raise BizError("already joined waitlist", 409)
        cur.execute(
            """
            INSERT INTO reservation_waitlist (
                lab_id, lab_name, user_name, user_role, date, time, reason, status,
                priority_score, priority_breakdown_json, source_reservation_id, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'waiting', %s, %s, %s, %s, %s)
            """,
            (
                lab_id,
                lab_name,
                user_name,
                user_role,
                date_text,
                time_text,
                reason,
                priority.get("score"),
                json.dumps(priority.get("breakdown") or {}, ensure_ascii=False, separators=(",", ":")),
                source_reservation_id,
                _to_text_time(datetime.now()),
                _to_text_time(datetime.now()),
            ),
        )
        return int(cur.lastrowid or 0)

    waitlist_id = run_in_transaction(_tx)
    audit_log(
        "user.reservation.waitlist.create",
        target_type="reservation_waitlist",
        target_id=waitlist_id,
        detail={"labName": lab_name, "date": date_text, "time": time_text, "priorityScore": priority.get("score")},
        actor={"id": current_user.get("id"), "username": user_name, "role": current_user.get("role")},
    )
    return jsonify({"ok": True, "data": {"id": waitlist_id, "priorityScore": priority.get("score"), "priorityBreakdown": priority.get("breakdown")}})


@app.get("/reservations/waitlist")
@auth_required()
def list_reservation_waitlist():
    current_user = g.current_user or {}
    user_name = str(current_user.get("username") or "").strip()
    role = str(current_user.get("role") or "").strip().lower()
    status = str(request.args.get("status") or "").strip().lower()
    lab_name = str(request.args.get("labName") or "").strip()
    date_text = str(request.args.get("date") or "").strip()
    mine = str(request.args.get("mine") or "").strip().lower() in {"1", "true", "yes", "on"}
    if role != "admin":
        mine = True

    where_sql = " WHERE 1=1"
    params = []
    if mine:
        where_sql += " AND user_name=%s"
        params.append(user_name)
    if status:
        where_sql += " AND status=%s"
        params.append(status)
    if lab_name:
        where_sql += " AND lab_name=%s"
        params.append(lab_name)
    if date_text:
        where_sql += " AND date=%s"
        params.append(date_text)

    rows = query(
        """
        SELECT id,
               lab_id AS labId,
               lab_name AS labName,
               user_name AS userName,
               user_role AS userRole,
               date,
               time,
               reason,
               status,
               priority_score AS priorityScore,
               priority_breakdown_json AS priorityBreakdownJson,
               source_reservation_id AS sourceReservationId,
               promoted_reservation_id AS promotedReservationId,
               promoted_at AS promotedAt,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM reservation_waitlist
        """
        + where_sql
        + """
        ORDER BY status='waiting' DESC, priority_score DESC, id ASC
        LIMIT 200
        """,
        tuple(params),
    )
    data = []
    for row in rows:
        breakdown_json = str(row.get("priorityBreakdownJson") or "").strip()
        try:
            breakdown = json.loads(breakdown_json) if breakdown_json else {}
        except Exception:
            breakdown = {}
        data.append(
            {
                "id": int(row.get("id") or 0),
                "labId": _to_int_or_none(row.get("labId")),
                "labName": str(row.get("labName") or "").strip(),
                "userName": str(row.get("userName") or "").strip(),
                "userRole": str(row.get("userRole") or "").strip(),
                "date": str(row.get("date") or "").strip(),
                "time": str(row.get("time") or "").strip(),
                "reason": str(row.get("reason") or "").strip(),
                "status": str(row.get("status") or "").strip(),
                "priorityScore": float(row.get("priorityScore") or 0),
                "priorityBreakdown": breakdown,
                "sourceReservationId": _to_int_or_none(row.get("sourceReservationId")),
                "promotedReservationId": _to_int_or_none(row.get("promotedReservationId")),
                "promotedAt": _to_text_time(row.get("promotedAt")),
                "createdAt": _to_text_time(row.get("createdAt")),
                "updatedAt": _to_text_time(row.get("updatedAt")),
            }
        )
    return jsonify({"ok": True, "data": data, "meta": {"count": len(data), "limit": limit}})


@app.post("/reservations/waitlist/<int:waitlist_id>/cancel")
@auth_required()
def cancel_reservation_waitlist(waitlist_id):
    current_user = g.current_user or {}
    user_name = str(current_user.get("username") or "").strip()
    role = str(current_user.get("role") or "").strip().lower()

    def _tx(cur):
        cur.execute(
            """
            SELECT id, user_name AS userName, status
            FROM reservation_waitlist
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(waitlist_id),),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("waitlist not found", 404)
        if role != "admin" and str(row.get("userName") or "").strip() != user_name:
            raise BizError("forbidden", 403)
        if str(row.get("status") or "").strip() != "waiting":
            raise BizError("invalid status", 409)
        cur.execute("UPDATE reservation_waitlist SET status='cancelled', updated_at=%s WHERE id=%s", (_to_text_time(datetime.now()), int(waitlist_id)))

    run_in_transaction(_tx)
    audit_log("reservation.waitlist.cancel", target_type="reservation_waitlist", target_id=waitlist_id, actor={"id": current_user.get("id"), "username": user_name, "role": current_user.get("role")})
    return jsonify({"ok": True})


@app.post("/admin/reservation-waitlist/<int:waitlist_id>/promote")
@auth_required(roles=["admin"])
def admin_promote_waitlist(waitlist_id):
    actor = g.current_user or {}
    rows = query(
        """
        SELECT id,
               lab_id AS labId,
               lab_name AS labName,
               date,
               time,
               status
        FROM reservation_waitlist
        WHERE id=%s
        LIMIT 1
        """,
        (int(waitlist_id),),
    )
    if not rows:
        raise BizError("waitlist not found", 404)
    row = rows[0] or {}
    if str(row.get("status") or "").strip() != "waiting":
        raise BizError("invalid status", 409)
    promoted = _try_promote_waitlist(row.get("labId"), row.get("labName"), row.get("date"), row.get("time"), actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")})
    if not promoted:
        raise BizError("promotion failed", 409)
    return jsonify({"ok": True, "data": promoted})


@app.get("/admin/reservation-priority-rules")
@auth_required(roles=["admin"])
def admin_get_reservation_priority_rule():
    return jsonify({"ok": True, "data": _serialize_reservation_priority_rule(_get_active_reservation_priority_rule())})


@app.post("/admin/reservation-priority-rules")
@auth_required(roles=["admin"])
def admin_save_reservation_priority_rule():
    actor = g.current_user or {}
    payload = request.get_json(force=True) or {}
    rule = _normalize_reservation_priority_rule_payload(payload)
    now_text = _to_text_time(datetime.now())

    def _tx(cur):
        cur.execute("UPDATE reservation_priority_rule SET status='inactive' WHERE status='active'")
        cur.execute(
            """
            INSERT INTO reservation_priority_rule (
                status, teacher_weight, student_weight, admin_weight,
                teaching_weight, research_weight, default_weight,
                violation_penalty, wait_hour_bonus, wait_hour_bonus_cap,
                updated_by, created_at, updated_at
            )
            VALUES ('active', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                rule["teacherWeight"],
                rule["studentWeight"],
                rule["adminWeight"],
                rule["teachingWeight"],
                rule["researchWeight"],
                rule["defaultWeight"],
                rule["violationPenalty"],
                rule["waitHourBonus"],
                rule["waitHourBonusCap"],
                str(actor.get("username") or "").strip(),
                now_text,
                now_text,
            ),
        )
        return int(cur.lastrowid or 0)

    rule_id = run_in_transaction(_tx)
    saved = _get_active_reservation_priority_rule()
    audit_log(
        "admin.reservation_priority_rule.save",
        target_type="reservation_priority_rule",
        target_id=rule_id,
        detail=_serialize_reservation_priority_rule(saved),
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": _serialize_reservation_priority_rule(saved)})


@app.post("/admin/reservation-priority-preview")
@auth_required(roles=["admin"])
def admin_preview_reservation_priority():
    actor = g.current_user or {}
    payload = request.get_json(force=True) or {}
    lab_name = str(payload.get("labName") or "").strip()
    date_text = str(payload.get("date") or "").strip()
    time_text = str(payload.get("time") or "").strip()
    if not lab_name or not date_text or not time_text:
        raise BizError("params error", 400)
    rule_payload = _normalize_reservation_priority_rule_payload(payload.get("rule") if isinstance(payload.get("rule"), dict) else payload)
    waiting_rows = query(
        """
        SELECT id,
               user_name AS userName,
               user_role AS userRole,
               reason,
               created_at AS createdAt
        FROM reservation_waitlist
        WHERE status='waiting'
          AND lab_name=%s
          AND date=%s
          AND time=%s
        ORDER BY id ASC
        LIMIT 100
        """,
        (lab_name, date_text, time_text),
    )
    ordered = []
    for row in waiting_rows:
        score_data = _build_reservation_waitlist_priority(
            str(row.get("userName") or "").strip(),
            user_role=str(row.get("userRole") or "").strip(),
            reason=str(row.get("reason") or "").strip(),
            created_at=row.get("createdAt"),
            rule=rule_payload,
        )
        ordered.append(
            {
                "id": int(row.get("id") or 0),
                "userName": str(row.get("userName") or "").strip(),
                "userRole": str(row.get("userRole") or "").strip(),
                "reason": str(row.get("reason") or "").strip(),
                "createdAt": _to_text_time(row.get("createdAt")),
                "priorityScore": score_data.get("score"),
                "priorityBreakdown": score_data.get("breakdown"),
            }
        )
    ordered.sort(key=lambda item: (-float(item.get("priorityScore") or 0), str(item.get("createdAt") or "")))
    result = {"slot": {"labName": lab_name, "date": date_text, "time": time_text}, "count": len(ordered), "items": ordered}
    execute_insert(
        """
        INSERT INTO reservation_rule_preview_log (preview_by, request_json, result_json, created_at)
        VALUES (%s, %s, %s, %s)
        """,
        (
            str(actor.get("username") or "").strip(),
            json.dumps({"labName": lab_name, "date": date_text, "time": time_text, "rule": rule_payload}, ensure_ascii=False, separators=(",", ":")),
            json.dumps(result, ensure_ascii=False, separators=(",", ":")),
            _to_text_time(datetime.now()),
        ),
    )
    audit_log(
        "admin.reservation_priority.preview",
        target_type="reservation_waitlist",
        detail={"labName": lab_name, "date": date_text, "time": time_text, "count": len(ordered)},
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": result})

@app.post("/reservations/<int:rid>/approve")
@auth_required(roles=["admin", "teacher"])
def approve_reservation(rid):
    actor_role = str((g.current_user or {}).get("role") or "").strip().lower()
    try:
        def _tx(cur):
            cur.execute(
                """
                SELECT id, lab_id AS labId, lab_name AS labName, date, time, status, review_role AS reviewRole
                FROM reservation
                WHERE id=%s
                LIMIT 1
                FOR UPDATE
                """,
                (rid,),
            )
            row = cur.fetchone()
            if not row:
                raise BizError("reservation not found", 404)
            if row["status"] != "pending":
                raise BizError("invalid status", 409)
            if not can_review_reservation(actor_role, row.get("reviewRole")):
                raise BizError("forbidden", 403)

            schedule_error = validate_reservation_schedule(
                row["date"],
                row["time"],
                lab_id=_to_int_or_none(row.get("labId")),
                lab_name=row.get("labName"),
            )
            if schedule_error:
                raise BizError(f"invalid reservation schedule: {schedule_error}", 400)

            lock_key = _reservation_lock_key(row["labName"], row["date"])
            if not _acquire_named_lock(cur, lock_key):
                raise BizError("reservation busy, try again", 409)
            try:
                if has_approved_conflict_with_cur(cur, row["labName"], row["date"], row["time"], exclude_id=rid):
                    raise BizError("reservation conflict with approved", 409)
                cur.execute(
                    """
                    UPDATE reservation
                    SET status='approved', reject_reason=''
                    WHERE id=%s AND status='pending'
                    """,
                    (rid,),
                )
                if cur.rowcount != 1:
                    raise BizError("reservation status changed, retry", 409)
            finally:
                _release_named_lock(cur, lock_key)

        run_in_transaction(_tx)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    audit_log("reservation.approve", target_type="reservation", target_id=rid)
    return jsonify({"ok": True})


@app.post("/reservations/<int:rid>/reject")
@auth_required(roles=["admin", "teacher"])
def reject_reservation(rid):
    data = request.get_json(force=True) or {}
    reason = (data.get("rejectReason") or "").strip()
    actor_role = str((g.current_user or {}).get("role") or "").strip().lower()
    try:
        def _tx(cur):
            cur.execute(
                "SELECT id, status, review_role AS reviewRole FROM reservation WHERE id=%s LIMIT 1 FOR UPDATE",
                (rid,),
            )
            row = cur.fetchone()
            if not row:
                raise BizError("reservation not found", 404)
            if row["status"] != "pending":
                raise BizError("invalid status", 409)
            if not can_review_reservation(actor_role, row.get("reviewRole")):
                raise BizError("forbidden", 403)
            cur.execute(
                "UPDATE reservation SET status='rejected', reject_reason=%s WHERE id=%s AND status='pending'",
                (reason, rid),
            )
            if cur.rowcount != 1:
                raise BizError("reservation status changed, retry", 409)

        run_in_transaction(_tx)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    audit_log(
        "reservation.reject",
        target_type="reservation",
        target_id=rid,
        detail={"rejectReason": reason},
    )
    return jsonify({"ok": True})


@app.post("/reservations/<int:rid>/note")
@auth_required(roles=["admin"])
def add_reservation_note(rid):
    data = request.get_json(force=True) or {}
    note = (data.get("note") or "").strip()
    if not note:
        return jsonify({"ok": False, "msg": "params error"}), 400

    row = query("SELECT id FROM reservation WHERE id=%s LIMIT 1", (rid,))
    if not row:
        return jsonify({"ok": False, "msg": "reservation not found"}), 404

    execute("UPDATE reservation SET admin_note=%s WHERE id=%s", (note, rid))
    audit_log(
        "admin.reservation.note",
        target_type="reservation",
        target_id=rid,
        detail={"note": note},
    )
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
