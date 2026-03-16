from . import core as _core

for _k, _v in _core.__dict__.items():
    if _k.startswith("__"):
        continue
    globals()[_k] = _v

del _k, _v, _core

EQUIPMENT_STATUS_SET = {"in_service", "repairing", "scrapped"}
EQUIPMENT_EVENT_TYPE_SET = {
    "register",
    "borrow",
    "return",
    "maintain",
    "inspect",
    "scrap",
    "transfer",
    "inventory",
    "maint_plan",
}
EQUIPMENT_EVENT_USER_ALLOWED = {"maintain"}
INVENTORY_SESSION_STATUS_SET = {"open", "closed"}
INVENTORY_ITEM_STATUS_SET = {"pending", "matched", "moved", "missing", "unexpected", "scrapped"}
INVENTORY_DIFF_TYPE_SET = {"", "lab_mismatch", "missing", "unexpected", "scrapped"}
REPAIR_ORDER_STATUS_FLOW = ("submitted", "accepted", "processing", "completed")
REPAIR_ORDER_STATUS_SET = set(REPAIR_ORDER_STATUS_FLOW)
REPAIR_ORDER_NEXT_STATUS = {
    "submitted": "accepted",
    "accepted": "processing",
    "processing": "completed",
}
REPAIR_ISSUE_TYPE_SET = {"computer", "lighting", "floor", "network", "other"}
REPAIR_ISSUE_TYPE_ALIAS = {
    "computer": "computer",
    "lighting": "lighting",
    "floor": "floor",
    "network": "network",
    "other": "other",
}
BORROW_REQUEST_STATUS_SET = {"pending", "approved", "rejected", "returned", "cancelled"}
BORROW_REMIND_TYPE_SET = {"auto", "manual"}
BORROW_EXTENSION_STATUS_SET = {"pending", "approved", "rejected", "cancelled"}
BORROW_COMPENSATION_STATUS_SET = {"pending", "confirmed", "paid", "waived"}


def _to_bool_flag(value):
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


def _now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_optional_bool(raw_value, field_name):
    text = str(raw_value or "").strip().lower()
    if text == "":
        return None
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise BizError(f"invalid {field_name}", 400)


def _normalize_text(value, field_name, max_len=255):
    text = str(value or "").strip()
    if len(text) > int(max_len):
        raise BizError(f"{field_name} too long", 400)
    return text


def _normalize_datetime_text(raw_value, field_name, allow_empty=True):
    text = str(raw_value or "").strip()
    if not text:
        if allow_empty:
            return None
        raise BizError(f"{field_name} required", 400)
    text = text.replace("T", " ")
    dt = _to_datetime(text)
    if dt == datetime.min:
        raise BizError(f"invalid {field_name}", 400)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _normalize_positive_int(raw_value, field_name, min_value=1, max_value=3650):
    if raw_value in (None, ""):
        return None
    num = _to_int_or_none(raw_value)
    if num is None:
        raise BizError(f"invalid {field_name}", 400)
    num = int(num)
    if num < int(min_value) or num > int(max_value):
        raise BizError(f"invalid {field_name}", 400)
    return num


def _build_inventory_no():
    return f"IV{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


def _new_qr_token():
    return uuid.uuid4().hex[:24]


def _normalize_repair_issue_type(value):
    text = str(value or "").strip()
    if not text:
        return "other"
    mapped = REPAIR_ISSUE_TYPE_ALIAS.get(text, REPAIR_ISSUE_TYPE_ALIAS.get(text.lower(), text.lower()))
    if mapped not in REPAIR_ISSUE_TYPE_SET:
        raise BizError("invalid issueType", 400)
    return mapped


def _normalize_repair_description(value, *, allow_empty=False):
    text = str(value or "").strip()
    if not text:
        if allow_empty:
            return ""
        raise BizError("description required", 400)
    if len(text) > 1000:
        raise BizError("description too long", 400)
    return text


def _normalize_repair_attachment_url(value):
    text = str(value or "").strip()
    if len(text) > 500:
        raise BizError("attachmentUrl too long", 400)
    return text


def _normalize_repair_attachment_item(value):
    row = value if isinstance(value, dict) else {}
    file_url = _normalize_repair_attachment_url(row.get("url") or row.get("fileUrl") or row.get("attachmentUrl"))
    file_name = _normalize_text(row.get("name") or row.get("fileName") or os.path.basename(file_url), "fileName", 200)
    file_type = _normalize_text(row.get("fileType") or "image", "fileType", 32) or "image"
    mime_type = _normalize_text(row.get("mimeType"), "mimeType", 100)
    ocr_text = _normalize_text(row.get("ocrText"), "ocrText", 1000)
    if not file_url and not ocr_text:
        return None
    return {
        "url": file_url,
        "name": file_name,
        "fileType": file_type,
        "mimeType": mime_type,
        "ocrText": ocr_text,
    }


def _normalize_repair_attachments_payload(value):
    items = []
    seen = set()
    if isinstance(value, list):
        source = value
    else:
        source = []
    for item in source:
        normalized = _normalize_repair_attachment_item(item)
        if not normalized:
            continue
        key = (normalized.get("url"), normalized.get("name"), normalized.get("ocrText"))
        if key in seen:
            continue
        seen.add(key)
        items.append(normalized)
        if len(items) >= 5:
            break
    return items


def _safe_int(value):
    n = _to_int_or_none(value)
    return int(n) if n is not None else None


