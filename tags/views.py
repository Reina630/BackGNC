from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Tag
from .serializers import TagSerializer


class TagViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les tags
    """
    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Optionnel : Filtrer par recherche
        """
        queryset = Tag.objects.all().order_by('name')
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset
    
    @action(detail=False, methods=['post'])
    def get_or_create(self, request):
        """
        Créer un tag s'il n'existe pas, sinon retourner le tag existant
        """
        name = request.data.get('name', '').strip()
        if not name:
            return Response({'error': 'Le nom du tag est requis'}, status=status.HTTP_400_BAD_REQUEST)
        
        tag, created = Tag.objects.get_or_create(name=name)
        serializer = self.get_serializer(tag)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
