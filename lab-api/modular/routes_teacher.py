from . import core as _core

for _k, _v in _core.__dict__.items():
    if _k.startswith("__"):
        continue
    globals()[_k] = _v

del _k, _v, _core

COURSE_STATUS_SET = {"enabled", "disabled", "deleted"}
TASK_FILE_STATUS_SET = {"active", "deleted"}
TASK_FILE_SUBDIR = "task_files"
TASK_FILE_MAX_SIZE_BYTES = max(1, int(env_int("TASK_FILE_MAX_SIZE_MB", 200))) * 1024 * 1024
TASK_SUBMISSION_STATUS_SET = {"active", "deleted"}
TASK_REVIEW_STATUS_SET = {"pending", "approved", "rejected"}
TASK_SUBMISSION_SUBDIR = "task_submissions"
TASK_SUBMISSION_MAX_SIZE_BYTES = max(1, int(env_int("TASK_SUBMISSION_MAX_SIZE_MB", 200))) * 1024 * 1024
COURSE_CODE_PATTERN = re.compile(r"^\d{6}$")


def _normalize_course_status(raw_status, allow_deleted=False):
    status = str(raw_status or "").strip().lower()
    if not status:
        return "enabled"
    if status not in COURSE_STATUS_SET:
        raise BizError("invalid course status", 400)
    if not allow_deleted and status == "deleted":
        raise BizError("invalid course status", 400)
    return status


def _normalize_course_code(raw_code):
    course_code = str(raw_code or "").strip()
    if not COURSE_CODE_PATTERN.match(course_code):
        raise BizError("invalid courseCode", 400)
    return course_code


def _build_course_code_candidate():
    return str((uuid.uuid4().int % 900000) + 100000)


def _generate_course_code_with_cur(cur):
    for _ in range(100):
        candidate = _build_course_code_candidate()
        cur.execute("SELECT id FROM course WHERE course_code=%s LIMIT 1", (candidate,))
        if cur.fetchone():
            continue
        return candidate
    raise BizError("course code busy", 500)


def _normalize_course_class_name(raw_class_name):
    class_name = str(raw_class_name or "").strip()
    if not class_name:
        raise BizError("className required", 400)
    if len(class_name) > 64:
        raise BizError("className too long", 400)
    return class_name


def _normalize_task_title(raw_title):
    title = str(raw_title or "").strip()
    if not title:
        raise BizError("title required", 400)
    if len(title) > 160:
        raise BizError("title too long", 400)
    return title


def _normalize_task_description(raw_description):
    description = str(raw_description or "").strip()
    if len(description) > 5000:
        raise BizError("description too long", 400)
    return description


def _normalize_task_review_status(raw_status, allow_empty=False):
    status = str(raw_status or "").strip().lower()
    if not status:
        if allow_empty:
            return ""
        raise BizError("reviewStatus required", 400)
    if status not in TASK_REVIEW_STATUS_SET:
        raise BizError("invalid reviewStatus", 400)
    return status


def _parse_task_review_status_filter(raw_status):
    status = str(raw_status or "").strip().lower()
    if not status or status == "all":
        return None
    if status not in TASK_REVIEW_STATUS_SET:
        raise BizError("invalid reviewStatus", 400)
    return status


def _normalize_task_review_score(raw_score, allow_empty=True):
    if raw_score in (None, ""):
        if allow_empty:
            return None
        raise BizError("reviewScore required", 400)

    text = str(raw_score).strip()
    if not text:
        if allow_empty:
            return None
        raise BizError("reviewScore required", 400)
    try:
        score = float(text)
    except (TypeError, ValueError):
        raise BizError("invalid reviewScore", 400)
    if score != score or score in (float("inf"), float("-inf")):
        raise BizError("invalid reviewScore", 400)
    if score < 0 or score > 100:
        raise BizError("reviewScore out of range", 400)
    return round(score, 2)


def _normalize_task_review_note(raw_note):
    note = str(raw_note or "").strip()
    if len(note) > 255:
        raise BizError("reviewNote too long", 400)
    return note


def _normalize_task_submission_text(raw_text):
    text = str(raw_text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""
    if len(text) > 20000:
        raise BizError("textContent too long", 400)
    return text


def _parse_pagination(page_raw, page_size_raw, default_page=1, default_page_size=20):
    page = _to_int_or_none(page_raw)
    page_size = _to_int_or_none(page_size_raw)
    if page is None:
        page = int(default_page)
    if page_size is None:
        page_size = int(default_page_size)
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 200))
    offset = (int(page) - 1) * int(page_size)
    return int(page), int(page_size), int(offset)


def _normalize_lab_id(raw_lab_id):
    if raw_lab_id in (None, ""):
        return None
    lab_id = _to_int_or_none(raw_lab_id)
    if lab_id is None or int(lab_id) <= 0:
        raise BizError("invalid labId", 400)
    return int(lab_id)


def _normalize_deadline(raw_deadline):
    text = str(raw_deadline or "").strip()
    if not text:
        return None
    fixed = text.replace("T", " ").replace("/", "-")
    fmts = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")
    parsed = None
    for fmt in fmts:
        try:
            parsed = datetime.strptime(fixed, fmt)
            break
        except ValueError:
            continue
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            raise BizError("invalid deadline", 400)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _parse_task_deadline_datetime(raw_deadline):
    text = str(raw_deadline or "").strip()
    if not text:
        return None
    fixed = text.replace("T", " ").replace("/", "-")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(fixed, fmt)
            if fmt == "%Y-%m-%d":
                parsed = parsed.replace(hour=23, minute=59, second=59)
            return parsed
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def _build_auto_notice_message(course_name, task_title, deadline_text, reminder_kind):
    c_name = str(course_name or "").strip() or "课程"
    t_title = str(task_title or "").strip() or "任务"
    deadline = str(deadline_text or "").strip() or "-"
    if reminder_kind == "overdue":
        return f"课程《{c_name}》任务《{t_title}》已截止（{deadline}），你仍未提交作业，请尽快补交。"
    return f"课程《{c_name}》任务《{t_title}》将于 {deadline} 截止，你当前尚未提交作业。"


def _format_course_row(row):
    item = row or {}
    return {
        "id": int(item.get("id") or 0),
        "name": str(item.get("name") or "").strip(),
        "description": str(item.get("description") or "").strip(),
        "className": str(item.get("className") or "").strip(),
        "courseCode": str(item.get("courseCode") or "").strip(),
        "teacherId": _to_int_or_none(item.get("teacherId")),
        "teacherUserName": str(item.get("teacherUserName") or "").strip(),
        "status": str(item.get("status") or "").strip(),
        "taskCount": int(item.get("taskCount") or 0),
        "createdAt": _to_text_time(item.get("createdAt")),
        "updatedAt": _to_text_time(item.get("updatedAt")),
    }


def _format_task_row(row):
    item = row or {}
    return {
        "id": int(item.get("id") or 0),
        "courseId": int(item.get("courseId") or 0),
        "title": str(item.get("title") or "").strip(),
        "description": str(item.get("description") or "").strip(),
        "labId": _to_int_or_none(item.get("labId")),
        "deadline": _to_text_time(item.get("deadline")),
        "teacherId": _to_int_or_none(item.get("teacherId")),
        "teacherUserName": str(item.get("teacherUserName") or "").strip(),
        "status": str(item.get("status") or "").strip(),
        "createdAt": _to_text_time(item.get("createdAt")),
        "updatedAt": _to_text_time(item.get("updatedAt")),
    }


def _format_task_file_row(row):
    item = row or {}
    return {
        "id": int(item.get("id") or 0),
        "taskId": int(item.get("taskId") or 0),
        "courseId": int(item.get("courseId") or 0),
        "fileName": str(item.get("fileName") or "").strip(),
        "fileUrl": str(item.get("fileUrl") or "").strip(),
        "fileSize": int(item.get("fileSize") or 0),
        "mimeType": str(item.get("mimeType") or "").strip(),
        "uploaderId": _to_int_or_none(item.get("uploaderId")),
        "uploaderUserName": str(item.get("uploaderUserName") or "").strip(),
        "status": str(item.get("status") or "").strip(),
        "createdAt": _to_text_time(item.get("createdAt")),
        "updatedAt": _to_text_time(item.get("updatedAt")),
    }


def _format_task_submission_row(row):
    item = row or {}
    review_status = str(item.get("reviewStatus") or "").strip().lower()
    if review_status not in TASK_REVIEW_STATUS_SET:
        review_status = "pending"
    review_score = None
    review_score_raw = item.get("reviewScore")
    if review_score_raw not in (None, ""):
        try:
            review_score = round(float(review_score_raw), 2)
        except (TypeError, ValueError):
            review_score = None
    return {
        "id": int(item.get("id") or 0),
        "taskId": int(item.get("taskId") or 0),
        "courseId": int(item.get("courseId") or 0),
        "courseName": str(item.get("courseName") or "").strip(),
        "taskTitle": str(item.get("taskTitle") or "").strip(),
        "studentId": _to_int_or_none(item.get("studentId")),
        "studentUserName": str(item.get("studentUserName") or "").strip(),
        "studentDisplayName": str(item.get("studentDisplayName") or "").strip(),
        "fileName": str(item.get("fileName") or "").strip(),
        "fileUrl": str(item.get("fileUrl") or "").strip(),
        "fileSize": int(item.get("fileSize") or 0),
        "mimeType": str(item.get("mimeType") or "").strip(),
        "status": str(item.get("status") or "").strip(),
        "reviewStatus": review_status,
        "reviewScore": review_score,
        "reviewNote": str(item.get("reviewNote") or "").strip(),
        "reviewedBy": str(item.get("reviewedBy") or "").strip(),
        "reviewedAt": _to_text_time(item.get("reviewedAt")),
        "createdAt": _to_text_time(item.get("createdAt")),
        "updatedAt": _to_text_time(item.get("updatedAt")),
    }


def _normalize_rubric_items_payload(raw_items):
    items = raw_items if isinstance(raw_items, list) else []
    normalized = []
    for idx, raw in enumerate(items[:20]):
        item_title = str((raw or {}).get("itemTitle") or (raw or {}).get("title") or "").strip()
        if not item_title:
            continue
        description = str((raw or {}).get("description") or "").strip()
        if len(description) > 500:
            raise BizError("rubric item description too long", 400)
        score_val = _normalize_task_review_score((raw or {}).get("maxScore"), allow_empty=False)
        normalized.append(
            {
                "itemTitle": item_title[:160],
                "description": description[:500],
                "maxScore": score_val,
                "sortOrder": idx + 1,
            }
        )
    return normalized


def _normalize_submission_rubric_scores(raw_scores):
    rows = raw_scores if isinstance(raw_scores, list) else []
    normalized = []
    for raw in rows[:30]:
        item_id = _to_int_or_none((raw or {}).get("itemId"))
        if not item_id or int(item_id) <= 0:
            continue
        score_val = _normalize_task_review_score((raw or {}).get("score"), allow_empty=True)
        comment = str((raw or {}).get("comment") or "").strip()
        if len(comment) > 500:
            raise BizError("rubric score comment too long", 400)
        normalized.append({"itemId": int(item_id), "score": score_val, "comment": comment[:500]})
    return normalized


def _normalize_submission_annotations(raw_annotations):
    rows = raw_annotations if isinstance(raw_annotations, list) else []
    normalized = []
    for raw in rows[:50]:
        content = str((raw or {}).get("content") or "").strip()
        if not content:
            continue
        anchor_type = str((raw or {}).get("anchorType") or "file").strip().lower() or "file"
        anchor_key = str((raw or {}).get("anchorKey") or "").strip()
        annotation_type = str((raw or {}).get("annotationType") or "comment").strip().lower() or "comment"
        if len(content) > 500:
            raise BizError("annotation content too long", 400)
        if len(anchor_key) > 128:
            raise BizError("annotation anchorKey too long", 400)
        normalized.append(
            {
                "annotationType": annotation_type[:32],
                "anchorType": anchor_type[:32],
                "anchorKey": anchor_key[:128],
                "content": content[:500],
            }
        )
    return normalized


def _get_task_rubric_payload(task_id):
    template_rows = query(
        """
        SELECT id,
               task_id AS taskId,
               course_id AS courseId,
               teacher_user_name AS teacherUserName,
               title,
               description,
               total_score AS totalScore,
               status,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM task_rubric_template
        WHERE task_id=%s
        LIMIT 1
        """,
        (int(task_id),),
    )
    template = template_rows[0] if template_rows else None
    if not template:
        return {"template": None, "items": []}
    item_rows = query(
        """
        SELECT id,
               template_id AS templateId,
               item_title AS itemTitle,
               description,
               max_score AS maxScore,
               sort_order AS sortOrder,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM task_rubric_item
        WHERE template_id=%s
        ORDER BY sort_order ASC, id ASC
        """,
        (int(template.get("id") or 0),),
    )
    return {"template": template, "items": item_rows}


def _get_submission_review_extras_payload(submission_id):
    score_rows = query(
        """
        SELECT id,
               submission_id AS submissionId,
               item_id AS itemId,
               item_title AS itemTitle,
               max_score AS maxScore,
               score,
               comment,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM task_submission_rubric_score
        WHERE submission_id=%s
        ORDER BY id ASC
        """,
        (int(submission_id),),
    )
    annotation_rows = query(
        """
        SELECT id,
               submission_id AS submissionId,
               annotation_type AS annotationType,
               anchor_type AS anchorType,
               anchor_key AS anchorKey,
               content,
               created_by AS createdBy,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM task_submission_annotation
        WHERE submission_id=%s
        ORDER BY id ASC
        """,
        (int(submission_id),),
    )
    return {"rubricScores": score_rows, "annotations": annotation_rows}


def _replace_submission_review_extras_with_cur(cur, submission_id, rubric_scores, annotations, reviewer):
    cur.execute("DELETE FROM task_submission_rubric_score WHERE submission_id=%s", (int(submission_id),))
    cur.execute("DELETE FROM task_submission_annotation WHERE submission_id=%s", (int(submission_id),))

    if rubric_scores:
        item_ids = [int(item["itemId"]) for item in rubric_scores]
        placeholders = ",".join(["%s"] * len(item_ids))
        cur.execute(
            f"""
            SELECT id, item_title AS itemTitle, max_score AS maxScore
            FROM task_rubric_item
            WHERE id IN ({placeholders})
            """,
            tuple(item_ids),
        )
        item_map = {int(row.get("id") or 0): row for row in (cur.fetchall() or [])}
        for item in rubric_scores:
            rubric_item = item_map.get(int(item["itemId"]))
            if not rubric_item:
                continue
            cur.execute(
                """
                INSERT INTO task_submission_rubric_score (
                    submission_id, item_id, item_title, max_score, score, comment, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    int(submission_id),
                    int(item["itemId"]),
                    str(rubric_item.get("itemTitle") or "").strip(),
                    rubric_item.get("maxScore"),
                    item.get("score"),
                    item.get("comment"),
                    _to_text_time(datetime.now()),
                    _to_text_time(datetime.now()),
                ),
            )

    for annotation in annotations or []:
        cur.execute(
            """
            INSERT INTO task_submission_annotation (
                submission_id, annotation_type, anchor_type, anchor_key, content, created_by, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                int(submission_id),
                annotation.get("annotationType"),
                annotation.get("anchorType"),
                annotation.get("anchorKey"),
                annotation.get("content"),
                reviewer,
                _to_text_time(datetime.now()),
                _to_text_time(datetime.now()),
            ),
        )


