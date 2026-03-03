from . import core as _core

for _k, _v in _core.__dict__.items():
    if _k.startswith("__"):
        continue
    globals()[_k] = _v

del _k, _v, _core

@app.get("/health")
def health():
    return jsonify({"ok": True, "time": datetime.now().isoformat(timespec="seconds")})


@app.get("/reservation-rules")
@auth_required()
def reservation_rules():
    return jsonify({"ok": True, "data": get_reservation_rules_payload()})


@app.get("/ai/recommend-slots")
@auth_required()
def ai_recommend_slots():
    try:
        lab_id = _to_int_or_none(request.args.get("lab_id"))
        days = _to_int_or_none(request.args.get("days"))
        k = _to_int_or_none(request.args.get("k"))

        if not lab_id or lab_id <= 0:
            raise BizError("lab_id required", 400)

        days = int(days or 14)
        k = int(k or 3)
        days = max(1, min(days, 60))
        k = max(1, min(k, 20))

        user_name = (g.current_user.get("username") or "").strip()
        if not user_name:
            raise BizError("unauthorized", 401)

        lab_rows = query("SELECT id, name FROM lab WHERE id=%s LIMIT 1", (lab_id,))
        if not lab_rows:
            raise BizError("lab not found", 404)
        lab_name = (lab_rows[0].get("name") or "").strip()
        if not lab_name:
            raise BizError("lab not found", 404)

        rule_payload = get_reservation_rules_payload()
        candidate_slots = _resolve_rule_slots(rule_payload)
        if not candidate_slots:
            raise BizError("no available rule slots", 409)
        candidate_windows = _build_recommend_time_windows(candidate_slots)
        if not candidate_windows:
            raise BizError("no candidate windows", 409)

        user_rows = query(
            """
            SELECT time
            FROM reservation
            WHERE user_name=%s AND status<>'cancelled'
            """,
            (user_name,),
        )
        global_rows = query(
            """
            SELECT time
            FROM reservation
            WHERE lab_id=%s AND status<>'cancelled'
            """,
            (lab_id,),
        )

        user_freq, user_max = _count_slot_frequency(user_rows)
        global_freq, global_max = _count_slot_frequency(global_rows)

        base_date = datetime.now().date()
        picked = []

        for offset in range(days):
            date_text = (base_date + timedelta(days=offset)).strftime("%Y-%m-%d")
            for window in candidate_windows:
                time_range = window["time"]
                schedule_error = validate_reservation_schedule(date_text, time_range)
                if schedule_error:
                    continue
                if has_approved_conflict(lab_name, date_text, time_range):
                    continue

                slot_items = window.get("slots") or []
                if not slot_items:
                    continue
                user_score = sum((float(user_freq.get(s) or 0) / float(user_max)) if user_max > 0 else 0.0 for s in slot_items) / len(slot_items)
                global_score = sum((float(global_freq.get(s) or 0) / float(global_max)) if global_max > 0 else 0.0 for s in slot_items) / len(slot_items)
                score = 0.7 * user_score + 0.3 * global_score

                picked.append(
                    {
                        "date": date_text,
                        "time": time_range,
                        "scoreRaw": score,
                        "sortStart": int(window.get("firstStart") or 0),
                        "reason": "双节连排推荐（基于历史预约偏好与实验室热度）",
                    }
                )

        picked.sort(key=lambda x: (-x["scoreRaw"], x["date"], x["sortStart"], x["time"]))

        recommendations = []
        for row in picked[:k]:
            recommendations.append(
                {
                    "date": row["date"],
                    "time": row["time"],
                    "score": round(float(row["scoreRaw"]), 4),
                    "reason": row["reason"],
                }
            )

        return jsonify({"code": 0, "data": {"recommendations": recommendations}, "msg": "ok"})
    except BizError as e:
        return jsonify({"code": int(e.status or 1), "data": {"recommendations": []}, "msg": e.msg}), e.status
    except Exception:
        return jsonify({"code": 500, "data": {"recommendations": []}, "msg": "internal error"}), 500