def _minutes_between(start_raw, end_raw):
    if start_raw in (None, "") or end_raw in (None, ""):
        return None
    start_dt = _to_datetime(start_raw)
    end_dt = _to_datetime(end_raw)
    if start_dt == datetime.min or end_dt == datetime.min:
        return None
    diff = int((end_dt - start_dt).total_seconds() // 60)
    if diff < 0:
        return None
    return diff


def _build_repair_order_no():
    return f"WO{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"


def _repair_order_select_fragment():
    return """
        SELECT rwo.id,
               rwo.order_no AS orderNo,
               rwo.equipment_id AS equipmentId,
               rwo.asset_code AS assetCode,
               rwo.equipment_name AS equipmentName,
               rwo.lab_id AS labId,
               rwo.lab_name AS labName,
               rwo.issue_type AS issueType,
               rwo.description,
               rwo.attachment_url AS attachmentUrl,
               rwo.ai_issue_type AS aiIssueType,
               rwo.ai_fault_part AS aiFaultPart,
               rwo.ai_priority AS aiPriority,
               rwo.ai_summary AS aiSummary,
               rwo.ai_possible_causes AS aiPossibleCauses,
               rwo.ai_suggestions AS aiSuggestions,
               rwo.ai_confidence AS aiConfidence,
               rwo.ai_ocr_text AS aiOcrText,
               rwo.ai_model_name AS aiModelName,
               rwo.ai_raw_json AS aiRawJson,
               rwo.status,
               rwo.submitter_id AS submitterId,
               rwo.submitter_name AS submitterName,
               rwo.assignee_id AS assigneeId,
               rwo.assignee_name AS assigneeName,
               rwo.submitted_at AS submittedAt,
               rwo.accepted_at AS acceptedAt,
               rwo.processing_at AS processingAt,
               rwo.completed_at AS completedAt,
               rwo.followup_score AS followupScore,
               rwo.followup_comment AS followupComment,
               rwo.followup_at AS followupAt,
               rwo.created_at AS createdAt,
               rwo.updated_at AS updatedAt
        FROM repair_work_order rwo
    """


def _decode_ai_suggestions(value):
    if isinstance(value, list):
        source = value
    else:
        text = str(value or "").strip()
        if not text:
            return []
        source = []
        try:
            obj = json.loads(text)
        except Exception:
            obj = None
        if isinstance(obj, list):
            source = obj
        elif isinstance(obj, str):
            source = [obj]
        else:
            source = re.split(r"[;\n]+", text)
    dedup = []
    seen = set()
    for item in source:
        text = re.sub(r"\s+", " ", str(item or "").strip())
        if not text:
            continue
        if len(text) > 120:
            text = text[:120]
        if text in seen:
            continue
        seen.add(text)
        dedup.append(text)
        if len(dedup) >= 5:
            break
    return dedup


def _format_repair_order_row(row):
    out = dict(row or {})
    duration = {
        "responseMinutes": _minutes_between(out.get("submittedAt"), out.get("acceptedAt")),
        "processingMinutes": _minutes_between(out.get("processingAt"), out.get("completedAt")),
        "totalMinutes": _minutes_between(out.get("submittedAt"), out.get("completedAt")),
        "elapsedMinutes": _minutes_between(out.get("submittedAt"), out.get("completedAt") or datetime.now()),
    }
    out["durations"] = duration

    for key in ("id", "equipmentId", "labId", "submitterId", "assigneeId"):
        n = _safe_int(out.get(key))
        out[key] = n if n is not None else 0 if key in ("id",) else None

    score = _safe_int(out.get("followupScore"))
    out["followupScore"] = score
    out["followupComment"] = str(out.get("followupComment") or "").strip()

    ai_issue_type = str(out.get("aiIssueType") or "").strip().lower()
    if ai_issue_type and ai_issue_type not in REPAIR_ISSUE_TYPE_SET:
        ai_issue_type = "other"
    ai_fault_part = str(out.get("aiFaultPart") or "").strip()
    ai_priority = str(out.get("aiPriority") or "").strip().upper()
    if ai_priority not in {"P0", "P1", "P2"}:
        ai_priority = "P2" if ai_issue_type else ""
    ai_summary = str(out.get("aiSummary") or "").strip()
    ai_possible_causes = _decode_ai_suggestions(out.get("aiPossibleCauses"))
    ai_suggestions = _decode_ai_suggestions(out.get("aiSuggestions"))
    try:
        ai_confidence = round(float(out.get("aiConfidence") or 0), 4)
    except Exception:
        ai_confidence = 0.0
    if ai_confidence < 0:
        ai_confidence = 0.0
    if ai_confidence > 1:
        ai_confidence = 1.0
    ai_raw_json = str(out.get("aiRawJson") or "").strip()
    if len(ai_raw_json) > 20000:
        ai_raw_json = ai_raw_json[:20000]
    ai_ocr_text = str(out.get("aiOcrText") or "").strip()
    ai_model_name = str(out.get("aiModelName") or "").strip()
    out["aiIssueType"] = ai_issue_type or None
    out["aiFaultPart"] = ai_fault_part or None
    out["aiPriority"] = ai_priority or None
    out["aiSummary"] = ai_summary or ""
    out["aiPossibleCauses"] = ai_possible_causes
    out["aiSuggestions"] = ai_suggestions
    out["aiConfidence"] = ai_confidence
    out["aiOcrText"] = ai_ocr_text
    out["aiModelName"] = ai_model_name
    out["aiRawJson"] = ai_raw_json
    out["ai"] = {
        "issueType": out["aiIssueType"],
        "faultPart": out["aiFaultPart"],
        "priority": out["aiPriority"],
        "summary": out["aiSummary"],
        "possibleCauses": ai_possible_causes,
        "suggestions": ai_suggestions,
        "confidence": ai_confidence,
        "ocrText": ai_ocr_text,
        "modelName": ai_model_name,
        "rawJson": ai_raw_json,
    }

    for key in (
        "submittedAt",
        "acceptedAt",
        "processingAt",
        "completedAt",
        "followupAt",
        "createdAt",
        "updatedAt",
    ):
        out[key] = _to_text_time(out.get(key))
    return out


def _get_repair_order_or_raise(order_id):
    rows = query(
        _repair_order_select_fragment()
        + """
          WHERE rwo.id=%s
          LIMIT 1
        """,
        (order_id,),
    )
    if not rows:
        raise BizError("repair order not found", 404)
    return rows[0]


def _get_repair_attachment_rows(order_id):
    rows = query(
        """
        SELECT id,
               work_order_id AS workOrderId,
               file_url AS fileUrl,
               file_name AS fileName,
               file_type AS fileType,
               mime_type AS mimeType,
               ocr_text AS ocrText,
               created_at AS createdAt
        FROM repair_attachment
        WHERE work_order_id=%s
        ORDER BY id ASC
        """,
        (int(order_id),),
    )
    data = []
    for row in rows or []:
        data.append(
            {
                "id": int(row.get("id") or 0),
                "workOrderId": int(row.get("workOrderId") or 0),
                "fileUrl": str(row.get("fileUrl") or "").strip(),
                "fileName": str(row.get("fileName") or "").strip(),
                "fileType": str(row.get("fileType") or "").strip() or "image",
                "mimeType": str(row.get("mimeType") or "").strip(),
                "ocrText": str(row.get("ocrText") or "").strip(),
                "createdAt": _to_text_time(row.get("createdAt")),
            }
        )
    return data


def _save_repair_attachments(order_id, attachments):
    rows = _normalize_repair_attachments_payload(attachments)
    if not rows:
        return []
    saved = []
    for item in rows:
        new_id = execute_insert(
            """
            INSERT INTO repair_attachment (work_order_id, file_url, file_name, file_type, mime_type, ocr_text, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                int(order_id),
                item.get("url"),
                item.get("name"),
                item.get("fileType"),
                item.get("mimeType"),
                item.get("ocrText"),
                _now_text(),
            ),
        )
        saved.append({**item, "id": int(new_id or 0)})
    return saved


def _build_repair_history_context(equipment_id=None, lab_id=None, limit=4):
    if equipment_id:
        rows = query(
            """
            SELECT issue_type AS issueType,
                   description,
                   status,
                   submitted_at AS createdAt
            FROM repair_work_order
            WHERE equipment_id=%s
            ORDER BY id DESC
            LIMIT %s
            """,
            (int(equipment_id), int(limit)),
        )
    elif lab_id:
        rows = query(
            """
            SELECT issue_type AS issueType,
                   description,
                   status,
                   submitted_at AS createdAt
            FROM repair_work_order
            WHERE lab_id=%s
            ORDER BY id DESC
            LIMIT %s
            """,
            (int(lab_id), int(limit)),
        )
    else:
        rows = []
    result = []
    for row in rows or []:
        result.append(
            {
                "issueType": str(row.get("issueType") or "").strip(),
                "description": str(row.get("description") or "").strip()[:180],
                "status": str(row.get("status") or "").strip(),
                "createdAt": _to_text_time(row.get("createdAt")),
            }
        )
    return result


def _log_repair_ai_diagnosis(work_order_id=None, equipment_id=None, lab_id=None, user_id=None, input_text="", attachments=None, ai_payload=None, fallback=False):
    payload = ai_payload if isinstance(ai_payload, dict) else {}
    return execute_insert(
        """
        INSERT INTO repair_ai_diagnosis_log (
            work_order_id, equipment_id, lab_id, user_id, input_text, attachment_json,
            issue_type, fault_part, priority, summary, possible_causes_json, suggestions_json,
            ocr_summary, confidence, model_name, result_json, fallback_flag, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            _to_int_or_none(work_order_id),
            _to_int_or_none(equipment_id),
            _to_int_or_none(lab_id),
            _to_int_or_none(user_id),
            str(input_text or "").strip()[:5000],
            _json_dumps_safe(attachments or []),
            str(payload.get("issueType") or "other").strip(),
            str(payload.get("faultPart") or "").strip()[:100],
            str(payload.get("priority") or "P2").strip(),
            str(payload.get("summary") or "").strip()[:500],
            _json_dumps_safe(payload.get("possibleCauses") or []),
            _json_dumps_safe(payload.get("suggestions") or []),
            str(payload.get("ocrSummary") or "").strip()[:500],
            float(payload.get("confidence") or 0),
            str(payload.get("modelName") or "").strip()[:120],
            str(payload.get("rawJson") or "").strip()[:20000],
            1 if fallback else 0,
            _now_text(),
        ),
    )


def _resolve_lab_name(lab_id):
    if lab_id is None:
        return ""
    rows = query("SELECT id, name FROM lab WHERE id=%s LIMIT 1", (lab_id,))
    if not rows:
        return ""
    return str(rows[0].get("name") or "").strip()


def _create_repair_order_record(
    *,
    submitter_id,
    submitter_name,
    equipment_id,
    asset_code,
    equipment_name,
    lab_id,
    lab_name,
    issue_type,
    description,
    attachment_url,
    ai_issue_type=None,
    ai_fault_part=None,
    ai_priority=None,
    ai_summary=None,
    ai_possible_causes_text=None,
    ai_suggestions_text=None,
    ai_confidence=None,
    ai_ocr_text=None,
    ai_model_name=None,
    ai_raw_json=None,
):
    ai_issue_type_text = str(ai_issue_type or "").strip().lower()[:32] or None
    ai_fault_part_text = str(ai_fault_part or "").strip()[:100] or None
    ai_priority_text = str(ai_priority or "").strip().upper()[:8] or None
    ai_summary_text = str(ai_summary or "").strip()[:500] or None
    ai_possible_causes_safe = str(ai_possible_causes_text or "").strip()
    if len(ai_possible_causes_safe) > 20000:
        ai_possible_causes_safe = ai_possible_causes_safe[:20000]
    ai_suggestions_safe = str(ai_suggestions_text or "").strip()
    if len(ai_suggestions_safe) > 20000:
        ai_suggestions_safe = ai_suggestions_safe[:20000]
    ai_ocr_text_safe = str(ai_ocr_text or "").strip()
    if len(ai_ocr_text_safe) > 20000:
        ai_ocr_text_safe = ai_ocr_text_safe[:20000]
    ai_model_name_text = str(ai_model_name or "").strip()[:120] or None
    ai_raw_json_safe = str(ai_raw_json or "").strip()
    if len(ai_raw_json_safe) > 20000:
        ai_raw_json_safe = ai_raw_json_safe[:20000]
    ai_confidence_value = None
    if ai_confidence not in (None, ""):
        try:
            ai_confidence_value = round(float(ai_confidence), 4)
        except Exception:
            ai_confidence_value = None
        if ai_confidence_value is not None:
            if ai_confidence_value < 0:
                ai_confidence_value = 0.0
            if ai_confidence_value > 1:
                ai_confidence_value = 1.0

    now_text = _now_text()
    new_id = execute_insert(
        """
        INSERT INTO repair_work_order (
            order_no, equipment_id, asset_code, equipment_name, lab_id, lab_name,
            issue_type, description, attachment_url,
            ai_issue_type, ai_fault_part, ai_priority, ai_summary, ai_possible_causes, ai_suggestions, ai_confidence, ai_ocr_text, ai_model_name, ai_raw_json,
            status,
            submitter_id, submitter_name, assignee_id, assignee_name,
            submitted_at, accepted_at, processing_at, completed_at,
            followup_score, followup_comment, followup_at, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            'submitted',
            %s, %s, NULL, '',
            %s, NULL, NULL, NULL,
            NULL, '', NULL, %s, %s
        )
        """,
        (
            _build_repair_order_no(),
            equipment_id,
            str(asset_code or "").strip(),
            str(equipment_name or "").strip(),
            lab_id,
            str(lab_name or "").strip(),
            issue_type,
            description,
            attachment_url,
            ai_issue_type_text,
            ai_fault_part_text,
            ai_priority_text,
            ai_summary_text,
            ai_possible_causes_safe,
            ai_suggestions_safe,
            ai_confidence_value,
            ai_ocr_text_safe,
            ai_model_name_text,
            ai_raw_json_safe,
            submitter_id,
            str(submitter_name or "").strip(),
            now_text,
            now_text,
            now_text,
        ),
    )
    return int(new_id)


def _normalize_ai_triage_payload(ai_result, fallback_issue_type="other"):
    source = ai_result if isinstance(ai_result, dict) else {}
    issue_type = str(source.get("issueType") or "").strip().lower()
    if issue_type not in REPAIR_ISSUE_TYPE_SET:
        issue_type = str(fallback_issue_type or "").strip().lower()
    if issue_type not in REPAIR_ISSUE_TYPE_SET:
        issue_type = "other"

    priority = str(source.get("priority") or "").strip().upper()
    if priority not in {"P0", "P1", "P2"}:
        priority = "P2"

    fault_part = str(source.get("faultPart") or "").strip()[:100]
    summary = str(source.get("summary") or "").strip()[:500]
    possible_causes = _decode_ai_suggestions(source.get("possibleCauses"))
    suggestions = _decode_ai_suggestions(source.get("suggestions"))
    if len(suggestions) > 5:
        suggestions = suggestions[:5]
    possible_causes_text = json.dumps(possible_causes[:4], ensure_ascii=False, separators=(",", ":"))
    if len(possible_causes_text) > 20000:
        possible_causes_text = possible_causes_text[:20000]
    suggestions_text = json.dumps(suggestions, ensure_ascii=False, separators=(",", ":"))
    if len(suggestions_text) > 20000:
        suggestions_text = suggestions_text[:20000]

    try:
        confidence = round(float(source.get("confidence") or 0), 4)
    except Exception:
        confidence = 0.0
    if confidence < 0:
        confidence = 0.0
    if confidence > 1:
        confidence = 1.0

    raw_json = str(source.get("rawJson") or "").strip()
    if not raw_json:
        raw_json = json.dumps(
            {
                "issueType": issue_type,
                "faultPart": fault_part,
                "priority": priority,
                "summary": summary,
                "possibleCauses": possible_causes,
                "suggestions": suggestions,
                "ocrSummary": str(source.get("ocrSummary") or "").strip(),
                "confidence": confidence,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    if len(raw_json) > 20000:
        raw_json = raw_json[:20000]

    return {
        "issueType": issue_type,
        "faultPart": fault_part,
        "priority": priority,
        "summary": summary,
        "possibleCauses": possible_causes,
        "possibleCausesText": possible_causes_text,
        "suggestions": suggestions,
        "suggestionsText": suggestions_text,
        "confidence": confidence,
        "ocrSummary": str(source.get("ocrSummary") or "").strip()[:500],
        "modelName": str(source.get("modelName") or "").strip()[:120],
        "rawJson": raw_json,
    }


def _parse_page_and_size(page_raw, page_size_raw, default_page=1, default_page_size=20):
    try:
        page = int(str(page_raw or default_page).strip())
    except (TypeError, ValueError):
        page = int(default_page)
    try:
        page_size = int(str(page_size_raw or default_page_size).strip())
    except (TypeError, ValueError):
        page_size = int(default_page_size)
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    return page, page_size, (page - 1) * page_size


def _normalize_status(raw_status):
    status = str(raw_status or "").strip() or "in_service"
    if status not in EQUIPMENT_STATUS_SET:
        raise BizError("invalid status", 400)
    return status


def _normalize_purchase_date(raw_date, field_name="purchaseDate"):
    text = str(raw_date or "").strip()
    if not text:
        return None
    date_dt = _parse_date_yyyy_mm_dd(text)
    if not date_dt:
        raise BizError(f"invalid {field_name}", 400)
    return date_dt.strftime("%Y-%m-%d")


def _normalize_price(raw_price, field_name="price"):
    if raw_price in (None, ""):
        return None
    text = str(raw_price).strip()
    if not text:
        return None
    try:
        return round(float(text), 2)
    except (TypeError, ValueError):
        raise BizError(f"invalid {field_name}", 400)


def _normalize_spec_json(raw_spec):
    if raw_spec in (None, ""):
        return None
    if isinstance(raw_spec, (dict, list)):
        return json.dumps(raw_spec, ensure_ascii=False, separators=(",", ":"))
    text = str(raw_spec).strip()
    return text or None


def _looks_like_pc_equipment(asset_code="", name="", spec_json=None):
    asset = str(asset_code or "").strip().upper()
    name_text = str(name or "").strip()
    if asset.startswith("PC-"):
        return True
    if "电脑" in name_text:
        return True
    if re.search(r"\bpc\b", name_text, flags=re.IGNORECASE):
        return True

    spec_map = _parse_equipment_spec_map(spec_json)
    category = str(spec_map.get("category") or "").strip().lower()
    return category in {"pc", "computer"}


def _is_lab_pc_equipment(asset_code="", name="", spec_json=None, lab_id=None, lab_name=""):
    lab_id_int = _to_int_or_none(lab_id)
    has_lab = (lab_id_int is not None and int(lab_id_int) > 0) or bool(str(lab_name or "").strip())
    if not has_lab:
        return False
    return _looks_like_pc_equipment(asset_code=asset_code, name=name, spec_json=spec_json)


def _resolve_allow_borrow_flag(payload, existing_allow_borrow=None):
    data = payload or {}
    allow_borrow = data.get("allowBorrow")
    if allow_borrow is not None:
        return bool(allow_borrow)
    if isinstance(existing_allow_borrow, bool):
        return existing_allow_borrow
    return not _is_lab_pc_equipment(
        asset_code=data.get("assetCode"),
        name=data.get("name"),
        spec_json=data.get("specJson"),
        lab_id=data.get("labId"),
        lab_name=data.get("labName"),
    )


def _normalize_equipment_payload(data):
    payload = data or {}
    asset_code = str(payload.get("assetCode") or "").strip()
    name = str(payload.get("name") or "").strip()
    if not asset_code:
        raise BizError("assetCode required", 400)
    if not name:
        raise BizError("name required", 400)

    lab_id = _to_int_or_none(payload.get("labId"))
    if payload.get("labId") not in (None, "") and lab_id is None:
        raise BizError("invalid labId", 400)
    allow_borrow = _parse_optional_bool(payload.get("allowBorrow"), "allowBorrow")

    return {
        "assetCode": asset_code,
        "name": name,
        "model": str(payload.get("model") or "").strip(),
        "brand": str(payload.get("brand") or "").strip(),
        "labId": lab_id,
        "labName": str(payload.get("labName") or "").strip(),
        "status": _normalize_status(payload.get("status")),
        "keeper": str(payload.get("keeper") or "").strip(),
        "purchaseDate": _normalize_purchase_date(payload.get("purchaseDate"), field_name="purchaseDate"),
        "price": _normalize_price(payload.get("price"), field_name="price"),
        "specJson": _normalize_spec_json(payload.get("specJson")),
        "imageUrl": str(payload.get("imageUrl") or "").strip(),
        "allowBorrow": allow_borrow,
    }


def _format_equipment_row(row):
    row = dict(row or {})
    row["createdAt"] = _to_text_time(row.get("createdAt"))
    row["updatedAt"] = _to_text_time(row.get("updatedAt"))
    row["purchaseDate"] = str(row.get("purchaseDate") or "")
    row["warrantyUntil"] = str(row.get("warrantyUntil") or "")
    row["borrowedAt"] = _to_text_time(row.get("borrowedAt"))
    row["expectedReturnAt"] = _to_text_time(row.get("expectedReturnAt"))
    row["lastReturnedAt"] = _to_text_time(row.get("lastReturnedAt"))
    row["lastTransferAt"] = _to_text_time(row.get("lastTransferAt"))
    row["nextMaintenanceAt"] = _to_text_time(row.get("nextMaintenanceAt"))
    row["lastMaintainedAt"] = _to_text_time(row.get("lastMaintainedAt"))
    row["scrappedAt"] = _to_text_time(row.get("scrappedAt"))
    row["isBorrowed"] = int(row.get("isBorrowed") or 0) == 1
    allow_raw = row.get("allowBorrow")
    if allow_raw in (None, ""):
        allow_raw = 1
    row["allowBorrow"] = int(allow_raw or 0) == 1

    maintenance_due = False
    warranty_expired = False
    now_dt = datetime.now()
    next_maint_raw = row.get("nextMaintenanceAt")
    if next_maint_raw:
        dt = _to_datetime(next_maint_raw)
        if dt != datetime.min and dt <= now_dt:
            maintenance_due = True
    warranty_raw = str(row.get("warrantyUntil") or "").strip()
    if warranty_raw:
        warranty_dt = _parse_date_yyyy_mm_dd(warranty_raw)
        if warranty_dt and warranty_dt.date() < now_dt.date():
            warranty_expired = True

    row["maintenanceDue"] = maintenance_due
    row["warrantyExpired"] = warranty_expired
    return row


def _borrow_request_is_overdue(row, now_dt=None):
    data = row or {}
    now_val = now_dt if isinstance(now_dt, datetime) else datetime.now()
    status = str(data.get("status") or "").strip().lower()
    if status != "approved":
        return False
    if str(data.get("returnedAt") or "").strip():
        return False
    expected_dt = _to_datetime(data.get("expectedReturnAt"))
    if expected_dt == datetime.min:
        return False
    return expected_dt < now_val


def _format_borrow_request_row(row):
    out = dict(row or {})
    out["createdAt"] = _to_text_time(out.get("createdAt"))
    out["updatedAt"] = _to_text_time(out.get("updatedAt"))
    out["borrowStartAt"] = _to_text_time(out.get("borrowStartAt"))
    out["expectedReturnAt"] = _to_text_time(out.get("expectedReturnAt"))
    out["lastRemindAt"] = _to_text_time(out.get("lastRemindAt"))
    out["approvedAt"] = _to_text_time(out.get("approvedAt"))
    out["returnedAt"] = _to_text_time(out.get("returnedAt"))
    out["remindCount"] = int(out.get("remindCount") or 0)
    out["riskFlag"] = int(out.get("riskFlag") or 0) == 1
    now_dt = datetime.now()
    out["isOverdue"] = _borrow_request_is_overdue(out, now_dt=now_dt)

    expected_dt = _to_datetime(out.get("expectedReturnAt"))
    if expected_dt == datetime.min:
        out["daysToReturn"] = None
    else:
        out["daysToReturn"] = int((expected_dt.date() - now_dt.date()).days)
    return out


def _borrow_overdue_history_count(user_name):
    owner = str(user_name or "").strip()
    if not owner:
        return 0
    rows = query(
        """
        SELECT COUNT(*) AS cnt
        FROM equipment_borrow_request
        WHERE applicant_user_name=%s
          AND (
              (status='approved' AND returned_at IS NULL AND expected_return_at IS NOT NULL AND expected_return_at < NOW())
              OR
              (status='returned' AND returned_at IS NOT NULL AND expected_return_at IS NOT NULL AND returned_at > expected_return_at)
          )
        """,
        (owner,),
    )
    return int((rows[0] or {}).get("cnt") or 0) if rows else 0


def _resolve_user_id_by_username_with_cur(cur, user_name):
    owner = str(user_name or "").strip()
    if not owner:
        return None
    cur.execute("SELECT id FROM user WHERE username=%s LIMIT 1", (owner,))
    row = cur.fetchone() or {}
    user_id = _to_int_or_none(row.get("id"))
    return int(user_id) if user_id is not None and int(user_id) > 0 else None


def _record_borrow_reminder_with_cur(cur, request_id, remind_type, remind_date_text, reminded_by, message):
    if remind_type not in BORROW_REMIND_TYPE_SET:
        raise BizError("invalid remindType", 400)
    remind_date = str(remind_date_text or "").strip()
    if not remind_date:
        raise BizError("remindDate required", 400)
    if not _parse_date_yyyy_mm_dd(remind_date):
        raise BizError("invalid remindDate", 400)
    now_text = _now_text()
    cur.execute(
        """
        INSERT INTO equipment_borrow_reminder_log (request_id, remind_type, remind_date, reminded_by, message, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            reminded_by=VALUES(reminded_by),
            message=VALUES(message),
            created_at=VALUES(created_at)
        """,
        (
            int(request_id),
            remind_type,
            remind_date,
            str(reminded_by or "").strip()[:64],
            str(message or "").strip()[:255],
            now_text,
        ),
    )


def borrow_ensure_auto_reminders(user_name="", include_all=False):
    owner = str(user_name or "").strip()
    if not include_all and not owner:
        return 0

    now_dt = datetime.now()
    today_text = now_dt.strftime("%Y-%m-%d")
    end_day_text = (now_dt + timedelta(days=7)).strftime("%Y-%m-%d")
    where_sql = """
        WHERE r.status='approved'
          AND r.returned_at IS NULL
          AND r.expected_return_at IS NOT NULL
          AND DATE(r.expected_return_at) >= %s
          AND DATE(r.expected_return_at) <= %s
    """
    params = [today_text, end_day_text]
    if not include_all:
        where_sql += " AND r.applicant_user_name=%s"
        params.append(owner)

    rows = query(
        """
        SELECT r.id,
               r.applicant_user_name AS applicantUserName,
               r.equipment_name AS equipmentName,
               r.equipment_asset_code AS equipmentAssetCode,
               r.expected_return_at AS expectedReturnAt
        FROM equipment_borrow_request r
        """
        + where_sql
        + " ORDER BY r.id DESC LIMIT 500",
        tuple(params),
    )

    inserted = 0
    for row in rows or []:
        request_id = int(row.get("id") or 0)
        if request_id <= 0:
            continue
        expected_dt = _to_datetime(row.get("expectedReturnAt"))
        if expected_dt == datetime.min:
            continue
        days_left = int((expected_dt.date() - now_dt.date()).days)
        if days_left < 0 or days_left > 7:
            continue
        target = str(row.get("equipmentName") or "").strip() or str(row.get("equipmentAssetCode") or "").strip() or "设备"
        message = f"{target} 将在 {days_left} 天后到期，请记得归还。"
        existed = query(
            """
            SELECT id
            FROM equipment_borrow_reminder_log
            WHERE request_id=%s AND remind_type='auto' AND remind_date=%s
            LIMIT 1
            """,
            (request_id, today_text),
        )
        if existed:
            continue
        execute_insert(
            """
            INSERT INTO equipment_borrow_reminder_log (request_id, remind_type, remind_date, reminded_by, message, created_at)
            VALUES (%s, 'auto', %s, 'system', %s, %s)
            """,
            (request_id, today_text, message[:255], _now_text()),
        )
        inserted += 1
    return inserted


def _borrow_request_select_fragment():
    return """
        SELECT r.id,
               r.equipment_id AS equipmentId,
               r.equipment_asset_code AS equipmentAssetCode,
               r.equipment_name AS equipmentName,
               r.equipment_lab_name AS equipmentLabName,
               r.applicant_user_name AS applicantUserName,
               r.applicant_role AS applicantRole,
               r.applicant_name AS applicantName,
               r.applicant_student_no AS applicantStudentNo,
               r.applicant_class_name AS applicantClassName,
               r.applicant_job_no AS applicantJobNo,
               r.borrow_start_at AS borrowStartAt,
               r.expected_return_at AS expectedReturnAt,
               r.purpose,
               r.status,
               r.reject_reason AS rejectReason,
               r.admin_note AS adminNote,
               r.remind_count AS remindCount,
               r.last_remind_at AS lastRemindAt,
               r.approved_by AS approvedBy,
               r.approved_at AS approvedAt,
               r.returned_by AS returnedBy,
               r.returned_at AS returnedAt,
               r.risk_flag AS riskFlag,
               r.risk_reason AS riskReason,
               r.created_at AS createdAt,
               r.updated_at AS updatedAt
        FROM equipment_borrow_request r
    """


def _build_borrow_ai_remind_message(row):
    item = row or {}
    target = str(item.get("equipmentName") or "").strip() or str(item.get("equipmentAssetCode") or "").strip() or "设备"
    expected_dt = _to_datetime(item.get("expectedReturnAt"))
    if expected_dt == datetime.min:
        return f"{target} 借用记录需要尽快确认归还时间，请及时处理。"
    now_dt = datetime.now()
    days = int((expected_dt.date() - now_dt.date()).days)
    if days < 0:
        return f"{target} 已逾期 {abs(days)} 天，请立即联系管理员完成归还登记。"
    if days == 0:
        return f"{target} 将于今天到期，请在结束使用后尽快归还并完成登记。"
    return f"{target} 还剩 {days} 天到期，请提前安排归还或提交续借申请。"


def _mark_borrow_request_returned_with_cur(cur, bid, actor, note="", return_channel="manual", scan_token=""):
    actor_name = str((actor or {}).get("username") or "").strip()
    now_text = _now_text()
    cur.execute(
        """
        SELECT id,
               equipment_id AS equipmentId,
               equipment_name AS equipmentName,
               equipment_asset_code AS equipmentAssetCode,
               expected_return_at AS expectedReturnAt,
               status
        FROM equipment_borrow_request
        WHERE id=%s
        LIMIT 1
        FOR UPDATE
        """,
        (int(bid),),
    )
    req = cur.fetchone()
    if not req:
        raise BizError("borrow request not found", 404)
    if str(req.get("status") or "").strip() != "approved":
        raise BizError("only approved request can be marked returned", 409)

    equipment_id = int(req.get("equipmentId") or 0)
    if equipment_id <= 0:
        raise BizError("invalid equipment", 409)
    cur.execute(
        """
        SELECT id
        FROM equipment
        WHERE id=%s
        LIMIT 1
        FOR UPDATE
        """,
        (equipment_id,),
    )
    eq = cur.fetchone()
    if not eq:
        raise BizError("equipment not found", 404)

    cur.execute(
        """
        UPDATE equipment
        SET is_borrowed=0,
            borrowed_by_id=NULL,
            borrowed_by='',
            borrowed_at=NULL,
            expected_return_at=NULL,
            last_returned_at=%s,
            updated_at=%s
        WHERE id=%s
        """,
        (now_text, now_text, equipment_id),
    )
    cur.execute(
        """
        UPDATE equipment_borrow_request
        SET status='returned',
            returned_by=%s,
            returned_at=%s,
            updated_at=%s
        WHERE id=%s
        """,
        (actor_name, now_text, now_text, int(bid)),
    )
    cur.execute(
        """
        INSERT INTO borrow_return_log (
            request_id, equipment_id, operator_name, operator_role, return_channel, scan_token, note, returned_at, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            int(bid),
            equipment_id,
            actor_name,
            str((actor or {}).get("role") or "").strip(),
            str(return_channel or "manual"),
            str(scan_token or "").strip()[:128],
            str(note or "").strip()[:255],
            now_text,
            now_text,
        ),
    )

    event_note = f"borrow request returned, requestId={int(bid)}, channel={return_channel}"
    if note:
        event_note += f"; note={note}"
    _insert_equipment_event_with_cur(
        cur,
        equipment_id=equipment_id,
        event_type="return",
        note=event_note,
        operator=actor,
        created_at=now_text,
    )

    expected_dt = _to_datetime(req.get("expectedReturnAt"))
    returned_dt = _to_datetime(now_text)
    returned_late = bool(expected_dt != datetime.min and returned_dt != datetime.min and returned_dt > expected_dt)
    return {"returnedLate": returned_late, "equipmentId": equipment_id}


def _parse_equipment_spec_map(raw_spec):
    if isinstance(raw_spec, dict):
        return dict(raw_spec)
    text = str(raw_spec or "").strip()
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except Exception:
        return {}
    if isinstance(obj, dict):
        return obj
    return {}


def _normalize_pc_seat_code(raw_seat):
    text = re.sub(r"\s+", "", str(raw_seat or "").strip().upper())
    if not text:
        return ""
    m = re.fullmatch(r"([A-Z]{1,3})(\d{1,3})", text)
    if not m:
        return ""
    return f"{m.group(1)}{int(m.group(2))}"


def _pc_runtime_status(equipment_status):
    status = str(equipment_status or "").strip().lower()
    if status == "scrapped":
        return "offline"
    if status == "repairing":
        return "warning"
    return "online"


def _find_equipment_or_raise(eid):
    rows = query(
        """
        SELECT id,
               asset_code AS assetCode,
               name,
               model,
               brand,
               lab_id AS labId,
               lab_name AS labName,
               status,
               keeper,
               purchase_date AS purchaseDate,
               price,
               spec_json AS specJson,
               image_url AS imageUrl,
               allow_borrow AS allowBorrow,
               is_borrowed AS isBorrowed,
               borrowed_by_id AS borrowedById,
               borrowed_by AS borrowedBy,
               borrowed_at AS borrowedAt,
               expected_return_at AS expectedReturnAt,
               last_returned_at AS lastReturnedAt,
               last_transfer_from_lab_id AS lastTransferFromLabId,
               last_transfer_from_lab_name AS lastTransferFromLabName,
               last_transfer_at AS lastTransferAt,
               next_maintenance_at AS nextMaintenanceAt,
               last_maintained_at AS lastMaintainedAt,
               maintenance_cycle_days AS maintenanceCycleDays,
               maintenance_note AS maintenanceNote,
               warranty_until AS warrantyUntil,
               qr_token AS qrToken,
               barcode_value AS barcodeValue,
               location_note AS locationNote,
               scrap_reason AS scrapReason,
               scrapped_at AS scrappedAt,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM equipment
        WHERE id=%s
        LIMIT 1
        """,
        (eid,),
    )
    if not rows:
        raise BizError("equipment not found", 404)
    return _format_equipment_row(rows[0])


@app.get("/equipments")
@auth_required()
def list_equipments():
    keyword = str(request.args.get("keyword") or "").strip()
    status = str(request.args.get("status") or "").strip()
    lab_id_raw = request.args.get("labId", "")
    lab_id = _to_int_or_none(lab_id_raw)
    if lab_id_raw not in (None, "") and lab_id is None:
        raise BizError("invalid labId", 400)
    if status and status not in EQUIPMENT_STATUS_SET:
        raise BizError("invalid status", 400)
    is_borrowed = _parse_optional_bool(request.args.get("isBorrowed"), "isBorrowed")
    allow_borrow_filter = _parse_optional_bool(request.args.get("allowBorrow"), "allowBorrow")
    borrowable_filter = _parse_optional_bool(request.args.get("borrowable"), "borrowable")
    if allow_borrow_filter is not None and borrowable_filter is not None and allow_borrow_filter != borrowable_filter:
        raise BizError("conflicting allowBorrow and borrowable", 400)
    if allow_borrow_filter is None:
        allow_borrow_filter = borrowable_filter

    maintenance_due_days_raw = request.args.get("maintenanceDueDays", "")
    maintenance_due_days = _to_int_or_none(maintenance_due_days_raw) if maintenance_due_days_raw not in (None, "") else None
    if maintenance_due_days_raw not in (None, "") and maintenance_due_days is None:
        raise BizError("invalid maintenanceDueDays", 400)
    if maintenance_due_days is not None and maintenance_due_days < 0:
        raise BizError("invalid maintenanceDueDays", 400)

    warranty_due_days_raw = request.args.get("warrantyDueDays", "")
    warranty_due_days = _to_int_or_none(warranty_due_days_raw) if warranty_due_days_raw not in (None, "") else None
    if warranty_due_days_raw not in (None, "") and warranty_due_days is None:
        raise BizError("invalid warrantyDueDays", 400)
    if warranty_due_days is not None and warranty_due_days < 0:
        raise BizError("invalid warrantyDueDays", 400)

    lifecycle = str(request.args.get("lifecycle") or "").strip().lower()
    if lifecycle and lifecycle not in {"borrowed", "maintenance_due", "warranty_due", "scrapped"}:
        raise BizError("invalid lifecycle", 400)

    page, page_size, offset = _parse_page_and_size(
        request.args.get("page", "1"),
        request.args.get("pageSize", "20"),
    )

    where_sql = " WHERE 1=1"
    params = []
    if keyword:
        where_sql += " AND (asset_code LIKE %s OR name LIKE %s OR lab_name LIKE %s OR borrowed_by LIKE %s OR barcode_value LIKE %s)"
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw, kw, kw])
    if lab_id is not None:
        where_sql += " AND lab_id=%s"
        params.append(lab_id)
    if status:
        where_sql += " AND status=%s"
        params.append(status)
    if is_borrowed is not None:
        where_sql += " AND is_borrowed=%s"
        params.append(1 if is_borrowed else 0)
    if allow_borrow_filter is not None:
        where_sql += " AND allow_borrow=%s"
        params.append(1 if allow_borrow_filter else 0)

    now_dt = datetime.now()
    if lifecycle == "borrowed":
        where_sql += " AND is_borrowed=1"
    elif lifecycle == "maintenance_due":
        where_sql += " AND next_maintenance_at IS NOT NULL AND next_maintenance_at<=%s"
        params.append(now_dt.strftime("%Y-%m-%d %H:%M:%S"))
    elif lifecycle == "warranty_due":
        where_sql += " AND warranty_until IS NOT NULL AND warranty_until<=%s"
        params.append(now_dt.strftime("%Y-%m-%d"))
    elif lifecycle == "scrapped":
        where_sql += " AND status='scrapped'"

    if maintenance_due_days is not None:
        deadline = now_dt + timedelta(days=int(maintenance_due_days))
        where_sql += " AND next_maintenance_at IS NOT NULL AND next_maintenance_at<=%s"
        params.append(deadline.strftime("%Y-%m-%d %H:%M:%S"))

    if warranty_due_days is not None:
        deadline = (now_dt + timedelta(days=int(warranty_due_days))).strftime("%Y-%m-%d")
        where_sql += " AND warranty_until IS NOT NULL AND warranty_until<=%s"
        params.append(deadline)

    total_rows = query("SELECT COUNT(*) AS cnt FROM equipment" + where_sql, params)
    total = int((total_rows[0] or {}).get("cnt") or 0) if total_rows else 0

    list_sql = (
        """
        SELECT id,
               asset_code AS assetCode,
               name,
               model,
               brand,
               lab_id AS labId,
               lab_name AS labName,
               status,
               keeper,
               purchase_date AS purchaseDate,
               price,
               spec_json AS specJson,
               image_url AS imageUrl,
               allow_borrow AS allowBorrow,
               is_borrowed AS isBorrowed,
               borrowed_by_id AS borrowedById,
               borrowed_by AS borrowedBy,
               borrowed_at AS borrowedAt,
               expected_return_at AS expectedReturnAt,
               last_returned_at AS lastReturnedAt,
               last_transfer_from_lab_id AS lastTransferFromLabId,
               last_transfer_from_lab_name AS lastTransferFromLabName,
               last_transfer_at AS lastTransferAt,
               next_maintenance_at AS nextMaintenanceAt,
               last_maintained_at AS lastMaintainedAt,
               maintenance_cycle_days AS maintenanceCycleDays,
               maintenance_note AS maintenanceNote,
               warranty_until AS warrantyUntil,
               qr_token AS qrToken,
               barcode_value AS barcodeValue,
               location_note AS locationNote,
               scrap_reason AS scrapReason,
               scrapped_at AS scrappedAt,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM equipment
        """
        + where_sql
        + " ORDER BY id DESC LIMIT %s OFFSET %s"
    )
    rows = query(list_sql, list(params) + [page_size, offset])
    data = [_format_equipment_row(row) for row in rows]
    return jsonify(
        {
            "ok": True,
            "data": data,
            "meta": {
                "page": page,
                "pageSize": page_size,
                "total": total,
            },
        }
    )


@app.get("/equipments/<int:eid>")
@auth_required()
def get_equipment(eid):
    return jsonify({"ok": True, "data": _find_equipment_or_raise(eid)})


@app.get("/borrow-requests")
@auth_required()
def list_borrow_requests():
    current_user = g.current_user or {}
    current_user_name = str(current_user.get("username") or "").strip()
    current_role = str(current_user.get("role") or "").strip().lower()
    is_admin = current_role == "admin"

    status_raw = str(request.args.get("status") or "").strip().lower()
    mine_raw = str(request.args.get("mine") or "").strip().lower()
    user_keyword = str(request.args.get("userKeyword") or "").strip()
    equipment_keyword = str(request.args.get("equipmentKeyword") or "").strip()
    applicant_role = str(request.args.get("applicantRole") or "").strip().lower()
    risk_only_raw = str(request.args.get("riskOnly") or "").strip().lower()
    user_filter = str(request.args.get("user") or "").strip()

    if applicant_role and applicant_role not in {"student", "teacher", "admin"}:
        raise BizError("invalid applicantRole", 400)

    mine = mine_raw in {"1", "true", "yes", "on"}
    if not is_admin:
        mine = True
        if user_keyword:
            raise BizError("forbidden", 403)
        if user_filter and user_filter != current_user_name:
            raise BizError("forbidden", 403)

    risk_only = risk_only_raw in {"1", "true", "yes", "on"}
    page, page_size, offset = _parse_page_and_size(request.args.get("page", "1"), request.args.get("pageSize", "20"))

    where_sql = " WHERE 1=1"
    params = []
    now_text = _now_text()

    if mine and current_user_name:
        where_sql += " AND r.applicant_user_name=%s"
        params.append(current_user_name)
    elif user_filter:
        where_sql += " AND r.applicant_user_name=%s"
        params.append(user_filter)
    elif user_keyword:
        where_sql += " AND (r.applicant_user_name LIKE %s OR r.applicant_name LIKE %s)"
        like_kw = f"%{user_keyword}%"
        params.extend([like_kw, like_kw])

    if equipment_keyword:
        where_sql += " AND (r.equipment_asset_code LIKE %s OR r.equipment_name LIKE %s OR r.equipment_lab_name LIKE %s)"
        like_eq = f"%{equipment_keyword}%"
        params.extend([like_eq, like_eq, like_eq])

    if applicant_role:
        where_sql += " AND r.applicant_role=%s"
        params.append(applicant_role)

    if risk_only:
        where_sql += " AND r.risk_flag=1"

    if status_raw:
        if status_raw == "overdue":
            where_sql += " AND r.status='approved' AND r.returned_at IS NULL AND r.expected_return_at < %s"
            params.append(now_text)
        else:
            parts = [x.strip() for x in status_raw.split(",") if x.strip()]
            for part in parts:
                if part not in BORROW_REQUEST_STATUS_SET:
                    raise BizError("invalid status", 400)
            if parts:
                where_sql += " AND r.status IN (" + ",".join(["%s"] * len(parts)) + ")"
                params.extend(parts)

    count_rows = query("SELECT COUNT(*) AS cnt FROM equipment_borrow_request r" + where_sql, tuple(params))
    total = int((count_rows[0] or {}).get("cnt") or 0) if count_rows else 0

    list_sql = _borrow_request_select_fragment() + where_sql + " ORDER BY r.id DESC LIMIT %s OFFSET %s"
    rows = query(list_sql, tuple(list(params) + [page_size, offset]))
    data = [_format_borrow_request_row(x) for x in rows]
    return jsonify(
        {
            "ok": True,
            "data": data,
            "meta": {
                "page": int(page),
                "pageSize": int(page_size),
                "total": int(total),
                "hasMore": (offset + len(data)) < total,
            },
        }
    )


@app.get("/borrow-requests/<int:bid>")
@auth_required()
def get_borrow_request_detail(bid):
    rows = query(_borrow_request_select_fragment() + " WHERE r.id=%s LIMIT 1", (int(bid),))
    if not rows:
        raise BizError("borrow request not found", 404)
    row = _format_borrow_request_row(rows[0])
    current_user = g.current_user or {}
    current_role = str(current_user.get("role") or "").strip().lower()
    current_user_name = str(current_user.get("username") or "").strip()
    if current_role != "admin" and current_user_name != str(row.get("applicantUserName") or "").strip():
        raise BizError("forbidden", 403)
    return jsonify({"ok": True, "data": row})


@app.post("/borrow-requests")
@auth_required()
def create_borrow_request():
    payload = request.get_json(force=True) or {}
    current_user = g.current_user or {}
    applicant_user_name = str(current_user.get("username") or "").strip()
    applicant_role = str(current_user.get("role") or "").strip().lower()
    if not applicant_user_name:
        raise BizError("unauthorized", 401)

    equipment_id = _to_int_or_none(payload.get("equipmentId"))
    if equipment_id is None or int(equipment_id) <= 0:
        raise BizError("equipmentId required", 400)
    applicant_name = _normalize_text(payload.get("applicantName"), "applicantName", 64)
    if not applicant_name:
        raise BizError("applicantName required", 400)
    borrow_start_at = _normalize_datetime_text(payload.get("borrowStartAt"), "borrowStartAt", allow_empty=False)
    expected_return_at = _normalize_datetime_text(payload.get("expectedReturnAt"), "expectedReturnAt", allow_empty=False)
    purpose = _normalize_text(payload.get("purpose"), "purpose", 255)
    if not purpose:
        raise BizError("purpose required", 400)

    applicant_student_no = _normalize_text(payload.get("studentNo"), "studentNo", 64)
    applicant_class_name = _normalize_text(payload.get("className"), "className", 64)
    applicant_job_no = _normalize_text(payload.get("jobNo"), "jobNo", 64)
    if applicant_role == "student":
        if not applicant_student_no:
            raise BizError("studentNo required", 400)
        if not applicant_class_name:
            raise BizError("className required", 400)
    if applicant_role == "teacher" and not applicant_job_no:
        raise BizError("jobNo required", 400)

    start_dt = _to_datetime(borrow_start_at)
    end_dt = _to_datetime(expected_return_at)
    if start_dt == datetime.min or end_dt == datetime.min:
        raise BizError("invalid datetime", 400)
    if end_dt <= start_dt:
        raise BizError("expectedReturnAt must be later than borrowStartAt", 400)

    overdue_history = _borrow_overdue_history_count(applicant_user_name)
    risk_flag = 1 if overdue_history > 0 else 0
    risk_reason = "该用户存在历史逾期借用记录" if risk_flag == 1 else ""

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   asset_code AS assetCode,
                   name,
                   lab_name AS labName,
                   status,
                   allow_borrow AS allowBorrow,
                   is_borrowed AS isBorrowed
            FROM equipment
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(equipment_id),),
        )
        equipment = cur.fetchone()
        if not equipment:
            raise BizError("equipment not found", 404)
        if str(equipment.get("status") or "").strip() == "scrapped":
            raise BizError("scrapped equipment cannot be borrowed", 409)
        if int(equipment.get("allowBorrow") if equipment.get("allowBorrow") not in (None, "") else 1) != 1:
            raise BizError("equipment is not available for borrow", 409)
        if int(equipment.get("isBorrowed") or 0) == 1:
            raise BizError("equipment already borrowed", 409)

        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM equipment_borrow_request
            WHERE applicant_user_name=%s
              AND equipment_id=%s
              AND status IN ('pending', 'approved')
            """,
            (applicant_user_name, int(equipment_id)),
        )
        active_cnt = int((cur.fetchone() or {}).get("cnt") or 0)
        if active_cnt > 0:
            raise BizError("you already have an active request for this equipment", 409)

        now_text = _now_text()
        cur.execute(
            """
            INSERT INTO equipment_borrow_request (
                equipment_id, equipment_asset_code, equipment_name, equipment_lab_name,
                applicant_user_name, applicant_role, applicant_name, applicant_student_no, applicant_class_name, applicant_job_no,
                borrow_start_at, expected_return_at, purpose, status,
                risk_flag, risk_reason, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s, %s)
            """,
            (
                int(equipment_id),
                str(equipment.get("assetCode") or "").strip(),
                str(equipment.get("name") or "").strip(),
                str(equipment.get("labName") or "").strip(),
                applicant_user_name,
                applicant_role,
                applicant_name,
                applicant_student_no,
                applicant_class_name,
                applicant_job_no,
                borrow_start_at,
                expected_return_at,
                purpose,
                int(risk_flag),
                risk_reason,
                now_text,
                now_text,
            ),
        )
        return int(cur.lastrowid or 0)

    new_id = run_in_transaction(_tx)
    audit_log(
        "user.borrow_request.create",
        target_type="borrow_request",
        target_id=new_id,
        detail={
            "equipmentId": int(equipment_id),
            "borrowStartAt": borrow_start_at,
            "expectedReturnAt": expected_return_at,
            "riskFlag": int(risk_flag),
        },
        actor={"id": current_user.get("id"), "username": applicant_user_name, "role": applicant_role},
    )
    return jsonify({"ok": True, "data": {"id": int(new_id), "status": "pending", "riskFlag": bool(risk_flag), "riskReason": risk_reason}})


@app.post("/borrow-requests/<int:bid>/cancel")
@auth_required()
def cancel_borrow_request(bid):
    current_user = g.current_user or {}
    current_user_name = str(current_user.get("username") or "").strip()
    current_role = str(current_user.get("role") or "").strip().lower()
    if not current_user_name:
        raise BizError("unauthorized", 401)

    def _tx(cur):
        cur.execute(
            """
            SELECT id, applicant_user_name AS applicantUserName, status
            FROM equipment_borrow_request
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(bid),),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("borrow request not found", 404)
        owner = str(row.get("applicantUserName") or "").strip()
        if current_role != "admin" and owner != current_user_name:
            raise BizError("forbidden", 403)
        if str(row.get("status") or "").strip() != "pending":
            raise BizError("only pending request can be cancelled", 409)
        cur.execute(
            "UPDATE equipment_borrow_request SET status='cancelled', updated_at=%s WHERE id=%s",
            (_now_text(), int(bid)),
        )

    run_in_transaction(_tx)
    audit_log(
        "user.borrow_request.cancel",
        target_type="borrow_request",
        target_id=bid,
        actor={"id": current_user.get("id"), "username": current_user_name, "role": current_role},
    )
    return jsonify({"ok": True})


@app.post("/borrow-requests/<int:bid>/approve")
@auth_required(roles=["admin"])
def approve_borrow_request(bid):
    actor = g.current_user or {}
    actor_name = str(actor.get("username") or "").strip()
    actor_role = str(actor.get("role") or "").strip()
    actor_id = _safe_int(actor.get("id"))
    now_text = _now_text()

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   equipment_id AS equipmentId,
                   applicant_user_name AS applicantUserName,
                   applicant_name AS applicantName,
                   borrow_start_at AS borrowStartAt,
                   expected_return_at AS expectedReturnAt,
                   status
            FROM equipment_borrow_request
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(bid),),
        )
        req = cur.fetchone()
        if not req:
            raise BizError("borrow request not found", 404)
        if str(req.get("status") or "").strip() != "pending":
            raise BizError("invalid status", 409)

        equipment_id = int(req.get("equipmentId") or 0)
        if equipment_id <= 0:
            raise BizError("invalid equipment", 409)
        cur.execute(
            """
            SELECT id, status, allow_borrow AS allowBorrow, is_borrowed AS isBorrowed
            FROM equipment
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (equipment_id,),
        )
        equipment = cur.fetchone()
        if not equipment:
            raise BizError("equipment not found", 404)
        if str(equipment.get("status") or "").strip() == "scrapped":
            raise BizError("scrapped equipment cannot be borrowed", 409)
        if int(equipment.get("allowBorrow") if equipment.get("allowBorrow") not in (None, "") else 1) != 1:
            raise BizError("equipment is not available for borrow", 409)
        if int(equipment.get("isBorrowed") or 0) == 1:
            raise BizError("equipment already borrowed", 409)

        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM equipment_borrow_request
            WHERE equipment_id=%s
              AND id<>%s
              AND status='approved'
              AND returned_at IS NULL
            """,
            (equipment_id, int(bid)),
        )
        active_approved = int((cur.fetchone() or {}).get("cnt") or 0)
        if active_approved > 0:
            raise BizError("equipment has another active approved request", 409)

        borrower_name = str(req.get("applicantName") or "").strip() or str(req.get("applicantUserName") or "").strip()
        borrower_id = _resolve_user_id_by_username_with_cur(cur, req.get("applicantUserName"))
        borrowed_at = _to_text_time(req.get("borrowStartAt")) or now_text
        expected_return_at = _to_text_time(req.get("expectedReturnAt")) or ""
        cur.execute(
            """
            UPDATE equipment
            SET is_borrowed=1,
                borrowed_by_id=%s,
                borrowed_by=%s,
                borrowed_at=%s,
                expected_return_at=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (borrower_id, borrower_name, borrowed_at, expected_return_at, now_text, equipment_id),
        )

        cur.execute(
            """
            UPDATE equipment_borrow_request
            SET status='approved',
                reject_reason='',
                approved_by=%s,
                approved_at=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (actor_name, now_text, now_text, int(bid)),
        )

        _insert_equipment_event_with_cur(
            cur,
            equipment_id=equipment_id,
            event_type="borrow",
            note=f"borrow request approved, requestId={int(bid)}, borrower={borrower_name}",
            operator=actor,
            created_at=now_text,
        )
        return {"equipmentId": equipment_id, "borrowerName": borrower_name}

    tx_result = run_in_transaction(_tx)
    audit_log(
        "admin.borrow_request.approve",
        target_type="borrow_request",
        target_id=bid,
        detail=tx_result,
        actor={"id": actor_id, "username": actor_name, "role": actor_role},
    )
    return jsonify({"ok": True})


@app.post("/borrow-requests/<int:bid>/reject")
@auth_required(roles=["admin"])
def reject_borrow_request(bid):
    payload = request.get_json(force=True) or {}
    reject_reason = _normalize_text(payload.get("rejectReason"), "rejectReason", 255)
    actor = g.current_user or {}
    actor_name = str(actor.get("username") or "").strip()
    actor_role = str(actor.get("role") or "").strip()
    actor_id = _safe_int(actor.get("id"))

    def _tx(cur):
        cur.execute(
            """
            SELECT id, status
            FROM equipment_borrow_request
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(bid),),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("borrow request not found", 404)
        if str(row.get("status") or "").strip() != "pending":
            raise BizError("invalid status", 409)
        cur.execute(
            """
            UPDATE equipment_borrow_request
            SET status='rejected',
                reject_reason=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (reject_reason, _now_text(), int(bid)),
        )

    run_in_transaction(_tx)
    audit_log(
        "admin.borrow_request.reject",
        target_type="borrow_request",
        target_id=bid,
        detail={"rejectReason": reject_reason},
        actor={"id": actor_id, "username": actor_name, "role": actor_role},
    )
    return jsonify({"ok": True})


@app.post("/borrow-requests/<int:bid>/note")
@auth_required(roles=["admin"])
def add_borrow_request_note(bid):
    payload = request.get_json(force=True) or {}
    note = _normalize_text(payload.get("note"), "note", 255)
    if not note:
        raise BizError("note required", 400)

    rows = query("SELECT id FROM equipment_borrow_request WHERE id=%s LIMIT 1", (int(bid),))
    if not rows:
        raise BizError("borrow request not found", 404)

    execute(
        "UPDATE equipment_borrow_request SET admin_note=%s, updated_at=%s WHERE id=%s",
        (note, _now_text(), int(bid)),
    )
    actor = g.current_user or {}
    audit_log(
        "admin.borrow_request.note",
        target_type="borrow_request",
        target_id=bid,
        detail={"note": note},
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    return jsonify({"ok": True})


@app.post("/borrow-requests/<int:bid>/remind")
@auth_required(roles=["admin"])
def remind_borrow_request(bid):
    payload = request.get_json(force=True) or {}
    remind_message = _normalize_text(payload.get("message"), "message", 255)
    actor = g.current_user or {}
    actor_name = str(actor.get("username") or "").strip()
    actor_role = str(actor.get("role") or "").strip()
    actor_id = _safe_int(actor.get("id"))
    now_text = _now_text()
    today_text = datetime.now().strftime("%Y-%m-%d")

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   status,
                   equipment_name AS equipmentName,
                   equipment_asset_code AS equipmentAssetCode
            FROM equipment_borrow_request
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(bid),),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("borrow request not found", 404)
        if str(row.get("status") or "").strip() != "approved":
            raise BizError("only approved request can be reminded", 409)

        target = str(row.get("equipmentName") or "").strip() or str(row.get("equipmentAssetCode") or "").strip() or "设备"
        message = remind_message or f"{target} 借用已接近归还时间，请记得归还。"

        cur.execute(
            """
            SELECT id
            FROM equipment_borrow_reminder_log
            WHERE request_id=%s AND remind_type='manual' AND remind_date=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(bid), today_text),
        )
        exists = cur.fetchone()
        _record_borrow_reminder_with_cur(
            cur,
            request_id=int(bid),
            remind_type="manual",
            remind_date_text=today_text,
            reminded_by=actor_name,
            message=message,
        )
        if not exists:
            cur.execute(
                """
                UPDATE equipment_borrow_request
                SET remind_count=remind_count+1,
                    last_remind_at=%s,
                    updated_at=%s
                WHERE id=%s
                """,
                (now_text, now_text, int(bid)),
            )
        else:
            cur.execute(
                "UPDATE equipment_borrow_request SET last_remind_at=%s, updated_at=%s WHERE id=%s",
                (now_text, now_text, int(bid)),
            )
        return {"message": message}

    tx_result = run_in_transaction(_tx)
    audit_log(
        "admin.borrow_request.remind",
        target_type="borrow_request",
        target_id=bid,
        detail=tx_result,
        actor={"id": actor_id, "username": actor_name, "role": actor_role},
    )
    return jsonify({"ok": True, "data": tx_result})


@app.post("/borrow-requests/<int:bid>/mark-returned")
@auth_required(roles=["admin"])
def mark_borrow_request_returned(bid):
    payload = request.get_json(force=True) or {}
    note = _normalize_text(payload.get("note"), "note", 255)
    actor = g.current_user or {}
    actor_name = str(actor.get("username") or "").strip()
    actor_role = str(actor.get("role") or "").strip()
    actor_id = _safe_int(actor.get("id"))
    now_text = _now_text()

    def _tx(cur):
        return _mark_borrow_request_returned_with_cur(cur, bid, actor, note=note, return_channel="manual", scan_token="")

    tx_result = run_in_transaction(_tx)
    audit_log(
        "admin.borrow_request.returned",
        target_type="borrow_request",
        target_id=bid,
        detail=tx_result,
        actor={"id": actor_id, "username": actor_name, "role": actor_role},
    )
    return jsonify({"ok": True, "data": tx_result})


@app.post("/borrow-requests/<int:bid>/renew")
@auth_required()
def create_borrow_extension_request(bid):
    payload = request.get_json(force=True) or {}
    current_user = g.current_user or {}
    user_name = str(current_user.get("username") or "").strip()
    role = str(current_user.get("role") or "").strip().lower()
    requested_return_at = _normalize_datetime_text(payload.get("requestedReturnAt"), "requestedReturnAt", allow_empty=False)
    reason = _normalize_text(payload.get("reason"), "reason", 255)
    if not user_name:
        raise BizError("unauthorized", 401)

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   applicant_user_name AS applicantUserName,
                   expected_return_at AS expectedReturnAt,
                   status
            FROM equipment_borrow_request
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(bid),),
        )
        req = cur.fetchone()
        if not req:
            raise BizError("borrow request not found", 404)
        if role != "admin" and str(req.get("applicantUserName") or "").strip() != user_name:
            raise BizError("forbidden", 403)
        if str(req.get("status") or "").strip() != "approved":
            raise BizError("only approved request can renew", 409)
        expected_dt = _to_datetime(req.get("expectedReturnAt"))
        next_dt = _to_datetime(requested_return_at)
        if expected_dt == datetime.min or next_dt == datetime.min or next_dt <= expected_dt:
            raise BizError("requestedReturnAt must be later than current expectedReturnAt", 400)
        cur.execute(
            """
            SELECT id
            FROM borrow_extension_request
            WHERE request_id=%s
              AND status='pending'
            LIMIT 1
            FOR UPDATE
            """,
            (int(bid),),
        )
        if cur.fetchone():
            raise BizError("pending renew request already exists", 409)
        cur.execute(
            """
            INSERT INTO borrow_extension_request (
                request_id, applicant_user_name, requested_return_at, reason, status, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, 'pending', %s, %s)
            """,
            (int(bid), user_name, requested_return_at, reason, _now_text(), _now_text()),
        )
        return int(cur.lastrowid or 0)

    extension_id = run_in_transaction(_tx)
    audit_log(
        "user.borrow_request.renew.create",
        target_type="borrow_extension_request",
        target_id=extension_id,
        detail={"requestId": int(bid), "requestedReturnAt": requested_return_at},
        actor={"id": current_user.get("id"), "username": user_name, "role": current_user.get("role")},
    )
    return jsonify({"ok": True, "data": {"id": extension_id}})


