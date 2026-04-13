"""
Script pour générer des courriers réalistes pour le système de gestion de courriers (GED).
Génère des courriers entrants et sortants avec toutes les informations nécessaires pour l'archivage.

Usage:
    python generate_test_documents.py

Ce script crée des courriers de test dans le dossier media/courriers/test/
avec des PDFs réalistes contenant toutes les métadonnées nécessaires.
"""
import os
import sys
import django
from pathlib import Path
from datetime import datetime, timedelta
import random

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ged.settings')
django.setup()

# Imports Django après setup
from django.core.files import File
from documents.models import Courrier, Categorie
from users.models import User
from django.utils import timezone

# Pour générer des PDF
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("⚠️  reportlab non installé - les PDF ne seront pas générés")
    print("   Installez avec: pip install reportlab")


def create_test_folder(base_path="test_documents"):
    """Crée le dossier de test"""
    path = Path(base_path)
    path.mkdir(exist_ok=True)
    return path


def generate_pdf(filepath, title, content):
    """Génère un fichier PDF avec du contenu"""
    if REPORTLAB_AVAILABLE:
        c = canvas.Canvas(str(filepath), pagesize=A4)
        width, height = A4
        
        # Titre
        c.setFont("Helvetica-Bold", 24)
        c.drawString(50, height - 100, title)
        
        # Date
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 130, f"Date: {datetime.now().strftime('%d/%m/%Y')}")
        
        # Contenu
        c.setFont("Helvetica", 12)
        y_position = height - 180
        for line in content.split('\n'):
            c.drawString(50, y_position, line)
            y_position -= 20
            if y_position < 100:
                c.showPage()
                y_position = height - 100
        
        c.save()
    else:
        # Création d'un fichier vide
        filepath.touch()


def generate_docx(filepath, title, content):
    """Génère un fichier DOCX avec du contenu"""
    if PYTHON_DOCX_AVAILABLE:
        doc = Document()
        doc.add_heading(title, 0)
        doc.add_paragraph(f"Date: {datetime.now().strftime('%d/%m/%Y')}")
        doc.add_paragraph('')
        
        for paragraph in content.split('\n\n'):
            doc.add_paragraph(paragraph)
        
        doc.save(str(filepath))
    else:
        filepath.touch()


def generate_xlsx(filepath, title, data):
    """Génère un fichier Excel avec des données"""
    if OPENPYXL_AVAILABLE:
        wb = Workbook()
        ws = wb.active
        ws.title = title[:31]  # Excel limite à 31 caractères
        
        # Ajout des en-têtes
        for col_idx, header in enumerate(data['headers'], 1):
            ws.cell(row=1, column=col_idx, value=header)
        
        # Ajout des données
        for row_idx, row_data in enumerate(data['rows'], 2):
            for col_idx, value in enumerate(row_data, 1):
                ws.cell(row=row_idx, column=col_idx, value=value)
        
        wb.save(str(filepath))
    else:
        filepath.touch()


def generate_image(filepath, title, size=(800, 600)):
    """Génère une image avec du texte"""
    if PIL_AVAILABLE:
        # Créer une image avec un fond coloré
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F']
        img = Image.new('RGB', size, color=random.choice(colors))
        
        draw = ImageDraw.Draw(img)
        
        # Essayer d'utiliser une police système
        try:
            font = ImageFont.truetype("arial.ttf", 40)
            small_font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Ajouter le titre centré
        bbox = draw.textbbox((0, 0), title, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size[0] - text_width) / 2
        y = (size[1] - text_height) / 2
        
        draw.text((x, y), title, fill='white', font=font)
        
        # Ajouter la date
        date_text = datetime.now().strftime('%d/%m/%Y')
        date_bbox = draw.textbbox((0, 0), date_text, font=small_font)
        date_width = date_bbox[2] - date_bbox[0]
        draw.text(((size[0] - date_width) / 2, y + 60), date_text, fill='white', font=small_font)
        
        img.save(str(filepath))
    else:
        filepath.touch()


