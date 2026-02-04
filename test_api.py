import streamlit as st
import google.generativeai as genai
import os

st.title("👨‍⚕️ Diagnostic de Connexion Google AI")

# 1. VÉRIFICATION DE LA CLÉ API
st.header("1. Vérification de la Clé API")
api_key = None

try:
    # On essaie de lire depuis les secrets Streamlit
    api_key = st.secrets["GOOGLE_API_KEY"]
    st.success("✅ Clé trouvée dans st.secrets")
except:
    st.warning("⚠️ Pas de clé dans st.secrets. Vérification des variables d'environnement...")
    # On essaie de lire depuis l'OS (si tu l'as mise ailleurs)
    api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ ARRÊT : Aucune Clé API trouvée nulle part. L'IA ne peut pas démarrer.")
    st.stop()
else:
    # On affiche juste les 4 derniers caractères pour vérifier que c'est la bonne
    st.info(f"Clé chargée (finissant par ...{api_key[-4:]})")
    genai.configure(api_key=api_key)

# 2. VÉRIFICATION DES MODÈLES DISPONIBLES
st.header("2. Modèles disponibles pour ton compte")
try:
    my_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            my_models.append(m.name)
    
    if len(my_models) > 0:
        st.success(f"✅ Accès confirmé ! Tu as accès à {len(my_models)} modèles.")
        st.code(my_models)
    else:
        st.error("❌ Connexion réussie, mais AUCUN modèle n'est disponible. Ton compte a peut-être un problème.")
        st.stop()
except Exception as e:
    st.error(f"❌ Erreur de connexion critique : {e}")
    st.stop()

# 3. TEST DE GÉNÉRATION (LE VRAI TEST)
st.header("3. Test de Génération (Hello World)")

# On prend le premier modèle de ta liste pour tester
model_to_test = my_models[0] 
st.write(f"Tentative de discussion avec : `{model_to_test}`...")

if st.button("Lancer le test IA"):
    try:
        model = genai.GenerativeModel(model_to_test)
        response = model.generate_content("Réponds juste par : 'Connexion réussie !'")
        st.balloons()
        st.success(f"🤖 L'IA a répondu : {response.text}")
        st.markdown("### verdict : TOUT FONCTIONNE ✅")
        st.info("Si ce test marche, le problème venait du code d'avant (mauvais nom de modèle).")
    except Exception as e:
        st.error(f"❌ L'IA a planté : {e}")
        st.markdown("""
        **Causes possibles :**
        - Erreur 429 : Quota épuisé (encore).
        - Erreur 400 : Clé invalide.
        - Erreur 403 : Accès interdit (Région géographique bloquée ?).
        """)
