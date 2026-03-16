from . import core as _core

for _k, _v in _core.__dict__.items():
    if _k.startswith("__"):
        continue
    globals()[_k] = _v

del _k, _v, _core


def _progress_now():
    return datetime.now()


def _progress_status_for_task(row):
    review_status = str((row or {}).get("reviewStatus") or "").strip().lower()
    submitted_at = _to_datetime((row or {}).get("submittedAt"))
    deadline_dt = _to_datetime((row or {}).get("deadline"))
    now_dt = _progress_now()
    if submitted_at != datetime.min:
        if review_status == "approved":
            return "reviewed_pass"
        if review_status == "rejected":
            return "reviewed_reject"
        return "pending_review"
    if deadline_dt != datetime.min and deadline_dt < now_dt:
        return "overdue"
    return "pending_submit"


def _build_task_progress_items(user_name):
    rows = query(
        """
        SELECT t.id AS taskId,
               t.course_id AS courseId,
               t.title AS taskTitle,
               t.deadline,
               c.name AS courseName,
               latest.id AS submissionId,
               latest.review_status AS reviewStatus,
               latest.created_at AS submittedAt,
               latest.reviewed_at AS reviewedAt
        FROM course_member cm
        INNER JOIN experiment_task t ON t.course_id=cm.course_id AND t.status='active'
        INNER JOIN course c ON c.id=t.course_id AND c.status<>'deleted'
        LEFT JOIN (
            SELECT s1.id,
                   s1.task_id,
                   s1.student_user_name,
                   s1.review_status,
                   s1.created_at,
                   s1.reviewed_at
            FROM experiment_task_submission s1
            INNER JOIN (
                SELECT task_id, student_user_name, MAX(id) AS maxId
                FROM experiment_task_submission
                WHERE status='active'
                GROUP BY task_id, student_user_name
            ) latest_row ON latest_row.maxId=s1.id
        ) latest ON latest.task_id=t.id AND latest.student_user_name=cm.student_user_name
        WHERE cm.student_user_name=%s
          AND cm.status='active'
        ORDER BY t.deadline ASC, t.id DESC
        LIMIT 100
        """,
        (user_name,),
    )
    items = []
    for row in rows:
        status = _progress_status_for_task(row)
        item = {
            "type": "task",
            "taskId": int(row.get("taskId") or 0),
            "courseId": int(row.get("courseId") or 0),
            "courseName": str(row.get("courseName") or "").strip(),
            "title": str(row.get("taskTitle") or "").strip(),
            "deadline": _to_text_time(row.get("deadline")),
            "reviewStatus": str(row.get("reviewStatus") or "").strip(),
            "submittedAt": _to_text_time(row.get("submittedAt")),
            "reviewedAt": _to_text_time(row.get("reviewedAt")),
            "status": status,
            "actionPath": f"/pages/teacher/course_detail?courseId={int(row.get('courseId') or 0)}",
        }
        items.append(item)
    return items


def _build_reservation_progress_items(user_name):
    rows = query(
        """
        SELECT id,
               lab_name AS labName,
               date,
               time,
               status,
               created_at AS createdAt,
               admin_note AS adminNote,
               reject_reason AS rejectReason
        FROM reservation
        WHERE user_name=%s
        ORDER BY id DESC
        LIMIT 30
        """,
        (user_name,),
    )
    return [
        {
            "type": "reservation",
            "id": int(row.get("id") or 0),
            "title": str(row.get("labName") or "").strip() or "未命名实验室",
            "date": str(row.get("date") or "").strip(),
            "time": str(row.get("time") or "").strip(),
            "status": str(row.get("status") or "").strip(),
            "createdAt": _to_text_time(row.get("createdAt")),
            "adminNote": str(row.get("adminNote") or "").strip(),
            "rejectReason": str(row.get("rejectReason") or "").strip(),
            "actionPath": "/pages/my/reservations",
        }
        for row in rows
    ]


def _build_waitlist_progress_items(user_name):
    rows = query(
        """
        SELECT id,
               lab_name AS labName,
               date,
               time,
               status,
               priority_score AS priorityScore,
               created_at AS createdAt
        FROM reservation_waitlist
        WHERE user_name=%s
        ORDER BY id DESC
        LIMIT 20
        """,
        (user_name,),
    )
    return [
        {
            "type": "waitlist",
            "id": int(row.get("id") or 0),
            "title": str(row.get("labName") or "").strip() or "预约候补",
            "date": str(row.get("date") or "").strip(),
            "time": str(row.get("time") or "").strip(),
            "status": str(row.get("status") or "").strip(),
            "priorityScore": float(row.get("priorityScore") or 0),
            "createdAt": _to_text_time(row.get("createdAt")),
            "actionPath": "/pages/my/reservations",
        }
        for row in rows
    ]


def _build_borrow_progress_items(user_name):
    rows = query(
        """
        SELECT id,
               equipment_name AS equipmentName,
               equipment_asset_code AS equipmentAssetCode,
               expected_return_at AS expectedReturnAt,
               returned_at AS returnedAt,
               status,
               created_at AS createdAt
        FROM equipment_borrow_request
        WHERE applicant_user_name=%s
        ORDER BY id DESC
        LIMIT 30
        """,
        (user_name,),
    )
    items = []
    now_dt = _progress_now()
    for row in rows:
        expected_dt = _to_datetime(row.get("expectedReturnAt"))
        overdue = bool(str(row.get("status") or "").strip() == "approved" and expected_dt != datetime.min and expected_dt < now_dt and not row.get("returnedAt"))
        items.append(
            {
                "type": "borrow",
                "id": int(row.get("id") or 0),
                "title": str(row.get("equipmentName") or "").strip() or str(row.get("equipmentAssetCode") or "").strip() or "设备借用",
                "status": "overdue" if overdue else str(row.get("status") or "").strip(),
                "expectedReturnAt": _to_text_time(row.get("expectedReturnAt")),
                "returnedAt": _to_text_time(row.get("returnedAt")),
                "createdAt": _to_text_time(row.get("createdAt")),
                "actionPath": "/pages/my/borrowings",
            }
        )
    return items


def _build_repair_progress_items(user_name):
    rows = query(
        """
        SELECT id,
               order_no AS orderNo,
               equipment_name AS equipmentName,
               lab_name AS labName,
               status,
               submitted_at AS submittedAt,
               updated_at AS updatedAt
        FROM repair_work_order
        WHERE submitter_name=%s
        ORDER BY id DESC
        LIMIT 20
        """,
        (user_name,),
    )
    return [
        {
            "type": "repair",
            "id": int(row.get("id") or 0),
            "title": str(row.get("equipmentName") or "").strip() or str(row.get("labName") or "").strip() or str(row.get("orderNo") or "").strip(),
            "status": str(row.get("status") or "").strip(),
            "submittedAt": _to_text_time(row.get("submittedAt")),
            "updatedAt": _to_text_time(row.get("updatedAt")),
            "actionPath": "/pages/my/repair_orders",
        }
        for row in rows
    ]


def _build_attendance_progress_items(user_name):
    active_rows = query(
        """
        SELECT s.id,
               s.course_id AS courseId,
               s.course_name AS courseName,
               s.lab_name AS labName,
               s.status,
               s.start_at AS startAt,
               s.end_at AS endAt,
               r.id AS recordId,
               r.status AS recordStatus,
               r.final_checkin_at AS finalCheckinAt
        FROM attendance_session s
        INNER JOIN course_member cm ON cm.course_id=s.course_id AND cm.student_user_name=%s AND cm.status='active'
        LEFT JOIN attendance_record r ON r.session_id=s.id AND r.student_user_name=%s
        WHERE s.status='open'
        ORDER BY s.id DESC
        LIMIT 20
        """,
        (user_name, user_name),
    )
    recent_rows = query(
        """
        SELECT r.id,
               r.session_id AS sessionId,
               s.course_name AS courseName,
               s.lab_name AS labName,
               r.status,
               r.final_checkin_at AS finalCheckinAt,
               r.updated_at AS updatedAt
        FROM attendance_record r
        LEFT JOIN attendance_session s ON s.id=r.session_id
        WHERE r.student_user_name=%s
        ORDER BY r.id DESC
        LIMIT 10
        """,
        (user_name,),
    )
    active = [
        {
            "type": "attendance",
            "id": int(row.get("id") or 0),
            "title": str(row.get("courseName") or "").strip() or "课堂签到",
            "labName": str(row.get("labName") or "").strip(),
            "status": str(row.get("recordStatus") or "pending").strip(),
            "startAt": _to_text_time(row.get("startAt")),
            "endAt": _to_text_time(row.get("endAt")),
            "recordId": _to_int_or_none(row.get("recordId")),
            "finalCheckinAt": _to_text_time(row.get("finalCheckinAt")),
            "actionPath": "/pages/student/attendance",
        }
        for row in active_rows
    ]
    recent = [
        {
            "type": "attendance_history",
            "id": int(row.get("id") or 0),
            "title": str(row.get("courseName") or "").strip() or "课堂签到",
            "labName": str(row.get("labName") or "").strip(),
            "status": str(row.get("status") or "").strip(),
            "finalCheckinAt": _to_text_time(row.get("finalCheckinAt")),
            "updatedAt": _to_text_time(row.get("updatedAt")),
            "actionPath": "/pages/student/attendance",
        }
        for row in recent_rows
    ]
    return {"active": active, "recent": recent}