def generate_ocr_test_documents(base_path="test_documents/ocr_test"):
    """
    Génère des courriers administratifs parfaits pour tester l'OCR.
    Chaque document contient tous les champs structurés que le parser sait extraire :
      - Objet, Réf, De, À, Date (numérique ou en lettres)
      - Corps avec mots-clés sortant / entrant
    """
    folder = Path(base_path)
    folder.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Dossier OCR Test: {folder.absolute()}\n")

    docs = [
        # ── ENTRANT 1 ──────────────────────────────────────────────────────────
        {
            'type': 'pdf',
            'filename': 'OCR_ENTRANT_1_Demande_devis.pdf',
            'title': 'OCR Test — Courrier entrant',
            'content': (
                "SOCIÉTÉ NIGÉRIENNE DES HYDROCARBURES (SONIDEP)\n"
                "BP 245 - Avenue des Forces Armées - Niamey, Niger\n"
                "Tél: +227 20 72 31 00  |  www.sonidep.ne\n"
                "\n"
                "Niamey, le 07 avril 2026\n"
                "\n"
                "De: SONIDEP SA — Direction des Systèmes d'Information\n"
                "À: IMAN Communication Digitale — Direction Générale\n"
                "\n"
                "Réf.: SONIDEP/DSI/2026/0156\n"
                "Objet: Demande de devis pour refonte du portail institutionnel\n"
                "\n"
                "Monsieur le Directeur Général,\n"
                "\n"
                "J'ai l'honneur de vous adresser la présente afin de solliciter un devis\n"
                "détaillé pour la refonte complète de notre portail institutionnel.\n"
                "\n"
                "PÉRIMÈTRE DU PROJET :\n"
                "• Site web responsive (mobile, tablette, desktop)\n"
                "• Espace client avec authentification sécurisée\n"
                "• Module de publication d'actualités (CMS)\n"
                "• Intégration des flux de données temps réel\n"
                "• Accessibilité WCAG 2.1 niveau AA\n"
                "• Migration des contenus existants\n"
                "\n"
                "Budget indicatif : 12 000 000 FCFA TTC\n"
                "Délai de réponse souhaité : avant le 20 avril 2026\n"
                "\n"
                "Pièces jointes : Cahier des charges fonctionnel (12 pages)\n"
                "\n"
                "Dans l'attente de votre retour, veuillez agréer, Monsieur le Directeur,\n"
                "l'expression de notre haute considération.\n"
                "\n"
                "Issoufou MAÏGA\n"
                "Directeur des Systèmes d'Information — SONIDEP\n"
                "Tél direct : +227 90 34 56 78\n"
            ),
        },
        # ── ENTRANT 2 ──────────────────────────────────────────────────────────
        {
            'type': 'pdf',
            'filename': 'OCR_ENTRANT_2_Reclamation.pdf',
            'title': 'OCR Test — Réclamation entrant',
            'content': (
                "CHAMBRE DE COMMERCE ET D'INDUSTRIE DU NIGER (CCIN)\n"
                "Place de la Concertation — BP 209 — Niamey, Niger\n"
                "\n"
                "Niamey, le 03/04/2026\n"
                "\n"
                "De: CCIN — Service Contentieux\n"
                "À: Direction Générale — IMAN Communication Digitale\n"
                "\n"
                "Réf.: CCIN/SC/2026/RE-042\n"
                "Objet: Réclamation relative au retard de livraison — Projet site e-commerce\n"
                "\n"
                "Madame, Monsieur,\n"
                "\n"
                "Par la présente, nous vous mettons en demeure de nous livrer dans un\n"
                "délai de 72 heures le site e-commerce objet du contrat\n"
                "IMAN/2026/CCIN/003 signé le 15 janvier 2026.\n"
                "\n"
                "Rappel des faits :\n"
                "  - Date de signature du contrat : 15/01/2026\n"
                "  - Délai contractuel : 60 jours (=>  17/03/2026)\n"
                "  - Acompte versé : 5 000 000 FCFA\n"
                "  - Retard constaté : 17 jours à ce jour\n"
                "\n"
                "En cas de non-livraison dans le délai imparti, nous nous réservons le\n"
                "droit d'appliquer les pénalités prévues à l'article 8 du contrat\n"
                "(2 % du montant total par jour de retard).\n"
                "\n"
                "Aïchatou CHAIBOU\n"
                "Directrice des Affaires Juridiques — CCIN\n"
            ),
        },
        # ── ENTRANT 3 ──────────────────────────────────────────────────────────
        {
            'type': 'pdf',
            'filename': 'OCR_ENTRANT_3_Commande.pdf',
            'title': 'OCR Test — Bon de commande entrant',
            'content': (
                "NIGELEC — Société Nigérienne d'Électricité\n"
                "Boulevard de la République — BP 11202 — Niamey\n"
                "Tél : +227 20 73 24 10\n"
                "\n"
                "Niamey, le 09 avril 2026\n"
                "\n"
                "Expéditeur: NIGELEC — Direction de la Communication\n"
                "Destinataire: IMAN Communication Digitale — Service Commercial\n"
                "\n"
                "N°: NIGELEC/COM/2026/BC-0089\n"
                "Objet: Bon de commande — Campagne de sensibilisation énergie solaire\n"
                "\n"
                "Madame, Monsieur,\n"
                "\n"
                "Faisant suite à votre offre commerciale réf. IMAN/OFF/2026/031 du\n"
                "25 mars 2026, nous vous passons commande ferme des prestations\n"
                "suivantes :\n"
                "\n"
                "  1. Création de 6 visuels pour réseaux sociaux    800 000 FCFA\n"
                "  2. Production d'un spot vidéo 30s               2 500 000 FCFA\n"
                "  3. Gestion campagne Facebook Ads (1 mois)       1 200 000 FCFA\n"
                "  4. Community management (1 mois)                1 000 000 FCFA\n"
                "                                              ─────────────────\n"
                "  TOTAL HT                                        5 500 000 FCFA\n"
                "  TVA 19 %                                        1 045 000 FCFA\n"
                "  TOTAL TTC                                       6 545 000 FCFA\n"
                "\n"
                "Conditions : 30 % à la commande, solde à la livraison.\n"
                "Délai souhaité : 21 avril 2026.\n"
                "\n"
                "Seydou MAÏGA\n"
                "Directeur de la Communication — NIGELEC\n"
            ),
        },
        # ── SORTANT 1 ──────────────────────────────────────────────────────────
        {
            'type': 'pdf',
            'filename': 'OCR_SORTANT_1_Proposition.pdf',
            'title': 'OCR Test — Courrier sortant (proposition)',
            'content': (
                "IMAN COMMUNICATION DIGITALE\n"
                "Quartier Plateau — BP 1523 — Niamey, Niger\n"
                "contact@iman-digital.ne  |  +227 96 45 78 90\n"
                "\n"
                "Niamey, le 08 avril 2026\n"
                "\n"
                "De: IMAN Communication Digitale — Direction Commerciale\n"
                "À: Ministère de l'Agriculture — Direction de la Communication\n"
                "\n"
                "Réf.: IMAN/PROP/2026/047\n"
                "Objet: Proposition commerciale — Campagne digitale sensibilisation agricole\n"
                "\n"
                "Monsieur le Directeur,\n"
                "\n"
                "Nous avons l'honneur de vous soumettre notre proposition commerciale\n"
                "en réponse à votre appel à manifestation d'intérêt du 28 mars 2026.\n"
                "\n"
                "Nous vous proposons une campagne digitale complète articulée autour\n"
                "de trois axes :\n"
                "\n"
                "  Phase 1 — Diagnostic et stratégie (2 semaines)\n"
                "    • Analyse de l'audience cible\n"
                "    • Définition des messages clés\n"
                "    • Planning de contenu\n"
                "\n"
                "  Phase 2 — Production de contenus (3 semaines)\n"
                "    • 30 visuels pédagogiques (techniques agricoles)\n"
                "    • 5 vidéos courtes sous-titrées (Haoussa + Zarma)\n"
                "    • 2 infographies synthétiques\n"
                "\n"
                "  Phase 3 — Diffusion et animation (8 semaines)\n"
                "    • Gestion quotidienne Facebook + YouTube\n"
                "    • Publicités ciblées zones rurales\n"
                "    • Rapport hebdomadaire d'impact\n"
                "\n"
                "Budget global : 18 500 000 FCFA TTC\n"
                "Validité de l'offre : 30 jours\n"
                "\n"
                "Nous vous prions de croire, Monsieur le Directeur, en l'assurance\n"
                "de notre entière disponibilité.\n"
                "\n"
                "Aminata SANI\n"
                "Directrice Commerciale — IMAN Communication Digitale\n"
            ),
        },
        # ── SORTANT 2 ──────────────────────────────────────────────────────────
        {
            'type': 'pdf',
            'filename': 'OCR_SORTANT_2_Reponse_reclamation.pdf',
            'title': 'OCR Test — Réponse à réclamation (sortant)',
            'content': (
                "IMAN COMMUNICATION DIGITALE\n"
                "Quartier Plateau — BP 1523 — Niamey, Niger\n"
                "contact@iman-digital.ne  |  +227 96 45 78 90\n"
                "\n"
                "Niamey, le 10/04/2026\n"
                "\n"
                "De: IMAN Communication Digitale — Direction Générale\n"
                "À: CCIN — Direction des Affaires Juridiques — Mme Aïchatou CHAIBOU\n"
                "\n"
                "Réf.: IMAN/DG/2026/REP-084\n"
                "V/Réf: CCIN/SC/2026/RE-042 du 03/04/2026\n"
                "Objet: Réponse à votre réclamation — Projet site e-commerce CCIN\n"
                "\n"
                "Madame la Directrice,\n"
                "\n"
                "Nous accusons réception de votre courrier référencé ci-dessus et\n"
                "nous vous remercions de nous avoir fait part de vos préoccupations.\n"
                "\n"
                "Par la présente, nous tenons à vous informer que le retard constaté\n"
                "est principalement dû :\n"
                "\n"
                "  1. À des modifications importantes du cahier des charges validées\n"
                "     conjointement le 05/02/2026 (+12 jours estimés)\n"
                "  2. À une indisponibilité de votre équipe pour les tests de\n"
                "     recette du 01/03 au 10/03/2026 (+9 jours)\n"
                "\n"
                "Nous vous prions de bien vouloir noter que :\n"
                "  • La version beta est déployée et accessible sur notre serveur de\n"
                "    test depuis le 08/04/2026\n"
                "  • La livraison finale est prévue le 14/04/2026\n"
                "  • Nous renonçons à la facturation des avenants liés aux modifications\n"
                "    (économie de 1 200 000 FCFA pour votre organisation)\n"
                "\n"
                "Veuillez agréer, Madame la Directrice, l'expression de notre\n"
                "considération distinguée.\n"
                "\n"
                "Amadou BOUBACAR\n"
                "Directeur Général — IMAN Communication Digitale\n"
            ),
        },
        # ── SORTANT 3 ──────────────────────────────────────────────────────────
        {
            'type': 'pdf',
            'filename': 'OCR_SORTANT_3_Facture.pdf',
            'title': 'OCR Test — Facture sortante',
            'content': (
                "IMAN COMMUNICATION DIGITALE\n"
                "Quartier Plateau — BP 1523 — Niamey\n"
                "NIF: 12345/P — RC: NI-NIA-2020-B-1234\n"
                "\n"
                "FACTURE N° IMAN/FACT/2026/0112\n"
                "\n"
                "Date: 10/04/2026\n"
                "Échéance: 10/05/2026\n"
                "\n"
                "De: IMAN Communication Digitale\n"
                "À: NIGELEC — Direction Administrative et Financière — BP 11202 Niamey\n"
                "\n"
                "Réf.: IMAN/FACT/2026/0112\n"
                "Objet: Facture prestations Community Management — Mars 2026\n"
                "\n"
                "Suite à notre contrat IMAN/2026/NIGELEC/CM du 01/03/2026, nous vous\n"
                "prions de bien vouloir trouver ci-dessous le détail de notre facturation\n"
                "pour le mois de mars 2026 :\n"
                "\n"
                "  Gestion réseaux sociaux (Facebook + Instagram + LinkedIn)\n"
                "    30 publications organiques                    1 800 000 FCFA\n"
                "  Création contenus visuels\n"
                "    15 visuels HD + 3 vidéos courtes             1 200 000 FCFA\n"
                "  Campagne Facebook Ads — mars 2026\n"
                "    Budget média 500 000 + gestion                  800 000 FCFA\n"
                "  Reportage photo (journée technique 15/03)         600 000 FCFA\n"
                "                                              ─────────────────\n"
                "  Sous-total HT                               4 400 000 FCFA\n"
                "  TVA 19 %                                      836 000 FCFA\n"
                "  TOTAL TTC                                   5 236 000 FCFA\n"
                "\n"
                "RIB : BIA Niger — 001 015 0123456789012\n"
                "Merci de mentionner la référence lors du virement.\n"
                "\n"
                "Amadou BOUBACAR\n"
                "Directeur Général\n"
            ),
        },
    ]

    created = 0
    for doc in docs:
        fp = folder / doc['filename']
        try:
            if doc['type'] == 'pdf':
                generate_pdf(fp, doc['title'], doc['content'])
                print(f"  ✅ PDF : {doc['filename']}")
            created += 1
        except Exception as e:
            print(f"  ❌ Erreur {doc['filename']}: {e}")

    print(f"\n  🎯 {created}/{len(docs)} documents OCR créés")
    print("  📌 Chaque document contient : De, À, Réf., Objet, Date => extraction garantie\n")


