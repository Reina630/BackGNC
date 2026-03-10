from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import User, Service, Notification
from .serializers import UserSerializer, ServiceSerializer, NotificationSerializer


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
            'user': UserSerializer(user, context={'request': request}).data
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
        serializer = UserSerializer(users, many=True, context={'request': request})
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = UserSerializer(data=request.data, context={'request': request})
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
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UserSerializer(user, data=request.data, partial=True, context={'request': request})
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
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UserSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_signature_view(request):
    """
    Mettre à jour la signature électronique et le mot de passe de signature
    """
    user = request.user
    
    # Mettre à jour la signature électronique si fournie
    if 'signature_electronique' in request.FILES:
        user.signature_electronique = request.FILES['signature_electronique']
    
    # Mettre à jour le mot de passe de signature si fourni
    if 'signature_password' in request.data:
        signature_password = request.data.get('signature_password')
        if signature_password:
            user.set_signature_password(signature_password)
    
    user.save()
    
    serializer = UserSerializer(user, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_signature_password_view(request):
    """
    Vérifier le mot de passe de signature
    """
    password = request.data.get('password')
    
    if not password:
        return Response(
            {'error': 'Mot de passe requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not request.user.signature_password:
        return Response(
            {'error': 'Aucun mot de passe de signature configuré'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if request.user.check_signature_password(password):
        return Response({'valid': True})
    else:
        return Response(
            {'valid': False, 'error': 'Mot de passe incorrect'},
            status=status.HTTP_401_UNAUTHORIZED
        )


# ==================== Gestion des services ====================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def services_view(request):
    """
    GET: Liste des services
    POST: Créer un service (admin uniquement)
    """
    if request.method == 'GET':
        services = Service.objects.all()
        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Vérifier si admin
        if request.user.role != 'admin':
            return Response({'error': 'Admin uniquement'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ServiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def service_detail_view(request, pk):
    """
    GET: Détails d'un service
    PUT: Modifier un service (admin uniquement)
    DELETE: Supprimer un service (admin uniquement)
    """
    try:
        service = Service.objects.get(pk=pk)
    except Service.DoesNotExist:
        return Response({'error': 'Service non trouvé'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = ServiceSerializer(service)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Vérifier si admin
        if request.user.role != 'admin':
            return Response({'error': 'Admin uniquement'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ServiceSerializer(service, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Vérifier si admin
        if request.user.role != 'admin':
            return Response({'error': 'Admin uniquement'}, status=status.HTTP_403_FORBIDDEN)
        
        service.delete()
        return Response({'message': 'Service supprimé'}, status=status.HTTP_204_NO_CONTENT)


# ==================== Gestion des notifications ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_view(request):
    """
    GET: Liste des notifications de l'utilisateur connecté
    """
    notifications = Notification.objects.filter(utilisateur=request.user)
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_non_lues_view(request):
    """
    GET: Nombre de notifications non lues
    """
    count = Notification.objects.filter(utilisateur=request.user, lue=False).count()
    return Response({'count': count})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marquer_notification_lue_view(request, pk):
    """
    POST: Marquer une notification comme lue
    """
    try:
        notification = Notification.objects.get(pk=pk, utilisateur=request.user)
    except Notification.DoesNotExist:
        return Response({'error': 'Notification non trouvée'}, status=status.HTTP_404_NOT_FOUND)
    
    notification.lue = True
    notification.lue_at = timezone.now()
    notification.save()
    
    serializer = NotificationSerializer(notification)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marquer_toutes_lues_view(request):
    """
    POST: Marquer toutes les notifications comme lues
    """
    Notification.objects.filter(utilisateur=request.user, lue=False).update(
        lue=True,
        lue_at=timezone.now()
    )
    return Response({'message': 'Toutes les notifications ont été marquées comme lues'})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def supprimer_notification_view(request, pk):
    """
    DELETE: Supprimer une notification
    """
    try:
        notification = Notification.objects.get(pk=pk, utilisateur=request.user)
    except Notification.DoesNotExist:
        return Response({'error': 'Notification non trouvée'}, status=status.HTTP_404_NOT_FOUND)
    
    notification.delete()
    return Response({'message': 'Notification supprimée'}, status=status.HTTP_204_NO_CONTENT)