@app.get("/borrow-requests/extensions")
@auth_required()
def list_borrow_extension_requests():
    current_user = g.current_user or {}
    user_name = str(current_user.get("username") or "").strip()
    role = str(current_user.get("role") or "").strip().lower()
    status = str(request.args.get("status") or "").strip().lower()
    request_id = _to_int_or_none(request.args.get("requestId"))

    where_sql = " WHERE 1=1"
    params = []
    if role != "admin":
        where_sql += " AND e.applicant_user_name=%s"
        params.append(user_name)
    if status:
        if status not in BORROW_EXTENSION_STATUS_SET:
            raise BizError("invalid status", 400)
        where_sql += " AND e.status=%s"
        params.append(status)
    if request_id:
        where_sql += " AND e.request_id=%s"
        params.append(int(request_id))

    rows = query(
        """
        SELECT e.id,
               e.request_id AS requestId,
               e.applicant_user_name AS applicantUserName,
               e.requested_return_at AS requestedReturnAt,
               e.reason,
               e.status,
               e.reviewed_by AS reviewedBy,
               e.reviewed_at AS reviewedAt,
               e.reject_reason AS rejectReason,
               e.created_at AS createdAt,
               e.updated_at AS updatedAt,
               r.equipment_name AS equipmentName,
               r.equipment_asset_code AS equipmentAssetCode,
               r.expected_return_at AS currentExpectedReturnAt
        FROM borrow_extension_request e
        LEFT JOIN equipment_borrow_request r ON r.id=e.request_id
        """
        + where_sql
        + """
        ORDER BY e.id DESC
        LIMIT 200
        """,
        tuple(params),
    )
    data = []
    for row in rows:
        data.append(
            {
                "id": int(row.get("id") or 0),
                "requestId": int(row.get("requestId") or 0),
                "applicantUserName": str(row.get("applicantUserName") or "").strip(),
                "requestedReturnAt": _to_text_time(row.get("requestedReturnAt")),
                "currentExpectedReturnAt": _to_text_time(row.get("currentExpectedReturnAt")),
                "reason": str(row.get("reason") or "").strip(),
                "status": str(row.get("status") or "").strip(),
                "reviewedBy": str(row.get("reviewedBy") or "").strip(),
                "reviewedAt": _to_text_time(row.get("reviewedAt")),
                "rejectReason": str(row.get("rejectReason") or "").strip(),
                "equipmentName": str(row.get("equipmentName") or "").strip(),
                "equipmentAssetCode": str(row.get("equipmentAssetCode") or "").strip(),
                "createdAt": _to_text_time(row.get("createdAt")),
                "updatedAt": _to_text_time(row.get("updatedAt")),
            }
        )
    return jsonify({"ok": True, "data": data})


