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
    """
    Extrait les champs clés d'un document administratif français.
    Stratégie : marqueurs explicites en priorité, puis heuristiques positionnelles.
    Champs extraits : date, objet, expéditeur, destinataire, référence, type.
    """
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
    full = '\n'.join(lines)

    # Labels de champs connus — servent à délimiter les blocs
    FIELD_LABEL = re.compile(
        r'^\s*(?:De|À|A|Objet|Réf|Ref|REF|Date|Expéditeur|Emetteur|Destinataire|'
        r'N°|No|Copie|Tel|Tél|Fax|Email|Service|Direction|Signat)',
        re.IGNORECASE,
    )

    # ── 1. DATE ──────────────────────────────────────────────────────────────
    mois_fr = {
        'janvier': '01', 'fevrier': '02', 'février': '02', 'mars': '03',
        'avril': '04', 'mai': '05', 'juin': '06', 'juillet': '07',
        'aout': '08', 'août': '08', 'septembre': '09', 'octobre': '10',
        'novembre': '11', 'decembre': '12', 'décembre': '12',
    }
    mois_pat = '|'.join(mois_fr.keys())

    def _parse_date(match, fmt):
        try:
            if fmt == 'text':
                d, m_str, y = match.group(1), match.group(2).lower(), match.group(3)
                return f"{y}-{mois_fr[m_str]}-{d.zfill(2)}"
            else:
                d, m, y = match.group(1), match.group(2), match.group(3)
                if 1 <= int(d) <= 31 and 1 <= int(m) <= 12:
                    return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
        except Exception:
            pass
        return ''

    # Priorité : date textuelle labelisée > date textuelle brute > numérique labelisée > numérique brute
    date_candidates = [
        (re.search(r'(?:Le\s+|le\s+|Date\s*[:\-]\s*)(\d{1,2})\s+(' + mois_pat + r')\s+(\d{4})\b', full, re.IGNORECASE), 'text'),
        (re.search(r'\b(\d{1,2})\s+(' + mois_pat + r')\s+(\d{4})\b', full, re.IGNORECASE), 'text'),
        (re.search(r'(?:Le\s+|Date\s*[:\-]\s*)(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})', full), 'numeric'),
        (re.search(r'\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b', full), 'numeric'),
    ]
    for m_obj, fmt in date_candidates:
        if m_obj:
            parsed = _parse_date(m_obj, fmt)
            if parsed:
                result['date_courrier'] = parsed
                break

    # ── 2. OBJET (multi-lignes) ───────────────────────────────────────────────
    objet_lines = []
    in_objet = False
    for line in lines:
        if re.match(r'^\s*(?:Objet|OBJET|Object|Sujet|SUJET)\s*[:\-]?\s*', line, re.IGNORECASE):
            in_objet = True
            # Contenu de la même ligne après "Objet :"
            after = re.split(r'(?:Objet|OBJET|Object|Sujet|SUJET)\s*[:\-]?\s*', line, maxsplit=1, flags=re.IGNORECASE)
            if len(after) > 1 and after[1].strip():
                objet_lines.append(after[1].strip())
            continue
        if in_objet:
            # Stopper sur un autre champ ou ligne vide ou trop courte
            if FIELD_LABEL.match(line) or len(line) < 3:
                break
            objet_lines.append(line)
            if len(objet_lines) >= 4:
                break
    if objet_lines:
        raw = ' '.join(objet_lines)
        result['objet'] = re.sub(r'\s+', ' ', raw).strip('—-– ')[:300]

    # Fallback : regex simple sur une ligne
    if not result['objet']:
        m = re.search(r'(?:Objet|OBJET|Sujet)\s*[:\-]\s*(.+?)(?:\n|$)', full, re.IGNORECASE)
        if m:
            result['objet'] = re.sub(r'\s+', ' ', m.group(1)).strip()[:300]

    # ── 3. RÉFÉRENCE ─────────────────────────────────────────────────────────
    for pat in [
        r'(?:Réf\.?|Ref\.?|REF\.?)\s*[:\-\.]\s*([A-Z0-9][A-Z0-9/\-\.]{2,})',
        r'N°\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-\.]{2,})',
        r'(?:FACTURE|Facture)\s+(?:N°|No)\s*[:\-\s]*([A-Z0-9][A-Z0-9/\-\.]+)',
    ]:
        m = re.search(pat, full, re.IGNORECASE)
        if m:
            ref = re.sub(r'\s+', '', m.group(1)).rstrip('.')
            if 3 <= len(ref) <= 100:
                result['reference_structure'] = ref
                break

    # ── 4. EXPÉDITEUR ────────────────────────────────────────────────────────
    # a) Marqueur explicite
    for pat in [
        r'(?:De\s*:|Expéditeur\s*:|Emetteur\s*:|Expediteur\s*:)\s*(.+?)(?=\n|$)',
        r'(?:De la part de|Par)\s*[:\-]?\s*(.+?)(?=\n|$)',
    ]:
        m = re.search(pat, full, re.IGNORECASE)
        if m:
            exp = re.sub(r'\s+', ' ', m.group(1)).strip()
            if len(exp) > 2:
                result['expediteur'] = exp[:200]
                break

    # b) Heuristique : en-tête du document (premières lignes en majuscules = raison sociale)
    if not result['expediteur']:
        for line in lines[:6]:
            if (
                len(line) > 4
                and not FIELD_LABEL.match(line)
                and not re.match(r'^\d', line)
                and (line.isupper() or (line[0].isupper() and not line.endswith(':')))
            ):
                result['expediteur'] = line[:200]
                break

    # ── 5. DESTINATAIRE ──────────────────────────────────────────────────────
    for pat in [
        r"(?:À l['']attention de|A l['']attention de)\s*[:\-]?\s*(.+?)(?=\n|$)",
        r'(?:À\s*:|A\s*:|Destinataire\s*:)\s*(.+?)(?=\n|$)',
        r'(?:Monsieur|Madame|M\.|Mme\.?)\s+(?:le\s+)?(?:Directeur|Président|Chef|Responsable|Ministre|DG|PDG|PCA)[^\n]{0,80}',
    ]:
        m = re.search(pat, full, re.IGNORECASE)
        if m:
            grp = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
            dest = re.sub(r'\s+', ' ', grp).strip()
            if len(dest) > 2:
                result['destinataire'] = dest[:200]
                break

    # ── 6. TYPE (heuristique mots-clés) ──────────────────────────────────────
    sortant_kws = [
        'nous vous informons', 'veuillez', 'je vous prie', 'nous vous prions',
        'par la présente', 'je me permets', "nous avons l'honneur",
        'avons l\'honneur', 'suite à notre', 'permettons de',
    ]
    if any(kw in full.lower() for kw in sortant_kws):
        result['type_courrier'] = 'sortant'

    # ── 7. NOTES (corps du document) ─────────────────────────────────────────
    body_start = 0
    for i, line in enumerate(lines):
        if re.match(r'^(Monsieur|Madame|Bonjour|Cher|Objet)[,\s]', line, re.IGNORECASE):
            body_start = i + 1
            break
    result['notes'] = re.sub(r'\s+', ' ', ' '.join(lines[body_start:body_start + 3])).strip()[:300]

    return result



