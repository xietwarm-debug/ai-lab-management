from . import core as _core

for _k, _v in _core.__dict__.items():
    if _k.startswith("__"):
        continue
    globals()[_k] = _v

del _k, _v, _core

USER_ROLES = {"student", "teacher", "admin"}
ROLE_ALIAS = {"user": "student"}
DEFAULT_ADMIN_RESET_PASSWORD = str(os.getenv("ADMIN_RESET_PASSWORD_DEFAULT", "123456") or "123456")
KNOWLEDGE_DOC_STATUS_SET = {"draft", "active", "disabled"}


def _normalize_role(value):
    role = str(value or "").strip().lower()
    return ROLE_ALIAS.get(role, role)


def _normalize_bool_filter(value, field_name):
    text = str(value or "").strip().lower()
    if not text or text == "all":
        return None
    if text in ("1", "true", "yes", "on"):
        return 1
    if text in ("0", "false", "no", "off"):
        return 0
    raise BizError(f"invalid {field_name}", 400)


def _normalize_non_negative_int(value, field_name, default_value=0, max_value=9999):
    if value in (None, ""):
        return int(default_value)
    try:
        num = int(value)
    except (TypeError, ValueError):
        raise BizError(f"invalid {field_name}", 400)
    if num < 0:
        raise BizError(f"invalid {field_name}", 400)
    if num > int(max_value):
        raise BizError(f"invalid {field_name}", 400)
    return num


def _normalize_optional_int(value, field_name, min_value=0, max_value=9999):
    if value in (None, ""):
        return None
    try:
        num = int(value)
    except (TypeError, ValueError):
        raise BizError(f"invalid {field_name}", 400)
    if num < int(min_value) or num > int(max_value):
        raise BizError(f"invalid {field_name}", 400)
    return num


def _coerce_bool(value, field_name, default_value=False):
    if value in (None, ""):
        return bool(default_value)
    if isinstance(value, bool):
        return bool(value)
    text = str(value or "").strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False
    raise BizError(f"invalid {field_name}", 400)


def _build_in_placeholders(items):
    arr = [x for x in (items or []) if x is not None]
    if not arr:
        return "", []
    return ",".join(["%s"] * len(arr)), arr


def _normalize_usernames(value):
    out = []
    if not isinstance(value, list):
        return out
    for item in value:
        text = str(item or "").strip()
        if not text:
            continue
        out.append(text)
    return out


def _normalize_ids(value):
    out = []
    if not isinstance(value, list):
        return out
    for item in value:
        num = _to_int_or_none(item)
        if num is None or int(num) <= 0:
            continue
        out.append(int(num))
    return out


def _normalize_device_name(value):
    return str(value or "").strip()[:128]


def _normalize_knowledge_doc_payload(payload, *, allow_partial=False):
    data = payload if isinstance(payload, dict) else {}
    title = str(data.get("title") or "").strip()
    content = str(data.get("content") or data.get("sourceContent") or "").strip()
    category = _knowledge_normalize_category(data.get("category"), default_value="other")
    scope_role = _knowledge_normalize_scope_role(data.get("scopeRole"), default_value="all")
    status = str(data.get("status") or ("draft" if not allow_partial else "")).strip().lower()
    source_url = str(data.get("sourceUrl") or "").strip()[:500]
    if status and status not in KNOWLEDGE_DOC_STATUS_SET:
        raise BizError("invalid status", 400)
    if not allow_partial or "title" in data:
        if not title:
            raise BizError("title required", 400)
        if len(title) > 200:
            raise BizError("title too long", 400)
    if not allow_partial or ("content" in data or "sourceContent" in data):
        if not content:
            raise BizError("content required", 400)
    if len(content) > 200000:
        raise BizError("content too long", 400)
    return {
        "title": title[:200],
        "content": content,
        "category": category,
        "scopeRole": scope_role,
        "status": status or "draft",
        "sourceUrl": source_url,
    }


def _format_knowledge_document_row(row):
    item = dict(row or {})
    return {
        "id": int(item.get("id") or 0),
        "title": str(item.get("title") or "").strip(),
        "category": str(item.get("category") or "").strip() or "other",
        "scopeRole": str(item.get("scopeRole") or "").strip() or "all",
        "status": str(item.get("status") or "").strip() or "draft",
        "sourceType": str(item.get("sourceType") or "").strip() or "text",
        "sourceUrl": str(item.get("sourceUrl") or "").strip(),
        "summary": str(item.get("summary") or "").strip(),
        "keywords": str(item.get("keywords") or "").strip(),
        "chunkCount": int(item.get("chunkCount") or 0),
        "lastIndexedAt": _to_text_time(item.get("lastIndexedAt")),
        "uploaderId": _to_int_or_none(item.get("uploaderId")),
        "uploaderName": str(item.get("uploaderName") or "").strip(),
        "createdAt": _to_text_time(item.get("createdAt")),
        "updatedAt": _to_text_time(item.get("updatedAt")),
    }


def _guess_device_name(user_agent):
    ua = str(user_agent or "").strip().lower()
    if not ua:
        return "未知设备"

    platform = "未知平台"
    if "windows" in ua:
        platform = "Windows"
    elif "macintosh" in ua or "mac os" in ua:
        platform = "macOS"
    elif "android" in ua:
        platform = "Android"
    elif "iphone" in ua or "ipad" in ua or "ios" in ua:
        platform = "iOS"
    elif "linux" in ua:
        platform = "Linux"

    runtime = "客户端"
    if "micromessenger" in ua:
        runtime = "微信"
    elif "uni-app" in ua or "uniapp" in ua:
        runtime = "UniApp"
    elif "edg/" in ua or "edge/" in ua:
        runtime = "Edge"
    elif "chrome/" in ua:
        runtime = "Chrome"
    elif "safari/" in ua and "chrome/" not in ua:
        runtime = "Safari"
    elif "firefox/" in ua:
        runtime = "Firefox"

    return f"{platform} · {runtime}"


def _resolve_device_name(raw_name, user_agent):
    name = _normalize_device_name(raw_name)
    return name if name else _guess_device_name(user_agent)


def _mask_phone(text):
    phone = str(text or "").strip()
    if len(phone) <= 3:
        return phone
    if len(phone) <= 7:
        return f"{phone[:3]}****"
    return f"{phone[:3]}****{phone[-4:]}"


def _mask_email(text):
    email = str(text or "").strip()
    if not email or "@" not in email:
        return email
    name, domain = email.split("@", 1)
    if len(name) <= 1:
        return f"*@" + domain
    if len(name) == 2:
        return f"{name[:1]}*@" + domain
    return f"{name[:1]}***{name[-1]}@" + domain


def _list_login_devices_payload(uid, current_refresh_token=""):
    user_id = int(uid or 0)
    if user_id <= 0:
        return []

    now = datetime.now()
    now_text = now.strftime("%Y-%m-%d %H:%M:%S")
    current_hash = ""
    token_text = str(current_refresh_token or "").strip()
    if token_text:
        current_hash = hash_refresh_token(token_text)
        execute(
            """
            UPDATE auth_refresh_token
            SET last_seen_at=%s, login_ip=%s
            WHERE user_id=%s
              AND token_hash=%s
              AND revoked_at IS NULL
            """,
            (now_text, get_client_ip(), user_id, current_hash),
        )

    rows = query(
        """
        SELECT id,
               token_hash AS tokenHash,
               device_name AS deviceName,
               user_agent AS userAgent,
               login_ip AS loginIp,
               created_at AS createdAt,
               last_seen_at AS lastSeenAt,
               expires_at AS expiresAt
        FROM auth_refresh_token
        WHERE user_id=%s
          AND revoked_at IS NULL
          AND expires_at > %s
        ORDER BY COALESCE(last_seen_at, created_at) DESC, id DESC
        LIMIT 30
        """,
        (user_id, now_text),
    )

    items = []
    for row in rows:
        data = row or {}
        token_hash = str(data.get("tokenHash") or "").strip()
        ua = str(data.get("userAgent") or "").strip()
        raw_name = str(data.get("deviceName") or "").strip()
        expires_at = data.get("expiresAt")
        expires_dt = _to_datetime(expires_at)
        if expires_dt <= now:
            continue
        item = {
            "id": int(data.get("id") or 0),
            "deviceName": _resolve_device_name(raw_name, ua),
            "loginIp": str(data.get("loginIp") or "").strip(),
            "createdAt": _to_text_time(data.get("createdAt")),
            "lastSeenAt": _to_text_time(data.get("lastSeenAt") or data.get("createdAt")),
            "expiresAt": _to_text_time(expires_at),
            "isCurrent": bool(current_hash and token_hash and token_hash == current_hash),
        }
        items.append(item)
    return items


def _split_import_text_rows(text):
    lines = str(text or "").splitlines()
    rows = []
    for raw in lines:
        line = str(raw or "").strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        parts = [x.strip() for x in re.split(r"[\t,，]", line)]
        first = str(parts[0] if parts else "").strip().lower()
        if first in ("username", "user", "用户名"):
            continue
        while len(parts) < 7:
            parts.append("")
        rows.append(
            {
                "username": parts[0],
                "password": parts[1],
                "role": parts[2],
                "className": parts[3],
                "graduationYear": parts[4],
                "nickname": parts[5],
                "phone": parts[6],
            }
        )
    return rows


def _format_user_admin_row(row):
    data = row or {}
    is_active = int(data.get("isActive") or 0)
    is_frozen = int(data.get("isFrozen") or 0)
    violation_count = int(data.get("violationCount") or 0)
    return {
        "id": int(data.get("id") or 0),
        "username": str(data.get("username") or "").strip(),
        "role": str(data.get("role") or "").strip(),
        "nickname": str(data.get("nickname") or "").strip(),
        "phone": str(data.get("phone") or "").strip(),
        "avatarUrl": str(data.get("avatarUrl") or "").strip(),
        "className": str(data.get("className") or "").strip(),
        "graduationYear": int(data.get("graduationYear") or 0),
        "isActive": 1 if is_active == 1 else 0,
        "isFrozen": 1 if is_frozen == 1 else 0,
        "activeState": "frozen" if is_frozen == 1 else "active" if is_active == 1 else "inactive",
        "lastLoginAt": _to_text_time(data.get("lastLoginAt")),
        "violationCount": max(0, violation_count),
        "hasViolation": bool(violation_count > 0),
    }


def _query_admin_user_row(uid):
    rows = query(
        """
        SELECT u.id,
               u.username,
               u.role,
               u.nickname,
               u.phone,
               u.avatar_url AS avatarUrl,
               u.class_name AS className,
               u.graduation_year AS graduationYear,
               u.is_active AS isActive,
               u.is_frozen AS isFrozen,
               u.last_login_at AS lastLoginAt,
               (
                   SELECT COUNT(*)
                   FROM reservation r
                   WHERE r.user_name=u.username
                     AND r.status='rejected'
               ) + (
                   SELECT COUNT(*)
                   FROM lost_found lf
                   WHERE lf.claim_apply_user=u.username
                     AND lf.claim_apply_status='rejected'
               ) + (
                   SELECT COUNT(*)
                   FROM equipment_borrow_request br
                   WHERE br.applicant_user_name=u.username
                     AND (
                         (br.status='approved' AND br.returned_at IS NULL AND br.expected_return_at IS NOT NULL AND br.expected_return_at < NOW())
                         OR
                         (br.status='returned' AND br.returned_at IS NOT NULL AND br.expected_return_at IS NOT NULL AND br.returned_at > br.expected_return_at)
                     )
               ) AS violationCount
        FROM user u
        WHERE u.id=%s
        LIMIT 1
        """,
        (uid,),
    )
    return rows[0] if rows else None


def _assert_user_editable(target_row, current_user, block_self=True):
    target = target_row or {}
    actor = current_user or {}
    target_id = int(target.get("id") or 0)
    target_username = str(target.get("username") or "").strip()
    actor_id = int(actor.get("id") or 0)
    if target_username == "admin1":
        raise BizError("admin1 cannot be modified", 409)
    if block_self and actor_id > 0 and target_id == actor_id:
        raise BizError("cannot modify yourself", 409)


def _normalize_todo_sort(value):
    text = str(value or "").strip()
    return text if text in ("priority", "createdAt", "deadline") else "priority"


def _normalize_todo_order(value):
    text = str(value or "").strip().lower()
    return "asc" if text == "asc" else "desc"


def _todo_priority_level(score):
    s = int(score or 0)
    if s >= 90:
        return "P0"
    if s >= 75:
        return "P1"
    if s >= 60:
        return "P2"
    return "P3"


def _sort_todo_items(items, sort_by="priority", sort_order="desc"):
    rows = list(items or [])
    if not rows:
        return rows
    by = _normalize_todo_sort(sort_by)
    order = _normalize_todo_order(sort_order)
    if by == "priority":
        if order == "asc":
            rows.sort(
                key=lambda x: (
                    int(x.get("priorityScore") or 0),
                    _to_datetime(x.get("deadlineAt") or x.get("createdAt")),
                    _to_datetime(x.get("createdAt")),
                )
            )
        else:
            rows.sort(
                key=lambda x: (
                    -int(x.get("priorityScore") or 0),
                    _to_datetime(x.get("deadlineAt") or x.get("createdAt")),
                    _to_datetime(x.get("createdAt")),
                )
            )
        return rows

    if by == "createdAt":
        rows.sort(key=lambda x: _to_datetime(x.get("createdAt")), reverse=(order == "desc"))
        return rows

    rows.sort(key=lambda x: _to_datetime(x.get("deadlineAt") or x.get("createdAt")), reverse=(order == "desc"))
    return rows


def _build_todo_card(key, title, desc, jump_url, total, timeout_count, items, batch_action):
    return {
        "key": str(key or ""),
        "title": str(title or ""),
        "description": str(desc or ""),
        "jumpUrl": str(jump_url or ""),
        "total": int(total or 0),
        "timeoutCount": int(timeout_count or 0),
        "items": list(items or []),
        "batchAction": str(batch_action or ""),
    }


def _update_user_role(uid, target_role, action):
    role = _normalize_role(target_role)
    if role not in USER_ROLES:
        raise BizError("invalid role", 400)

    target_user = _query_admin_user_row(uid)
    if not target_user:
        raise BizError("user not found", 404)

    current_user = g.current_user or {}
    old_role = str(target_user.get("role") or "").strip()
    username = str(target_user.get("username") or "").strip()

    _assert_user_editable(target_user, current_user, block_self=True)

    if old_role == role:
        return {"id": int(uid), "role": role, "changed": False}

    execute("UPDATE user SET role=%s WHERE id=%s", (role, uid))
    audit_log(
        action,
        target_type="user",
        target_id=uid,
        detail={"fromRole": old_role, "toRole": role, "targetUsername": username},
        actor={
            "id": current_user.get("id"),
            "username": current_user.get("username"),
            "role": current_user.get("role"),
        },
    )
    return {"id": int(uid), "role": role, "changed": True}

@app.get("/health")
def health():
    return jsonify({"ok": True, "time": datetime.now().isoformat(timespec="seconds")})


@app.get("/reservation-rules")
@auth_required()
def reservation_rules():
    lab_id = _to_int_or_none(request.args.get("labId") or request.args.get("lab_id"))
    lab_name = str(request.args.get("labName") or request.args.get("lab_name") or "").strip()
    return jsonify({"ok": True, "data": get_reservation_rules_payload(lab_id=lab_id, lab_name=lab_name)})


@app.get("/admin/reservation-rules")
@auth_required(roles=["admin"])
def get_admin_reservation_rules():
    return jsonify({"ok": True, "data": get_reservation_rules_admin_payload()})


@app.post("/admin/reservation-rules")
@auth_required(roles=["admin"])
def save_admin_reservation_rules():
    data = request.get_json(force=True) or {}
    actor = g.current_user or {}
    operator = str(actor.get("username") or "").strip()

    normalized = save_reservation_rule_config(data, updated_by=operator)
    global_scope = normalized.get("global") if isinstance(normalized.get("global"), dict) else {}
    lab_rules = normalized.get("labRules") if isinstance(normalized.get("labRules"), list) else []
    audit_log(
        "admin.reservation_rules.update",
        target_type="reservation_rule",
        target_id="global",
        detail={
            "minDaysAhead": global_scope.get("minDaysAhead"),
            "maxDaysAhead": global_scope.get("maxDaysAhead"),
            "slotCount": len(global_scope.get("slots") or []),
            "disabledDateCount": len(global_scope.get("disabledDates") or []),
            "blackoutCount": len(global_scope.get("blackoutSlots") or []),
            "approvalMode": (global_scope.get("approval") or {}).get("mode"),
            "labRuleCount": len(lab_rules),
        },
        actor={"id": actor.get("id"), "username": operator, "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": get_reservation_rules_admin_payload()})


