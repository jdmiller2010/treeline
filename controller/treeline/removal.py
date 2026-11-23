"""Erasing a treehouse: the one place a family's own "Delete everything" and the end of a staff archive share (docs/DATA_LAYER.md,
"Writes that touch two files": one central transaction first, then the other families' notes, then the household file)."""

from . import db, households


def end_all_strings(c, tid):
    """Cut every string of this treehouse (inside the caller's central transaction). Returns the other families that had a live or
    paused one, to be told afterwards."""
    tell = []
    for st in c.execute("SELECT * FROM string WHERE (a_id=? OR b_id=?) AND state!='cut'", (tid, tid)).fetchall():
        c.execute("UPDATE string SET state='cut', updated_at=? WHERE id=?", (db.iso(), st["id"]))
        if st["state"] in ("live", "paused"):
            tell.append(st["b_id"] if st["a_id"] == tid else st["a_id"])
    return tell


def tell_ended(others, title):
    """After the central change has committed: a crash in between loses a note (harmless); the other order could announce a string
    that was never cut."""
    for other in others:
        households.add_notice(other, "string_ended", title, "The string between your treehouses has ended.")


def erase_central(c, tid):
    """Every central record of the treehouse, in the caller's transaction. Returns the families to tell."""
    tell = end_all_strings(c, tid)
    db.leave_treehouse(c, tid)
    # The ledger keeps rows other families' copies may still be waiting for: only this family's side is scrubbed.
    c.execute("DELETE FROM call_event WHERE call_id IN (SELECT id FROM call WHERE "
              "caller_treehouse=? AND callee_treehouse IS NULL)", (tid,))
    c.execute("DELETE FROM call WHERE (caller_treehouse=? AND callee_treehouse IS NULL) OR "
              "(callee_treehouse=? AND caller_treehouse IS NULL)", (tid, tid))
    c.execute("UPDATE call SET caller_treehouse=NULL, caller_handset=NULL WHERE caller_treehouse=?", (tid,))
    c.execute("UPDATE call SET callee_treehouse=NULL, answered_handset=NULL WHERE callee_treehouse=?", (tid,))
    c.execute("DELETE FROM call_event WHERE call_id IN (SELECT id FROM call WHERE "
              "caller_treehouse IS NULL AND callee_treehouse IS NULL)")
    c.execute("DELETE FROM call WHERE caller_treehouse IS NULL AND callee_treehouse IS NULL")
    for e in [r["email"] for r in c.execute("SELECT email FROM grown_up WHERE treehouse_id=?", (tid,))]:
        c.execute("DELETE FROM session WHERE email=?", (e,))
        c.execute("DELETE FROM push_subscription WHERE email=?", (e,))
    for sql in ("DELETE FROM grown_up WHERE treehouse_id=?", "DELETE FROM ladder_code WHERE treehouse_id=?",
                "DELETE FROM handset WHERE treehouse_id=?", "DELETE FROM string WHERE a_id=? OR b_id=?"):
        c.execute(sql, (tid,) * sql.count("?"))
    c.execute("UPDATE treehouse SET name='(deleted)', deleted_at=? WHERE id=?", (db.iso(), tid))
    return tell
