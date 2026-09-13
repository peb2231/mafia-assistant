import streamlit as st
import random
import copy

# 페이지 설정
st.set_page_config(page_title="마피아 어시스턴트", page_icon="🕵️", layout="centered")

# ==========================================
# 1. 세션 상태 초기화
# ==========================================
def init_session_state():
    default_states = {
        'phase': 'setup',              
        'player_count': 4,
        'roles_pool': [],              
        'pool_created': False,         
        'players_info': {},            
        'setup_turn_idx': 0,
        'role_revealed': False,
        'draw_log': [],
        
        # 게임 진행 상태
        'history': [],                 
        'day': 1,
        'is_night': True,
        'night_queue': [],             
        'current_role_idx': -1,        
        'night_targets': {},           
        'spy_connected': False,
        'reporter_used': False,
        'reporter_target_day': None,
        'sys_msg': "",
        'vote_mode': False,
        'day_vote_target': None        # 낮 투표에서 지목된 사람 추적용
    }
    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

special_roles_pool = ["🪖 군인", "🏛️ 정치인", "📰 기자", "🔍 탐정"]
night_order = ["스파이", "마피아", "의사", "경찰", "기자", "탐정"]
role_desc = {
    "🕵️ 마피아": "밤마다 1명 암살", "👮 경찰": "밤마다 마피아 여부 확인", "💉 의사": "밤마다 1명 치료",
    "🙂 시민": "투표로 마피아 처형", "🕶️ 스파이": "마피아 찾으면 접선", "📰 기자": "2일차 밤 1명 취재(전체공개)",
    "🔍 탐정": "대상의 밤 지목 확인", "🏛️ 정치인": "투표 시 2표 행사", "🪖 군인": "마피아 공격 1회 방어"
}

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
    random.shuffle(base)
    return base

def get_alive_roles():
    alive = []
    for pid, pinfo in st.session_state.players_info.items():
        if pinfo['alive']:
            for role_name in night_order:
                if role_name in pinfo['role']: alive.append(role_name)
    return list(set(alive))

def check_win():
    mafia_count = sum(1 for p in st.session_state.players_info.values() if p['alive'] and "마피아" in p['role'])
    if st.session_state.spy_connected:
        mafia_count += sum(1 for p in st.session_state.players_info.values() if p['alive'] and "스파이" in p['role'])
    citizen_count = sum(1 for p in st.session_state.players_info.values() if p['alive'] and "마피아" not in p['role'] and "스파이" not in p['role'])
    
    if mafia_count == 0: return "🎉 시민 승리!"
    elif mafia_count >= citizen_count: return "💀 마피아 승리!"
    return None

def save_timeline():
    state_copy = {
        'day': st.session_state.day, 'is_night': st.session_state.is_night,
        'players_info': copy.deepcopy(st.session_state.players_info),
        'night_queue': copy.deepcopy(st.session_state.night_queue),
        'current_role_idx': st.session_state.current_role_idx,
        'night_targets': copy.deepcopy(st.session_state.night_targets),
        'spy_connected': st.session_state.spy_connected,
        'reporter_used': st.session_state.reporter_used,
        'reporter_target_day': st.session_state.reporter_target_day,
        'sys_msg': st.session_state.sys_msg,
        'day_vote_target': st.session_state.day_vote_target
    }
    st.session_state.history.append(state_copy)

def restore_timeline():
    if st.session_state.history:
        prev = st.session_state.history.pop()
        for k, v in prev.items(): st.session_state[k] = v