def _can_manage_course(current_user, course_row):
    role = str((current_user or {}).get("role") or "").strip()
    username = str((current_user or {}).get("username") or "").strip()
    course_teacher = str((course_row or {}).get("teacherUserName") or "").strip()
    return role == "admin" or (username and username == course_teacher)


def _can_manage_task(current_user, task_row):
    role = str((current_user or {}).get("role") or "").strip()
    username = str((current_user or {}).get("username") or "").strip()
    task_teacher = str((task_row or {}).get("taskTeacherUserName") or "").strip()
    course_teacher = str((task_row or {}).get("courseTeacherUserName") or "").strip()
    if role == "admin":
        return True
    return bool(username and username in {task_teacher, course_teacher})


def _is_course_member_active(course_id, student_user_name):
    cid = _to_int_or_none(course_id)
    user_name = str(student_user_name or "").strip()
    if not cid or not user_name:
        return False
    rows = query(
        """
        SELECT id
        FROM course_member
        WHERE course_id=%s
          AND student_user_name=%s
          AND status='active'
        LIMIT 1
        """,
        (int(cid), user_name),
    )
    return bool(rows)


def _sanitize_upload_file_name(raw_name):
    name = str(raw_name or "").strip().replace("\\", "/")
    name = name.split("/")[-1]
    name = re.sub(r"[\r\n\t]+", "", name).strip()
    if not name:
        raise BizError("filename required", 400)
    if len(name) > 255:
        name = name[:255]
    return name


def _build_task_file_store_name(file_name):
    ext = str(os.path.splitext(file_name)[1] or "").strip()
    if len(ext) > 20:
        ext = ext[:20]
    if ext and not re.match(r"^\.[A-Za-z0-9._-]{1,20}$", ext):
        ext = ""
    return f"{uuid.uuid4().hex}{ext}"


def _query_task_access_row(task_id):
    rows = query(
        """
        SELECT t.id AS taskId,
               t.course_id AS courseId,
               t.title,
               t.status AS taskStatus,
               t.teacher_user_name AS taskTeacherUserName,
               c.status AS courseStatus,
               c.teacher_user_name AS courseTeacherUserName
        FROM experiment_task t
        LEFT JOIN course c ON c.id=t.course_id
        WHERE t.id=%s
        LIMIT 1
        """,
        (task_id,),
    )
    return rows[0] if rows else None


def _ensure_task_view_access_or_raise(current_user, task_row):
    if not task_row:
        raise BizError("task not found", 404)
    task_status = str(task_row.get("taskStatus") or "").strip()
    course_status = str(task_row.get("courseStatus") or "").strip()
    if task_status == "deleted" or course_status == "deleted":
        raise BizError("task not found", 404)
    can_manage = _can_manage_task(current_user, task_row)
    if not can_manage and (task_status != "active" or course_status != "enabled"):
        raise BizError("forbidden", 403)
    if not can_manage:
        role = str((current_user or {}).get("role") or "").strip()
        user_name = str((current_user or {}).get("username") or "").strip()
        if role == "student" and not _is_course_member_active(task_row.get("courseId"), user_name):
            raise BizError("forbidden", 403)
    return can_manage


def _ensure_task_submit_access_or_raise(current_user, task_row):
    if not task_row:
        raise BizError("task not found", 404)
    task_status = str(task_row.get("taskStatus") or "").strip()
    course_status = str(task_row.get("courseStatus") or "").strip()
    if task_status == "deleted" or course_status == "deleted":
        raise BizError("task not found", 404)

    can_manage = _can_manage_task(current_user, task_row)
    if can_manage:
        return True

    role = str((current_user or {}).get("role") or "").strip()
    if role != "student":
        raise BizError("forbidden", 403)
    if task_status != "active" or course_status != "enabled":
        raise BizError("forbidden", 403)
    user_name = str((current_user or {}).get("username") or "").strip()
    if not _is_course_member_active(task_row.get("courseId"), user_name):
        raise BizError("forbidden", 403)
    return True


def _resolve_student_display_name(student_id, student_user_name):
    uid = _to_int_or_none(student_id)
    user_name = str(student_user_name or "").strip()
    rows = []
    if uid and int(uid) > 0:
        rows = query("SELECT username, nickname FROM user WHERE id=%s LIMIT 1", (int(uid),))
    if not rows and user_name:
        rows = query("SELECT username, nickname FROM user WHERE username=%s LIMIT 1", (user_name,))

    if rows:
        row = rows[0] or {}
        nickname = str(row.get("nickname") or "").strip()
        username = str(row.get("username") or "").strip()
        if nickname:
            return nickname[:64]
        if username:
            return username[:64]
    return user_name[:64]


def _build_homework_review_where(current_user, query_args):
    role = str((current_user or {}).get("role") or "").strip().lower()
    user_name = str((current_user or {}).get("username") or "").strip()
    args = query_args or {}
    where_sql = " WHERE s.status='active' AND t.status<>'deleted' AND c.status<>'deleted'"
    params = []

    teacher_user_name = str(args.get("teacherUserName") or "").strip()
    if role == "admin":
        if teacher_user_name:
            where_sql += " AND (t.teacher_user_name=%s OR c.teacher_user_name=%s)"
            params.extend([teacher_user_name, teacher_user_name])
    else:
        if role != "teacher":
            raise BizError("forbidden", 403)
        if not user_name:
            raise BizError("unauthorized", 401)
        where_sql += " AND (t.teacher_user_name=%s OR c.teacher_user_name=%s)"
        params.extend([user_name, user_name])

    course_id_raw = args.get("courseId", "")
    course_id = _to_int_or_none(course_id_raw)
    if course_id_raw not in (None, "") and (course_id is None or int(course_id) <= 0):
        raise BizError("invalid courseId", 400)
    if course_id is not None and int(course_id) > 0:
        where_sql += " AND s.course_id=%s"
        params.append(int(course_id))

    task_id_raw = args.get("taskId", "")
    task_id = _to_int_or_none(task_id_raw)
    if task_id_raw not in (None, "") and (task_id is None or int(task_id) <= 0):
        raise BizError("invalid taskId", 400)
    if task_id is not None and int(task_id) > 0:
        where_sql += " AND s.task_id=%s"
        params.append(int(task_id))

    review_status = _parse_task_review_status_filter(args.get("reviewStatus"))
    if review_status == "pending":
        where_sql += " AND (s.review_status='pending' OR s.review_status IS NULL OR s.review_status='')"
    elif review_status:
        where_sql += " AND s.review_status=%s"
        params.append(review_status)

    keyword = str(args.get("keyword") or "").strip()
    if keyword:
        kw = f"%{keyword}%"
        where_sql += " AND (s.student_user_name LIKE %s OR s.student_display_name LIKE %s OR s.file_name LIKE %s OR t.title LIKE %s OR c.name LIKE %s)"
        params.extend([kw, kw, kw, kw, kw])

    return where_sql, params


@app.post("/teacher/courses")
@auth_required(roles=["teacher", "admin"])
def create_teacher_course():
    payload = request.get_json(force=True) or {}
    current_user = g.current_user or {}
    teacher_id = _to_int_or_none(current_user.get("id"))
    teacher_user_name = str(current_user.get("username") or "").strip()
    if not teacher_user_name:
        raise BizError("unauthorized", 401)

    name = str(payload.get("name") or "").strip()
    if not name:
        raise BizError("name required", 400)
    if len(name) > 120:
        raise BizError("name too long", 400)

    description = str(payload.get("description") or "").strip()
    if len(description) > 5000:
        raise BizError("description too long", 400)

    class_name = _normalize_course_class_name(payload.get("className"))
    status = _normalize_course_status(payload.get("status"))
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        course_code = _generate_course_code_with_cur(cur)
        cur.execute(
            """
            INSERT INTO course (
                name, description, class_name, course_code, teacher_id, teacher_user_name, status, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (name, description, class_name, course_code, teacher_id, teacher_user_name, status, now_text, now_text),
        )
        return {"id": int(cur.lastrowid or 0), "courseCode": course_code}

    created = run_in_transaction(_tx)
    new_id = int(created.get("id") or 0)
    audit_log(
        "teacher.course.create",
        target_type="course",
        target_id=new_id,
        detail={"name": name, "className": class_name, "status": status, "courseCode": created.get("courseCode")},
    )
    return jsonify({"ok": True, "data": {"id": int(new_id), "courseCode": created.get("courseCode")}})


@app.post("/teacher/courses/<int:course_id>")
@auth_required(roles=["teacher", "admin"])
def update_teacher_course(course_id):
    payload = request.get_json(force=True) or {}
    current_user = g.current_user or {}

    name = str(payload.get("name") or "").strip()
    if not name:
        raise BizError("name required", 400)
    if len(name) > 120:
        raise BizError("name too long", 400)

    description = str(payload.get("description") or "").strip()
    if len(description) > 5000:
        raise BizError("description too long", 400)
    class_name = _normalize_course_class_name(payload.get("className"))
    status = _normalize_course_status(payload.get("status"))
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   teacher_id AS teacherId,
                   teacher_user_name AS teacherUserName,
                   status
            FROM course
            WHERE id=%s
              AND status<>'deleted'
            LIMIT 1
            FOR UPDATE
            """,
            (course_id,),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("course not found", 404)
        if not _can_manage_course(current_user, row):
            raise BizError("forbidden", 403)

        cur.execute(
            """
            UPDATE course
            SET name=%s, description=%s, class_name=%s, status=%s, updated_at=%s
            WHERE id=%s
            """,
            (name, description, class_name, status, now_text, course_id),
        )
        if int(cur.rowcount or 0) != 1:
            raise BizError("course not found", 404)

    run_in_transaction(_tx)
    audit_log(
        "teacher.course.update",
        target_type="course",
        target_id=course_id,
        detail={"name": name, "className": class_name, "status": status},
    )
    return jsonify({"ok": True})


@app.post("/teacher/courses/<int:course_id>/delete")
@auth_required(roles=["teacher", "admin"])
def delete_teacher_course(course_id):
    current_user = g.current_user or {}
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   name,
                   status,
                   teacher_id AS teacherId,
                   teacher_user_name AS teacherUserName
            FROM course
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (course_id,),
        )
        row = cur.fetchone()
        if not row or str(row.get("status") or "").strip() == "deleted":
            raise BizError("course not found", 404)
        if not _can_manage_course(current_user, row):
            raise BizError("forbidden", 403)

        cur.execute(
            """
            UPDATE course
            SET status='deleted', updated_at=%s
            WHERE id=%s
              AND status<>'deleted'
            """,
            (now_text, course_id),
        )
        if int(cur.rowcount or 0) != 1:
            raise BizError("course not found", 404)

        cur.execute(
            """
            UPDATE experiment_task
            SET status='deleted', updated_at=%s
            WHERE course_id=%s
              AND status<>'deleted'
            """,
            (now_text, course_id),
        )
        cascade_task_count = int(cur.rowcount or 0)

        cur.execute(
            """
            UPDATE experiment_task_file
            SET status='deleted', updated_at=%s
            WHERE task_id IN (
                SELECT id
                FROM experiment_task
                WHERE course_id=%s
            )
              AND status<>'deleted'
            """,
            (now_text, course_id),
        )
        cascade_file_count = int(cur.rowcount or 0)
        cur.execute(
            """
            UPDATE experiment_task_submission
            SET status='deleted', updated_at=%s
            WHERE task_id IN (
                SELECT id
                FROM experiment_task
                WHERE course_id=%s
            )
              AND status<>'deleted'
            """,
            (now_text, course_id),
        )
        cascade_submission_count = int(cur.rowcount or 0)
        cur.execute(
            """
            UPDATE course_member
            SET status='removed', updated_at=%s
            WHERE course_id=%s
              AND status='active'
            """,
            (now_text, course_id),
        )
        cascade_member_count = int(cur.rowcount or 0)
        cur.execute(
            """
            UPDATE course_task_notice
            SET status='deleted', updated_at=%s
            WHERE course_id=%s
              AND status='active'
            """,
            (now_text, course_id),
        )
        cascade_notice_count = int(cur.rowcount or 0)
        return {
            "name": str(row.get("name") or "").strip(),
            "cascadeTaskCount": cascade_task_count,
            "cascadeFileCount": cascade_file_count,
            "cascadeSubmissionCount": cascade_submission_count,
            "cascadeMemberCount": cascade_member_count,
            "cascadeNoticeCount": cascade_notice_count,
        }

    deleted = run_in_transaction(_tx)
    audit_log(
        "teacher.course.delete",
        target_type="course",
        target_id=course_id,
        detail={
            "name": deleted.get("name"),
            "deleteMode": "soft",
            "cascadeTaskCount": int(deleted.get("cascadeTaskCount") or 0),
            "cascadeFileCount": int(deleted.get("cascadeFileCount") or 0),
            "cascadeSubmissionCount": int(deleted.get("cascadeSubmissionCount") or 0),
            "cascadeMemberCount": int(deleted.get("cascadeMemberCount") or 0),
            "cascadeNoticeCount": int(deleted.get("cascadeNoticeCount") or 0),
        },
    )
    return jsonify({"ok": True, "data": {"id": int(course_id)}})


@app.get("/teacher/courses")
@auth_required(roles=["teacher", "admin"])
def list_teacher_courses():
    keyword = str(request.args.get("keyword") or "").strip()
    class_name = str(request.args.get("className") or "").strip()
    current_user = g.current_user or {}
    username = str(current_user.get("username") or "").strip()
    role = str(current_user.get("role") or "").strip()
    is_admin = role == "admin"

    where_sql = " WHERE c.status<>'deleted'"
    params = []
    if not is_admin:
        where_sql += " AND c.teacher_user_name=%s"
        params.append(username)
    if keyword:
        kw = f"%{keyword}%"
        if is_admin:
            where_sql += " AND (c.name LIKE %s OR c.description LIKE %s OR c.teacher_user_name LIKE %s)"
            params.extend([kw, kw, kw])
        else:
            where_sql += " AND (c.name LIKE %s OR c.description LIKE %s)"
            params.extend([kw, kw])
    if class_name:
        where_sql += " AND c.class_name LIKE %s"
        params.append(f"%{class_name}%")

    rows = query(
        """
        SELECT c.id,
               c.name,
               c.description,
               c.class_name AS className,
               c.course_code AS courseCode,
               c.teacher_id AS teacherId,
               c.teacher_user_name AS teacherUserName,
               c.status,
               c.created_at AS createdAt,
               c.updated_at AS updatedAt,
               (
                   SELECT COUNT(*)
                   FROM experiment_task t
                   WHERE t.course_id=c.id AND t.status<>'deleted'
               ) AS taskCount
        FROM course c
        """
        + where_sql
        + " ORDER BY c.id DESC"
        ,
        params,
    )
    return jsonify({"ok": True, "data": [_format_course_row(row) for row in rows]})


