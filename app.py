import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import sqlite3
import time
import random

# --- CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("⚠️ Clé API manquante. Vérifiez les secrets Streamlit.")
    st.stop()

# --- SÉCURITÉ MODÈLE ---
# On utilise le modèle le plus stable et rapide
MODEL_NAME = 'gemini-1.5-flash' 

st.set_page_config(page_title="ClaimCheck AI - Expert ANAM", page_icon="🇲🇦", layout="wide")

# --- FONCTION ROBUSTE AVEC "AMORTISSEUR" (RETRY LOGIC) ---
def ask_gemini_secure(prompt, image):
    """Interroge l'IA avec un système de réessai automatique en cas d'erreur 429"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content([prompt, image])
            return response.text
        except Exception as e:
            error_str = str(e)
            # Si c'est une erreur de quota (429), on attend et on réessaie
            if "429" in error_str:
                wait_time = (attempt + 1) * 5  # Attendre 5s, puis 10s, puis 15s...
                st.warning(f"🚦 Trafic élevé sur l'IA. Pause de {wait_time} secondes...")
                time.sleep(wait_time)
                continue
            # Si c'est une autre erreur, on l'affiche
            else:
                st.error(f"Erreur technique IA : {e}")
                return None
    return None

# --- CERVEAU : CONNEXION BDD ---
def get_tarif_reference(nom_ou_code, secteur):
    try:
        conn = sqlite3.connect('claimcheck.db')
        c = conn.cursor()
        colonne_prix = "tarif_prive" if secteur == "PRIVE" else "tarif_public"
        
        # 1. Recherche par Code (K, B, C...)
        c.execute(f"SELECT {colonne_prix}, description FROM lettres_cles WHERE code=?", (nom_ou_code.upper(),))
        res = c.fetchone()
        if res:
            conn.close()
            return {"type": "lettre", "valeur": res[0], "desc": res[1]}
            
        # 2. Recherche par Forfait
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
    1. Détermine si c'est un établissement PUBLIC (Hôpital, CHU, Ministère) ou PRIVE (Clinique, Cabinet, Dr).
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
    
    json_text = ask_gemini_secure(prompt, image)
    
    if json_text:
        try:
            clean_json = json_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except:
            st.error("Erreur de lecture des données reçues.")
            return None
    return None

# --- INTERFACE ---
st.title("ClaimCheck AI 🇲🇦")
st.caption("Mode : Robuste | Référentiel : ANAM & TNR 2007")

col_upload, col_result = st.columns([1, 2])

with col_upload:
    uploaded_file = st.file_uploader("Scanner un document", type=['jpg', 'png', 'jpeg'])
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Document à auditer", use_column_width=True)

with col_result:
    if uploaded_file and st.button("Lancer l'Audit"):
        with st.spinner("⚡ Analyse intelligente en cours (Mode Sécurisé)..."):
            
            data = analyser_document_ia(image)
            
            if data:
                secteur = data.get("secteur", "PRIVE").upper()
                nom_hopital = data.get("etablissement", "Non identifié")
                
                # En-tête dynamique
                if secteur == "PUBLIC":
                    st.info(f"🏛️ **SECTEUR PUBLIC DÉTECTÉ**\n\nÉtablissement : {nom_hopital}\nGrille tarifaire : Hôpitaux (K=13 DH).")
                else:
                    st.warning(f"🏨 **SECTEUR PRIVÉ DÉTECTÉ**\n\nÉtablissement : {nom_hopital}\nGrille tarifaire : Cliniques (K=22.50 DH).")
                
                st.divider()
                
                # Analyse
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
                    
                    if code: 
                        ref = get_tarif_reference(code, secteur)
                        if ref and ref["type"] == "lettre":
                            prix_legal = ref["valeur"] * coeff
                    
                    if prix_legal == 0: 
                        ref = get_tarif_reference(desc, secteur)
                        if ref: 
                            prix_legal = ref["valeur"]
                    
                    c1, c2, c3 = st.columns([3, 2, 2])
                    c1.write(f"**{desc}**")
                    if code and coeff > 0: c1.caption(f"Code : {code}{coeff}")
                    c2.write(f"Facturé : **{prix_facture} DH**")
                    
                    if prix_legal > 0:
                        diff = prix_facture - prix_legal
                        if diff > (prix_legal * 0.1):
                            c3.error(f"❌ Ref: {prix_legal} DH")
                            st.caption(f"⚠️ **Surfacturation de {diff:.2f} DH**")
                        elif diff < -(prix_legal * 0.1):
                            c3.warning(f"⚠️ Ref: {prix_legal} DH")
                            st.caption("Sous-facturation")
                        else:
                            c3.success(f"✅ Ref: {prix_legal} DH")
                            st.caption("Conforme")
                    else:
                        c3.info("❓ Pas de réf")
                    
                    st.divider()
            else:
                st.error("L'IA n'a pas pu lire le document après plusieurs essais.")
