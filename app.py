import streamlit as st
import google.generativeai as genai

st.title("🔑 Test Ultime de la Clé Google")

# 1. Lecture de la clé
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    st.success(f"Clé trouvée : ...{api_key[-5:]}") # Montre la fin pour vérifier que c'est la NOUVELLE
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"Problème lecture secrets : {e}")
    st.stop()

# 2. Test simple
if st.button("Tester la connexion maintenant"):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Réponds juste 'OK' si tu me reçois.")
        st.balloons()
        st.success(f"RÉPONSE GOOGLE : {response.text}")
        st.info("Si tu vois ce message, la clé MARCHE. On peut remettre le gros code.")
    except Exception as e:
        st.error(f"❌ ERREUR BRUTE : {e}")
        st.markdown("""
        **Interprétation :**
        * **429** : Quota dépassé (Même avec la nouvelle clé, Google bloque l'IP Streamlit).
        * **400/403** : Clé invalide ou mal copiée.
        """)