@app.post("/agent/chat")
@auth_required()
def agent_chat():
    data = request.get_json(force=True) or {}
    text = str(data.get("text") or "").strip()
    if not text:
        return _agent_response(code=400, msg="text required", reply="请先输入你要预约的内容。", action="ask_info", http_status=400)

    current_role = str((g.current_user or {}).get("role") or "").strip()
    user_name = (g.current_user.get("username") or "").strip()
    if not user_name:
        return _agent_response(code=401, msg="unauthorized", reply="登录状态失效，请重新登录。", action="error", http_status=401)

    rule_payload = get_reservation_rules_payload()
    pending_ctx = _agent_pending_get(user_name)
    period_time_text = _extract_time_from_period_expression(text)
    fallback_date_text = _extract_date_from_text(text)
    fallback_lab_name = _extract_lab_name_from_text(text)

    tool_call = _agent_translate_intent(
        text=text,
        pending_ctx=pending_ctx,
        fallback_date_text=fallback_date_text,
        period_time_text=period_time_text,
        fallback_lab_name=fallback_lab_name,
    )
    return _agent_execute_tool(
        tool_call=tool_call,
        user_name=user_name,
        current_role=current_role,
        text=text,
        rule_payload=rule_payload,
    )


@app.post("/login")
def login():
    data = request.get_json(force=True) or {}
    username = (data.get("username") or "").strip()
    password = str(data.get("password") or "")
    role_want = (data.get("role") or "").strip()  # optional
    ip = get_client_ip()

    limited = enforce_rate_limit("login", f"{ip}:{username.lower()}")
    if limited:
        return limited

    if not username or not password:
        audit_log(
            "auth.login.failed",
            target_type="auth",
            target_id=username,
            detail={"reason": "params_error"},
            actor={"username": username},
        )
        return jsonify({"ok": False, "msg": "params error"}), 400

    row = query(
        "SELECT id, username, role, password_hash AS passwordHash FROM user WHERE username=%s LIMIT 1",
        (username,),
    )
    if not row:
        audit_log(
            "auth.login.failed",
            target_type="auth",
            target_id=username,
            detail={"reason": "user_not_found"},
            actor={"username": username},
        )
        return jsonify({"ok": False, "msg": "user not found"}), 404

    password_hash = (row[0].get("passwordHash") or "").strip()
    if not password_hash or not check_password_hash(password_hash, password):
        audit_log(
            "auth.login.failed",
            target_type="auth",
            target_id=username,
            detail={"reason": "invalid_password"},
            actor={"id": row[0]["id"], "username": row[0]["username"], "role": row[0]["role"]},
        )
        return jsonify({"ok": False, "msg": "invalid username or password"}), 400

    db_role = row[0]["role"]
    is_admin = (db_role == "admin")

    if role_want:
        if role_want not in ("user", "admin"):
            return jsonify({"ok": False, "msg": "params error"}), 400
        if role_want == "admin" and not is_admin:
            return jsonify({"ok": False, "msg": "not admin"}), 403

    token = create_access_token({"id": row[0]["id"], "username": row[0]["username"], "role": db_role})
    refresh_token = issue_refresh_token(row[0]["id"])
    audit_log(
        "auth.login.success",
        target_type="auth",
        target_id=row[0]["id"],
        detail={"role": db_role},
        actor={"id": row[0]["id"], "username": row[0]["username"], "role": db_role},
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "userId": row[0]["id"],
                "username": row[0]["username"],
                "role": db_role,
                "token": token,
                "refreshToken": refresh_token,
                "expiresIn": JWT_EXPIRE_SECONDS,
            },
        }
    )


@app.post("/register")
def register():
    data = request.get_json(force=True) or {}
    username = (data.get("username") or "").strip()
    password = str(data.get("password") or "")
    ip = get_client_ip()

    limited = enforce_rate_limit("register", f"{ip}:{username.lower()}")
    if limited:
        return limited

    if not username:
        audit_log(
            "auth.register.failed",
            target_type="auth",
            detail={"reason": "username_required"},
            actor={"username": username},
        )
        return jsonify({"ok": False, "msg": "username required"}), 400
    if len(password) < 6:
        audit_log(
            "auth.register.failed",
            target_type="auth",
            target_id=username,
            detail={"reason": "password_too_short"},
            actor={"username": username},
        )
        return jsonify({"ok": False, "msg": "password must be at least 6 chars"}), 400

    row = query("SELECT id FROM user WHERE username=%s LIMIT 1", (username,))
    if row:
        audit_log(
            "auth.register.failed",
            target_type="auth",
            target_id=username,
            detail={"reason": "user_exists"},
            actor={"username": username},
        )
        return jsonify({"ok": False, "msg": "user exists"}), 409

    new_id = execute_insert(
        "INSERT INTO user (username, role, password_hash) VALUES (%s, %s, %s)",
        (username, "student", generate_password_hash(password)),
    )
    token = create_access_token({"id": new_id, "username": username, "role": "student"})
    refresh_token = issue_refresh_token(new_id)
    audit_log(
        "auth.register.success",
        target_type="auth",
        target_id=new_id,
        detail={"role": "student"},
        actor={"id": new_id, "username": username, "role": "student"},
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "userId": new_id,
                "username": username,
                "role": "student",
                "token": token,
                "refreshToken": refresh_token,
                "expiresIn": JWT_EXPIRE_SECONDS,
            },
        }
    )


