from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User
from .serializers import UserSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Login avec username ou email et password
    """
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not password:
        return Response(
            {'error': 'Password requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not username and not email:
        return Response(
            {'error': 'Username ou email requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Tenter d'abord avec username si fourni
    user = None
    if username:
        user = authenticate(username=username, password=password)
    
    # Si pas trouvé et email fourni, chercher par email
    if not user and email:
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(username=user_obj.username, password=password)
        except User.DoesNotExist:
            pass
    
    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        })
    
    return Response(
        {'error': 'Identifiants invalides'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token_view(request):
    """
    Rafraîchir l'access token
    """
    refresh_token = request.data.get('refresh')
    
    if not refresh_token:
        return Response(
            {'error': 'Refresh token requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        refresh = RefreshToken(refresh_token)
        return Response({'access': str(refresh.access_token)})
    except:
        return Response(
            {'error': 'Token invalide'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Déconnexion
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'Déconnexion réussie'})
    except:
        return Response({'error': 'Erreur'}, status=status.HTTP_400_BAD_REQUEST)


# ==================== Gestion des utilisateurs ====================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def users_view(request):
    """
    GET: Liste des utilisateurs (admin uniquement)
    POST: Créer un utilisateur (admin uniquement)
    """
    # Vérifier si admin
    if request.user.role != 'admin':
        return Response({'error': 'Admin uniquement'}, status=status.HTTP_403_FORBIDDEN)
    
    if request.method == 'GET':
        users = User.objects.all().order_by('-date_joined')
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_detail_view(request, pk):
    """
    GET: Détails d'un utilisateur
    PUT: Modifier un utilisateur
    DELETE: Supprimer un utilisateur
    Admin uniquement
    """
    # Vérifier si admin
    if request.user.role != 'admin':
        return Response({'error': 'Admin uniquement'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = UserSerializer(user)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        user.is_active = False
        user.save()
        return Response({'message': 'Utilisateur désactivé'})


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """
    GET: Mon profil
    PUT: Modifier mon profil
    """
    if request.method == 'GET':
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
