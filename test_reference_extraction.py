"""
Test simple pour vérifier l'extraction de référence
"""
import re

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

    # --- Référence (version améliorée) ---
    # Pattern plus robuste pour capturer les références avec différents formats
    # Exemples: Réf.: SONIDEP/DSI/2026/0156, N°: 2026-001, REF-2026-123
    ref_m = re.search(
        r'(?:Réf\.?|Ref\.?|REF\.?|N°|No|Numéro|Référence)\s*[:\-.\s]+\s*([A-Z0-9/\-\.]+(?:\s+[A-Z0-9/\-\.]+)*)',
        text, re.IGNORECASE
    )
    if ref_m:
        # Nettoyer la référence capturée (enlever espaces multiples)
        ref = ref_m.group(1).strip()
        ref = re.sub(r'\s+', ' ', ref)  # Normaliser les espaces
        result['reference_structure'] = ref[:100]
        
    return result


# Test avec le texte du PDF OCR
test_text = """SOCIÉTÉ NIGÉRIENNE DES HYDROCARBURES (SONIDEP)
BP 245 - Avenue des Forces Armées - Niamey, Niger
Tél: +227 20 72 31 00  |  www.sonidep.ne

Niamey, le 07 avril 2026

De: SONIDEP SA — Direction des Systèmes d'Information
À: IMAN Communication Digitale — Direction Générale

Réf.: SONIDEP/DSI/2026/0156
Objet: Demande de devis pour refonte du portail institutionnel

Monsieur le Directeur Général,

J'ai l'honneur de vous adresser la présente finalement de solliciter un devis
détaillé pour la refonte complète de notre portail institutionnel.
"""

print("🔍 Test d'extraction de référence\n")
print("=" * 60)
print("TEXTE À ANALYSER:")
print(test_text[:300] + "...")
print("=" * 60)

result = parse_french_document(test_text)

print("\n📊 RÉSULTATS DE L'EXTRACTION:")
print(f"Référence détectée: '{result['reference_structure']}'")
print(f"Objet: '{result['objet']}'")
print(f"Expéditeur: '{result['expediteur']}'")
print(f"Destinataire: '{result['destinataire']}'")

if result['reference_structure']:
    print("\n✅ SUCCÈS: La référence a été extraite correctement!")
else:
    print("\n❌ ÉCHEC: Aucune référence détectée")
    
    # Test manuel des patterns
    print("\n🔧 Debug du pattern regex:")
    patterns = [
        r'Réf\.\s*:\s*([A-Z0-9/\-\.]+)',
        r'Réf\.?\s*:\s*([A-Z0-9/\-\.]+)',
        r'(?:Réf|REF)\s*[:\-.\s]+\s*([A-Z0-9/\-\.]+)',
        r'(?:Réf\.?|Ref\.?|REF\.?)\s*[:\-.\s]+\s*([A-Z0-9/\-\.]+)',
    ]
    
    for i, pat in enumerate(patterns, 1):
        m = re.search(pat, test_text, re.IGNORECASE)
        if m:
            print(f"  Pattern {i}: MATCH → '{m.group(1)}'")
        else:
            print(f"  Pattern {i}: NO MATCH")
