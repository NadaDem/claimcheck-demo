import streamlit as st
import google.generativeai as genai

st.title("📋 Inventaire de la Nouvelle Clé")

try:
    # On charge ta nouvelle clé
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    
    st.write("Interrogation de Google en cours...")
    
    # On demande la liste
    models = genai.list_models()
    
    found = False
    st.write("### Modèles disponibles :")
    
    for m in models:
        # On affiche tout ce qui peut générer du texte/image
        if 'generateContent' in m.supported_generation_methods:
            st.success(f"✅ {m.name}")
            found = True
            
    if not found:
        st.error("Aucun modèle trouvé ! Le compte est peut-être vide.")

except Exception as e:
    st.error(f"Erreur technique : {e}")
