import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
from datetime import datetime
import time
from fpdf import FPDF

# --- CONFIGURATION ---
st.set_page_config(page_title="ClaimCheck AI - Ultimate", page_icon="🇲🇦", layout="wide")

# --- LA LISTE D'ÉLITE (ORDRE DE BATAILLE) ---
# Le système essaiera ces modèles dans l'ordre jusqu'à ce que l'un d'eux réussisse.
MODELS_TO_TRY = [
    "gemini-2.0-flash-lite-preview-02-05", # 1. Le Speedster (Nouveau & Rapide)
    "gemini-1.5-flash",                    # 2. Le Standard (Fiable & Gratuit)
    "gemini-1.5-flash-latest",             # 3. Variante du standard
    "gemini-1.5-pro",                      # 4. Le Cerveau (Plus lent mais puissant)
    "gemini-pro-vision"                    # 5. L'Ancien (Dernier recours)
]

# --- FONCTION INTELLIGENTE : LE ROTATOR ---
def analyse_multimodele(image):
    # 1. Vérif Clé
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        st.error("🚨 Clé API manquante. Ajoutez GOOGLE_API_KEY dans les secrets.")
        st.stop()

    prompt = f"""
    Tu es un auditeur médical expert CNSS au Maroc. Analyse ce document.
    Date du jour : {datetime.now().strftime("%d/%m/%Y")}.

    RÈGLES D'OR :
    1. Trouve le Médecin (Nom, INPE) et la Spécialité.
    2. Vérifie la CONFORMITÉ : Date des soins (Délai > 60j ?), Signature, Cachet.
    3. FACTURATION : Liste les actes et compare avec le TNR (G=80/150DH, K=22.50DH).
    
    JSON STRICT (Pas de markdown, pas de texte avant/après) :
    {{
        "medecin": {{"nom": "...", "inpe": "...", "specialite": "..."}},
        "conformite": {{
            "date_soins": "JJ/MM/AAAA",
            "delai_60j_depasse": true,
            "signature_presente": true,
            "cachet_present": true
        }},
        "actes": [
            {{"nom": "...", "prix_facture": 0.0, "prix_ref": 0.0, "statut": "OK" or "Surfacturation"}}
        ],
        "synthese": "..."
    }}
    """

    last_error = ""

    # 2. LA BOUCLE DE SURVIE
    for model_name in MODELS_TO_TRY:
        try:
            # On tente le modèle courant
            model = genai.GenerativeModel(model_name)
            
            # Appel API
            response = model.generate_content([prompt, image])
            
            # Si on arrive là, c'est que ça a marché !
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            
            return data, model_name # On renvoie les données ET le nom du sauveur

        except Exception as e:
            # Si ça plante, on log l'erreur et on passe au suivant
            error_msg = str(e)
            if "429" in error_msg:
                # Quota dépassé pour ce modèle précis
                continue
            elif "404" in error_msg or "not found" in error_msg.lower():
                # Modèle pas dispo sur ce compte
                continue
            else:
                last_error = error_msg
                continue
    
    # Si on sort de la boucle, c'est que TOUT a échoué
    st.error(f"❌ Échec Total. Dernière erreur : {last_error}")
    return None, None

# --- GÉNÉRATEUR PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Rapport Audit - ClaimCheck', 0, 1, 'C')
        self.ln(10)

def generer_pdf(data):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(0, 10, f"Medecin: {data['medecin']['nom']}", 0, 1)
    pdf.cell(0, 10, f"INPE: {data['medecin']['inpe']}", 0, 1)
    pdf.ln(5)
    
    c = data['conformite']
    pdf.cell(0, 10, f"Date: {c['date_soins']} (Rejet >60j : {'OUI' if c['delai_60j_depasse'] else 'NON'})", 0, 1)
    pdf.cell(0, 10, f"Authenticite: {'OK' if c['signature_presente'] and c['cachet_present'] else 'INCOMPLET'}", 0, 1)
    pdf.ln(5)
    
    pdf.cell(0, 10, "Facturation:", 0, 1)
    for acte in data['actes']:
        pdf.cell(0, 10, f"- {acte['nom']} : {acte['prix_facture']} DH ({acte['statut']})", 0, 1)
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- INTERFACE ---
st.title("ClaimCheck AI 🇲🇦")
st.caption("Architecture : Multi-Modèles (Redondance active)")

col1, col2 = st.columns([1, 1])

with col1:
    uploaded_file = st.file_uploader("Document", type=['jpg', 'png', 'jpeg'])
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Pièce justificative", use_column_width=True)

with col2:
    if uploaded_file and st.button("Lancer l'Audit Ultime", type="primary"):
        with st.spinner("🔄 Recherche du meilleur modèle IA disponible..."):
            
            # APPEL DE LA FONCTION MULTI-MODELE
            data, model_used = analyse_multimodele(image)
            
            if data:
                # Indicateur de succès
                st.toast(f"Analyse réussie avec : {model_used}", icon="🚀")
                st.success("Dossier traité.")
                
                # 1. IDENTITÉ
                st.subheader("👨‍⚕️ Identité")
                st.write(f"**Médecin :** {data['medecin']['nom']}")
                inpe = data['medecin']['inpe']
                if any(x in inpe.lower() for x in ["non", "inconnu"]):
                    st.warning(f"INPE : ⚠️ {inpe}")
                else:
                    st.success(f"INPE : ✅ {inpe}")
                
                st.divider()

                # 2. CONFORMITÉ
                st.subheader("📝 Contrôle Admin")
                k1, k2, k3 = st.columns(3)
                
                # Délai
                if data['conformite']['delai_60j_depasse']:
                    k1.error("Délai : ⛔ > 60j")
                else:
                    k1.success("Délai : ✅ OK")
                
                # Signature
                if data['conformite']['signature_presente']:
                    k2.success("Signé : ✅")
                else:
                    k2.error("Signé : ❌")

                # Cachet
                if data['conformite']['cachet_present']:
                    k3.success("Tampon : ✅")
                else:
                    k3.error("Tampon : ❌")
                
                st.divider()

                # 3. FINANCE
                st.subheader("💰 Tarification")
                for acte in data['actes']:
                    col_a, col_b = st.columns([3, 1])
                    if acte['statut'] == "OK":
                        col_a.success(f"{acte['nom']}")
                        col_b.write(f"**{acte['prix_facture']} DH**")
                    else:
                        col_a.error(f"{acte['nom']}")
                        col_b.write(f"**{acte['prix_facture']} DH**")
                        st.caption(f"⚠️ Ref: {acte['prix_ref']} DH")

                st.info(f"🤖 **Synthèse :** {data['synthese']}")

                # PDF
                try:
                    pdf_data = generer_pdf(data)
                    st.download_button("📄 Rapport PDF", pdf_data, "audit.pdf", "application/pdf")
                except:
                    pass
