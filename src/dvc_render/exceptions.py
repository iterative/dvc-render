class DvcRenderException(Exception):
    pass


class MissingPlaceholderError(DvcRenderException):
    def __init__(self, placeholder, template_type):
        super().__init__(f"{template_type} template has to contain '{placeholder}'.")
