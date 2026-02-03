import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import sqlite3

# --- CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("⚠️ Clé API manquante. Configurez les secrets dans Streamlit.")
    st.stop()

model = genai.GenerativeModel('gemini-1.5-pro')

st.set_page_config(page_title="ClaimCheck AI - Expert", page_icon="🇲🇦", layout="wide")

# --- CERVEAU : CONNEXION BDD ---
def get_tarif_reference(nom_ou_code, secteur):
    """Cherche le prix officiel dans notre base de données"""
    conn = sqlite3.connect('claimcheck.db')
    c = conn.cursor()
    
    # On sélectionne la bonne colonne de prix
    colonne_prix = "tarif_prive" if secteur == "PRIVE" else "tarif_public"
    
    # 1. Est-ce une Lettre Clé ? (ex: K, C, B)
    c.execute(f"SELECT {colonne_prix}, description FROM lettres_cles WHERE code=?", (nom_ou_code.upper(),))
    res = c.fetchone()
    if res:
        conn.close()
        return {"type": "lettre", "valeur": res[0], "desc": res[1]}
        
    # 2. Est-ce un Forfait ? (ex: Césarienne)
    c.execute(f"SELECT {colonne_prix}, nom_acte FROM forfaits WHERE mots_cles LIKE ?", (f"%{nom_ou_code.lower()}%",))
    res = c.fetchone()
    conn.close()
    
    if res:
        return {"type": "forfait", "valeur": res[0], "desc": res[1]}
        
    return None

# --- YEUX : ANALYSE DOC (VERSION DEBUG) ---
def analyser_document_ia(image):
    prompt = """
    Tu es un auditeur médical expert au Maroc. Analyse ce document.
    
    ÉTAPE 1 : DÉTECTION DU SECTEUR
    - Si tu vois "Ministère de la Santé", "CHU", "Hôpital Provincial", "Royaume du Maroc" (logo) -> Secteur PUBLIC.
    - Si tu vois "Clinique", "Polyclinique", "Cabinet", "Centre Privé", "Dr" -> Secteur PRIVE.
    
    ÉTAPE 2 : EXTRACTION
    Réponds UNIQUEMENT avec un JSON valide, sans texte avant ni après, sous cette forme :
    {
        "secteur": "PUBLIC" ou "PRIVE",
        "etablissement": "Nom de l'hôpital ou clinique",
        "actes": [
            {
                "description": "Nom de l'acte",
                "code": "Lettre clé (K, B, C) ou null",
                "coefficient": "Valeur du coeff ou 0",
                "montant_facture": "Montant en DH ou 0"
            }
        ]
    }
    """
    try:
        response = model.generate_content([prompt, image])
        
        # --- DEBUG : ON AFFICHE CE QUE L'IA RACONTE ---
        st.write("🤖 **DEBUG - Réponse brute de l'IA :**")
        st.code(response.text) 
        # -----------------------------------------------

        # Nettoyage un peu plus agressif du JSON
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        
        # On tente de charger
        return json.loads(clean_json)

    except Exception as e:
        # ON AFFICHE L'ERREUR EXACTE
        st.error(f"⚠️ ERREUR TECHNIQUE : {e}")
        return None

# --- INTERFACE ---
st.title("ClaimCheck AI 🇲🇦")
st.markdown("### 🛡️ Audit de Facturation Médicale (Public & Privé)")

uploaded_file = st.file_uploader("Scanner le dossier", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Document reçu", width=400)
    
    if st.button("Lancer l'Audit"):
        with st.spinner("🕵️‍♂️ Analyse du secteur et des tarifs en cours..."):
            
            # 1. L'IA lit le document
            data = analyser_document_ia(image)
            
            if data:
                secteur = data.get("secteur", "PRIVE")
                nom_hopital = data.get("etablissement", "Inconnu")
                
                # 2. Affichage du Contexte
                if secteur == "PUBLIC":
                    st.info(f"🏛️ **Secteur Public Détecté** ({nom_hopital})\n\nApplication du Tarif Hôpital (K=13 DH).")
                else:
                    st.warning(f"🏨 **Secteur Privé Détecté** ({nom_hopital})\n\nApplication du Tarif Clinique (K=22.50 DH).")
                
                st.divider()
                
                # 3. Analyse ligne par ligne
                for acte in data.get("actes", []):
                    desc = acte.get("description", "Acte inconnu")
                    code = acte.get("code")
                    coeff = float(acte.get("coefficient") or 0)
                    prix_facture = float(acte.get("montant_facture") or 0)
                    
                    # On interroge la base de données
                    ref = None
                    prix_legal = 0
                    
                    if code: # Recherche par Code (K, B...)
                        ref = get_tarif_reference(code, secteur)
                        if ref and ref["type"] == "lettre":
                            prix_legal = ref["valeur"] * coeff
                    else: # Recherche par Nom (Césarienne...)
                        ref = get_tarif_reference(desc, secteur)
                        if ref: prix_legal = ref["valeur"]
                    
                    # Verdict
                    c1, c2, c3 = st.columns([3, 2, 2])
                    c1.write(f"**{desc}**")
                    if code: c1.caption(f"Code: {code} {coeff}")
                    
                    c2.write(f"Facturé: **{prix_facture} DH**")
                    
                    if prix_legal > 0:
                        diff = prix_facture - prix_legal
                        if diff > (prix_legal * 0.1): # Marge 10%
                            c3.error(f"❌ Ref: {prix_legal} DH")
                            st.write(f"⚠️ **Surfacturation de {diff} DH** detected!")
                        elif diff < -(prix_legal * 0.1):
                            c3.warning(f"⚠️ Ref: {prix_legal} DH")
                            st.write("Sous-facturation (Perte financière).")
                        else:
                            c3.success(f"✅ Ref: {prix_legal} DH")
                    else:
                        c3.info("❓ Pas de référence")
                    
                    st.divider()
                    
            else:
                st.error("Lecture impossible. Image trop floue ?")
