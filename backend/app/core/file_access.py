from app.models.file_record import FileRecord
from app.schemas.user import UserPublic


def can_view_file(user: UserPublic, file_record: FileRecord) -> bool:
    if user.role == "admin":
        return True

    if user.role == "staff":
        return True

    return False


def can_delete_file(user: UserPublic, file_record: FileRecord) -> bool:
    if user.role == "admin":
        return True

    if user.role == "staff":
        return file_record.uploaded_by_email == user.email

    return False