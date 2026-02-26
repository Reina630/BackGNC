from django_filters import rest_framework as filters
from .models import Document


class DocumentFilter(filters.FilterSet):
    # Recherche par période
    date_from = filters.DateFilter(field_name="created_at", lookup_expr='gte')
    date_to = filters.DateFilter(field_name="created_at", lookup_expr='lte')

    # Recherche par taille (min/max)
    size_min = filters.NumberFilter(field_name="file_size", lookup_expr='gte')
    size_max = filters.NumberFilter(field_name="file_size", lookup_expr='lte')

    class Meta:
        model = Document
        fields = {
            'title': ['icontains'],
            'file_type': ['exact'],
            'folder': ['exact', 'isnull'],
            'owner': ['exact'],
            'tags__name': ['icontains', 'exact'],  # Recherche dans les tags
            'is_favorite': ['exact'],  # Filtre par favoris
        }