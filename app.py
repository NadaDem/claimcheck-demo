import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import sqlite3

# --- 1. CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("⚠️ Clé API manquante. Vérifiez les secrets Streamlit.")
    st.stop()

# --- 2. LE CHANGEMENT CRUCIAL (Basé sur ta liste) ---
# On utilise le modèle présent dans ton diagnostic : 'models/gemini-2.0-flash'
try:
    model = genai.GenerativeModel('models/gemini-2.0-flash')
except Exception as e:
    st.error(f"Erreur de chargement du modèle : {e}")
    st.stop()

st.set_page_config(page_title="ClaimCheck AI - Expert ANAM", page_icon="🇲🇦", layout="wide")

# --- 3. CERVEAU : CONNEXION BASE DE DONNÉES ---
def get_tarif_reference(nom_ou_code, secteur):
    """Cherche le prix officiel dans notre base de données"""
    try:
        conn = sqlite3.connect('claimcheck.db')
        c = conn.cursor()
    except:
        return None # Pas de base trouvée
    
    # Sélection de la colonne selon le secteur
    colonne_prix = "tarif_prive" if secteur == "PRIVE" else "tarif_public"
    
    # A. Recherche par Code (K, B, C...)
    try:
        c.execute(f"SELECT {colonne_prix}, description FROM lettres_cles WHERE code=?", (nom_ou_code.upper(),))
        res = c.fetchone()
        if res:
            conn.close()
            return {"type": "lettre", "valeur": res[0], "desc": res[1]}
            
        # B. Recherche par Forfait (Césarienne, Scanner...)
        # On cherche un mot clé dans la description
        c.execute(f"SELECT {colonne_prix}, nom_acte FROM forfaits WHERE mots_cles LIKE ?", (f"%{nom_ou_code.lower()}%",))
        res = c.fetchone()
        conn.close()
        
        if res:
            return {"type": "forfait", "valeur": res[0], "desc": res[1]}
    except:
        return None
        
    return None

# --- 4. YEUX : ANALYSE DOC PAR L'IA ---
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
                "description": "Nom de l'acte (ex: Consultation, Césarienne, Scanner)",
                "code": "Code si visible (ex: K, C, B) sinon null",
                "coefficient": "Valeur du coeff (ex: 50, 100) sinon 0",
                "montant_facture": "Montant total en DH"
            }
        ]
    }
    """
    try:
        # On utilise le modèle 2.0 Flash qui est très rapide
        response = model.generate_content([prompt, image])
        # Nettoyage chirurgical de la réponse pour éviter les bugs JSON
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"Erreur d'analyse IA : {e}")
        return None

# --- 5. INTERFACE UTILISATEUR ---
st.title("ClaimCheck AI 🇲🇦")
st.caption("Moteur : Gemini 2.0 Flash | Référentiel : ANAM & TNR 2007")

col_upload, col_result = st.columns([1, 2])

with col_upload:
    uploaded_file = st.file_uploader("Scanner un document", type=['jpg', 'png', 'jpeg'])
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Document à auditer", use_column_width=True)

with col_result:
    if uploaded_file and st.button("Lancer l'Audit"):
        with st.spinner("⚡ Analyse intelligente en cours..."):
            
            data = analyser_document_ia(image)
            
            if data:
                secteur = data.get("secteur", "PRIVE").upper()
                nom_hopital = data.get("etablissement", "Non identifié")
                
                # En-tête dynamique selon le secteur
                if secteur == "PUBLIC":
                    st.info(f"🏛️ **SECTEUR PUBLIC DÉTECTÉ**\n\nÉtablissement : {nom_hopital}\nGrille tarifaire : Hôpitaux (K=13 DH).")
                else:
                    st.warning(f"🏨 **SECTEUR PRIVÉ DÉTECTÉ**\n\nÉtablissement : {nom_hopital}\nGrille tarifaire : Cliniques (K=22.50 DH).")
                
                st.divider()
                
                # Analyse détaillée des actes
                actes = data.get("actes", [])
                if not actes:
                    st.warning("Aucun acte tarifié détecté sur ce document.")
                
                for acte in actes:
                    desc = acte.get("description", "Acte inconnu")
                    code = acte.get("code")
                    coeff = float(acte.get("coefficient") or 0)
                    prix_facture = float(acte.get("montant_facture") or 0)
                    
                    # Interrogation du cerveau (Base de données)
                    ref = None
                    prix_legal = 0
                    mode_calcul = ""
                    
                    # Stratégie de recherche : Code d'abord, sinon Nom
                    if code: 
                        ref = get_tarif_reference(code, secteur)
                        if ref and ref["type"] == "lettre":
                            prix_legal = ref["valeur"] * coeff
                            mode_calcul = f"Calculé : {code} ({ref['valeur']} DH) x {coeff}"
                    
                    if prix_legal == 0: # Si pas trouvé par code, on cherche par nom (Forfait)
                        ref = get_tarif_reference(desc, secteur)
                        if ref: 
                            prix_legal = ref["valeur"]
                            mode_calcul = "Forfait Conventionnel"
                    
                    # Affichage du résultat
                    c1, c2, c3 = st.columns([3, 2, 2])
                    
                    # Colonne 1 : Description
                    c1.write(f"**{desc}**")
                    if code and coeff > 0:
                        c1.caption(f"Code lu : {code}{coeff}")
                    
                    # Colonne 2 : Prix Facturé
                    c2.write(f"Facturé : **{prix_facture} DH**")
                    
                    # Colonne 3 : Verdict
                    if prix_legal > 0:
                        diff = prix_facture - prix_legal
                        # Marge de tolérance de 10%
                        if diff > (prix_legal * 0.1):
                            c3.error(f"❌ Ref: {prix_legal} DH")
                            st.caption(f"⚠️ **Surfacturation de {diff:.2f} DH**")
                        elif diff < -(prix_legal * 0.1):
                            c3.warning(f"⚠️ Ref: {prix_legal} DH")
                            st.caption("Sous-facturation (Perte)")
                        else:
                            c3.success(f"✅ Ref: {prix_legal} DH")
                            st.caption("Conforme")
                    else:
                        c3.info("❓ Pas de réf")
                        st.caption("Non trouvé dans la base")
                    
                    st.divider()
                    
            else:
                st.error("L'IA n'a pas pu lire le document. Essayez une image plus nette.")
