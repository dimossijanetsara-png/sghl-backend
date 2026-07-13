from typing import Any, List
from ninja import Schema
from ninja.pagination import PageNumberPagination


class SGHLPagination(PageNumberPagination):
    """
    Pagination compatible frontend Vue — retourne { count, results }
    au lieu de { count, items } (défaut Django Ninja).
    """
    page_size = 20
    items_attribute = 'results'   # clé utilisée par Ninja en interne

    class Output(Schema):
        count: int
        results: List[Any]

    def paginate_queryset(self, queryset, pagination, **params):
        offset = (pagination.page - 1) * self.page_size
        count = self._items_count(queryset)
        results = list(queryset[offset: offset + self.page_size])
        return {'count': count, 'results': results}
