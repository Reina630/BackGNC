from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import cv2 as cv
import numpy as np
import base64
import json
import re


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


def parse_french_document(text):
    """Parse le texte d'un document administratif français pour extraire les champs clés."""
    result = {
        'objet': '',
        'expediteur': '',
        'destinataire': '',
        'date_courrier': '',
        'reference_structure': '',
        'type_courrier': 'entrant',
        'notes': '',
    }

    if not text:
        return result

    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # --- Date numérique ---
    date_match = re.search(r'\b(\d{1,2})[/\-.](\d{1,2})[/\.\-](\d{4})\b', text)
    if date_match:
        d, m, y = date_match.groups()
        try:
            result['date_courrier'] = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
        except Exception:
            pass
    else:
        # Date en lettres: "10 avril 2026"
        mois_fr = {
            'janvier': '01', 'fevrier': '02', 'février': '02', 'mars': '03',
            'avril': '04', 'mai': '05', 'juin': '06', 'juillet': '07',
            'aout': '08', 'août': '08', 'septembre': '09', 'octobre': '10',
            'novembre': '11', 'decembre': '12', 'décembre': '12',
        }
        date_text_pat = r'\b(\d{1,2})\s+(' + '|'.join(mois_fr.keys()) + r')\s+(\d{4})\b'
        m2 = re.search(date_text_pat, text.lower())
        if m2:
            d, m_str, y = m2.groups()
            result['date_courrier'] = f"{y}-{mois_fr[m_str]}-{d.zfill(2)}"

    # --- Objet ---
    # Amélioration: capturer l'objet sur plusieurs lignes potentielles
    # Chercher "Objet:" ou équivalents, puis capturer jusqu'à 2-3 lignes
    objet_m = re.search(
        r'(?:Objet|OBJET|Sujet|SUJET|Concernant|Concerne|Object)\s*[:\-]?\s*(.+?)(?=\n\s*(?:De|À|Date|Réf|Expediteur|Destinataire|$))',
        text, re.IGNORECASE | re.DOTALL
    )
    if objet_m:
        obj = objet_m.group(1).strip()
        # Nettoyer les caractères parasites OCR et retours à la ligne multiples
        obj = re.sub(r'\s+', ' ', obj)
        # Enlever les tirets en début si présents
        obj = obj.lstrip('—-–').strip()
        result['objet'] = obj[:200]
    
    # Si pas trouvé avec le pattern principal, essayer un pattern plus permissif
    if not result['objet']:
        # Chercher une ligne qui commence par "Objet" avec ou sans ":"
        for line in lines:
            if re.match(r'^\s*(?:Objet|OBJET|Sujet|SUJET)', line, re.IGNORECASE):
                # Extraire tout ce qui suit "Objet:"
                parts = re.split(r'(?:Objet|OBJET|Sujet|SUJET)\s*[:\-]?\s*', line, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) > 1:
                    obj = parts[1].strip()
                    obj = re.sub(r'\s+', ' ', obj)
                    obj = obj.lstrip('—-–').strip()
                    if obj and len(obj) > 3:  # Au moins 3 caractères
                        result['objet'] = obj[:200]
                        break

    # --- Référence ---
    # Pattern amélioré pour capturer les références avec différents formats
    # Exemples: Réf.: SONIDEP/DSI/2026/0156, N°: 2026-001, REF-2026-123, Réf : ABC123
    # FACTURE N° IMAN/FACT/2026/0112
    ref_patterns = [
        # Pattern pour FACTURE N° suivi de la référence
        r'(?:FACTURE|Facture)\s+(?:N°|No)\s*[:\-\s]*([A-Z0-9/\-\.]+(?:[/\-][A-Z0-9]+)*)',
        # Pattern principal avec séparateurs variés
        r'(?:Réf\.?|Ref\.?|REF\.?|N°|No\.?|Numéro|Référence)\s*[:\-.\s]+\s*([A-Z0-9/\-\.]+(?:[/\-][A-Z0-9]+)*)',
        # Pattern alternatif pour "Réf:" suivi de la référence
        r'(?:Réf\.?|Ref\.?|REF\.?)\s*:\s*([A-Z][A-Z0-9/\-\.]+(?:[/\-][A-Z0-9]+)*)',
        # Pattern pour numéros simples
        r'(?:N°|No\.?|Numéro)\s*[:\-\s]*([A-Z0-9]{3,}[A-Z0-9/\-\.]*)',
    ]
    
    for pattern in ref_patterns:
        ref_m = re.search(pattern, text, re.IGNORECASE)
        if ref_m:
            # Nettoyer la référence capturée
            ref = ref_m.group(1).strip()
            # Enlever les espaces internes
            ref = re.sub(r'\s+', '', ref)
            # Couper au premier mot non-référence (Date, Objet, etc.)
            ref = re.split(r'(?:Date|Objet|Sujet|Expediteur|De|À)', ref, maxsplit=1)[0]
            if len(ref) >= 3:  # Au moins 3 caractères
                result['reference_structure'] = ref[:100]
                break

    # --- Expéditeur ---
    # Essayer plusieurs patterns avec des variantes OCR
    for pat in [
        r'(?:De\s*:|Expéditeur\s*:|Emetteur\s*:|Expediteur\s*:)\s*(.+?)(?=\n\s*(?:À|A\s|Destinataire|Date|Réf|NIF|Objet|$))',
        r'(?:De la part de|Par)\s*[:\-]?\s*(.+?)(?=\n|$)',
        r'De\s*:\s*(.+?)(?=\n\s*(?:À|A\s|Destinataire|Date|$))',
    ]:
        exp_m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if exp_m:
            exp = exp_m.group(1).strip()
            # Nettoyer les espaces multiples et retours à la ligne
            exp = re.sub(r'\s+', ' ', exp)
            # Enlever les tirets en début
            exp = exp.lstrip('—-–').strip()
            if exp and len(exp) > 2:
                result['expediteur'] = exp[:200]
                break

    # --- Destinataire ---
    for pat in [
        r'(?:À\s*:|A\s*:|Destinataire\s*:)\s*(.+?)(?=\n\s*(?:Réf|Date|Objet|NIF|De\s|$))',
        r"(?:À l['']attention de|A l['']attention de)\s*[:\-]?\s*(.+?)(?=\n|$)",
        r'À\s*:\s*(.+?)(?=\n\s*(?:Réf|Date|Objet|$))',
    ]:
        dest_m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if dest_m:
            dest = dest_m.group(1).strip()
            # Nettoyer les espaces multiples et retours à la ligne
            dest = re.sub(r'\s+', ' ', dest)
            # Enlever les tirets en début
            dest = dest.lstrip('—-–').strip()
            if dest and len(dest) > 2:
                result['destinataire'] = dest[:200]
                break

    # --- Type courrier (heuristique) ---
    sortant_kws = [
        'nous vous informons', 'veuillez', 'je vous prie', 'nous vous prions',
        'par la présente', 'je me permets', "nous avons l'honneur", 'suite à notre',
    ]
    if any(kw in text.lower() for kw in sortant_kws):
        result['type_courrier'] = 'sortant'

    # --- Notes (extrait du corps) ---
    body_start = 0
    for i, line in enumerate(lines):
        if any(kw in line.lower() for kw in ['objet :', 'monsieur,', 'madame,', 'bonjour,']):
            body_start = i + 1
            break
    excerpt = ' '.join(lines[body_start:body_start + 3])
    result['notes'] = excerpt[:300]

    return result


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def extract_document_info(request):
    """
    Extrait les informations d'un document (image ou PDF) via OCR (Tesseract).
    Retourne les champs administratifs pour pré-remplir le formulaire d'archivage.
    """
    if 'file' not in request.FILES:
        return Response({'error': 'Aucun fichier fourni'}, status=status.HTTP_400_BAD_REQUEST)

    file = request.FILES['file']
    file_name = (file.name or '').lower()
    file_bytes = file.read()
    extracted_text = ''
    ocr_used = False

    try:
        if file_name.endswith('.pdf'):
            # Essai 1 : extraction native (PDF numérique)
            try:
                import pdfplumber
                import io as _io
                with pdfplumber.open(_io.BytesIO(file_bytes)) as pdf:
                    pages_text = []
                    for page in pdf.pages[:5]:
                        t = page.extract_text()
                        if t:
                            pages_text.append(t)
                    extracted_text = '\n'.join(pages_text)
            except ImportError:
                pass

            # Essai 2 : OCR sur PDF scanné
            if not extracted_text.strip():
                try:
                    import pytesseract
                    from PIL import Image
                    from pdf2image import convert_from_bytes
                    import io as _io
                    images = convert_from_bytes(file_bytes, first_page=1, last_page=2, dpi=200)
                    texts = []
                    for img in images:
                        texts.append(pytesseract.image_to_string(img, lang='fra+eng'))
                    extracted_text = '\n'.join(texts)
                    ocr_used = True
                except ImportError:
                    pass
        else:
            # Image : OCR direct
            try:
                import pytesseract
                from PIL import Image
                import io as _io
                img = Image.open(_io.BytesIO(file_bytes))
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                extracted_text = pytesseract.image_to_string(img, lang='fra+eng')
                ocr_used = True
            except ImportError:
                return Response({
                    'fields': parse_french_document(''),
                    'ocr_used': False,
                    'text_length': 0,
                    'warning': 'pytesseract non installé. Installez : pip install pytesseract Pillow',
                })
            except Exception as e:
                return Response({
                    'fields': parse_french_document(''),
                    'ocr_used': False,
                    'text_length': 0,
                    'warning': f'Erreur OCR : {str(e)}',
                })
    except Exception as e:
        return Response({
            'fields': parse_french_document(''),
            'ocr_used': False,
            'text_length': 0,
            'warning': str(e),
        })

    parsed = parse_french_document(extracted_text)
    return Response({
        'fields': parsed,
        'ocr_used': ocr_used,
        'text_length': len(extracted_text),
        'extracted_text': extracted_text[:500] if extracted_text else '',  # Pour debug
    })