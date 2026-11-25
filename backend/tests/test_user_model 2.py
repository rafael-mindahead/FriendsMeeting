
import re
from unittest.mock import patch

from app.Database.base import Base
from app.models.user import User, generate_friend_code


def test_user_model():
    assert issubclass(User, Base)
    assert User.__tablename__ == "users"


def test_user_primary_key():
    assert User.__table__.c.id.primary_key


def test_unique_user_fields():
    columns = User.__table__.c

    assert columns.username.unique
    assert columns.email.unique
    assert columns.friend_code.unique


def test_friend_code_format():
    for _ in range(20):
        code = generate_friend_code()

        assert len(code) == 11
        assert re.fullmatch(r"FM-[A-Z2-9]{8}", code)


def test_friend_code_generation():
    with patch(
        "app.models.user.secrets.choice",
        return_value="X"
    ) as mocked_choice:
        code = generate_friend_code()

    assert code == "FM-XXXXXXXX"
    assert mocked_choice.call_count == 8


def test_created_at_default():
    column = User.__table__.c.created_at

    assert column.server_default is not None
    assert column.nullable is False