def _preprocess_for_ocr(pil_img):
    """
    Prétraitement d'une image PIL avant OCR Tesseract.
    - Conversion en niveaux de gris
    - Redimensionnement si trop petite (min 1500px de large)
    - Binarisation adaptative (Otsu) pour maximiser le contraste texte/fond
    """
    import numpy as np
    from PIL import Image

    # Convertir en niveaux de gris
    if pil_img.mode != 'L':
        pil_img = pil_img.convert('L')

    # Upscale si l'image est trop petite
    w, h = pil_img.size
    if w < 1500:
        scale = 1500 / w
        pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Binarisation Otsu via OpenCV
    arr = np.array(pil_img)
    _, binary = cv.threshold(arr, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)

    # Légère débruitisation
    binary = cv.fastNlMeansDenoising(binary, None, 10, 7, 21)

    return Image.fromarray(binary)


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
                    images = convert_from_bytes(file_bytes, first_page=1, last_page=3, dpi=300)
                    texts = []
                    for img in images:
                        img = _preprocess_for_ocr(img)
                        texts.append(pytesseract.image_to_string(
                            img, lang='fra', config='--oem 3 --psm 6'
                        ))
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
                if img.mode not in ('RGB', 'L', 'RGBA'):
                    img = img.convert('RGB')
                img = _preprocess_for_ocr(img)
                extracted_text = pytesseract.image_to_string(
                    img, lang='fra', config='--oem 3 --psm 6'
                )
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