@app.get("/me/profile")
@auth_required()
def get_my_profile():
    uid = int((g.current_user or {}).get("id") or 0)
    if uid <= 0:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401

    row = get_user_profile_row_by_id(uid)
    if not row:
        return jsonify({"ok": False, "msg": "user not found"}), 404
    return jsonify({"ok": True, "data": format_user_profile_payload(row)})


@app.post("/me/profile")
@auth_required()
def update_my_profile():
    uid = int((g.current_user or {}).get("id") or 0)
    if uid <= 0:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401

    payload = request.get_json(force=True) or {}
    has_nickname = "nickname" in payload
    has_phone = "phone" in payload
    has_email = "email" in payload
    has_class_name = ("className" in payload) or ("class_name" in payload)
    has_student_no = ("studentNo" in payload) or ("student_no" in payload)
    has_job_no = ("jobNo" in payload) or ("job_no" in payload)
    has_avatar = ("avatarUrl" in payload) or ("avatar" in payload) or ("avatar_url" in payload)

    if not (has_nickname or has_phone or has_email or has_class_name or has_student_no or has_job_no or has_avatar):
        return jsonify({"ok": False, "msg": "nothing to update"}), 400

    try:
        updated = update_user_profile_fields(
            uid,
            nickname=(payload.get("nickname") if has_nickname else None),
            phone=(payload.get("phone") if has_phone else None),
            email=(payload.get("email") if has_email else None),
            class_name=(payload.get("className") if "className" in payload else payload.get("class_name") if has_class_name else None),
            student_no=(payload.get("studentNo") if "studentNo" in payload else payload.get("student_no") if has_student_no else None),
            job_no=(payload.get("jobNo") if "jobNo" in payload else payload.get("job_no") if has_job_no else None),
            avatar_url=(
                payload.get("avatarUrl")
                if "avatarUrl" in payload
                else payload.get("avatar")
                if "avatar" in payload
                else payload.get("avatar_url")
                if "avatar_url" in payload
                else None
            ),
        )
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    changed_fields = []
    if has_nickname:
        changed_fields.append("nickname")
    if has_phone:
        changed_fields.append("phone")
    if has_email:
        changed_fields.append("email")
    if has_class_name:
        changed_fields.append("className")
    if has_student_no:
        changed_fields.append("studentNo")
    if has_job_no:
        changed_fields.append("jobNo")
    if has_avatar:
        changed_fields.append("avatarUrl")

    actor = g.current_user or {}
    audit_log(
        "user.profile.update",
        target_type="user",
        target_id=uid,
        detail={"fields": changed_fields},
        actor={
            "id": actor.get("id"),
            "username": actor.get("username"),
            "role": actor.get("role"),
        },
    )
    return jsonify({"ok": True, "data": updated})


@app.get("/auth/security")
@auth_required()
def get_auth_security():
    uid = int((g.current_user or {}).get("id") or 0)
    if uid <= 0:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401

    rows = query("SELECT phone, email FROM user WHERE id=%s LIMIT 1", (uid,))
    if not rows:
        return jsonify({"ok": False, "msg": "user not found"}), 404

    row = rows[0] or {}
    phone = str(row.get("phone") or "").strip()
    email = str(row.get("email") or "").strip()
    current_refresh_token = str(request.args.get("currentRefreshToken") or "").strip()
    devices = _list_login_devices_payload(uid, current_refresh_token=current_refresh_token)
    current_device = next((x for x in devices if x.get("isCurrent")), None) or {}

    return jsonify(
        {
            "ok": True,
            "data": {
                "phone": phone,
                "phoneMasked": _mask_phone(phone),
                "phoneBound": bool(phone),
                "email": email,
                "emailMasked": _mask_email(email),
                "emailBound": bool(email),
                "devices": devices,
                "deviceCount": len(devices),
                "currentDeviceId": int(current_device.get("id") or 0),
            },
        }
    )