@app.post("/borrow-requests/extensions/<int:extension_id>/approve")
@auth_required(roles=["admin"])
def approve_borrow_extension_request(extension_id):
    actor = g.current_user or {}
    now_text = _now_text()

    def _tx(cur):
        cur.execute(
            """
            SELECT e.id,
                   e.request_id AS requestId,
                   e.requested_return_at AS requestedReturnAt,
                   e.status,
                   r.status AS requestStatus
            FROM borrow_extension_request e
            LEFT JOIN equipment_borrow_request r ON r.id=e.request_id
            WHERE e.id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(extension_id),),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("extension request not found", 404)
        if str(row.get("status") or "").strip() != "pending":
            raise BizError("invalid status", 409)
        if str(row.get("requestStatus") or "").strip() != "approved":
            raise BizError("borrow request not active", 409)
        cur.execute(
            """
            UPDATE equipment_borrow_request
            SET expected_return_at=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (row.get("requestedReturnAt"), now_text, int(row.get("requestId") or 0)),
        )
        cur.execute(
            """
            UPDATE borrow_extension_request
            SET status='approved',
                reviewed_by=%s,
                reviewed_at=%s,
                reject_reason='',
                updated_at=%s
            WHERE id=%s
            """,
            (str(actor.get("username") or "").strip(), now_text, now_text, int(extension_id)),
        )
        return {"requestId": int(row.get("requestId") or 0), "requestedReturnAt": _to_text_time(row.get("requestedReturnAt"))}

    tx_result = run_in_transaction(_tx)
    audit_log("admin.borrow_request.renew.approve", target_type="borrow_extension_request", target_id=extension_id, detail=tx_result, actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")})
    return jsonify({"ok": True, "data": tx_result})


@app.post("/borrow-requests/extensions/<int:extension_id>/reject")
@auth_required(roles=["admin"])
def reject_borrow_extension_request(extension_id):
    payload = request.get_json(force=True) or {}
    reject_reason = _normalize_text(payload.get("rejectReason"), "rejectReason", 255)
    actor = g.current_user or {}

    def _tx(cur):
        cur.execute("SELECT id, status FROM borrow_extension_request WHERE id=%s LIMIT 1 FOR UPDATE", (int(extension_id),))
        row = cur.fetchone()
        if not row:
            raise BizError("extension request not found", 404)
        if str(row.get("status") or "").strip() != "pending":
            raise BizError("invalid status", 409)
        cur.execute(
            """
            UPDATE borrow_extension_request
            SET status='rejected',
                reviewed_by=%s,
                reviewed_at=%s,
                reject_reason=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (str(actor.get("username") or "").strip(), _now_text(), reject_reason, _now_text(), int(extension_id)),
        )

    run_in_transaction(_tx)
    audit_log("admin.borrow_request.renew.reject", target_type="borrow_extension_request", target_id=extension_id, detail={"rejectReason": reject_reason}, actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")})
    return jsonify({"ok": True})


@app.post("/borrow-requests/<int:bid>/ai-remind")
@auth_required(roles=["admin"])
def ai_remind_borrow_request(bid):
    actor = g.current_user or {}
    rows = query(
        """
        SELECT id,
               equipment_name AS equipmentName,
               equipment_asset_code AS equipmentAssetCode,
               expected_return_at AS expectedReturnAt,
               status
        FROM equipment_borrow_request
        WHERE id=%s
        LIMIT 1
        """,
        (int(bid),),
    )
    if not rows:
        raise BizError("borrow request not found", 404)
    row = rows[0] or {}
    if str(row.get("status") or "").strip() != "approved":
        raise BizError("only approved request can be reminded", 409)
    message = _build_borrow_ai_remind_message(row)
    request.get_json(silent=True)
    # reuse the existing manual remind path so remind counters stay consistent
    with app.test_request_context(json={"message": message}, headers={"Authorization": request.headers.get("Authorization", "")}):
        g.current_user = actor
        res = remind_borrow_request(int(bid))
    log_ai_action(
        "admin.borrow_request.ai_remind",
        target_type="borrow_request",
        target_id=bid,
        suggestion={"message": message},
        execute_payload={"message": message},
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    return res


@app.post("/borrow-requests/scan-return")
@auth_required(roles=["admin"])
def scan_return_borrow_request():
    payload = request.get_json(force=True) or {}
    token = _normalize_text(payload.get("token"), "token", 128)
    note = _normalize_text(payload.get("note"), "note", 255)
    if not token:
        raise BizError("token required", 400)
    actor = g.current_user or {}
    rows = query(
        """
        SELECT id
        FROM equipment
        WHERE qr_token=%s OR barcode_value=%s OR asset_code=%s
        LIMIT 1
        """,
        (token, token, token),
    )
    if not rows:
        raise BizError("equipment not found", 404)
    equipment_id = int(rows[0].get("id") or 0)
    req_rows = query(
        """
        SELECT id
        FROM equipment_borrow_request
        WHERE equipment_id=%s
          AND status='approved'
          AND returned_at IS NULL
        ORDER BY id DESC
        LIMIT 1
        """,
        (equipment_id,),
    )
    if not req_rows:
        raise BizError("active borrow request not found", 404)
    request_id = int(req_rows[0].get("id") or 0)
    tx_result = run_in_transaction(lambda cur: _mark_borrow_request_returned_with_cur(cur, request_id, actor, note=note, return_channel="scan", scan_token=token))
    audit_log(
        "admin.borrow_request.scan_return",
        target_type="borrow_request",
        target_id=request_id,
        detail={"equipmentId": equipment_id, "token": token},
        actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": {"requestId": request_id, **tx_result}})


@app.get("/borrow-compensations")
@auth_required()
def list_borrow_compensations():
    current_user = g.current_user or {}
    user_name = str(current_user.get("username") or "").strip()
    role = str(current_user.get("role") or "").strip().lower()
    status = str(request.args.get("status") or "").strip().lower()
    request_id = _to_int_or_none(request.args.get("requestId"))
    where_sql = " WHERE 1=1"
    params = []
    if role != "admin":
        where_sql += " AND c.applicant_user_name=%s"
        params.append(user_name)
    if status:
        if status not in BORROW_COMPENSATION_STATUS_SET:
            raise BizError("invalid status", 400)
        where_sql += " AND c.status=%s"
        params.append(status)
    if request_id:
        where_sql += " AND c.request_id=%s"
        params.append(int(request_id))

    rows = query(
        """
        SELECT c.id,
               c.request_id AS requestId,
               c.equipment_id AS equipmentId,
               c.applicant_user_name AS applicantUserName,
               c.damage_level AS damageLevel,
               c.description,
               c.image_url AS imageUrl,
               c.amount,
               c.status,
               c.handled_by AS handledBy,
               c.handled_at AS handledAt,
               c.created_at AS createdAt,
               c.updated_at AS updatedAt,
               r.equipment_name AS equipmentName,
               r.equipment_asset_code AS equipmentAssetCode
        FROM borrow_compensation_order c
        LEFT JOIN equipment_borrow_request r ON r.id=c.request_id
        """
        + where_sql
        + """
        ORDER BY c.id DESC
        LIMIT 200
        """,
        tuple(params),
    )
    data = []
    for row in rows:
        data.append(
            {
                "id": int(row.get("id") or 0),
                "requestId": int(row.get("requestId") or 0),
                "equipmentId": int(row.get("equipmentId") or 0),
                "applicantUserName": str(row.get("applicantUserName") or "").strip(),
                "damageLevel": str(row.get("damageLevel") or "").strip(),
                "description": str(row.get("description") or "").strip(),
                "imageUrl": str(row.get("imageUrl") or "").strip(),
                "amount": float(row.get("amount") or 0),
                "status": str(row.get("status") or "").strip(),
                "handledBy": str(row.get("handledBy") or "").strip(),
                "handledAt": _to_text_time(row.get("handledAt")),
                "equipmentName": str(row.get("equipmentName") or "").strip(),
                "equipmentAssetCode": str(row.get("equipmentAssetCode") or "").strip(),
                "createdAt": _to_text_time(row.get("createdAt")),
                "updatedAt": _to_text_time(row.get("updatedAt")),
            }
        )
    return jsonify({"ok": True, "data": data})


@app.post("/borrow-requests/<int:bid>/compensations")
@auth_required(roles=["admin"])
def create_borrow_compensation(bid):
    payload = request.get_json(force=True) or {}
    damage_level = _normalize_text(payload.get("damageLevel"), "damageLevel", 32) or "normal"
    description = _normalize_text(payload.get("description"), "description", 500)
    image_url = _normalize_text(payload.get("imageUrl"), "imageUrl", 255)
    try:
        amount = round(float(payload.get("amount") or 0), 2)
    except (TypeError, ValueError):
        raise BizError("invalid amount", 400)
    if amount < 0:
        raise BizError("invalid amount", 400)
    actor = g.current_user or {}
    req_rows = query(
        """
        SELECT id,
               equipment_id AS equipmentId,
               applicant_user_name AS applicantUserName
        FROM equipment_borrow_request
        WHERE id=%s
        LIMIT 1
        """,
        (int(bid),),
    )
    if not req_rows:
        raise BizError("borrow request not found", 404)
    req = req_rows[0] or {}
    compensation_id = execute_insert(
        """
        INSERT INTO borrow_compensation_order (
            request_id, equipment_id, applicant_user_name, damage_level, description, image_url, amount, status, handled_by, handled_at, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s, %s)
        """,
        (
            int(bid),
            int(req.get("equipmentId") or 0),
            str(req.get("applicantUserName") or "").strip(),
            damage_level,
            description,
            image_url,
            amount,
            str(actor.get("username") or "").strip(),
            _now_text(),
            _now_text(),
            _now_text(),
        ),
    )
    audit_log("admin.borrow_compensation.create", target_type="borrow_compensation_order", target_id=compensation_id, detail={"requestId": int(bid), "amount": amount}, actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")})
    return jsonify({"ok": True, "data": {"id": int(compensation_id)}})


@app.post("/borrow-compensations/<int:compensation_id>/status")
@auth_required(roles=["admin"])
def update_borrow_compensation_status(compensation_id):
    payload = request.get_json(force=True) or {}
    status = _normalize_text(payload.get("status"), "status", 16)
    if status not in BORROW_COMPENSATION_STATUS_SET:
        raise BizError("invalid status", 400)
    actor = g.current_user or {}
    execute(
        """
        UPDATE borrow_compensation_order
        SET status=%s,
            handled_by=%s,
            handled_at=%s,
            updated_at=%s
        WHERE id=%s
        """,
        (status, str(actor.get("username") or "").strip(), _now_text(), _now_text(), int(compensation_id)),
    )
    audit_log("admin.borrow_compensation.status", target_type="borrow_compensation_order", target_id=compensation_id, detail={"status": status}, actor={"id": actor.get("id"), "username": actor.get("username"), "role": actor.get("role")})
    return jsonify({"ok": True})


@app.get("/pcs/status")
@auth_required(roles=["admin"])
def list_pcs_status():
    lab_id_raw = str(request.args.get("labId") or "").strip()
    if not lab_id_raw:
        raise BizError("labId required", 400)
    lab_id = _to_int_or_none(lab_id_raw)
    if lab_id is None:
        raise BizError("invalid labId", 400)

    include_non_pc = _to_bool_flag(request.args.get("includeNonPc"))
    rows = query(
        """
        SELECT id,
               asset_code AS assetCode,
               name,
               status,
               lab_id AS labId,
               lab_name AS labName,
               spec_json AS specJson,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM equipment
        WHERE lab_id=%s
        ORDER BY id ASC
        """,
        (int(lab_id),),
    )

    data = []
    for row in rows:
        spec = _parse_equipment_spec_map(row.get("specJson"))
        category = str(spec.get("category") or "").strip().lower()
        asset_code = str(row.get("assetCode") or "").strip().upper()
        is_pc = category == "pc" or asset_code.startswith("PC-")
        if not include_non_pc and not is_pc:
            continue

        seat_raw = spec.get("seatCode") or spec.get("seat") or spec.get("seat_code") or ""
        if not seat_raw and asset_code.startswith("PC-"):
            seat_raw = asset_code[3:]
        seat_code = _normalize_pc_seat_code(seat_raw)

        last_seen_raw = spec.get("lastSeen") or spec.get("last_seen") or row.get("updatedAt") or row.get("createdAt")
        last_seen = _to_text_time(last_seen_raw)
        runtime_status = _pc_runtime_status(row.get("status"))

        data.append(
            {
                "equipmentId": int(row.get("id") or 0),
                "assetCode": str(row.get("assetCode") or ""),
                "name": str(row.get("name") or ""),
                "labId": _safe_int(row.get("labId")),
                "labName": str(row.get("labName") or ""),
                "seatCode": seat_code,
                "status": runtime_status,
                "state": runtime_status,
                "lastSeen": last_seen,
                "updatedAt": _to_text_time(row.get("updatedAt")),
                "equipmentStatus": str(row.get("status") or ""),
            }
        )

    return jsonify({"ok": True, "data": data, "meta": {"count": len(data)}})


@app.post("/equipments")
@auth_required(roles=["admin"])
def create_equipment():
    payload = _normalize_equipment_payload(request.get_json(force=True) or {})
    payload["allowBorrow"] = _resolve_allow_borrow_flag(payload)
    dup = query("SELECT id FROM equipment WHERE asset_code=%s LIMIT 1", (payload["assetCode"],))
    if dup:
        raise BizError("asset_code exists", 409)

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_id = execute_insert(
        """
        INSERT INTO equipment (
            asset_code, name, model, brand, lab_id, lab_name,
            status, keeper, purchase_date, price, spec_json, image_url, allow_borrow, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            payload["assetCode"],
            payload["name"],
            payload["model"],
            payload["brand"],
            payload["labId"],
            payload["labName"],
            payload["status"],
            payload["keeper"],
            payload["purchaseDate"],
            payload["price"],
            payload["specJson"],
            payload["imageUrl"],
            1 if payload["allowBorrow"] else 0,
            created_at,
        ),
    )
    audit_log("equipment.create", "equipment", new_id, detail=payload)
    return jsonify({"ok": True, "data": {"id": int(new_id)}})


@app.post("/equipments/<int:eid>")
@auth_required(roles=["admin"])
def update_equipment(eid):
    existing = _find_equipment_or_raise(eid)
    payload = _normalize_equipment_payload(request.get_json(force=True) or {})
    payload["allowBorrow"] = _resolve_allow_borrow_flag(payload, existing_allow_borrow=existing.get("allowBorrow"))
    dup = query(
        "SELECT id FROM equipment WHERE asset_code=%s AND id<>%s LIMIT 1",
        (payload["assetCode"], eid),
    )
    if dup:
        raise BizError("asset_code exists", 409)

    execute(
        """
        UPDATE equipment
        SET asset_code=%s,
            name=%s,
            model=%s,
            brand=%s,
            lab_id=%s,
            lab_name=%s,
            status=%s,
            keeper=%s,
            purchase_date=%s,
            price=%s,
            spec_json=%s,
            image_url=%s,
            allow_borrow=%s
        WHERE id=%s
        """,
        (
            payload["assetCode"],
            payload["name"],
            payload["model"],
            payload["brand"],
            payload["labId"],
            payload["labName"],
            payload["status"],
            payload["keeper"],
            payload["purchaseDate"],
            payload["price"],
            payload["specJson"],
            payload["imageUrl"],
            1 if payload["allowBorrow"] else 0,
            eid,
        ),
    )
    audit_log("equipment.update", "equipment", eid, detail=payload)
    return jsonify({"ok": True})


@app.post("/equipments/<int:eid>/delete")
@auth_required(roles=["admin"])
def delete_equipment(eid):
    def _tx(cur):
        cur.execute(
            """
            SELECT id, asset_code AS assetCode, name
            FROM equipment
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (eid,),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("equipment not found", 404)

        cur.execute("SELECT COUNT(*) AS cnt FROM equipment_event WHERE equipment_id=%s", (eid,))
        ref_cnt = int((cur.fetchone() or {}).get("cnt") or 0)
        if ref_cnt > 0:
            raise BizError("equipment has events, cannot delete", 409)
        cur.execute("SELECT COUNT(*) AS cnt FROM repair_work_order WHERE equipment_id=%s", (eid,))
        repair_ref_cnt = int((cur.fetchone() or {}).get("cnt") or 0)
        if repair_ref_cnt > 0:
            raise BizError("equipment has repair orders, cannot delete", 409)

        cur.execute("DELETE FROM equipment WHERE id=%s", (eid,))
        if int(cur.rowcount or 0) != 1:
            raise BizError("equipment not found", 404)
        return row

    deleted = run_in_transaction(_tx)
    audit_log(
        "equipment.delete",
        "equipment",
        eid,
        detail={"assetCode": deleted.get("assetCode") or "", "name": deleted.get("name") or ""},
    )
    return jsonify({"ok": True})


@app.get("/equipments/<int:eid>/events")
@auth_required()
def list_equipment_events(eid):
    _find_equipment_or_raise(eid)
    page, page_size, offset = _parse_page_and_size(
        request.args.get("page", "1"),
        request.args.get("pageSize", "20"),
    )
    total_rows = query("SELECT COUNT(*) AS cnt FROM equipment_event WHERE equipment_id=%s", (eid,))
    total = int((total_rows[0] or {}).get("cnt") or 0) if total_rows else 0

    rows = query(
        """
        SELECT id,
               equipment_id AS equipmentId,
               event_type AS eventType,
               operator_id AS operatorId,
               operator_name AS operatorName,
               note,
               attachment_url AS attachmentUrl,
               created_at AS createdAt
        FROM equipment_event
        WHERE equipment_id=%s
        ORDER BY id DESC
        LIMIT %s OFFSET %s
        """,
        (eid, page_size, offset),
    )
    for row in rows:
        row["createdAt"] = _to_text_time(row.get("createdAt"))
    return jsonify(
        {
            "ok": True,
            "data": rows,
            "meta": {
                "page": page,
                "pageSize": page_size,
                "total": total,
            },
        }
    )


@app.post("/equipments/<int:eid>/events")
@auth_required()
def create_equipment_event(eid):
    equipment = _find_equipment_or_raise(eid)
    payload = request.get_json(force=True) or {}
    event_type = str(payload.get("eventType") or "").strip().lower()
    if event_type not in EQUIPMENT_EVENT_TYPE_SET:
        raise BizError("invalid eventType", 400)

    current_user = g.current_user or {}
    current_role = str(current_user.get("role") or "").strip()
    if current_role != "admin" and event_type not in EQUIPMENT_EVENT_USER_ALLOWED:
        raise BizError("forbidden", 403)

    note = str(payload.get("note") or "").strip()
    attachment_url = str(payload.get("attachmentUrl") or "").strip()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    operator_id = _to_int_or_none(current_user.get("id"))
    operator_name = str(current_user.get("username") or "").strip()

    new_id = execute_insert(
        """
        INSERT INTO equipment_event (
            equipment_id, event_type, operator_id, operator_name, note, attachment_url, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (eid, event_type, operator_id, operator_name, note, attachment_url, created_at),
    )
    audit_log(
        "equipment_event.create",
        "equipment_event",
        new_id,
        detail={
            "equipmentId": eid,
            "eventType": event_type,
            "attachmentUrl": attachment_url,
        },
    )
    repair_order_id = None
    if event_type == "maintain":
        issue_type = _normalize_repair_issue_type(payload.get("issueType"))
        desc = _normalize_repair_description(payload.get("description") or note, allow_empty=True)
        if not desc:
            desc = "equipment repair"
        repair_order_id = _create_repair_order_record(
            submitter_id=operator_id,
            submitter_name=operator_name,
            equipment_id=_safe_int(equipment.get("id")),
            asset_code=equipment.get("assetCode"),
            equipment_name=equipment.get("name"),
            lab_id=_safe_int(equipment.get("labId")),
            lab_name=equipment.get("labName"),
            issue_type=issue_type,
            description=desc,
            attachment_url=attachment_url,
        )
        audit_log(
            "repair_order.create",
            "repair_work_order",
            repair_order_id,
            detail={
                "source": "equipment_event",
                "equipmentId": _safe_int(equipment.get("id")),
                "eventId": int(new_id),
            },
            actor={"id": operator_id, "username": operator_name, "role": current_role},
        )
    return jsonify({"ok": True, "data": {"id": int(new_id), "repairOrderId": repair_order_id}})


def _insert_equipment_event_with_cur(
    cur,
    *,
    equipment_id,
    event_type,
    note="",
    attachment_url="",
    operator=None,
    created_at=None,
):
    if event_type not in EQUIPMENT_EVENT_TYPE_SET:
        raise BizError("invalid eventType", 400)
    actor = operator or getattr(g, "current_user", {}) or {}
    operator_id = _to_int_or_none(actor.get("id"))
    operator_name = str(actor.get("username") or "").strip()
    created_text = str(created_at or "").strip() or _now_text()
    cur.execute(
        """
        INSERT INTO equipment_event (
            equipment_id, event_type, operator_id, operator_name, note, attachment_url, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            int(equipment_id),
            str(event_type),
            operator_id,
            operator_name,
            str(note or "").strip(),
            str(attachment_url or "").strip(),
            created_text,
        ),
    )
    return int(cur.lastrowid or 0)


def _format_inventory_session_row(row):
    out = dict(row or {})
    out["id"] = int(out.get("id") or 0)
    out["labId"] = _safe_int(out.get("labId"))
    out["plannedCount"] = int(out.get("plannedCount") or 0)
    out["checkedCount"] = int(out.get("checkedCount") or 0)
    out["diffCount"] = int(out.get("diffCount") or 0)
    out["startedAt"] = _to_text_time(out.get("startedAt"))
    out["closedAt"] = _to_text_time(out.get("closedAt"))
    out["createdAt"] = _to_text_time(out.get("createdAt"))
    out["updatedAt"] = _to_text_time(out.get("updatedAt"))
    return out


def _format_inventory_item_row(row):
    out = dict(row or {})
    out["id"] = int(out.get("id") or 0)
    out["sessionId"] = _safe_int(out.get("sessionId"))
    out["equipmentId"] = _safe_int(out.get("equipmentId"))
    out["expectedLabId"] = _safe_int(out.get("expectedLabId"))
    out["scannedLabId"] = _safe_int(out.get("scannedLabId"))
    out["scannedAt"] = _to_text_time(out.get("scannedAt"))
    out["createdAt"] = _to_text_time(out.get("createdAt"))
    out["updatedAt"] = _to_text_time(out.get("updatedAt"))
    return out


def _get_inventory_session_or_raise(session_id):
    rows = query(
        """
        SELECT id,
               inventory_no AS inventoryNo,
               lab_id AS labId,
               lab_name AS labName,
               status,
               planned_count AS plannedCount,
               checked_count AS checkedCount,
               diff_count AS diffCount,
               started_by AS startedBy,
               started_at AS startedAt,
               closed_by AS closedBy,
               closed_at AS closedAt,
               note,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM equipment_inventory_session
        WHERE id=%s
        LIMIT 1
        """,
        (int(session_id),),
    )
    if not rows:
        raise BizError("inventory session not found", 404)
    return _format_inventory_session_row(rows[0])


def _refresh_inventory_session_stats_with_cur(cur, session_id):
    cur.execute(
        """
        SELECT COUNT(*) AS plannedCount,
               SUM(CASE WHEN scan_status<>'pending' THEN 1 ELSE 0 END) AS checkedCount,
               SUM(CASE WHEN discrepancy_type<>'' THEN 1 ELSE 0 END) AS diffCount
        FROM equipment_inventory_item
        WHERE session_id=%s
        """,
        (int(session_id),),
    )
    agg = cur.fetchone() or {}
    planned_count = int(agg.get("plannedCount") or 0)
    checked_count = int(agg.get("checkedCount") or 0)
    diff_count = int(agg.get("diffCount") or 0)
    cur.execute(
        """
        UPDATE equipment_inventory_session
        SET planned_count=%s,
            checked_count=%s,
            diff_count=%s,
            updated_at=%s
        WHERE id=%s
        """,
        (planned_count, checked_count, diff_count, _now_text(), int(session_id)),
    )
    return {
        "plannedCount": planned_count,
        "checkedCount": checked_count,
        "diffCount": diff_count,
    }


def _extract_scan_tokens(raw_code):
    code = str(raw_code or "").strip()
    if not code:
        raise BizError("code required", 400)

    hit = re.search(r"[?&](?:code|token|assetCode)=([^&#]+)", code, flags=re.IGNORECASE)
    if hit:
        code = str(hit.group(1) or "").strip()

    token = ""
    upper_code = code.upper()
    if upper_code.startswith("LAB-ASSET:"):
        token = str(code.split(":", 1)[1] or "").strip()
    return code, token


def _find_equipment_id_by_scan_code(raw_code):
    code, token = _extract_scan_tokens(raw_code)

    if token:
        rows = query("SELECT id FROM equipment WHERE qr_token=%s LIMIT 1", (token,))
        if rows:
            return int(rows[0].get("id") or 0)

    rows = query(
        """
        SELECT id
        FROM equipment
        WHERE UPPER(asset_code)=UPPER(%s) OR UPPER(barcode_value)=UPPER(%s)
        LIMIT 1
        """,
        (code, code),
    )
    if rows:
        return int(rows[0].get("id") or 0)
    raise BizError("equipment not found by code", 404)


def _ensure_equipment_qr_token(eid):
    equipment = _find_equipment_or_raise(eid)
    current = str(equipment.get("qrToken") or "").strip()
    if current:
        return current

    for _ in range(8):
        token = _new_qr_token()
        dup = query("SELECT id FROM equipment WHERE qr_token=%s LIMIT 1", (token,))
        if dup:
            continue
        execute("UPDATE equipment SET qr_token=%s WHERE id=%s", (token, int(eid)))
        return token
    raise BizError("failed to generate qr token", 500)


@app.post("/equipments/<int:eid>/scrap")
@auth_required(roles=["admin"])
def scrap_equipment(eid):
    payload = request.get_json(force=True) or {}
    reason = _normalize_text(payload.get("reason"), "reason", 255)
    if not reason:
        raise BizError("reason required", 400)

    actor = g.current_user or {}
    actor_id = _safe_int(actor.get("id"))
    actor_name = str(actor.get("username") or "").strip()
    actor_role = str(actor.get("role") or "").strip()
    now_text = _now_text()

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   status,
                   is_borrowed AS isBorrowed,
                   asset_code AS assetCode,
                   name
            FROM equipment
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(eid),),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("equipment not found", 404)

        if str(row.get("status") or "").strip() == "scrapped":
            return {"changed": False, "assetCode": row.get("assetCode"), "name": row.get("name")}

        if int(row.get("isBorrowed") or 0) == 1:
            raise BizError("equipment is borrowed, return first", 409)

        cur.execute(
            """
            UPDATE equipment
            SET status='scrapped',
                is_borrowed=0,
                borrowed_by_id=NULL,
                borrowed_by='',
                borrowed_at=NULL,
                expected_return_at=NULL,
                scrap_reason=%s,
                scrapped_at=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (reason, now_text, now_text, int(eid)),
        )
        _insert_equipment_event_with_cur(
            cur,
            equipment_id=eid,
            event_type="scrap",
            note=reason,
            operator=actor,
            created_at=now_text,
        )
        return {"changed": True, "assetCode": row.get("assetCode"), "name": row.get("name")}

    tx_result = run_in_transaction(_tx)
    audit_log(
        "equipment.scrap",
        "equipment",
        eid,
        detail={"reason": reason, "changed": bool(tx_result.get("changed"))},
        actor={"id": actor_id, "username": actor_name, "role": actor_role},
    )
    return jsonify({"ok": True, "data": _find_equipment_or_raise(eid), "meta": tx_result})


@app.post("/equipments/<int:eid>/borrow")
@auth_required(roles=["admin"])
def borrow_equipment(eid):
    payload = request.get_json(force=True) or {}
    borrower_name = _normalize_text(payload.get("borrowerName"), "borrowerName", 64)
    if not borrower_name:
        raise BizError("borrowerName required", 400)
    borrower_id = _to_int_or_none(payload.get("borrowerId"))
    if payload.get("borrowerId") not in (None, "") and borrower_id is None:
        raise BizError("invalid borrowerId", 400)
    expected_return_at = _normalize_datetime_text(payload.get("expectedReturnAt"), "expectedReturnAt", allow_empty=True)
    note = _normalize_text(payload.get("note"), "note", 255)

    actor = g.current_user or {}
    actor_id = _safe_int(actor.get("id"))
    actor_name = str(actor.get("username") or "").strip()
    actor_role = str(actor.get("role") or "").strip()
    now_text = _now_text()

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   status,
                   allow_borrow AS allowBorrow,
                   is_borrowed AS isBorrowed
            FROM equipment
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(eid),),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("equipment not found", 404)

        status = str(row.get("status") or "").strip()
        if status == "scrapped":
            raise BizError("scrapped equipment cannot be borrowed", 409)
        if int(row.get("allowBorrow") if row.get("allowBorrow") not in (None, "") else 1) != 1:
            raise BizError("equipment is not available for borrow", 409)
        if int(row.get("isBorrowed") or 0) == 1:
            raise BizError("equipment already borrowed", 409)

        cur.execute(
            """
            UPDATE equipment
            SET is_borrowed=1,
                borrowed_by_id=%s,
                borrowed_by=%s,
                borrowed_at=%s,
                expected_return_at=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (borrower_id, borrower_name, now_text, expected_return_at, now_text, int(eid)),
        )

        event_note = f"borrower={borrower_name}"
        if expected_return_at:
            event_note += f"; expectedReturnAt={expected_return_at}"
        if note:
            event_note += f"; note={note}"
        _insert_equipment_event_with_cur(
            cur,
            equipment_id=eid,
            event_type="borrow",
            note=event_note,
            operator=actor,
            created_at=now_text,
        )
        return {"borrowerName": borrower_name, "expectedReturnAt": expected_return_at or ""}

    tx_result = run_in_transaction(_tx)
    audit_log(
        "equipment.borrow",
        "equipment",
        eid,
        detail=tx_result,
        actor={"id": actor_id, "username": actor_name, "role": actor_role},
    )
    return jsonify({"ok": True, "data": _find_equipment_or_raise(eid)})


@app.post("/equipments/<int:eid>/return")
@auth_required(roles=["admin"])
def return_equipment(eid):
    payload = request.get_json(force=True) or {}
    note = _normalize_text(payload.get("note"), "note", 255)
    actor = g.current_user or {}
    actor_id = _safe_int(actor.get("id"))
    actor_name = str(actor.get("username") or "").strip()
    actor_role = str(actor.get("role") or "").strip()
    now_text = _now_text()

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   status,
                   is_borrowed AS isBorrowed,
                   borrowed_by AS borrowedBy
            FROM equipment
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(eid),),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("equipment not found", 404)
        if int(row.get("isBorrowed") or 0) != 1:
            raise BizError("equipment is not borrowed", 409)

        cur.execute(
            """
            UPDATE equipment
            SET is_borrowed=0,
                borrowed_by_id=NULL,
                borrowed_by='',
                borrowed_at=NULL,
                expected_return_at=NULL,
                last_returned_at=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (now_text, now_text, int(eid)),
        )
        event_note = f"return by {actor_name or '-'}"
        if row.get("borrowedBy"):
            event_note += f"; borrower={row.get('borrowedBy')}"
        if note:
            event_note += f"; note={note}"
        _insert_equipment_event_with_cur(
            cur,
            equipment_id=eid,
            event_type="return",
            note=event_note,
            operator=actor,
            created_at=now_text,
        )
        return {"returnedAt": now_text}

    tx_result = run_in_transaction(_tx)
    audit_log(
        "equipment.return",
        "equipment",
        eid,
        detail=tx_result,
        actor={"id": actor_id, "username": actor_name, "role": actor_role},
    )
    return jsonify({"ok": True, "data": _find_equipment_or_raise(eid)})


@app.post("/equipments/<int:eid>/transfer")
@auth_required(roles=["admin"])
def transfer_equipment(eid):
    payload = request.get_json(force=True) or {}
    to_lab_id = _to_int_or_none(payload.get("toLabId"))
    if payload.get("toLabId") not in (None, "") and to_lab_id is None:
        raise BizError("invalid toLabId", 400)
    to_lab_name = _normalize_text(payload.get("toLabName"), "toLabName", 128)
    if to_lab_id is not None and not to_lab_name:
        to_lab_name = _resolve_lab_name(to_lab_id)
    if not to_lab_name:
        raise BizError("toLabName required", 400)
    note = _normalize_text(payload.get("note"), "note", 255)

    actor = g.current_user or {}
    actor_id = _safe_int(actor.get("id"))
    actor_name = str(actor.get("username") or "").strip()
    actor_role = str(actor.get("role") or "").strip()
    now_text = _now_text()

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   status,
                   lab_id AS labId,
                   lab_name AS labName
            FROM equipment
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(eid),),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("equipment not found", 404)
        if str(row.get("status") or "").strip() == "scrapped":
            raise BizError("scrapped equipment cannot be transferred", 409)

        old_lab_id = _safe_int(row.get("labId"))
        old_lab_name = str(row.get("labName") or "").strip()
        if old_lab_id == to_lab_id and old_lab_name == to_lab_name:
            return {"changed": False, "fromLab": old_lab_name, "toLab": to_lab_name}

        cur.execute(
            """
            UPDATE equipment
            SET lab_id=%s,
                lab_name=%s,
                last_transfer_from_lab_id=%s,
                last_transfer_from_lab_name=%s,
                last_transfer_at=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (to_lab_id, to_lab_name, old_lab_id, old_lab_name, now_text, now_text, int(eid)),
        )

        event_note = f"from={old_lab_name or '-'}; to={to_lab_name}"
        if note:
            event_note += f"; note={note}"
        _insert_equipment_event_with_cur(
            cur,
            equipment_id=eid,
            event_type="transfer",
            note=event_note,
            operator=actor,
            created_at=now_text,
        )
        return {"changed": True, "fromLab": old_lab_name, "toLab": to_lab_name}

    tx_result = run_in_transaction(_tx)
    audit_log(
        "equipment.transfer",
        "equipment",
        eid,
        detail=tx_result,
        actor={"id": actor_id, "username": actor_name, "role": actor_role},
    )
    return jsonify({"ok": True, "data": _find_equipment_or_raise(eid), "meta": tx_result})


@app.post("/equipments/<int:eid>/maintenance-plan")
@auth_required(roles=["admin"])
def update_equipment_maintenance_plan(eid):
    _find_equipment_or_raise(eid)
    payload = request.get_json(force=True) or {}
    if not isinstance(payload, dict):
        raise BizError("invalid payload", 400)

    sets = []
    params = []
    changed_fields = {}

    if "nextMaintenanceAt" in payload:
        next_maintenance_at = _normalize_datetime_text(payload.get("nextMaintenanceAt"), "nextMaintenanceAt", allow_empty=True)
        sets.append("next_maintenance_at=%s")
        params.append(next_maintenance_at)
        changed_fields["nextMaintenanceAt"] = next_maintenance_at or ""

    if "maintenanceCycleDays" in payload:
        cycle_days = _normalize_positive_int(payload.get("maintenanceCycleDays"), "maintenanceCycleDays", 1, 3650)
        sets.append("maintenance_cycle_days=%s")
        params.append(cycle_days)
        changed_fields["maintenanceCycleDays"] = cycle_days

    if "maintenanceNote" in payload:
        maintenance_note = _normalize_text(payload.get("maintenanceNote"), "maintenanceNote", 255)
        sets.append("maintenance_note=%s")
        params.append(maintenance_note)
        changed_fields["maintenanceNote"] = maintenance_note

    if "warrantyUntil" in payload:
        warranty_until = _normalize_purchase_date(payload.get("warrantyUntil"), field_name="warrantyUntil")
        sets.append("warranty_until=%s")
        params.append(warranty_until)
        changed_fields["warrantyUntil"] = warranty_until or ""

    if "locationNote" in payload:
        location_note = _normalize_text(payload.get("locationNote"), "locationNote", 128)
        sets.append("location_note=%s")
        params.append(location_note)
        changed_fields["locationNote"] = location_note

    if "barcodeValue" in payload:
        barcode_value = _normalize_text(payload.get("barcodeValue"), "barcodeValue", 128)
        sets.append("barcode_value=%s")
        params.append(barcode_value)
        changed_fields["barcodeValue"] = barcode_value

    mark_maintained = _to_bool_flag(payload.get("markMaintained"))
    if mark_maintained:
        sets.append("last_maintained_at=%s")
        params.append(_now_text())
        changed_fields["markMaintained"] = True

    if not sets:
        raise BizError("no fields to update", 400)

    now_text = _now_text()
    sets.append("updated_at=%s")
    params.append(now_text)
    params.append(int(eid))

    execute("UPDATE equipment SET " + ", ".join(sets) + " WHERE id=%s", tuple(params))

    actor = g.current_user or {}
    note = json.dumps(changed_fields, ensure_ascii=False, separators=(",", ":"))
    execute_insert(
        """
        INSERT INTO equipment_event (
            equipment_id, event_type, operator_id, operator_name, note, attachment_url, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            int(eid),
            "maint_plan",
            _to_int_or_none(actor.get("id")),
            str(actor.get("username") or "").strip(),
            note[:1000],
            "",
            now_text,
        ),
    )

    audit_log(
        "equipment.maintenance_plan",
        "equipment",
        eid,
        detail=changed_fields,
        actor={"id": _safe_int(actor.get("id")), "username": str(actor.get("username") or "").strip(), "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": _find_equipment_or_raise(eid)})


