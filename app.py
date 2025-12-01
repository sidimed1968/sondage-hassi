import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
import base64

# --- CONFIGURATION ---
SHEET_NAME = "Sondage_Hassi_Elbekay"
CREDENTIALS_FILE = "credentials.json"
MAX_ENFANTS_PREVISION = 15 # On prévoit de la place pour 15 enfants max par ligne (ajustable)

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    from gtts import gTTS
    import io
    LIBS_OK = True
except ImportError:
    LIBS_OK = False

# --- QUESTIONS PRINCIPALES ---
QUESTIONS_MAIN = [
    {"id": "Q1", "key": "NomFamille", "fr": "1. Nom de la famille ?", "ar": "1. اسم الأسرة؟", "type": "text"},
    {"id": "Q2", "key": "GrandeFamille", "fr": "2. Nom de la grande famille ?", "ar": "2. اسم الأسرة الكبيرة؟", "type": "text"},
    {"id": "Q3", "key": "ChefFamille", "fr": "3. Nom du chef de famille ?", "ar": "3. اسم رب الأسرة؟", "type": "text"},
    {"id": "Q4", "key": "Responsable", "fr": "4. Nom du responsable (si différent) ?", "ar": "4. اسم المسؤول (إذا كان مختلفًا)؟", "type": "text"},
    {"id": "Q5", "key": "EnVie", "fr": "5. Le chef est-il en vie ?", "ar": "5. هل هو على قيد الحياة؟", "type": "radio", "opts_fr": ["Oui", "Non"], "opts_ar": ["نعم", "لا"]},
    {"id": "Q6", "key": "Age", "fr": "6. Âge du chef ?", "ar": "6. العمر؟", "type": "number"},
    {"id": "Q7", "key": "Sexe", "fr": "7. Sexe ?", "ar": "7. الجنس؟", "type": "radio", "opts_fr": ["Homme", "Femme"], "opts_ar": ["رجل", "امرأة"]},
    {"id": "Q8", "key": "EtatCivil", "fr": "8. État civil ?", "ar": "8. الحالة الاجتماعية؟", "type": "radio", "opts_fr": ["Célibataire", "Marié(e)", "Divorcé(e)", "Veuf/Veuve"], "opts_ar": ["أعزب", "متزوج", "مطلق", "أرمل"]},
    {"id": "Q9", "key": "Tel", "fr": "9. Numéro de téléphone ?", "ar": "9. رقم الهاتف؟", "type": "text"},
    {"id": "Q10", "key": "CNI", "fr": "10. Numéro Carte d'Identité ?", "ar": "10. رقم بطاقة التعريف؟", "type": "text"},
    {"id": "Q11", "key": "Localite", "fr": "11. Localité ?", "ar": "11. القرية؟", "type": "radio_autre", "opts_fr": ["Hassi El Bekay", "Autre"], "opts_ar": ["احسي البكاي", "أخرى"]},
    {"id": "Q12", "key": "StatutLogement", "fr": "12. Statut du logement ?", "ar": "12. وضعية المسكن؟", "type": "radio_autre", "opts_fr": ["Propriétaire", "Locataire", "Hébergé(e)", "Autre"], "opts_ar": ["ملك", "إيجار", "ضيافة", "أخرى"]},
    {"id": "Q13", "key": "AEnfants", "fr": "13. La famille a-t-elle des enfants ?", "ar": "13. هل لدى الأسرة أولاد؟", "type": "radio", "opts_fr": ["Oui", "Non"], "opts_ar": ["نعم", "لا"]},
    {"id": "Q14", "key": "NbEnfants", "fr": "14. Nombre d'enfants ?", "ar": "14. عدد الأولاد؟", "type": "number"},
    {"id": "Q26", "key": "Photo", "fr": "26. Photo du logement", "ar": "26. صورة للمسكن", "type": "camera"},
    {"id": "Q27", "key": "GPS", "fr": "27. Coordonnées GPS", "ar": "27. إحداثيات GPS", "type": "gps"},
]

