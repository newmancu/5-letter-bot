class BaseArgException(Exception):
    pass


class WordLenMismatch(BaseArgException):
    def __init__(self, got_len: int, expected_len: int) -> None:
        super().__init__()
        self.got_len = got_len
        self.expected_len = expected_len


class NonRussionWordError(BaseArgException):
    pass