@app.get("/student/progress")
@auth_required()
def get_student_progress():
    current_user = g.current_user or {}
    user_name = str(current_user.get("username") or "").strip()
    if not user_name:
        raise BizError("unauthorized", 401)

    task_items = _build_task_progress_items(user_name)
    reservation_items = _build_reservation_progress_items(user_name)
    waitlist_items = _build_waitlist_progress_items(user_name)
    borrow_items = _build_borrow_progress_items(user_name)
    repair_items = _build_repair_progress_items(user_name)
    attendance_pack = _build_attendance_progress_items(user_name)
    attendance_active_items = attendance_pack.get("active") or []
    attendance_recent_items = attendance_pack.get("recent") or []

    todo_items = []
    todo_items.extend([item for item in task_items if item.get("status") in {"pending_submit", "overdue", "pending_review"}][:6])
    todo_items.extend([item for item in attendance_active_items if item.get("status") in {"pending", "pending_confirm", ""}][:4])
    todo_items.extend([item for item in borrow_items if item.get("status") in {"overdue", "approved"}][:3])
    todo_items.extend([item for item in reservation_items if item.get("status") == "pending"][:3])
    todo_items = todo_items[:12]

    timeline = []
    timeline.extend(task_items[:10])
    timeline.extend(reservation_items[:10])
    timeline.extend(waitlist_items[:6])
    timeline.extend(borrow_items[:10])
    timeline.extend(repair_items[:10])
    timeline.extend(attendance_recent_items[:10])
    timeline.sort(key=lambda item: str(item.get("updatedAt") or item.get("reviewedAt") or item.get("submittedAt") or item.get("createdAt") or item.get("finalCheckinAt") or item.get("deadline") or item.get("startAt") or ""), reverse=True)

    summary = {
        "pendingTaskCount": len([item for item in task_items if item.get("status") in {"pending_submit", "overdue"}]),
        "pendingReviewCount": len([item for item in task_items if item.get("status") == "pending_review"]),
        "activeReservationCount": len([item for item in reservation_items if item.get("status") in {"pending", "approved"}]),
        "waitlistCount": len([item for item in waitlist_items if item.get("status") == "waiting"]),
        "borrowActiveCount": len([item for item in borrow_items if item.get("status") in {"pending", "approved", "overdue"}]),
        "borrowOverdueCount": len([item for item in borrow_items if item.get("status") == "overdue"]),
        "repairActiveCount": len([item for item in repair_items if item.get("status") in {"submitted", "accepted", "processing"}]),
        "pendingAttendanceCount": len([item for item in attendance_active_items if item.get("status") in {"pending", "pending_confirm", ""}]),
    }

    data = {
        "summary": summary,
        "todoItems": todo_items,
        "timeline": timeline[:30],
        "sections": {
            "tasks": task_items[:20],
            "reservations": reservation_items[:20],
            "waitlist": waitlist_items[:20],
            "borrowings": borrow_items[:20],
            "repairs": repair_items[:20],
            "attendance": attendance_active_items[:20],
        },
    }
    return jsonify({"ok": True, "data": data})