@app.get("/teacher/task-templates")
@auth_required(roles=["teacher", "admin"])
def list_teacher_task_templates():
    current_user = g.current_user or {}
    role = str(current_user.get("role") or "").strip().lower()
    username = str(current_user.get("username") or "").strip()
    teacher_user_name = str(request.args.get("teacherUserName") or "").strip()
    keyword = str(request.args.get("keyword") or "").strip()
    limit_raw = _to_int_or_none(request.args.get("limit"))
    limit = max(1, min(int(limit_raw or 30), 100))

    where_sql = " WHERE t.status='active' AND c.status<>'deleted'"
    params = []

    if role != "admin":
        where_sql += " AND t.teacher_user_name=%s"
        params.append(username)
    elif teacher_user_name:
        where_sql += " AND t.teacher_user_name=%s"
        params.append(teacher_user_name)

    if keyword:
        kw = f"%{keyword}%"
        where_sql += " AND (t.title LIKE %s OR t.description LIKE %s OR c.name LIKE %s)"
        params.extend([kw, kw, kw])

    params.append(limit)
    rows = query(
        """
        SELECT t.id,
               t.course_id AS courseId,
               t.title,
               t.description,
               t.lab_id AS labId,
               t.deadline,
               t.teacher_user_name AS teacherUserName,
               t.created_at AS createdAt,
               c.name AS courseName
        FROM experiment_task t
        INNER JOIN course c ON c.id=t.course_id
        """
        + where_sql
        + " ORDER BY t.id DESC LIMIT %s",
        params,
    )
    return jsonify(
        {
            "ok": True,
            "data": [
                {
                    "id": int(row.get("id") or 0),
                    "courseId": int(row.get("courseId") or 0),
                    "courseName": str(row.get("courseName") or "").strip(),
                    "title": str(row.get("title") or "").strip(),
                    "description": str(row.get("description") or "").strip(),
                    "labId": _to_int_or_none(row.get("labId")),
                    "deadline": _to_text_time(row.get("deadline")),
                    "teacherUserName": str(row.get("teacherUserName") or "").strip(),
                    "createdAt": _to_text_time(row.get("createdAt")),
                }
                for row in rows
            ],
        }
    )


@app.get("/courses")
@auth_required()
def list_public_courses():
    keyword = str(request.args.get("keyword") or "").strip()
    class_name = str(request.args.get("className") or "").strip()
    current_user = g.current_user or {}
    role = str(current_user.get("role") or "").strip()
    username = str(current_user.get("username") or "").strip()
    where_sql = " WHERE c.status='enabled'"
    params = []
    if role == "student":
        where_sql += (
            " AND EXISTS ("
            "SELECT 1 FROM course_member m "
            "WHERE m.course_id=c.id AND m.student_user_name=%s AND m.status='active'"
            ")"
        )
        params.append(username)
    if keyword:
        kw = f"%{keyword}%"
        where_sql += " AND (c.name LIKE %s OR c.description LIKE %s OR c.teacher_user_name LIKE %s)"
        params.extend([kw, kw, kw])
    if class_name:
        where_sql += " AND c.class_name LIKE %s"
        params.append(f"%{class_name}%")

    rows = query(
        """
        SELECT c.id,
               c.name,
               c.description,
               c.class_name AS className,
               c.course_code AS courseCode,
               c.teacher_id AS teacherId,
               c.teacher_user_name AS teacherUserName,
               c.status,
               c.created_at AS createdAt,
               c.updated_at AS updatedAt,
               (
                   SELECT COUNT(*)
                   FROM experiment_task t
                   WHERE t.course_id=c.id AND t.status<>'deleted'
               ) AS taskCount
        FROM course c
        """
        + where_sql
        + " ORDER BY c.id DESC"
        ,
        params,
    )
    return jsonify({"ok": True, "data": [_format_course_row(row) for row in rows]})


@app.post("/courses/join-by-code")
@auth_required()
def join_course_by_code():
    current_user = g.current_user or {}
    role = str(current_user.get("role") or "").strip()
    student_user_name = str(current_user.get("username") or "").strip()
    student_id = _to_int_or_none(current_user.get("id"))
    if role != "student":
        raise BizError("forbidden", 403)
    if not student_user_name:
        raise BizError("unauthorized", 401)

    payload = request.get_json(force=True) or {}
    course_code = _normalize_course_code(payload.get("courseCode") or payload.get("course_code") or payload.get("code"))
    student_display_name = _resolve_student_display_name(student_id, student_user_name)
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   name,
                   description,
                   class_name AS className,
                   course_code AS courseCode,
                   teacher_id AS teacherId,
                   teacher_user_name AS teacherUserName,
                   status,
                   created_at AS createdAt,
                   updated_at AS updatedAt
            FROM course
            WHERE course_code=%s
            LIMIT 1
            FOR UPDATE
            """,
            (course_code,),
        )
        row = cur.fetchone()
        if not row or str(row.get("status") or "").strip() == "deleted":
            raise BizError("course not found", 404)
        if str(row.get("status") or "").strip() != "enabled":
            raise BizError("course not open", 409)

        cur.execute(
            """
            INSERT INTO course_member (
                course_id, student_id, student_user_name, student_display_name, status, joined_at, updated_at
            ) VALUES (%s, %s, %s, %s, 'active', %s, %s)
            ON DUPLICATE KEY UPDATE
                student_id=VALUES(student_id),
                student_display_name=VALUES(student_display_name),
                status='active',
                updated_at=VALUES(updated_at)
            """,
            (
                int(row.get("id") or 0),
                student_id,
                student_user_name,
                student_display_name,
                now_text,
                now_text,
            ),
        )
        return _format_course_row(row)

    joined_course = run_in_transaction(_tx)
    audit_log(
        "student.course.join_by_code",
        target_type="course",
        target_id=joined_course.get("id"),
        detail={
            "courseCode": joined_course.get("courseCode"),
            "studentUserName": student_user_name,
        },
        actor={"id": student_id, "username": student_user_name, "role": role},
    )
    return jsonify({"ok": True, "data": joined_course})


@app.post("/teacher/courses/<int:course_id>/tasks")
@auth_required(roles=["teacher", "admin"])
def create_course_task(course_id):
    payload = request.get_json(force=True) or {}
    current_user = g.current_user or {}
    username = str(current_user.get("username") or "").strip()
    teacher_id = _to_int_or_none(current_user.get("id"))
    if not username:
        raise BizError("unauthorized", 401)

    title = _normalize_task_title(payload.get("title"))
    description = _normalize_task_description(payload.get("description"))
    lab_id = _normalize_lab_id(payload.get("labId"))
    deadline = _normalize_deadline(payload.get("deadline"))

    if lab_id is not None:
        lab_row = query("SELECT id FROM lab WHERE id=%s LIMIT 1", (lab_id,))
        if not lab_row:
            raise BizError("lab not found", 404)

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   teacher_id AS teacherId,
                   teacher_user_name AS teacherUserName,
                   status
            FROM course
            WHERE id=%s
              AND status<>'deleted'
            LIMIT 1
            FOR UPDATE
            """,
            (course_id,),
        )
        course_row = cur.fetchone()
        if not course_row:
            raise BizError("course not found", 404)
        if not _can_manage_course(current_user, course_row):
            raise BizError("forbidden", 403)

        cur.execute(
            """
            INSERT INTO experiment_task (
                course_id, title, description, lab_id, deadline,
                teacher_id, teacher_user_name, status, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', %s, %s)
            """,
            (
                course_id,
                title,
                description,
                lab_id,
                deadline,
                teacher_id,
                username,
                now_text,
                now_text,
            ),
        )
        return int(cur.lastrowid or 0)

    new_id = run_in_transaction(_tx)
    audit_log(
        "teacher.task.create",
        target_type="experiment_task",
        target_id=new_id,
        detail={"courseId": int(course_id), "title": title, "labId": lab_id, "deadline": deadline or ""},
    )
    return jsonify({"ok": True, "data": {"id": int(new_id)}})


@app.get("/courses/<int:course_id>/tasks")
@auth_required()
def list_course_tasks(course_id):
    current_user = g.current_user or {}
    username = str(current_user.get("username") or "").strip()
    role = str(current_user.get("role") or "").strip()
    course_rows = query(
        """
        SELECT id,
               name,
               description,
               class_name AS className,
               course_code AS courseCode,
               teacher_id AS teacherId,
               teacher_user_name AS teacherUserName,
               status,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM course
        WHERE id=%s
          AND status<>'deleted'
        LIMIT 1
        """,
        (course_id,),
    )
    if not course_rows:
        raise BizError("course not found", 404)
    course = _format_course_row(course_rows[0])
    can_manage = role == "admin" or (username and username == course.get("teacherUserName"))

    if str(course.get("status") or "") != "enabled" and not can_manage:
        raise BizError("forbidden", 403)
    if role == "student" and not can_manage:
        if not _is_course_member_active(course_id, username):
            raise BizError("forbidden", 403)

    task_where_sql = " WHERE course_id=%s AND status<>'deleted'"
    task_params = [course_id]
    if not can_manage:
        task_where_sql = " WHERE course_id=%s AND status='active'"

    task_rows = query(
        """
        SELECT id,
               course_id AS courseId,
               title,
               description,
               lab_id AS labId,
               deadline,
               teacher_id AS teacherId,
               teacher_user_name AS teacherUserName,
               status,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM experiment_task
        """
        + task_where_sql
        + " ORDER BY id DESC"
        ,
        task_params,
    )
    tasks = [_format_task_row(row) for row in task_rows]
    return jsonify({"ok": True, "data": {"course": course, "tasks": tasks}})


@app.get("/teacher/courses/<int:course_id>/students")
@auth_required(roles=["teacher", "admin"])
def list_teacher_course_students(course_id):
    current_user = g.current_user or {}
    course_rows = query(
        """
        SELECT id,
               name,
               description,
               class_name AS className,
               course_code AS courseCode,
               teacher_id AS teacherId,
               teacher_user_name AS teacherUserName,
               status,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM course
        WHERE id=%s
          AND status<>'deleted'
        LIMIT 1
        """,
        (course_id,),
    )
    if not course_rows:
        raise BizError("course not found", 404)
    course = course_rows[0] or {}
    if not _can_manage_course(current_user, course):
        raise BizError("forbidden", 403)

    task_rows = query(
        """
        SELECT id,
               course_id AS courseId,
               title,
               deadline,
               status,
               created_at AS createdAt
        FROM experiment_task
        WHERE course_id=%s
          AND status='active'
        ORDER BY id ASC
        """,
        (course_id,),
    )
    member_rows = query(
        """
        SELECT id,
               course_id AS courseId,
               student_id AS studentId,
               student_user_name AS studentUserName,
               student_display_name AS studentDisplayName,
               status,
               joined_at AS joinedAt,
               updated_at AS updatedAt
        FROM course_member
        WHERE course_id=%s
          AND status='active'
        ORDER BY joined_at DESC, id DESC
        """,
        (course_id,),
    )

    submit_map = {}
    if task_rows and member_rows:
        submit_rows = query(
            """
            SELECT s.task_id AS taskId,
                   s.student_user_name AS studentUserName,
                   COUNT(*) AS submitCount,
                   MAX(s.created_at) AS lastSubmittedAt
            FROM experiment_task_submission s
            INNER JOIN experiment_task t ON t.id=s.task_id
            WHERE s.course_id=%s
              AND s.status='active'
              AND t.status='active'
            GROUP BY s.task_id, s.student_user_name
            """,
            (course_id,),
        )
        for row in submit_rows:
            key = (int(row.get("taskId") or 0), str(row.get("studentUserName") or "").strip())
            if key[0] <= 0 or not key[1]:
                continue
            submit_map[key] = {
                "submitCount": int(row.get("submitCount") or 0),
                "lastSubmittedAt": _to_text_time(row.get("lastSubmittedAt")),
            }

    tasks = []
    for row in task_rows:
        tasks.append(
            {
                "id": int(row.get("id") or 0),
                "courseId": int(row.get("courseId") or 0),
                "title": str(row.get("title") or "").strip(),
                "deadline": _to_text_time(row.get("deadline")),
                "status": str(row.get("status") or "").strip(),
                "createdAt": _to_text_time(row.get("createdAt")),
            }
        )

    students = []
    total_task_count = len(tasks)
    for row in member_rows:
        user_name = str(row.get("studentUserName") or "").strip()
        status_list = []
        submitted_task_count = 0
        for task in tasks:
            key = (int(task.get("id") or 0), user_name)
            submit_info = submit_map.get(key) or {}
            submitted = int(submit_info.get("submitCount") or 0) > 0
            if submitted:
                submitted_task_count += 1
            status_list.append(
                {
                    "taskId": int(task.get("id") or 0),
                    "submitted": bool(submitted),
                    "submitCount": int(submit_info.get("submitCount") or 0),
                    "lastSubmittedAt": str(submit_info.get("lastSubmittedAt") or ""),
                }
            )
        students.append(
            {
                "id": int(row.get("id") or 0),
                "courseId": int(row.get("courseId") or 0),
                "studentId": _to_int_or_none(row.get("studentId")),
                "studentUserName": user_name,
                "studentDisplayName": str(row.get("studentDisplayName") or "").strip(),
                "status": str(row.get("status") or "").strip(),
                "joinedAt": _to_text_time(row.get("joinedAt")),
                "updatedAt": _to_text_time(row.get("updatedAt")),
                "totalTaskCount": int(total_task_count),
                "submittedTaskCount": int(submitted_task_count),
                "missingTaskCount": int(max(0, total_task_count - submitted_task_count)),
                "taskStatusList": status_list,
            }
        )

    return jsonify(
        {
            "ok": True,
            "data": {
                "course": _format_course_row(course),
                "tasks": tasks,
                "students": students,
                "studentCount": len(students),
            },
        }
    )


@app.post("/teacher/courses/<int:course_id>/students/<student_user_name>/remove")
@auth_required(roles=["teacher", "admin"])
def remove_teacher_course_student(course_id, student_user_name):
    current_user = g.current_user or {}
    target_user_name = str(student_user_name or "").strip()
    if not target_user_name:
        raise BizError("studentUserName required", 400)
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   name,
                   teacher_user_name AS teacherUserName,
                   status
            FROM course
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (course_id,),
        )
        course_row = cur.fetchone()
        if not course_row or str(course_row.get("status") or "").strip() == "deleted":
            raise BizError("course not found", 404)
        if not _can_manage_course(current_user, course_row):
            raise BizError("forbidden", 403)

        cur.execute(
            """
            SELECT id,
                   student_id AS studentId,
                   student_display_name AS studentDisplayName,
                   status
            FROM course_member
            WHERE course_id=%s
              AND student_user_name=%s
              AND status='active'
            LIMIT 1
            FOR UPDATE
            """,
            (course_id, target_user_name),
        )
        member_row = cur.fetchone()
        if not member_row:
            raise BizError("student not in course", 404)

        cur.execute(
            """
            UPDATE course_member
            SET status='removed', updated_at=%s
            WHERE id=%s
              AND status='active'
            """,
            (now_text, int(member_row.get("id") or 0)),
        )
        if int(cur.rowcount or 0) != 1:
            raise BizError("student not in course", 404)

        return {
            "courseName": str(course_row.get("name") or "").strip(),
            "studentId": _to_int_or_none(member_row.get("studentId")),
            "studentDisplayName": str(member_row.get("studentDisplayName") or "").strip(),
        }

    removed = run_in_transaction(_tx)
    audit_log(
        "teacher.course_student.remove",
        target_type="course",
        target_id=course_id,
        detail={
            "studentUserName": target_user_name,
            "studentDisplayName": removed.get("studentDisplayName"),
            "studentId": removed.get("studentId"),
            "courseName": removed.get("courseName"),
        },
    )
    return jsonify({"ok": True, "data": {"courseId": int(course_id), "studentUserName": target_user_name}})


