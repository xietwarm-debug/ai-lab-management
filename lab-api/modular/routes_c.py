from . import core as _core

for _k, _v in _core.__dict__.items():
    if _k.startswith("__"):
        continue
    globals()[_k] = _v

del _k, _v, _core

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
        return jsonify({"ok": False, "msg": e.msg}), e.status

    return jsonify({"ok": True, "data": {"id": created["id"]}})


@app.post("/reservations/<int:rid>/cancel")
@auth_required()
def cancel_reservation(rid):
    user = (g.current_user.get("username") or "").strip()
    if not user:
        return jsonify({"ok": False, "msg": "user required"}), 400

    row = query("SELECT id, user_name AS user, status FROM reservation WHERE id=%s LIMIT 1", (rid,))
    if not row:
        return jsonify({"ok": False, "msg": "reservation not found"}), 404
    if row[0]["user"] != user:
        return jsonify({"ok": False, "msg": "forbidden"}), 403

    if row[0]["status"] in ("rejected", "cancelled"):
        return jsonify({"ok": True})

    execute("UPDATE reservation SET status='cancelled' WHERE id=%s", (rid,))
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
    schedule_error = validate_reservation_schedule(date, time_range)
    if schedule_error:
        return jsonify({"ok": False, "msg": schedule_error}), 400

    try:
        def _tx(cur):
            cur.execute(
                """
                SELECT id, lab_name AS labName, user_name AS user, status
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
            if row["user"] != user:
                raise BizError("forbidden", 403)
            if row["status"] not in ("pending", "approved"):
                raise BizError("invalid status", 400)

            lab_name = row["labName"]
            lock_key = _reservation_lock_key(lab_name, date)
            if not _acquire_named_lock(cur, lock_key):
                raise BizError("reservation busy, try again", 409)
            try:
                if has_approved_conflict_with_cur(cur, lab_name, date, time_range, exclude_id=rid):
                    raise BizError("reservation conflict with approved", 409)
                cur.execute(
                    """
                    UPDATE reservation
                    SET date=%s, time=%s, status='pending', reject_reason=''
                    WHERE id=%s
                    """,
                    (date, time_range, rid),
                )
            finally:
                _release_named_lock(cur, lock_key)

        run_in_transaction(_tx)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    return jsonify({"ok": True})


@app.post("/reservations/<int:rid>/admin-cancel")
@auth_required(roles=["admin"])
def admin_cancel_reservation(rid):
    row = query("SELECT id FROM reservation WHERE id=%s LIMIT 1", (rid,))
    if not row:
        return jsonify({"ok": False, "msg": "reservation not found"}), 404

    execute("UPDATE reservation SET status='cancelled' WHERE id=%s", (rid,))
    audit_log("admin.reservation.cancel", target_type="reservation", target_id=rid)
    return jsonify({"ok": True})


@app.post("/reservations/<int:rid>/admin-reschedule")
@auth_required(roles=["admin"])
def admin_reschedule_reservation(rid):
    data = request.get_json(force=True) or {}
    date = (data.get("date") or "").strip()
    time_range = (data.get("time") or "").strip()
    if not date or not time_range:
        return jsonify({"ok": False, "msg": "params error"}), 400
    schedule_error = validate_reservation_schedule(date, time_range)
    if schedule_error:
        return jsonify({"ok": False, "msg": schedule_error}), 400

    try:
        def _tx(cur):
            cur.execute(
                """
                SELECT id, lab_name AS labName, status
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
            if row["status"] not in ("pending", "approved"):
                raise BizError("invalid status", 400)

            lab_name = row["labName"]
            lock_key = _reservation_lock_key(lab_name, date)
            if not _acquire_named_lock(cur, lock_key):
                raise BizError("reservation busy, try again", 409)
            try:
                if has_approved_conflict_with_cur(cur, lab_name, date, time_range, exclude_id=rid):
                    raise BizError("reservation conflict with approved", 409)
                cur.execute(
                    """
                    UPDATE reservation
                    SET date=%s, time=%s, status='pending', reject_reason=''
                    WHERE id=%s
                    """,
                    (date, time_range, rid),
                )
            finally:
                _release_named_lock(cur, lock_key)

        run_in_transaction(_tx)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    audit_log(
        "admin.reservation.reschedule",
        target_type="reservation",
        target_id=rid,
        detail={"date": date, "time": time_range},
    )
    return jsonify({"ok": True})


@app.post("/reservations/batch")
@auth_required(roles=["admin"])
def batch_reservations():
    data = request.get_json(force=True) or {}
    action = (data.get("action") or "").strip()  # approve/cancel
    ids = data.get("ids") or []
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

    if action == "approve":
        approved_ids = []
        conflict_ids = []
        invalid_status_ids = []
        invalid_schedule_ids = []
        not_found_ids = []
        busy_ids = []

        def _tx(cur):
            for rid in clean_ids:
                cur.execute(
                    """
                    SELECT id, lab_name AS labName, date, time, status
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

                schedule_error = validate_reservation_schedule(row["date"], row["time"])
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
    current_user = g.current_user
    is_admin = current_user.get("role") == "admin"
    use_pagination = bool(page_raw or page_size_raw)

    # non-admin: user filter can only query self
    if not is_admin and user and user != current_user.get("username"):
        return jsonify({"ok": False, "msg": "forbidden"}), 403
    if not is_admin and user_keyword:
        return jsonify({"ok": False, "msg": "forbidden"}), 403

    # non-admin and no explicit user filter: default to self unless this is a lab calendar query
    if not is_admin and not user:
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

    base_sql = """
        SELECT id,
               lab_name AS labName,
               user_name AS user,
               date,
               time,
               reason,
               status,
               reject_reason AS rejectReason,
               admin_note AS adminNote,
               created_at AS createdAt
        FROM reservation
    """

    if not use_pagination:
        rows = query(base_sql + where_sql + " ORDER BY id DESC", params)
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
        SELECT id,
               lab_name AS labName,
               user_name AS user,
               date,
               time,
               reason,
               status,
               reject_reason AS rejectReason,
               admin_note AS adminNote,
               created_at AS createdAt
        FROM reservation
        WHERE id=%s
        LIMIT 1
        """,
        (rid,),
    )
    if not row:
        return jsonify({"ok": False, "msg": "reservation not found"}), 404
    current_user = g.current_user
    if current_user.get("role") != "admin" and row[0].get("user") != current_user.get("username"):
        return jsonify({"ok": False, "msg": "forbidden"}), 403
    return jsonify({"ok": True, "data": row[0]})


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
    type_filter = request.args.get("type", "").strip()
    if not user:
        return jsonify([])

    allowed_types = {"reservation", "lostfound"}
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
                msg = "预约已通过"
            elif status == "rejected":
                msg = f"预约已驳回：{r.get('rejectReason') or ''}"
            elif status == "cancelled":
                msg = "预约已取消"
            elif status == "pending":
                msg = "预约待审批"
            else:
                msg = f"预约状态：{status}"

            note = (r.get("adminNote") or "").strip()
            if note:
                msg = f"{msg}（备注：{note}）"
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
            title = r.get("title") or "失物招领"
            row_type = r.get("type") or ""
            owner = (r.get("owner") or "").strip()
            claim_apply_status = (r.get("claimApplyStatus") or "").strip()
            claim_apply_user = (r.get("claimApplyUser") or "").strip()

            # owner notifications
            if owner == user:
                if row_type == "found":
                    if claim_apply_status == "pending":
                        who = (r.get("claimApplyName") or claim_apply_user or "用户")
                        notices.append(
                            {
                                "id": f"lostfound-owner-{r.get('id')}-pending",
                                "type": "lostfound",
                                "labName": title,
                                "status": "claim_pending",
                                "message": f"你拾到的物品《{title}》收到认领申请：{who}",
                                "createdAt": _to_text_time(r.get("claimApplyAt") or r.get("createdAt")),
                                "_sortAt": _to_datetime(r.get("claimApplyAt") or r.get("createdAt")),
                            }
                        )
                    elif claim_apply_status == "approved":
                        claim_text = "、".join(
                            [x for x in [r.get("claimStudentId"), r.get("claimName"), r.get("claimClass")] if x]
                        )
                        msg = f"你拾到的物品《{title}》已完成认领"
                        if claim_text:
                            msg = f"{msg}（认领信息：{claim_text}）"
                        notices.append(
                            {
                                "id": f"lostfound-owner-{r.get('id')}-approved",
                                "type": "lostfound",
                                "labName": title,
                                "status": "claim_approved",
                                "message": msg,
                                "createdAt": _to_text_time(r.get("claimReviewedAt") or r.get("createdAt")),
                                "_sortAt": _to_datetime(r.get("claimReviewedAt") or r.get("createdAt")),
                            }
                        )
                    elif claim_apply_status == "rejected":
                        note = (r.get("claimReviewNote") or "").strip()
                        msg = f"你拾到的物品《{title}》的认领申请已驳回"
                        if note:
                            msg = f"{msg}（原因：{note}）"
                        notices.append(
                            {
                                "id": f"lostfound-owner-{r.get('id')}-rejected",
                                "type": "lostfound",
                                "labName": title,
                                "status": "claim_rejected",
                                "message": msg,
                                "createdAt": _to_text_time(r.get("claimReviewedAt") or r.get("createdAt")),
                                "_sortAt": _to_datetime(r.get("claimReviewedAt") or r.get("createdAt")),
                            }
                        )
                    else:
                        row_status = (r.get("status") or "").strip()
                        if row_status == "closed":
                            claim_text = "、".join(
                                [x for x in [r.get("claimStudentId"), r.get("claimName"), r.get("claimClass")] if x]
                            )
                            msg = f"你拾到的物品《{title}》已处理"
                            if claim_text:
                                msg = f"{msg}（认领信息：{claim_text}）"
                        else:
                            msg = f"你拾到的物品《{title}》处理中"
                        notices.append(
                            {
                                "id": f"lostfound-owner-{r.get('id')}-open",
                                "type": "lostfound",
                                "labName": title,
                                "status": row_status or "open",
                                "message": msg,
                                "createdAt": _to_text_time(r.get("createdAt")),
                                "_sortAt": _to_datetime(r.get("createdAt")),
                            }
                        )
                else:
                    status = r.get("status") or ""
                    if status == "closed":
                        claim_text = "、".join(
                            [x for x in [r.get("claimStudentId"), r.get("claimName"), r.get("claimClass")] if x]
                        )
                        msg = f"你发布的失物《{title}》已处理"
                        if claim_text:
                            msg = f"{msg}（认领信息：{claim_text}）"
                    else:
                        msg = f"你发布的失物《{title}》处理中"
                    notices.append(
                        {
                            "id": f"lostfound-owner-{r.get('id')}-status",
                            "type": "lostfound",
                            "labName": title,
                            "status": status,
                            "message": msg,
                            "createdAt": _to_text_time(r.get("createdAt")),
                            "_sortAt": _to_datetime(r.get("createdAt")),
                        }
                    )

            # claimant notifications
            if claim_apply_user == user and owner != user:
                if claim_apply_status == "pending":
                    msg = f"你提交的《{title}》认领申请待审核"
                    status = "claim_pending"
                    at = r.get("claimApplyAt") or r.get("createdAt")
                elif claim_apply_status == "approved":
                    msg = f"你提交的《{title}》认领申请已通过"
                    status = "claim_approved"
                    at = r.get("claimReviewedAt") or r.get("createdAt")
                elif claim_apply_status == "rejected":
                    note = (r.get("claimReviewNote") or "").strip()
                    msg = f"你提交的《{title}》认领申请已驳回"
                    if note:
                        msg = f"{msg}（原因：{note}）"
                    status = "claim_rejected"
                    at = r.get("claimReviewedAt") or r.get("createdAt")
                else:
                    msg = f"你提交的《{title}》认领申请处理中"
                    status = "claim_pending"
                    at = r.get("claimApplyAt") or r.get("createdAt")
                notices.append(
                    {
                        "id": f"lostfound-claimant-{r.get('id')}-{claim_apply_status or 'none'}",
                        "type": "lostfound",
                        "labName": title,
                        "status": status,
                        "message": msg,
                        "createdAt": _to_text_time(at),
                        "_sortAt": _to_datetime(at),
                    }
                )

    notices.sort(key=lambda x: x.get("_sortAt", datetime.min), reverse=True)
    for n in notices:
        n.pop("_sortAt", None)
    return jsonify(notices[:100])


@app.get("/announcements")
@auth_required()
def get_announcements():
    limit_raw = request.args.get("limit", "").strip()
    try:
        limit = int(limit_raw or "20")
    except ValueError:
        limit = 20
    limit = max(1, min(limit, 100))

    rows = query(
        """
        SELECT id,
               title,
               content,
               publisher_name AS publisherName,
               created_at AS createdAt
        FROM announcement
        ORDER BY id DESC
        LIMIT %s
        """,
        (limit,),
    )

    data = []
    for row in rows:
        data.append(
            {
                "id": row.get("id"),
                "title": row.get("title") or "",
                "content": row.get("content") or "",
                "publisherName": row.get("publisherName") or "",
                "createdAt": _to_text_time(row.get("createdAt")),
                "type": "announcement",
            }
        )
    return jsonify({"ok": True, "data": data})


@app.post("/announcements")
@auth_required(roles=["admin"])
def publish_announcement():
    payload = request.get_json(force=True) or {}
    title = str(payload.get("title") or "").strip()
    content = str(payload.get("content") or "").strip()

    if not title:
        return jsonify({"ok": False, "msg": "title required"}), 400
    if not content:
        return jsonify({"ok": False, "msg": "content required"}), 400
    if len(title) > 120:
        return jsonify({"ok": False, "msg": "title too long"}), 400
    if len(content) > 5000:
        return jsonify({"ok": False, "msg": "content too long"}), 400

    current_user = g.current_user or {}
    publisher_id = _to_int_or_none(current_user.get("id"))
    publisher_name = str(current_user.get("username") or "").strip()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_id = execute_insert(
        """
        INSERT INTO announcement (title, content, publisher_id, publisher_name, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (title, content, publisher_id, publisher_name, created_at),
    )

    audit_log(
        "admin.announcement.publish",
        target_type="announcement",
        target_id=new_id,
        detail={"title": title},
    )

    return jsonify(
        {
            "ok": True,
            "data": {
                "id": new_id,
                "title": title,
                "content": content,
                "publisherName": publisher_name,
                "createdAt": created_at,
                "type": "announcement",
            },
        }
    )


@app.post("/reservations/<int:rid>/approve")
@auth_required(roles=["admin"])
def approve_reservation(rid):
    try:
        def _tx(cur):
            cur.execute(
                """
                SELECT id, lab_name AS labName, date, time, status
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

            schedule_error = validate_reservation_schedule(row["date"], row["time"])
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

    audit_log("admin.reservation.approve", target_type="reservation", target_id=rid)
    return jsonify({"ok": True})


@app.post("/reservations/<int:rid>/reject")
@auth_required(roles=["admin"])
def reject_reservation(rid):
    data = request.get_json(force=True) or {}
    reason = (data.get("rejectReason") or "").strip()
    try:
        def _tx(cur):
            cur.execute("SELECT id, status FROM reservation WHERE id=%s LIMIT 1 FOR UPDATE", (rid,))
            row = cur.fetchone()
            if not row:
                raise BizError("reservation not found", 404)
            if row["status"] != "pending":
                raise BizError("invalid status", 409)
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
        "admin.reservation.reject",
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