@app.get("/equipments/maintenance/due")
@auth_required(roles=["admin"])
def list_due_maintenance_equipments():
    days_raw = request.args.get("days", "30")
    days = _to_int_or_none(days_raw)
    if days is None or days < 0 or days > 3650:
        raise BizError("invalid days", 400)
    limit_raw = request.args.get("limit", "200")
    limit = _to_int_or_none(limit_raw)
    if limit is None or limit < 1 or limit > 500:
        raise BizError("invalid limit", 400)

    now_dt = datetime.now()
    dt_deadline = now_dt + timedelta(days=int(days))
    date_deadline = dt_deadline.strftime("%Y-%m-%d")

    rows = query(
        """
        SELECT id,
               asset_code AS assetCode,
               name,
               lab_id AS labId,
               lab_name AS labName,
               status,
               is_borrowed AS isBorrowed,
               borrowed_by AS borrowedBy,
               next_maintenance_at AS nextMaintenanceAt,
               warranty_until AS warrantyUntil,
               maintenance_cycle_days AS maintenanceCycleDays,
               maintenance_note AS maintenanceNote,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM equipment
        WHERE status<>'scrapped'
          AND (
              (next_maintenance_at IS NOT NULL AND next_maintenance_at<=%s)
              OR (warranty_until IS NOT NULL AND warranty_until<=%s)
          )
        ORDER BY next_maintenance_at ASC, warranty_until ASC, id DESC
        LIMIT %s
        """,
        (dt_deadline.strftime("%Y-%m-%d %H:%M:%S"), date_deadline, int(limit)),
    )
    data = []
    for row in rows:
        item = _format_equipment_row(row)
        due_tags = []
        next_maintenance = _to_datetime(item.get("nextMaintenanceAt"))
        if next_maintenance != datetime.min and next_maintenance <= dt_deadline:
            due_tags.append("maintenance")
        warranty_until = _parse_date_yyyy_mm_dd(item.get("warrantyUntil"))
        if warranty_until and warranty_until.date() <= dt_deadline.date():
            due_tags.append("warranty")
        item["dueTags"] = due_tags
        data.append(item)
    return jsonify({"ok": True, "data": data, "meta": {"days": int(days), "count": len(data)}})