@app.post("/teacher/courses/<int:course_id>/tasks/<int:task_id>/notify-missing")
@auth_required(roles=["teacher", "admin"])
def notify_missing_students(course_id, task_id):
    current_user = g.current_user or {}
    teacher_user_name = str(current_user.get("username") or "").strip()
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   name,
                   teacher_user_name AS teacherUserName,
                   status
            FROM course
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (course_id,),
        )
        course_row = cur.fetchone()
        if not course_row or str(course_row.get("status") or "").strip() == "deleted":
            raise BizError("course not found", 404)
        if not _can_manage_course(current_user, course_row):
            raise BizError("forbidden", 403)

        cur.execute(
            """
            SELECT id,
                   title,
                   status
            FROM experiment_task
            WHERE id=%s
              AND course_id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (task_id, course_id),
        )
        task_row = cur.fetchone()
        if not task_row or str(task_row.get("status") or "").strip() == "deleted":
            raise BizError("task not found", 404)

        cur.execute(
            """
            SELECT student_user_name AS studentUserName,
                   student_display_name AS studentDisplayName
            FROM course_member
            WHERE course_id=%s
              AND status='active'
            """,
            (course_id,),
        )
        member_rows = cur.fetchall() or []
        if not member_rows:
            return {
                "courseId": int(course_id),
                "taskId": int(task_id),
                "taskTitle": str(task_row.get("title") or "").strip(),
                "notifiedCount": 0,
                "missingStudents": [],
            }

        cur.execute(
            """
            SELECT DISTINCT student_user_name AS studentUserName
            FROM experiment_task_submission
            WHERE task_id=%s
              AND status='active'
            """,
            (task_id,),
        )
        submitted_rows = cur.fetchall() or []
        submitted_users = {str((x or {}).get("studentUserName") or "").strip() for x in submitted_rows}
        submitted_users = {x for x in submitted_users if x}

        missing_rows = []
        for row in member_rows:
            user_name = str((row or {}).get("studentUserName") or "").strip()
            if not user_name or user_name in submitted_users:
                continue
            missing_rows.append(
                {
                    "studentUserName": user_name,
                    "studentDisplayName": str((row or {}).get("studentDisplayName") or "").strip(),
                }
            )

        if not missing_rows:
            return {
                "courseId": int(course_id),
                "taskId": int(task_id),
                "taskTitle": str(task_row.get("title") or "").strip(),
                "notifiedCount": 0,
                "missingStudents": [],
            }

        course_name = str(course_row.get("name") or "").strip() or f"#{course_id}"
        task_title = str(task_row.get("title") or "").strip() or f"#{task_id}"
        message = f"课程《{course_name}》任务《{task_title}》尚未提交作业文件，请尽快完成。"
        sender_user_name = teacher_user_name or str(course_row.get("teacherUserName") or "").strip()
        for row in missing_rows:
            cur.execute(
                """
                INSERT INTO course_task_notice (
                    course_id, task_id, to_user_name, teacher_user_name, message, status, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, 'active', %s, %s)
                """,
                (
                    int(course_id),
                    int(task_id),
                    row.get("studentUserName"),
                    sender_user_name,
                    message,
                    now_text,
                    now_text,
                ),
            )

        return {
            "courseId": int(course_id),
            "taskId": int(task_id),
            "taskTitle": task_title,
            "notifiedCount": len(missing_rows),
            "missingStudents": missing_rows,
        }

    notified = run_in_transaction(_tx)
    audit_log(
        "teacher.task.notify_missing",
        target_type="experiment_task",
        target_id=task_id,
        detail={
            "courseId": int(course_id),
            "taskTitle": notified.get("taskTitle"),
            "notifiedCount": int(notified.get("notifiedCount") or 0),
        },
    )
    return jsonify({"ok": True, "data": notified})


@app.post("/teacher/courses/<int:course_id>/tasks/auto-notify")
@auth_required(roles=["teacher", "admin"])
def auto_notify_missing_students(course_id):
    current_user = g.current_user or {}
    now_dt = datetime.now()
    now_text = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    remind_date = now_dt.strftime("%Y-%m-%d")

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   name,
                   teacher_user_name AS teacherUserName,
                   status
            FROM course
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (course_id,),
        )
        course_row = cur.fetchone()
        if not course_row or str(course_row.get("status") or "").strip() == "deleted":
            raise BizError("course not found", 404)
        if not _can_manage_course(current_user, course_row):
            raise BizError("forbidden", 403)

        course_name = str(course_row.get("name") or "").strip()
        teacher_user_name = str(current_user.get("username") or "").strip() or str(course_row.get("teacherUserName") or "").strip()

        cur.execute(
            """
            SELECT id,
                   title,
                   deadline
            FROM experiment_task
            WHERE course_id=%s
              AND status='active'
              AND deadline IS NOT NULL
            ORDER BY id ASC
            """,
            (course_id,),
        )
        task_rows = cur.fetchall() or []
        if not task_rows:
            return {
                "courseId": int(course_id),
                "taskCount": 0,
                "autoNotifiedCount": 0,
                "beforeDeadlineCount": 0,
                "overdueCount": 0,
            }

        cur.execute(
            """
            SELECT student_user_name AS studentUserName,
                   student_display_name AS studentDisplayName
            FROM course_member
            WHERE course_id=%s
              AND status='active'
            """,
            (course_id,),
        )
        member_rows = cur.fetchall() or []
        if not member_rows:
            return {
                "courseId": int(course_id),
                "taskCount": len(task_rows),
                "autoNotifiedCount": 0,
                "beforeDeadlineCount": 0,
                "overdueCount": 0,
            }

        task_ids = [int((row or {}).get("id") or 0) for row in task_rows]
        task_ids = [tid for tid in task_ids if tid > 0]
        if not task_ids:
            return {
                "courseId": int(course_id),
                "taskCount": 0,
                "autoNotifiedCount": 0,
                "beforeDeadlineCount": 0,
                "overdueCount": 0,
            }

        task_placeholders = ",".join(["%s"] * len(task_ids))
        cur.execute(
            f"""
            SELECT task_id AS taskId,
                   student_user_name AS studentUserName,
                   COUNT(*) AS submitCount
            FROM experiment_task_submission
            WHERE task_id IN ({task_placeholders})
              AND status='active'
            GROUP BY task_id, student_user_name
            """,
            tuple(task_ids),
        )
        submit_rows = cur.fetchall() or []
        submitted_keys = set()
        for row in submit_rows:
            task_id = int((row or {}).get("taskId") or 0)
            user_name = str((row or {}).get("studentUserName") or "").strip()
            if task_id <= 0 or not user_name:
                continue
            if int((row or {}).get("submitCount") or 0) <= 0:
                continue
            submitted_keys.add((task_id, user_name))

        member_user_names = []
        for row in member_rows:
            user_name = str((row or {}).get("studentUserName") or "").strip()
            if user_name:
                member_user_names.append(user_name)
        member_user_names = sorted(set(member_user_names))
        if not member_user_names:
            return {
                "courseId": int(course_id),
                "taskCount": len(task_rows),
                "autoNotifiedCount": 0,
                "beforeDeadlineCount": 0,
                "overdueCount": 0,
            }

        sub_placeholders = ",".join(["%s"] * len(member_user_names))
        cur.execute(
            f"""
            SELECT user_name AS userName,
                   enabled,
                   before_hours AS beforeHours,
                   remind_overdue AS remindOverdue
            FROM course_task_notice_subscription
            WHERE user_name IN ({sub_placeholders})
            """,
            tuple(member_user_names),
        )
        sub_rows = cur.fetchall() or []
        sub_map = {}
        for row in sub_rows:
            user_name = str((row or {}).get("userName") or "").strip()
            if not user_name:
                continue
            sub_map[user_name] = {
                "enabled": bool(int((row or {}).get("enabled") or 0) == 1),
                "beforeHours": max(1, min(int((row or {}).get("beforeHours") or 24), 168)),
                "remindOverdue": bool(int((row or {}).get("remindOverdue") or 0) == 1),
            }

        auto_notified_count = 0
        before_deadline_count = 0
        overdue_count = 0

        for task_row in task_rows:
            task_id = int((task_row or {}).get("id") or 0)
            task_title = str((task_row or {}).get("title") or "").strip()
            deadline_text = _to_text_time((task_row or {}).get("deadline"))
            deadline_dt = _parse_task_deadline_datetime((task_row or {}).get("deadline"))
            if task_id <= 0 or not deadline_dt:
                continue

            hours_left = (deadline_dt - now_dt).total_seconds() / 3600.0
            for member in member_rows:
                student_user_name = str((member or {}).get("studentUserName") or "").strip()
                if not student_user_name:
                    continue
                if (task_id, student_user_name) in submitted_keys:
                    continue

                pref = sub_map.get(student_user_name) or {"enabled": True, "beforeHours": 24, "remindOverdue": True}
                if not pref.get("enabled"):
                    continue

                reminder_kind = ""
                if hours_left <= 0:
                    if not pref.get("remindOverdue"):
                        continue
                    reminder_kind = "overdue"
                else:
                    before_hours = max(1, min(int(pref.get("beforeHours") or 24), 168))
                    if hours_left > before_hours:
                        continue
                    reminder_kind = "before_deadline"

                inserted = insert_course_task_auto_notice_log_with_cur(
                    cur,
                    course_id=course_id,
                    task_id=task_id,
                    to_user_name=student_user_name,
                    reminder_kind=reminder_kind,
                    remind_date=remind_date,
                    created_at=now_text,
                )
                if not inserted:
                    continue

                message = _build_auto_notice_message(course_name, task_title, deadline_text, reminder_kind)
                cur.execute(
                    """
                    INSERT INTO course_task_notice (
                        course_id, task_id, to_user_name, teacher_user_name, message, status, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, 'active', %s, %s)
                    """,
                    (
                        int(course_id),
                        task_id,
                        student_user_name,
                        teacher_user_name,
                        message,
                        now_text,
                        now_text,
                    ),
                )
                auto_notified_count += 1
                if reminder_kind == "overdue":
                    overdue_count += 1
                else:
                    before_deadline_count += 1

        return {
            "courseId": int(course_id),
            "taskCount": len(task_rows),
            "autoNotifiedCount": int(auto_notified_count),
            "beforeDeadlineCount": int(before_deadline_count),
            "overdueCount": int(overdue_count),
        }

    notified = run_in_transaction(_tx)
    audit_log(
        "teacher.task.auto_notify_missing",
        target_type="course",
        target_id=course_id,
        detail={
            "taskCount": int(notified.get("taskCount") or 0),
            "autoNotifiedCount": int(notified.get("autoNotifiedCount") or 0),
            "beforeDeadlineCount": int(notified.get("beforeDeadlineCount") or 0),
            "overdueCount": int(notified.get("overdueCount") or 0),
        },
    )
    return jsonify({"ok": True, "data": notified})


@app.post("/teacher/tasks/<int:task_id>/delete")
@auth_required(roles=["teacher", "admin"])
def delete_course_task(task_id):
    current_user = g.current_user or {}
    username = str(current_user.get("username") or "").strip()
    role = str(current_user.get("role") or "").strip()
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            """
            SELECT t.id,
                   t.course_id AS courseId,
                   t.title,
                   t.status,
                   t.teacher_user_name AS taskTeacherUserName,
                   c.teacher_user_name AS courseTeacherUserName
            FROM experiment_task t
            LEFT JOIN course c ON c.id=t.course_id
            WHERE t.id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (task_id,),
        )
        row = cur.fetchone()
        if not row or str(row.get("status") or "").strip() == "deleted":
            raise BizError("task not found", 404)

        task_teacher = str(row.get("taskTeacherUserName") or "").strip()
        course_teacher = str(row.get("courseTeacherUserName") or "").strip()
        if role != "admin" and username not in {task_teacher, course_teacher}:
            raise BizError("forbidden", 403)

        cur.execute(
            """
            UPDATE experiment_task
            SET status='deleted', updated_at=%s
            WHERE id=%s
              AND status<>'deleted'
            """,
            (now_text, task_id),
        )
        if int(cur.rowcount or 0) != 1:
            raise BizError("task not found", 404)
        cur.execute(
            """
            UPDATE experiment_task_file
            SET status='deleted', updated_at=%s
            WHERE task_id=%s
              AND status<>'deleted'
            """,
            (now_text, task_id),
        )
        cascade_file_count = int(cur.rowcount or 0)
        cur.execute(
            """
            UPDATE experiment_task_submission
            SET status='deleted', updated_at=%s
            WHERE task_id=%s
              AND status<>'deleted'
            """,
            (now_text, task_id),
        )
        cascade_submission_count = int(cur.rowcount or 0)
        cur.execute(
            """
            UPDATE course_task_notice
            SET status='deleted', updated_at=%s
            WHERE task_id=%s
              AND status='active'
            """,
            (now_text, task_id),
        )
        return {
            "courseId": int(row.get("courseId") or 0),
            "title": str(row.get("title") or "").strip(),
            "cascadeFileCount": cascade_file_count,
            "cascadeSubmissionCount": cascade_submission_count,
            "cascadeNoticeCount": int(cur.rowcount or 0),
        }

    deleted = run_in_transaction(_tx)
    audit_log(
        "teacher.task.delete",
        target_type="experiment_task",
        target_id=task_id,
        detail={
            "courseId": deleted.get("courseId"),
            "title": deleted.get("title"),
            "deleteMode": "soft",
            "cascadeFileCount": int(deleted.get("cascadeFileCount") or 0),
            "cascadeSubmissionCount": int(deleted.get("cascadeSubmissionCount") or 0),
            "cascadeNoticeCount": int(deleted.get("cascadeNoticeCount") or 0),
        },
    )
    return jsonify({"ok": True, "data": {"id": int(task_id)}})


@app.get("/tasks/<int:task_id>/files")
@auth_required()
def list_task_files(task_id):
    current_user = g.current_user or {}
    task_row = _query_task_access_row(task_id)
    _ensure_task_view_access_or_raise(current_user, task_row)

    rows = query(
        """
        SELECT id,
               task_id AS taskId,
               course_id AS courseId,
               file_name AS fileName,
               file_url AS fileUrl,
               file_size AS fileSize,
               mime_type AS mimeType,
               uploader_id AS uploaderId,
               uploader_user_name AS uploaderUserName,
               status,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM experiment_task_file
        WHERE task_id=%s
          AND status='active'
        ORDER BY id DESC
        """,
        (task_id,),
    )
    return jsonify({"ok": True, "data": [_format_task_file_row(row) for row in rows]})


