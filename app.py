import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import sqlite3
import time
import importlib.metadata

# --- 1. CONTRÔLE TECHNIQUE ---
st.set_page_config(page_title="ClaimCheck AI - Expert", page_icon="🇲🇦", layout="wide")

try:
    lib_version = importlib.metadata.version("google-generativeai")
except:
    lib_version = "Inconnue"

st.sidebar.caption(f"SDK Google : {lib_version}")

# --- 2. CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("⚠️ Clé API manquante.")
    st.stop()

# --- 3. LISTE DE SECOURS (ON PASSE AU "PRO") ---
# Puisque tes quotas "Flash" sont vides (Erreur 429), on tente les "Pro".
MODELS_TO_TRY = [
    'models/gemini-1.5-pro',             # Le plus intelligent (Quota séparé ?)
    'models/gemini-1.5-pro-latest',      # Sa variante
    'models/gemini-pro',                 # L'ancienne version (souvent dispo)
    'models/gemini-pro-vision',          # L'ancien spécialiste image
    'models/gemini-2.0-flash-lite'       # On garde le lite en dernier recours
]

def ask_gemini_rotator(prompt, image):
    logs = []
    
    for model_name in MODELS_TO_TRY:
        try:
            # On tente le modèle
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([prompt, image])
            
            # Si ça marche
            st.toast(f"✅ Succès avec : {model_name}", icon="🚀")
            return response.text
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                logs.append(f"⏳ {model_name} : Quota plein (429)")
            elif "404" in error_str:
                logs.append(f"⚠️ {model_name} : Non trouvé")
            else:
                logs.append(f"❌ {model_name} : {error_str}")
            continue

    # Si tout échoue
    st.error("❌ Tous les quotas sont épuisés pour le moment.")
    with st.expander("Voir le détail"):
        for log in logs:
            st.code(log)
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
        with st.spinner("Recherche d'un modèle disponible (Mode PRO)..."):
            data = analyser_document_ia(image)
            
            if data:
                secteur = data.get("secteur", "PRIVE")
                nom = data.get("etablissement", "?")
                
                if secteur == "PUBLIC":
                    st.info(f"🏛️ Secteur Public ({nom})")
                else:
                    st.warning(f"🏨 Secteur Privé ({nom})")
                
                st.divider()
                
                for acte in data.get("actes", []):
                    desc = acte.get("description", "Inconnu")
                    prix = float(acte.get("montant_facture") or 0)
                    
                    st.markdown(f"**{desc}**")
                    st.write(f"Facturé : {prix} DH")
                    st.divider()
            else:
                st.error("Lecture impossible ou quotas épuisés.")