@app.post("/auth/refresh")
def refresh_access_token():
    data = request.get_json(force=True) or {}
    refresh_token = str(data.get("refreshToken") or "").strip()
    ip = get_client_ip()
    limited = enforce_rate_limit("refresh", f"{ip}:{hash_refresh_token(refresh_token)[:12] if refresh_token else 'none'}")
    if limited:
        return limited
    if not refresh_token:
        audit_log("auth.refresh.failed", target_type="auth", detail={"reason": "refresh_token_required"})
        return jsonify({"ok": False, "msg": "refreshToken required"}), 400

    row = get_refresh_token_row(refresh_token)
    if not is_refresh_token_valid(row):
        audit_log("auth.refresh.failed", target_type="auth", detail={"reason": "invalid_refresh_token"})
        return jsonify({"ok": False, "msg": "invalid refresh token"}), 401

    user_rows = query("SELECT id, username, role FROM user WHERE id=%s LIMIT 1", (row["userId"],))
    if not user_rows:
        revoke_refresh_token(refresh_token)
        audit_log("auth.refresh.failed", target_type="auth", detail={"reason": "user_not_found"})
        return jsonify({"ok": False, "msg": "invalid refresh token"}), 401
    user = user_rows[0]

    new_refresh = issue_refresh_token(user["id"])
    revoke_refresh_token(refresh_token, replaced_by_hash=hash_refresh_token(new_refresh))
    access_token = create_access_token({"id": user["id"], "username": user["username"], "role": user["role"]})
    audit_log(
        "auth.refresh.success",
        target_type="auth",
        target_id=user["id"],
        detail={"role": user["role"]},
        actor={"id": user["id"], "username": user["username"], "role": user["role"]},
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "userId": user["id"],
                "username": user["username"],
                "role": user["role"],
                "token": access_token,
                "refreshToken": new_refresh,
                "expiresIn": JWT_EXPIRE_SECONDS,
            },
        }
    )


@app.post("/auth/logout")
@auth_required()
def logout():
    data = request.get_json(force=True) or {}
    refresh_token = str(data.get("refreshToken") or "").strip()
    if refresh_token:
        revoke_refresh_token(refresh_token)
    return jsonify({"ok": True})


@app.post("/auth/change-password")
@auth_required()
def change_password():
    data = request.get_json(force=True) or {}
    old_password = str(data.get("oldPassword") or "")
    new_password = str(data.get("newPassword") or "")
    uid = g.current_user["id"]

    limited = enforce_rate_limit("change_password", f"{get_client_ip()}:{uid}")
    if limited:
        return limited

    if not old_password or len(new_password) < 6:
        audit_log(
            "auth.change_password.failed",
            target_type="auth",
            target_id=uid,
            detail={"reason": "params_error"},
        )
        return jsonify({"ok": False, "msg": "params error"}), 400

    row = query("SELECT id, password_hash AS passwordHash FROM user WHERE id=%s LIMIT 1", (uid,))
    if not row:
        audit_log(
            "auth.change_password.failed",
            target_type="auth",
            target_id=uid,
            detail={"reason": "user_not_found"},
        )
        return jsonify({"ok": False, "msg": "user not found"}), 404
    password_hash = (row[0].get("passwordHash") or "").strip()
    if not password_hash or not check_password_hash(password_hash, old_password):
        audit_log(
            "auth.change_password.failed",
            target_type="auth",
            target_id=uid,
            detail={"reason": "old_password_incorrect"},
        )
        return jsonify({"ok": False, "msg": "old password incorrect"}), 400

    execute("UPDATE user SET password_hash=%s WHERE id=%s", (generate_password_hash(new_password), uid))
    execute("UPDATE auth_refresh_token SET revoked_at=%s WHERE user_id=%s AND revoked_at IS NULL", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uid))
    audit_log("auth.change_password.success", target_type="auth", target_id=uid)
    return jsonify({"ok": True})


