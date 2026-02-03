import streamlit as st
import time
from PIL import Image
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ClaimCheck AI", page_icon="🩺", layout="centered")

# --- HEADER (En-tête) ---
st.title("ClaimCheck AI 🇲🇦")
st.success("Mode Beta : Activé")
st.write("Validation automatique des feuilles de soins & Ordonnances.")

# --- ZONE D'UPLOAD (La caméra) ---
st.markdown("---")
st.subheader("1. Scannez le document")
uploaded_file = st.file_uploader("Prendre une photo ou importer", type=['png', 'jpg', 'jpeg'])

# --- LE CERVEAU (Simulation) ---
if uploaded_file is not None:
    # Afficher l'image prise
    image = Image.open(uploaded_file)
    st.image(image, caption='Document reçu', use_column_width=True)
    
    st.markdown("---")
    st.subheader("2. Analyse en cours")
    
    # Bouton d'action
    if st.button("Lancer l'audit de conformité"):
        # Barre de progression pour l'effet "Waouh"
        my_bar = st.progress(0)
        
        with st.spinner('Lecture optique (OCR Gemini)...'):
            time.sleep(1) # Faux temps d'attente
            my_bar.progress(30)
            
        with st.spinner('Vérification Tarifaire (Base ANAM)...'):
            time.sleep(1)
            my_bar.progress(60)
            
        with st.spinner('Recherche des signatures manquantes...'):
            time.sleep(1)
            my_bar.progress(100)
        
        # Le Résultat qui s'affiche
        st.success("✅ Dossier reçu et sécurisé !")
        
        st.info("""
        **Statut :** En cours de traitement.
        Le rapport détaillé des erreurs sera envoyé sur votre WhatsApp Pro sous 24h.
        
        **Merci de votre participation au programme Beta.**
        """)
        
        st.balloons()