@app.post("/auth/bind-phone")
@auth_required()
def bind_phone():
    data = request.get_json(force=True) or {}
    phone = _normalize_profile_phone(data.get("phone"))
    if not phone:
        return jsonify({"ok": False, "msg": "phone required"}), 400

    uid = int((g.current_user or {}).get("id") or 0)
    if uid <= 0:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401

    execute("UPDATE user SET phone=%s WHERE id=%s", (phone, uid))
    actor = g.current_user or {}
    audit_log(
        "auth.bind_phone",
        target_type="user",
        target_id=uid,
        detail={"phoneMasked": _mask_phone(phone)},
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": {"phone": phone, "phoneMasked": _mask_phone(phone), "phoneBound": True}})


@app.post("/auth/bind-email")
@auth_required()
def bind_email():
    data = request.get_json(force=True) or {}
    email = _normalize_profile_email(data.get("email"))
    if not email:
        return jsonify({"ok": False, "msg": "email required"}), 400

    uid = int((g.current_user or {}).get("id") or 0)
    if uid <= 0:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401

    execute("UPDATE user SET email=%s WHERE id=%s", (email, uid))
    actor = g.current_user or {}
    audit_log(
        "auth.bind_email",
        target_type="user",
        target_id=uid,
        detail={"emailMasked": _mask_email(email)},
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": {"email": email, "emailMasked": _mask_email(email), "emailBound": True}})


@app.get("/auth/login-devices")
@auth_required()
def list_login_devices():
    uid = int((g.current_user or {}).get("id") or 0)
    if uid <= 0:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401
    current_refresh_token = str(request.args.get("currentRefreshToken") or "").strip()
    items = _list_login_devices_payload(uid, current_refresh_token=current_refresh_token)
    return jsonify({"ok": True, "data": {"items": items, "total": len(items)}})


@app.post("/auth/login-devices/<int:device_id>/revoke")
@auth_required()
def revoke_login_device(device_id):
    uid = int((g.current_user or {}).get("id") or 0)
    if uid <= 0:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401

    data = request.get_json(force=True) or {}
    current_refresh_token = str(data.get("currentRefreshToken") or "").strip()
    current_hash = hash_refresh_token(current_refresh_token) if current_refresh_token else ""

    rows = query(
        """
        SELECT id,
               token_hash AS tokenHash,
               device_name AS deviceName,
               user_agent AS userAgent,
               revoked_at AS revokedAt,
               expires_at AS expiresAt
        FROM auth_refresh_token
        WHERE id=%s
          AND user_id=%s
        LIMIT 1
        """,
        (device_id, uid),
    )
    if not rows:
        return jsonify({"ok": False, "msg": "device not found"}), 404

    row = rows[0] or {}
    target_hash = str(row.get("tokenHash") or "").strip()
    if current_hash and target_hash and current_hash == target_hash:
        return jsonify({"ok": False, "msg": "cannot revoke current device"}), 400
    if row.get("revokedAt"):
        return jsonify({"ok": True, "data": {"revoked": False, "reason": "already_revoked"}})
    if _to_datetime(row.get("expiresAt")) <= datetime.now():
        return jsonify({"ok": True, "data": {"revoked": False, "reason": "already_expired"}})

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute(
        "UPDATE auth_refresh_token SET revoked_at=%s WHERE id=%s AND user_id=%s AND revoked_at IS NULL",
        (now_text, device_id, uid),
    )
    actor = g.current_user or {}
    audit_log(
        "auth.login_device.revoke",
        target_type="auth_refresh_token",
        target_id=device_id,
        detail={"deviceName": _resolve_device_name(row.get("deviceName"), row.get("userAgent"))},
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": {"revoked": True}})


@app.post("/auth/login-devices/revoke-others")
@auth_required()
def revoke_login_devices_others():
    uid = int((g.current_user or {}).get("id") or 0)
    if uid <= 0:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401

    data = request.get_json(force=True) or {}
    current_refresh_token = str(data.get("currentRefreshToken") or "").strip()
    current_hash = hash_refresh_token(current_refresh_token) if current_refresh_token else ""
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    where_sql = "user_id=%s AND revoked_at IS NULL AND expires_at>%s"
    where_params = [uid, now_text]
    if current_hash:
        where_sql += " AND token_hash<>%s"
        where_params.append(current_hash)

    def _tx(cur):
        cur.execute(f"SELECT COUNT(*) AS cnt FROM auth_refresh_token WHERE {where_sql}", tuple(where_params))
        before = int((cur.fetchone() or {}).get("cnt") or 0)
        cur.execute(
            f"UPDATE auth_refresh_token SET revoked_at=%s WHERE {where_sql}",
            tuple([now_text] + where_params),
        )
        revoked = int(cur.rowcount or 0)
        return {"before": before, "revoked": revoked}

    result = run_in_transaction(_tx)
    actor = g.current_user or {}
    audit_log(
        "auth.login_device.revoke_others",
        target_type="auth_refresh_token",
        target_id=uid,
        detail={"candidateCount": int(result.get("before") or 0), "revokedCount": int(result.get("revoked") or 0)},
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": {"revokedCount": int(result.get("revoked") or 0)}})


def _normalize_subscription_bool(raw_value, default_value=False):
    if raw_value is None:
        return bool(default_value)
    if isinstance(raw_value, bool):
        return raw_value
    text = str(raw_value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default_value)


@app.get("/me/course-task-reminder-subscription")
@auth_required()
def get_my_course_task_reminder_subscription():
    user_name = str((g.current_user or {}).get("username") or "").strip()
    if not user_name:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401
    data = get_course_task_reminder_subscription(user_name)
    return jsonify({"ok": True, "data": data})


@app.post("/me/course-task-reminder-subscription")
@auth_required()
def update_my_course_task_reminder_subscription():
    user = g.current_user or {}
    user_name = str(user.get("username") or "").strip()
    user_id = _to_int_or_none(user.get("id"))
    if not user_name:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401

    payload = request.get_json(force=True) or {}
    enabled = _normalize_subscription_bool(payload.get("enabled"), True)
    remind_overdue = _normalize_subscription_bool(payload.get("remindOverdue"), True)
    before_hours = payload.get("beforeHours")
    if before_hours in (None, ""):
        before_hours = 24

    try:
        data = save_course_task_reminder_subscription(
            user_name=user_name,
            enabled=enabled,
            before_hours=before_hours,
            remind_overdue=remind_overdue,
        )
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    audit_log(
        "user.course_task_reminder_subscription.update",
        target_type="user",
        target_id=user_name,
        detail={
            "enabled": bool(data.get("enabled")),
            "beforeHours": int(data.get("beforeHours") or 24),
            "remindOverdue": bool(data.get("remindOverdue")),
        },
        actor={
            "id": user_id,
            "username": user_name,
            "role": user.get("role"),
        },
    )
    return jsonify({"ok": True, "data": data})


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
        plans = build_reservation_plans(
            user_name=user_name,
            lab_id_or_name=lab_id,
            preferred_date="",
            preferred_time="",
            days=days,
            k=k,
        )
        recommendations = [{"date": x.get("date"), "time": x.get("time"), "score": x.get("score"), "reason": x.get("reason")} for x in plans]

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
    save_agent_chat_message(user_name, "user", text, action="user_input")
    result = None

    pending_intent = str((pending_ctx or {}).get("intent") or "").strip()
    pending_state = str((pending_ctx or {}).get("state") or "").strip().lower() or "collecting"
    pending_is_multiturn = _agent_is_multiturn_intent(pending_intent)
    current_tool_op = str((tool_call or {}).get("op") or "").strip()
    current_intent = _agent_multiturn_intent_from_tool(current_tool_op)

    def _maybe_offer_time_plans(slot_payload, source_tag):
        slots = slot_payload if isinstance(slot_payload, dict) else {}
        lab_name = str(slots.get("labName") or "").strip()
        date_text = str(slots.get("date") or "").strip()
        if not lab_name or not date_text:
            return None
        try:
            plans = build_reservation_plans(
                user_name=user_name,
                lab_id_or_name=lab_name,
                preferred_date=date_text,
                preferred_time=str(slots.get("time") or "").strip(),
                days=7,
                k=3,
            )
        except Exception:
            plans = []
        plans = _agent_normalize_plan_items(plans)
        if not plans:
            return None

        plan_slots = dict(slots)
        plan_slots["plans"] = plans
        plan_slots["planPrompt"] = "你还没确定时间，我给你3个可选方案："
        _agent_pending_set(
            user_name,
            "reserve_plan_pick",
            slots=plan_slots,
            missing_slots=["selectedPlanId"],
            state="collecting",
        )
        audit_log(
            "agent.reservation.plan.generated",
            target_type="reservation_plan",
            detail={
                "source": str(source_tag or "agent"),
                "labName": lab_name,
                "preferredDate": date_text,
                "preferredTime": str(slots.get("time") or "").strip(),
                "planCount": len(plans),
            },
            actor={"id": g.current_user.get("id"), "username": user_name, "role": current_role},
        )
        return _agent_build_need_more_info_response("reserve_plan_pick", plan_slots, ["selectedPlanId"])

    if pending_is_multiturn and not _agent_is_pending_abort_text(text):
        if current_intent and current_intent != pending_intent:
            _agent_pending_clear(user_name, reason="switch_intent")
            pending_ctx = {}
            pending_intent = ""
            pending_state = "collecting"
            pending_is_multiturn = False
        elif current_tool_op and current_tool_op not in {"general_reply"} and not current_intent and not _agent_is_confirm_text(text):
            _agent_pending_clear(user_name, reason="switch_intent")
            pending_ctx = {}
            pending_intent = ""
            pending_state = "collecting"
            pending_is_multiturn = False

    if pending_is_multiturn:
        if _agent_is_pending_abort_text(text):
            _agent_pending_clear(user_name, reason="user_cancel")
            result = _agent_response(code=0, msg="ok", reply="已取消本次操作。你可以重新描述需求。", action="cancel_aborted", http_status=200)
        elif pending_state == "confirming" and _agent_is_confirm_text(text):
            confirm_slots = dict((pending_ctx or {}).get("slots") or {})
            execute_tool_call = _agent_multiturn_build_tool_call(pending_intent, confirm_slots)
            if pending_intent == "reserve_plan_pick":
                selected_plan = _agent_get_selected_plan_from_slots(confirm_slots)
                if selected_plan:
                    audit_log(
                        "agent.reservation.plan.execute",
                        target_type="reservation_plan",
                        detail={
                            "planId": selected_plan.get("planId"),
                            "labName": selected_plan.get("labName"),
                            "date": selected_plan.get("date"),
                            "time": selected_plan.get("time"),
                        },
                        actor={"id": g.current_user.get("id"), "username": user_name, "role": current_role},
                    )
            if not execute_tool_call:
                result = _agent_build_need_more_info_response(pending_intent, confirm_slots, ["selectedPlanId"])
            else:
                _agent_pending_clear(user_name, reason="confirmed_execute")
                result = _agent_execute_tool(
                    tool_call=execute_tool_call,
                    user_name=user_name,
                    current_role=current_role,
                    text=text,
                    rule_payload=rule_payload,
                )
        else:
            merged_slots = _agent_collect_slots_for_intent(
                pending_intent,
                text=text,
                tool_call=tool_call,
                pending_ctx=pending_ctx,
            )
            missing_slots = _agent_compute_missing_slots_for_intent(pending_intent, merged_slots)
            if missing_slots:
                if pending_intent == "reserve_create" and ("time" in missing_slots) and ("labName" not in missing_slots) and ("date" not in missing_slots):
                    result = _maybe_offer_time_plans(merged_slots, "uncertain_time_pending")
                if result is None:
                    _agent_pending_set(
                        user_name,
                        pending_intent,
                        slots=merged_slots,
                        missing_slots=missing_slots,
                        state="collecting",
                    )
                    result = _agent_build_need_more_info_response(pending_intent, merged_slots, missing_slots)
            else:
                _agent_pending_set(
                    user_name,
                    pending_intent,
                    slots=merged_slots,
                    missing_slots=[],
                    state="confirming",
                )
                if pending_intent == "reserve_plan_pick":
                    selected_plan = _agent_get_selected_plan_from_slots(merged_slots)
                    if selected_plan:
                        audit_log(
                            "agent.reservation.plan.select",
                            target_type="reservation_plan",
                            detail={
                                "planId": selected_plan.get("planId"),
                                "labName": selected_plan.get("labName"),
                                "date": selected_plan.get("date"),
                                "time": selected_plan.get("time"),
                            },
                            actor={"id": g.current_user.get("id"), "username": user_name, "role": current_role},
                        )
                result = _agent_build_confirm_response(pending_intent, merged_slots)
    elif current_intent:
        initial_slots = _agent_collect_slots_for_intent(
            current_intent,
            text=text,
            tool_call=tool_call,
            pending_ctx={},
        )
        initial_missing = _agent_compute_missing_slots_for_intent(current_intent, initial_slots)
        if initial_missing:
            if current_intent == "reserve_create" and ("time" in initial_missing) and ("labName" not in initial_missing) and ("date" not in initial_missing):
                result = _maybe_offer_time_plans(initial_slots, "uncertain_time_initial")
            if result is None:
                _agent_pending_set(
                    user_name,
                    current_intent,
                    slots=initial_slots,
                    missing_slots=initial_missing,
                    state="collecting",
                )
                result = _agent_build_need_more_info_response(current_intent, initial_slots, initial_missing)

    if result is None:
        result = _agent_execute_tool(
            tool_call=tool_call,
            user_name=user_name,
            current_role=current_role,
            text=text,
            rule_payload=rule_payload,
        )
    try:
        response_obj = result[0] if isinstance(result, tuple) else result
        payload = response_obj.get_json(silent=True) if hasattr(response_obj, "get_json") else {}
        payload = payload if isinstance(payload, dict) else {}
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        reply = str(data.get("reply") or "").strip()
        action = str(data.get("action") or "").strip()
        meta = {}
        if isinstance(data.get("reservation"), dict):
            meta["reservation"] = data.get("reservation")
        if isinstance(data.get("repairOrder"), dict):
            meta["repairOrder"] = data.get("repairOrder")
        if isinstance(data.get("search"), dict):
            query_text = str((data.get("search") or {}).get("query") or "").strip()
            if query_text:
                meta["search"] = {"query": query_text}
        raw_sources = data.get("sources")
        if isinstance(raw_sources, list):
            compact_sources = []
            for item in raw_sources[:6]:
                row = item if isinstance(item, dict) else {}
                title = str(row.get("title") or "").strip()
                url = str(row.get("url") or "").strip()
                published_date = str(row.get("publishedDate") or row.get("published_date") or "").strip()
                if not title and not url:
                    continue
                compact_sources.append(
                    {
                        "title": title[:200],
                        "url": url[:500],
                        "publishedDate": published_date[:40],
                    }
                )
            if compact_sources:
                meta["sources"] = compact_sources
        if reply:
            save_agent_chat_message(user_name, "assistant", reply, action=action, meta=meta)
    except Exception:
        pass
    return result


@app.get("/agent/history")
@auth_required()
def agent_history():
    user_name = (g.current_user.get("username") or "").strip()
    if not user_name:
        return jsonify({"code": 401, "msg": "unauthorized", "data": {"messages": []}}), 401
    limit = _to_int_or_none(request.args.get("limit")) or 80
    messages = list_agent_chat_messages(user_name, limit=limit)
    return jsonify({"code": 0, "msg": "ok", "data": {"messages": messages}})


@app.post("/agent/history/clear")
@auth_required()
def clear_agent_history():
    user_name = (g.current_user.get("username") or "").strip()
    if not user_name:
        return jsonify({"code": 401, "msg": "unauthorized", "data": {"cleared": 0}}), 401
    cleared = int(clear_agent_chat_messages(user_name) or 0)
    audit_log(
        "agent.chat.history.clear",
        target_type="agent_chat",
        target_id=user_name,
        detail={"cleared": cleared},
        actor={"id": g.current_user.get("id"), "username": user_name, "role": g.current_user.get("role")},
    )
    return jsonify({"code": 0, "msg": "ok", "data": {"cleared": cleared}})


@app.post("/login")
def login():
    data = request.get_json(force=True) or {}
    username = (data.get("username") or "").strip()
    password = str(data.get("password") or "")
    device_name_raw = data.get("deviceName")
    role_want = _normalize_role(data.get("role"))  # optional
    ip = get_client_ip()
    user_agent = str(request.headers.get("User-Agent") or "").strip()
    device_name = _resolve_device_name(device_name_raw, user_agent)

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
        """
        SELECT id,
               username,
               role,
               password_hash AS passwordHash,
               is_active AS isActive,
               is_frozen AS isFrozen
        FROM user
        WHERE username=%s
        LIMIT 1
        """,
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

    if int(row[0].get("isActive") or 0) != 1:
        audit_log(
            "auth.login.failed",
            target_type="auth",
            target_id=username,
            detail={"reason": "account_disabled"},
            actor={"id": row[0]["id"], "username": row[0]["username"], "role": row[0]["role"]},
        )
        return jsonify({"ok": False, "msg": "account disabled"}), 403

    if int(row[0].get("isFrozen") or 0) == 1:
        audit_log(
            "auth.login.failed",
            target_type="auth",
            target_id=username,
            detail={"reason": "account_frozen"},
            actor={"id": row[0]["id"], "username": row[0]["username"], "role": row[0]["role"]},
        )
        return jsonify({"ok": False, "msg": "account frozen"}), 403

    db_role = row[0]["role"]
    is_admin = (db_role == "admin")

    if role_want:
        if role_want not in USER_ROLES:
            return jsonify({"ok": False, "msg": "params error"}), 400
        if role_want == "admin" and not is_admin:
            return jsonify({"ok": False, "msg": "not admin"}), 403

    token = create_access_token({"id": row[0]["id"], "username": row[0]["username"], "role": db_role})
    refresh_token = issue_refresh_token(
        row[0]["id"],
        device_name=device_name,
        user_agent=user_agent,
        login_ip=ip,
    )
    execute(
        "UPDATE user SET last_login_at=%s, last_login_ip=%s WHERE id=%s",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ip, row[0]["id"]),
    )
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
    device_name_raw = data.get("deviceName")
    ip = get_client_ip()
    user_agent = str(request.headers.get("User-Agent") or "").strip()
    device_name = _resolve_device_name(device_name_raw, user_agent)

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
    refresh_token = issue_refresh_token(
        new_id,
        device_name=device_name,
        user_agent=user_agent,
        login_ip=ip,
    )
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
    device_name_raw = data.get("deviceName")
    ip = get_client_ip()
    user_agent = str(request.headers.get("User-Agent") or "").strip()
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

    user_rows = query(
        """
        SELECT id,
               username,
               role,
               is_active AS isActive,
               is_frozen AS isFrozen
        FROM user
        WHERE id=%s
        LIMIT 1
        """,
        (row["userId"],),
    )
    if not user_rows:
        revoke_refresh_token(refresh_token)
        audit_log("auth.refresh.failed", target_type="auth", detail={"reason": "user_not_found"})
        return jsonify({"ok": False, "msg": "invalid refresh token"}), 401
    user = user_rows[0]

    if int(user.get("isActive") or 0) != 1:
        revoke_refresh_token(refresh_token)
        audit_log("auth.refresh.failed", target_type="auth", target_id=user.get("id"), detail={"reason": "account_disabled"})
        return jsonify({"ok": False, "msg": "account disabled"}), 403
    if int(user.get("isFrozen") or 0) == 1:
        revoke_refresh_token(refresh_token)
        audit_log("auth.refresh.failed", target_type="auth", target_id=user.get("id"), detail={"reason": "account_frozen"})
        return jsonify({"ok": False, "msg": "account frozen"}), 403

    fallback_device_name = row.get("deviceName") if isinstance(row, dict) else ""
    fallback_user_agent = row.get("userAgent") if isinstance(row, dict) else ""
    fallback_login_ip = row.get("loginIp") if isinstance(row, dict) else ""
    device_name = _resolve_device_name(device_name_raw or fallback_device_name, user_agent or fallback_user_agent)
    new_refresh = issue_refresh_token(
        user["id"],
        device_name=device_name,
        user_agent=(user_agent or str(fallback_user_agent or "").strip()),
        login_ip=(ip or str(fallback_login_ip or "").strip()),
    )
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
    keyword = str(request.args.get("keyword") or "").strip()
    role_raw = str(request.args.get("role") or "").strip()
    class_name_raw = request.args.get("className")
    graduation_year_raw = request.args.get("graduationYear")
    graduate_reference_year_raw = request.args.get("graduateReferenceYear")
    never_logged_in_raw = request.args.get("neverLoggedIn")
    graduate_pending_deactivate_raw = request.args.get("graduatePendingDeactivate")
    violation_unfrozen_raw = request.args.get("violationUnfrozen")
    missing_class_name_raw = request.args.get("missingClassName")
    missing_graduation_year_raw = request.args.get("missingGraduationYear")
    is_active_raw = request.args.get("isActive")
    is_frozen_raw = request.args.get("isFrozen")
    has_violation_raw = request.args.get("hasViolation")
    login_days_raw = request.args.get("loginDays")
    page_raw = request.args.get("page")
    page_size_raw = request.args.get("pageSize")

    try:
        role = _normalize_role(role_raw) if role_raw else ""
        if role and role not in USER_ROLES:
            raise BizError("invalid role", 400)
        class_name = _normalize_profile_class_name(class_name_raw or "")
        graduation_year = _normalize_optional_int(graduation_year_raw, "graduationYear", min_value=0, max_value=2200)
        graduate_reference_year = _normalize_optional_int(
            graduate_reference_year_raw, "graduateReferenceYear", min_value=2000, max_value=2200
        )
        never_logged_in_filter = _normalize_bool_filter(never_logged_in_raw, "neverLoggedIn")
        graduate_pending_deactivate_filter = _normalize_bool_filter(
            graduate_pending_deactivate_raw, "graduatePendingDeactivate"
        )
        violation_unfrozen_filter = _normalize_bool_filter(violation_unfrozen_raw, "violationUnfrozen")
        missing_class_name_filter = _normalize_bool_filter(missing_class_name_raw, "missingClassName")
        missing_graduation_year_filter = _normalize_bool_filter(
            missing_graduation_year_raw, "missingGraduationYear"
        )
        is_active_filter = _normalize_bool_filter(is_active_raw, "isActive")
        is_frozen_filter = _normalize_bool_filter(is_frozen_raw, "isFrozen")
        has_violation_filter = _normalize_bool_filter(has_violation_raw, "hasViolation")
        login_days = _normalize_optional_int(login_days_raw, "loginDays", min_value=0, max_value=3650)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    where_sql = " WHERE 1=1"
    params = []
    current_year = int(graduate_reference_year or datetime.now().year)
    violation_expr = (
        "("
        "(SELECT COUNT(*) FROM reservation r WHERE r.user_name=u.username AND r.status='rejected')"
        " + "
        "(SELECT COUNT(*) FROM lost_found lf WHERE lf.claim_apply_user=u.username AND lf.claim_apply_status='rejected')"
        " + "
        "("
        "SELECT COUNT(*)"
        " FROM equipment_borrow_request br"
        " WHERE br.applicant_user_name=u.username"
        "   AND ("
        "       (br.status='approved' AND br.returned_at IS NULL AND br.expected_return_at IS NOT NULL AND br.expected_return_at < NOW())"
        "       OR"
        "       (br.status='returned' AND br.returned_at IS NOT NULL AND br.expected_return_at IS NOT NULL AND br.returned_at > br.expected_return_at)"
        "   )"
        ")"
        ")"
    )

    if role:
        where_sql += " AND u.role=%s"
        params.append(role)

    if class_name:
        where_sql += " AND u.class_name LIKE %s"
        params.append(f"%{class_name}%")

    if graduation_year is not None:
        where_sql += " AND u.graduation_year=%s"
        params.append(int(graduation_year))

    if graduate_pending_deactivate_filter is not None and int(graduate_pending_deactivate_filter) == 1:
        where_sql += " AND u.role='student' AND u.graduation_year > 0 AND u.graduation_year <= %s AND u.is_active=1"
        params.append(current_year)

    if missing_class_name_filter is not None and int(missing_class_name_filter) == 1:
        where_sql += " AND u.role='student' AND TRIM(COALESCE(u.class_name, ''))=''"

    if missing_graduation_year_filter is not None and int(missing_graduation_year_filter) == 1:
        where_sql += " AND u.role='student' AND COALESCE(u.graduation_year, 0) <= 0"

    if is_active_filter is not None:
        where_sql += " AND u.is_active=%s"
        params.append(int(is_active_filter))

    if is_frozen_filter is not None:
        where_sql += " AND u.is_frozen=%s"
        params.append(int(is_frozen_filter))

    if never_logged_in_filter is not None:
        if int(never_logged_in_filter) == 1:
            where_sql += " AND u.last_login_at IS NULL"
        else:
            where_sql += " AND u.last_login_at IS NOT NULL"
    elif login_days is not None:
        cutoff = (datetime.now() - timedelta(days=int(login_days))).strftime("%Y-%m-%d %H:%M:%S")
        where_sql += " AND u.last_login_at IS NOT NULL AND u.last_login_at >= %s"
        params.append(cutoff)

    if has_violation_filter is not None:
        if int(has_violation_filter) == 1:
            where_sql += f" AND {violation_expr} > 0"
        else:
            where_sql += f" AND {violation_expr} = 0"

    if violation_unfrozen_filter is not None and int(violation_unfrozen_filter) == 1:
        where_sql += f" AND {violation_expr} > 0 AND u.is_frozen=0"

    if keyword:
        where_sql += (
            " AND (u.username LIKE %s OR u.nickname LIKE %s OR u.phone LIKE %s OR u.class_name LIKE %s OR CAST(u.id AS CHAR) LIKE %s)"
        )
        like_key = f"%{keyword}%"
        params.extend([like_key, like_key, like_key, like_key, like_key])

    base_sql = f"""
        SELECT u.id,
               u.username,
               u.role,
               u.nickname,
               u.phone,
               u.avatar_url AS avatarUrl,
               u.class_name AS className,
               u.graduation_year AS graduationYear,
               u.is_active AS isActive,
               u.is_frozen AS isFrozen,
               u.last_login_at AS lastLoginAt,
               {violation_expr} AS violationCount
        FROM user u
    """

    use_pagination = bool(page_raw or page_size_raw)
    if not use_pagination:
        rows = query(base_sql + where_sql + " ORDER BY u.id ASC", params)
        return jsonify({"ok": True, "data": [_format_user_admin_row(x) for x in rows], "meta": {"total": len(rows)}})

    try:
        page = int(page_raw or "1")
    except ValueError:
        page = 1
    try:
        page_size = int(page_size_raw or "20")
    except ValueError:
        page_size = 20
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    offset = (page - 1) * page_size

    count_rows = query("SELECT COUNT(*) AS cnt FROM user u" + where_sql, params)
    total = int((count_rows[0] or {}).get("cnt") or 0) if count_rows else 0

    list_sql = base_sql + where_sql + " ORDER BY u.id ASC LIMIT %s OFFSET %s"
    list_params = list(params) + [page_size, offset]
    rows = query(list_sql, list_params)
    return jsonify(
        {
            "ok": True,
            "data": [_format_user_admin_row(x) for x in rows],
            "meta": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "hasMore": (offset + len(rows)) < total,
            },
        }
    )


@app.get("/users/governance-stats")
@auth_required(roles=["admin"])
def get_user_governance_stats():
    graduate_reference_year_raw = request.args.get("graduateReferenceYear")
    try:
        graduate_reference_year = _normalize_optional_int(
            graduate_reference_year_raw, "graduateReferenceYear", min_value=2000, max_value=2200
        )
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status
    violation_expr = (
        "("
        "(SELECT COUNT(*) FROM reservation r WHERE r.user_name=u.username AND r.status='rejected')"
        " + "
        "(SELECT COUNT(*) FROM lost_found lf WHERE lf.claim_apply_user=u.username AND lf.claim_apply_status='rejected')"
        " + "
        "("
        "SELECT COUNT(*)"
        " FROM equipment_borrow_request br"
        " WHERE br.applicant_user_name=u.username"
        "   AND ("
        "       (br.status='approved' AND br.returned_at IS NULL AND br.expected_return_at IS NOT NULL AND br.expected_return_at < NOW())"
        "       OR"
        "       (br.status='returned' AND br.returned_at IS NOT NULL AND br.expected_return_at IS NOT NULL AND br.returned_at > br.expected_return_at)"
        "   )"
        ")"
        ")"
    )
    current_year = int(graduate_reference_year or datetime.now().year)
    rows = query(
        f"""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN u.role='admin' THEN 1 ELSE 0 END) AS adminCount,
               SUM(CASE WHEN u.role='teacher' THEN 1 ELSE 0 END) AS teacherCount,
               SUM(CASE WHEN u.role='student' THEN 1 ELSE 0 END) AS studentCount,
               SUM(CASE WHEN u.role='student' AND u.last_login_at IS NULL THEN 1 ELSE 0 END) AS neverLoginStudentCount,
               SUM(CASE WHEN u.role='student' AND COALESCE(u.graduation_year, 0) > 0 AND u.graduation_year <= %s AND u.is_active=1 THEN 1 ELSE 0 END) AS graduatePendingDeactivateCount,
               SUM(CASE WHEN {violation_expr} > 0 AND u.is_frozen=0 THEN 1 ELSE 0 END) AS violationUnfrozenCount,
               SUM(CASE WHEN u.role='student' AND TRIM(COALESCE(u.class_name, ''))='' THEN 1 ELSE 0 END) AS missingClassNameCount,
               SUM(CASE WHEN u.role='student' AND COALESCE(u.graduation_year, 0) <= 0 THEN 1 ELSE 0 END) AS missingGraduationYearCount
        FROM user u
        """,
        (current_year,),
    )
    row = (rows or [{}])[0] or {}
    data = {
        "total": int(row.get("total") or 0),
        "adminCount": int(row.get("adminCount") or 0),
        "teacherCount": int(row.get("teacherCount") or 0),
        "studentCount": int(row.get("studentCount") or 0),
        "neverLoginStudentCount": int(row.get("neverLoginStudentCount") or 0),
        "graduatePendingDeactivateCount": int(row.get("graduatePendingDeactivateCount") or 0),
        "violationUnfrozenCount": int(row.get("violationUnfrozenCount") or 0),
        "missingClassNameCount": int(row.get("missingClassNameCount") or 0),
        "missingGraduationYearCount": int(row.get("missingGraduationYearCount") or 0),
        "graduateReferenceYear": current_year,
    }
    return jsonify({"ok": True, "data": data})


@app.get("/users/<int:uid>/detail")
@auth_required(roles=["admin"])
def get_user_detail(uid):
    detail_limit = _normalize_non_negative_int(request.args.get("limit"), "limit", default_value=20, max_value=200)
    detail_limit = max(5, int(detail_limit or 20))

    user_row = _query_admin_user_row(uid)
    if not user_row:
        return jsonify({"ok": False, "msg": "user not found"}), 404

    username = str(user_row.get("username") or "").strip()
    reservations = query(
        """
        SELECT id, lab_name AS labName, date, time, status, reason, reject_reason AS rejectReason, created_at AS createdAt
        FROM reservation
        WHERE user_name=%s
        ORDER BY id DESC
        LIMIT %s
        """,
        (username, detail_limit),
    )
    for row in reservations:
        row["createdAt"] = _to_text_time(row.get("createdAt"))

    repairs = query(
        """
        SELECT id,
               order_no AS orderNo,
               issue_type AS issueType,
               lab_name AS labName,
               equipment_name AS equipmentName,
               status,
               created_at AS createdAt
        FROM repair_work_order
        WHERE submitter_name=%s
        ORDER BY id DESC
        LIMIT %s
        """,
        (username, detail_limit),
    )
    for row in repairs:
        row["createdAt"] = _to_text_time(row.get("createdAt"))

    lost_found = query(
        """
        SELECT id,
               title,
               item_type AS itemType,
               status,
               owner,
               claim_apply_status AS claimApplyStatus,
               claim_apply_user AS claimApplyUser,
               created_at AS createdAt
        FROM lost_found
        WHERE owner=%s OR claim_apply_user=%s
        ORDER BY id DESC
        LIMIT %s
        """,
        (username, username, detail_limit),
    )
    for row in lost_found:
        row["createdAt"] = _to_text_time(row.get("createdAt"))
        row["relation"] = "owner" if str(row.get("owner") or "").strip() == username else "claimant"

    teacher_courses = query(
        """
        SELECT id,
               name,
               class_name AS className,
               course_code AS courseCode,
               status,
               created_at AS createdAt
        FROM course
        WHERE teacher_user_name=%s
          AND status<>'deleted'
        ORDER BY id DESC
        LIMIT %s
        """,
        (username, detail_limit),
    )
    for row in teacher_courses:
        row["createdAt"] = _to_text_time(row.get("createdAt"))

    joined_courses = query(
        """
        SELECT m.course_id AS courseId,
               c.name,
               c.class_name AS className,
               c.course_code AS courseCode,
               c.teacher_user_name AS teacherUserName,
               c.status AS courseStatus,
               m.status AS memberStatus,
               m.joined_at AS joinedAt
        FROM course_member m
        LEFT JOIN course c ON c.id=m.course_id
        WHERE m.student_user_name=%s
          AND m.status='active'
          AND c.status<>'deleted'
        ORDER BY m.id DESC
        LIMIT %s
        """,
        (username, detail_limit),
    )
    for row in joined_courses:
        row["joinedAt"] = _to_text_time(row.get("joinedAt"))

    audit_rows = query(
        """
        SELECT id,
               action,
               operator_id AS operatorId,
               operator_name AS operatorName,
               operator_role AS operatorRole,
               target_type AS targetType,
               target_id AS targetId,
               detail_json AS detailJson,
               created_at AS createdAt
        FROM audit_log
        WHERE operator_id=%s
           OR operator_name=%s
           OR (target_type='user' AND target_id=%s)
        ORDER BY id DESC
        LIMIT %s
        """,
        (uid, username, str(uid), max(20, detail_limit)),
    )
    for row in audit_rows:
        row["createdAt"] = _to_text_time(row.get("createdAt"))
        raw = str(row.get("detailJson") or "").strip()
        if raw:
            try:
                row["detail"] = json.loads(raw)
            except Exception:
                row["detail"] = {"raw": raw}
        else:
            row["detail"] = {}
        row.pop("detailJson", None)

    violation_records = []
    violation_res = query(
        """
        SELECT id,
               date AS happenedAt,
               reject_reason AS detail,
               reason
        FROM reservation
        WHERE user_name=%s
          AND status='rejected'
        ORDER BY id DESC
        LIMIT 50
        """,
        (username,),
    )
    for row in violation_res:
        violation_records.append(
            {
                "source": "reservation",
                "id": int(row.get("id") or 0),
                "happenedAt": str(row.get("happenedAt") or "").strip(),
                "reason": str(row.get("reason") or "").strip(),
                "detail": str(row.get("detail") or "").strip(),
            }
        )
    violation_claim = query(
        """
        SELECT id,
               created_at AS happenedAt,
               title,
               claim_review_note AS detail
        FROM lost_found
        WHERE claim_apply_user=%s
          AND claim_apply_status='rejected'
        ORDER BY id DESC
        LIMIT 50
        """,
        (username,),
    )
    for row in violation_claim:
        violation_records.append(
            {
                "source": "lostfound_claim",
                "id": int(row.get("id") or 0),
                "happenedAt": _to_text_time(row.get("happenedAt")),
                "reason": str(row.get("title") or "").strip(),
                "detail": str(row.get("detail") or "").strip(),
            }
        )
    violation_borrow = query(
        """
        SELECT id,
               equipment_name AS equipmentName,
               equipment_asset_code AS equipmentAssetCode,
               expected_return_at AS expectedReturnAt,
               returned_at AS returnedAt,
               status
        FROM equipment_borrow_request
        WHERE applicant_user_name=%s
          AND (
              (status='approved' AND returned_at IS NULL AND expected_return_at IS NOT NULL AND expected_return_at < NOW())
              OR
              (status='returned' AND returned_at IS NOT NULL AND expected_return_at IS NOT NULL AND returned_at > expected_return_at)
          )
        ORDER BY id DESC
        LIMIT 50
        """,
        (username,),
    )
    for row in violation_borrow:
        equipment_text = str(row.get("equipmentName") or "").strip() or str(row.get("equipmentAssetCode") or "").strip()
        status = str(row.get("status") or "").strip()
        reason = "借用逾期未归还" if status == "approved" else "借用逾期归还"
        happened_at = _to_text_time(row.get("returnedAt") or row.get("expectedReturnAt"))
        expected_return = _to_text_time(row.get("expectedReturnAt"))
        detail_parts = [equipment_text or "-", f"应还时间：{expected_return or '-'}"]
        returned_at = _to_text_time(row.get("returnedAt"))
        if returned_at:
            detail_parts.append(f"实际归还：{returned_at}")
        violation_records.append(
            {
                "source": "borrow_overdue",
                "id": int(row.get("id") or 0),
                "happenedAt": happened_at,
                "reason": reason,
                "detail": "；".join(detail_parts),
            }
        )
    violation_records.sort(key=lambda x: str(x.get("happenedAt") or ""), reverse=True)

    reservation_count_rows = query("SELECT COUNT(*) AS cnt FROM reservation WHERE user_name=%s", (username,))
    repair_count_rows = query("SELECT COUNT(*) AS cnt FROM repair_work_order WHERE submitter_name=%s", (username,))
    lost_count_rows = query(
        "SELECT COUNT(*) AS cnt FROM lost_found WHERE owner=%s OR claim_apply_user=%s",
        (username, username),
    )
    course_count = int(len(teacher_courses) + len(joined_courses))

    payload = {
        "user": _format_user_admin_row(user_row),
        "summary": {
            "reservationTotal": int((reservation_count_rows[0] or {}).get("cnt") or 0) if reservation_count_rows else 0,
            "repairTotal": int((repair_count_rows[0] or {}).get("cnt") or 0) if repair_count_rows else 0,
            "lostFoundTotal": int((lost_count_rows[0] or {}).get("cnt") or 0) if lost_count_rows else 0,
            "courseTotal": course_count,
            "auditTotal": len(audit_rows),
            "violationTotal": len(violation_records),
        },
        "reservations": reservations,
        "repairs": repairs,
        "lostFound": lost_found,
        "courses": {
            "teaching": teacher_courses,
            "joined": joined_courses,
        },
        "auditActions": audit_rows,
        "violationRecords": violation_records[: max(detail_limit, 20)],
    }
    return jsonify({"ok": True, "data": payload})


@app.get("/admin/todo-center")
@auth_required(roles=["admin"])
def admin_todo_center():
    sort_by = _normalize_todo_sort(request.args.get("sortBy"))
    sort_order = _normalize_todo_order(request.args.get("sortOrder"))
    limit_per_card = _normalize_non_negative_int(request.args.get("limitPerCard"), "limitPerCard", default_value=20, max_value=200)
    limit_per_card = max(1, int(limit_per_card or 20))
    scan_limit = max(limit_per_card * 4, 60)

    now_dt = datetime.now()
    now_text = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    today_start = now_dt.strftime("%Y-%m-%d 00:00:00")
    tomorrow_start = (now_dt + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
    seven_days_ago_start = (now_dt - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    task_deadline_limit = (now_dt + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")

    def _age_minutes(time_value):
        dt = _to_datetime(time_value)
        if dt == datetime.min:
            return 0
        return max(0, int((now_dt - dt).total_seconds() // 60))

    def _hours_to(target_value):
        dt = _to_datetime(target_value)
        if dt == datetime.min:
            return 10**6
        return (dt - now_dt).total_seconds() / 3600.0

    reservation_rows = query(
        """
        SELECT id,
               lab_name AS labName,
               user_name AS userName,
               date,
               time,
               reason,
               created_at AS createdAt
        FROM reservation
        WHERE status='pending'
        ORDER BY created_at ASC, id ASC
        LIMIT %s
        """,
        (scan_limit,),
    )
    reservation_count_rows = query("SELECT COUNT(*) AS cnt FROM reservation WHERE status='pending'")
    reservation_total = int((reservation_count_rows[0] or {}).get("cnt") or 0) if reservation_count_rows else len(reservation_rows)
    reservation_items = []
    for row in reservation_rows:
        entity_id = int(row.get("id") or 0)
        if entity_id <= 0:
            continue
        created_at = _to_text_time(row.get("createdAt"))
        age_hours = _age_minutes(created_at) / 60.0
        timeout = bool(age_hours >= 8)
        score = 82 + min(18, int(age_hours // 2))
        if timeout:
            score += 8
        score = max(0, min(99, int(score)))
        reservation_items.append(
            {
                "id": f"reservation_pending:{entity_id}",
                "category": "reservation_pending",
                "entityId": entity_id,
                "title": f"{str(row.get('labName') or '').strip() or '-'} · {str(row.get('date') or '').strip()} {str(row.get('time') or '').strip()}",
                "subtitle": f"user: {str(row.get('userName') or '').strip() or '-'}",
                "detail": str(row.get("reason") or "").strip(),
                "createdAt": created_at,
                "deadlineAt": created_at,
                "priorityScore": score,
                "priorityLevel": _todo_priority_level(score),
                "timeout": timeout,
                "jumpUrl": f"/pages/admin/approve-detail?id={entity_id}",
                "processAction": "approve",
            }
        )
    reservation_items = _sort_todo_items(reservation_items, sort_by=sort_by, sort_order=sort_order)
    reservation_items = reservation_items[:limit_per_card]
    reservation_timeout_count = len([x for x in reservation_items if x.get("timeout")])

    repair_rows = query(
        """
        SELECT id,
               order_no AS orderNo,
               lab_name AS labName,
               equipment_name AS equipmentName,
               submitter_name AS submitterName,
               submitted_at AS submittedAt,
               created_at AS createdAt
        FROM repair_work_order
        WHERE status='submitted'
        ORDER BY submitted_at ASC, id ASC
        LIMIT %s
        """,
        (scan_limit,),
    )
    repair_count_rows = query("SELECT COUNT(*) AS cnt FROM repair_work_order WHERE status='submitted'")
    repair_total = int((repair_count_rows[0] or {}).get("cnt") or 0) if repair_count_rows else len(repair_rows)
    repair_items = []
    for row in repair_rows:
        entity_id = int(row.get("id") or 0)
        if entity_id <= 0:
            continue
        created_at = _to_text_time(row.get("submittedAt") or row.get("createdAt"))
        age_hours = _age_minutes(created_at) / 60.0
        timeout = bool(age_hours >= 24)
        score = 76 + min(16, int(age_hours // 4))
        if timeout:
            score += 10
        score = max(0, min(99, int(score)))
        repair_items.append(
            {
                "id": f"repair_pending:{entity_id}",
                "category": "repair_pending",
                "entityId": entity_id,
                "title": f"{str(row.get('orderNo') or '').strip() or ('#' + str(entity_id))} · {str(row.get('labName') or '').strip() or '-'}",
                "subtitle": f"submitter: {str(row.get('submitterName') or '').strip() or '-'}",
                "detail": str(row.get("equipmentName") or "").strip(),
                "createdAt": created_at,
                "deadlineAt": created_at,
                "priorityScore": score,
                "priorityLevel": _todo_priority_level(score),
                "timeout": timeout,
                "jumpUrl": f"/pages/admin/repair_orders?status=submitted&focusId={entity_id}",
                "processAction": "accept",
            }
        )
    repair_items = _sort_todo_items(repair_items, sort_by=sort_by, sort_order=sort_order)
    repair_items = repair_items[:limit_per_card]
    repair_timeout_count = len([x for x in repair_items if x.get("timeout")])

    alarm_rows = query(
        """
        SELECT id,
               lab_name AS labName,
               alarm_code AS alarmCode,
               level,
               message,
               created_at AS createdAt
        FROM lab_sensor_alarm
        WHERE level IN ('alarm', 'critical')
          AND created_at >= %s
        ORDER BY created_at DESC, id DESC
        LIMIT %s
        """,
        (seven_days_ago_start, scan_limit),
    )
    alarm_count_rows = query(
        """
        SELECT COUNT(*) AS cnt
        FROM lab_sensor_alarm
        WHERE level IN ('alarm', 'critical')
          AND created_at >= %s
        """,
        (seven_days_ago_start,),
    )
    alarm_total = int((alarm_count_rows[0] or {}).get("cnt") or 0) if alarm_count_rows else len(alarm_rows)
    alarm_items = []
    for row in alarm_rows:
        entity_id = int(row.get("id") or 0)
        if entity_id <= 0:
            continue
        created_at = _to_text_time(row.get("createdAt"))
        age_minutes = _age_minutes(created_at)
        timeout = bool(age_minutes >= 60)
        level = str(row.get("level") or "alarm").strip().lower()
        score = 92 + (4 if level == "critical" else 0) + min(3, int(age_minutes // 60))
        if timeout:
            score += 6
        score = max(0, min(99, int(score)))
        alarm_items.append(
            {
                "id": f"alarm_high_risk:{entity_id}",
                "category": "alarm_high_risk",
                "entityId": entity_id,
                "title": f"{str(row.get('labName') or '').strip() or '-'} · {str(row.get('alarmCode') or '').strip() or '-'}",
                "subtitle": f"level: {level}",
                "detail": str(row.get("message") or "").strip(),
                "createdAt": created_at,
                "deadlineAt": created_at,
                "priorityScore": score,
                "priorityLevel": _todo_priority_level(score),
                "timeout": timeout,
                "jumpUrl": "/pages/admin/labs",
                "processAction": "mark_done",
            }
        )
    alarm_items = _sort_todo_items(alarm_items, sort_by=sort_by, sort_order=sort_order)
    alarm_items = alarm_items[:limit_per_card]
    alarm_timeout_count = len([x for x in alarm_items if x.get("timeout")])

    claim_rows = query(
        """
        SELECT id,
               title,
               claim_apply_user AS claimApplyUser,
               claim_apply_name AS claimApplyName,
               claim_apply_at AS claimApplyAt,
               created_at AS createdAt
        FROM lost_found
        WHERE item_type='found'
          AND status='open'
          AND claim_apply_status='pending'
        ORDER BY COALESCE(claim_apply_at, created_at) ASC, id ASC
        LIMIT %s
        """,
        (scan_limit,),
    )
    claim_count_rows = query(
        """
        SELECT COUNT(*) AS cnt
        FROM lost_found
        WHERE item_type='found'
          AND status='open'
          AND claim_apply_status='pending'
        """
    )
    claim_total = int((claim_count_rows[0] or {}).get("cnt") or 0) if claim_count_rows else len(claim_rows)
    claim_items = []
    for row in claim_rows:
        entity_id = int(row.get("id") or 0)
        if entity_id <= 0:
            continue
        created_at = _to_text_time(row.get("claimApplyAt") or row.get("createdAt"))
        age_hours = _age_minutes(created_at) / 60.0
        timeout = bool(age_hours >= 24)
        score = 74 + min(18, int(age_hours // 6))
        if timeout:
            score += 10
        score = max(0, min(99, int(score)))
        claim_items.append(
            {
                "id": f"claim_pending:{entity_id}",
                "category": "claim_pending",
                "entityId": entity_id,
                "title": str(row.get("title") or "").strip() or f"#{entity_id}",
                "subtitle": f"applicant: {str(row.get('claimApplyName') or row.get('claimApplyUser') or '').strip() or '-'}",
                "detail": "",
                "createdAt": created_at,
                "deadlineAt": created_at,
                "priorityScore": score,
                "priorityLevel": _todo_priority_level(score),
                "timeout": timeout,
                "jumpUrl": f"/pages/admin/lostfound?type=found&claimApplyStatus=pending&focusId={entity_id}",
                "processAction": "approve_claim",
            }
        )
    claim_items = _sort_todo_items(claim_items, sort_by=sort_by, sort_order=sort_order)
    claim_items = claim_items[:limit_per_card]
    claim_timeout_count = len([x for x in claim_items if x.get("timeout")])

    task_rows = query(
        """
        SELECT t.id,
               t.course_id AS courseId,
               t.title,
               t.deadline,
               t.created_at AS createdAt,
               c.name AS courseName,
               c.class_name AS className,
               (
                   SELECT COUNT(*)
                   FROM course_member cm
                   WHERE cm.course_id=t.course_id
                     AND cm.status='active'
               ) AS totalStudents,
               (
                   SELECT COUNT(DISTINCT s.student_user_name)
                   FROM experiment_task_submission s
                   WHERE s.task_id=t.id
                     AND s.status='active'
               ) AS submittedStudents
        FROM experiment_task t
        LEFT JOIN course c ON c.id=t.course_id
        WHERE t.status='active'
          AND c.status='enabled'
          AND t.deadline IS NOT NULL
          AND t.deadline <= %s
        ORDER BY t.deadline ASC, t.id ASC
        LIMIT %s
        """,
        (task_deadline_limit, scan_limit),
    )
    task_count_rows = query(
        """
        SELECT COUNT(*) AS cnt
        FROM (
            SELECT t.id
            FROM experiment_task t
            LEFT JOIN course c ON c.id=t.course_id
            WHERE t.status='active'
              AND c.status='enabled'
              AND t.deadline IS NOT NULL
              AND t.deadline <= %s
              AND (
                   SELECT COUNT(*)
                   FROM course_member cm
                   WHERE cm.course_id=t.course_id
                     AND cm.status='active'
              ) > (
                   SELECT COUNT(DISTINCT s.student_user_name)
                   FROM experiment_task_submission s
                   WHERE s.task_id=t.id
                     AND s.status='active'
              )
        ) t1
        """,
        (task_deadline_limit,),
    )
    task_total = int((task_count_rows[0] or {}).get("cnt") or 0) if task_count_rows else 0
    task_items = []
    for row in task_rows:
        task_id = int(row.get("id") or 0)
        course_id = int(row.get("courseId") or 0)
        if task_id <= 0 or course_id <= 0:
            continue
        total_students = int(row.get("totalStudents") or 0)
        submitted_students = int(row.get("submittedStudents") or 0)
        missing_students = max(0, total_students - submitted_students)
        if missing_students <= 0:
            continue
        deadline_at = _to_text_time(row.get("deadline"))
        created_at = _to_text_time(row.get("createdAt"))
        hours_left = _hours_to(deadline_at)
        timeout = bool(hours_left <= 0)
        score = 60 + min(25, missing_students * 4)
        if hours_left <= 6:
            score += 20
        elif hours_left <= 24:
            score += 12
        elif hours_left <= 48:
            score += 6
        if timeout:
            score += 12
        score = max(0, min(99, int(score)))
        task_items.append(
            {
                "id": f"course_task_due:{task_id}",
                "category": "course_task_due",
                "entityId": task_id,
                "courseId": course_id,
                "taskId": task_id,
                "title": f"{str(row.get('courseName') or '').strip() or '-'} · {str(row.get('title') or '').strip() or '-'}",
                "subtitle": f"missing: {missing_students}/{max(0, total_students)}",
                "detail": str(row.get("className") or "").strip(),
                "createdAt": created_at,
                "deadlineAt": deadline_at,
                "priorityScore": score,
                "priorityLevel": _todo_priority_level(score),
                "timeout": timeout,
                "jumpUrl": f"/pages/teacher/course_detail?courseId={course_id}",
                "processAction": "notify_missing",
            }
        )
    task_items = _sort_todo_items(task_items, sort_by=sort_by, sort_order=sort_order)
    task_items = task_items[:limit_per_card]
    task_timeout_count = len([x for x in task_items if x.get("timeout")])

    announcement_rows = query(
        """
        SELECT id,
               title,
               publish_at AS publishAt,
               publisher_name AS publisherName,
               created_at AS createdAt
        FROM announcement
        WHERE COALESCE(publish_at, created_at) >= %s
          AND COALESCE(publish_at, created_at) < %s
          AND COALESCE(publish_at, created_at) > %s
        ORDER BY COALESCE(publish_at, created_at) ASC, id ASC
        LIMIT %s
        """,
        (today_start, tomorrow_start, now_text, scan_limit),
    )
    announcement_count_rows = query(
        """
        SELECT COUNT(*) AS cnt
        FROM announcement
        WHERE COALESCE(publish_at, created_at) >= %s
          AND COALESCE(publish_at, created_at) < %s
          AND COALESCE(publish_at, created_at) > %s
        """,
        (today_start, tomorrow_start, now_text),
    )
    announcement_total = (
        int((announcement_count_rows[0] or {}).get("cnt") or 0) if announcement_count_rows else len(announcement_rows)
    )
    announcement_items = []
    for row in announcement_rows:
        entity_id = int(row.get("id") or 0)
        if entity_id <= 0:
            continue
        publish_at = _to_text_time(row.get("publishAt") or row.get("createdAt"))
        hours_left = _hours_to(publish_at)
        timeout = bool(hours_left <= 0)
        score = 58
        if hours_left <= 2:
            score += 18
        elif hours_left <= 6:
            score += 12
        elif hours_left <= 12:
            score += 8
        score = max(0, min(99, int(score)))
        announcement_items.append(
            {
                "id": f"announcement_today_scheduled:{entity_id}",
                "category": "announcement_today_scheduled",
                "entityId": entity_id,
                "title": str(row.get("title") or "").strip() or f"#{entity_id}",
                "subtitle": f"publisher: {str(row.get('publisherName') or '').strip() or '-'}",
                "detail": "",
                "createdAt": _to_text_time(row.get("createdAt")),
                "deadlineAt": publish_at,
                "priorityScore": score,
                "priorityLevel": _todo_priority_level(score),
                "timeout": timeout,
                "jumpUrl": "/pages/admin/admin",
                "processAction": "publish_now",
            }
        )
    announcement_items = _sort_todo_items(announcement_items, sort_by=sort_by, sort_order=sort_order)
    announcement_items = announcement_items[:limit_per_card]
    announcement_timeout_count = len([x for x in announcement_items if x.get("timeout")])

    cards = [
        _build_todo_card(
            "reservation_pending",
            "待审批预约",
            "需要审批的预约申请",
            "/pages/admin/approve?status=pending",
            reservation_total,
            reservation_timeout_count,
            reservation_items,
            "批量通过",
        ),
        _build_todo_card(
            "repair_pending",
            "待处理报修",
            "待受理工单",
            "/pages/admin/repair_orders?status=submitted",
            repair_total,
            repair_timeout_count,
            repair_items,
            "批量受理",
        ),
        _build_todo_card(
            "alarm_high_risk",
            "高风险告警",
            "近 7 天高风险告警",
            "/pages/admin/labs",
            alarm_total,
            alarm_timeout_count,
            alarm_items,
            "标记已跟进",
        ),
        _build_todo_card(
            "claim_pending",
            "待审核认领申请",
            "失物认领待审核",
            "/pages/admin/lostfound?type=found&claimApplyStatus=pending",
            claim_total,
            claim_timeout_count,
            claim_items,
            "批量通过认领",
        ),
        _build_todo_card(
            "course_task_due",
            "即将截止未完成课程任务",
            "3 天内截止且仍有缺交",
            "/pages/teacher/courses",
            task_total,
            task_timeout_count,
            task_items,
            "批量催交",
        ),
        _build_todo_card(
            "announcement_today_scheduled",
            "今日公告计划发布",
            "今日待发布公告",
            "/pages/admin/admin",
            announcement_total,
            announcement_timeout_count,
            announcement_items,
            "批量立即发布",
        ),
    ]

    flat_items = []
    for card in cards:
        flat_items.extend(card.get("items") or [])
    flat_items = _sort_todo_items(flat_items, sort_by=sort_by, sort_order=sort_order)

    summary = {
        "total": sum(int(card.get("total") or 0) for card in cards),
        "timeoutTotal": sum(int(card.get("timeoutCount") or 0) for card in cards),
        "highPriorityTotal": len([x for x in flat_items if int(x.get("priorityScore") or 0) >= 75]),
    }
    return jsonify(
        {
            "ok": True,
            "data": {
                "generatedAt": now_text,
                "sortBy": sort_by,
                "sortOrder": sort_order,
                "summary": summary,
                "cards": cards,
                "flatItems": flat_items[: max(limit_per_card * 3, 60)],
            },
        }
    )


def _safe_stats_query(sql, params=None):
    try:
        return query(sql, params or ())
    except Exception as e:
        print(f"[warn] admin stats query failed: {e}")
        return []


def _to_stat_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _unwrap_json_response_payload(response):
    target = response
    if isinstance(response, tuple) and response:
        target = response[0]
    if hasattr(target, "get_json"):
        payload = target.get_json(silent=True) or {}
        if isinstance(payload, dict):
            return payload
    return {}


def _get_admin_dashboard_snapshot():
    payload = _unwrap_json_response_payload(admin_stats_dashboard())
    return payload.get("data") if isinstance(payload.get("data"), dict) else {}


def _get_admin_todo_snapshot():
    payload = _unwrap_json_response_payload(admin_todo_center())
    return payload.get("data") if isinstance(payload.get("data"), dict) else {}


def _build_admin_daily_brief_payload():
    dashboard = _get_admin_dashboard_snapshot()
    todo = _get_admin_todo_snapshot()
    overview = dashboard.get("overview") if isinstance(dashboard.get("overview"), dict) else {}
    cards = todo.get("cards") if isinstance(todo.get("cards"), list) else []
    summary = todo.get("summary") if isinstance(todo.get("summary"), dict) else {}
    top_labs = dashboard.get("topLabs30d") if isinstance(dashboard.get("topLabs30d"), list) else []

    highlights = []
    focus_actions = []
    for card in cards[:6]:
        total = _to_stat_int(card.get("total"))
        timeout_count = _to_stat_int(card.get("timeoutCount"))
        title = str(card.get("title") or "").strip()
        if total <= 0 or not title:
            continue
        if timeout_count > 0:
            highlights.append(f"{title} {total} 项，其中超时 {timeout_count} 项。")
        else:
            highlights.append(f"{title} 当前共有 {total} 项。")
        focus_actions.append(
            {
                "title": title,
                "description": str(card.get("description") or "").strip(),
                "jumpUrl": str(card.get("jumpUrl") or "").strip(),
                "priority": "P0" if timeout_count > 0 else "P1" if total >= 5 else "P2",
            }
        )

    top_lab = (top_labs[:1] or [{}])[0] or {}
    if top_lab:
        highlights.append(
            f"近 30 天最热实验室是 {str(top_lab.get('labName') or '-').strip() or '-'}，"
            f"累计 { _to_stat_int(top_lab.get('count')) } 次预约。"
        )
    alarms_today = _to_stat_int(overview.get("alarmsToday"))
    if alarms_today > 0:
        highlights.append(f"今日告警 {alarms_today} 条，建议优先检查实验室环境与设备状态。")

    summary_text = (
        f"当前管理员待办总量 { _to_stat_int(summary.get('total')) } 项，"
        f"高优先级 { _to_stat_int(summary.get('highPriorityTotal')) } 项，"
        f"超时 { _to_stat_int(summary.get('timeoutTotal')) } 项。"
    )
    return {
        "generatedAt": str(todo.get("generatedAt") or dashboard.get("generatedAt") or ""),
        "summaryText": summary_text,
        "riskLevel": "high" if _to_stat_int(summary.get("timeoutTotal")) >= 6 or alarms_today > 0 else "medium" if _to_stat_int(summary.get("highPriorityTotal")) >= 8 else "low",
        "highlights": highlights[:6],
        "focusActions": focus_actions[:5],
    }


def _answer_admin_stats_question(question, dashboard):
    raw = str(question or "").strip()
    compact = re.sub(r"\s+", "", raw)
    top_labs = dashboard.get("topLabs30d") if isinstance(dashboard.get("topLabs30d"), list) else []
    overview = dashboard.get("overview") if isinstance(dashboard.get("overview"), dict) else {}
    users = dashboard.get("users") if isinstance(dashboard.get("users"), dict) else {}
    repair = dashboard.get("repair") if isinstance(dashboard.get("repair"), dict) else {}
    alarms = dashboard.get("alarms") if isinstance(dashboard.get("alarms"), dict) else {}
    equipment = dashboard.get("equipment") if isinstance(dashboard.get("equipment"), dict) else {}
    announcements = dashboard.get("announcements") if isinstance(dashboard.get("announcements"), dict) else {}
    reservations = dashboard.get("reservations") if isinstance(dashboard.get("reservations"), dict) else {}

    if not compact:
        return {
            "intent": "summary",
            "matched": False,
            "answer": (
                f"当前共有 { _to_stat_int(overview.get('usersTotal')) } 个用户，"
                f"{ _to_stat_int(overview.get('reservationsTotal')) } 条预约，"
                f"{ _to_stat_int(overview.get('pendingReservations')) } 条待审批预约。"
            ),
        }

    if "实验室" in compact and any(token in compact for token in ("最多", "最高", "最热", "第一")) and top_labs:
        item = top_labs[0] or {}
        return {
            "intent": "top_lab",
            "matched": True,
            "answer": f"近 30 天预约最热的实验室是 {item.get('labName') or '-'}，累计 { _to_stat_int(item.get('count')) } 次预约。",
        }
    if "待审批" in compact or "待审" in compact:
        return {"intent": "pending_reservations", "matched": True, "answer": f"当前待审批预约共有 { _to_stat_int(overview.get('pendingReservations')) } 条。"}
    if ("今天" in compact or "今日" in compact) and "预约" in compact:
        return {"intent": "today_reservations", "matched": True, "answer": f"今天共有 { _to_stat_int(reservations.get('today')) } 条预约。"}
    if ("今天" in compact or "今日" in compact) and "报修" in compact:
        return {"intent": "today_repairs", "matched": True, "answer": f"今天新增报修 { _to_stat_int(repair.get('today')) } 条。"}
    if ("今天" in compact or "今日" in compact) and ("告警" in compact or "报警" in compact):
        return {"intent": "today_alarms", "matched": True, "answer": f"今天共有 { _to_stat_int(alarms.get('today')) } 条实验室告警。"}
    if "管理员" in compact and "多少" in compact:
        return {"intent": "admin_count", "matched": True, "answer": f"当前管理员账号共有 { _to_stat_int((users.get('byRole') or {}).get('admin')) } 个。"}
    if "教师" in compact and "多少" in compact:
        return {"intent": "teacher_count", "matched": True, "answer": f"当前教师账号共有 { _to_stat_int((users.get('byRole') or {}).get('teacher')) } 个。"}
    if "学生" in compact and "多少" in compact:
        return {"intent": "student_count", "matched": True, "answer": f"当前学生账号共有 { _to_stat_int((users.get('byRole') or {}).get('student')) } 个。"}
    if "设备" in compact and any(token in compact for token in ("维修", "修理", "报修中")):
        return {
            "intent": "equipment_repairing",
            "matched": True,
            "answer": f"当前维修中的设备有 { _to_stat_int(equipment.get('repairing')) } 台，总设备数为 { _to_stat_int(equipment.get('total')) } 台。",
        }
    if "公告" in compact and any(token in compact for token in ("定时", "待发布", "计划")):
        return {"intent": "scheduled_announcements", "matched": True, "answer": f"当前有 { _to_stat_int(announcements.get('scheduled')) } 条定时公告待发布。"}

    return {
        "intent": "summary",
        "matched": False,
        "answer": (
            f"按后台总览看：用户 { _to_stat_int(overview.get('usersTotal')) } 个，"
            f"预约 { _to_stat_int(overview.get('reservationsTotal')) } 条，"
            f"报修 { _to_stat_int(repair.get('total')) } 条。"
        ),
    }


def _build_admin_risk_alerts_payload():
    dashboard = _get_admin_dashboard_snapshot()
    todo = _get_admin_todo_snapshot()
    summary = todo.get("summary") if isinstance(todo.get("summary"), dict) else {}
    alerts = []
    cards = todo.get("cards") if isinstance(todo.get("cards"), list) else []
    for card in cards:
        total = _to_stat_int(card.get("total"))
        timeout_count = _to_stat_int(card.get("timeoutCount"))
        if total <= 0:
            continue
        score = 40 + min(40, total * 2) + min(20, timeout_count * 4)
        if timeout_count > 0 or total >= 8:
            alerts.append(
                {
                    "title": str(card.get("title") or "").strip(),
                    "description": f"当前 {total} 项，超时 {timeout_count} 项。",
                    "level": "high" if timeout_count > 0 else "medium",
                    "score": score,
                    "jumpUrl": str(card.get("jumpUrl") or "").strip(),
                }
            )
    alarms_today = _to_stat_int(((dashboard.get("alarms") or {}).get("today")))
    if alarms_today > 0:
        alerts.append(
            {
                "title": "实验室告警",
                "description": f"今日告警 {alarms_today} 条，建议优先排查。",
                "level": "high",
                "score": 95,
                "jumpUrl": "/pages/admin/labs",
            }
        )
    repairing = _to_stat_int(((dashboard.get("equipment") or {}).get("repairing")))
    total_equipment = max(1, _to_stat_int(((dashboard.get("equipment") or {}).get("total"))))
    if repairing / float(total_equipment) >= 0.15:
        alerts.append(
            {
                "title": "设备维修占比偏高",
                "description": f"当前维修中设备 {repairing} 台，占比约 {round(repairing / float(total_equipment) * 100, 1)}%。",
                "level": "medium",
                "score": 74,
                "jumpUrl": "/pages/admin/equipments",
            }
        )
    prediction_payload = list_equipment_failure_predictions(limit=3, horizon_days=7, auto_refresh=True)
    prediction_items = prediction_payload.get("items") if isinstance(prediction_payload.get("items"), list) else []
    high_prediction_count = len([item for item in prediction_items if str(item.get("riskLevel") or "").strip() == "high"])
    if high_prediction_count > 0:
        alerts.append(
            {
                "title": "设备未来故障风险偏高",
                "description": f"未来 7 天内预计有 {high_prediction_count} 台设备存在高风险故障倾向。",
                "level": "high",
                "score": 88,
                "jumpUrl": "/pages/admin/stats",
            }
        )
    alerts.sort(key=lambda x: (-_to_stat_int(x.get("score")), str(x.get("title") or "")))
    return {
        "generatedAt": str(todo.get("generatedAt") or dashboard.get("generatedAt") or ""),
        "summary": summary,
        "alerts": alerts[:6],
    }


def _build_admin_equipment_health_payload(limit=8):
    payload = list_equipment_failure_predictions(limit=max(1, int(limit or 8)), horizon_days=30, auto_refresh=True)
    raw_items = payload.get("items") if isinstance(payload.get("items"), list) else []
    items = []
    for row in raw_items:
        top_factors = row.get("topFactors") if isinstance(row.get("topFactors"), list) else []
        reason_lines = [f"{str(item.get('label') or '').strip()} +{item.get('score')}" for item in top_factors[:3] if str(item.get("label") or "").strip()]
        if row.get("lastRepairDays") is not None:
            reason_lines.append(f"距最近一次维修 {int(row.get('lastRepairDays') or 0)} 天")
        items.append(
            {
                "equipmentId": int(row.get("equipmentId") or 0),
                "assetCode": str(row.get("assetCode") or "").strip(),
                "name": str(row.get("name") or "").strip(),
                "status": str(row.get("status") or "").strip(),
                "labId": _to_int_or_none(row.get("labId")),
                "labName": str(row.get("labName") or "").strip(),
                "predictDate": str(row.get("predictDate") or "").strip(),
                "horizonDays": int(row.get("horizonDays") or 30),
                "repairCount7d": int(row.get("repairCount7d") or 0),
                "repairCount30d": int(row.get("repairCount30d") or 0),
                "repairCount90d": int(row.get("repairCount90d") or 0),
                "alarmCount30d": int(row.get("alarmCount30d") or 0),
                "borrowCount30d": int(row.get("borrowCount30d") or 0),
                "riskScore": float(row.get("riskScore") or 0),
                "failureProbability": float(row.get("failureProbability") or 0),
                "riskLevel": str(row.get("riskLevel") or "").strip() or "low",
                "predictedIssueType": str(row.get("predictedIssueType") or "").strip() or "other",
                "priority": "P1" if float(row.get("riskScore") or 0) >= 85 else "P2" if float(row.get("riskScore") or 0) >= 65 else "P3",
                "reasonLines": reason_lines[:4],
                "topFactors": top_factors[:5],
                "recommendation": str(row.get("recommendation") or "").strip(),
                "jumpUrl": "/pages/admin/repair_orders",
            }
        )
    return {"generatedAt": str(payload.get("predictDate") or datetime.now().strftime("%Y-%m-%d")), "items": items}


@app.get("/admin/stats/dashboard")
@auth_required(roles=["admin"])
def admin_stats_dashboard():
    now_dt = datetime.now()
    now_text = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    today = now_dt.date()
    today_text = today.strftime("%Y-%m-%d")
    tomorrow_text = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    seven_days_ago_text = (today - timedelta(days=6)).strftime("%Y-%m-%d")
    thirty_days_ago_text = (today - timedelta(days=29)).strftime("%Y-%m-%d")
    today_start = f"{today_text} 00:00:00"
    tomorrow_start = f"{tomorrow_text} 00:00:00"
    seven_days_ago_start = f"{seven_days_ago_text} 00:00:00"
    thirty_days_ago_start = f"{thirty_days_ago_text} 00:00:00"

    user_rows = _safe_stats_query("SELECT role, COUNT(*) AS cnt FROM user GROUP BY role")
    user_by_role = {}
    user_total = 0
    for row in user_rows:
        role = str(row.get("role") or "unknown").strip() or "unknown"
        cnt = _to_stat_int(row.get("cnt"))
        user_by_role[role] = user_by_role.get(role, 0) + cnt
        user_total += cnt

    lab_summary_rows = _safe_stats_query(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN status='free' THEN 1 ELSE 0 END) AS freeCnt,
               SUM(CASE WHEN status='busy' THEN 1 ELSE 0 END) AS busyCnt,
               SUM(capacity) AS totalCapacity,
               SUM(device_count) AS totalDevices
        FROM lab
        """
    )
    lab_summary = (lab_summary_rows or [{}])[0] or {}

    reservation_status_rows = _safe_stats_query("SELECT status, COUNT(*) AS cnt FROM reservation GROUP BY status")
    reservation_by_status = {}
    reservation_total = 0
    for row in reservation_status_rows:
        status = str(row.get("status") or "unknown").strip() or "unknown"
        cnt = _to_stat_int(row.get("cnt"))
        reservation_by_status[status] = reservation_by_status.get(status, 0) + cnt
        reservation_total += cnt
    reservation_today_rows = _safe_stats_query("SELECT COUNT(*) AS cnt FROM reservation WHERE date=%s", (today_text,))
    reservation_today = _to_stat_int(((reservation_today_rows or [{}])[0] or {}).get("cnt"))

    reservation_recent7d_status_rows = _safe_stats_query(
        """
        SELECT status, COUNT(*) AS cnt
        FROM reservation
        WHERE created_at >= %s
        GROUP BY status
        """,
        (seven_days_ago_start,),
    )
    reservation_recent7d_by_status = {}
    reservation_recent7d_total = 0
    for row in reservation_recent7d_status_rows:
        status = str(row.get("status") or "unknown").strip() or "unknown"
        cnt = _to_stat_int(row.get("cnt"))
        reservation_recent7d_by_status[status] = reservation_recent7d_by_status.get(status, 0) + cnt
        reservation_recent7d_total += cnt

    reservation_trend_rows = _safe_stats_query(
        """
        SELECT DATE(created_at) AS day, COUNT(*) AS cnt
        FROM reservation
        WHERE created_at >= %s
        GROUP BY DATE(created_at)
        ORDER BY day ASC
        """,
        (seven_days_ago_start,),
    )
    trend_map = {}
    for row in reservation_trend_rows:
        day_text = str(row.get("day") or "").strip()
        if not day_text:
            continue
        trend_map[day_text] = _to_stat_int(row.get("cnt"))
    reservation_trend_7d = []
    for i in range(7):
        day_dt = today - timedelta(days=6 - i)
        day_text = day_dt.strftime("%Y-%m-%d")
        reservation_trend_7d.append(
            {
                "date": day_text,
                "label": day_dt.strftime("%m-%d"),
                "count": _to_stat_int(trend_map.get(day_text)),
            }
        )

    lost_found_summary_rows = _safe_stats_query(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) AS openCnt,
               SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END) AS closedCnt,
               SUM(CASE WHEN claim_apply_status='pending' THEN 1 ELSE 0 END) AS claimPendingCnt
        FROM lost_found
        """
    )
    lost_found_summary = (lost_found_summary_rows or [{}])[0] or {}

    announcement_summary_rows = _safe_stats_query(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN COALESCE(publish_at, created_at) <= %s THEN 1 ELSE 0 END) AS publishedCnt,
               SUM(CASE WHEN COALESCE(publish_at, created_at) > %s THEN 1 ELSE 0 END) AS scheduledCnt,
               SUM(CASE WHEN is_pinned=1 THEN 1 ELSE 0 END) AS pinnedCnt
        FROM announcement
        """,
        (now_text, now_text),
    )
    announcement_summary = (announcement_summary_rows or [{}])[0] or {}

    recent_announcement_rows = _safe_stats_query(
        """
        SELECT id,
               title,
               publisher_name AS publisherName,
               publish_at AS publishAt,
               created_at AS createdAt,
               is_pinned AS isPinned
        FROM announcement
        ORDER BY is_pinned DESC,
                 COALESCE(pinned_at, '1970-01-01 00:00:00') DESC,
                 COALESCE(publish_at, created_at) DESC,
                 id DESC
        LIMIT 5
        """
    )
    recent_announcements = []
    for row in recent_announcement_rows:
        publish_at_text = _to_text_time(row.get("publishAt") or row.get("createdAt"))
        recent_announcements.append(
            {
                "id": _to_stat_int(row.get("id")),
                "title": str(row.get("title") or "").strip(),
                "publisherName": str(row.get("publisherName") or "").strip(),
                "publishAt": publish_at_text,
                "isPinned": _to_stat_int(row.get("isPinned")) == 1,
                "status": "scheduled" if _to_datetime(publish_at_text) > now_dt else "published",
            }
        )

    equipment_summary_rows = _safe_stats_query(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN status='in_service' THEN 1 ELSE 0 END) AS inServiceCnt,
               SUM(CASE WHEN status='repairing' THEN 1 ELSE 0 END) AS repairingCnt,
               SUM(CASE WHEN status='scrapped' THEN 1 ELSE 0 END) AS scrappedCnt
        FROM equipment
        """
    )
    equipment_summary = (equipment_summary_rows or [{}])[0] or {}

    repair_summary_rows = _safe_stats_query(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN created_at >= %s AND created_at < %s THEN 1 ELSE 0 END) AS todayCnt,
               SUM(CASE WHEN created_at >= %s THEN 1 ELSE 0 END) AS recent7dCnt,
               SUM(CASE WHEN status='submitted' THEN 1 ELSE 0 END) AS submittedCnt,
               SUM(CASE WHEN status='accepted' THEN 1 ELSE 0 END) AS acceptedCnt,
               SUM(CASE WHEN status='processing' THEN 1 ELSE 0 END) AS processingCnt,
               SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completedCnt
        FROM repair_work_order
        """,
        (today_start, tomorrow_start, seven_days_ago_start),
    )
    repair_summary = (repair_summary_rows or [{}])[0] or {}

    alarm_summary_rows = _safe_stats_query(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN created_at >= %s AND created_at < %s THEN 1 ELSE 0 END) AS todayCnt,
               SUM(CASE WHEN created_at >= %s THEN 1 ELSE 0 END) AS recent7dCnt
        FROM lab_sensor_alarm
        """,
        (today_start, tomorrow_start, seven_days_ago_start),
    )
    alarm_summary = (alarm_summary_rows or [{}])[0] or {}

    top_lab_rows = _safe_stats_query(
        """
        SELECT lab_name AS labName,
               COUNT(*) AS cnt,
               SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pendingCnt,
               SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approvedCnt
        FROM reservation
        WHERE created_at >= %s
        GROUP BY lab_name
        ORDER BY cnt DESC
        LIMIT 5
        """,
        (thirty_days_ago_start,),
    )
    top_labs_30d = []
    for row in top_lab_rows:
        top_labs_30d.append(
            {
                "labName": str(row.get("labName") or "").strip() or "未命名实验室",
                "count": _to_stat_int(row.get("cnt")),
                "pendingCount": _to_stat_int(row.get("pendingCnt")),
                "approvedCount": _to_stat_int(row.get("approvedCnt")),
            }
        )

    recent_audit_rows = _safe_stats_query(
        """
        SELECT action,
               operator_name AS operatorName,
               target_type AS targetType,
               target_id AS targetId,
               created_at AS createdAt
        FROM audit_log
        ORDER BY id DESC
        LIMIT 8
        """
    )
    recent_audit = []
    for row in recent_audit_rows:
        recent_audit.append(
            {
                "action": str(row.get("action") or "").strip(),
                "operatorName": str(row.get("operatorName") or "").strip(),
                "targetType": str(row.get("targetType") or "").strip(),
                "targetId": str(row.get("targetId") or "").strip(),
                "createdAt": _to_text_time(row.get("createdAt")),
            }
        )

    overview = {
        "usersTotal": user_total,
        "labsTotal": _to_stat_int(lab_summary.get("total")),
        "reservationsTotal": reservation_total,
        "pendingReservations": _to_stat_int(reservation_by_status.get("pending")),
        "lostFoundOpen": _to_stat_int(lost_found_summary.get("openCnt")),
        "claimPending": _to_stat_int(lost_found_summary.get("claimPendingCnt")),
        "repairToday": _to_stat_int(repair_summary.get("todayCnt")),
        "alarmsToday": _to_stat_int(alarm_summary.get("todayCnt")),
    }

    return jsonify(
        {
            "ok": True,
            "data": {
                "generatedAt": now_text,
                "overview": overview,
                "users": {
                    "total": user_total,
                    "byRole": user_by_role,
                },
                "labs": {
                    "total": _to_stat_int(lab_summary.get("total")),
                    "free": _to_stat_int(lab_summary.get("freeCnt")),
                    "busy": _to_stat_int(lab_summary.get("busyCnt")),
                    "totalCapacity": _to_stat_int(lab_summary.get("totalCapacity")),
                    "totalDevices": _to_stat_int(lab_summary.get("totalDevices")),
                },
                "reservations": {
                    "total": reservation_total,
                    "today": reservation_today,
                    "byStatus": reservation_by_status,
                    "recent7dTotal": reservation_recent7d_total,
                    "recent7dByStatus": reservation_recent7d_by_status,
                    "trend7d": reservation_trend_7d,
                },
                "lostFound": {
                    "total": _to_stat_int(lost_found_summary.get("total")),
                    "open": _to_stat_int(lost_found_summary.get("openCnt")),
                    "closed": _to_stat_int(lost_found_summary.get("closedCnt")),
                    "claimPending": _to_stat_int(lost_found_summary.get("claimPendingCnt")),
                },
                "announcements": {
                    "total": _to_stat_int(announcement_summary.get("total")),
                    "published": _to_stat_int(announcement_summary.get("publishedCnt")),
                    "scheduled": _to_stat_int(announcement_summary.get("scheduledCnt")),
                    "pinned": _to_stat_int(announcement_summary.get("pinnedCnt")),
                    "recent": recent_announcements,
                },
                "equipment": {
                    "total": _to_stat_int(equipment_summary.get("total")),
                    "inService": _to_stat_int(equipment_summary.get("inServiceCnt")),
                    "repairing": _to_stat_int(equipment_summary.get("repairingCnt")),
                    "scrapped": _to_stat_int(equipment_summary.get("scrappedCnt")),
                },
                "repair": {
                    "total": _to_stat_int(repair_summary.get("total")),
                    "today": _to_stat_int(repair_summary.get("todayCnt")),
                    "recent7d": _to_stat_int(repair_summary.get("recent7dCnt")),
                    "byStatus": {
                        "submitted": _to_stat_int(repair_summary.get("submittedCnt")),
                        "accepted": _to_stat_int(repair_summary.get("acceptedCnt")),
                        "processing": _to_stat_int(repair_summary.get("processingCnt")),
                        "completed": _to_stat_int(repair_summary.get("completedCnt")),
                    },
                },
                "alarms": {
                    "total": _to_stat_int(alarm_summary.get("total")),
                    "today": _to_stat_int(alarm_summary.get("todayCnt")),
                    "recent7d": _to_stat_int(alarm_summary.get("recent7dCnt")),
                },
                "topLabs30d": top_labs_30d,
                "recentAudit": recent_audit,
            },
        }
    )


@app.get("/admin/ai/daily-brief")
@auth_required(roles=["admin"])
def admin_ai_daily_brief():
    return jsonify({"ok": True, "data": _build_admin_daily_brief_payload()})


@app.post("/admin/stats/ai-query")
@auth_required(roles=["admin"])
def admin_ai_stats_query():
    payload = request.get_json(force=True) or {}
    question = str(payload.get("question") or "").strip()
    dashboard = _get_admin_dashboard_snapshot()
    answered = _answer_admin_stats_question(question, dashboard)
    return jsonify({"ok": True, "data": {"question": question, **answered}})


@app.get("/admin/ai/risk-alerts")
@auth_required(roles=["admin"])
def admin_ai_risk_alerts():
    return jsonify({"ok": True, "data": _build_admin_risk_alerts_payload()})


@app.get("/admin/ai/equipment-health")
@auth_required(roles=["admin"])
def admin_ai_equipment_health():
    limit = _to_int_or_none(request.args.get("limit")) or 8
    limit = max(1, min(int(limit), 20))
    return jsonify({"ok": True, "data": _build_admin_equipment_health_payload(limit=limit)})


@app.post("/admin/ai/equipment-health/refresh")
@auth_required(roles=["admin"])
def admin_refresh_equipment_health():
    payload = request.get_json(silent=True) or {}
    horizons = payload.get("horizonDaysList")
    if not isinstance(horizons, list):
        horizons = [7, 30]
    result = refresh_equipment_failure_predictions(horizon_days_list=horizons)
    return jsonify({"ok": True, "data": result})


@app.get("/admin/knowledge/documents")
@auth_required(roles=["admin"])
def admin_list_knowledge_documents():
    status = str(request.args.get("status") or "").strip().lower()
    category = _knowledge_normalize_category(request.args.get("category"), default_value="")
    keyword = str(request.args.get("keyword") or "").strip()
    where_sql = " WHERE 1=1"
    params = []
    if status:
        if status not in KNOWLEDGE_DOC_STATUS_SET:
            raise BizError("invalid status", 400)
        where_sql += " AND status=%s"
        params.append(status)
    if category and category != "other":
        where_sql += " AND category=%s"
        params.append(category)
    if keyword:
        where_sql += " AND (title LIKE %s OR summary LIKE %s OR keywords LIKE %s)"
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw])
    rows = query(
        """
        SELECT id,
               title,
               category,
               scope_role AS scopeRole,
               status,
               source_type AS sourceType,
               source_url AS sourceUrl,
               summary,
               keywords,
               chunk_count AS chunkCount,
               last_indexed_at AS lastIndexedAt,
               uploader_id AS uploaderId,
               uploader_name AS uploaderName,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM knowledge_document
        """
        + where_sql
        + """
        ORDER BY updated_at DESC, id DESC
        LIMIT 200
        """,
        tuple(params),
    )
    return jsonify({"ok": True, "data": [_format_knowledge_document_row(row) for row in rows]})


@app.post("/admin/knowledge/documents")
@auth_required(roles=["admin"])
def admin_create_knowledge_document():
    payload = _normalize_knowledge_doc_payload(request.get_json(force=True) or {})
    actor = g.current_user or {}
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            """
            INSERT INTO knowledge_document (
                title, category, scope_role, status, source_type, source_url,
                summary, keywords, source_content, chunk_count, last_indexed_at,
                uploader_id, uploader_name, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, 'text', %s, '', '', %s, 0, NULL, %s, %s, %s, %s)
            """,
            (
                payload.get("title"),
                payload.get("category"),
                payload.get("scopeRole"),
                payload.get("status"),
                payload.get("sourceUrl"),
                payload.get("content"),
                _to_int_or_none(actor.get("id")),
                str(actor.get("username") or "").strip(),
                now_text,
                now_text,
            ),
        )
        return int(cur.lastrowid or 0)

    document_id = run_in_transaction(_tx)
    index_result = rebuild_knowledge_document_chunks(document_id)
    audit_log(
        "admin.knowledge.document.create",
        target_type="knowledge_document",
        target_id=document_id,
        detail={"category": payload.get("category"), "scopeRole": payload.get("scopeRole"), "chunkCount": index_result.get("chunkCount")},
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    rows = query(
        """
        SELECT id,
               title,
               category,
               scope_role AS scopeRole,
               status,
               source_type AS sourceType,
               source_url AS sourceUrl,
               summary,
               keywords,
               chunk_count AS chunkCount,
               last_indexed_at AS lastIndexedAt,
               uploader_id AS uploaderId,
               uploader_name AS uploaderName,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM knowledge_document
        WHERE id=%s
        LIMIT 1
        """,
        (document_id,),
    )
    return jsonify({"ok": True, "data": _format_knowledge_document_row((rows or [{}])[0])})


@app.post("/admin/knowledge/documents/<int:doc_id>")
@auth_required(roles=["admin"])
def admin_update_knowledge_document(doc_id):
    payload = _normalize_knowledge_doc_payload(request.get_json(force=True) or {}, allow_partial=True)
    actor = g.current_user or {}
    rows = query("SELECT id, title, source_content AS sourceContent FROM knowledge_document WHERE id=%s LIMIT 1", (int(doc_id),))
    if not rows:
        raise BizError("knowledge document not found", 404)
    row = rows[0] or {}
    next_title = payload.get("title") or str(row.get("title") or "").strip()
    next_content = payload.get("content") if payload.get("content") else str(row.get("sourceContent") or "").strip()
    next_category = payload.get("category") or "other"
    next_scope_role = payload.get("scopeRole") or "all"
    next_status = payload.get("status") or "draft"
    next_source_url = payload.get("sourceUrl") or ""
    execute(
        """
        UPDATE knowledge_document
        SET title=%s,
            category=%s,
            scope_role=%s,
            status=%s,
            source_url=%s,
            source_content=%s,
            updated_at=%s
        WHERE id=%s
        """,
        (next_title, next_category, next_scope_role, next_status, next_source_url, next_content, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(doc_id)),
    )
    index_result = rebuild_knowledge_document_chunks(doc_id)
    audit_log(
        "admin.knowledge.document.update",
        target_type="knowledge_document",
        target_id=doc_id,
        detail={"chunkCount": index_result.get("chunkCount")},
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    detail_rows = query(
        """
        SELECT id,
               title,
               category,
               scope_role AS scopeRole,
               status,
               source_type AS sourceType,
               source_url AS sourceUrl,
               summary,
               keywords,
               chunk_count AS chunkCount,
               last_indexed_at AS lastIndexedAt,
               uploader_id AS uploaderId,
               uploader_name AS uploaderName,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM knowledge_document
        WHERE id=%s
        LIMIT 1
        """,
        (int(doc_id),),
    )
    return jsonify({"ok": True, "data": _format_knowledge_document_row((detail_rows or [{}])[0])})


@app.post("/admin/knowledge/documents/<int:doc_id>/status")
@auth_required(roles=["admin"])
def admin_update_knowledge_document_status(doc_id):
    payload = request.get_json(force=True) or {}
    status = str(payload.get("status") or "").strip().lower()
    if status not in KNOWLEDGE_DOC_STATUS_SET:
        raise BizError("invalid status", 400)
    exists = query("SELECT id FROM knowledge_document WHERE id=%s LIMIT 1", (int(doc_id),))
    if not exists:
        raise BizError("knowledge document not found", 404)
    execute("UPDATE knowledge_document SET status=%s, updated_at=%s WHERE id=%s", (status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(doc_id)))
    return jsonify({"ok": True, "data": {"id": int(doc_id), "status": status}})


@app.post("/admin/knowledge/documents/<int:doc_id>/reindex")
@auth_required(roles=["admin"])
def admin_reindex_knowledge_document(doc_id):
    result = rebuild_knowledge_document_chunks(doc_id)
    return jsonify({"ok": True, "data": result})


@app.post("/knowledge/ask")
@auth_required()
def ask_knowledge():
    payload = request.get_json(force=True) or {}
    question = str(payload.get("question") or payload.get("query") or "").strip()
    if not question:
        raise BizError("question required", 400)
    current_user = g.current_user or {}
    current_role = str(current_user.get("role") or "").strip().lower()
    result = ask_knowledge_base(question, current_role=current_role, actor=current_user)
    if not result.get("matched"):
        return jsonify({"ok": True, "data": {"matched": False, "answer": "", "sources": [], "queryLogId": 0}})
    return jsonify(
        {
            "ok": True,
            "data": {
                "matched": True,
                "answer": str(result.get("answer") or "").strip(),
                "sources": result.get("sources") or [],
                "queryLogId": int(result.get("queryLogId") or 0),
            },
        }
    )


@app.post("/knowledge/feedback")
@auth_required()
def feedback_knowledge():
    payload = request.get_json(force=True) or {}
    query_log_id = _to_int_or_none(payload.get("queryLogId"))
    if not query_log_id or int(query_log_id) <= 0:
        raise BizError("queryLogId required", 400)
    helpful = _coerce_bool(payload.get("helpful"), "helpful", default_value=True)
    comment = str(payload.get("comment") or "").strip()[:255]
    current_user = g.current_user or {}
    new_id = execute_insert(
        """
        INSERT INTO knowledge_feedback (query_log_id, user_id, username, helpful, comment, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            int(query_log_id),
            _to_int_or_none(current_user.get("id")),
            str(current_user.get("username") or "").strip(),
            1 if helpful else 0,
            comment,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    return jsonify({"ok": True, "data": {"id": int(new_id or 0)}})


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
    result = _update_user_role(uid, "admin", "admin.user.promote")
    return jsonify({"ok": True, "data": {"id": result["id"], "role": result["role"]}})


@app.post("/users/<int:uid>/demote")
@auth_required(roles=["admin"])
def demote_user(uid):
    result = _update_user_role(uid, "student", "admin.user.demote")
    return jsonify({"ok": True, "data": {"id": result["id"], "role": result["role"]}})


@app.post("/users/<int:uid>/set-role")
@auth_required(roles=["admin"])
def set_user_role(uid):
    data = request.get_json(force=True) or {}
    target_role = data.get("role")
    result = _update_user_role(uid, target_role, "admin.user.set_role")
    return jsonify({"ok": True, "data": {"id": result["id"], "role": result["role"]}})


@app.post("/users/<int:uid>/delete")
@auth_required(roles=["admin"])
def delete_user(uid):
    target = _query_admin_user_row(uid)
    if not target:
        raise BizError("user not found", 404)

    current_user = g.current_user or {}
    target_username = str(target.get("username") or "").strip()
    _assert_user_editable(target, current_user, block_self=True)

    def _tx(cur):
        cur.execute("DELETE FROM auth_refresh_token WHERE user_id=%s", (uid,))
        cur.execute("DELETE FROM user WHERE id=%s", (uid,))
        if int(cur.rowcount or 0) <= 0:
            raise BizError("user not found", 404)

    run_in_transaction(_tx)
    audit_log(
        "admin.user.delete",
        target_type="user",
        target_id=uid,
        detail={
            "targetUsername": target_username,
            "targetRole": str(target.get("role") or ""),
        },
        actor={
            "id": current_user.get("id"),
            "username": current_user.get("username"),
            "role": current_user.get("role"),
        },
    )
    return jsonify({"ok": True, "data": {"id": int(uid)}})


@app.post("/users/<int:uid>/freeze")
@auth_required(roles=["admin"])
def freeze_user(uid):
    target = _query_admin_user_row(uid)
    if not target:
        raise BizError("user not found", 404)
    actor = g.current_user or {}
    _assert_user_editable(target, actor, block_self=True)

    if int(target.get("isFrozen") or 0) == 1:
        return jsonify({"ok": True, "data": {"id": int(uid), "isFrozen": 1, "changed": False}})

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute("UPDATE user SET is_frozen=1 WHERE id=%s", (uid,))
        cur.execute("UPDATE auth_refresh_token SET revoked_at=%s WHERE user_id=%s AND revoked_at IS NULL", (now_text, uid))

    run_in_transaction(_tx)
    audit_log(
        "admin.user.freeze",
        target_type="user",
        target_id=uid,
        detail={"targetUsername": str(target.get("username") or "").strip()},
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": {"id": int(uid), "isFrozen": 1, "changed": True}})


@app.post("/users/<int:uid>/unfreeze")
@auth_required(roles=["admin"])
def unfreeze_user(uid):
    target = _query_admin_user_row(uid)
    if not target:
        raise BizError("user not found", 404)
    actor = g.current_user or {}
    if str(target.get("username") or "").strip() == "admin1":
        raise BizError("admin1 cannot be modified", 409)

    if int(target.get("isFrozen") or 0) == 0:
        return jsonify({"ok": True, "data": {"id": int(uid), "isFrozen": 0, "changed": False}})

    execute("UPDATE user SET is_frozen=0 WHERE id=%s", (uid,))
    audit_log(
        "admin.user.unfreeze",
        target_type="user",
        target_id=uid,
        detail={"targetUsername": str(target.get("username") or "").strip()},
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": {"id": int(uid), "isFrozen": 0, "changed": True}})


@app.post("/users/<int:uid>/reset-password")
@auth_required(roles=["admin"])
def reset_user_password(uid):
    data = request.get_json(force=True) or {}
    provided = str(data.get("newPassword") or "").strip()
    target_password = provided or DEFAULT_ADMIN_RESET_PASSWORD
    if len(target_password) < 6:
        raise BizError("newPassword too short", 400)

    target = _query_admin_user_row(uid)
    if not target:
        raise BizError("user not found", 404)
    actor = g.current_user or {}
    _assert_user_editable(target, actor, block_self=True)

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute("UPDATE user SET password_hash=%s WHERE id=%s", (generate_password_hash(target_password), uid))
        cur.execute("UPDATE auth_refresh_token SET revoked_at=%s WHERE user_id=%s AND revoked_at IS NULL", (now_text, uid))

    run_in_transaction(_tx)
    audit_log(
        "admin.user.reset_password",
        target_type="user",
        target_id=uid,
        detail={
            "targetUsername": str(target.get("username") or "").strip(),
            "useDefaultPassword": not bool(provided),
        },
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "id": int(uid),
                "changed": True,
                "temporaryPassword": target_password if not provided else "",
            },
        }
    )


def _normalize_admin_create_user_payload(payload):
    data = payload if isinstance(payload, dict) else {}
    username = str(data.get("username") or "").strip()
    if not username:
        raise BizError("username required", 400)
    if len(username) > 64:
        raise BizError("username too long", 400)

    role = _normalize_role(data.get("role") or "student")
    if role not in USER_ROLES:
        raise BizError("invalid role", 400)

    nickname = _normalize_profile_nickname(data.get("nickname") or "")
    phone = _normalize_profile_phone(data.get("phone") or "")
    class_name = _normalize_profile_class_name(data.get("className") or "")
    graduation_year = _normalize_optional_int(data.get("graduationYear"), "graduationYear", min_value=0, max_value=2200)
    graduation_year = int(graduation_year or 0)
    is_active = 1 if _coerce_bool(data.get("isActive"), "isActive", default_value=True) else 0
    is_frozen = 1 if _coerce_bool(data.get("isFrozen"), "isFrozen", default_value=False) else 0

    password = str(data.get("password") or data.get("initialPassword") or "").strip()
    default_password = str(data.get("defaultPassword") or DEFAULT_ADMIN_RESET_PASSWORD or "").strip()
    if data.get("defaultPassword") not in (None, "") and len(default_password) < 6:
        raise BizError("defaultPassword too short", 400)
    if not password:
        password = username if role == "student" else default_password
    if len(password) < 6:
        raise BizError("password too short", 400)

    if role == "student":
        if not class_name:
            raise BizError("className required", 400)
        if graduation_year <= 0:
            raise BizError("graduationYear required", 400)

    return {
        "username": username,
        "role": role,
        "password": password,
        "nickname": nickname,
        "phone": phone,
        "className": class_name,
        "graduationYear": graduation_year,
        "isActive": is_active,
        "isFrozen": is_frozen,
    }


def _admin_import_user_rows(rows, *, update_if_exists=True, default_password=""):
    inserted = 0
    updated = 0
    skipped = 0
    failed = 0
    errors = []

    for idx, raw in enumerate(rows or [], start=1):
        raw_username = ""
        try:
            row = raw if isinstance(raw, dict) else {}
            raw_username = str(row.get("username") or "")
            username = str(row.get("username") or "").strip()
            if not username:
                raise BizError("username required", 400)
            if len(username) > 64:
                raise BizError("username too long", 400)

            role = _normalize_role(row.get("role") or "student")
            if role not in USER_ROLES:
                raise BizError("invalid role", 400)

            class_name = _normalize_profile_class_name(row.get("className") or "")
            graduation_year = _normalize_optional_int(row.get("graduationYear"), "graduationYear", min_value=0, max_value=2200)
            graduation_year = int(graduation_year or 0)

            nickname = _normalize_profile_nickname(row.get("nickname") or "")
            phone = _normalize_profile_phone(row.get("phone") or "")
            password = str(row.get("password") or "").strip()
            if password and len(password) < 6:
                raise BizError("password too short", 400)

            is_active = 1 if _coerce_bool(row.get("isActive"), "isActive", default_value=True) else 0
            is_frozen = 1 if _coerce_bool(row.get("isFrozen"), "isFrozen", default_value=False) else 0

            existing_rows = query("SELECT id, username FROM user WHERE username=%s LIMIT 1", (username,))
            if existing_rows:
                existing_id = int(existing_rows[0].get("id") or 0)
                if username == "admin1":
                    skipped += 1
                    continue
                if not update_if_exists:
                    skipped += 1
                    continue

                if password:
                    execute(
                        """
                        UPDATE user
                        SET role=%s,
                            password_hash=%s,
                            nickname=%s,
                            phone=%s,
                            class_name=%s,
                            graduation_year=%s,
                            is_active=%s,
                            is_frozen=%s
                        WHERE id=%s
                        """,
                        (
                            role,
                            generate_password_hash(password),
                            nickname,
                            phone,
                            class_name,
                            graduation_year,
                            is_active,
                            is_frozen,
                            existing_id,
                        ),
                    )
                else:
                    execute(
                        """
                        UPDATE user
                        SET role=%s,
                            nickname=%s,
                            phone=%s,
                            class_name=%s,
                            graduation_year=%s,
                            is_active=%s,
                            is_frozen=%s
                        WHERE id=%s
                        """,
                        (role, nickname, phone, class_name, graduation_year, is_active, is_frozen, existing_id),
                    )
                updated += 1
                continue

            final_password = password or default_password
            if len(final_password) < 6:
                raise BizError("password too short", 400)
            execute_insert(
                """
                INSERT INTO user (
                    username,
                    role,
                    password_hash,
                    nickname,
                    phone,
                    class_name,
                    graduation_year,
                    is_active,
                    is_frozen
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    username,
                    role,
                    generate_password_hash(final_password),
                    nickname,
                    phone,
                    class_name,
                    graduation_year,
                    is_active,
                    is_frozen,
                ),
            )
            inserted += 1
        except BizError as e:
            failed += 1
            errors.append({"row": idx, "username": raw_username, "reason": e.msg})
        except Exception as e:
            failed += 1
            errors.append({"row": idx, "username": raw_username, "reason": str(e)})

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "errors": errors[:200],
    }


@app.post("/users")
@auth_required(roles=["admin"])
def create_user():
    payload = _normalize_admin_create_user_payload(request.get_json(force=True) or {})
    existing_rows = query("SELECT id FROM user WHERE username=%s LIMIT 1", (payload["username"],))
    if existing_rows:
        raise BizError("user exists", 409)

    user_id = execute_insert(
        """
        INSERT INTO user (
            username,
            role,
            password_hash,
            nickname,
            phone,
            class_name,
            graduation_year,
            is_active,
            is_frozen
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            payload["username"],
            payload["role"],
            generate_password_hash(payload["password"]),
            payload["nickname"],
            payload["phone"],
            payload["className"],
            payload["graduationYear"],
            payload["isActive"],
            payload["isFrozen"],
        ),
    )

    actor = g.current_user or {}
    audit_log(
        "admin.user.create",
        target_type="user",
        target_id=user_id,
        detail={
            "targetUsername": payload["username"],
            "targetRole": payload["role"],
            "className": payload["className"],
            "graduationYear": int(payload["graduationYear"] or 0),
            "initialPasswordMode": "username" if payload["role"] == "student" and payload["password"] == payload["username"] else "custom",
        },
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )

    created = _query_admin_user_row(user_id)
    return jsonify(
        {
            "ok": True,
            "data": {
                "user": _format_user_admin_row(created),
                "initialPassword": payload["password"],
            },
        }
    )


@app.post("/users/batch-generate-students")
@auth_required(roles=["admin"])
def batch_generate_students():
    data = request.get_json(force=True) or {}
    prefix = str(data.get("prefix") or "").strip()
    if not prefix:
        raise BizError("prefix required", 400)
    if len(prefix) > 48:
        raise BizError("prefix too long", 400)

    start_no = _normalize_non_negative_int(data.get("startNo"), "startNo", default_value=1, max_value=99999999)
    count = _normalize_non_negative_int(data.get("count"), "count", default_value=0, max_value=500)
    number_width = _normalize_non_negative_int(data.get("numberWidth"), "numberWidth", default_value=2, max_value=16)
    if start_no <= 0:
        raise BizError("invalid startNo", 400)
    if count <= 0:
        raise BizError("count required", 400)
    if number_width <= 0:
        raise BizError("invalid numberWidth", 400)

    class_name = _normalize_profile_class_name(data.get("className") or "")
    if not class_name:
        raise BizError("className required", 400)
    graduation_year = _normalize_optional_int(data.get("graduationYear"), "graduationYear", min_value=2000, max_value=2200)
    if graduation_year is None:
        raise BizError("graduationYear required", 400)

    update_if_exists = _coerce_bool(data.get("updateIfExists"), "updateIfExists", default_value=False)
    dry_run = _coerce_bool(data.get("dryRun"), "dryRun", default_value=False)

    rows = []
    preview = []
    for offset in range(count):
        seq = start_no + offset
        suffix = str(seq).zfill(number_width)
        username = f"{prefix}{suffix}"
        if len(username) > 64:
            raise BizError("generated username too long", 400)
        item = {
            "username": username,
            "role": "student",
            "password": username,
            "className": class_name,
            "graduationYear": int(graduation_year),
            "isActive": True,
            "isFrozen": False,
        }
        rows.append(item)
        preview.append(
            {
                "username": username,
                "password": username,
                "className": class_name,
                "graduationYear": int(graduation_year),
            }
        )

    if dry_run:
        return jsonify(
            {
                "ok": True,
                "data": {
                    "dryRun": True,
                    "count": count,
                    "startNo": start_no,
                    "endNo": start_no + count - 1,
                    "preview": preview[:500],
                },
            }
        )

    result = _admin_import_user_rows(rows, update_if_exists=update_if_exists, default_password=DEFAULT_ADMIN_RESET_PASSWORD)
    actor = g.current_user or {}
    audit_log(
        "admin.user.batch_generate_students",
        target_type="user",
        target_id="batch",
        detail={
            "prefix": prefix,
            "startNo": int(start_no),
            "count": int(count),
            "numberWidth": int(number_width),
            "className": class_name,
            "graduationYear": int(graduation_year),
            "updateIfExists": bool(update_if_exists),
            "inserted": int(result.get("inserted") or 0),
            "updated": int(result.get("updated") or 0),
            "skipped": int(result.get("skipped") or 0),
            "failed": int(result.get("failed") or 0),
        },
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                **result,
                "count": count,
                "startNo": start_no,
                "endNo": start_no + count - 1,
            },
        }
    )


@app.post("/users/import")
@auth_required(roles=["admin"])
def import_users():
    data = request.get_json(force=True) or {}
    rows = data.get("rows")
    if not isinstance(rows, list):
        rows = _split_import_text_rows(data.get("text"))
    update_if_exists = _coerce_bool(data.get("updateIfExists"), "updateIfExists", default_value=True)

    default_password = str(data.get("defaultPassword") or DEFAULT_ADMIN_RESET_PASSWORD or "").strip()
    if len(default_password) < 6:
        raise BizError("defaultPassword too short", 400)

    if not rows:
        raise BizError("rows required", 400)
    if len(rows) > 2000:
        raise BizError("rows too many", 400)

    actor = g.current_user or {}
    result = _admin_import_user_rows(rows, update_if_exists=update_if_exists, default_password=default_password)

    audit_log(
        "admin.user.import",
        target_type="user",
        target_id="batch",
        detail={
            "inserted": int(result.get("inserted") or 0),
            "updated": int(result.get("updated") or 0),
            "skipped": int(result.get("skipped") or 0),
            "failed": int(result.get("failed") or 0),
            "updateIfExists": bool(update_if_exists),
        },
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    return jsonify(
        {
            "ok": True,
            "data": result,
        }
    )


@app.post("/users/batch-set-role")
@auth_required(roles=["admin"])
def batch_set_user_role():
    data = request.get_json(force=True) or {}
    target_role = _normalize_role(data.get("role"))
    if target_role not in USER_ROLES:
        raise BizError("invalid role", 400)

    ids = _normalize_ids(data.get("ids"))
    usernames = _normalize_usernames(data.get("usernames"))
    if not ids and not usernames:
        raise BizError("ids or usernames required", 400)

    actor = g.current_user or {}
    user_map = {}
    if ids:
        placeholders, id_params = _build_in_placeholders(ids)
        rows = query(
            f"""
            SELECT id,
                   username,
                   role
            FROM user
            WHERE id IN ({placeholders})
            """,
            tuple(id_params),
        )
        for row in rows:
            user_map[int(row.get("id") or 0)] = row
    if usernames:
        placeholders, name_params = _build_in_placeholders(usernames)
        rows = query(
            f"""
            SELECT id,
                   username,
                   role
            FROM user
            WHERE username IN ({placeholders})
            """,
            tuple(name_params),
        )
        for row in rows:
            user_map[int(row.get("id") or 0)] = row

    target_rows = list(user_map.values())
    found_ids = {int(x.get("id") or 0) for x in target_rows}
    found_names = {str(x.get("username") or "").strip() for x in target_rows}
    missing_ids = [x for x in ids if int(x) not in found_ids]
    missing_names = [x for x in usernames if x not in found_names]

    changed = 0
    unchanged = 0
    skipped = []
    for row in target_rows:
        uid = int(row.get("id") or 0)
        username = str(row.get("username") or "").strip()
        old_role = str(row.get("role") or "").strip()
        try:
            _assert_user_editable(row, actor, block_self=True)
        except BizError as e:
            skipped.append({"id": uid, "username": username, "reason": e.msg})
            continue

        if old_role == target_role:
            unchanged += 1
            continue
        execute("UPDATE user SET role=%s WHERE id=%s", (target_role, uid))
        changed += 1

    audit_log(
        "admin.user.batch_set_role",
        target_type="user",
        target_id="batch",
        detail={
            "targetRole": target_role,
            "requestedCount": len(ids) + len(usernames),
            "foundCount": len(target_rows),
            "changed": changed,
            "unchanged": unchanged,
            "skipped": len(skipped),
            "missingIdCount": len(missing_ids),
            "missingUsernameCount": len(missing_names),
        },
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "changed": changed,
                "unchanged": unchanged,
                "skipped": skipped,
                "missingIds": missing_ids,
                "missingUsernames": missing_names,
            },
        }
    )


@app.post("/users/batch-deactivate-graduates")
@auth_required(roles=["admin"])
def batch_deactivate_graduates():
    data = request.get_json(force=True) or {}
    graduation_year = _normalize_optional_int(data.get("graduationYear"), "graduationYear", min_value=2000, max_value=2200)
    if graduation_year is None:
        raise BizError("graduationYear required", 400)

    mode = str(data.get("mode") or "eq").strip().lower()
    if mode not in ("eq", "lte"):
        raise BizError("invalid mode", 400)
    class_keyword = str(data.get("classKeyword") or "").strip()
    if len(class_keyword) > 64:
        raise BizError("classKeyword too long", 400)
    dry_run = _coerce_bool(data.get("dryRun"), "dryRun", default_value=False)

    where_parts = ["role='student'", "graduation_year>0"]
    params = []
    if mode == "lte":
        where_parts.append("graduation_year<=%s")
    else:
        where_parts.append("graduation_year=%s")
    params.append(int(graduation_year))
    if class_keyword:
        where_parts.append("class_name LIKE %s")
        params.append(f"%{class_keyword}%")

    rows = query(
        f"""
        SELECT id,
               username,
               role,
               class_name AS className,
               graduation_year AS graduationYear,
               is_active AS isActive,
               is_frozen AS isFrozen
        FROM user
        WHERE {" AND ".join(where_parts)}
        ORDER BY id ASC
        """,
        tuple(params),
    )

    actor = g.current_user or {}
    target_ids = []
    preview = []
    skipped = []
    for row in rows:
        uid = int(row.get("id") or 0)
        username = str(row.get("username") or "").strip()
        try:
            _assert_user_editable(row, actor, block_self=True)
        except BizError as e:
            skipped.append({"id": uid, "username": username, "reason": e.msg})
            continue
        target_ids.append(uid)
        preview.append(
            {
                "id": uid,
                "username": username,
                "className": str(row.get("className") or "").strip(),
                "graduationYear": int(row.get("graduationYear") or 0),
                "isActive": 1 if int(row.get("isActive") or 0) == 1 else 0,
                "isFrozen": 1 if int(row.get("isFrozen") or 0) == 1 else 0,
            }
        )

    if dry_run or not target_ids:
        return jsonify(
            {
                "ok": True,
                "data": {
                    "dryRun": bool(dry_run),
                    "matched": len(target_ids),
                    "deactivated": 0,
                    "revokedTokens": 0,
                    "skipped": skipped,
                    "preview": preview[:200],
                },
            }
        )

    placeholders, id_params = _build_in_placeholders(target_ids)
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            f"UPDATE user SET is_active=0, is_frozen=0 WHERE id IN ({placeholders})",
            tuple(id_params),
        )
        deactivated = int(cur.rowcount or 0)
        cur.execute(
            f"UPDATE auth_refresh_token SET revoked_at=%s WHERE user_id IN ({placeholders}) AND revoked_at IS NULL",
            tuple([now_text] + list(id_params)),
        )
        revoked = int(cur.rowcount or 0)
        return {"deactivated": deactivated, "revoked": revoked}

    result = run_in_transaction(_tx)
    audit_log(
        "admin.user.batch_deactivate_graduates",
        target_type="user",
        target_id="batch",
        detail={
            "graduationYear": int(graduation_year),
            "mode": mode,
            "classKeyword": class_keyword,
            "deactivated": int((result or {}).get("deactivated") or 0),
            "revokedTokens": int((result or {}).get("revoked") or 0),
            "matched": len(target_ids),
            "skipped": len(skipped),
        },
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "dryRun": False,
                "matched": len(target_ids),
                "deactivated": int((result or {}).get("deactivated") or 0),
                "revokedTokens": int((result or {}).get("revoked") or 0),
                "skipped": skipped,
            },
        }
    )


