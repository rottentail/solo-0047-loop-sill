class MediaError(ValueError):
    """输入存在可向操作人员解释的错误。"""

    def __init__(self, message, *, status=400):
        super().__init__(message)
        self.status = status


def integer(value, name, lower, upper):
    if type(value) is not int or not lower <= value <= upper:
        raise MediaError(f'{name}须为 {lower} 到 {upper} 之间的整数')
    return value


def object_fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise MediaError('缺少必要字段或包含未知字段')
    return value