@app.post("/teacher/tasks/<int:task_id>/files/upload")
@auth_required(roles=["teacher", "admin"])
def upload_task_file(task_id):
    current_user = g.current_user or {}
    uploader_id = _to_int_or_none(current_user.get("id"))
    uploader_user_name = str(current_user.get("username") or "").strip()
    if not uploader_user_name:
        raise BizError("unauthorized", 401)

    if "file" not in request.files:
        raise BizError("file required", 400)
    f = request.files["file"]
    raw_name = _sanitize_upload_file_name(getattr(f, "filename", ""))
    mime_type = str(getattr(f, "mimetype", "") or "").strip()
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            """
            SELECT t.id AS taskId,
                   t.course_id AS courseId,
                   t.title,
                   t.status AS taskStatus,
                   t.teacher_user_name AS taskTeacherUserName,
                   c.status AS courseStatus,
                   c.teacher_user_name AS courseTeacherUserName
            FROM experiment_task t
            LEFT JOIN course c ON c.id=t.course_id
            WHERE t.id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (task_id,),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("task not found", 404)
        if str(row.get("taskStatus") or "").strip() == "deleted" or str(row.get("courseStatus") or "").strip() == "deleted":
            raise BizError("task not found", 404)
        if not _can_manage_task(current_user, row):
            raise BizError("forbidden", 403)

        os.makedirs(os.path.join(UPLOAD_DIR, TASK_FILE_SUBDIR), exist_ok=True)
        store_name = _build_task_file_store_name(raw_name)
        rel_path = f"{TASK_FILE_SUBDIR}/{store_name}"
        abs_path = os.path.join(UPLOAD_DIR, TASK_FILE_SUBDIR, store_name)
        f.save(abs_path)
        file_size = int(os.path.getsize(abs_path) or 0)
        if file_size <= 0:
            try:
                os.remove(abs_path)
            except OSError:
                pass
            raise BizError("empty file", 400)
        if file_size > TASK_FILE_MAX_SIZE_BYTES:
            try:
                os.remove(abs_path)
            except OSError:
                pass
            raise BizError("file too large", 400)

        file_url = f"/uploads/{rel_path}"
        cur.execute(
            """
            INSERT INTO experiment_task_file (
                task_id, course_id, file_name, file_url, file_size, mime_type,
                uploader_id, uploader_user_name, status, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active', %s, %s)
            """,
            (
                int(row.get("taskId") or 0),
                int(row.get("courseId") or 0),
                raw_name,
                file_url,
                file_size,
                mime_type,
                uploader_id,
                uploader_user_name,
                now_text,
                now_text,
            ),
        )
        new_id = int(cur.lastrowid or 0)
        return {
            "id": new_id,
            "taskId": int(row.get("taskId") or 0),
            "courseId": int(row.get("courseId") or 0),
            "title": str(row.get("title") or "").strip(),
            "fileName": raw_name,
            "fileUrl": file_url,
            "fileSize": file_size,
            "mimeType": mime_type,
            "uploaderId": uploader_id,
            "uploaderUserName": uploader_user_name,
            "status": "active",
            "createdAt": now_text,
            "updatedAt": now_text,
        }

    saved = run_in_transaction(_tx)
    audit_log(
        "teacher.task_file.upload",
        target_type="experiment_task_file",
        target_id=saved.get("id"),
        detail={
            "taskId": saved.get("taskId"),
            "courseId": saved.get("courseId"),
            "fileName": saved.get("fileName"),
            "fileSize": saved.get("fileSize"),
            "mimeType": saved.get("mimeType"),
            "maxSizeBytes": TASK_FILE_MAX_SIZE_BYTES,
        },
    )
    return jsonify({"ok": True, "data": saved})


@app.post("/teacher/task-files/<int:file_id>/delete")
@auth_required(roles=["teacher", "admin"])
def delete_task_file(file_id):
    current_user = g.current_user or {}
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            """
            SELECT f.id,
                   f.task_id AS taskId,
                   f.course_id AS courseId,
                   f.file_name AS fileName,
                   f.status AS fileStatus,
                   t.title AS taskTitle,
                   t.teacher_user_name AS taskTeacherUserName,
                   c.teacher_user_name AS courseTeacherUserName
            FROM experiment_task_file f
            LEFT JOIN experiment_task t ON t.id=f.task_id
            LEFT JOIN course c ON c.id=t.course_id
            WHERE f.id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (file_id,),
        )
        row = cur.fetchone()
        if not row or str(row.get("fileStatus") or "").strip() == "deleted":
            raise BizError("file not found", 404)
        if not _can_manage_task(current_user, row):
            raise BizError("forbidden", 403)

        cur.execute(
            """
            UPDATE experiment_task_file
            SET status='deleted', updated_at=%s
            WHERE id=%s
              AND status<>'deleted'
            """,
            (now_text, file_id),
        )
        if int(cur.rowcount or 0) != 1:
            raise BizError("file not found", 404)
        return {
            "id": int(row.get("id") or 0),
            "taskId": int(row.get("taskId") or 0),
            "courseId": int(row.get("courseId") or 0),
            "fileName": str(row.get("fileName") or "").strip(),
            "taskTitle": str(row.get("taskTitle") or "").strip(),
        }

    deleted = run_in_transaction(_tx)
    audit_log(
        "teacher.task_file.delete",
        target_type="experiment_task_file",
        target_id=file_id,
        detail={
            "taskId": deleted.get("taskId"),
            "courseId": deleted.get("courseId"),
            "taskTitle": deleted.get("taskTitle"),
            "fileName": deleted.get("fileName"),
            "deleteMode": "soft",
        },
    )
    return jsonify({"ok": True, "data": {"id": int(file_id), "taskId": deleted.get("taskId")}})


@app.get("/teacher/tasks/<int:task_id>/student-files")
@auth_required(roles=["teacher", "admin"])
def list_task_student_files(task_id):
    current_user = g.current_user or {}
    task_row = _query_task_access_row(task_id)
    if not task_row:
        raise BizError("task not found", 404)
    if str(task_row.get("taskStatus") or "").strip() == "deleted" or str(task_row.get("courseStatus") or "").strip() == "deleted":
        raise BizError("task not found", 404)
    if not _can_manage_task(current_user, task_row):
        raise BizError("forbidden", 403)

    rows = query(
        """
        SELECT id,
               task_id AS taskId,
               course_id AS courseId,
               student_id AS studentId,
               student_user_name AS studentUserName,
               student_display_name AS studentDisplayName,
               file_name AS fileName,
               file_url AS fileUrl,
               file_size AS fileSize,
               mime_type AS mimeType,
               status,
               review_status AS reviewStatus,
               review_score AS reviewScore,
               review_note AS reviewNote,
               reviewed_by AS reviewedBy,
               reviewed_at AS reviewedAt,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM experiment_task_submission
        WHERE task_id=%s
          AND status='active'
        ORDER BY id DESC
        """,
        (task_id,),
    )
    return jsonify({"ok": True, "data": [_format_task_submission_row(row) for row in rows]})


@app.get("/teacher/homework-reviews")
@auth_required(roles=["teacher", "admin"])
def list_teacher_homework_reviews():
    current_user = g.current_user or {}
    page, page_size, offset = _parse_pagination(request.args.get("page", "1"), request.args.get("pageSize", "20"))
    where_sql, params = _build_homework_review_where(current_user, request.args)

    from_sql = (
        """
        FROM experiment_task_submission s
        INNER JOIN experiment_task t ON t.id=s.task_id
        INNER JOIN course c ON c.id=s.course_id
        """
    )

    total_rows = query("SELECT COUNT(*) AS cnt " + from_sql + where_sql, tuple(params))
    total = int((total_rows[0] or {}).get("cnt") or 0) if total_rows else 0

    rows = query(
        """
        SELECT s.id,
               s.task_id AS taskId,
               s.course_id AS courseId,
               c.name AS courseName,
               t.title AS taskTitle,
               s.student_id AS studentId,
               s.student_user_name AS studentUserName,
               s.student_display_name AS studentDisplayName,
               s.file_name AS fileName,
               s.file_url AS fileUrl,
               s.file_size AS fileSize,
               s.mime_type AS mimeType,
               s.status,
               s.review_status AS reviewStatus,
               s.review_score AS reviewScore,
               s.review_note AS reviewNote,
               s.reviewed_by AS reviewedBy,
               s.reviewed_at AS reviewedAt,
               s.created_at AS createdAt,
               s.updated_at AS updatedAt
        """
        + from_sql
        + where_sql
        + """
        ORDER BY
            CASE COALESCE(NULLIF(s.review_status, ''), 'pending')
                WHEN 'pending' THEN 0
                WHEN 'rejected' THEN 1
                WHEN 'approved' THEN 2
                ELSE 3
            END ASC,
            s.updated_at DESC,
            s.id DESC
        LIMIT %s OFFSET %s
        """,
        tuple(list(params) + [int(page_size), int(offset)]),
    )
    data = [_format_task_submission_row(row) for row in rows]

    summary_rows = query(
        """
        SELECT COALESCE(NULLIF(s.review_status, ''), 'pending') AS reviewStatus,
               COUNT(*) AS cnt,
               AVG(CASE WHEN COALESCE(NULLIF(s.review_status, ''), 'pending')='approved' THEN s.review_score END) AS avgApprovedScore
        """
        + from_sql
        + where_sql
        + """
        GROUP BY COALESCE(NULLIF(s.review_status, ''), 'pending')
        """,
        tuple(params),
    )
    summary = {"pending": 0, "approved": 0, "rejected": 0, "avgApprovedScore": None}
    for row in summary_rows or []:
        status = str((row or {}).get("reviewStatus") or "").strip().lower()
        cnt = int((row or {}).get("cnt") or 0)
        if status in {"pending", "approved", "rejected"}:
            summary[status] = cnt
        if status == "approved":
            avg_raw = (row or {}).get("avgApprovedScore")
            if avg_raw not in (None, ""):
                try:
                    summary["avgApprovedScore"] = round(float(avg_raw), 2)
                except (TypeError, ValueError):
                    summary["avgApprovedScore"] = None

    return jsonify(
        {
            "ok": True,
            "data": data,
            "meta": {
                "page": int(page),
                "pageSize": int(page_size),
                "total": int(total),
                "hasMore": bool(offset + len(data) < total),
                "summary": summary,
            },
        }
    )


@app.get("/teacher/homework-reviews/export")
@auth_required(roles=["teacher", "admin"])
def export_teacher_homework_reviews():
    current_user = g.current_user or {}
    where_sql, params = _build_homework_review_where(current_user, request.args)
    from_sql = (
        """
        FROM experiment_task_submission s
        INNER JOIN experiment_task t ON t.id=s.task_id
        INNER JOIN course c ON c.id=s.course_id
        """
    )
    rows = query(
        """
        SELECT s.id,
               s.task_id AS taskId,
               s.course_id AS courseId,
               c.name AS courseName,
               t.title AS taskTitle,
               s.student_id AS studentId,
               s.student_user_name AS studentUserName,
               s.student_display_name AS studentDisplayName,
               s.file_name AS fileName,
               s.file_url AS fileUrl,
               s.file_size AS fileSize,
               s.mime_type AS mimeType,
               s.status,
               s.review_status AS reviewStatus,
               s.review_score AS reviewScore,
               s.review_note AS reviewNote,
               s.reviewed_by AS reviewedBy,
               s.reviewed_at AS reviewedAt,
               s.created_at AS createdAt,
               s.updated_at AS updatedAt
        """
        + from_sql
        + where_sql
        + """
        ORDER BY
            c.id DESC,
            t.id DESC,
            s.id DESC
        """,
        tuple(params),
    )
    status_text_map = {"pending": "待批改", "approved": "已通过", "rejected": "已驳回"}
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "提交ID",
            "课程ID",
            "课程名称",
            "任务ID",
            "任务标题",
            "学生账号",
            "学生姓名",
            "文件名",
            "提交时间",
            "批改状态",
            "分数",
            "评语",
            "批改人",
            "批改时间",
        ]
    )
    for row in rows or []:
        item = _format_task_submission_row(row)
        score_val = item.get("reviewScore")
        score_text = ""
        if score_val not in (None, ""):
            score_text = f"{float(score_val):.2f}"
        writer.writerow(
            [
                int(item.get("id") or 0),
                int(item.get("courseId") or 0),
                str(item.get("courseName") or ""),
                int(item.get("taskId") or 0),
                str(item.get("taskTitle") or ""),
                str(item.get("studentUserName") or ""),
                str(item.get("studentDisplayName") or ""),
                str(item.get("fileName") or ""),
                str(item.get("createdAt") or ""),
                status_text_map.get(str(item.get("reviewStatus") or ""), str(item.get("reviewStatus") or "")),
                score_text,
                str(item.get("reviewNote") or ""),
                str(item.get("reviewedBy") or ""),
                str(item.get("reviewedAt") or ""),
            ]
        )
    file_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    return (
        "\ufeff" + output.getvalue(),
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f"attachment; filename=teacher_homework_scores_{file_tag}.csv",
        },
    )


def _task_submission_abs_path(file_url):
    raw = str(file_url or "").strip()
    prefix = "/uploads/"
    if not raw.startswith(prefix):
        return ""
    rel_path = raw[len(prefix) :].replace("/", os.sep)
    abs_path = os.path.normpath(os.path.join(UPLOAD_DIR, rel_path))
    upload_root = os.path.normpath(UPLOAD_DIR)
    try:
        if os.path.commonpath([upload_root, abs_path]) != upload_root:
            return ""
    except ValueError:
        return ""
    if not os.path.isfile(abs_path):
        return ""
    return abs_path


def _read_submission_text_excerpt(file_url, file_name="", mime_type="", max_chars=1600):
    ext = os.path.splitext(str(file_name or "").strip().lower())[1]
    mime = str(mime_type or "").strip().lower()
    text_exts = {".txt", ".md", ".markdown", ".json", ".csv", ".log", ".py", ".js", ".ts", ".java", ".c", ".cpp", ".sql", ".yaml", ".yml"}
    if ext not in text_exts and not mime.startswith("text/") and mime not in {"application/json", "application/xml"}:
        return ""
    abs_path = _task_submission_abs_path(file_url)
    if not abs_path:
        return ""
    try:
        with open(abs_path, "rb") as fp:
            raw = fp.read(12000)
    except OSError:
        return ""
    if not raw:
        return ""
    for encoding in ("utf-8", "gbk", "utf-16"):
        try:
            text = raw.decode(encoding)
            break
        except Exception:
            text = ""
    if not text:
        text = raw.decode("utf-8", errors="ignore")
    text = re.sub(r"\s+", " ", str(text or "").strip())
    if len(text) > max_chars:
        text = text[:max_chars]
    return text