# ==========================================
# 3. 설정 화면 렌더링
# ==========================================
def render_setup():
    st.markdown("""<style>.block-container { padding-top: 1.5rem; max-width: 500px; }</style>""", unsafe_allow_html=True)
    st.title("🕵️ 마피아 어시스턴트")
    
    st.session_state.player_count = st.selectbox("인원수", [4, 5, 6, 7, 8], index=0)
    setup_method = st.radio("뽑기 방식", ["사회자 방식으로 뽑기", "참가자 방식으로 뽑기"], horizontal=True)
    st.divider()

    if setup_method == "사회자 방식으로 뽑기":
        name_method = st.radio("이름 설정", ["숫자로 만들기 (P1, P2...)", "직접 입력하기"], horizontal=True)
        player_names = []
        if "직접" in name_method:
            cols = st.columns(2)
            for i in range(st.session_state.player_count):
                with cols[i % 2]:
                    n = st.text_input(f"P{i+1} 이름", key=f"n_{i}")
                    player_names.append(n if n else f"P{i+1}")
        else:
            player_names = [f"P{i+1}" for i in range(st.session_state.player_count)]

        if st.button("👥 역할 배정 완료", use_container_width=True, type="primary"):
            roles = setup_roles(st.session_state.player_count)
            st.session_state.players_info = {}
            for i in range(st.session_state.player_count):
                st.session_state.players_info[i+1] = {"name": player_names[i], "role": roles[i], "alive": True, "shield": "군인" in roles[i]}
            start_game_init()

    else:
        if not st.session_state.pool_created:
            if st.button("🎲 역할 풀 생성", use_container_width=True):
                st.session_state.roles_pool = setup_roles(st.session_state.player_count)
                st.session_state.setup_turn_idx = 0
                st.session_state.players_info = {}
                st.session_state.pool_created = True
                st.rerun()

        if st.session_state.pool_created:
            turn = st.session_state.setup_turn_idx
            if turn < st.session_state.player_count:
                st.write(f"**🙋‍♂️ {turn+1}번째 플레이어**")
                p_name = st.text_input("이름 입력:", disabled=st.session_state.role_revealed)
                
                if not st.session_state.role_revealed:
                    if st.button("확인하기", use_container_width=True):
                        p_name = p_name if p_name else f"P{turn+1}"
                        role = st.session_state.roles_pool.pop()
                        st.session_state.players_info[turn+1] = {"name": p_name, "role": role, "alive": True, "shield": "군인" in role}
                        st.session_state.role_revealed = True
                        st.rerun()
                else:
                    role_assigned = st.session_state.players_info[turn+1]['role']
                    st.success(f"직업: **[{role_assigned}]**\n\n({role_desc[role_assigned]})")
                    if turn == st.session_state.player_count - 1:
                        if st.button("설정 마치기 (사회자 전달)", use_container_width=True, type="primary"): start_game_init()
                    else:
                        if st.button("다음사람 ➡️", use_container_width=True):
                            st.session_state.role_revealed = False
                            st.session_state.setup_turn_idx += 1
                            st.rerun()

def start_game_init():
    st.session_state.phase = 'game'
    st.session_state.history = []
    st.session_state.day = 1
    st.session_state.is_night = True
    st.session_state.night_queue = [r for r in night_order if r in get_alive_roles()]
    st.session_state.current_role_idx = -1
    st.session_state.sys_msg = "🌙 1일차 밤이 되었습니다. [▶ 다음]을 누르세요."
    st.session_state.day_vote_target = None
    st.rerun()

