import logging

def dedupe_material_ids(course_ids, module_ids, topic_ids):
    """
    Deduplicates material IDs based on hierarchy: topic > module > course.
    Returns (course_deduped, module_deduped, topic_deduped) lists.
    """
    selected = {}
    for cid in (course_ids or []):
        if cid:
            selected[cid] = "course"
    for cid in (module_ids or []):
        if cid:
            selected[cid] = "module"
    for cid in (topic_ids or []):
        if cid:
            selected[cid] = "topic"

    c_out = []
    m_out = []
    t_out = []
    
    added = set()
    for cid in (course_ids or []):
        if selected.get(cid) == "course" and cid not in added:
            c_out.append(cid)
            added.add(cid)
    for cid in (module_ids or []):
        if selected.get(cid) == "module" and cid not in added:
            m_out.append(cid)
            added.add(cid)
    for cid in (topic_ids or []):
        if selected.get(cid) == "topic" and cid not in added:
            t_out.append(cid)
            added.add(cid)

    return c_out, m_out, t_out

def resolve_grounding_context(course, module, topic):
    """
    Collects, deduplicates, and resolves course, module, and topic level material chunks.
    Logs warnings for missing or empty chunk text.
    """
    course_ids = getattr(course, "course_material_ids", []) or []
    module_ids = getattr(module, "module_material_ids", []) or []
    topic_ids = getattr(topic, "topic_material_ids", []) or []

    # Get deduplicated lists preserving order
    c_ids, m_ids, t_ids = dedupe_material_ids(course_ids, module_ids, topic_ids)

    res = {
        "course_chunks": [],
        "module_chunks": [],
        "topic_chunks": [],
        "web_chunks": [],
        "fallback_used": False
    }

    material_bank = getattr(course, "material_bank", {}) or {}

    # Helper to resolve lists
    def resolve_list(ids, level_name):
        for cid in ids:
            text = material_bank.get(cid)
            if text is None:
                logging.warning(f"[Grounding Resolver] Missing material chunk_id: {cid}")
                continue
            if not text.strip():
                logging.warning(f"[Grounding Resolver] Empty material chunk_id: {cid}")
                continue
            res[f"{level_name}_chunks"].append({
                "chunk_id": cid,
                "text": text
            })

    resolve_list(c_ids, "course")
    resolve_list(m_ids, "module")
    resolve_list(t_ids, "topic")

    return res