# --- FONCTIONS ---
def play_audio_auto(text, lang):
    if not LIBS_OK: return
    try:
        tts = gTTS(text, lang=lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp, format='audio/mp3', autoplay=True)
        st.markdown("<style>audio { display: none !important; }</style>", unsafe_allow_html=True)
    except: pass

def connect_google_sheet():
    if "gcp_service_account" in st.secrets:
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            sheet = client.open(SHEET_NAME).sheet1
            return sheet, "OK"
        except Exception as e: return None, str(e)
    elif os.path.exists(CREDENTIALS_FILE):
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
            client = gspread.authorize(creds)
            sheet = client.open(SHEET_NAME).sheet1
            return sheet, "OK"
        except Exception as e: return None, str(e)
    else: return None, "Aucune méthode de connexion."

def generate_headers():
    """Génère la liste des titres de colonnes pour Google Sheets"""
    # 1. Colonnes Famille
    headers = [q["key"] for q in QUESTIONS_MAIN]
    
    # 2. Colonnes GPS détaillées
    if "Lat" not in headers: headers.append("Lat")
    if "Long" not in headers: headers.append("Long")
    
    headers.append("Date_Enquete")

    # 3. Colonnes Enfants (répétées X fois)
    # On génère des colonnes pour 15 enfants potentiels pour que le tableau soit prêt
    child_fields = ["Nom", "Sexe", "Mere", "Niveau", "Pro", "Grade", "Act_Femme", "Sante", "Maladie", "Aide", "Orga"]
    
    for i in range(1, MAX_ENFANTS_PREVISION + 1):
        for field in child_fields:
            headers.append(f"Enfant_{i}_{field}")
            
    return headers

# --- MAIN ---
def main():
    st.set_page_config(page_title="Sondage Hassi", layout="centered")

    if "data" not in st.session_state: st.session_state.data = {}
    if "children" not in st.session_state: st.session_state.children = []
    if "q_index" not in st.session_state: st.session_state.q_index = -1
    if "lang" not in st.session_state: st.session_state.lang = "fr"
    if "child_idx" not in st.session_state: st.session_state.child_idx = 0
    if "in_child_loop" not in st.session_state: st.session_state.in_child_loop = False
    if "edit_mode" not in st.session_state: st.session_state.edit_mode = False

    # Accueil
    if st.session_state.q_index == -1:
        st.title("📋 Enquête Hassi Elbekay")
        st.info("Cliquez sur DÉMARRER.")
        l = st.radio("Langue / اللغة", ["Français", "العربية"])
        st.session_state.lang = "fr" if l == "Français" else "ar"
        if st.button("🚀 DÉMARRER / ابدأ", type="primary"):
            st.session_state.q_index = 0
            st.rerun()
        return

    lc = st.session_state.lang

    if st.session_state.q_index >= len(QUESTIONS_MAIN):
        show_recap_screen(lc)
        return

    if st.session_state.in_child_loop:
        handle_child_loop(lc)
        return

    q_data = QUESTIONS_MAIN[st.session_state.q_index]
    show_main_question(q_data, lc)