# ==========================================
# 4. 게임 화면 렌더링
# ==========================================
def render_game():
    # -----------------------------------------------------
    # 여백 축소 & 기본 테마 어댑티브(Adaptive) CSS
    # -----------------------------------------------------
    phase_text = f"🌙 {st.session_state.day}일차 밤" if st.session_state.is_night else f"☀️ {st.session_state.day}일차 낮"
    
    st.markdown(f"""
        <style>
        .block-container {{ padding-top: 1rem; padding-bottom: 1rem; max-width: 500px; }}
        h3 {{ font-size: 1.1rem !important; margin-bottom: 0.3rem !important; padding-top: 0.5rem !important; }}
        hr {{ margin: 0.8rem 0; }}
        p {{ margin-bottom: 0.4rem; font-size: 0.9rem; }}
        .fixed-header {{
            position: fixed; top: 2.875rem; left: 0; width: 100%;
            background-color: var(--secondary-background-color); 
            color: var(--text-color);
            z-index: 9999; text-align: center; padding: 10px 0;
            font-size: 1.1rem; font-weight: bold; border-bottom: 1px solid var(--border-color);
        }}
        .sys-box {{
            background-color: var(--secondary-background-color); border-radius: 6px; 
            padding: 10px; min-height: 45px; font-size: 0.9rem;
        }}
        .stButton>button {{
            min-height: 2.5rem; padding: 2px 5px; font-size: 0.85rem;
        }}
        .spacer {{ height: 45px; }}
        </style>
        <div class="fixed-header">{phase_text}</div>
        <div class="spacer"></div>
    """, unsafe_allow_html=True)

    # 1. 초기화 버튼
    c_left, c_right = st.columns([3, 1])
    with c_right:
        if st.button("🔄 리셋", use_container_width=True):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    # 2. 시스템 메시지
    win_status = check_win()
    if win_status: st.markdown(f"<div class='sys-box' style='color:#e74c3c; font-weight:bold;'>🏆 {win_status}</div>", unsafe_allow_html=True)
    else: st.markdown(f"<div class='sys-box'>{st.session_state.sys_msg}</div>", unsafe_allow_html=True)

    st.write("---")

    # 3. 행동 조작
    if st.session_state.is_night:
        st.write("### 🌙 행동 조작")
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.button("◀ 이전", use_container_width=True, disabled=st.session_state.current_role_idx <= -1):
                st.session_state.current_role_idx -= 1
                update_night_sys_msg(); st.rerun()
        with c2:
            if st.session_state.current_role_idx == -1: st.markdown("<div style='text-align:center;'>대기 중</div>", unsafe_allow_html=True)
            elif st.session_state.current_role_idx >= len(st.session_state.night_queue): st.markdown("<div style='text-align:center;'>행동 완료</div>", unsafe_allow_html=True)
            else: st.markdown(f"<div style='text-align:center; font-weight:bold;'>[{st.session_state.night_queue[st.session_state.current_role_idx]}]</div>", unsafe_allow_html=True)
        with c3:
            if st.button("다음 ▶", use_container_width=True, disabled=st.session_state.current_role_idx >= len(st.session_state.night_queue)):
                st.session_state.current_role_idx += 1
                update_night_sys_msg(); st.rerun()
    else:
        st.write("### ☀️ 낮 투표 모드")
        st.session_state.vote_mode = st.toggle("🗳️ 안전잠금 해제 (버튼 활성화)", value=st.session_state.vote_mode)

    st.write("---")

    # 4. 플레이어 목록 (단일 투표 변경 로직 적용)
    st.write("### 👥 플레이어")
    cols = st.columns(2)
    sorted_players = sorted(st.session_state.players_info.items(), key=lambda x: x[0])
    
    current_role = None
    if st.session_state.is_night and 0 <= st.session_state.current_role_idx < len(st.session_state.night_queue):
        current_role = st.session_state.night_queue[st.session_state.current_role_idx]

    for i, (pid, pinfo) in enumerate(sorted_players):
        status = "💀" if not pinfo['alive'] else "🙂"
        btn_text = f"{pinfo['name']} ({pinfo['role']}) {status}"
        
        # 낮 투표에서 지목된 사람 시각화
        if not st.session_state.is_night and st.session_state.day_vote_target == pid:
            btn_text = f"💀 [처형됨]\n{pinfo['name']} ({pinfo['role']})"

        # 밤 행동에서 지목된 사람 시각화
        if st.session_state.is_night and current_role and st.session_state.night_targets.get(current_role) == pid:
            btn_text = f"🎯 [지목됨]\n{btn_text}"

        with cols[i % 2]:
            is_disabled = True
            
            # 낮 투표 모드 로직
            if not st.session_state.is_night and st.session_state.vote_mode:
                # 살아있는 사람 또는 방금 투표로 죽은 사람만 누를 수 있음 (밤에 죽은 사람은 비활성)
                if pinfo['alive'] or st.session_state.day_vote_target == pid:
                    is_disabled = False
                    
                if st.button(btn_text, key=f"v_{pid}", use_container_width=True, disabled=is_disabled):
                    if st.session_state.day_vote_target == pid:
                        # 이미 죽인 사람을 다시 누르면 -> 취소(부활)
                        st.session_state.players_info[pid]['alive'] = True
                        st.session_state.day_vote_target = None
                        st.session_state.sys_msg = f"⚖️ {pinfo['name']} 처형을 취소했습니다."
                    else:
                        # 다른 사람을 누르면 -> 기존 사람 살리고 새 사람 죽임
                        if st.session_state.day_vote_target is not None:
                            st.session_state.players_info[st.session_state.day_vote_target]['alive'] = True
                        st.session_state.players_info[pid]['alive'] = False
                        st.session_state.day_vote_target = pid
                        st.session_state.sys_msg = f"⚖️ {pinfo['name']}님을 처형했습니다."
                    st.rerun()

            # 밤 행동 모드 로직
            else:
                if st.session_state.is_night and current_role and pinfo['alive']: 
                    is_disabled = False
                if st.button(btn_text, key=f"p_{pid}", use_container_width=True, disabled=is_disabled):
                    handle_night_action(pid, pinfo)

    st.write("---")

    # 5. 시간선 이동
    st.write("### ⏳ 시간선 이동")
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        if st.button("⏪ 이전 시간", use_container_width=True, disabled=len(st.session_state.history)==0):
            restore_timeline(); st.rerun()
    with t_col2:
        btn_label = "다음 (낮) ⏩" if st.session_state.is_night else "다음 (밤) ⏩"
        if st.button(btn_label, use_container_width=True): 
            save_timeline()
            if st.session_state.is_night:
                st.session_state.is_night = False
                st.session_state.vote_mode = False
                st.session_state.day_vote_target = None # 낮으로 넘어올 때 투표 타겟 초기화
                
                msg_list = [f"☀️ {st.session_state.day}일 아침"]
                if "마피아" in st.session_state.night_targets:
                    t_pid = st.session_state.night_targets["마피아"]
                    t_info = st.session_state.players_info[t_pid]
                    if st.session_state.night_targets.get("의사") == t_pid: msg_list.append("💉 의사 활약. 사망자 없음.")
                    elif "군인" in t_info['role'] and t_info['shield']:
                        st.session_state.players_info[t_pid]['shield'] = False; msg_list.append(f"🪖 군인({t_info['name']}) 방어 성공.")
                    else:
                        st.session_state.players_info[t_pid]['alive'] = False; msg_list.append(f"💀 {t_info['name']} 암살당함.")
                else: msg_list.append("🕊️ 평화로운 밤.")
                
                if st.session_state.reporter_target_day:
                    r_pid = st.session_state.reporter_target_day
                    msg_list.append(f"📰 [특종] {st.session_state.players_info[r_pid]['name']} 직업은 [{st.session_state.players_info[r_pid]['role']}]")
                    st.session_state.reporter_target_day = None
                st.session_state.sys_msg = "\n".join(msg_list)
            else:
                st.session_state.day += 1; st.session_state.is_night = True; st.session_state.night_targets = {}
                st.session_state.night_queue = [r for r in night_order if r in get_alive_roles()]
                st.session_state.current_role_idx = -1
                st.session_state.day_vote_target = None # 밤으로 넘어갈 때도 깔끔하게 초기화
                st.session_state.sys_msg = "🌙 밤이 되었습니다. [▶ 다음]을 누르세요."
            st.rerun()

