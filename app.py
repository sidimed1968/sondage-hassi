import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
import base64

# --- CONFIGURATION ---
SHEET_NAME = "Sondage_Hassi_Elbekay"
CREDENTIALS_FILE = "credentials.json"

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    from gtts import gTTS
    import io
    LIBS_OK = True
except ImportError:
    LIBS_OK = False

# --- LISTE DES QUESTIONS PRINCIPALES (Q1-Q14 et Q26-Q27) ---
QUESTIONS_MAIN = [
    # PARTIE A
    {"id": "Q1", "key": "NomFamille", "fr": "1. Nom de la famille ?", "ar": "1. اسم الأسرة؟", "type": "text"},
    {"id": "Q2", "key": "GrandeFamille", "fr": "2. Nom de la grande famille ?", "ar": "2. اسم الأسرة الكبيرة؟", "type": "text"},
    # PARTIE B
    {"id": "Q3", "key": "ChefFamille", "fr": "3. Nom du chef de famille ?", "ar": "3. اسم رب الأسرة؟", "type": "text"},
    {"id": "Q4", "key": "Responsable", "fr": "4. Nom du responsable (si différent) ?", "ar": "4. اسم المسؤول (إذا كان مختلفًا)؟", "type": "text"},
    {"id": "Q5", "key": "EnVie", "fr": "5. Le chef est-il en vie ?", "ar": "5. هل هو على قيد الحياة؟", "type": "radio", "opts_fr": ["Oui", "Non"], "opts_ar": ["نعم", "لا"]},
    
    # SAUT -> Q13 si Non
    {"id": "Q6", "key": "Age", "fr": "6. Âge du chef ?", "ar": "6. العمر؟", "type": "number"},
    {"id": "Q7", "key": "Sexe", "fr": "7. Sexe ?", "ar": "7. الجنس؟", "type": "radio", "opts_fr": ["Homme", "Femme"], "opts_ar": ["رجل", "امرأة"]},
    {"id": "Q8", "key": "EtatCivil", "fr": "8. État civil ?", "ar": "8. الحالة الاجتماعية؟", "type": "radio", "opts_fr": ["Célibataire", "Marié(e)", "Divorcé(e)", "Veuf/Veuve"], "opts_ar": ["أعزب", "متزوج", "مطلق", "أرمل"]},
    {"id": "Q9", "key": "Tel", "fr": "9. Numéro de téléphone ?", "ar": "9. رقم الهاتف؟", "type": "text"},
    {"id": "Q10", "key": "CNI", "fr": "10. Numéro Carte d'Identité ?", "ar": "10. رقم بطاقة التعريف؟", "type": "text"},
    
    # PARTIE C
    {"id": "Q11", "key": "Localite", "fr": "11. Localité ?", "ar": "11. القرية؟", "type": "radio_autre", "opts_fr": ["Hassi El Bekay", "Autre"], "opts_ar": ["احسي البكاي", "أخرى"]},
    {"id": "Q12", "key": "StatutLogement", "fr": "12. Statut du logement ?", "ar": "12. وضعية المسكن؟", "type": "radio_autre", "opts_fr": ["Propriétaire", "Locataire", "Hébergé(e)", "Autre"], "opts_ar": ["ملك", "إيجار", "ضيافة", "أخرى"]},
    
    # PARTIE D
    {"id": "Q13", "key": "AEnfants", "fr": "13. La famille a-t-elle des enfants ?", "ar": "13. هل لدى الأسرة أولاد؟", "type": "radio", "opts_fr": ["Oui", "Non"], "opts_ar": ["نعم", "لا"]},
    # SAUT -> Q26 si Non
    {"id": "Q14", "key": "NbEnfants", "fr": "14. Nombre d'enfants ?", "ar": "14. عدد الأولاد؟", "type": "number"},
    
    # PARTIE F
    {"id": "Q26", "key": "Photo", "fr": "26. Photo du logement", "ar": "26. صورة للمسكن", "type": "camera"},
    {"id": "Q27", "key": "GPS", "fr": "27. Coordonnées GPS", "ar": "27. إحداثيات GPS", "type": "gps"},
]