@app.get("/equipments/<int:eid>/code")
@auth_required(roles=["admin"])
def get_equipment_code_payload(eid):
    equipment = _find_equipment_or_raise(eid)
    token = _ensure_equipment_qr_token(eid)
    barcode_value = str(equipment.get("barcodeValue") or "").strip() or str(equipment.get("assetCode") or "").strip()
    if not barcode_value:
        raise BizError("assetCode required for barcode", 409)
    if barcode_value != str(equipment.get("barcodeValue") or "").strip():
        execute("UPDATE equipment SET barcode_value=%s WHERE id=%s", (barcode_value, int(eid)))
        equipment = _find_equipment_or_raise(eid)
    qr_text = f"LAB-ASSET:{token}"
    return jsonify(
        {
            "ok": True,
            "data": {
                "equipmentId": int(equipment.get("id") or 0),
                "assetCode": str(equipment.get("assetCode") or ""),
                "name": str(equipment.get("name") or ""),
                "labName": str(equipment.get("labName") or ""),
                "locationNote": str(equipment.get("locationNote") or ""),
                "qrToken": token,
                "qrText": qr_text,
                "barcodeValue": barcode_value,
            },
        }
    )


@app.get("/equipments/scan")
@auth_required()
def locate_equipment_by_scan_code():
    code = str(request.args.get("code") or "").strip()
    if not code:
        raise BizError("code required", 400)
    eid = _find_equipment_id_by_scan_code(code)
    row = _find_equipment_or_raise(eid)
    return jsonify({"ok": True, "data": row})