def update_night_sys_msg():
    if st.session_state.current_role_idx == -1: st.session_state.sys_msg = "🌙 대기 중. [▶ 다음] 선택."
    elif st.session_state.current_role_idx >= len(st.session_state.night_queue): st.session_state.sys_msg = "🌙 행동 종료. 아래 [다음 (낮) ⏩] 선택."
    else:
        role = st.session_state.night_queue[st.session_state.current_role_idx]
        msg = {"스파이":"확인할 대상 선택", "마피아":"암살 대상 선택", "의사":"치료 대상 선택", "경찰":"조사 대상 선택", "탐정":"추리 대상 선택"}
        if role == "기자":
            if st.session_state.day == 1: m = "🚫 1일차 취재 불가"
            elif st.session_state.reporter_used: m = "🚫 특종 이미 사용됨"
            else: m = "📝 취재 대상 선택"
        else: m = f"📝 {msg[role]}"
        st.session_state.sys_msg = f"[{role}] {m}"

def handle_night_action(pid, pinfo):
    role = st.session_state.night_queue[st.session_state.current_role_idx]
    if role == "기자" and (st.session_state.day == 1 or st.session_state.reporter_used): return 
    
    st.session_state.night_targets[role] = pid
    t_role, t_name = pinfo['role'], pinfo['name']
    
    if role == "스파이":
        if "마피아" in t_role: st.session_state.spy_connected = True; m = f"🤝 마피아({t_name}) 발견."
        else: m = f"👁️ {t_name}은(는) [{t_role}]."
    elif role == "마피아": m = f"🔫 {t_name} 암살 지목."
    elif role == "의사": m = f"💉 {t_name} 치료 지목."
    elif role == "경찰": m = f"🚨 {t_name}은(는) 마피아가 맞음!" if "마피아" in t_role else f"✅ {t_name}은(는) 마피아 아님."
    elif role == "기자": st.session_state.reporter_used = True; st.session_state.reporter_target_day = pid; m = f"📸 {t_name} 취재 완료."
    elif role == "탐정":
        v = next((st.session_state.players_info[t]['name'] for r, t in st.session_state.night_targets.items() if r in t_role), None)
        m = f"🔍 {t_name}은(는) [{v}] 지목함." if v else f"🔍 {t_name} 행동 없음."
    
    st.session_state.sys_msg = m
    st.rerun()

if st.session_state.phase == 'setup': render_setup()
else: render_game()