@app.post("/auth/clear-records")
@auth_required()
def clear_records():
    data = request.get_json(force=True) or {}
    scope = str(data.get("scope") or "mine").strip().lower()
    if scope not in ("mine", "all"):
        return jsonify({"ok": False, "msg": "invalid scope"}), 400

    current_user = g.current_user or {}
    username = str(current_user.get("username") or "").strip()
    role = str(current_user.get("role") or "").strip()
    if not username:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401
    if scope == "all" and role != "admin":
        return jsonify({"ok": False, "msg": "forbidden"}), 403

    try:
        def _tx(cur):
            if scope == "all":
                cur.execute("SELECT COUNT(*) AS cnt FROM reservation")
                reservation_before = int((cur.fetchone() or {}).get("cnt") or 0)
                cur.execute("DELETE FROM reservation")
                reservation_deleted = int(cur.rowcount or 0)

                cur.execute("SELECT COUNT(*) AS cnt FROM lost_found")
                lostfound_before = int((cur.fetchone() or {}).get("cnt") or 0)
                cur.execute("DELETE FROM lost_found")
                lostfound_deleted = int(cur.rowcount or 0)

                return {
                    "scope": "all",
                    "reservationBefore": reservation_before,
                    "reservationDeleted": reservation_deleted,
                    "lostfoundBefore": lostfound_before,
                    "lostfoundDeleted": lostfound_deleted,
                    "claimApplyCleared": 0,
                }

            cur.execute("SELECT COUNT(*) AS cnt FROM reservation WHERE user_name=%s", (username,))
            reservation_before = int((cur.fetchone() or {}).get("cnt") or 0)
            cur.execute("DELETE FROM reservation WHERE user_name=%s", (username,))
            reservation_deleted = int(cur.rowcount or 0)

            cur.execute("SELECT COUNT(*) AS cnt FROM lost_found WHERE owner=%s", (username,))
            lostfound_before = int((cur.fetchone() or {}).get("cnt") or 0)
            cur.execute("DELETE FROM lost_found WHERE owner=%s", (username,))
            lostfound_deleted = int(cur.rowcount or 0)

            # Clear this user's pending/rejected claim applications on records owned by others.
            cur.execute(
                """
                UPDATE lost_found
                SET claim_apply_status='',
                    claim_apply_user='',
                    claim_apply_reason='',
                    claim_apply_student_id='',
                    claim_apply_name='',
                    claim_apply_class='',
                    claim_apply_at=NULL,
                    claim_reviewed_by='',
                    claim_reviewed_at=NULL,
                    claim_review_note=''
                WHERE claim_apply_user=%s
                  AND owner<>%s
                  AND claim_apply_status IN ('pending','rejected')
                """,
                (username, username),
            )
            claim_apply_cleared = int(cur.rowcount or 0)

            return {
                "scope": "mine",
                "reservationBefore": reservation_before,
                "reservationDeleted": reservation_deleted,
                "lostfoundBefore": lostfound_before,
                "lostfoundDeleted": lostfound_deleted,
                "claimApplyCleared": claim_apply_cleared,
            }

        result = run_in_transaction(_tx)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    audit_log(
        "auth.clear_records",
        target_type="data",
        target_id=(scope if scope == "all" else username),
        detail={
            "scope": result.get("scope"),
            "reservationDeleted": int(result.get("reservationDeleted") or 0),
            "lostfoundDeleted": int(result.get("lostfoundDeleted") or 0),
            "claimApplyCleared": int(result.get("claimApplyCleared") or 0),
        },
        actor={"id": current_user.get("id"), "username": username, "role": role},
    )
    return jsonify({"ok": True, "data": result})


@app.get("/users")
@auth_required(roles=["admin"])
def list_users():
    rows = query("SELECT id, username, role FROM user ORDER BY id ASC")
    return jsonify(rows)