@app.post("/equipments/inventory-sessions")
@auth_required(roles=["admin"])
def create_inventory_session():
    payload = request.get_json(force=True) or {}
    lab_id = _to_int_or_none(payload.get("labId"))
    if payload.get("labId") not in (None, "") and lab_id is None:
        raise BizError("invalid labId", 400)
    lab_name = _normalize_text(payload.get("labName"), "labName", 128)
    if lab_id is not None and not lab_name:
        lab_name = _resolve_lab_name(lab_id)
    note = _normalize_text(payload.get("note"), "note", 255)

    actor = g.current_user or {}
    actor_name = str(actor.get("username") or "").strip()
    if not actor_name:
        raise BizError("unauthorized", 401)

    now_text = _now_text()
    inventory_no = _build_inventory_no()

    def _tx(cur):
        cur.execute(
            """
            INSERT INTO equipment_inventory_session (
                inventory_no, lab_id, lab_name, status,
                planned_count, checked_count, diff_count,
                started_by, started_at, note, created_at, updated_at
            ) VALUES (%s, %s, %s, 'open', 0, 0, 0, %s, %s, %s, %s, %s)
            """,
            (inventory_no, lab_id, lab_name, actor_name, now_text, note, now_text, now_text),
        )
        session_id = int(cur.lastrowid or 0)

        where_sql = " WHERE 1=1"
        params = []
        if lab_id is not None:
            where_sql += " AND lab_id=%s"
            params.append(lab_id)
        elif lab_name:
            where_sql += " AND lab_name=%s"
            params.append(lab_name)

        cur.execute(
            """
            SELECT id AS equipmentId,
                   asset_code AS assetCode,
                   name,
                   lab_id AS labId,
                   lab_name AS labName
            FROM equipment
            """
            + where_sql
            + " ORDER BY id ASC",
            tuple(params),
        )
        rows = cur.fetchall() or []
        planned = 0
        for eq in rows:
            asset_code = str(eq.get("assetCode") or "").strip()
            if not asset_code:
                continue
            planned += 1
            cur.execute(
                """
                INSERT INTO equipment_inventory_item (
                    session_id, equipment_id, asset_code, equipment_name,
                    expected_lab_id, expected_lab_name,
                    scan_status, discrepancy_type,
                    scanned_by, scanned_at, note, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, 'pending', '', '', NULL, '', %s, %s)
                """,
                (
                    session_id,
                    _safe_int(eq.get("equipmentId")),
                    asset_code,
                    str(eq.get("name") or "").strip(),
                    _safe_int(eq.get("labId")),
                    str(eq.get("labName") or "").strip(),
                    now_text,
                    now_text,
                ),
            )

        cur.execute(
            """
            UPDATE equipment_inventory_session
            SET planned_count=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (planned, now_text, session_id),
        )
        return {"sessionId": session_id, "plannedCount": planned}

    tx_result = run_in_transaction(_tx)
    session_id = int(tx_result.get("sessionId") or 0)

    audit_log(
        "equipment.inventory.start",
        "equipment_inventory_session",
        session_id,
        detail={
            "inventoryNo": inventory_no,
            "labId": lab_id,
            "labName": lab_name,
            "plannedCount": int(tx_result.get("plannedCount") or 0),
        },
        actor={"id": _safe_int(actor.get("id")), "username": actor_name, "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": _get_inventory_session_or_raise(session_id)})


@app.get("/equipments/inventory-sessions")
@auth_required(roles=["admin"])
def list_inventory_sessions():
    status = str(request.args.get("status") or "").strip().lower()
    if status and status not in INVENTORY_SESSION_STATUS_SET:
        raise BizError("invalid status", 400)

    lab_id = _to_int_or_none(request.args.get("labId"))
    if request.args.get("labId", "") not in (None, "") and lab_id is None:
        raise BizError("invalid labId", 400)

    page, page_size, offset = _parse_page_and_size(request.args.get("page", "1"), request.args.get("pageSize", "20"))
    where_sql = " WHERE 1=1"
    params = []
    if status:
        where_sql += " AND status=%s"
        params.append(status)
    if lab_id is not None:
        where_sql += " AND lab_id=%s"
        params.append(lab_id)

    total_rows = query("SELECT COUNT(*) AS cnt FROM equipment_inventory_session" + where_sql, tuple(params))
    total = int((total_rows[0] or {}).get("cnt") or 0) if total_rows else 0

    rows = query(
        """
        SELECT id,
               inventory_no AS inventoryNo,
               lab_id AS labId,
               lab_name AS labName,
               status,
               planned_count AS plannedCount,
               checked_count AS checkedCount,
               diff_count AS diffCount,
               started_by AS startedBy,
               started_at AS startedAt,
               closed_by AS closedBy,
               closed_at AS closedAt,
               note,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM equipment_inventory_session
        """
        + where_sql
        + " ORDER BY id DESC LIMIT %s OFFSET %s",
        tuple(list(params) + [page_size, offset]),
    )
    data = [_format_inventory_session_row(row) for row in rows]
    return jsonify({"ok": True, "data": data, "meta": {"page": page, "pageSize": page_size, "total": total}})


@app.get("/equipments/inventory-sessions/<int:sid>")
@auth_required(roles=["admin"])
def get_inventory_session_detail(sid):
    session = _get_inventory_session_or_raise(sid)
    status = str(request.args.get("itemStatus") or "").strip().lower()
    if status and status not in INVENTORY_ITEM_STATUS_SET:
        raise BizError("invalid itemStatus", 400)
    diff_only = _to_bool_flag(request.args.get("diffOnly"))
    keyword = str(request.args.get("keyword") or "").strip()

    page, page_size, offset = _parse_page_and_size(request.args.get("page", "1"), request.args.get("pageSize", "20"))
    where_sql = " WHERE session_id=%s"
    params = [int(sid)]
    if status:
        where_sql += " AND scan_status=%s"
        params.append(status)
    if diff_only:
        where_sql += " AND discrepancy_type<>''"
    if keyword:
        where_sql += " AND (asset_code LIKE %s OR equipment_name LIKE %s OR expected_lab_name LIKE %s OR scanned_lab_name LIKE %s)"
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw, kw])

    total_rows = query("SELECT COUNT(*) AS cnt FROM equipment_inventory_item" + where_sql, tuple(params))
    total = int((total_rows[0] or {}).get("cnt") or 0) if total_rows else 0

    rows = query(
        """
        SELECT id,
               session_id AS sessionId,
               equipment_id AS equipmentId,
               asset_code AS assetCode,
               equipment_name AS equipmentName,
               expected_lab_id AS expectedLabId,
               expected_lab_name AS expectedLabName,
               scanned_lab_id AS scannedLabId,
               scanned_lab_name AS scannedLabName,
               scan_status AS scanStatus,
               discrepancy_type AS discrepancyType,
               scanned_by AS scannedBy,
               scanned_at AS scannedAt,
               note,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM equipment_inventory_item
        """
        + where_sql
        + " ORDER BY id DESC LIMIT %s OFFSET %s",
        tuple(list(params) + [page_size, offset]),
    )
    items = [_format_inventory_item_row(row) for row in rows]
    return jsonify(
        {
            "ok": True,
            "data": {"session": session, "items": items},
            "meta": {"page": page, "pageSize": page_size, "total": total},
        }
    )


@app.post("/equipments/inventory-sessions/<int:sid>/scan")
@auth_required(roles=["admin"])
def scan_inventory_session_item(sid):
    payload = request.get_json(force=True) or {}
    code = str(payload.get("code") or "").strip()
    if not code:
        raise BizError("code required", 400)
    note = _normalize_text(payload.get("note"), "note", 255)

    actor = g.current_user or {}
    actor_name = str(actor.get("username") or "").strip()
    if not actor_name:
        raise BizError("unauthorized", 401)
    now_text = _now_text()
    target_eid = _find_equipment_id_by_scan_code(code)

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   inventory_no AS inventoryNo,
                   status
            FROM equipment_inventory_session
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(sid),),
        )
        session = cur.fetchone()
        if not session:
            raise BizError("inventory session not found", 404)
        if str(session.get("status") or "").strip() != "open":
            raise BizError("inventory session already closed", 409)

        cur.execute(
            """
            SELECT id,
                   asset_code AS assetCode,
                   name,
                   status,
                   lab_id AS labId,
                   lab_name AS labName
            FROM equipment
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(target_eid),),
        )
        equipment = cur.fetchone()
        if not equipment:
            raise BizError("equipment not found", 404)

        asset_code = str(equipment.get("assetCode") or "").strip()
        cur.execute(
            """
            SELECT id,
                   expected_lab_id AS expectedLabId,
                   expected_lab_name AS expectedLabName,
                   scan_status AS scanStatus,
                   discrepancy_type AS discrepancyType,
                   scanned_at AS scannedAt
            FROM equipment_inventory_item
            WHERE session_id=%s AND asset_code=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(sid), asset_code),
        )
        item = cur.fetchone()

        scan_status = "matched"
        discrepancy = ""

        if str(equipment.get("status") or "").strip() == "scrapped":
            scan_status = "scrapped"
            discrepancy = "scrapped"

        if item:
            if item.get("scannedAt"):
                result = {
                    "itemId": int(item.get("id") or 0),
                    "assetCode": asset_code,
                    "scanStatus": str(item.get("scanStatus") or ""),
                    "discrepancyType": str(item.get("discrepancyType") or ""),
                    "duplicate": True,
                }
                stats = _refresh_inventory_session_stats_with_cur(cur, sid)
                result["stats"] = stats
                return result

            expected_lab_id = _safe_int(item.get("expectedLabId"))
            expected_lab_name = str(item.get("expectedLabName") or "").strip()
            scanned_lab_id = _safe_int(equipment.get("labId"))
            scanned_lab_name = str(equipment.get("labName") or "").strip()

            if scan_status != "scrapped":
                if expected_lab_id is not None and scanned_lab_id is not None and expected_lab_id != scanned_lab_id:
                    scan_status = "moved"
                    discrepancy = "lab_mismatch"
                elif expected_lab_name and scanned_lab_name and expected_lab_name != scanned_lab_name:
                    scan_status = "moved"
                    discrepancy = "lab_mismatch"

            cur.execute(
                """
                UPDATE equipment_inventory_item
                SET equipment_id=%s,
                    equipment_name=%s,
                    scanned_lab_id=%s,
                    scanned_lab_name=%s,
                    scan_status=%s,
                    discrepancy_type=%s,
                    scanned_by=%s,
                    scanned_at=%s,
                    note=%s,
                    updated_at=%s
                WHERE id=%s
                """,
                (
                    int(target_eid),
                    str(equipment.get("name") or "").strip(),
                    scanned_lab_id,
                    scanned_lab_name,
                    scan_status,
                    discrepancy,
                    actor_name,
                    now_text,
                    note,
                    now_text,
                    int(item.get("id") or 0),
                ),
            )
            item_id = int(item.get("id") or 0)
        else:
            if scan_status != "scrapped":
                scan_status = "unexpected"
                discrepancy = "unexpected"
            cur.execute(
                """
                INSERT INTO equipment_inventory_item (
                    session_id, equipment_id, asset_code, equipment_name,
                    expected_lab_id, expected_lab_name,
                    scanned_lab_id, scanned_lab_name,
                    scan_status, discrepancy_type,
                    scanned_by, scanned_at, note, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, NULL, '', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    int(sid),
                    int(target_eid),
                    asset_code,
                    str(equipment.get("name") or "").strip(),
                    _safe_int(equipment.get("labId")),
                    str(equipment.get("labName") or "").strip(),
                    scan_status,
                    discrepancy,
                    actor_name,
                    now_text,
                    note,
                    now_text,
                    now_text,
                ),
            )
            item_id = int(cur.lastrowid or 0)

        _insert_equipment_event_with_cur(
            cur,
            equipment_id=target_eid,
            event_type="inventory",
            note=f"session={session.get('inventoryNo')}; status={scan_status}; diff={discrepancy or '-'}",
            operator=actor,
            created_at=now_text,
        )

        stats = _refresh_inventory_session_stats_with_cur(cur, sid)
        return {
            "itemId": item_id,
            "equipmentId": int(target_eid),
            "assetCode": asset_code,
            "scanStatus": scan_status,
            "discrepancyType": discrepancy,
            "duplicate": False,
            "stats": stats,
        }

    tx_result = run_in_transaction(_tx)
    audit_log(
        "equipment.inventory.scan",
        "equipment_inventory_session",
        sid,
        detail={
            "assetCode": tx_result.get("assetCode"),
            "scanStatus": tx_result.get("scanStatus"),
            "discrepancyType": tx_result.get("discrepancyType"),
            "duplicate": bool(tx_result.get("duplicate")),
        },
        actor={"id": _safe_int(actor.get("id")), "username": actor_name, "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": tx_result})


@app.post("/equipments/inventory-sessions/<int:sid>/close")
@auth_required(roles=["admin"])
def close_inventory_session(sid):
    actor = g.current_user or {}
    actor_name = str(actor.get("username") or "").strip()
    if not actor_name:
        raise BizError("unauthorized", 401)
    now_text = _now_text()

    def _tx(cur):
        cur.execute(
            """
            SELECT id, status, inventory_no AS inventoryNo
            FROM equipment_inventory_session
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (int(sid),),
        )
        session = cur.fetchone()
        if not session:
            raise BizError("inventory session not found", 404)

        if str(session.get("status") or "").strip() == "closed":
            stats = _refresh_inventory_session_stats_with_cur(cur, sid)
            return {"closed": False, "stats": stats, "inventoryNo": session.get("inventoryNo")}

        cur.execute(
            """
            UPDATE equipment_inventory_item
            SET scan_status='missing',
                discrepancy_type='missing',
                note=CASE WHEN note='' THEN 'not scanned before closing' ELSE note END,
                updated_at=%s
            WHERE session_id=%s AND scan_status='pending'
            """,
            (now_text, int(sid)),
        )

        stats = _refresh_inventory_session_stats_with_cur(cur, sid)
        cur.execute(
            """
            UPDATE equipment_inventory_session
            SET status='closed',
                closed_by=%s,
                closed_at=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (actor_name, now_text, now_text, int(sid)),
        )
        return {"closed": True, "stats": stats, "inventoryNo": session.get("inventoryNo")}

    tx_result = run_in_transaction(_tx)
    audit_log(
        "equipment.inventory.close",
        "equipment_inventory_session",
        sid,
        detail=tx_result,
        actor={"id": _safe_int(actor.get("id")), "username": actor_name, "role": actor.get("role")},
    )
    return jsonify({"ok": True, "data": _get_inventory_session_or_raise(sid), "meta": tx_result})


@app.get("/equipments/inventory-sessions/<int:sid>/diffs")
@auth_required(roles=["admin"])
def list_inventory_session_diffs(sid):
    _get_inventory_session_or_raise(sid)
    rows = query(
        """
        SELECT id,
               session_id AS sessionId,
               equipment_id AS equipmentId,
               asset_code AS assetCode,
               equipment_name AS equipmentName,
               expected_lab_id AS expectedLabId,
               expected_lab_name AS expectedLabName,
               scanned_lab_id AS scannedLabId,
               scanned_lab_name AS scannedLabName,
               scan_status AS scanStatus,
               discrepancy_type AS discrepancyType,
               scanned_by AS scannedBy,
               scanned_at AS scannedAt,
               note,
               created_at AS createdAt,
               updated_at AS updatedAt
        FROM equipment_inventory_item
        WHERE session_id=%s AND discrepancy_type<>''
        ORDER BY id DESC
        LIMIT 500
        """,
        (int(sid),),
    )
    data = [_format_inventory_item_row(row) for row in rows]
    return jsonify({"ok": True, "data": data, "meta": {"count": len(data)}})


@app.post("/repair-orders")
@auth_required()
def create_repair_order():
    payload = request.get_json(force=True) or {}
    current_user = g.current_user or {}
    submitter_id = _safe_int(current_user.get("id"))
    submitter_name = str(current_user.get("username") or "").strip()
    if not submitter_name:
        raise BizError("unauthorized", 401)

    issue_type = _normalize_repair_issue_type(payload.get("issueType"))
    description = _normalize_repair_description(payload.get("description"))
    attachment_url = _normalize_repair_attachment_url(payload.get("attachmentUrl"))
    attachment_ocr_text = _normalize_text(payload.get("ocrText"), "ocrText", 1000)
    attachments = _normalize_repair_attachments_payload(payload.get("attachments"))
    if attachment_url and not any(str(item.get("url") or "").strip() == attachment_url for item in attachments):
        attachments.insert(
            0,
            {
                "url": attachment_url,
                "name": _normalize_text(payload.get("attachmentName") or os.path.basename(attachment_url), "attachmentName", 200),
                "fileType": "image",
                "mimeType": "",
                "ocrText": attachment_ocr_text,
            },
        )
    if not attachment_url and attachments:
        attachment_url = _normalize_repair_attachment_url((attachments[0] or {}).get("url"))

    equipment_id = _to_int_or_none(payload.get("equipmentId"))
    if payload.get("equipmentId") not in (None, "") and equipment_id is None:
        raise BizError("invalid equipmentId", 400)

    lab_id = _to_int_or_none(payload.get("labId"))
    if payload.get("labId") not in (None, "") and lab_id is None:
        raise BizError("invalid labId", 400)
    lab_name = str(payload.get("labName") or "").strip()

    asset_code = ""
    equipment_name = ""
    equipment_status = ""
    lab_status = ""
    if equipment_id:
        equipment = _find_equipment_or_raise(equipment_id)
        equipment_id = _safe_int(equipment.get("id"))
        asset_code = str(equipment.get("assetCode") or "").strip()
        equipment_name = str(equipment.get("name") or "").strip()
        equipment_status = str(equipment.get("status") or "").strip()
        lab_id = _safe_int(equipment.get("labId"))
        lab_name = str(equipment.get("labName") or "").strip() or lab_name
    else:
        equipment_id = None
        if lab_id is not None and not lab_name:
            lab_name = _resolve_lab_name(lab_id)

    equipment_meta = {
        "id": equipment_id,
        "assetCode": asset_code,
        "name": equipment_name,
        "status": equipment_status,
        "issueTypeHint": issue_type,
    }
    lab_meta = {
        "id": lab_id,
        "name": lab_name,
        "status": lab_status,
    }
    history_context = _build_repair_history_context(equipment_id=equipment_id, lab_id=lab_id, limit=4)
    triage_result = ai_triage_repair(
        description,
        equipment_meta=equipment_meta,
        lab_meta=lab_meta,
        attachments=attachments,
        history_context=history_context,
    )
    ai_payload = _normalize_ai_triage_payload(triage_result, fallback_issue_type=issue_type)

    new_id = _create_repair_order_record(
        submitter_id=submitter_id,
        submitter_name=submitter_name,
        equipment_id=equipment_id,
        asset_code=asset_code,
        equipment_name=equipment_name,
        lab_id=lab_id,
        lab_name=lab_name,
        issue_type=issue_type,
        description=description,
        attachment_url=attachment_url,
        ai_issue_type=ai_payload.get("issueType"),
        ai_fault_part=ai_payload.get("faultPart"),
        ai_priority=ai_payload.get("priority"),
        ai_summary=ai_payload.get("summary"),
        ai_possible_causes_text=ai_payload.get("possibleCausesText"),
        ai_suggestions_text=ai_payload.get("suggestionsText"),
        ai_confidence=ai_payload.get("confidence"),
        ai_ocr_text=ai_payload.get("ocrSummary"),
        ai_model_name=ai_payload.get("modelName"),
        ai_raw_json=ai_payload.get("rawJson"),
    )
    saved_attachments = _save_repair_attachments(new_id, attachments)
    _log_repair_ai_diagnosis(
        work_order_id=new_id,
        equipment_id=equipment_id,
        lab_id=lab_id,
        user_id=submitter_id,
        input_text=description,
        attachments=saved_attachments,
        ai_payload=ai_payload,
        fallback=float(ai_payload.get("confidence") or 0) < 0.45,
    )
    audit_log(
        "repair_order.create",
        "repair_work_order",
        new_id,
        detail={
            "issueType": issue_type,
            "equipmentId": equipment_id,
            "labId": lab_id,
            "ai_issue_type": ai_payload.get("issueType"),
            "ai_fault_part": ai_payload.get("faultPart"),
            "ai_priority": ai_payload.get("priority"),
        },
        actor={"id": submitter_id, "username": submitter_name, "role": current_user.get("role")},
    )
    row = _format_repair_order_row(_get_repair_order_or_raise(new_id))
    row["attachments"] = _get_repair_attachment_rows(new_id)
    response_ai = row.get("ai") if isinstance(row.get("ai"), dict) else {
        "issueType": ai_payload.get("issueType"),
        "faultPart": ai_payload.get("faultPart"),
        "priority": ai_payload.get("priority"),
        "summary": ai_payload.get("summary"),
        "possibleCauses": ai_payload.get("possibleCauses"),
        "suggestions": ai_payload.get("suggestions"),
        "confidence": ai_payload.get("confidence"),
        "ocrText": ai_payload.get("ocrSummary"),
        "modelName": ai_payload.get("modelName"),
        "rawJson": ai_payload.get("rawJson"),
    }
    return jsonify({"ok": True, "data": row, "order": row, "ai": response_ai})


@app.get("/repair-orders")
@auth_required()
def list_repair_orders():
    current_user = g.current_user or {}
    current_role = str(current_user.get("role") or "").strip()
    current_name = str(current_user.get("username") or "").strip()

    page, page_size, offset = _parse_page_and_size(
        request.args.get("page", "1"),
        request.args.get("pageSize", "20"),
    )
    status = str(request.args.get("status") or "").strip().lower()
    if status and status not in REPAIR_ORDER_STATUS_SET:
        raise BizError("invalid status", 400)
    issue_type = str(request.args.get("issueType") or "").strip()
    if issue_type:
        issue_type = _normalize_repair_issue_type(issue_type)
    keyword = str(request.args.get("keyword") or "").strip()

    equipment_id = _to_int_or_none(request.args.get("equipmentId"))
    if request.args.get("equipmentId", "") not in (None, "") and equipment_id is None:
        raise BizError("invalid equipmentId", 400)
    lab_id = _to_int_or_none(request.args.get("labId"))
    if request.args.get("labId", "") not in (None, "") and lab_id is None:
        raise BizError("invalid labId", 400)

    where_sql = " WHERE 1=1"
    params = []
    if status:
        where_sql += " AND rwo.status=%s"
        params.append(status)
    if issue_type:
        where_sql += " AND rwo.issue_type=%s"
        params.append(issue_type)
    if equipment_id is not None:
        where_sql += " AND rwo.equipment_id=%s"
        params.append(equipment_id)
    if lab_id is not None:
        where_sql += " AND rwo.lab_id=%s"
        params.append(lab_id)
    if keyword:
        where_sql += (
            " AND (rwo.order_no LIKE %s OR rwo.description LIKE %s OR rwo.lab_name LIKE %s "
            "OR rwo.equipment_name LIKE %s OR rwo.asset_code LIKE %s OR rwo.submitter_name LIKE %s OR rwo.assignee_name LIKE %s)"
        )
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw, kw, kw, kw, kw])

    if current_role != "admin":
        where_sql += " AND rwo.submitter_name=%s"
        params.append(current_name)
    elif _to_bool_flag(request.args.get("mine")):
        where_sql += " AND rwo.submitter_name=%s"
        params.append(current_name)

    total_rows = query("SELECT COUNT(*) AS cnt FROM repair_work_order rwo" + where_sql, params)
    total = int((total_rows[0] or {}).get("cnt") or 0) if total_rows else 0

    rows = query(
        _repair_order_select_fragment()
        + where_sql
        + """
          ORDER BY rwo.submitted_at DESC, rwo.id DESC
          LIMIT %s OFFSET %s
        """,
        list(params) + [page_size, offset],
    )
    data = [_format_repair_order_row(row) for row in rows]
    return jsonify(
        {
            "ok": True,
            "data": data,
            "meta": {
                "page": page,
                "pageSize": page_size,
                "total": total,
            },
        }
    )


