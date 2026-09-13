from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Consistent page-number pagination for large API collections."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
