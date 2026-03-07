from .repositories.mock import MockEventRepository

_repo = MockEventRepository()


def get_repository() -> MockEventRepository:
    return _repo
