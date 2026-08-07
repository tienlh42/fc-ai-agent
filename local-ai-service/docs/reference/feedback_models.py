"""Django feedback models supplied by the backend team.

Reference only. This file is outside ``app`` and must not be imported by the
Local AI runtime. Use it as the source of truth for feedback tool JSON Schemas.
"""

from django.utils.translation import gettext_lazy as _  # type: ignore
from django.db.models.constraints import UniqueConstraint, CheckConstraint  # type: ignore
from django.db.models.query import Q  # type: ignore
from app.models import BaseModel
from django.db.models import (  # type: ignore
    CharField,
    ForeignKey,
    TextField,
    BigIntegerField,
    TextChoices,
    IntegerField,
    SlugField,
    BooleanField,
    CASCADE,
)


class FeedbackStatus(TextChoices):
    NEW = "new", _("new")
    REVIEW = "review", _("review")
    PROCESSING = "processing", _("processing")
    VERIFIED = "verified", _("verified")
    CLOSE_TICKET = "close-ticket", _("close-ticket")


class FeedbackPriority(TextChoices):
    LOW = "low", _("low")
    MEDIUM = "medium", _("medium")
    HIGH = "high", _("high")


class ApprovalStatus(TextChoices):
    CREATED = "created", _("created")
    APPROVED = "approved", _("approved")
    REJECTED = "rejected", _("rejected")


class Reason(BaseModel):
    vi_slug = SlugField(max_length=300, null=True, blank=True)
    en_slug = SlugField(max_length=300, null=True, blank=True)
    vi_name = CharField(max_length=300)
    en_name = CharField(max_length=300)
    campus_id = BigIntegerField(null=True, blank=True)
    order = IntegerField(default=1)


class PipeLine(BaseModel):
    vi_slug = SlugField(max_length=300, null=True, blank=True)
    en_slug = SlugField(max_length=300, null=True, blank=True)
    vi_name = CharField(max_length=300)
    en_name = CharField(max_length=300)
    order = IntegerField(default=1)


class FeedBack(BaseModel):
    title = CharField(max_length=200)
    description = TextField()
    priority = CharField(
        max_length=20, choices=FeedbackPriority.choices, default=FeedbackPriority.MEDIUM
    )
    reason = ForeignKey("Reason", related_name="reason_feedback", on_delete=CASCADE)
    guardian_id = BigIntegerField()  # person id
    student_id = BigIntegerField()  # person id
    campus_id = BigIntegerField(null=True, blank=True)
    feedback_status = CharField(max_length=255, default="new")
    source = CharField(max_length=255, blank=True)


class Solution(BaseModel):
    feedback = ForeignKey(
        "FeedBack", related_name="solution_feedback", on_delete=CASCADE
    )
    solution = TextField()


class FileAttachment(BaseModel):
    feedback = ForeignKey("FeedBack", related_name="file_attachment", on_delete=CASCADE)
    type = CharField(max_length=255, null=True, blank=True)
    name = CharField(max_length=255, null=True, blank=True)
    url = CharField(max_length=255, null=True, blank=True)
    path = CharField(max_length=255)
    mime_type = CharField(max_length=255, null=True, blank=True)
    extension = CharField(max_length=255, null=True, blank=True)


class Process(BaseModel):
    feedback = ForeignKey("FeedBack", on_delete=CASCADE)
    pipeline = ForeignKey("PipeLine", on_delete=CASCADE)


class FollowUpRule(BaseModel):
    campus_id = BigIntegerField(null=True, blank=True)
    staff_id = CharField(max_length=255, null=True, blank=True)
    staff_email = CharField(max_length=255)
    auto_follow_up = BooleanField(default=False)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["campus_id", "staff_email"],
                condition=Q(deleted=False),
                name="unique_follow_rule_campus_email_not_deleted",
            )
        ]


class AutoAssignToRule(BaseModel):
    reason = ForeignKey("Reason", related_name="assign_reason_rule", on_delete=CASCADE)
    campus_id = BigIntegerField(null=True, blank=True)
    school_id = BigIntegerField(null=True, blank=True)
    staff_id = CharField(max_length=255, null=True, blank=True)
    staff_email = CharField(max_length=255)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["reason_id", "campus_id", "staff_email"],
                condition=Q(deleted=False),
                name="unique_auto_assign_rule_reason_campus_email_not_deleted",
            )
        ]


class AssignToRule(BaseModel):
    campus_id = BigIntegerField(null=True, blank=True)
    staff_id = CharField(max_length=255, null=True, blank=True)
    staff_email = CharField(max_length=255)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["campus_id", "staff_email"],
                condition=Q(deleted=False),
                name="unique_assign_rule_campus_email_not_deleted",
            )
        ]


class ApprovalRule(BaseModel):
    campus_id = BigIntegerField(null=True, blank=True)
    staff_id = CharField(max_length=255, null=True, blank=True)
    staff_email = CharField(max_length=255)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["campus_id", "staff_email"],
                condition=Q(deleted=False),
                name="unique_approval_rule_campus_email_not_deleted",
            )
        ]


class FollowUp(BaseModel):
    feedback = ForeignKey(
        "FeedBack", related_name="follow_up_feedback", on_delete=CASCADE
    )
    staff_id = CharField(max_length=255, null=True, blank=True)

    class Meta:
        unique_together = ("feedback", "staff_id")


class AssignTo(BaseModel):
    feedback = ForeignKey(
        "FeedBack", related_name="assign_to_feedback", on_delete=CASCADE
    )
    staff_id = CharField(max_length=255, null=True, blank=True)

    class Meta:
        unique_together = ("feedback", "staff_id")


class Approval(BaseModel):
    feedback = ForeignKey(
        "FeedBack", related_name="approval_feedback", on_delete=CASCADE
    )
    staff_id = CharField(max_length=255, null=True, blank=True)
    status = CharField(
        max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.CREATED
    )
    order = IntegerField(default=1)

    class Meta:
        unique_together = ("feedback", "staff_id")


class ActionNote(BaseModel):
    feedback = ForeignKey(
        "FeedBack", related_name="action_note_feedback", on_delete=CASCADE
    )
    note = TextField()
    created_by_id = CharField(max_length=255, null=True, blank=True)


class ActivityLog(BaseModel):
    feedback = ForeignKey("FeedBack", related_name="log_feedback", on_delete=CASCADE)
    action = CharField(max_length=255)
    note = TextField()
    old_data = TextField(null=True, blank=True)


class Rating(BaseModel):
    feedback = ForeignKey(
        "FeedBack", related_name="rating_feedback", on_delete=CASCADE
    )
    note = TextField(null=True, blank=True)
    rating = IntegerField()
    uuid = CharField(max_length=255)

    class Meta:
        constraints = [
            CheckConstraint(
                condition=Q(rating__gte=1) & Q(rating__lte=5),
                name="rating_range_1_to_5",
            )
        ]
