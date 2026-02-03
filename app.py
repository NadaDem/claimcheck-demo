import streamlit as st
import google.generativeai as genai
from PIL import Image
import json

# --- CONFIGURATION DU CERVEAU ---
# On récupère la clé depuis le coffre-fort Streamlit
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("⚠️ Clé API manquante dans les Secrets Streamlit.")
    st.stop()

# On utilise le modèle rapide et gratuit
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="ClaimCheck AI - Live", page_icon="🇲🇦", layout="centered")

# --- FONCTION D'INTELLIGENCE ---
def analyser_dossier(image_file):
    img = Image.open(image_file)
    
    # C'est ici que je donne les ordres à l'IA (Le Prompt Engineering)
    prompt = """
    Agis comme un expert en assurance maladie marocaine (CNSS/AMO).
    Analyse cette feuille de soins ou ordonnance.
    Extrais les informations suivantes au format JSON strict :
    1. "type_document": "Feuille de Soins" ou "Ordonnance" ou "Autre"
    2. "patient_nom": Nom du patient (si lisible, sinon "Illisible")
    3. "medecin_inpe": Numéro INPE du médecin (séquence de chiffres)
    4. "date_soins": Date des soins (JJ/MM/AAAA)
    5. "montant_total": Montant total facturé (numérique)
    6. "signature_presente": true ou false (y a-t-il un cachet/signature en bas ?)
    7. "code_barres_medicaments": true ou false (y a-t-il des vignettes de médicaments collées ?)
    
    Si une info est manquante, mets null.
    """
    
    response = model.generate_content([prompt, img])
    
    # Nettoyage de la réponse pour avoir du JSON pur
    clean_text = response.text.replace('```json', '').replace('```', '')
    return json.loads(clean_text)

# --- INTERFACE ---
st.title("ClaimCheck AI 🇲🇦")
st.caption("Moteur : Gemini 1.5 Flash | Mode : Audit Réel")

uploaded_file = st.file_uploader("Scannez le document (Photo)", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    # Affichage image
    image = Image.open(uploaded_file)
    st.image(image, caption='Document analysé', use_column_width=True)
    
    if st.button("Lancer l'Audit Intelligent"):
        with st.spinner('Analyse IA en cours (Lecture manuscrite)...'):
            try:
                # APPEL RÉEL À L'IA
                data = analyser_dossier(uploaded_file)
                
                # --- RÉSULTATS ---
                st.divider()
                st.subheader("🔍 Résultats de l'extraction")
                
                # On affiche les données brutes lues par l'IA
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Document :** {data.get('type_document')}")
                    st.write(f"**Patient :** {data.get('patient_nom')}")
                    st.write(f"**Date :** {data.get('date_soins')}")
                with col2:
                    st.write(f"**INPE Médecin :** {data.get('medecin_inpe')}")
                    st.write(f"**Montant :** {data.get('montant_total')} DH")
                    
                # --- LE VERDICT (Logique Métier) ---
                st.divider()
                st.subheader("🛡️ Verdict de Conformité")
                
                erreurs = []
                
                # Règle 1 : La Signature
                if not data.get('signature_presente'):
                    erreurs.append("❌ **CRITIQUE :** Signature/Cachet médecin manquant.")
                else:
                    st.success("✅ Signature détectée")
                    
                # Règle 2 : L'INPE (Le numéro du médecin doit exister)
                if not data.get('medecin_inpe'):
                    erreurs.append("⚠️ **RISQUE :** Numéro INPE introuvable ou illisible.")
                
                # Règle 3 : Le Montant
                if data.get('montant_total') == 0 or data.get('montant_total') is None:
                    erreurs.append("⚠️ **FINANCE :** Aucun montant détecté.")

                # Affichage final
                if erreurs:
                    st.error("DOSSIER À RISQUE DE REJET")
                    for e in erreurs:
                        st.write(e)
                else:
                    st.balloons()
                    st.success("DOSSIER VALIDE (PRET POUR ENVOI)")
                    
            except Exception as e:
                st.error(f"Erreur d'analyse : {e}")
