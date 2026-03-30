import streamlit as st
import random

# ==========================================
# 0. 페이지 설정
# ==========================================
st.set_page_config(page_title="마피아 게임 도우미", page_icon="🕵️", layout="centered")

# ==========================================
# 1. 세션 상태 초기화
# ==========================================
special_roles_pool = ["🪖 군인", "🏛️ 정치인", "📰 기자", "🔍 탐정"]
night_order = ["스파이", "마피아", "의사", "경찰", "기자", "탐정"]

def init_session_state():
    defaults = {
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
        'sys_msgs': []
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()

# ==========================================
# 2. 게임 로직
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

def log_msg(msg):
    st.session_state.sys_msgs.insert(0, msg)

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
        if "마피아" in role:
            mafia_count += 1
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

# --- 버튼 콜백 ---
def cb_set_roles(count):
    st.session_state.roles = setup_roles(count)
    st.session_state.draw_log = []
    st.session_state.player_number = 1
    st.session_state.sys_msgs = [f"👥 {count}인 역할이 설정되었습니다. 역할을 뽑아주세요."]

def cb_draw_role():
    if st.session_state.roles:
        picked = random.choice(st.session_state.roles)
        st.session_state.roles.remove(picked)
        pnum = st.session_state.player_number
        log_entry = f"플레이어 {pnum} → {picked}"
        st.session_state.draw_log.append(log_entry)
        
        st.session_state.players_info[pnum] = {
            "role": picked,
            "alive": True,
            "shield": "군인" in picked
        }
        
        st.session_state.sys_msgs = [f"🎉 {log_entry} (남은 직업: {len(st.session_state.roles)}개)"]
        st.session_state.player_number += 1

def cb_start_game():
    st.session_state.phase = 'game'
    st.session_state.day = 1
    st.session_state.is_night = True
    cb_start_night_phase()

def cb_reset():
    for key in st.session_state.keys():
        del st.session_state[key]
    init_session_state()

def cb_start_night_phase():
    st.session_state.night_targets = {}
    st.session_state.current_night_role = None
    alive_roles = get_alive_roles()
    st.session_state.night_queue = [role for role in night_order if role in alive_roles]
    st.session_state.sys_msgs = [f"🌙 {st.session_state.day}일차 밤이 되었습니다. [다음 직업]을 눌러주세요."]

def cb_next_night_action():
    if not st.session_state.night_queue:
        st.session_state.current_night_role = None
        st.session_state.sys_msgs = ["🌙 모든 밤 행동이 끝났습니다. [낮/밤 전환] 버튼을 누르세요."]
        return

    role = st.session_state.night_queue.pop(0)
    st.session_state.current_night_role = role
    msg = f"🌙 [{role}]은(는) 밤 행동을 취하십시오.\n"
    st.session_state.sys_msgs = [msg]

def cb_process_night_results():
    log_msg(f"☀️ {st.session_state.day}일차 아침이 밝았습니다.")
    targets = st.session_state.night_targets
    pinfo = st.session_state.players_info
    
    if "마피아" in targets:
        target_pid = targets["마피아"]
        target_role = pinfo[target_pid]['role']
        
        if "의사" in targets and targets["의사"] == target_pid:
            log_msg("💉 의사의 활약으로 간밤에 아무도 죽지 않았습니다!")
        elif "군인" in target_role and pinfo[target_pid].get('shield', False):
            pinfo[target_pid]['shield'] = False
            log_msg(f"🪖 군인(플레이어 {target_pid})님이 마피아의 공격을 버텼습니다!")
        else:
            log_msg(f"💀 밤 사이 플레이어 {target_pid}님이 사망했습니다.")
            kill_player(target_pid)
    else:
        log_msg("🕊️ 간밤에 아무도 죽지 않았습니다.")

    win = check_win()
    if win: log_msg(f"🏆 {win}")

def cb_toggle_day_night():
    if st.session_state.is_night:
        st.session_state.is_night = False
        cb_process_night_results()
    else:
        st.session_state.day += 1
        st.session_state.is_night = True
        cb_start_night_phase()

def cb_player_click(pid):
    pinfo = st.session_state.players_info[pid]
    kill_player(pid)
    log_msg(f"⚖️ 투표 결과: 플레이어 {pid}님이 처형되었습니다.")
    win = check_win()
    if win: log_msg(f"🏆 {win}")

# ==========================================
# 3. UI 렌더링
# ==========================================
st.title("🕵️ 마피아 게임 도우미")

if st.session_state.phase == 'setup':
    col1, col2 = st.columns([1, 1])
    with col1:
        p_count = st.selectbox("인원수 설정", [4, 5, 6, 7, 8], index=0)
    with col2:
        st.button("👥 설정 적용", on_click=cb_set_roles, args=(p_count,), use_container_width=True)

    st.button("🎭 역할 뽑기", on_click=cb_draw_role, disabled=len(st.session_state.roles)==0)

    if st.session_state.sys_msgs:
        st.info(st.session_state.sys_msgs[0])

    if len(st.session_state.draw_log) == p_count and len(st.session_state.roles) == 0:
        st.success("🎊 모든 역할이 배정되었습니다!")
        st.button("▶️ 게임 시작", on_click=cb_start_game)

elif st.session_state.phase == 'game':
    st.button("🔄 리셋", on_click=cb_reset)
    st.button("⏭ 낮/밤 전환", on_click=cb_toggle_day_night)

    st.write("### 플레이어 목록")
    for pid, pinfo in st.session_state.players_info.items():
        btn_label = f"P{pid} ({pinfo['role']})"
        if not pinfo['alive']: btn_label += " 💀"
        st.button(btn_label, key=f"pbtn_{pid}", on_click=cb_player_click, args=(pid,))