def _build_homework_ai_suggestion(submission_row):
    row = submission_row or {}
    created_at_text = _to_text_time(row.get("createdAt"))
    created_dt = _to_datetime(created_at_text)
    deadline_text = _to_text_time(row.get("deadline"))
    deadline_dt = _parse_task_deadline_datetime(deadline_text)
    file_size = int(row.get("fileSize") or 0)
    excerpt = _read_submission_text_excerpt(row.get("fileUrl"), row.get("fileName"), row.get("mimeType"))
    char_count = len(excerpt)
    line_count = len([x for x in re.split(r"[\r\n]+", excerpt) if str(x or "").strip()]) if excerpt else 0
    delay_hours = 0.0
    if deadline_dt and created_dt != datetime.min:
        delay_hours = max(0.0, round((created_dt - deadline_dt).total_seconds() / 3600.0, 2))

    score = 85
    signals = []
    risks = []
    limitations = []

    if deadline_dt:
        if delay_hours <= 0:
            signals.append("按截止时间看，本次提交是按时完成的。")
        elif delay_hours <= 24:
            score -= 8
            risks.append(f"提交时间晚于截止时间约 {delay_hours:.1f} 小时。")
        elif delay_hours <= 72:
            score -= 16
            risks.append(f"提交时间晚于截止时间约 {delay_hours:.1f} 小时，迟交较明显。")
        else:
            score -= 28
            risks.append(f"提交时间晚于截止时间约 {delay_hours:.1f} 小时，建议重点核查。")
    else:
        limitations.append("当前任务未配置明确截止时间，未做时效性扣分。")

    if file_size <= 0:
        score -= 40
        risks.append("文件大小异常，建议先确认提交文件是否完整。")
    elif file_size < 1024:
        score -= 18
        risks.append("文件体积很小，可能只有封面或内容不完整。")
    elif file_size < 4096:
        score -= 8
        signals.append("文件较小，建议结合正文内容再确认完整度。")
    else:
        signals.append(f"文件大小约 {round(file_size / 1024.0, 1)} KB。")

    if excerpt:
        if char_count < 80:
            score -= 22
            risks.append("可读正文很短，疑似内容不足。")
        elif char_count < 300:
            score -= 10
            signals.append("可读正文较短，建议关注是否只提交了摘要。")
        else:
            score += 4
            signals.append(f"已解析到约 {char_count} 个字符的正文内容。")
        if line_count >= 20:
            score += 2
    else:
        limitations.append("当前文件不是易解析文本，建议仍需人工查看正文。")

    score = max(0, min(100, int(round(score))))
    suggested_status = "approved" if score >= 60 else "rejected"

    if suggested_status == "approved":
        note_parts = ["AI 初审建议通过。"]
        if delay_hours > 0:
            note_parts.append(f"本次提交存在迟交（约 {delay_hours:.1f} 小时），建议酌情扣分。")
        if excerpt and char_count >= 300:
            note_parts.append("从可读正文和文件体量看，提交内容具备基本完整性。")
        elif not excerpt:
            note_parts.append("因无法直接解析正文，请老师打开文件做最终确认。")
    else:
        note_parts = ["AI 初审建议先驳回或要求补充。"]
        if delay_hours > 0:
            note_parts.append(f"迟交约 {delay_hours:.1f} 小时。")
        if file_size < 4096:
            note_parts.append("文件体积偏小，疑似内容不完整。")
        if excerpt and char_count < 80:
            note_parts.append("可读正文过短，建议补充实验过程与结果。")
        if not excerpt:
            note_parts.append("当前无法解析正文，建议人工核验后再决定。")

    summary = (
        f"建议{('通过' if suggested_status == 'approved' else '驳回')}，"
        f"建议分数 {score} 分。"
    )
    return {
        "suggestedStatus": suggested_status,
        "suggestedScore": score,
        "suggestedNote": " ".join([x for x in note_parts if x]),
        "summary": summary,
        "signals": signals[:5],
        "risks": risks[:5],
        "limitations": limitations[:3],
        "metrics": {
            "fileSize": file_size,
            "charCount": char_count,
            "lineCount": line_count,
            "delayHours": delay_hours,
            "hasTextExcerpt": bool(excerpt),
        },
    }


def _build_homework_ai_batch_summary(items):
    rows = items if isinstance(items, list) else []
    approved_count = 0
    rejected_count = 0
    score_sum = 0.0
    score_count = 0
    risk_counter = {}
    signal_counter = {}
    limitation_counter = {}

    def _push_counter(counter, values, limit=3):
        for raw in list(values or [])[:limit]:
            text = str(raw or "").strip()
            if not text:
                continue
            counter[text] = int(counter.get(text) or 0) + 1

    for item in rows:
        suggestion = item.get("suggestion") if isinstance(item, dict) else {}
        if not isinstance(suggestion, dict):
            continue
        status = str(suggestion.get("suggestedStatus") or "").strip()
        if status == "approved":
            approved_count += 1
        elif status == "rejected":
            rejected_count += 1
        try:
            score_sum += float(suggestion.get("suggestedScore") or 0)
            score_count += 1
        except Exception:
            pass
        _push_counter(risk_counter, suggestion.get("risks"), limit=4)
        _push_counter(signal_counter, suggestion.get("signals"), limit=3)
        _push_counter(limitation_counter, suggestion.get("limitations"), limit=2)

    def _top_items(counter, kind, limit=5):
        pairs = sorted(counter.items(), key=lambda x: (int(x[1] or 0), str(x[0] or "")), reverse=True)
        return [{"text": str(text or ""), "count": int(count or 0), "kind": kind} for text, count in pairs[:limit]]

    avg_score = round(score_sum / score_count, 2) if score_count > 0 else None
    return {
        "total": len(rows),
        "approvedCount": approved_count,
        "rejectedCount": rejected_count,
        "avgSuggestedScore": avg_score,
        "commonIssues": _top_items(risk_counter, "risk", limit=5),
        "commonSignals": _top_items(signal_counter, "signal", limit=4),
        "commonLimitations": _top_items(limitation_counter, "limitation", limit=3),
    }


def _get_manageable_task_row_or_raise(task_id, current_user):
    rows = query(
        """
        SELECT t.id,
               t.course_id AS courseId,
               t.title AS taskTitle,
               t.description AS taskDescription,
               t.lab_id AS labId,
               t.deadline,
               t.status AS taskStatus,
               t.teacher_user_name AS taskTeacherUserName,
               c.id AS courseRowId,
               c.name AS courseName,
               c.teacher_user_name AS courseTeacherUserName,
               c.status AS courseStatus
        FROM experiment_task t
        LEFT JOIN course c ON c.id=t.course_id
        WHERE t.id=%s
        LIMIT 1
        """,
        (int(task_id),),
    )
    row = rows[0] if rows else None
    if not row or str(row.get("taskStatus") or "").strip() == "deleted":
        raise BizError("task not found", 404)
    if str(row.get("courseStatus") or "").strip() == "deleted":
        raise BizError("course not found", 404)
    if not _can_manage_task(current_user, row):
        raise BizError("forbidden", 403)
    return row


def _build_teacher_task_notice_draft(task_row, audience="学生", extra_hint=""):
    row = task_row or {}
    course_name = str(row.get("courseName") or "").strip() or "课程"
    task_title = str(row.get("taskTitle") or "").strip() or "实验任务"
    deadline_text = _to_text_time(row.get("deadline"))
    description = str(row.get("taskDescription") or "").strip()
    audience_text = str(audience or "学生").strip() or "学生"
    hint = str(extra_hint or "").strip()

    title = f"{course_name}《{task_title}》通知"
    lines = [f"各位{audience_text}："]
    lines.append(f"请关注《{task_title}》的最新安排。")
    if deadline_text:
        lines.append(f"任务截止时间为 {deadline_text}，请按时完成并提交。")
    if description:
        brief = re.sub(r"\s+", " ", description).strip()
        if len(brief) > 120:
            brief = brief[:120] + "…"
        lines.append(f"任务说明：{brief}")
    if hint:
        lines.append(f"补充提醒：{hint}")
    lines.append("如需补交、改期或设备支持，请提前联系任课教师。")
    lines.append("收到后请相互转告。")
    content = "\n".join(lines)
    return {
        "title": title[:120],
        "content": content[:5000],
        "summary": f"已生成面向{audience_text}的课程通知草稿。",
        "audience": audience_text,
        "deadline": deadline_text,
    }


@app.post("/teacher/tasks/<int:task_id>/ai-reserve-plan")
@auth_required(roles=["teacher", "admin"])
def teacher_task_ai_reserve_plan(task_id):
    payload = request.get_json(force=True) or {}
    current_user = g.current_user or {}
    task_row = _get_manageable_task_row_or_raise(task_id, current_user)

    preferred_date = str(payload.get("preferredDate") or "").strip()
    preferred_time = str(payload.get("preferredTime") or "").strip()
    days = max(3, min(int(_to_int_or_none(payload.get("days")) or 7), 21))
    plan_count = max(3, min(int(_to_int_or_none(payload.get("k")) or 3), 5))

    if preferred_date and not _agent_is_valid_date_text(preferred_date):
        raise BizError("invalid preferredDate", 400)
    if preferred_time and not parse_slots(preferred_time):
        raise BizError("invalid preferredTime", 400)

    task_lab_id = _to_int_or_none(payload.get("labId")) or _to_int_or_none(task_row.get("labId"))
    if not task_lab_id:
        raise BizError("labId required", 400)

    lab_rows = query("SELECT id, name FROM lab WHERE id=%s LIMIT 1", (int(task_lab_id),))
    if not lab_rows:
        raise BizError("lab not found", 404)
    lab_row = lab_rows[0] or {}
    student_count_rows = query(
        """
        SELECT COUNT(*) AS cnt
        FROM course_member
        WHERE course_id=%s
          AND status='active'
        """,
        (int(task_row.get("courseId") or 0),),
    )
    student_count = int((student_count_rows[0] or {}).get("cnt") or 0) if student_count_rows else 0

    plans = build_reservation_plans(
        user_name=str(current_user.get("username") or "").strip(),
        lab_id_or_name=int(task_lab_id),
        preferred_date=preferred_date,
        preferred_time=preferred_time,
        days=days,
        k=plan_count,
    )
    normalized_plans = _agent_normalize_plan_items(plans)
    for item in normalized_plans:
        base_reason = str(item.get("reason") or "").strip()
        extra_bits = [f"课程人数约 {student_count} 人"]
        if preferred_date and preferred_time:
            extra_bits.append("已按你的偏好时段寻找替代方案")
        item["reason"] = "；".join([x for x in [base_reason] + extra_bits if x])

    audit_log(
        "teacher.task.ai_reserve_plan",
        target_type="experiment_task",
        target_id=task_id,
        detail={
            "courseId": int(task_row.get("courseId") or 0),
            "labId": int(task_lab_id),
            "preferredDate": preferred_date,
            "preferredTime": preferred_time,
            "planCount": len(normalized_plans),
        },
        actor={"id": current_user.get("id"), "username": current_user.get("username"), "role": current_user.get("role")},
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "taskId": int(task_row.get("id") or 0),
                "courseId": int(task_row.get("courseId") or 0),
                "courseName": str(task_row.get("courseName") or "").strip(),
                "taskTitle": str(task_row.get("taskTitle") or "").strip(),
                "labId": int(lab_row.get("id") or 0),
                "labName": str(lab_row.get("name") or "").strip(),
                "studentCount": student_count,
                "preferredDate": preferred_date,
                "preferredTime": preferred_time,
                "plans": normalized_plans[:plan_count],
            },
        }
    )


@app.post("/teacher/tasks/<int:task_id>/ai-notice-draft")
@auth_required(roles=["teacher", "admin"])
def teacher_task_ai_notice_draft(task_id):
    payload = request.get_json(force=True) or {}
    current_user = g.current_user or {}
    task_row = _get_manageable_task_row_or_raise(task_id, current_user)
    audience = str(payload.get("audience") or "学生").strip() or "学生"
    extra_hint = str(payload.get("extraHint") or "").strip()
    draft = _build_teacher_task_notice_draft(task_row, audience=audience, extra_hint=extra_hint)
    audit_log(
        "teacher.task.ai_notice_draft",
        target_type="experiment_task",
        target_id=task_id,
        detail={"courseId": int(task_row.get("courseId") or 0), "audience": audience},
        actor={"id": current_user.get("id"), "username": current_user.get("username"), "role": current_user.get("role")},
    )
    return jsonify({"ok": True, "data": draft})


@app.get("/teacher/student-files/<int:file_id>/ai-review-suggestion")
@auth_required(roles=["teacher", "admin"])
def teacher_get_ai_review_suggestion(file_id):
    current_user = g.current_user or {}
    rows = query(
        """
        SELECT s.id,
               s.task_id AS taskId,
               s.course_id AS courseId,
               s.student_user_name AS studentUserName,
               s.student_display_name AS studentDisplayName,
               s.file_name AS fileName,
               s.file_url AS fileUrl,
               s.file_size AS fileSize,
               s.mime_type AS mimeType,
               s.created_at AS createdAt,
               s.review_status AS reviewStatus,
               s.review_score AS reviewScore,
               s.review_note AS reviewNote,
               s.status AS submissionStatus,
               t.title AS taskTitle,
               t.description AS taskDescription,
               t.deadline,
               t.status AS taskStatus,
               t.teacher_user_name AS taskTeacherUserName,
               c.name AS courseName,
               c.status AS courseStatus,
               c.teacher_user_name AS courseTeacherUserName
        FROM experiment_task_submission s
        LEFT JOIN experiment_task t ON t.id=s.task_id
        LEFT JOIN course c ON c.id=s.course_id
        WHERE s.id=%s
        LIMIT 1
        """,
        (int(file_id),),
    )
    row = rows[0] if rows else None
    if not row or str(row.get("submissionStatus") or "").strip() == "deleted":
        return jsonify({"ok": False, "msg": "file not found"}), 404
    if str(row.get("taskStatus") or "").strip() == "deleted" or str(row.get("courseStatus") or "").strip() == "deleted":
        return jsonify({"ok": False, "msg": "task not found"}), 404
    if not _can_manage_task(current_user, row):
        return jsonify({"ok": False, "msg": "forbidden"}), 403

    suggestion = _build_homework_ai_suggestion(row)
    audit_log(
        "teacher.student_file.ai_review_suggest",
        target_type="experiment_task_submission",
        target_id=file_id,
        detail={
            "taskId": int(row.get("taskId") or 0),
            "courseId": int(row.get("courseId") or 0),
            "suggestedStatus": suggestion.get("suggestedStatus"),
            "suggestedScore": suggestion.get("suggestedScore"),
        },
        actor={"id": current_user.get("id"), "username": current_user.get("username"), "role": current_user.get("role")},
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "fileId": int(row.get("id") or 0),
                "taskId": int(row.get("taskId") or 0),
                "courseId": int(row.get("courseId") or 0),
                "courseName": str(row.get("courseName") or "").strip(),
                "taskTitle": str(row.get("taskTitle") or "").strip(),
                "studentUserName": str(row.get("studentUserName") or "").strip(),
                "studentDisplayName": str(row.get("studentDisplayName") or "").strip(),
                "fileName": str(row.get("fileName") or "").strip(),
                "currentReviewStatus": str(row.get("reviewStatus") or "").strip(),
                "currentReviewScore": row.get("reviewScore"),
                "suggestion": suggestion,
            },
        }
    )