# --- FONCTIONS ---

def play_audio_auto(text, lang):
    """
    Joue l'audio en utilisant le lecteur natif Streamlit (compatible Cloud).
    Cache le lecteur visuellement pour garder l'aspect 'Assistant'.
    """
    if not LIBS_OK: return
    try:
        # Génération du son
        tts = gTTS(text, lang=lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        
        # Lecteur audio invisible mais en autoplay
        st.audio(fp, format='audio/mp3', autoplay=True)
        
        # CSS pour cacher le lecteur (optionnel, enlever si besoin de debug)
        st.markdown("""
            <style>
                audio { display: none !important; }
            </style>
        """, unsafe_allow_html=True)
        
    except Exception:
        pass

def connect_google_sheet():
    """Connexion compatible PC (fichier local) et Cloud (Secrets)"""
    
    # 1. Priorité : Secrets du Cloud (Streamlit Community Cloud)
    if "gcp_service_account" in st.secrets:
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            sheet = client.open(SHEET_NAME).sheet1
            return sheet, "OK"
        except Exception as e:
            return None, str(e)

    # 2. Sinon : Fichier local (Pour test sur PC)
    elif os.path.exists(CREDENTIALS_FILE):
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
            client = gspread.authorize(creds)
            sheet = client.open(SHEET_NAME).sheet1
            return sheet, "OK"
        except Exception as e:
            return None, str(e)
    
    else:
        return None, "Aucune méthode de connexion trouvée (Ni Secrets, ni Fichier JSON)."

# --- LOGIQUE PRINCIPALE ---
def main():
    st.set_page_config(page_title="Sondage Hassi", layout="centered")

    # Initialisation des variables de session
    if "data" not in st.session_state: st.session_state.data = {}
    if "children" not in st.session_state: st.session_state.children = []
    if "q_index" not in st.session_state: st.session_state.q_index = -1
    if "lang" not in st.session_state: st.session_state.lang = "fr"
    
    if "child_idx" not in st.session_state: st.session_state.child_idx = 0
    if "in_child_loop" not in st.session_state: st.session_state.in_child_loop = False
    if "edit_mode" not in st.session_state: st.session_state.edit_mode = False

    # --- ECRAN D'ACCUEIL ---
    if st.session_state.q_index == -1:
        st.title("📋 Enquête Hassi Elbekay")
        st.info("Cliquez sur DÉMARRER pour lancer l'assistant.")
        l = st.radio("Langue / اللغة", ["Français", "العربية"])
        st.session_state.lang = "fr" if l == "Français" else "ar"
        if st.button("🚀 DÉMARRER / ابدأ", type="primary"):
            st.session_state.q_index = 0
            st.rerun()
        return

    lc = st.session_state.lang

    # --- GESTION DU FLUX ---
    # 1. Fin du questionnaire -> Récapitulatif
    if st.session_state.q_index >= len(QUESTIONS_MAIN):
        show_recap_screen(lc)
        return

    # 2. Boucle Enfants
    if st.session_state.in_child_loop:
        handle_child_loop(lc)
        return

    # 3. Question Principale Standard
    q_data = QUESTIONS_MAIN[st.session_state.q_index]
    show_main_question(q_data, lc)

def show_main_question(q, lc):
    # Barre de progression
    st.progress((st.session_state.q_index + 1) / (len(QUESTIONS_MAIN) + 1))
    
    txt = q[lc]
    st.markdown(f"## {txt}")
    
    # Audio : Jouer seulement si la question change
    if "last_spoken_q" not in st.session_state or st.session_state.last_spoken_q != q["id"]:
        play_audio_auto(txt, lc)
        st.session_state.last_spoken_q = q["id"]

    val_key = q["key"]
    old_val = st.session_state.data.get(val_key)

    # Formulaire
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
            # Gestion de la sauvegarde "Autre: ..."
            if old_val and ("Autre" in str(old_val) or "أخرى" in str(old_val)) and ":" in str(old_val):
                 current_selection = opts[-1]
                 precision_val = str(old_val).split(":", 1)[1].strip()
            elif old_val not in opts:
                current_selection = opts[0]
            
            ix = opts.index(current_selection) if current_selection in opts else 0
            res_radio = st.radio("Choix", opts, index=ix)
            
            lbl_prec = "Si 'Autre', précisez ici / حدد هنا إذا اخترت 'أخرى'"
            res_prec = st.text_input(lbl_prec, value=precision_val)
            
            if "Autre" in res_radio or "أخرى" in res_radio:
                res = f"Autre: {res_prec}" if res_prec else "Autre (Non précisé)"
            else:
                res = res_radio

        elif q["type"] == "camera":
            cam = st.camera_input("Photo")
            if cam: res = "Photo_Recue"
            elif old_val: res = old_val
            else: res = "Non"
        
        elif q["type"] == "gps":
            c1, c2 = st.columns(2)
            lat_val = st.session_state.data.get("Lat", "")
            long_val = st.session_state.data.get("Long", "")
            lat = c1.text_input("Latitude", value=lat_val)
            lng = c2.text_input("Longitude", value=long_val)
            res = "GPS_OK"

        c1, c2 = st.columns(2)
        if c1.form_submit_button("⬅ Retour"):
            if st.session_state.edit_mode:
                st.session_state.q_index = len(QUESTIONS_MAIN)
            elif st.session_state.q_index > 0:
                st.session_state.q_index -= 1
            st.rerun()

        if c2.form_submit_button("Suivant ➡", type="primary"):
            st.session_state.data[val_key] = res
            if q["type"] == "gps":
                st.session_state.data["Lat"] = lat
                st.session_state.data["Long"] = lng
            
            # --- LOGIQUE DE SAUT (JUMPS) ---
            
            # 1. Si Q5 (En vie) == Non -> Aller à Q13
            if q["id"] == "Q5" and res and ("Non" in str(res) or "لا" in str(res)):
                target = next(i for i, x in enumerate(QUESTIONS_MAIN) if x["id"] == "Q13")
                st.session_state.q_index = target
                st.rerun()
                return

            # 2. Si Q13 (Enfants) == Non -> Aller à Q26 (Photo)
            if q["id"] == "Q13" and res and ("Non" in str(res) or "لا" in str(res)):
                target = next(i for i, x in enumerate(QUESTIONS_MAIN) if x["id"] == "Q26")
                st.session_state.q_index = target
                st.rerun()
                return

            # 3. Si Q14 (Nb Enfants) > 0 -> Boucle Enfants
            if q["id"] == "Q14":
                nb = int(res)
                st.session_state.data["NbEnfants"] = nb
                if nb > 0:
                    if len(st.session_state.children) < nb:
                        for _ in range(nb - len(st.session_state.children)):
                            st.session_state.children.append({})
                    st.session_state.in_child_loop = True
                    st.session_state.child_idx = 0
                    st.rerun()
                    return

            # Navigation standard
            if st.session_state.edit_mode:
                st.session_state.edit_mode = False
                st.session_state.q_index = len(QUESTIONS_MAIN)
            else:
                st.session_state.q_index += 1
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

    # --- CHAMPS SANS FORMULAIRE POUR INTERACTIVITÉ ---

    # 15. NOM
    lbl_15 = "15. Nom de l'enfant / اسم الولد"
    nom = st.text_input(lbl_15, value=d.get("Nom", ""), key=f"c_nom_{idx}")
    
    # 16. SEXE
    lbl_16 = "16. Sexe / الجنس"
    opts_sexe = ["Homme", "Femme"] if lc=="fr" else ["رجل", "امرأة"]
    idx_sexe = 0 if d.get("Sexe") != opts_sexe[1] else 1
    sexe = st.radio(lbl_16, opts_sexe, index=idx_sexe, key=f"c_sexe_{idx}")
    
    # 17. MERE
    lbl_17 = "17. Nom de la mère / اسم الأم"
    mere = st.text_input(lbl_17, value=d.get("Mere", ""), key=f"c_mere_{idx}")
    
    # 18. NIVEAU
    lbl_18 = "18. Niveau scolaire / المستوى الدراسي"
    # Valeurs stockées en FR pour simplicité, affichage bilingue géré par l'index
    niv_opts_fr = ["Sans", "Primaire", "Secondaire", "Universitaire", "Mahadra"]
    niv_opts_ar = ["بدون مستوى", "ابتدائي", "ثانوي", "جامعي", "محظرة"]
    niv_opts_display = niv_opts_fr if lc == "fr" else niv_opts_ar
    
    # On stocke la valeur affichée
    saved_niv = d.get("Niveau", niv_opts_display[0])
    try: idx_niv = niv_opts_display.index(saved_niv)
    except: idx_niv = 0
    niv = st.selectbox(lbl_18, niv_opts_display, index=idx_niv, key=f"c_niv_{idx}")
    
    # 19. SITUATION PRO (Avec tiret neutre)
    lbl_19 = "19. Situation professionnelle / الوضعية المهنية"
    pro_opts_fr = ["-", "Fonctionnaire", "Employé(e) privé", "Travaux libéraux", "Sans emploi", "Étudiant", "Autre"]
    pro_opts_ar = ["-", "موظف", "عامل في القطاع الخاص", "أعمال حرة", "عاطل عن العمل", "طالب", "أخرى"]
    pro_opts = pro_opts_fr if lc == "fr" else pro_opts_ar
    
    saved_pro = d.get("Pro", "-")
    try: idx_pro = pro_opts.index(saved_pro)
    except: idx_pro = 0
    pro = st.selectbox(lbl_19, pro_opts, index=idx_pro, key=f"c_pro_{idx}")

    # 20. GRADE (Conditionnel)
    grade = "N/A"
    if pro in ["Fonctionnaire", "موظف"]:
        st.info("ℹ️ Grade requis / الدرجة مطلوبة")
        lbl_20 = "20. Grade / الدرجة الوظيفية"
        gr_opts_fr = ["Ministre", "Directeur Général", "Directeur", "Chef de Service", "Autre"]
        gr_opts_ar = ["وزير", "مدير عام", "مدير", "رئيس مصلحة", "أخرى"]
        gr_opts = gr_opts_fr if lc == "fr" else gr_opts_ar
        
        saved_gr = d.get("Grade", gr_opts[0])
        try: idx_gr = gr_opts.index(saved_gr)
        except: idx_gr = 0
        grade = st.selectbox(lbl_20, gr_opts, index=idx_gr, key=f"c_grade_{idx}")

    # 21. ACTIVITE FEMME (Conditionnel)
    act_femme = "N/A"
    if sexe in ["Femme", "امرأة"]:
        lbl_21 = "21. Activité professionnelle (si femme) / النشاط المهني (إذا كانت امرأة)"
        act_femme = st.text_input(lbl_21, value=d.get("Act_Femme", ""), key=f"c_act_{idx}")

    # 22. SANTE
    lbl_22 = "22. État de santé / الحالة الصحية"
    sante_opts = ["Bon / جيدة", "Malade / مريض"]
    saved_sante = d.get("Sante", sante_opts[0])
    try: idx_sante = sante_opts.index(saved_sante)
    except: idx_sante = 0
    sante = st.radio(lbl_22, sante_opts, index=idx_sante, key=f"c_sante_{idx}")

    # 23. MALADIE (Conditionnel)
    maladie = "N/A"
    if "Malade" in sante or "مريض" in sante:
        st.info("ℹ️ Préciser le type de maladie / تحديد نوع المرض")
        lbl_23 = "23. Type de maladie / نوع المرض"
        mal_opts_fr = ["Maladie chronique", "Maladie aiguë", "Handicap", "Autre"]
        mal_opts_ar = ["مرض مزمن", "مرض حاد", "إعاقة", "آخر"]
        mal_opts = mal_opts_fr if lc == "fr" else mal_opts_ar
        
        saved_mal = d.get("Maladie", mal_opts[0])
        try: idx_mal = mal_opts.index(saved_mal)
        except: idx_mal = 0
        maladie = st.selectbox(lbl_23, mal_opts, index=idx_mal, key=f"c_maladie_{idx}")

    # 24. AIDE
    lbl_24 = "24. A-t-il/elle bénéficié d'une aide ? / هل استفاد(ت) من مساعدة؟"
    aide_opts = ["Oui / نعم", "Non / لا"]
    saved_aide = d.get("Aide", aide_opts[1])
    try: idx_aide = aide_opts.index(saved_aide)
    except: idx_aide = 1
    aide = st.radio(lbl_24, aide_opts, index=idx_aide, key=f"c_aide_{idx}")

    # 25. ORGANISME (Conditionnel)
    orga = "N/A"
    if "Oui" in aide or "نعم" in aide:
        st.info("ℹ️ Quel organisme ? / ما هي الهيئة؟")
        lbl_25 = "25. Si oui, quel organisme ? / إذا كان الجواب 'نعم'، ما هي الهيئة؟"
        orga = st.text_input(lbl_25, value=d.get("Orga", ""), key=f"c_orga_{idx}")

    # Navigation Enfants
    c1, c2 = st.columns(2)
    
    child_save = {
        "Nom": nom, "Sexe": sexe, "Mere": mere, "Niveau": niv,
        "Pro": pro, "Grade": grade, "Act_Femme": act_femme,
        "Sante": sante, "Maladie": maladie, "Aide": aide, "Orga": orga
    }
    
    if c1.button("⬅ Précédent / السابق", key=f"b_p_{idx}"):
        st.session_state.children[idx] = child_save
        if idx > 0:
            st.session_state.child_idx -= 1
            st.rerun()
        else:
            st.session_state.in_child_loop = False
            target = next(i for i, x in enumerate(QUESTIONS_MAIN) if x["id"] == "Q14")
            st.session_state.q_index = target
            st.rerun()

    if c2.button("Suivant ➡ / التالي", key=f"b_n_{idx}", type="primary"):
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
    st.success("✅ Saisie Terminée ! / تمت التعبئة")
    
    data_rows = []
    for q in QUESTIONS_MAIN:
        k = q["key"]
        if k in st.session_state.data:
            data_rows.append({"Q": q["id"], "Libellé": q[lc], "Réponse": st.session_state.data[k]})
    st.table(pd.DataFrame(data_rows))

    if st.session_state.children:
        st.subheader(f"Enfants / الأولاد ({len(st.session_state.children)})")
        if st.button("✏️ Modifier les Enfants / تعديل الأولاد"):
            st.session_state.in_child_loop = True
            st.session_state.child_idx = 0
            st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        opts = [f"{r['Q']} - {r['Libellé']}" for r in data_rows]
        sel = st.selectbox("Modifier Question / تعديل سؤال :", opts)
        if st.button("Aller Modifier / تعديل"):
            qid = sel.split(" - ")[0]
            idx = next(i for i, x in enumerate(QUESTIONS_MAIN) if x["id"] == qid)
            st.session_state.q_index = idx
            st.session_state.edit_mode = True
            st.rerun()

    with c2:
        st.write("")
        if st.button("🚀 ENVOYER / إرسال", type="primary"):
            with st.spinner("Envoi vers Google Sheets... / جاري الإرسال..."):
                sheet, msg = connect_google_sheet()
                if sheet:
                    try:
                        # 1. Données Famille
                        ordered_row = []
                        keys_order = [q["key"] for q in QUESTIONS_MAIN]
                        for k in keys_order:
                            ordered_row.append(st.session_state.data.get(k, ""))
                        
                        ordered_row.append(str(datetime.now()))

                        # 2. Données Enfants (Flattening)
                        for i, child in enumerate(st.session_state.children):
                            c_vals = [
                                child.get("Nom", ""), child.get("Sexe", ""), child.get("Mere", ""),
                                child.get("Niveau", ""), child.get("Pro", ""), child.get("Grade", ""),
                                child.get("Act_Femme", ""), child.get("Sante", ""), child.get("Maladie", ""),
                                child.get("Aide", ""), child.get("Orga", "")
                            ]
                            ordered_row.extend(c_vals)

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
                    except Exception as e:
                        st.error(f"Erreur Envoi: {e}")
                else:
                    st.error(msg)

if __name__ == "__main__":
    main()