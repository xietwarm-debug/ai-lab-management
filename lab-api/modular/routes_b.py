from . import core as _core

for _k, _v in _core.__dict__.items():
    if _k.startswith("__"):
        continue
    globals()[_k] = _v

del _k, _v, _core

@app.get("/lostfound")
@auth_required()
def list_lost_found():
    status = request.args.get("status", "").strip()
    item_type = request.args.get("type", "").strip()
    owner = request.args.get("owner", "").strip()
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
            created_at=CASE WHEN %s='closed' THEN %s ELSE created_at END
        WHERE id=%s
        """,
        (status, claim_student_id, claim_name, claim_class, status, status_time, lid),
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
        return jsonify(rows)

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
    return jsonify(rows)


@app.post("/labs/<int:lid>")
@auth_required(roles=["admin"])
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
@auth_required(roles=["admin"])
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
@auth_required(roles=["admin"])
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

    schedule_error = validate_reservation_schedule(date_text, time_text)
    if schedule_error:
        raise BizError(schedule_error, 400)

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
                INSERT INTO reservation (lab_id, lab_name, user_name, date, time, reason, status, reject_reason, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,'pending','',%s)
                """,
                (resolved_lab_id, resolved_lab_name, user, date_text, time_text, reason_text, created_at),
            )
            return cur.lastrowid
        finally:
            _release_named_lock(cur, lock_key)

    new_id = run_in_transaction(_tx)
    return {
        "id": int(new_id),
        "labId": resolved_lab_id,
        "labName": resolved_lab_name,
        "date": date_text,
        "time": time_text,
        "reason": reason_text,
        "status": "pending",
    }