def show_main_question(q, lc):
    st.progress((st.session_state.q_index + 1) / (len(QUESTIONS_MAIN) + 1))
    txt = q[lc]
    st.markdown(f"## {txt}")
    
    if "last_spoken_q" not in st.session_state or st.session_state.last_spoken_q != q["id"]:
        play_audio_auto(txt, lc)
        st.session_state.last_spoken_q = q["id"]

    val_key = q["key"]
    old_val = st.session_state.data.get(val_key)

    with st.form(key=f"form_{val_key}"):
        res = None
        if q["type"] == "text":
            res = st.text_input("Réponse / الجواب", value=old_val if old_val else "")
        elif q["type"] == "number":
            res = st.number_input("Nombre", min_value=0, value=int(old_val) if old_val else 0)
        elif q["type"] == "radio":
            opts = q[f"opts_{lc}"]
            ix = opts.index(old_val) if old_val in opts else 0
            res = st.radio("Choix", opts, index=ix)
        elif q["type"] == "radio_autre":
            opts = q[f"opts_{lc}"]
            current_selection = old_val
            precision_val = ""
            if old_val and ("Autre" in str(old_val) or "أخرى" in str(old_val)) and ":" in str(old_val):
                 current_selection = opts[-1]
                 precision_val = str(old_val).split(":", 1)[1].strip()
            elif old_val not in opts: current_selection = opts[0]
            ix = opts.index(current_selection) if current_selection in opts else 0
            res_radio = st.radio("Choix", opts, index=ix)
            lbl_prec = "Si 'Autre', précisez ici / حدد هنا إذا اخترت 'أخرى'"
            res_prec = st.text_input(lbl_prec, value=precision_val)
            if "Autre" in res_radio or "أخرى" in res_radio: res = f"Autre: {res_prec}" if res_prec else "Autre (Non précisé)"
            else: res = res_radio
        elif q["type"] == "camera":
            cam = st.camera_input("Photo")
            if cam: res = "Photo_Recue"
            elif old_val: res = old_val
            else: res = "Non"
        elif q["type"] == "gps":
            c1, c2 = st.columns(2)
            lat = c1.text_input("Latitude", value=st.session_state.data.get("Lat", ""))
            lng = c2.text_input("Longitude", value=st.session_state.data.get("Long", ""))
            res = "GPS_OK"

        c1, c2 = st.columns(2)
        if c1.form_submit_button("⬅ Retour"):
            if st.session_state.edit_mode: st.session_state.q_index = len(QUESTIONS_MAIN)
            elif st.session_state.q_index > 0: st.session_state.q_index -= 1
            st.rerun()

        if c2.form_submit_button("Suivant ➡", type="primary"):
            st.session_state.data[val_key] = res
            if q["type"] == "gps":
                st.session_state.data["Lat"] = lat
                st.session_state.data["Long"] = lng
            
            # SAUTS
            if q["id"] == "Q5" and res and ("Non" in str(res) or "لا" in str(res)):
                target = next(i for i, x in enumerate(QUESTIONS_MAIN) if x["id"] == "Q13")
                st.session_state.q_index = target
                st.rerun()
                return
            if q["id"] == "Q13" and res and ("Non" in str(res) or "لا" in str(res)):
                target = next(i for i, x in enumerate(QUESTIONS_MAIN) if x["id"] == "Q26")
                st.session_state.q_index = target
                st.rerun()
                return
            if q["id"] == "Q14":
                nb = int(res)
                st.session_state.data["NbEnfants"] = nb
                if nb > 0:
                    if len(st.session_state.children) < nb:
                        for _ in range(nb - len(st.session_state.children)): st.session_state.children.append({})
                    st.session_state.in_child_loop = True
                    st.session_state.child_idx = 0
                    st.rerun()
                    return

            if st.session_state.edit_mode:
                st.session_state.edit_mode = False
                st.session_state.q_index = len(QUESTIONS_MAIN)
            else: st.session_state.q_index += 1
            st.rerun()