@app.get("/audit-logs")
@auth_required(roles=["admin"])
def list_audit_logs():
    action = request.args.get("action", "").strip()
    operator = request.args.get("operator", "").strip()
    target_type = request.args.get("targetType", "").strip()
    start_date = request.args.get("startDate", "").strip()
    end_date = request.args.get("endDate", "").strip()
    page_raw = request.args.get("page", "1").strip()
    page_size_raw = request.args.get("pageSize", request.args.get("limit", "50")).strip()

    try:
        page = int(page_raw)
    except ValueError:
        page = 1
    try:
        page_size = int(page_size_raw)
    except ValueError:
        page_size = 50

    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    offset = (page - 1) * page_size

    rows, total, err = fetch_audit_logs(
        action=action,
        operator=operator,
        target_type=target_type,
        start_date=start_date,
        end_date=end_date,
        limit=page_size,
        offset=offset,
        with_total=True,
    )
    if err:
        return jsonify({"ok": False, "msg": err}), 400

    for row in rows:
        raw = (row.get("detailJson") or "").strip()
        if raw:
            try:
                row["detail"] = json.loads(raw)
            except Exception:
                row["detail"] = {"raw": raw}
        else:
            row["detail"] = {}
        row["createdAt"] = _to_text_time(row.get("createdAt"))
        row.pop("detailJson", None)

    return jsonify(
        {
            "ok": True,
            "data": rows,
            "meta": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "hasMore": (offset + len(rows)) < int(total or 0),
            },
        }
    )


@app.get("/audit-logs/export")
@auth_required(roles=["admin"])
def export_audit_logs():
    action = request.args.get("action", "").strip()
    operator = request.args.get("operator", "").strip()
    target_type = request.args.get("targetType", "").strip()
    start_date = request.args.get("startDate", "").strip()
    end_date = request.args.get("endDate", "").strip()
    limit_raw = request.args.get("limit", "2000").strip()

    try:
        limit = int(limit_raw)
    except ValueError:
        limit = 2000
    limit = max(1, min(limit, 5000))

    rows, _, err = fetch_audit_logs(
        action=action,
        operator=operator,
        target_type=target_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=0,
        with_total=False,
    )
    if err:
        return jsonify({"ok": False, "msg": err}), 400

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "created_at",
        "action",
        "operator_id",
        "operator_name",
        "operator_role",
        "target_type",
        "target_id",
        "ip",
        "detail_json",
    ])
    for r in rows:
        writer.writerow([
            r.get("id"),
            _to_text_time(r.get("createdAt")),
            r.get("action"),
            r.get("operatorId"),
            r.get("operatorName"),
            r.get("operatorRole"),
            r.get("targetType"),
            r.get("targetId"),
            r.get("ip"),
            r.get("detailJson") or "",
        ])
    csv_data = output.getvalue()
    return (
        csv_data,
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": "attachment; filename=audit_logs.csv",
        },
    )


@app.post("/users/<int:uid>/promote")
@auth_required(roles=["admin"])
def promote_user(uid):
    operator = (g.current_user.get("username") or "").strip()
    if operator != "admin1":
        return jsonify({"ok": False, "msg": "forbidden"}), 403

    row = query("SELECT id, username, role FROM user WHERE id=%s LIMIT 1", (uid,))
    if not row:
        return jsonify({"ok": False, "msg": "user not found"}), 404

    if row[0]["role"] == "admin":
        return jsonify({"ok": True, "msg": "already admin"})

    execute("UPDATE user SET role='admin' WHERE id=%s", (uid,))
    audit_log(
        "admin.user.promote",
        target_type="user",
        target_id=uid,
        detail={"fromRole": row[0]["role"], "toRole": "admin", "targetUsername": row[0]["username"]},
    )
    return jsonify({"ok": True})


@app.post("/users/<int:uid>/demote")
@auth_required(roles=["admin"])
def demote_user(uid):
    operator = (g.current_user.get("username") or "").strip()
    if operator != "admin1":
        return jsonify({"ok": False, "msg": "forbidden"}), 403

    row = query("SELECT id, username, role FROM user WHERE id=%s LIMIT 1", (uid,))
    if not row:
        return jsonify({"ok": False, "msg": "user not found"}), 404

    if row[0]["role"] != "admin":
        return jsonify({"ok": True, "msg": "already non-admin"})

    execute("UPDATE user SET role='student' WHERE id=%s", (uid,))
    audit_log(
        "admin.user.demote",
        target_type="user",
        target_id=uid,
        detail={"fromRole": row[0]["role"], "toRole": "student", "targetUsername": row[0]["username"]},
    )
    return jsonify({"ok": True})


