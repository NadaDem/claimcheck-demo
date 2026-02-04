import streamlit as st
import base64
from groq import Groq
from PIL import Image
import json
import io
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURATION ---
st.set_page_config(page_title="ClaimCheck AI - Ultimate", page_icon="🇲🇦", layout="wide")

# --- LISTE DES MODÈLES GROQ (Ordre de survie) ---
# On essaie le plus gros (90b) en premier, puis les variantes stables
GROQ_MODELS = [
    "llama-3.2-90b-vision-preview",  # Le plus puissant (Recommandé)
    "llama-3.2-11b-vision-preview",  # (Celui qui a planté, on le garde en dernier recours)
    "llama-3.2-11b-vision",          # Nom potentiel de la version stable
    "llama-3.2-90b-vision"           # Nom potentiel de la version stable
]

# --- 1. MOTEUR INTELLIGENT (GROQ) ---
def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def analyse_avec_groq_rotator(uploaded_file):
    # 1. Vérification Clé
    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except:
        st.error("🚨 CLÉ MANQUANTE : Ajoutez 'GROQ_API_KEY' dans les Secrets.")
        return None

    client = Groq(api_key=api_key)
    base64_image = encode_image(uploaded_file)
    
    # 2. Le Prompt Expert
    prompt = f"""
    Tu es un expert en audit médical CNSS/AMO au Maroc. Analyse ce document.
    Date d'aujourd'hui : {datetime.now().strftime("%d/%m/%Y")}
    
    TA MISSION :
    1. IDENTITÉ : Trouve le médecin (Nom, INPE, Spécialité) et le Patient.
    2. CONFORMITÉ :
       - La date des soins est-elle vieille de plus de 60 jours ? (OUI/NON)
       - Y a-t-il une signature manuscrite ? (OUI/NON)
       - Y a-t-il un cachet/tampon ? (OUI/NON)
    3. TARIFICATION : Liste les actes, leur prix facturé, et compare avec le référentiel (TNR) :
       - Consultation G : 80 DH (Privé)
       - Consultation Spé : 150 DH (Privé)
       - Acte K : 22.50 DH (Privé)
    
    Renvoie un JSON STRICT :
    {{
        "medecin": {{"nom": "...", "inpe": "...", "specialite": "..."}},
        "conformite": {{
            "date_soins": "JJ/MM/AAAA",
            "delai_60j_depasse": true/false,
            "signature_presente": true/false,
            "cachet_present": true/false
        }},
        "actes": [
            {{"nom": "...", "prix_facture": 0.0, "prix_ref": 0.0, "statut": "OK" or "Surfacturation"}}
        ],
        "synthese": "Ton avis en 1 phrase."
    }}
    """

    last_error = ""

    # 3. La Boucle de Tentative (Rotator)
    for model_name in GROQ_MODELS:
        try:
            # On tente le modèle
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                        ],
                    }
                ],
                temperature=0.0,
                max_tokens=1024,
                top_p=1,
                stream=False,
                response_format={"type": "json_object"},
            )
            
            # Si ça marche, on sort de la boucle et on renvoie le résultat
            st.toast(f"✅ Modèle utilisé : {model_name}", icon="🚀")
            return json.loads(completion.choices[0].message.content)

        except Exception as e:
            error_msg = str(e)
            # Si c'est une erreur de modèle retiré (404/400), on continue au suivant
            if "model_decommissioned" in error_msg or "not found" in error_msg or "404" in error_msg or "400" in error_msg:
                continue 
            else:
                last_error = error_msg
    
    # Si on arrive ici, tout a échoué
    st.error(f"❌ Échec de tous les modèles Groq. Dernière erreur : {last_error}")
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
    
    pdf.cell(0, 10, f"Medecin: {data['medecin']['nom']} (INPE: {data['medecin']['inpe']})", 0, 1)
    pdf.cell(0, 10, f"Date Soins: {data['conformite']['date_soins']}", 0, 1)
    
    status_delai = "REJET (>60j)" if data['conformite']['delai_60j_depasse'] else "VALIDE"
    pdf.cell(0, 10, f"Delai: {status_delai}", 0, 1)
    
    pdf.ln(5)
    pdf.cell(0, 10, "Actes:", 0, 1)
    for acte in data['actes']:
        pdf.cell(0, 10, f"- {acte['nom']} : {acte['prix_facture']} DH ({acte['statut']})", 0, 1)
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 3. INTERFACE ---
st.title("ClaimCheck AI 🇲🇦")
st.caption("Moteur : Groq Llama 3.2 (Multi-Modèles)")

col1, col2 = st.columns([1, 1])

with col1:
    uploaded_file = st.file_uploader("Document", type=['jpg', 'png', 'jpeg'])
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Document source", use_column_width=True)

with col2:
    if uploaded_file and st.button("Lancer l'Audit", type="primary"):
        with st.spinner("🕵️‍♂️ Analyse approfondie en cours..."):
            
            data = analyse_avec_groq_rotator(uploaded_file)
            
            if data:
                st.success("Analyse terminée !")
                
                # BLOC 1 : MEDECIN
                st.subheader("👨‍⚕️ Médecin & INPE")
                c1, c2 = st.columns(2)
                c1.info(f"Nom : **{data['medecin']['nom']}**")
                
                inpe = data['medecin']['inpe']
                if "Non" in inpe or "Inconnu" in inpe:
                    c2.warning("INPE : ⚠️ Non détecté")
                else:
                    c2.success(f"INPE : ✅ {inpe}")

                st.divider()

                # BLOC 2 : CONFORMITÉ
                st.subheader("📝 Contrôle Administratif")
                k1, k2, k3 = st.columns(3)
                
                # Date & Délai
                date_soins = data['conformite']['date_soins']
                if data['conformite']['delai_60j_depasse']:
                    k1.error(f"Délai : ⛔ DÉPASSÉ\n({date_soins})")
                else:
                    k1.success(f"Délai : ✅ VALIDE\n({date_soins})")
                
                # Signature
                if data['conformite']['signature_presente']:
                    k2.success("Signature : ✅")
                else:
                    k2.error("Signature : ❌ MANQUANTE")

                # Cachet
                if data['conformite']['cachet_present']:
                    k3.success("Cachet : ✅")
                else:
                    k3.error("Cachet : ❌ MANQUANT")
                
                st.divider()

                # BLOC 3 : FINANCE
                st.subheader("💰 Tarification")
                for acte in data['actes']:
                    if acte['statut'] == "OK":
                        st.success(f"{acte['nom']} : {acte['prix_facture']} DH")
                    else:
                        st.error(f"{acte['nom']} : {acte['prix_facture']} DH")
                        st.caption(f"⚠️ Tarif Ref : {acte['prix_ref']} DH | Surfacturation détectée")

                # PDF
                try:
                    pdf_data = generer_pdf(data)
                    st.download_button("📄 Télécharger Rapport PDF", pdf_data, "audit.pdf", "application/pdf")
                except:
                    pass