@app.get("/repair-orders/<int:oid>")
@auth_required()
def get_repair_order_detail(oid):
    row = _get_repair_order_or_raise(oid)
    current_user = g.current_user or {}
    current_role = str(current_user.get("role") or "").strip()
    current_name = str(current_user.get("username") or "").strip()
    if current_role != "admin":
        submitter = str(row.get("submitterName") or "").strip()
        if submitter != current_name:
            raise BizError("forbidden", 403)
    payload = _format_repair_order_row(row)
    payload["attachments"] = _get_repair_attachment_rows(oid)
    return jsonify({"ok": True, "data": payload})


@app.post("/repair-orders/<int:oid>/status")
@auth_required(roles=["admin"])
def update_repair_order_status(oid):
    payload = request.get_json(force=True) or {}
    target_status = str(payload.get("status") or "").strip().lower()
    if target_status not in REPAIR_ORDER_STATUS_SET:
        raise BizError("invalid status", 400)

    assignee_id_input = _to_int_or_none(payload.get("assigneeId"))
    assignee_name_input = str(payload.get("assigneeName") or "").strip()
    actor = g.current_user or {}
    actor_id = _safe_int(actor.get("id"))
    actor_name = str(actor.get("username") or "").strip()
    now_text = _now_text()

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   status,
                   equipment_id AS equipmentId,
                   assignee_id AS assigneeId,
                   assignee_name AS assigneeName
            FROM repair_work_order
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (oid,),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("repair order not found", 404)

        old_status = str(row.get("status") or "").strip()
        if old_status == target_status:
            if target_status in {"accepted", "processing"} and (assignee_id_input is not None or assignee_name_input):
                assignee_id = assignee_id_input if assignee_id_input is not None else _safe_int(row.get("assigneeId"))
                assignee_name = assignee_name_input or str(row.get("assigneeName") or "").strip() or actor_name
                if assignee_id is None:
                    assignee_id = actor_id
                cur.execute(
                    """
                    UPDATE repair_work_order
                    SET assignee_id=%s,
                        assignee_name=%s,
                        updated_at=%s
                    WHERE id=%s
                    """,
                    (assignee_id, assignee_name, now_text, oid),
                )
            return {
                "oldStatus": old_status,
                "newStatus": target_status,
                "equipmentId": _safe_int(row.get("equipmentId")),
                "changed": False,
            }

        expected = REPAIR_ORDER_NEXT_STATUS.get(old_status)
        if expected != target_status:
            raise BizError("invalid status transition", 409)

        assignee_id = _safe_int(row.get("assigneeId"))
        assignee_name = str(row.get("assigneeName") or "").strip()
        if assignee_id_input is not None:
            assignee_id = assignee_id_input
        if assignee_name_input:
            assignee_name = assignee_name_input

        if target_status in {"accepted", "processing"}:
            if assignee_id is None:
                assignee_id = actor_id
            if not assignee_name:
                assignee_name = actor_name

        if target_status == "accepted":
            cur.execute(
                """
                UPDATE repair_work_order
                SET status='accepted',
                    assignee_id=%s,
                    assignee_name=%s,
                    accepted_at=COALESCE(accepted_at, %s),
                    updated_at=%s
                WHERE id=%s
                """,
                (assignee_id, assignee_name, now_text, now_text, oid),
            )
        elif target_status == "processing":
            cur.execute(
                """
                UPDATE repair_work_order
                SET status='processing',
                    assignee_id=%s,
                    assignee_name=%s,
                    accepted_at=COALESCE(accepted_at, %s),
                    processing_at=COALESCE(processing_at, %s),
                    updated_at=%s
                WHERE id=%s
                """,
                (assignee_id, assignee_name, now_text, now_text, now_text, oid),
            )
        elif target_status == "completed":
            cur.execute(
                """
                UPDATE repair_work_order
                SET status='completed',
                    completed_at=COALESCE(completed_at, %s),
                    updated_at=%s
                WHERE id=%s
                """,
                (now_text, now_text, oid),
            )

        equipment_id = _safe_int(row.get("equipmentId"))
        if equipment_id is not None:
            if target_status in {"accepted", "processing"}:
                cur.execute(
                    """
                    UPDATE equipment
                    SET status='repairing'
                    WHERE id=%s AND status<>'scrapped'
                    """,
                    (equipment_id,),
                )
            elif target_status == "completed":
                cur.execute(
                    """
                    UPDATE equipment
                    SET status='in_service'
                    WHERE id=%s AND status='repairing'
                    """,
                    (equipment_id,),
                )

        return {
            "oldStatus": old_status,
            "newStatus": target_status,
            "equipmentId": equipment_id,
            "changed": True,
        }

    result = run_in_transaction(_tx)
    audit_log(
        "repair_order.status.update",
        "repair_work_order",
        oid,
        detail={
            "fromStatus": result.get("oldStatus"),
            "toStatus": result.get("newStatus"),
            "equipmentId": result.get("equipmentId"),
            "changed": bool(result.get("changed")),
        },
        actor={"id": actor_id, "username": actor_name, "role": actor.get("role")},
    )
    row = _format_repair_order_row(_get_repair_order_or_raise(oid))
    return jsonify({"ok": True, "data": row})


@app.post("/repair-orders/<int:oid>/followup")
@auth_required()
def followup_repair_order(oid):
    payload = request.get_json(force=True) or {}
    score = _to_int_or_none(payload.get("score"))
    if payload.get("score") not in (None, "") and (score is None or score < 1 or score > 5):
        raise BizError("invalid score", 400)
    comment = str(payload.get("comment") or "").strip()
    if len(comment) > 500:
        raise BizError("comment too long", 400)

    actor = g.current_user or {}
    actor_role = str(actor.get("role") or "").strip()
    actor_name = str(actor.get("username") or "").strip()
    actor_id = _safe_int(actor.get("id"))
    now_text = _now_text()

    def _tx(cur):
        cur.execute(
            """
            SELECT id,
                   status,
                   submitter_name AS submitterName
            FROM repair_work_order
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (oid,),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("repair order not found", 404)
        status = str(row.get("status") or "").strip()
        if status != "completed":
            raise BizError("repair order not completed", 409)

        submitter_name = str(row.get("submitterName") or "").strip()
        if actor_role != "admin" and submitter_name != actor_name:
            raise BizError("forbidden", 403)

        cur.execute(
            """
            UPDATE repair_work_order
            SET followup_score=%s,
                followup_comment=%s,
                followup_at=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (score, comment, now_text, now_text, oid),
        )
        return True

    run_in_transaction(_tx)
    audit_log(
        "repair_order.followup",
        "repair_work_order",
        oid,
        detail={"score": score, "hasComment": bool(comment)},
        actor={"id": actor_id, "username": actor_name, "role": actor_role},
    )
    row = _format_repair_order_row(_get_repair_order_or_raise(oid))
    return jsonify({"ok": True, "data": row})


def _csv_pick(row, header_map, key):
    col_name = header_map.get(key)
    if not col_name:
        return ""
    return str(row.get(col_name) or "").strip()


def _repair_issue_type_label(issue_type):
    text = str(issue_type or "").strip().lower()
    if text == "computer":
        return "电脑问题"
    if text == "lighting":
        return "电灯问题"
    if text == "floor":
        return "地板问题"
    if text == "network":
        return "网络问题"
    return "其他问题"


def _repair_issue_type_from_attachment_name(raw_name):
    name = str(raw_name or "").strip().lower()
    if not name:
        return ""
    if any(token in name for token in ("screen", "monitor", "display", "host", "pc", "computer", "蓝屏", "黑屏", "死机")):
        return "computer"
    if any(token in name for token in ("light", "lamp", "lighting", "灯", "照明")):
        return "lighting"
    if any(token in name for token in ("floor", "tile", "ground", "地板", "瓷砖")):
        return "floor"
    if any(token in name for token in ("network", "net", "wifi", "router", "网络", "断网")):
        return "network"
    return ""


@app.post("/repair-orders/ai-diagnose")
@auth_required()
def repair_order_ai_diagnose():
    payload = request.get_json(force=True) or {}
    current_user = g.current_user or {}
    description = str(payload.get("description") or "").strip()
    attachment_url = _normalize_repair_attachment_url(payload.get("attachmentUrl"))
    attachment_name = str(payload.get("attachmentName") or "").strip()
    attachment_ocr_text = _normalize_text(payload.get("ocrText"), "ocrText", 1000)
    attachments = _normalize_repair_attachments_payload(payload.get("attachments"))
    if attachment_url and not any(str(item.get("url") or "").strip() == attachment_url for item in attachments):
        attachments.insert(
            0,
            {
                "url": attachment_url,
                "name": attachment_name or os.path.basename(str(attachment_url or "").strip()),
                "fileType": "image",
                "mimeType": "",
                "ocrText": attachment_ocr_text,
            },
        )
    issue_hint = str(payload.get("issueType") or "").strip().lower()
    fallback_issue = issue_hint if issue_hint in REPAIR_ISSUE_TYPE_SET else "other"

    if not description and not attachment_url and not attachment_name and not attachments:
        raise BizError("description or attachment required", 400)

    equipment_id = _to_int_or_none(payload.get("equipmentId"))
    if payload.get("equipmentId") not in (None, "") and equipment_id is None:
        raise BizError("invalid equipmentId", 400)

    lab_id = _to_int_or_none(payload.get("labId"))
    if payload.get("labId") not in (None, "") and lab_id is None:
        raise BizError("invalid labId", 400)

    equipment_meta = {}
    lab_meta = {
        "id": lab_id,
        "name": str(payload.get("labName") or "").strip(),
        "issueTypeHint": fallback_issue,
    }
    if equipment_id:
        equipment = _find_equipment_or_raise(equipment_id)
        equipment_meta = {
            "id": _safe_int(equipment.get("id")),
            "assetCode": str(equipment.get("assetCode") or "").strip(),
            "name": str(equipment.get("name") or "").strip(),
            "status": str(equipment.get("status") or "").strip(),
            "issueTypeHint": fallback_issue,
        }
        lab_meta["id"] = _safe_int(equipment.get("labId"))
        lab_meta["name"] = str(equipment.get("labName") or "").strip() or lab_meta.get("name")

    attachment_names = [attachment_name or os.path.basename(str(attachment_url or "").strip())]
    attachment_names.extend([str(item.get("name") or "").strip() for item in attachments if str(item.get("name") or "").strip()])
    attachment_hint = ""
    for item_name in attachment_names:
        attachment_hint = _repair_issue_type_from_attachment_name(item_name)
        if attachment_hint:
            break
    diagnose_desc = description
    if attachment_hint:
        diagnose_desc = (diagnose_desc + f"\n附件线索：{_repair_issue_type_label(attachment_hint)}").strip()
    if attachment_ocr_text:
        diagnose_desc = (diagnose_desc + f"\nOCR线索：{attachment_ocr_text}").strip()

    history_context = _build_repair_history_context(equipment_id=equipment_id, lab_id=lab_id, limit=4)
    triage = ai_triage_repair(
        diagnose_desc,
        equipment_meta=equipment_meta,
        lab_meta=lab_meta,
        attachments=attachments,
        history_context=history_context,
    )
    normalized = _normalize_ai_triage_payload(triage, fallback_issue_type=attachment_hint or fallback_issue)

    if attachment_hint and normalized.get("confidence", 0) < 0.55:
        normalized["issueType"] = attachment_hint
        normalized["confidence"] = max(float(normalized.get("confidence") or 0), 0.38)

    suggestions = list(normalized.get("suggestions") or [])
    if not suggestions:
        suggestions = [
            "保留现场照片并补充故障出现时间、频率和影响范围。",
            "若影响上课，请先联系管理员安排人工排查或更换设备。",
        ]
    if attachment_url:
        suggestions.insert(0, "已记录附图，可连同描述一并提交正式报修。")
    normalized["suggestions"] = suggestions[:5]

    fallback = float(normalized.get("confidence") or 0) < 0.45
    summary = str(normalized.get("summary") or "").strip()
    if not summary:
        summary = f"AI 预判为{_repair_issue_type_label(normalized.get('issueType'))}，优先级 {normalized.get('priority') or 'P2'}。"
    if fallback:
        summary += " 当前置信度较低，建议补充描述或转人工确认。"
    normalized["summary"] = summary
    _log_repair_ai_diagnosis(
        work_order_id=None,
        equipment_id=equipment_id,
        lab_id=lab_id,
        user_id=_safe_int(current_user.get("id")),
        input_text=diagnose_desc,
        attachments=attachments,
        ai_payload=normalized,
        fallback=fallback,
    )

    return jsonify(
        {
            "ok": True,
            "data": {
                "issueType": normalized.get("issueType"),
                "issueTypeLabel": _repair_issue_type_label(normalized.get("issueType")),
                "faultPart": normalized.get("faultPart"),
                "priority": normalized.get("priority"),
                "confidence": normalized.get("confidence"),
                "summary": summary,
                "possibleCauses": normalized.get("possibleCauses") or [],
                "ocrSummary": normalized.get("ocrSummary") or "",
                "suggestions": normalized.get("suggestions"),
                "modelName": normalized.get("modelName") or "",
                "fallback": fallback,
                "usedAttachment": bool(attachment_url or attachment_name or attachments),
            },
        }
    )


@app.post("/equipments/import")
@auth_required(roles=["admin"])
def import_equipments_csv():
    if "file" not in request.files:
        raise BizError("file required", 400)
    f = request.files["file"]
    if not f.filename:
        raise BizError("filename required", 400)

    raw = f.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise BizError("csv must be utf-8 encoded", 400)

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise BizError("csv header required", 400)

    header_map = {}
    for col in reader.fieldnames:
        key = str(col or "").strip().lower()
        if key and key not in header_map:
            header_map[key] = col

    required_headers = {"asset_code", "name"}
    if any(h not in header_map for h in required_headers):
        raise BizError("csv missing required headers: asset_code,name", 400)

    inserted = 0
    updated = 0
    failed = 0
    errors = []
    lab_id_cache = {}

    for row_idx, row in enumerate(reader, start=2):
        try:
            asset_code = _csv_pick(row, header_map, "asset_code")
            name = _csv_pick(row, header_map, "name")
            if not asset_code or not name:
                raise BizError("asset_code and name required", 400)

            status = _csv_pick(row, header_map, "status") or "in_service"
            status = _normalize_status(status)
            purchase_date = _normalize_purchase_date(
                _csv_pick(row, header_map, "purchase_date"),
                field_name="purchase_date",
            )
            price = _normalize_price(_csv_pick(row, header_map, "price"), field_name="price")

            model = _csv_pick(row, header_map, "model")
            brand = _csv_pick(row, header_map, "brand")
            lab_name = _csv_pick(row, header_map, "lab_name")
            keeper = _csv_pick(row, header_map, "keeper")
            spec_json = _csv_pick(row, header_map, "spec_json") or None
            image_url = _csv_pick(row, header_map, "image_url")
            allow_borrow_raw = _csv_pick(row, header_map, "allow_borrow") or _csv_pick(row, header_map, "allowborrow")
            allow_borrow_input = _parse_optional_bool(allow_borrow_raw, "allow_borrow")

            lab_id = None
            if lab_name:
                if lab_name in lab_id_cache:
                    lab_id = lab_id_cache[lab_name]
                else:
                    lab_rows = query("SELECT id FROM lab WHERE name=%s LIMIT 1", (lab_name,))
                    if lab_rows:
                        lab_id = int(lab_rows[0]["id"])
                    lab_id_cache[lab_name] = lab_id

            existing = query("SELECT id, allow_borrow AS allowBorrow FROM equipment WHERE asset_code=%s LIMIT 1", (asset_code,))
            if existing:
                equipment_id = int(existing[0]["id"])
                existing_allow_borrow = int(existing[0].get("allowBorrow") if existing[0].get("allowBorrow") not in (None, "") else 1) == 1
                if allow_borrow_input is None:
                    allow_borrow = existing_allow_borrow
                else:
                    allow_borrow = bool(allow_borrow_input)
                execute(
                    """
                    UPDATE equipment
                    SET name=%s,
                        model=%s,
                        brand=%s,
                        lab_id=%s,
                        lab_name=%s,
                        status=%s,
                        keeper=%s,
                        purchase_date=%s,
                        price=%s,
                        spec_json=%s,
                        image_url=%s,
                        allow_borrow=%s
                    WHERE id=%s
                    """,
                    (
                        name,
                        model,
                        brand,
                        lab_id,
                        lab_name,
                        status,
                        keeper,
                        purchase_date,
                        price,
                        spec_json,
                        image_url,
                        1 if allow_borrow else 0,
                        equipment_id,
                    ),
                )
                updated += 1
            else:
                allow_borrow = bool(allow_borrow_input) if allow_borrow_input is not None else not _is_lab_pc_equipment(
                    asset_code=asset_code,
                    name=name,
                    spec_json=spec_json,
                    lab_id=lab_id,
                    lab_name=lab_name,
                )
                created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                execute_insert(
                    """
                    INSERT INTO equipment (
                        asset_code, name, model, brand, lab_id, lab_name,
                        status, keeper, purchase_date, price, spec_json, image_url, allow_borrow, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        asset_code,
                        name,
                        model,
                        brand,
                        lab_id,
                        lab_name,
                        status,
                        keeper,
                        purchase_date,
                        price,
                        spec_json,
                        image_url,
                        1 if allow_borrow else 0,
                        created_at,
                    ),
                )
                inserted += 1
        except BizError as e:
            failed += 1
            errors.append({"row": row_idx, "reason": e.msg})
        except Exception as e:
            failed += 1
            errors.append({"row": row_idx, "reason": str(e)})

    audit_log(
        "equipment.import",
        "equipment",
        detail={"inserted": inserted, "updated": updated, "failed": failed},
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "inserted": inserted,
                "updated": updated,
                "failed": failed,
                "errors": errors,
            },
        }
    )
