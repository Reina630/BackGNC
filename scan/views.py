from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import cv2 as cv
import numpy as np
import base64
import json


def order_points(pts):
    """Ordonne les points dans l'ordre : haut-gauche, haut-droit, bas-droit, bas-gauche"""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def detect_corners(request):
    """
    Détecte automatiquement les 4 coins d'un document dans une image.
    Envoie une image, reçoit les coordonnées des 4 coins.
    """
    if 'file' not in request.FILES:
        return Response(
            {'error': 'Aucune image fournie'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Lire l'image
        file = request.FILES['file']
        file_bytes = file.read()
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv.imdecode(nparr, cv.IMREAD_COLOR)
        
        if img is None:
            return Response(
                {'error': 'Impossible de lire l\'image'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        h, w = img.shape[:2]

        # Détection des contours
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        blur = cv.bilateralFilter(gray, 9, 75, 75)
        edged = cv.Canny(blur, 50, 150)

        contours, _ = cv.findContours(edged, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv.contourArea, reverse=True)[:5]

        # Points par défaut (90% de l'image)
        points = [
            [w * 0.1, h * 0.1],
            [w * 0.9, h * 0.1],
            [w * 0.9, h * 0.9],
            [w * 0.1, h * 0.9]
        ]

        # Chercher un contour à 4 côtés
        for cnt in contours:
            peri = cv.arcLength(cnt, True)
            approx = cv.approxPolyDP(cnt, 0.02 * peri, True)
            if len(approx) == 4:
                points = approx.reshape(4, 2).tolist()
                break

        return Response({
            'corners': points,
            'width': w,
            'height': h
        })
        
    except Exception as e:
        return Response(
            {'error': f'Erreur lors de la détection : {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def warp_document(request):
    """
    Redresse et améliore un document à partir de 4 points.
    Envoie une image + 4 points, reçoit l'image redressée et améliorée.
    """
    if 'file' not in request.FILES:
        return Response(
            {'error': 'Aucune image fournie'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if 'points' not in request.data:
        return Response(
            {'error': 'Les points sont requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Lire l'image
        file = request.FILES['file']
        file_bytes = file.read()
        img = cv.imdecode(np.frombuffer(file_bytes, np.uint8), cv.IMREAD_COLOR)
        
        if img is None:
            return Response(
                {'error': 'Impossible de lire l\'image'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Récupérer les points
        points_data = request.data['points']
        if isinstance(points_data, str):
            points_data = json.loads(points_data)
        pts = np.array(points_data, dtype="float32")
        
        # Ordonner les points
        rect = order_points(pts)
        (tl, tr, br, bl) = rect

        # Calculer les dimensions du document redressé
        width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
        height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))

        # Transformation perspective
        dst = np.array([
            [0, 0],
            [width - 1, 0],
            [width - 1, height - 1],
            [0, height - 1]
        ], dtype="float32")
        
        M = cv.getPerspectiveTransform(rect, dst)
        warped = cv.warpPerspective(img, M, (width, height))

        # --- Améliorations de qualité ---

        # 1. Suppression des ombres et correction de l'illumination
        dilated = cv.dilate(warped, np.ones((7, 7), np.uint8))
        bg_img = cv.medianBlur(dilated, 21)
        diff = cv.absdiff(warped, bg_img)
        diff = 255 - diff
        norm_img = cv.normalize(diff, None, alpha=0, beta=255, 
                               norm_type=cv.NORM_MINMAX, dtype=cv.CV_8UC1)

        # 2. Conversion en gris et augmentation du contraste
        gray = cv.cvtColor(norm_img, cv.COLOR_BGR2GRAY)

        # 3. Netteté du texte
        gaussian_blur = cv.GaussianBlur(gray, (0, 0), 3)
        sharpened = cv.addWeighted(gray, 1.5, gaussian_blur, -0.5, 0)

        # 4. Réduction du bruit
        final = cv.fastNlMeansDenoising(sharpened, None, 10, 7, 21)

        # Encoder en base64
        _, buffer = cv.imencode('.jpg', final, [cv.IMWRITE_JPEG_QUALITY, 95])
        img_str = base64.b64encode(buffer).decode()

        return Response({
            'image': f'data:image/jpeg;base64,{img_str}'
        })
        
    except Exception as e:
        return Response(
            {'error': f'Erreur lors du traitement : {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )