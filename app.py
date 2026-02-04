import streamlit as st
from groq import Groq

st.title("🔍 Diagnostic Groq")

try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
    
    st.write("Connexion réussie. Voici les modèles disponibles :")
    
    models = client.models.list()
    
    found_vision = False
    for m in models.data:
        # On affiche tout, mais on met en gras ceux qui font de la vision
        if "vision" in m.id:
            st.success(f"👁️ VISION : {m.id}")
            found_vision = True
        else:
            st.write(f"Standard : {m.id}")
            
    if not found_vision:
        st.error("Aucun modèle 'Vision' trouvé ! C'est ça le problème.")

except Exception as e:
    st.error(f"Erreur de connexion : {e}")
