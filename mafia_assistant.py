import streamlit as st
import random

# 모바일 화면에 맞게 레이아웃 넓게 쓰기
st.set_page_config(page_title="마피아 게임 어시스턴트", page_icon="🕵️", layout="centered")

# 호환성을 위한 재실행 함수
def do_rerun():
    if hasattr(st, 'rerun'):
        st.rerun()
    else:
        st.experimental_rerun()

# ==========================================
# 1. 세션 상태 (전역 변수) 초기화
# ==========================================
def init_session_state():
    default_states = {
        'phase': 'setup',
        'roles': [],
        'draw_log': [],
        'player_number': 1,
        'players_info': {},
        'day': 1,
        'is_night': True,
        'spy_connected': False,
        'night_queue': [],
        'current_night_role': None,
        'night_targets': {},
        'reporter_used': False,
        'reporter_target_day': None,
        'sys_msg': "",
        'game_result': None
    }
    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

special_roles_pool = ["🪖 군인", "🏛️ 정치인", "📰 기자", "🔍 탐정"]
night_order = ["스파이", "마피아", "의사", "경찰", "기자", "탐정"]

# ==========================================
# 2. 게임 로직 함수
# ==========================================
def setup_roles(count):
    base = ["🕵️ 마피아", "👮 경찰", "💉 의사", "🙂 시민"]
    if count == 5: base.append("🙂 시민")
    elif count == 6: base += ["🙂 시민", "🕶️ 스파이"]
    elif count == 7:
        base.append("🕵️ 마피아")
        base += random.sample(special_roles_pool, 2)
    elif count == 8:
        base.append("🕵️ 마피아")
        base += random.sample(special_roles_pool, 2)
        base.append("🕶️ 스파이")
    return base

def get_alive_roles():
    alive = []
    for pid, pinfo in st.session_state.players_info.items():
        if pinfo['alive']:
            for role_name in night_order:
                if role_name in pinfo['role']:
                    alive.append(role_name)
    return list(set(alive))

def check_win():
    mafia_count = 0
    citizen_count = 0
    for pid, pinfo in st.session_state.players_info.items():
        if not pinfo['alive']: continue
        role = pinfo['role']
        if "마피아" in role: mafia_count += 1
        elif "스파이" in role:
            if st.session_state.spy_connected: mafia_count += 1
        else:
            if "정치인" in role: citizen_count += 2
            else: citizen_count += 1

    if mafia_count == 0: return "🎉 시민 승리!"
    elif mafia_count >= citizen_count: return "💀 마피아 승리!"
    return None

def kill_player(pid):
    st.session_state.players_info[pid]['alive'] = False
    if "스파이" in st.session_state.players_info[pid]['role'] and not st.session_state.spy_connected:
        return "스파이_사망"
    return "사망"

# ==========================================
# 3. 화면 렌더링 (설정 화면)
# ===
