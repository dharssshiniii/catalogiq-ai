# Review workflow

Fields begin `AUTO_ACCEPTED`, `NEEDS_REVIEW`, or `CONFLICT`. A `prototype-reviewer` may approve, correct with a note, or reject with a reason. Corrections rebuild deterministic descriptions; decisions preserve reviewer and timestamp. Product approval is separate. Rejected fields are excluded from CSV while audit JSON retains provenance and history. Authentication is deferred without changing the audit-ready model.
