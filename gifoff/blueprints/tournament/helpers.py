from inflection import parameterize
from werkzeug.routing import BaseConverter

def add_app_url_map_converter(self, func, name=None):
    """
    Register a custom URL map converters, available application wide.

    :param name: the optional name of the filter, otherwise the function name
                 will be used.
    """

    def register_converter(state):
        state.app.url_map.converters[name or func.__name__] = func

    self.record_once(register_converter)


class IDSlugConverter(BaseConverter):
    """Matches an int id and optional slug, separated by "/".

    :param attr: name of field to slugify, or None for default of str(instance)
    :param length: max length of slug when building url
    """

    regex = r'-?\d+(?:/[\w\-]*)?'

    def __init__(self, map, attr='name', length=80):
        self.attr = attr
        self.length = int(length)
        super(IDSlugConverter, self).__init__(map)

    def to_python(self, value):
        id, slug = (value.split('/') + [None])[:2]
        return int(id)

    def to_url(self, value):
        raw = str(value) if self.attr is None else getattr(value, self.attr, '')
        slug = parameterize(raw)[:self.length].rstrip('-')
        return '{}/{}'.format(value.id, slug).rstrip('/')