@app.post("/teacher/student-files/ai-review-suggestions")
@auth_required(roles=["teacher", "admin"])
def teacher_batch_get_ai_review_suggestions():
    payload = request.get_json(force=True) or {}
    raw_ids = payload.get("fileIds")
    if not isinstance(raw_ids, list):
        raise BizError("fileIds required", 400)
    clean_ids = []
    seen_ids = set()
    for raw in raw_ids:
        file_id = _to_int_or_none(raw)
        if not file_id or int(file_id) <= 0 or int(file_id) in seen_ids:
            continue
        seen_ids.add(int(file_id))
        clean_ids.append(int(file_id))
        if len(clean_ids) >= 50:
            break
    if not clean_ids:
        raise BizError("fileIds required", 400)

    placeholders = ",".join(["%s"] * len(clean_ids))
    current_user = g.current_user or {}
    rows = query(
        f"""
        SELECT s.id,
               s.task_id AS taskId,
               s.course_id AS courseId,
               s.student_user_name AS studentUserName,
               s.student_display_name AS studentDisplayName,
               s.file_name AS fileName,
               s.file_url AS fileUrl,
               s.file_size AS fileSize,
               s.mime_type AS mimeType,
               s.created_at AS createdAt,
               s.review_status AS reviewStatus,
               s.review_score AS reviewScore,
               s.review_note AS reviewNote,
               s.status AS submissionStatus,
               t.title AS taskTitle,
               t.description AS taskDescription,
               t.deadline,
               t.status AS taskStatus,
               t.teacher_user_name AS taskTeacherUserName,
               c.name AS courseName,
               c.status AS courseStatus,
               c.teacher_user_name AS courseTeacherUserName
        FROM experiment_task_submission s
        LEFT JOIN experiment_task t ON t.id=s.task_id
        LEFT JOIN course c ON c.id=s.course_id
        WHERE s.id IN ({placeholders})
        """,
        tuple(clean_ids),
    )
    if not rows:
        return jsonify({"ok": False, "msg": "file not found"}), 404

    order_map = {file_id: idx for idx, file_id in enumerate(clean_ids)}
    items = []
    for row in rows:
        if str(row.get("submissionStatus") or "").strip() == "deleted":
            continue
        if str(row.get("taskStatus") or "").strip() == "deleted" or str(row.get("courseStatus") or "").strip() == "deleted":
            continue
        if not _can_manage_task(current_user, row):
            continue
        suggestion = _build_homework_ai_suggestion(row)
        items.append(
            {
                "fileId": int(row.get("id") or 0),
                "taskId": int(row.get("taskId") or 0),
                "courseId": int(row.get("courseId") or 0),
                "courseName": str(row.get("courseName") or "").strip(),
                "taskTitle": str(row.get("taskTitle") or "").strip(),
                "studentUserName": str(row.get("studentUserName") or "").strip(),
                "studentDisplayName": str(row.get("studentDisplayName") or "").strip(),
                "fileName": str(row.get("fileName") or "").strip(),
                "currentReviewStatus": str(row.get("reviewStatus") or "").strip(),
                "currentReviewScore": row.get("reviewScore"),
                "suggestion": suggestion,
            }
        )
    if not items:
        return jsonify({"ok": False, "msg": "forbidden"}), 403

    items.sort(key=lambda x: order_map.get(int(x.get("fileId") or 0), 10**9))
    summary = _build_homework_ai_batch_summary(items)
    audit_log(
        "teacher.student_file.ai_review_suggest.batch",
        target_type="experiment_task_submission",
        detail={
            "count": len(items),
            "approvedCount": int(summary.get("approvedCount") or 0),
            "rejectedCount": int(summary.get("rejectedCount") or 0),
        },
        actor={"id": current_user.get("id"), "username": current_user.get("username"), "role": current_user.get("role")},
    )
    return jsonify({"ok": True, "data": {"items": items, "summary": summary}})


@app.get("/teacher/tasks/<int:task_id>/rubric")
@auth_required(roles=["teacher", "admin"])
def teacher_get_task_rubric(task_id):
    current_user = g.current_user or {}
    task_row = _query_task_access_row(task_id)
    if not task_row:
        raise BizError("task not found", 404)
    if not _can_manage_task(current_user, task_row):
        raise BizError("forbidden", 403)
    return jsonify({"ok": True, "data": _get_task_rubric_payload(task_id)})


@app.post("/teacher/tasks/<int:task_id>/rubric")
@auth_required(roles=["teacher", "admin"])
def teacher_save_task_rubric(task_id):
    current_user = g.current_user or {}
    reviewer = str(current_user.get("username") or "").strip()
    task_row = _query_task_access_row(task_id)
    if not task_row:
        raise BizError("task not found", 404)
    if not _can_manage_task(current_user, task_row):
        raise BizError("forbidden", 403)

    payload = request.get_json(force=True) or {}
    title = str(payload.get("title") or "实验任务评分标准").strip()[:160]
    description = str(payload.get("description") or "").strip()[:500]
    items = _normalize_rubric_items_payload(payload.get("items"))
    total_score = round(sum([float(item.get("maxScore") or 0) for item in items]), 2)
    now_text = _to_text_time(datetime.now())

    def _tx(cur):
        cur.execute(
            """
            SELECT id
            FROM task_rubric_template
            WHERE task_id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(task_id),),
        )
        row = cur.fetchone()
        if row:
            template_id = int(row.get("id") or 0)
            cur.execute(
                """
                UPDATE task_rubric_template
                SET course_id=%s,
                    teacher_user_name=%s,
                    title=%s,
                    description=%s,
                    total_score=%s,
                    status='active',
                    updated_at=%s
                WHERE id=%s
                """,
                (int(task_row.get("courseId") or 0), reviewer, title, description, total_score, now_text, template_id),
            )
            cur.execute("DELETE FROM task_rubric_item WHERE template_id=%s", (template_id,))
        else:
            cur.execute(
                """
                INSERT INTO task_rubric_template (
                    task_id, course_id, teacher_user_name, title, description, total_score, status, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'active', %s, %s)
                """,
                (int(task_id), int(task_row.get("courseId") or 0), reviewer, title, description, total_score, now_text, now_text),
            )
            template_id = int(cur.lastrowid or 0)
        for item in items:
            cur.execute(
                """
                INSERT INTO task_rubric_item (
                    template_id, item_title, description, max_score, sort_order, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (template_id, item.get("itemTitle"), item.get("description"), item.get("maxScore"), item.get("sortOrder"), now_text, now_text),
            )
        return template_id

    template_id = run_in_transaction(_tx)
    audit_log(
        "teacher.task.rubric.save",
        target_type="experiment_task",
        target_id=task_id,
        detail={"templateId": template_id, "itemCount": len(items), "totalScore": total_score},
        actor={"id": current_user.get("id"), "username": reviewer, "role": current_user.get("role")},
    )
    return jsonify({"ok": True, "data": _get_task_rubric_payload(task_id)})


@app.get("/teacher/student-files/<int:file_id>/review-workspace")
@auth_required(roles=["teacher", "admin"])
def teacher_get_review_workspace(file_id):
    current_user = g.current_user or {}
    rows = query(
        """
        SELECT s.id,
               s.task_id AS taskId,
               s.course_id AS courseId,
               s.student_user_name AS studentUserName,
               s.student_display_name AS studentDisplayName,
               s.file_name AS fileName,
               s.file_url AS fileUrl,
               s.file_size AS fileSize,
               s.mime_type AS mimeType,
               s.created_at AS createdAt,
               s.review_status AS reviewStatus,
               s.review_score AS reviewScore,
               s.review_note AS reviewNote,
               s.reviewed_by AS reviewedBy,
               s.reviewed_at AS reviewedAt,
               s.status AS submissionStatus,
               t.title AS taskTitle,
               t.status AS taskStatus,
               t.teacher_user_name AS taskTeacherUserName,
               c.name AS courseName,
               c.status AS courseStatus,
               c.teacher_user_name AS courseTeacherUserName
        FROM experiment_task_submission s
        LEFT JOIN experiment_task t ON t.id=s.task_id
        LEFT JOIN course c ON c.id=s.course_id
        WHERE s.id=%s
        LIMIT 1
        """,
        (int(file_id),),
    )
    row = rows[0] if rows else None
    if not row or str(row.get("submissionStatus") or "").strip() == "deleted":
        raise BizError("file not found", 404)
    if str(row.get("taskStatus") or "").strip() == "deleted" or str(row.get("courseStatus") or "").strip() == "deleted":
        raise BizError("task not found", 404)
    if not _can_manage_task(current_user, row):
        raise BizError("forbidden", 403)
    return jsonify(
        {
            "ok": True,
            "data": {
                "submission": _format_task_submission_row(row),
                "rubric": _get_task_rubric_payload(int(row.get("taskId") or 0)),
                "reviewExtras": _get_submission_review_extras_payload(file_id),
            },
        }
    )


@app.post("/teacher/student-files/ai-review-apply-batch")
@auth_required(roles=["teacher", "admin"])
def teacher_batch_apply_ai_review_suggestions():
    payload = request.get_json(force=True) or {}
    raw_ids = payload.get("fileIds")
    if not isinstance(raw_ids, list):
        raise BizError("fileIds required", 400)
    current_user = g.current_user or {}
    actor = {"id": current_user.get("id"), "username": current_user.get("username"), "role": current_user.get("role")}

    clean_ids = []
    seen = set()
    for raw in raw_ids:
        fid = _to_int_or_none(raw)
        if not fid or int(fid) <= 0 or int(fid) in seen:
            continue
        seen.add(int(fid))
        clean_ids.append(int(fid))
        if len(clean_ids) >= 50:
            break
    if not clean_ids:
        raise BizError("fileIds required", 400)

    results = []
    for file_id in clean_ids:
        try:
            apply_res = teacher_apply_ai_review_suggestion(file_id=file_id, _internal=True)
            results.append({"fileId": int(file_id), "ok": True, "data": apply_res})
        except BizError as e:
            results.append({"fileId": int(file_id), "ok": False, "msg": e.msg})

    success_count = len([item for item in results if item.get("ok")])
    audit_log(
        "teacher.student_file.ai_review_apply.batch",
        target_type="experiment_task_submission",
        detail={"total": len(clean_ids), "successCount": success_count},
        actor=actor,
    )
    log_ai_action(
        "teacher.student_file.ai_review_apply.batch",
        target_type="experiment_task_submission",
        target_id="batch",
        execute_payload={"fileIds": clean_ids, "successCount": success_count},
        actor=actor,
    )
    return jsonify({"ok": True, "data": {"items": results, "successCount": success_count, "total": len(clean_ids)}})


@app.post("/teacher/student-files/<int:file_id>/ai-review-apply")
@auth_required(roles=["teacher", "admin"])
def teacher_apply_ai_review_suggestion(file_id, _internal=False):
    current_user = g.current_user or {}
    reviewer = str(current_user.get("username") or "").strip()
    rows = query(
        """
        SELECT s.id,
               s.task_id AS taskId,
               s.course_id AS courseId,
               s.student_user_name AS studentUserName,
               s.student_display_name AS studentDisplayName,
               s.file_name AS fileName,
               s.file_url AS fileUrl,
               s.file_size AS fileSize,
               s.mime_type AS mimeType,
               s.created_at AS createdAt,
               s.review_status AS reviewStatus,
               s.review_score AS reviewScore,
               s.review_note AS reviewNote,
               s.status AS submissionStatus,
               t.title AS taskTitle,
               t.description AS taskDescription,
               t.deadline,
               t.status AS taskStatus,
               t.teacher_user_name AS taskTeacherUserName,
               c.name AS courseName,
               c.status AS courseStatus,
               c.teacher_user_name AS courseTeacherUserName
        FROM experiment_task_submission s
        LEFT JOIN experiment_task t ON t.id=s.task_id
        LEFT JOIN course c ON c.id=s.course_id
        WHERE s.id=%s
        LIMIT 1
        """,
        (int(file_id),),
    )
    row = rows[0] if rows else None
    if not row or str(row.get("submissionStatus") or "").strip() == "deleted":
        raise BizError("file not found", 404)
    if str(row.get("taskStatus") or "").strip() == "deleted" or str(row.get("courseStatus") or "").strip() == "deleted":
        raise BizError("task not found", 404)
    if not _can_manage_task(current_user, row):
        raise BizError("forbidden", 403)

    suggestion = _build_homework_ai_suggestion(row)
    review_status = _normalize_task_review_status(suggestion.get("suggestedStatus"))
    review_score = _normalize_task_review_score(suggestion.get("suggestedScore"), allow_empty=(review_status != "approved"))
    review_note = _normalize_task_review_note(suggestion.get("suggestedNote"))
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            """
            UPDATE experiment_task_submission
            SET review_status=%s,
                review_score=%s,
                review_note=%s,
                reviewed_by=%s,
                reviewed_at=%s,
                updated_at=%s
            WHERE id=%s
              AND status='active'
            """,
            (review_status, review_score, review_note, reviewer, now_text, now_text, int(file_id)),
        )
        if int(cur.rowcount or 0) != 1:
            raise BizError("file not found", 404)
        cur.execute(
            """
            SELECT s.id,
                   s.task_id AS taskId,
                   s.course_id AS courseId,
                   c.name AS courseName,
                   t.title AS taskTitle,
                   s.student_id AS studentId,
                   s.student_user_name AS studentUserName,
                   s.student_display_name AS studentDisplayName,
                   s.file_name AS fileName,
                   s.file_url AS fileUrl,
                   s.file_size AS fileSize,
                   s.mime_type AS mimeType,
                   s.status,
                   s.review_status AS reviewStatus,
                   s.review_score AS reviewScore,
                   s.review_note AS reviewNote,
                   s.reviewed_by AS reviewedBy,
                   s.reviewed_at AS reviewedAt,
                   s.created_at AS createdAt,
                   s.updated_at AS updatedAt
            FROM experiment_task_submission s
            LEFT JOIN experiment_task t ON t.id=s.task_id
            LEFT JOIN course c ON c.id=s.course_id
            WHERE s.id=%s
              AND s.status='active'
            LIMIT 1
            """,
            (int(file_id),),
        )
        updated = cur.fetchone()
        if not updated:
            raise BizError("file not found", 404)
        return _format_task_submission_row(updated)

    reviewed = run_in_transaction(_tx)
    detail = {
        "taskId": reviewed.get("taskId"),
        "courseId": reviewed.get("courseId"),
        "studentUserName": reviewed.get("studentUserName"),
        "reviewStatus": reviewed.get("reviewStatus"),
        "reviewScore": reviewed.get("reviewScore"),
    }
    audit_log("teacher.student_file.ai_review_apply", target_type="experiment_task_submission", target_id=file_id, detail=detail, actor={"id": current_user.get("id"), "username": reviewer, "role": current_user.get("role")})
    log_ai_action(
        "teacher.student_file.ai_review_apply",
        target_type="experiment_task_submission",
        target_id=file_id,
        suggestion=suggestion,
        execute_payload=detail,
        actor={"id": current_user.get("id"), "username": reviewer, "role": current_user.get("role")},
    )
    if _internal:
        return reviewed
    return jsonify({"ok": True, "data": reviewed})