def handle_child_loop(lc):
    idx = st.session_state.child_idx
    total = st.session_state.data["NbEnfants"]
    st.markdown(f"### 👶 Enfant {idx + 1} / {total}")
    intro = f"Informations pour l'enfant {idx + 1}" if lc == "fr" else f"معلومات الطفل {idx + 1}"
    if "last_spoken_child" not in st.session_state or st.session_state.last_spoken_child != idx:
        play_audio_auto(intro, lc)
        st.session_state.last_spoken_child = idx

    d = st.session_state.children[idx]
    
    # CHAMPS ENFANTS
    nom = st.text_input("15. Nom / الاسم", value=d.get("Nom", ""), key=f"c_nom_{idx}")
    
    opts_sexe = ["Homme", "Femme"] if lc=="fr" else ["رجل", "امرأة"]
    idx_sexe = 0 if d.get("Sexe") != opts_sexe[1] else 1
    sexe = st.radio("16. Sexe / الجنس", opts_sexe, index=idx_sexe, key=f"c_sexe_{idx}")
    
    mere = st.text_input("17. Nom Mère / اسم الأم", value=d.get("Mere", ""), key=f"c_mere_{idx}")
    
    niv_opts_fr = ["Sans", "Primaire", "Secondaire", "Universitaire", "Mahadra"]
    niv_opts_ar = ["بدون مستوى", "ابتدائي", "ثانوي", "جامعي", "محظرة"]
    niv_opts = niv_opts_fr if lc == "fr" else niv_opts_ar
    saved_niv = d.get("Niveau", niv_opts[0])
    try: idx_niv = niv_opts.index(saved_niv)
    except: idx_niv = 0
    niv = st.selectbox("18. Niveau / المستوى", niv_opts, index=idx_niv, key=f"c_niv_{idx}")
    
    pro_opts_fr = ["-", "Fonctionnaire", "Employé(e) privé", "Travaux libéraux", "Sans emploi", "Étudiant", "Autre"]
    pro_opts_ar = ["-", "موظف", "عامل في القطاع الخاص", "أعمال حرة", "عاطل عن العمل", "طالب", "أخرى"]
    pro_opts = pro_opts_fr if lc == "fr" else pro_opts_ar
    saved_pro = d.get("Pro", "-")
    try: idx_pro = pro_opts.index(saved_pro)
    except: idx_pro = 0
    pro = st.selectbox("19. Situation / الوضعية", pro_opts, index=idx_pro, key=f"c_pro_{idx}")

    grade = "N/A"
    if pro in ["Fonctionnaire", "موظف"]:
        st.info("ℹ️ Grade requis")
        gr_opts_fr = ["Ministre", "DG", "Directeur", "Chef Sce", "Autre"]
        gr_opts_ar = ["وزير", "مدير عام", "مدير", "رئيس مصلحة", "أخرى"]
        gr_opts = gr_opts_fr if lc == "fr" else gr_opts_ar
        saved_gr = d.get("Grade", gr_opts[0])
        try: idx_gr = gr_opts.index(saved_gr)
        except: idx_gr = 0
        grade = st.selectbox("20. Grade / الدرجة", gr_opts, index=idx_gr, key=f"c_grade_{idx}")

    act_femme = "N/A"
    if sexe in ["Femme", "امرأة"]:
        act_femme = st.text_input("21. Activité (Femme)", value=d.get("Act_Femme", ""), key=f"c_act_{idx}")

    sante_opts = ["Bon / جيدة", "Malade / مريض"]
    saved_sante = d.get("Sante", sante_opts[0])
    try: idx_sante = sante_opts.index(saved_sante)
    except: idx_sante = 0
    sante = st.radio("22. Santé / الصحة", sante_opts, index=idx_sante, key=f"c_sante_{idx}")

    maladie = "N/A"
    if "Malade" in sante or "مريض" in sante:
        mal_opts_fr = ["Chronique", "Aiguë", "Handicap", "Autre"]
        mal_opts_ar = ["مزمن", "حاد", "إعاقة", "آخر"]
        mal_opts = mal_opts_fr if lc == "fr" else mal_opts_ar
        saved_mal = d.get("Maladie", mal_opts[0])
        try: idx_mal = mal_opts.index(saved_mal)
        except: idx_mal = 0
        maladie = st.selectbox("23. Maladie / المرض", mal_opts, index=idx_mal, key=f"c_maladie_{idx}")

    aide_opts = ["Oui / نعم", "Non / لا"]
    saved_aide = d.get("Aide", aide_opts[1])
    try: idx_aide = aide_opts.index(saved_aide)
    except: idx_aide = 1
    aide = st.radio("24. Aide ? / مساعدة؟", aide_opts, index=idx_aide, key=f"c_aide_{idx}")

    orga = "N/A"
    if "Oui" in aide or "نعم" in aide:
        orga = st.text_input("25. Organisme / الهيئة", value=d.get("Orga", ""), key=f"c_orga_{idx}")

    c1, c2 = st.columns(2)
    child_save = {"Nom": nom, "Sexe": sexe, "Mere": mere, "Niveau": niv, "Pro": pro, "Grade": grade, "Act_Femme": act_femme, "Sante": sante, "Maladie": maladie, "Aide": aide, "Orga": orga}
    
    if c1.button("⬅ Précédent", key=f"b_p_{idx}"):
        st.session_state.children[idx] = child_save
        if idx > 0:
            st.session_state.child_idx -= 1
            st.rerun()
        else:
            st.session_state.in_child_loop = False
            target = next(i for i, x in enumerate(QUESTIONS_MAIN) if x["id"] == "Q14")
            st.session_state.q_index = target
            st.rerun()

    if c2.button("Suivant ➡", key=f"b_n_{idx}", type="primary"):
        st.session_state.children[idx] = child_save
        if idx < total - 1:
            st.session_state.child_idx += 1
            st.rerun()
        else:
            st.session_state.in_child_loop = False
            target = next(i for i, x in enumerate(QUESTIONS_MAIN) if x["id"] == "Q26")
            st.session_state.q_index = target
            st.rerun()

