import streamlit as st
import base64
from groq import Groq
from PIL import Image
import json
import io
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURATION ---
st.set_page_config(page_title="ClaimCheck AI - REAL MODE", page_icon="🇲🇦", layout="wide")

# --- 1. MOTEUR D'INTELLIGENCE (GROQ - LLAMA 3.2) ---
def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def analyse_avec_groq(uploaded_file):
    # RÉCUPÉRATION SÉCURISÉE DE LA CLÉ
    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except:
        st.error("🚨 CLÉ MANQUANTE : Ajoutez 'GROQ_API_KEY' dans les Secrets Streamlit.")
        return None

    client = Groq(api_key=api_key)
    base64_image = encode_image(uploaded_file)

    # LE PROMPT (Cerveau de l'opération)
    prompt = """
    Tu es un expert en audit médical pour la CNSS au Maroc. Analyse ce document (Scan/Photo).
    
    TÂCHES :
    1.  Extraire les informations du médecin (Nom, INPE, Spécialité).
    2.  Vérifier la conformité administrative (Date, Signature, Cachet).
    3.  Lister les actes médicaux et leurs prix facturés.
    4.  Comparer avec ces tarifs de référence (TNR) : 
        - Consultation Généraliste (C) : 80 DH (Secteur Privé) / 60 DH (Public)
        - Consultation Spécialiste (CS) : 150 DH (Privé) / 80 DH (Public)
        - Acte K : 22.50 DH (Privé) / 13 DH (Public)
    
    IMPORTANT : Si tu ne trouves pas une info, mets "Non détecté". Ne pas inventer.
    
    FORMAT JSON STRICT :
    {
        "medecin": {"nom": "...", "inpe": "...", "specialite": "..."},
        "conformite": {
            "date_soins": "JJ/MM/AAAA",
            "signature_visible": true/false,
            "cachet_visible": true/false
        },
        "actes": [
            {"nom": "...", "prix_facture": 0.0, "prix_ref": 0.0, "statut": "OK" ou "Surfacturation"}
        ],
        "synthese": "Ton avis professionnel en 1 phrase."
    }
    """

    try:
        # APPEL RÉEL À L'API (Pas de simulation)
        completion = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview", # Modèle Vision très rapide
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                    ],
                }
            ],
            temperature=0.0, # Zéro créativité = Rigueur maximale
            max_tokens=1024,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"},
        )
        return json.loads(completion.choices[0].message.content)

    except Exception as e:
        # EN CAS D'ERREUR, ON AFFICHE TOUT (Pas de cache-misère)
        st.error(f"❌ ERREUR API : {str(e)}")
        return None

# --- 2. GÉNÉRATEUR PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Rapport Audit - ClaimCheck', 0, 1, 'C')
        self.ln(10)

def generer_pdf(data):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Contenu
    pdf.cell(0, 10, f"Médecin: {data['medecin']['nom']}", 0, 1)
    pdf.cell(0, 10, f"Date Soins: {data['conformite']['date_soins']}", 0, 1)
    pdf.ln(5)
    pdf.cell(0, 10, "Détail des Actes:", 0, 1)
    for acte in data['actes']:
        pdf.cell(0, 10, f"- {acte['nom']} : {acte['prix_facture']} DH ({acte['statut']})", 0, 1)
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 3. INTERFACE ---
st.title("ClaimCheck AI 🇲🇦")
st.caption("Mode : RÉEL (Connecté à Groq Llama 3.2)")

col1, col2 = st.columns([1, 1])

with col1:
    uploaded_file = st.file_uploader("Scanner un document", type=['jpg', 'png', 'jpeg'])
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Document source", use_column_width=True)

with col2:
    if uploaded_file and st.button("Lancer l'Audit Réel", type="primary"):
        with st.spinner("⏳ Interrogation du modèle Llama 3.2 Vision..."):
            
            # APPEL DE LA FONCTION SANS FILET
            data = analyse_avec_groq(uploaded_file)
            
            if data:
                # --- AFFICHAGE DES RÉSULTATS RÉELS ---
                st.success("Analyse terminée !")
                
                # 1. Identité
                st.markdown("### 👨‍⚕️ Identité")
                st.write(f"**Médecin :** {data['medecin']['nom']}")
                st.write(f"**INPE :** {data['medecin']['inpe']}")
                
                # 2. Conformité
                st.markdown("### 📝 Conformité")
                c1, c2, c3 = st.columns(3)
                c1.metric("Date", data['conformite']['date_soins'])
                c2.metric("Signature", "OUI" if data['conformite']['signature_visible'] else "NON")
                c3.metric("Cachet", "OUI" if data['conformite']['cachet_visible'] else "NON")
                
                st.divider()
                
                # 3. Tarifs
                st.markdown("### 💰 Analyse Financière")
                for acte in data['actes']:
                    if acte['statut'] == "OK":
                        st.success(f"{acte['nom']} : {acte['prix_facture']} DH (Conforme)")
                    else:
                        st.error(f"{acte['nom']} : {acte['prix_facture']} DH (Ref: {acte['prix_ref']} DH)")
                
                st.info(f"🤖 **Synthèse :** {data['synthese']}")
                
                # 4. PDF
                try:
                    pdf_data = generer_pdf(data)
                    st.download_button("📄 Télécharger le Rapport", pdf_data, "rapport.pdf", "application/pdf")
                except:
                    st.warning("PDF non généré (caractères spéciaux ?)")