def main():
    """Fonction principale pour générer tous les courriers de test"""
    print("🚀 Génération des courriers de test pour Iman...\n")
    
    # Créer le dossier de test
    test_folder = create_test_folder()
    print(f"📁 Dossier créé: {test_folder.absolute()}\n")
    
    # Liste des courriers à générer
    documents = [
        {
            'type': 'pdf',
            'filename': 'Demande_Devis_Site_Web_SONITEL.pdf',
            'title': 'Demande de devis - Refonte site web',
            'content': '''SOCIÉTÉ NIGÉRIENNE DES TÉLÉCOMMUNICATIONS (SONITEL)
Avenue de la Mairie - BP 208 - Niamey, Niger
Tél: +227 20 73 24 18

                        Niamey, le 15 mars 2026

À l'attention de
Monsieur le Directeur Général
IMAN Communication Digitale
Quartier Plateau - Niamey

Objet: Demande de devis pour refonte de site web d'entreprise
Référence: SONITEL/DG/2026/042

Monsieur le Directeur,

Dans le cadre de notre stratégie de transformation digitale, la SONITEL souhaite procéder à la refonte complète de son site web institutionnel.

CAHIER DES CHARGES:
• Site web responsive (mobile, tablette, desktop)
• Interface moderne et ergonomique
• Espace client sécurisé
• Module de paiement en ligne
• Système de gestion de contenu (CMS)
• Intégration API pour suivi consommation
• Multilingue (Français, Haoussa, Zarma)

LIVRABLES ATTENDUS:
- Maquettes graphiques (3 propositions)
- Développement front-end et back-end
- Formation des administrateurs
- Maintenance 12 mois

Budget indicatif: 15 000 000 FCFA
Délai souhaité: 3 mois

Nous vous prions de nous faire parvenir votre proposition commerciale détaillée avant le 30 mars 2026.

Cordialement,

Moussa IBRAHIM
Directeur Général
SONITEL'''
        },
        {
            'type': 'docx',
            'filename': 'Proposition_Commerciale_Campagne_SNV.docx',
            'title': 'Proposition commerciale - Campagne digitale',
            'content': '''IMAN COMMUNICATION DIGITALE
Quartier Plateau, Rue des Ambassades
BP 1523 - Niamey, Niger
contact@iman-digital.ne | +227 96 45 78 90

                    PROPOSITION COMMERCIALE

Client: Société Nigérienne de Vente (SNV)
Date: 20 mars 2026
Référence: IMAN/PROP/2026/018
Validité: 30 jours

OBJET: Campagne digitale pour lancement nouveau produit

Cher Client,

Suite à notre entretien du 18 mars 2026, nous avons le plaisir de vous soumettre notre proposition pour la campagne de lancement de votre nouvelle gamme de smartphones.

STRATÉGIE PROPOSÉE:

Phase 1 - Teasing (2 semaines)
• Création de contenus mystère sur les réseaux sociaux
• Campagne Google Ads ciblée
• Partenariat avec 5 influenceurs nigériens

Phase 2 - Lancement (1 semaine)
• Événement live Facebook + Instagram
• Vidéo publicitaire professionnelle 60s
• Articles sponsorisés médias en ligne
• Jeu concours avec dotations

Phase 3 - Conversion (3 semaines)
• Publicités Facebook/Instagram (reach + conversion)
• Campagne d'emailing (15 000 contacts)
• Retargeting display
• Community management quotidien

BUDGET DÉTAILLÉ:
Création de contenus: 3 500 000 FCFA
Médias sociaux: 4 200 000 FCFA
Production vidéo: 2 800 000 FCFA
Influenceurs: 1 500 000 FCFA
Community management (6 semaines): 1 200 000 FCFA

TOTAL HT: 13 200 000 FCFA
TVA 19%: 2 508 000 FCFA
TOTAL TTC: 15 708 000 FCFA

Délai de réalisation: 6 semaines

Nous restons à votre disposition pour tout complément d'information.

Cordialement,

Aminata SANI
Directrice Commerciale
IMAN Communication Digitale'''
        },
        {
            'type': 'pdf',
            'filename': 'Facture_Client_Orange_Niger.pdf',
            'title': 'Facture n° 2026-089',
            'content': '''IMAN COMMUNICATION DIGITALE
Quartier Plateau - BP 1523 - Niamey
NIF: 12345/P - RC: NI-NIA-2020-B-1234
Tél: +227 96 45 78 90

                            FACTURE

N° 2026-089
Date: 28 février 2026
Échéance: 30 mars 2026

CLIENT:
Orange Niger SA
Boulevard Mali Béro
BP 333 - Niamey

PRESTATIONS:

1. Community Management - Février 2026
   Gestion Facebook + Instagram + Twitter
   30 publications organiques
   20h de réponses commentaires/messages              1 800 000 FCFA

2. Création de contenus visuels
   15 visuels pour réseaux sociaux
   3 vidéos courtes (stories)                         1 200 000 FCFA

3. Campagne publicitaire Facebook Ads
   Budget média: 500 000 FCFA
   Gestion de campagne                                  800 000 FCFA

4. Reportage photo événement 4G
   Shooting 1 journée + retouches                       600 000 FCFA

                                                    _______________
Sous-total HT                                        4 400 000 FCFA
TVA 19%                                                836 000 FCFA
                                                    _______________
TOTAL TTC                                            5 236 000 FCFA

Conditions de paiement: 30 jours
Mode de paiement: Virement bancaire
RIB: BIA Niger - 001 015 0123456789012

Merci de mentionner le numéro de facture lors du paiement.

Le Directeur Général
Amadou BOUBACAR'''
        },
        {
            'type': 'docx',
            'filename': 'Commande_Branding_Hotel_Sahel.docx',
            'title': 'Bon de commande - Identité visuelle',
            'content': '''HÔTEL SAHEL PALACE
Avenue Méditerranée - Niamey
Tél: +227 20 73 45 67

                        BON DE COMMANDE

N° BC-2026/025
Date: 10 mars 2026

Fournisseur:
IMAN Communication Digitale
Quartier Plateau - Niamey

Objet: Création d'identité visuelle complète

Prestations commandées:

1. IDENTITÉ VISUELLE
   • Création logo (3 propositions)
   • Déclinaison charte graphique
   • Guide d'utilisation brand book

2. SUPPORTS PRINT
   • Carte de visite (design + impression 500 ex)
   • Papier à en-tête (design + impression 200 ex)
   • Enveloppes DL (design + impression 200 ex)
   • Flyers A5 (design + impression 1000 ex)

3. SUPPORTS DIGITAUX
   • Signature email
   • Templates réseaux sociaux (10 modèles)
   • Bannières web (3 formats)

Montant total: 6 500 000 FCFA TTC
(selon devis IMAN/2026/045 accepté)

Délai de livraison: 45 jours
Modalités de paiement: 40% à la commande, 60% à la livraison

Date de livraison souhaitée: 25 avril 2026

Fait à Niamey, le 10 mars 2026

Pour l'Hôtel Sahel Palace          Pour IMAN Communication
Signature et cachet                Signature et cachet'''
        },
        {
            'type': 'pdf',
            'filename': 'Demande_Support_Maintenance_Site.pdf',
            'title': 'Demande de support technique',
            'content': '''CHAMBRES DES MÉTIERS DU NIGER
Boulevard de l'Indépendance - Niamey
contact@chambresmetiers.ne

                        Niamey, le 25 mars 2026

À IMAN Communication Digitale
Service Technique
Niamey

Objet: Demande d'intervention - Site web inaccessible
Urgence: HAUTE

Messieurs,

Nous vous informons que notre site web www.chambresmetiers.ne est inaccessible depuis ce matin 8h00.

SYMPTÔMES CONSTATÉS:
• Message erreur 500 - Internal Server Error
• Impossible d'accéder au back-office
• Emails de contact non reçus

IMPACT:
• Les artisans ne peuvent plus s'inscrire en ligne
• Perte de visibilité et d'activité
• Échéance inscription salon dans 3 jours

Nous vous demandons une intervention en urgence aujourd'hui même.

Merci de nous tenir informés de l'avancement par téléphone au +227 90 12 34 56.

Dans l'attente,

Boubacar MOUSSA
Secrétaire Général
Tél: +227 90 12 34 56'''
        },
        {
            'type': 'docx',
            'filename': 'Devis_Formation_Reseaux_Sociaux.docx',
            'title': 'Devis - Formation réseaux sociaux',
            'content': '''IMAN COMMUNICATION DIGITALE
Centre de Formation Certifié
Niamey, Niger

                            DEVIS

Client: Ministère du Commerce et de la Promotion du Secteur Privé
Date: 18 mars 2026
Référence: IMAN/FORM/2026/012
Validité: 45 jours

OBJET: Formation "Community Management et Réseaux Sociaux"

PROGRAMME DE FORMATION (5 jours - 35 heures):

JOUR 1 - Introduction aux réseaux sociaux
• Panorama des plateformes (Facebook, Instagram, Twitter, LinkedIn)
• Enjeux pour les institutions publiques
• Bonnes pratiques et erreurs à éviter

JOUR 2 - Stratégie de contenu
• Ligne éditoriale et planning de publication
• Création de contenus engageants
• Outils de création graphique (Canva)

JOUR 3 - Community Management
• Gestion de communauté
• Modération et gestion de crise
• Analyse des performances

JOUR 4 - Facebook Business Manager
• Configuration compte professionnel
• Création de campagnes publicitaires
• Ciblage et optimisation budget

JOUR 5 - Instagram et LinkedIn
• Stories et Reels
• Instagram Shopping
• LinkedIn pour organisation

MODALITÉS:
Public: 15 participants (cadres communication)
Lieu: Salle de formation Iman (équipée)
Horaires: 9h-17h (pause déjeuner 12h-14h)
Support: Manuel + accès plateforme e-learning 3 mois

TARIFICATION:
Formation (5 jours x 15 participants): 4 500 000 FCFA
Supports pédagogiques: 300 000 FCFA
Pauses café + déjeuners: 1 200 000 FCFA

TOTAL HT: 6 000 000 FCFA
TVA 19%: 1 140 000 FCFA
TOTAL TTC: 7 140 000 FCFA

Dates proposées: 15-19 avril 2026

Formateurs certifiés:
• Aminata SANI - Expert Social Media (8 ans d'expérience)
• Ibrahim KONATE - Consultant Digital Marketing

Cordialement,
IMAN Communication Digitale'''
        },
        {
            'type': 'pdf',
            'filename': 'Reclamation_Retard_Livraison_Client.pdf',
            'title': 'Réclamation client - Retard projet',
            'content': '''ASSOCIATION DES FEMMES ENTREPRENEURES DU NIGER (AFEN)
Quartier Yantala - Niamey
Tél: +227 91 23 45 67

                        Niamey, le 22 mars 2026

RECOMMANDÉ AVEC AR

À Monsieur le Directeur Général
IMAN Communication Digitale
Quartier Plateau - Niamey

Objet: Réclamation - Retard de livraison projet site web
Référence projet: IMAN/2025/089

Monsieur le Directeur,

Nous nous permettons de vous écrire pour exprimer notre mécontentement concernant le retard important dans la livraison de notre site web.

RAPPEL DES FAITS:
• Contrat signé: 15 janvier 2026
• Délai contractuel: 60 jours (soit livraison le 16 mars 2026)
• Date du jour: 22 mars 2026 (6 jours de retard)
• Acompte versé: 4 000 000 FCFA (50%)

CONSÉQUENCES:
• Impossibilité de lancer la campagne de collecte de fonds
• Report de notre assemblée générale
• Perte de crédibilité auprès de nos partenaires

DEMANDES:
1. Livraison immédiate du site dans les 48h
2. Application de la pénalité contractuelle (2% par jour de retard)
3. Entretien avec votre direction pour garanties

Nous espérons une réponse rapide et une résolution urgente.

Sauf résolution sous 7 jours, nous serons contraints de saisir le Centre d'Arbitrage de la Chambre de Commerce.

Recevez, Monsieur le Directeur, nos salutations distinguées.

Mme Haoua HAMIDOU
Présidente AFEN'''
        },
        {
            'type': 'docx',
            'filename': 'Facture_Fournisseur_Hebergement.docx',
            'title': 'Facture fournisseur - Hébergement web',
            'content': '''NIGER DATACENTER SARL
Zone Industrielle - Niamey
NIF: 98765/P
Tél: +227 20 35 67 89

                            FACTURE

N° NDC-2026-0342
Date: 1er mars 2026
Échéance: 15 mars 2026

CLIENT:
IMAN Communication Digitale
Quartier Plateau - BP 1523
Niamey, Niger

DÉSIGNATION:

Hébergement mutualisé - Mars 2026
• 10 sites web hébergés
• Bande passante illimitée
• Sauvegardes quotidiennes
• Support technique 24/7
Pack Business                                           180 000 FCFA

Noms de domaine - Renouvellement annuel
• iman-digital.ne (1 an)                                 25 000 FCFA
• clients sites .ne x 5                                 125 000 FCFA

Certificats SSL
• 6 certificats SSL Premium                              90 000 FCFA

                                                    _______________
Sous-total HT                                           420 000 FCFA
TVA 19%                                                  79 800 FCFA
                                                    _______________
TOTAL TTC                                               499 800 FCFA

Modalités de paiement:
Virement bancaire sous 15 jours
Banque ECOBANK Niger
IBAN: NE001001012345678901234

En cas de retard: pénalités 2% + suspension service après 30 jours

Le Directeur Commercial
Issoufou GARBA

Niger Datacenter SARL
www.nigerdatacenter.ne'''
        },
        {
            'type': 'pdf',
            'filename': 'Contrat_Prestation_Community_Management.pdf',
            'title': 'Contrat de prestation - Community Management',
            'content': '''CONTRAT DE PRESTATION DE SERVICES
Community Management

Entre les soussignés:

1) IMAN Communication Digitale
Quartier Plateau - BP 1523 - Niamey
NIF: 12345/P - RC: NI-NIA-2020-B-1234
Représentée par M. Amadou BOUBACAR, Directeur Général
Ci-après dénommée "Le Prestataire"

ET

2) NIGELEC (Société Nigérienne d'Électricité)
Boulevard de la République - Niamey
Représentée par M. Seydou MAÏGA, Directeur Communication
Ci-après dénommée "Le Client"

ARTICLE 1 - OBJET
Le Prestataire s'engage à assurer la gestion complète des réseaux sociaux du Client selon les modalités définies ci-après.

ARTICLE 2 - PRESTATIONS
2.1 Gestion quotidienne des pages:
• Facebook (page entreprise + 2 pages régionales)
• LinkedIn (page entreprise)
• Twitter (compte officiel)

2.2 Services inclus:
• Création et publication de contenus (15 posts/semaine)
• Modération et réponses aux commentaires
• Veille et gestion de l'e-réputation
• Reporting mensuel avec statistiques

ARTICLE 3 - DURÉE
Contrat d'une durée de 12 mois renouvelable
Début: 1er avril 2026
Fin: 31 mars 2027

ARTICLE 4 - TARIF
Forfait mensuel: 2 500 000 FCFA HT
TVA 19%: 475 000 FCFA
Total TTC mensuel: 2 975 000 FCFA

Facturation: chaque 1er du mois
Paiement: sous 30 jours

ARTICLE 5 - RÉSILIATION
Préavis de résiliation: 3 mois
Résiliation possible à tout moment en cas de manquement grave

Fait à Niamey, le 15 mars 2026
En 2 exemplaires originaux

Pour IMAN Communication          Pour NIGELEC
Amadou BOUBACAR                  Seydou MAÏGA
DG                               Directeur Communication

Signature et cachet              Signature et cachet'''
        },
        {
            'type': 'docx',
            'filename': 'Reponse_Appel_Offres_Ministere.docx',
            'title': 'Réponse à appel d\'offres',
            'content': '''IMAN COMMUNICATION DIGITALE
Quartier Plateau - Niamey
NIF: 12345/P

                        Niamey, le 20 mars 2026

À Monsieur le Secrétaire Général
Ministère de la Santé Publique
Boulevard de l'Hôpital - Niamey

Objet: Réponse à l'Appel d'Offres n° MSP/AO/2026/008
"Campagne de sensibilisation digitale sur la vaccination"

Monsieur le Secrétaire Général,

Nous avons l'honneur de répondre à votre appel d'offres relatif à la campagne de communication digitale pour la promotion de la vaccination auprès des jeunes mères.

NOTRE COMPRÉHENSION DU PROJET:
Le Ministère souhaite toucher 500 000 femmes en âge de procréer à travers une campagne digitale innovante et impactante sur 6 mois.

NOTRE PROPOSITION:

1. STRATÉGIE DIGITALE
• Campagne multi-plateformes (Facebook, WhatsApp, SMS)
• Création de contenus en langues locales (Haoussa, Zarma, Peul)
• Partenariat avec influenceuses mamans nigériennes
• Chatbot WhatsApp pour information et prise de RDV

2. PRODUCTION DE CONTENUS
• 12 vidéos témoignages (femmes vaccinées)
• 50 visuels pédagogiques animés
• 24 spots radio pour relai
• Formation de 20 ambassadrices vaccination

3. DIFFUSION ET ANIMATION
• Gestion campagnes Facebook Ads (ciblage précis)
• Animation quotidienne des pages
• Webinaire mensuel avec professionnels de santé
• Jeux concours éducatifs

BUDGET GLOBAL: 45 000 000 FCFA TTC
(Détail en annexe)

ÉQUIPE DÉDIÉE:
• Chef de projet: 1 personne à temps plein
• Community managers: 2 personnes
• Créatifs: 3 personnes
• Data analyst: 1 personne

DÉLAI: 6 mois (Mai - Octobre 2026)

RÉFÉRENCES:
• Campagne UNICEF Niger (2024)
• Projet SNU "Éducation des filles" (2025)
• Orange Niger - Campagne santé mobile (2025)

Pièces jointes (11 documents):
✓ Formulaire DC1 complété
✓ Attestation fiscale
✓ Registre de commerce
✓ Références clients (3)
✓ CVs équipe
✓ Planning détaillé
✓ Budget détaillé
✓ etc.

Nous restons à votre disposition.

Cordialement,

Amadou BOUBACAR
Directeur Général
IMAN Communication Digitale'''
        },
        {
            'type': 'pdf',
            'filename': 'Rapport_Mensuel_Activite_Client.pdf',
            'title': 'Rapport mensuel d\'activité',
            'content': '''IMAN COMMUNICATION DIGITALE

        RAPPORT MENSUEL D'ACTIVITÉ RÉSEAUX SOCIAUX
                    Février 2026

Client: AIR TRANSPORT NIGER (ATN)
Période: 1er - 28 février 2026

═══════════════════════════════════════════════

RÉSUMÉ EXÉCUTIF

▸ Croissance de l'audience: +12%
▸ Engagement global: +18%
▸ Portée totale: 285 000 personnes
▸ Taux d'interaction moyen: 4.2%

═══════════════════════════════════════════════

1. FACEBOOK - @AirTransportNiger

Statistiques:
• Abonnés: 18 500 (+1 200 vs janvier)
• Publications: 22 posts
• Portée: 195 000 personnes
• Engagement: 8 200 interactions
• Messages reçus: 145 (tous répondus en <2h)

Top 3 publications:
1. Vidéo nouvelle desserte Agadez (12 500 vues)
2. Promo Niamey-Abidjan (2 100 partages)
3. Célébration 10 ans ATN (5 600 likes)

2. INSTAGRAM - @airtransportniger

Statistiques:
• Abonnés: 8 900 (+650 vs janvier)
• Publications: 18 posts + 42 stories
• Portée: 52 000 comptes atteints
• Engagement: 3 800 interactions

Meilleure story: Coulisses cockpit (18 500 vues)

3. LINKEDIN - Air Transport Niger

Statistiques:
• Abonnés: 3 200 (+180 vs janvier)
• Publications: 8 posts professionnels
• Impressions: 38 000
• Engagement: 890 interactions

4. CAMPAGNE PUBLICITAIRE

Budget dépensé: 450 000 FCFA
Résultats:
• 125 000 personnes touchées
• 850 clics vers site web
• 23 réservations directes
• Coût par clic: 529 FCFA

5. GESTION DE COMMUNAUTÉ

• 145 messages privés traités
• 312 commentaires modérés
• 18 demandes d'information vol
• 5 réclamations gérées (toutes résolues)
• Temps de réponse moyen: 1h20

6. RECOMMANDATIONS MARS 2026

✓ Lancer campagne vidéo "Sécurité aérienne"
✓ Collaborer avec influenceurs voyage nigériens
✓ Augmenter budget pub pour Pâques (+30%)
✓ Créer concours "Gagnez vos billets"

═══════════════════════════════════════════════

Rapport établi par:
Équipe Community Management IMAN
Contact: cm@iman-digital.ne

Niamey, le 5 mars 2026'''
        }
    ]
    documents = [
        {
            'type': 'pdf',
            'filename': 'Convocation_Reunion_Service.pdf',
            'title': 'Convocation à une réunion de service',
            'content': '''MINISTÈRE DE L'ADMINISTRATION TERRITORIALE
Direction des Ressources Humaines

                            CONVOCATION

Objet: Réunion de service mensuelle
Référence: DRH/2026/0342
Date: Le 25 mars 2026

Monsieur/Madame,

Vous êtes convoqué(e) à la réunion mensuelle du service qui se tiendra:

Date: Lundi 8 avril 2026
Heure: 10h00
Lieu: Salle de conférence A - Bâtiment administratif

Ordre du jour:
1. Approbation du procès-verbal de la réunion précédente
2. Point sur l'état d'avancement des projets en cours
3. Présentation du nouveau système de gestion documentaire
4. Planification des activités du mois d'avril
5. Questions diverses

Votre présence est obligatoire. En cas d'empêchement majeur, merci de prévenir le secrétariat au moins 48h à l'avance.

Le Chef de Service
Amadou DIALLO'''
        },
        {
            'type': 'docx',
            'filename': 'Notification_Conge_Accorde.docx',
            'title': 'Notification de congé accordé',
            'content': '''RÉPUBLIQUE DU SÉNÉGAL
Un Peuple - Un But - Une Foi

MINISTÈRE DE LA FONCTION PUBLIQUE
Direction Générale de la Fonction Publique

                    NOTIFICATION DE CONGÉ

N° 2026/DGFP/875

Par la présente, nous avons l'honneur de vous notifier que votre demande de congé annuel a été acceptée dans les conditions suivantes:

Bénéficiaire: Mme Fatou SARR
Matricule: 2019-0456
Service: Direction de la Comptabilité

Période de congé:
Du 15 avril 2026 au 30 avril 2026 (15 jours ouvrables)

Observations:
Votre dossier est complet. Vous êtes prié(e) de bien vouloir passer au bureau du personnel avant votre départ pour retirer votre ordre de mission.

À votre retour, vous devrez impérativement vous présenter au service pour la reprise de service.

Nous vous souhaitons un excellent repos.

Fait à Dakar, le 20 mars 2026

Le Directeur des Ressources Humaines
Ibrahim KANE'''
        },
        {
            'type': 'pdf',
            'filename': 'Demande_Fournitures_Bureau.pdf',
            'title': 'Demande de fournitures de bureau',
            'content': '''DIRECTION DES SERVICES GÉNÉRAUX
Service de la Logistique

                    DEMANDE DE FOURNITURES

Référence: DSG/LOG/2026/127
Date: 22 mars 2026

Service demandeur: Direction de la Comptabilité
Responsable: M. Moussa NDIAYE

Liste des fournitures demandées:

PAPETERIE:
- Ramettes de papier A4 (80g): 50 paquets
- Stylos billes (bleu): 100 unités
- Stylos billes (rouge): 50 unités
- Marqueurs permanents: 30 unités
- Agrafeuses: 10 unités
- Boîtes d'agrafes: 50 boîtes

CONSOMMABLES INFORMATIQUES:
- Toner pour imprimante HP LaserJet: 5 cartouches
- Toner couleur pour imprimante Canon: 3 jeux
- Clés USB 32 Go: 20 unités

CLASSEMENT:
- Classeurs à levier: 100 unités
- Chemises cartonnées: 200 unités
- Pochettes plastiques perforées: 500 unités

Motif: Renouvellement stock trimestriel
Budget disponible: Oui
Imputation budgétaire: Ligne 2026-22-01

Demandeur: M. Moussa NDIAYE
Visa du chef de service: Amadou DIALLO'''
        },
        {
            'type': 'docx',
            'filename': 'Reponse_Reclamation_Citoyen.docx',
            'title': 'Réponse à une réclamation',
            'content': '''COMMUNE DE DAKAR
Cabinet du Maire

Dakar, le 28 mars 2026

Objet: Réponse à votre réclamation n°2026/RC/0234
Référence: Votre courrier du 15 mars 2026

Monsieur Oumar FALL
Quartier Liberté 6
Dakar

Monsieur,

Nous accusons réception de votre courrier en date du 15 mars 2026, par lequel vous nous faites part de votre préoccupation concernant l'éclairage public défaillant dans votre quartier.

Nous tenons à vous informer que votre réclamation a retenu toute notre attention et a été transmise au Service Technique Municipal pour traitement.

À cet effet, nous avons le plaisir de vous communiquer que:

1. Une mission de constat a été effectuée le 20 mars 2026
2. Les travaux de réparation sont programmés pour la semaine du 1er au 5 avril 2026
3. Le remplacement de 12 lampadaires défectueux sera effectué
4. L'entretien général du réseau électrique du quartier sera réalisé

Nous vous remercions pour votre vigilance citoyenne qui nous permet d'améliorer continuellement nos services.

Veuillez agréer, Monsieur, l'expression de notre considération distinguée.

Le Maire
Cheikh Tidiane DIEYE'''
        },
        {
            'type': 'pdf',
            'filename': 'Note_Service_Horaires_Ramadan.pdf',
            'title': 'Note de service - Aménagement horaires',
            'content': '''PRÉSIDENCE DE LA RÉPUBLIQUE
Secrétariat Général du Gouvernement

                    NOTE DE SERVICE N° 08/2026

Objet: Aménagement des horaires de travail pendant le mois de Ramadan
Date: 10 mars 2026

LE SECRÉTAIRE GÉNÉRAL DU GOUVERNEMENT

À Mesdames et Messieurs les Ministres,
À Mesdames et Messieurs les Directeurs Généraux,

J'ai l'honneur de porter à votre connaissance que, conformément aux dispositions réglementaires en vigueur, les horaires de travail seront aménagés pendant le mois de Ramadan comme suit:

HORAIRES POUR LES SERVICES ADMINISTRATIFS:

Du lundi au jeudi:
- Matin: 8h00 à 15h00 (pause de 12h00 à 12h30)
- Pas de travail l'après-midi

Vendredi:
- Matin uniquement: 8h00 à 13h00

DISPOSITIONS PARTICULIÈRES:

1. Les services essentiels et de permanence maintiennent leur fonctionnement normal
2. Les agents ayant des missions terrain doivent coordonner avec leur hiérarchie
3. Les réunions interministérielles sont à programmer entre 9h00 et 13h00

Période d'application: Du 11 mars au 9 avril 2026

Fait à Dakar, le 10 mars 2026

Le Secrétaire Général du Gouvernement
Abdoulaye MBAYE'''
        },
        {
            'type': 'docx',
            'filename': 'Lettre_Felicitations_Agent.docx',
            'title': 'Lettre de félicitations',
            'content': '''MINISTÈRE DE L'ÉDUCATION NATIONALE
Direction des Ressources Humaines

Dakar, le 18 mars 2026

                    LETTRE DE FÉLICITATIONS

À Madame Aïssatou DIOP
Inspectrice de l'Enseignement
Académie de Thiès

Madame l'Inspectrice,

J'ai le plaisir de vous adresser mes plus vives félicitations pour l'excellence de votre travail durant l'année scolaire 2025-2026.

Votre engagement remarquable dans:
• L'amélioration du taux de réussite de votre circonscription (+18%)
• La formation continue des enseignants (25 sessions organisées)
• Le suivi pédagogique de 45 établissements
• L'innovation pédagogique avec l'introduction du numérique éducatif

Ces résultats exceptionnels témoignent de votre professionnalisme et de votre dévouement au service de l'éducation nationale.

Votre action contribue significativement à l'atteinte des objectifs du Plan Sectoriel de l'Éducation.

En reconnaissance de votre mérite, votre dossier sera présenté à la prochaine commission d'avancement.

Je vous encourage à poursuivre dans cette voie d'excellence.

Veuillez agréer, Madame l'Inspectrice, l'expression de ma haute considération.

Le Ministre de l'Éducation Nationale
Professeur Mamadou TALLA'''
        },
        {
            'type': 'pdf',
            'filename': 'Demande_Autorisation_Absence.pdf',
            'title': 'Demande d\'autorisation d\'absence',
            'content': '''DEMANDE D'AUTORISATION D'ABSENCE

Nom et Prénoms: SECK Mariama
Matricule: 2020-0892
Fonction: Secrétaire Administrative
Service: Direction des Affaires Administratives

Objet de la demande: Autorisation d'absence pour raisons médicales

Madame la Directrice,

J'ai l'honneur de solliciter de votre haute bienveillance une autorisation d'absence pour raisons médicales.

Détails de la demande:
- Date: Jeudi 4 avril 2026
- Durée: Journée complète
- Motif: Rendez-vous médical spécialisé (certificat médical joint)

Je m'engage à:
• Rattraper le travail en retard dès mon retour
• Informer ma collègue Mme FALL des dossiers urgents en cours
• Rester joignable par téléphone en cas d'urgence absolue

Pièces jointes:
- Convocation médicale
- Certificat médical

Dans l'attente d'une suite favorable, je vous prie d'agréer, Madame la Directrice, l'expression de ma respectueuse considération.

Fait à Dakar, le 25 mars 2026

Signature:
Mariama SECK

AVIS DU CHEF DE SERVICE:
☐ Favorable      ☐ Défavorable

Date et signature:'''
        },
        {
            'type': 'docx',
            'filename': 'Ordre_Mission_Deplacement.docx',
            'title': 'Ordre de mission',
            'content': '''RÉPUBLIQUE DU SÉNÉGAL
Un Peuple - Un But - Une Foi

MINISTÈRE DES FINANCES ET DU BUDGET
Direction Générale du Budget

                    ORDRE DE MISSION N° 2026/DGB/185

Le Directeur Général du Budget

Autorise

Monsieur Cheikh DIALLO
Fonction: Contrôleur des Finances
Service: Direction du Contrôle Budgétaire

À se rendre:
Destination: Saint-Louis, Région du Nord
Période: Du 10 au 14 avril 2026 (5 jours)

Objet de la mission:
1. Audit du budget régional exercice 2025
2. Formation des comptables publics sur le nouveau système SIGFIP
3. Évaluation des projets d'investissement en cours
4. Rencontre avec les autorités régionales

Moyens de transport: Véhicule administratif (Toyota Hilux - Imm. DK-2345-A)
Prise en charge: Per diem réglementaire + frais de carburant

Budget: Ligne budgétaire 2026-66-02-21
Montant global: 350 000 FCFA

Observations:
- Rapport de mission à remettre dans les 7 jours suivant le retour
- Photos et compte-rendu des formations dispensées
- États de présence signés par les bénéficiaires

Fait à Dakar, le 2 avril 2026

Le Directeur Général du Budget
Abdoul Aziz WANE

Cachet officiel'''
        },
        {
            'type': 'pdf',
            'filename': 'Appel_Cotisation_Mutuelle.pdf',
            'title': 'Appel de cotisation',
            'content': '''MUTUELLE DES AGENTS DE L'ÉTAT
Siège Social: Avenue Bourguiba, Dakar

                    APPEL DE COTISATION
                    Exercice 2026 - 1er Trimestre

Référence: MAE/2026/COT-Q1/4523

Adhérent: M. Abdoulaye NIANG
N° adhérent: MAE-2019-3456
Service: Ministère de la Santé

Cher membre,

Nous vous prions de bien vouloir régler votre cotisation trimestrielle dans les délais suivants:

DÉTAIL DE LA COTISATION:

Cotisation principale (janvier-mars 2026):          15 000 FCFA
Cotisation enfants (3 ayants droit):                 9 000 FCFA
Assurance complémentaire:                            5 000 FCFA
                                                    ____________
TOTAL À PAYER:                                      29 000 FCFA

Date limite de paiement: 15 avril 2026

MODALITÉS DE PAIEMENT:
- Prélèvement automatique sur salaire (option recommandée)
- Virement bancaire: CBAO - RIB: SN08 01 015 03456789012 75
- Paiement au guichet: Siège de la mutuelle

RAPPEL DES AVANTAGES:
✓ Remboursement jusqu'à 80% des frais médicaux
✓ Prise en charge des hospitalisations
✓ Assurance vie et invalidité
✓ Aide scolaire annuelle

Pour toute information: (+221) 33 821 45 67 ou contact@mutuelle-etat.sn

Le Secrétaire Général
Mamadou FALL'''
        },
        {
            'type': 'docx',
            'filename': 'Courrier_Relance_Paiement.docx',
            'title': 'Courrier de relance',
            'content': '''AGENCE COMPTABLE DE L'ÉTAT
Service du Recouvrement

Dakar, le 20 mars 2026

LETTRE DE RELANCE N° 2026/ACE/REL/0892

Société: ENTREPRISE GENERALE DU BÂTIMENT (EGB SARL)
Adresse: Zone Industrielle, Rufisque
N° contribuable: 2015-B-4589

Objet: Relance pour paiement de facture impayée

Monsieur le Directeur Général,

Nous avons l'honneur de porter à votre connaissance que malgré nos précédents courriers, nous constatons que la facture ci-après demeure impayée:

RÉFÉRENCE DE LA CRÉANCE:
- Facture n°: F-2025/0234
- Date d'émission: 15 novembre 2025
- Montant: 4 500 000 FCFA
- Objet: Travaux de réfection Bureau du Ministère des Finances
- Échéance: 15 décembre 2025
- Retard: 95 jours

Ce retard de paiement entraîne:
• Pénalités de retard: 2% par mois (180 000 FCFA à ce jour)
• Inscription au fichier des mauvais payeurs
• Impossibilité de soumissionner aux prochains marchés publics

Nous vous invitons à régulariser votre situation dans un délai de 15 jours à compter de la réception de la présente.

Passé ce délai, nous serons contraints d'engager une procédure de recouvrement contentieux.

Pour tout renseignement: M. Alioune BA - Tél: (+221) 33 849 12 34

Veuillez agréer, Monsieur le Directeur Général, nos salutations distinguées.

Le Comptable Principal
Boubacar SARR'''
        },
        {
            'type': 'pdf',
            'filename': 'Notification_Mutation_Interne.pdf',
            'title': 'Notification de mutation',
            'content': '''MINISTÈRE DE L'INTÉRIEUR
Direction des Ressources Humaines

                    DÉCISION DE MUTATION INTERNE

N° 2026/MINT/DRH/MUT/045
Date: 15 mars 2026

LE MINISTRE DE L'INTÉRIEUR

Vu le Code de la fonction publique;
Vu le décret n° 2024-1234 portant organisation du Ministère de l'Intérieur;
Vu les nécessités de service;

DÉCIDE:

Article 1er: M. Omar DIAGNE, actuellement en service à la Direction de la Sécurité Publique de Dakar, est muté à la Préfecture de Kaolack en qualité de Chef de Division Administrative.

Article 2: Cette mutation prendra effet à compter du 1er mai 2026.

Article 3: L'intéressé conserve son grade, son échelon et ses émoluments.

Article 4: Les frais de déménagement seront pris en charge par l'administration conformément à la réglementation en vigueur (arrêté n° 2023-0567).

Article 5: M. Omar DIAGNE disposera d'un délai de trois (3) semaines pour rejoindre son nouveau poste.

Article 6: La présente décision sera notifiée à l'intéressé et aux services concernés.

Fait à Dakar, le 15 mars 2026

Le Ministre de l'Intérieur
Général Antoine Félix DIOME

Ampliation:
- Intéressé
- Direction de la Sécurité Publique - Dakar
- Préfecture de Kaolack
- Direction Administrative et Financière
- Archives'''
        },
        {
            'type': 'docx',
            'filename': 'Demande_Information_Administrative.docx',
            'title': 'Demande d\'information',
            'content': '''Monsieur Lamine THIAM
Avocat à la Cour
Cabinet THIAM & Associés
Rue Huart, Dakar

Dakar, le 22 mars 2026

À Monsieur le Directeur
Direction de l'Urbanisme et de l'Habitat
Ministère de l'Urbanisme
Dakar

Objet: Demande d'information sur procédure d'obtention de permis de construire
Référence: Dossier client n° 2026/CTH/089

Monsieur le Directeur,

J'ai l'honneur de solliciter de votre haute bienveillance les informations suivantes concernant la procédure d'obtention d'un permis de construire:

INFORMATIONS DEMANDÉES:

1. Liste exhaustive des pièces constitutives du dossier de demande de permis de construire pour un immeuble R+4 à usage d'habitation

2. Délais réglementaires d'instruction du dossier

3. Frais et taxes applicables (droits de timbre, redevances, etc.)

4. Conditions spécifiques pour les zones classées ou protégées

5. Procédure de recours en cas de refus

CONTEXTE:
Cette demande s'inscrit dans le cadre d'un projet immobilier que mon client, M. Moussa SALL, envisage de réaliser sur une parcelle sise à la VDN (Titre Foncier n° 12345/DK).

Je vous serais reconnaissant de bien vouloir me faire parvenir ces informations dans les meilleurs délais.

Veuillez agréer, Monsieur le Directeur, l'expression de ma haute considération.

Maître Lamine THIAM
Avocat à la Cour

Tél: (+221) 33 824 56 78
Email: l.thiam@cabinet-thiam.sn'''
        }
    ]
    
    # Générer chaque document
    created_count = 0
    for doc in documents:
        filepath = test_folder / doc['filename']
        
        try:
            if doc['type'] == 'pdf':
                generate_pdf(filepath, doc['title'], doc['content'])
                print(f"✅ PDF créé: {doc['filename']}")
            elif doc['type'] == 'docx':
                generate_docx(filepath, doc['title'], doc['content'])
                print(f"✅ DOCX créé: {doc['filename']}")
            elif doc['type'] == 'xlsx':
                generate_xlsx(filepath, doc['title'], doc['data'])
                print(f"✅ XLSX créé: {doc['filename']}")
            elif doc['type'] == 'image':
                generate_image(filepath, doc['title'])
                print(f"✅ Image créée: {doc['filename']}")
            
            created_count += 1
        except Exception as e:
            print(f"❌ Erreur pour {doc['filename']}: {e}")
    
    print(f"\n✨ {created_count}/{len(documents)} courriers créés avec succès!")
    print(f"📂 Emplacement: {test_folder.absolute()}")

    # --- Documents OCR parfaits ---
    print("\n🔍 Génération des documents OCR de test (structurés pour extraction automatique)...")
    generate_ocr_test_documents(base_path=str(test_folder / "ocr_test"))

    # Suggestions
    print("\n💡 Suggestions d'utilisation:")
    print("   • Utilisez ces courriers pour tester le registre de courrier")
    print("   • Testez la classification par type (entrant/sortant/interne)")
    print("   • Vérifiez l'affectation aux services et collaborateurs")
    print("   • Testez le workflow de traitement des courriers")
    print("   • Simulez des échéances et urgences")
    print("\n📋 Types de courriers générés (contexte Niger - Agence digitale):")
    print("   - Demandes de devis et appels d'offres")
    print("   - Propositions commerciales et contrats")
    print("   - Factures clients et fournisseurs")
    print("   - Réclamations et support technique")
    print("   - Rapports d'activité")
    print("   - Commandes et bons de livraison")


if __name__ == "__main__":
    main()