def show_recap_screen(lc):
    st.success("✅ Saisie Terminée !")
    data_rows = []
    for q in QUESTIONS_MAIN:
        k = q["key"]
        if k in st.session_state.data: data_rows.append({"Q": q["id"], "Libellé": q[lc], "Réponse": st.session_state.data[k]})
    st.table(pd.DataFrame(data_rows))

    if st.session_state.children:
        st.subheader(f"Enfants ({len(st.session_state.children)})")
        if st.button("✏️ Modifier les Enfants"):
            st.session_state.in_child_loop = True
            st.session_state.child_idx = 0
            st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        opts = [f"{r['Q']} - {r['Libellé']}" for r in data_rows]
        sel = st.selectbox("Modifier Question :", opts)
        if st.button("Aller Modifier"):
            qid = sel.split(" - ")[0]
            idx = next(i for i, x in enumerate(QUESTIONS_MAIN) if x["id"] == qid)
            st.session_state.q_index = idx
            st.session_state.edit_mode = True
            st.rerun()

    with c2:
        st.write("")
        if st.button("🚀 ENVOYER / إرسال", type="primary"):
            with st.spinner("Envoi..."):
                sheet, msg = connect_google_sheet()
                if sheet:
                    try:
                        # GESTION AUTOMATIQUE DES EN-TÊTES SI FICHIER VIDE
                        try:
                            # On essaie de lire la ligne 1. Si vide ou erreur -> on crée les titres
                            first_row = sheet.row_values(1)
                        except:
                            first_row = []
                        
                        if not first_row:
                            headers = generate_headers()
                            sheet.append_row(headers)

                        # CONSTRUCTION DE LA LIGNE DE DONNÉES
                        ordered_row = []
                        # 1. Famille (Q1-Q27)
                        keys_order = [q["key"] for q in QUESTIONS_MAIN]
                        for k in keys_order: ordered_row.append(st.session_state.data.get(k, ""))
                        
                        # 2. GPS et Date
                        ordered_row.append(st.session_state.data.get("Lat", ""))
                        ordered_row.append(st.session_state.data.get("Long", ""))
                        ordered_row.append(str(datetime.now()))

                        # 3. Enfants (Flatten)
                        child_fields = ["Nom", "Sexe", "Mere", "Niveau", "Pro", "Grade", "Act_Femme", "Sante", "Maladie", "Aide", "Orga"]
                        for child in st.session_state.children:
                            for field in child_fields:
                                ordered_row.append(child.get(field, ""))
                        
                        sheet.append_row(ordered_row)
                        
                        st.balloons()
                        msg_succes = "🎉 Félicitations ! Le questionnaire a été rempli sans erreur et envoyé avec succès. / مبروك! تم ملء الاستبيان بنجاح وإرساله."
                        st.success(msg_succes)
                        play_audio_auto(msg_succes, lc)
                        time.sleep(5)
                        st.session_state.data = {}
                        st.session_state.children = []
                        st.session_state.q_index = 0
                        st.rerun()
                    except Exception as e: st.error(f"Erreur Envoi: {e}")
                else: st.error(msg)

if __name__ == "__main__":
    main()