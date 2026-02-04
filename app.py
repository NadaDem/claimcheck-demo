import streamlit as st
import google.generativeai as genai

st.title("📋 Liste de vos Modèles Google AI")

try:
    # Configuration avec ta clé
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    
    st.write("Voici la liste exacte des modèles disponibles pour votre compte. C'est cette liste qui fait foi.")
    
    found = False
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            st.code(m.name) # Affiche le nom exact à copier
            found = True
            
    if not found:
        st.error("Aucun modèle compatible trouvé.")

except Exception as e:
    st.error(f"Erreur : {e}")
