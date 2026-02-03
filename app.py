import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import sqlite3

# --- CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("⚠️ Clé API manquante.")
    st.stop()

model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="ClaimCheck AI - Expert ANAM", page_icon="🇲🇦", layout="wide")

# --- CONNEXION BASE DE DONNÉES ---
def get_tarif(code_ou_nom, secteur):
    """Cherche le tarif dans la DB selon le secteur (PRIVE ou PUBLIC)"""
    conn = sqlite3.connect('claimcheck.db')
    c = conn.cursor()
    
    colonne_tarif = "tarif_prive" if secteur == "PRIVE" else "tarif_public"
    
    # 1. Chercher dans les Lettres Clés (C, K, B...)
    c.execute(f"SELECT {colonne_tarif}, description FROM lettres_cles WHERE code=?", (code_ou_nom,))
    res = c.fetchone()
    if res:
        conn.close()
        return {"type": "lettre", "valeur": res[0], "desc": res[1]}
    
    # 2. Chercher dans les Forfaits (Césarienne, Scanner...)
    c.execute(f"SELECT {colonne_tarif}, nom_acte FROM forfaits WHERE mots_cles LIKE ?", (f"%{code_ou_nom.lower()}%",))
    res = c.fetchone()
    conn.close()
    
    if res:
        return {"type": "forfait", "valeur": res[0], "desc": res[1]}
    
    return None

# --- FONCTIONS IA ---
def analyser_document(image):
    prompt = """
    Analyse ce document médical marocain.
    
    ÉTAPE 1 : IDENTIFICATION DU SECTEUR
    Cherche des indices :
    - PUBLIC : "Royaume du Maroc", "Ministère de la Santé", "CHU", "Hôpital Provincial".
    - PRIVÉ : "Clinique", "Cabinet", "Polyclinique", "Centre", "Dr".
    
    ÉTAPE 2 : EXTRACTION DES DONNÉES
    Extrais en JSON :
    {
        "secteur": "PRIVE" ou "PUBLIC",
        "etablissement": "Nom trouvé",
        "actes": [
            {
                "description": "Nom de l'acte (ex: Césarienne, Scanner, Consultation)",
                "code": "Lettre clé (ex: K, C, B) si visible",
                "coefficient": "Valeur du coeff (ex: 100, 20)",
                "montant_total": "Prix total facturé en DH"
            }
        ]
    }
    """
    try:
        response = model.generate_content([prompt, image])
        json_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(json_text)
    except:
        return None

# --- INTERFACE ---
st.title("ClaimCheck AI 🏥")
st.markdown("**Système d'Audit Tarifaire Intelligent (ANAM / CNSS / CNOPS)**")

col_upload, col_result = st.columns([1, 2])

with col_upload:
    uploaded_file = st.file_uploader("Scanner une facture ou feuille de soins", type=['jpg', 'png', 'jpeg'])
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Document", use_column_width=True)

with col_result:
    if uploaded_file and st.button("Lancer l'Audit de Conformité", type="primary"):
        with st.spinner("🔍 Analyse Sectorielle & Vérification BDD..."):
            data = analyser_document(image)
            
            if data:
                secteur = data.get("secteur", "PRIVE")
                etablissement = data.get("etablissement", "Non identifié")
                
                # En-tête du rapport
                if secteur == "PUBLIC":
                    st.info(f"🏛️ **Secteur Public Détecté** ({etablissement})\n\nApplication de la Grille Hôpitaux (K=13 DH, C=50 DH).")
                else:
                    st.warning(f"🏨 **Secteur Privé Détecté** ({etablissement})\n\nApplication de la Grille Cliniques (K=22.50 DH, C=80 DH).")
                
                st.divider()
                
                # Analyse ligne par ligne
                for acte in data.get("actes", []):
                    desc = acte.get("description", "Acte")
                    code = acte.get("code")
                    coeff = float(acte.get("coefficient") or 0)
                    prix_facture = float(acte.get("montant_total") or 0)
                    
                    # Recherche du tarif légal
                    ref = None
                    
                    # Stratégie de recherche
                    if code: # Si on a un code (ex: K100)
                        ref = get_tarif(code, secteur)
                        if ref and ref["type"] == "lettre":
                            prix_legal = ref["valeur"] * coeff
                        else:
                            prix_legal = 0
                    else: # Recherche par nom (ex: Césarienne)
                        ref = get_tarif(desc, secteur)
                        prix_legal = ref["valeur"] if ref else 0
                    
                    # Affichage du verdict
                    with st.container():
                        c1, c2, c3 = st.columns([3, 2, 2])
                        c1.write(f"**{desc}**")
                        if code: c1.caption(f"Code: {code} {coeff}")
                        
                        c2.write(f"Facturé: **{prix_facture} DH**")
                        
                        if prix_legal > 0:
                            diff = prix_facture - prix_legal
                            if diff > (prix_legal * 0.1): # Marge 10%
                                c3.error(f"❌ Ref: {prix_legal} DH")
                                st.write(f"⚠️ **Surfacturation de {diff} DH** par rapport au tarif réglementaire {secteur}.")
                            else:
                                c3.success(f"✅ Ref: {prix_legal} DH")
                        else:
                            c3.info("❓ Pas de ref")
                            st.caption("Acte non trouvé dans la base ANAM standard.")
                        st.divider()
            else:
                st.error("Erreur de lecture. Document illisible.")
