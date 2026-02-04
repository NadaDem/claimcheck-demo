import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import sqlite3
import time

# --- CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("⚠️ Clé API manquante. Vérifiez les secrets Streamlit.")
    st.stop()

st.set_page_config(page_title="ClaimCheck AI - Expert", page_icon="🇲🇦", layout="wide")

# --- LISTE DE SÉCURITÉ BASÉE SUR TA LISTE EXACTE ---
# On priorise le "Lite" et le "Latest" qui sont les plus permissifs sur les quotas
MODELS_TO_TRY = [
    'models/gemini-2.0-flash-lite-001',  # TRES RAPIDE et économique (Priorité 1)
    'models/gemini-flash-latest',        # L'alias standard (Priorité 2)
    'models/gemini-2.0-flash',           # La version 2.0 standard (Priorité 3)
    'models/gemini-pro-latest'           # Le fallback Pro (Priorité 4)
]

# --- FONCTION ROBUSTE "PASSE-PARTOUT" ---
def ask_gemini_rotator(prompt, image):
    """Essaie les modèles de ta liste un par un jusqu'à ce que ça passe"""
    
    last_error = ""
    
    for model_name in MODELS_TO_TRY:
        try:
            # On tente avec le modèle courant
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([prompt, image])
            
            # Si on arrive ici, c'est que ça a marché !
            st.toast(f"✅ Succès avec : {model_name}", icon="🚀")
            return response.text
            
        except Exception as e:
            error_str = str(e)
            # Si c'est une erreur de quota (429) ou introuvable (404), on passe au suivant
            if "429" in error_str or "404" in error_str:
                continue
            else:
                last_error = error_str
    
    # Si on arrive ici, tous les modèles ont échoué
    st.error(f"❌ Tous les modèles sont indisponibles. Dernière erreur : {last_error}")
    return None

# --- CERVEAU : CONNEXION BDD ---
def get_tarif_reference(nom_ou_code, secteur):
    try:
        conn = sqlite3.connect('claimcheck.db')
        c = conn.cursor()
        colonne_prix = "tarif_prive" if secteur == "PRIVE" else "tarif_public"
        
        # 1. Recherche par Code Exact (K, B, C...)
        c.execute(f"SELECT {colonne_prix}, description FROM lettres_cles WHERE code=?", (nom_ou_code.upper(),))
        res = c.fetchone()
        if res:
            conn.close()
            return {"type": "lettre", "valeur": res[0], "desc": res[1]}
            
        # 2. Recherche par Mot Clé (Forfaits)
        c.execute(f"SELECT {colonne_prix}, nom_acte FROM forfaits WHERE mots_cles LIKE ?", (f"%{nom_ou_code.lower()}%",))
        res = c.fetchone()
        conn.close()
        
        if res:
            return {"type": "forfait", "valeur": res[0], "desc": res[1]}
    except:
        return None
    return None

# --- YEUX : ANALYSE DOC ---
def analyser_document_ia(image):
    prompt = """
    Tu es un expert en facturation médicale marocaine (CNSS/AMO). Analyse cette image.
    
    TA MISSION :
    1. Détermine si c'est un établissement PUBLIC (Hôpital, CHU) ou PRIVE (Clinique, Cabinet).
    2. Extrais les actes facturés.
    
    FORMAT DE RÉPONSE ATTENDU (JSON STRICT UNIQUEMENT) :
    {
        "secteur": "PUBLIC" ou "PRIVE",
        "etablissement": "Nom visible ou Inconnu",
        "actes": [
            {
                "description": "Nom de l'acte",
                "code": "Code si visible (ex: K, C, B) sinon null",
                "coefficient": "Valeur du coeff (ex: 50, 100) sinon 0",
                "montant_facture": "Montant total en DH"
            }
        ]
    }
    """
    
    json_text = ask_gemini_rotator(prompt, image)
    
    if json_text:
        try:
            # Nettoyage renforcé
            clean_json = json_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except:
            st.error("L'IA a répondu mais le format n'est pas lisible.")
            return None
    return None

# --- INTERFACE ---
st.title("ClaimCheck AI 🇲🇦")
st.caption("Mode : Expert | Modèle : Gemini 2.0 Flash Lite")

col_upload, col_result = st.columns([1, 2])

with col_upload:
    uploaded_file = st.file_uploader("Scanner un document", type=['jpg', 'png', 'jpeg'])
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Document à auditer", use_column_width=True)

with col_result:
    if uploaded_file and st.button("Lancer l'Audit", type="primary"):
        with st.spinner("⚡ Analyse intelligente en cours..."):
            
            data = analyser_document_ia(image)
            
            if data:
                secteur = data.get("secteur", "PRIVE").upper()
                nom_hopital = data.get("etablissement", "Non identifié")
                
                if secteur == "PUBLIC":
                    st.info(f"🏛️ **SECTEUR PUBLIC DÉTECTÉ**\n\nÉtablissement : {nom_hopital}\nGrille tarifaire : Hôpitaux (K=13 DH).")
                else:
                    st.warning(f"🏨 **SECTEUR PRIVÉ DÉTECTÉ**\n\nÉtablissement : {nom_hopital}\nGrille tarifaire : Cliniques (K=22.50 DH).")
                
                st.divider()
                
                actes = data.get("actes", [])
                if not actes:
                    st.warning("Aucun acte tarifié détecté.")
                
                for acte in actes:
                    desc = acte.get("description", "Acte inconnu")
                    code = acte.get("code")
                    coeff = float(acte.get("coefficient") or 0)
                    prix_facture = float(acte.get("montant_facture") or 0)
                    
                    ref = None
                    prix_legal = 0
                    
                    # Logique de calcul
                    if code: 
                        ref = get_tarif_reference(code, secteur)
                        if ref and ref["type"] == "lettre":
                            prix_legal = ref["valeur"] * coeff
                    
                    if prix_legal == 0: 
                        ref = get_tarif_reference(desc, secteur)
                        if ref: 
                            prix_legal = ref["valeur"]
                    
                    # Affichage
                    c1, c2, c3 = st.columns([3, 2, 2])
                    c1.markdown(f"**{desc}**")
                    if code and coeff > 0: c1.caption(f"Code : {code}{coeff}")
                    c2.write(f"Facturé : **{prix_facture} DH**")
                    
                    if prix_legal > 0:
                        diff = prix_facture - prix_legal
                        if diff > (prix_legal * 0.1): # Marge 10%
                            c3.error(f"❌ Ref: {prix_legal}")
                            st.caption(f"⚠️ **+{diff:.2f} DH**")
                        elif diff < -(prix_legal * 0.1):
                            c3.warning(f"⚠️ Ref: {prix_legal}")
                            st.caption("Sous-facturation")
                        else:
                            c3.success(f"✅ Ref: {prix_legal}")
                            st.caption("Conforme")
                    else:
                        c3.info("❓ Pas de réf")
                    
                    st.divider()
            else:
                st.error("L'IA n'a pas pu lire le document.")
