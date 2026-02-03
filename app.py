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

# --- DIAGNOSTIC (POUR VOIR CE QUI MARCHE VRAIMENT) ---
# Cela va afficher sur ton écran la liste des modèles disponibles
try:
    st.sidebar.write("🔍 **Diagnostic Modèles :**")
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    st.sidebar.code(available_models)
except Exception as e:
    st.sidebar.error(f"Erreur connexion API : {e}")

# --- CHANGEMENT DÉFINITIF DU MODÈLE ---
# On utilise 'gemini-pro' (le plus stable/compatible) au lieu de flash/1.5
try:
    model = genai.GenerativeModel('gemini-pro')
except:
    st.error("Impossible de charger le modèle standard.")
    st.stop()

st.set_page_config(page_title="ClaimCheck AI - Expert", page_icon="🇲🇦", layout="wide")

# --- CERVEAU : CONNEXION BDD ---
def get_tarif_reference(nom_ou_code, secteur):
    conn = sqlite3.connect('claimcheck.db')
    c = conn.cursor()
    colonne_prix = "tarif_prive" if secteur == "PRIVE" else "tarif_public"
    
    c.execute(f"SELECT {colonne_prix}, description FROM lettres_cles WHERE code=?", (nom_ou_code.upper(),))
    res = c.fetchone()
    if res:
        conn.close()
        return {"type": "lettre", "valeur": res[0], "desc": res[1]}
        
    c.execute(f"SELECT {colonne_prix}, nom_acte FROM forfaits WHERE mots_cles LIKE ?", (f"%{nom_ou_code.lower()}%",))
    res = c.fetchone()
    conn.close()
    
    if res:
        return {"type": "forfait", "valeur": res[0], "desc": res[1]}
    return None

# --- YEUX : ANALYSE DOC ---
def analyser_document_ia(image):
    # Prompt simplifié pour éviter les erreurs de parsing avec le vieux modèle
    prompt = """
    Analyse ce document médical marocain.
    Réponds UNIQUEMENT avec un JSON valide. Pas de texte avant ou après.
    
    Structure attendue :
    {
        "secteur": "PUBLIC" (si Ministère/CHU) ou "PRIVE" (si Clinique/Cabinet),
        "etablissement": "Nom visible",
        "actes": [
            {
                "description": "Nom acte",
                "code": "Code (K, B, C) ou null",
                "coefficient": 0,
                "montant_facture": 0
            }
        ]
    }
    """
    try:
        response = model.generate_content([prompt, image])
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"Erreur Lecture IA : {e}")
        return None

# --- INTERFACE ---
st.title("ClaimCheck AI 🇲🇦")
st.markdown("### 🛡️ Audit de Facturation Médicale (Public & Privé)")

uploaded_file = st.file_uploader("Scanner le dossier", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Document reçu", width=400)
    
    if st.button("Lancer l'Audit"):
        with st.spinner("🕵️‍♂️ Audit en cours..."):
            
            data = analyser_document_ia(image)
            
            if data:
                secteur = data.get("secteur", "PRIVE")
                nom_hopital = data.get("etablissement", "Inconnu")
                
                if secteur == "PUBLIC":
                    st.info(f"🏛️ **Secteur Public Détecté** ({nom_hopital}) -> Tarif Hôpital")
                else:
                    st.warning(f"🏨 **Secteur Privé Détecté** ({nom_hopital}) -> Tarif Clinique")
                
                st.divider()
                
                for acte in data.get("actes", []):
                    desc = acte.get("description", "Acte inconnu")
                    code = acte.get("code")
                    coeff = float(acte.get("coefficient") or 0)
                    prix_facture = float(acte.get("montant_facture") or 0)
                    
                    ref = None
                    prix_legal = 0
                    
                    if code: 
                        ref = get_tarif_reference(code, secteur)
                        if ref and ref["type"] == "lettre":
                            prix_legal = ref["valeur"] * coeff
                    else:
                        ref = get_tarif_reference(desc, secteur)
                        if ref: prix_legal = ref["valeur"]
                    
                    c1, c2, c3 = st.columns([3, 2, 2])
                    c1.write(f"**{desc}**")
                    if code: c1.caption(f"Code: {code} {coeff}")
                    c2.write(f"Facturé: **{prix_facture} DH**")
                    
                    if prix_legal > 0:
                        diff = prix_facture - prix_legal
                        if diff > (prix_legal * 0.1):
                            c3.error(f"❌ Ref: {prix_legal} DH")
                            st.write(f"⚠️ **Surfacturation de {diff} DH**")
                        else:
                            c3.success(f"✅ Ref: {prix_legal} DH")
                    else:
                        c3.info("❓ Pas de référence")
                    st.divider()