@app.post("/teacher/student-files/<int:file_id>/review")
@auth_required(roles=["teacher", "admin"])
def review_task_student_file(file_id):
    payload = request.get_json(force=True) or {}
    review_status = _normalize_task_review_status(payload.get("reviewStatus"))
    if review_status not in {"approved", "rejected"}:
        raise BizError("invalid reviewStatus", 400)
    review_score = _normalize_task_review_score(payload.get("reviewScore"), allow_empty=(review_status != "approved"))
    if review_status == "approved" and review_score is None:
        raise BizError("reviewScore required", 400)
    review_note = _normalize_task_review_note(payload.get("reviewNote"))
    rubric_scores = _normalize_submission_rubric_scores(payload.get("rubricScores"))
    annotations = _normalize_submission_annotations(payload.get("annotations"))
    current_user = g.current_user or {}
    reviewer = str(current_user.get("username") or "").strip()
    if not reviewer:
        raise BizError("unauthorized", 401)
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            """
            SELECT s.id,
                   s.task_id AS taskId,
                   s.course_id AS courseId,
                   s.student_user_name AS studentUserName,
                   s.student_display_name AS studentDisplayName,
                   s.file_name AS fileName,
                   s.status AS submissionStatus,
                   t.title AS taskTitle,
                   t.status AS taskStatus,
                   t.teacher_user_name AS taskTeacherUserName,
                   c.name AS courseName,
                   c.status AS courseStatus,
                   c.teacher_user_name AS courseTeacherUserName
            FROM experiment_task_submission s
            LEFT JOIN experiment_task t ON t.id=s.task_id
            LEFT JOIN course c ON c.id=t.course_id
            WHERE s.id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(file_id),),
        )
        row = cur.fetchone()
        if not row or str(row.get("submissionStatus") or "").strip() == "deleted":
            raise BizError("file not found", 404)
        if str(row.get("taskStatus") or "").strip() == "deleted" or str(row.get("courseStatus") or "").strip() == "deleted":
            raise BizError("task not found", 404)
        if not _can_manage_task(current_user, row):
            raise BizError("forbidden", 403)

        cur.execute(
            """
            UPDATE experiment_task_submission
            SET review_status=%s,
                review_score=%s,
                review_note=%s,
                reviewed_by=%s,
                reviewed_at=%s,
                updated_at=%s
            WHERE id=%s
              AND status='active'
            """,
            (
                review_status,
                review_score,
                review_note,
                reviewer,
                now_text,
                now_text,
                int(file_id),
            ),
        )
        if int(cur.rowcount or 0) != 1:
            raise BizError("file not found", 404)

        _replace_submission_review_extras_with_cur(cur, file_id, rubric_scores, annotations, reviewer)

        cur.execute(
            """
            SELECT s.id,
                   s.task_id AS taskId,
                   s.course_id AS courseId,
                   c.name AS courseName,
                   t.title AS taskTitle,
                   s.student_id AS studentId,
                   s.student_user_name AS studentUserName,
                   s.student_display_name AS studentDisplayName,
                   s.file_name AS fileName,
                   s.file_url AS fileUrl,
                   s.file_size AS fileSize,
                   s.mime_type AS mimeType,
                   s.status,
                   s.review_status AS reviewStatus,
                   s.review_score AS reviewScore,
                   s.review_note AS reviewNote,
                   s.reviewed_by AS reviewedBy,
                   s.reviewed_at AS reviewedAt,
                   s.created_at AS createdAt,
                   s.updated_at AS updatedAt
            FROM experiment_task_submission s
            LEFT JOIN experiment_task t ON t.id=s.task_id
            LEFT JOIN course c ON c.id=s.course_id
            WHERE s.id=%s
              AND s.status='active'
            LIMIT 1
            """,
            (int(file_id),),
        )
        updated_row = cur.fetchone()
        if not updated_row:
            raise BizError("file not found", 404)
        return _format_task_submission_row(updated_row)

    reviewed = run_in_transaction(_tx)
    audit_log(
        "teacher.student_file.review",
        target_type="experiment_task_submission",
        target_id=file_id,
        detail={
            "taskId": reviewed.get("taskId"),
            "courseId": reviewed.get("courseId"),
            "studentUserName": reviewed.get("studentUserName"),
            "reviewStatus": reviewed.get("reviewStatus"),
            "reviewScore": reviewed.get("reviewScore"),
            "rubricScoreCount": len(rubric_scores),
            "annotationCount": len(annotations),
        },
        actor={"id": current_user.get("id"), "username": reviewer, "role": current_user.get("role")},
    )
    return jsonify({"ok": True, "data": reviewed})


@app.get("/tasks/<int:task_id>/student-files")
@auth_required()
def list_my_task_student_files(task_id):
    current_user = g.current_user or {}
    user_name = str(current_user.get("username") or "").strip()
    role = str(current_user.get("role") or "").strip()
    if not user_name:
        raise BizError("unauthorized", 401)

    task_row = _query_task_access_row(task_id)
    can_manage = _ensure_task_view_access_or_raise(current_user, task_row)
    query_params = [task_id]
    extra_where = ""
    if not can_manage:
        if role != "student":
            raise BizError("forbidden", 403)
        extra_where = " AND student_user_name=%s"
        query_params.append(user_name)

    rows = query(
        """
        SELECT id,
               task_id AS taskId,
               course_id AS courseId,
               student_id AS studentId,
               student_user_name AS studentUserName,
               student_display_name AS studentDisplayName,
               file_name AS fileName,
               file_url AS fileUrl,
               file_size AS fileSize,
               mime_type AS mimeType,
               status,
               review_status AS reviewStatus,
               review_score AS reviewScore,
               review_note AS reviewNote,
               reviewed_by AS reviewedBy,
               reviewed_at AS reviewedAt,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM experiment_task_submission
        WHERE task_id=%s
          AND status='active'
        """
        + extra_where
        + """
        ORDER BY id DESC
        """,
        tuple(query_params),
    )
    return jsonify({"ok": True, "data": [_format_task_submission_row(row) for row in rows]})


@app.post("/tasks/<int:task_id>/student-files/upload")
@auth_required()
def upload_task_student_file(task_id):
    current_user = g.current_user or {}
    student_id = _to_int_or_none(current_user.get("id"))
    student_user_name = str(current_user.get("username") or "").strip()
    if not student_user_name:
        raise BizError("unauthorized", 401)
    has_file = "file" in request.files
    text_content = _normalize_task_submission_text(
        (request.form.get("textContent") if request.form else None)
        or ((request.get_json(silent=True) or {}).get("textContent"))
    )
    if not has_file and not text_content:
        raise BizError("file or textContent required", 400)

    f = request.files["file"] if has_file else None
    raw_name = _sanitize_upload_file_name(getattr(f, "filename", "")) if has_file else "文本作业.txt"
    mime_type = str(getattr(f, "mimetype", "") or "").strip() if has_file else "text/plain"
    student_display_name = _resolve_student_display_name(student_id, student_user_name)
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            """
            SELECT t.id AS taskId,
                   t.course_id AS courseId,
                   t.title,
                   t.status AS taskStatus,
                   t.teacher_user_name AS taskTeacherUserName,
                   c.status AS courseStatus,
                   c.teacher_user_name AS courseTeacherUserName
            FROM experiment_task t
            LEFT JOIN course c ON c.id=t.course_id
            WHERE t.id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (task_id,),
        )
        row = cur.fetchone()
        _ensure_task_submit_access_or_raise(current_user, row)

        os.makedirs(os.path.join(UPLOAD_DIR, TASK_SUBMISSION_SUBDIR), exist_ok=True)
        store_name = _build_task_file_store_name(raw_name)
        rel_path = f"{TASK_SUBMISSION_SUBDIR}/{store_name}"
        abs_path = os.path.join(UPLOAD_DIR, TASK_SUBMISSION_SUBDIR, store_name)
        if has_file:
            f.save(abs_path)
        else:
            with open(abs_path, "w", encoding="utf-8") as fp:
                fp.write(text_content)
        file_size = int(os.path.getsize(abs_path) or 0)
        if file_size <= 0:
            try:
                os.remove(abs_path)
            except OSError:
                pass
            raise BizError("empty submission", 400)
        if file_size > TASK_SUBMISSION_MAX_SIZE_BYTES:
            try:
                os.remove(abs_path)
            except OSError:
                pass
            raise BizError("submission too large", 400)

        file_url = f"/uploads/{rel_path}"
        cur.execute(
            """
            UPDATE experiment_task_submission
            SET status='deleted', updated_at=%s
            WHERE task_id=%s
              AND student_user_name=%s
              AND status='active'
            """,
            (
                now_text,
                int(row.get("taskId") or 0),
                student_user_name,
            ),
        )
        replaced_count = int(cur.rowcount or 0)
        cur.execute(
            """
            INSERT INTO experiment_task_submission (
                task_id, course_id, student_id, student_user_name, student_display_name,
                file_name, file_url, file_size, mime_type, status, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', %s, %s)
            """,
            (
                int(row.get("taskId") or 0),
                int(row.get("courseId") or 0),
                student_id,
                student_user_name,
                student_display_name,
                raw_name,
                file_url,
                file_size,
                mime_type,
                now_text,
                now_text,
            ),
        )
        new_id = int(cur.lastrowid or 0)
        return {
            "id": new_id,
            "taskId": int(row.get("taskId") or 0),
            "courseId": int(row.get("courseId") or 0),
            "studentId": student_id,
            "studentUserName": student_user_name,
            "studentDisplayName": student_display_name,
            "fileName": raw_name,
            "fileUrl": file_url,
            "fileSize": file_size,
            "mimeType": mime_type,
            "status": "active",
            "replacedCount": replaced_count,
            "createdAt": now_text,
            "updatedAt": now_text,
        }

    saved = run_in_transaction(_tx)
    audit_log(
        "task.student_file.upload",
        target_type="experiment_task_submission",
        target_id=saved.get("id"),
        detail={
            "taskId": saved.get("taskId"),
            "courseId": saved.get("courseId"),
            "studentUserName": saved.get("studentUserName"),
            "fileName": saved.get("fileName"),
            "fileSize": saved.get("fileSize"),
            "mimeType": saved.get("mimeType"),
            "maxSizeBytes": TASK_SUBMISSION_MAX_SIZE_BYTES,
            "replacedCount": int(saved.get("replacedCount") or 0),
            "submitMode": "file" if has_file else "text",
        },
        actor={"id": student_id, "username": student_user_name, "role": current_user.get("role")},
    )
    return jsonify({"ok": True, "data": saved})


@app.post("/tasks/student-files/<int:file_id>/withdraw")
@auth_required()
def withdraw_my_task_student_file(file_id):
    current_user = g.current_user or {}
    student_user_name = str(current_user.get("username") or "").strip()
    role = str(current_user.get("role") or "").strip().lower()
    if not student_user_name:
        raise BizError("unauthorized", 401)
    if role != "student":
        raise BizError("forbidden", 403)

    now_dt = datetime.now()
    now_text = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            """
            SELECT s.id,
                   s.task_id AS taskId,
                   s.course_id AS courseId,
                   s.student_user_name AS studentUserName,
                   s.file_name AS fileName,
                   s.status AS submissionStatus,
                   t.title AS taskTitle,
                   t.status AS taskStatus,
                   t.deadline AS deadline,
                   c.status AS courseStatus
            FROM experiment_task_submission s
            LEFT JOIN experiment_task t ON t.id=s.task_id
            LEFT JOIN course c ON c.id=t.course_id
            WHERE s.id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (file_id,),
        )
        row = cur.fetchone()
        if not row or str(row.get("submissionStatus") or "").strip() == "deleted":
            raise BizError("file not found", 404)
        if str(row.get("studentUserName") or "").strip() != student_user_name:
            raise BizError("forbidden", 403)
        if str(row.get("taskStatus") or "").strip() == "deleted" or str(row.get("courseStatus") or "").strip() == "deleted":
            raise BizError("task not found", 404)

        deadline_dt = _parse_task_deadline_datetime(row.get("deadline"))
        if deadline_dt and now_dt > deadline_dt:
            raise BizError("deadline passed, cannot withdraw", 409)

        cur.execute(
            """
            UPDATE experiment_task_submission
            SET status='deleted', updated_at=%s
            WHERE id=%s
              AND status='active'
            """,
            (now_text, file_id),
        )
        if int(cur.rowcount or 0) != 1:
            raise BizError("file not found", 404)
        return {
            "id": int(row.get("id") or 0),
            "taskId": int(row.get("taskId") or 0),
            "courseId": int(row.get("courseId") or 0),
            "taskTitle": str(row.get("taskTitle") or "").strip(),
            "fileName": str(row.get("fileName") or "").strip(),
            "deadline": _to_text_time(row.get("deadline")),
        }

    withdrawn = run_in_transaction(_tx)
    audit_log(
        "student.task_file.withdraw",
        target_type="experiment_task_submission",
        target_id=file_id,
        detail={
            "taskId": withdrawn.get("taskId"),
            "courseId": withdrawn.get("courseId"),
            "taskTitle": withdrawn.get("taskTitle"),
            "fileName": withdrawn.get("fileName"),
            "deadline": withdrawn.get("deadline"),
        },
        actor={"id": current_user.get("id"), "username": student_user_name, "role": role},
    )
    return jsonify({"ok": True, "data": {"id": int(file_id), "taskId": withdrawn.get("taskId")}})


@app.post("/teacher/student-files/<int:file_id>/delete")
@auth_required(roles=["teacher", "admin"])
def delete_task_student_file(file_id):
    current_user = g.current_user or {}
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        cur.execute(
            """
            SELECT s.id,
                   s.task_id AS taskId,
                   s.course_id AS courseId,
                   s.file_name AS fileName,
                   s.student_user_name AS studentUserName,
                   s.status AS submissionStatus,
                   t.title AS taskTitle,
                   t.teacher_user_name AS taskTeacherUserName,
                   c.teacher_user_name AS courseTeacherUserName
            FROM experiment_task_submission s
            LEFT JOIN experiment_task t ON t.id=s.task_id
            LEFT JOIN course c ON c.id=t.course_id
            WHERE s.id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (file_id,),
        )
        row = cur.fetchone()
        if not row or str(row.get("submissionStatus") or "").strip() == "deleted":
            raise BizError("file not found", 404)
        if not _can_manage_task(current_user, row):
            raise BizError("forbidden", 403)

        cur.execute(
            """
            UPDATE experiment_task_submission
            SET status='deleted', updated_at=%s
            WHERE id=%s
              AND status<>'deleted'
            """,
            (now_text, file_id),
        )
        if int(cur.rowcount or 0) != 1:
            raise BizError("file not found", 404)
        return {
            "id": int(row.get("id") or 0),
            "taskId": int(row.get("taskId") or 0),
            "courseId": int(row.get("courseId") or 0),
            "taskTitle": str(row.get("taskTitle") or "").strip(),
            "studentUserName": str(row.get("studentUserName") or "").strip(),
            "fileName": str(row.get("fileName") or "").strip(),
        }

    deleted = run_in_transaction(_tx)
    audit_log(
        "teacher.student_file.delete",
        target_type="experiment_task_submission",
        target_id=file_id,
        detail={
            "taskId": deleted.get("taskId"),
            "courseId": deleted.get("courseId"),
            "taskTitle": deleted.get("taskTitle"),
            "studentUserName": deleted.get("studentUserName"),
            "fileName": deleted.get("fileName"),
            "deleteMode": "soft",
        },
    )
    return jsonify({"ok": True, "data": {"id": int(file_id), "taskId": deleted.get("taskId")}})
