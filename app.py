import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import sqlite3
import time
import importlib.metadata

# --- 1. CONTRÔLE TECHNIQUE (VERSION) ---
st.set_page_config(page_title="ClaimCheck AI - Ultimate", page_icon="🇲🇦", layout="wide")

try:
    # On récupère la version installée sur le serveur
    lib_version = importlib.metadata.version("google-generativeai")
except:
    lib_version = "Inconnue"

# Si la version est trop vieille, on arrête tout
st.sidebar.markdown(f"**Version SDK Google :** `{lib_version}`")
if lib_version < "0.8.0" and lib_version != "Inconnue":
    st.error(f"🚨 **MISE À JOUR REQUISE** 🚨")
    st.error(f"Votre serveur utilise une vieille version ({lib_version}). Il faut la version 0.8.0 minimum.")
    st.info("👉 Allez dans 'Manage App' (en bas à droite) > 3 petits points > **Reboot App**.")
    st.stop()

# --- 2. CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("⚠️ Clé API manquante.")
    st.stop()

# --- 3. LISTE DES MODÈLES (Sélection chirurgicale) ---
# On utilise ceux qui sont apparus dans TA liste verte précédente.
MODELS_TO_TRY = [
    'models/gemini-flash-latest',        # Le plus sûr (souvent un alias du 1.5)
    'models/gemini-1.5-flash',           # Le standard
    'models/gemini-2.0-flash-lite-preview-02-05', # Le nouveau (si dispo)
    'models/gemini-pro',                 # L'ancien fiable
]

def ask_gemini_rotator(prompt, image):
    last_error = "Aucun essai."
    
    for model_name in MODELS_TO_TRY:
        try:
            # On tente le modèle
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([prompt, image])
            st.toast(f"✅ Succès avec : {model_name}", icon="🚀")
            return response.text
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                # Quota dépassé, on passe au suivant sans pleurer
                continue 
            elif "404" in error_str:
                # Modèle pas trouvé, on passe
                continue
            else:
                last_error = error_str
                
    # Si on arrive ici, c'est l'échec total
    st.error("❌ Échec de tous les modèles.")
    with st.expander("Voir l'erreur technique"):
        st.write(last_error)
    return None

# --- CERVEAU : BDD ---
def get_tarif_reference(nom_ou_code, secteur):
    try:
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
    except:
        return None
    return None

# --- YEUX : ANALYSE ---
def analyser_document_ia(image):
    prompt = """
    Expert facturation médicale Maroc (CNSS). Analyse l'image.
    Sortie JSON STRICT :
    {
        "secteur": "PUBLIC" ou "PRIVE",
        "etablissement": "Nom ou Inconnu",
        "actes": [
            {
                "description": "Nom acte",
                "code": "Code (K, C) ou null",
                "coefficient": 0,
                "montant_facture": 0
            }
        ]
    }
    """
    res = ask_gemini_rotator(prompt, image)
    if res:
        try:
            return json.loads(res.replace("```json", "").replace("```", "").strip())
        except:
            return None
    return None

# --- INTERFACE ---
st.title("ClaimCheck AI 🇲🇦")

col1, col2 = st.columns([1, 2])

with col1:
    uploaded_file = st.file_uploader("Document", type=['jpg', 'png', 'jpeg'])
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, use_column_width=True)

with col2:
    if uploaded_file and st.button("Lancer l'Audit", type="primary"):
        with st.spinner("Analyse en cours..."):
            data = analyser_document_ia(image)
            
            if data:
                secteur = data.get("secteur", "PRIVE")
                nom = data.get("etablissement", "?")
                st.success(f"Secteur détecté : {secteur} ({nom})")
                
                for acte in data.get("actes", []):
                    desc = acte.get("description", "Inconnu")
                    prix = acte.get("montant_facture", 0)
                    st.write(f"**{desc}** : {prix} DH")
                    st.divider()
            else:
                st.error("Lecture impossible. Essayez une autre photo.")
