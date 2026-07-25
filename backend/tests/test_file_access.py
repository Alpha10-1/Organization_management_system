from app.core.file_access import can_delete_file, can_view_file
from app.schemas.user import UserPublic


def make_user(role, email="user@org.com"):
    return UserPublic(id=1, name="Test User", email=email, role=role, disabled=False)


class FakeFileRecord:
    """Stand-in for a FileRecord row -- only uploaded_by_email matters
    to the access-control logic under test."""

    def __init__(self, uploaded_by_email):
        self.uploaded_by_email = uploaded_by_email


def test_admin_can_view_any_file():
    admin = make_user("admin")
    file = FakeFileRecord(uploaded_by_email="someone-else@org.com")
    assert can_view_file(admin, file) is True


def test_staff_can_view_any_file():
    staff = make_user("staff")
    file = FakeFileRecord(uploaded_by_email="someone-else@org.com")
    assert can_view_file(staff, file) is True


def test_admin_can_delete_any_file():
    admin = make_user("admin", email="admin@org.com")
    file = FakeFileRecord(uploaded_by_email="someone-else@org.com")
    assert can_delete_file(admin, file) is True


def test_staff_can_delete_their_own_file():
    staff = make_user("staff", email="staff@org.com")
    file = FakeFileRecord(uploaded_by_email="staff@org.com")
    assert can_delete_file(staff, file) is True


def test_staff_cannot_delete_someone_elses_file():
    staff = make_user("staff", email="staff@org.com")
    file = FakeFileRecord(uploaded_by_email="someone-else@org.com")
    assert can_delete_file(staff, file) is False


def test_unknown_role_cannot_delete():
    guest = make_user("guest", email="guest@org.com")
    file = FakeFileRecord(uploaded_by_email="guest@org.com")
    assert can_delete_file(guest, file) is False
