import streamlit as st
import random
import copy

# 모바일 화면에 맞게 레이아웃 넓게 쓰기
st.set_page_config(page_title="마피아 게임 어시스턴트", page_icon="🕵️", layout="centered")

# ==========================================
# 1. 세션 상태 초기화
# ==========================================
def init_session_state():
    default_states = {
        'phase': 'setup',              
        'player_count': 4,
        'roles_pool': [],              
        'pool_created': False,         # (수정) 역할 풀 생성 여부 유지
        'players_info': {},            
        
        # 참가자 뽑기 모드용 상태
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
        
        # 특수 직업 상태
        'spy_connected': False,
        'reporter_used': False,
        'reporter_target_day': None,
        
        # UI 상태
        'sys_msg': "",
        'vote_mode': False             
    }
    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

special_roles_pool = ["🪖 군인", "🏛️ 정치인", "📰 기자", "🔍 탐정"]
night_order = ["스파이", "마피아", "의사", "경찰", "기자", "탐정"]
role_desc = {
    "🕵️ 마피아": "밤마다 1명 암살",
    "👮 경찰": "밤마다 마피아 여부 확인",
    "💉 의사": "밤마다 1명 치료",
    "🙂 시민": "선량한 시민입니다. 투표로 마피아를 잡으세요.",
    "🕶️ 스파이": "마피아 찾으면 접선 (밤에 마피아와 함께 행동)",
    "📰 기자": "2일차 밤부터 1명 취재 (다음날 아침 직업 전체공개, 1회용)",
    "🔍 탐정": "밤에 대상이 누구를 지목했는지 확인",
    "🏛️ 정치인": "투표 시 2표 행사",
    "🪖 군인": "마피아 공격 1회 자동 방어"
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
        elif "스파이" in role and st.session_state.spy_connected: 
            mafia_count += 1
        else:
            citizen_count += 1

    if mafia_count == 0: return "🎉 시민 승리!"
    elif mafia_count >= citizen_count: return "💀 마피아 승리!"
    return None

def save_timeline():
    state_copy = {
        'day': st.session_state.day,
        'is_night': st.session_state.is_night,
        'players_info': copy.deepcopy(st.session_state.players_info),
        'night_queue': copy.deepcopy(st.session_state.night_queue),
        'current_role_idx': st.session_state.current_role_idx,
        'night_targets': copy.deepcopy(st.session_state.night_targets),
        'spy_connected': st.session_state.spy_connected,
        'reporter_used': st.session_state.reporter_used,
        'reporter_target_day': st.session_state.reporter_target_day,
        'sys_msg': st.session_state.sys_msg
    }
    st.session_state.history.append(state_copy)

def restore_timeline():
    if st.session_state.history:
        prev_state = st.session_state.history.pop()
        for k, v in prev_state.items():
            st.session_state[k] = v

# ==========================================
# 3. 설정 화면 렌더링
# ==========================================
def render_setup():
    st.title("🕵️ 마피아 게임 어시스턴트")
    
    st.session_state.player_count = st.selectbox("인원수 설정", [4, 5, 6, 7, 8], index=0)
    setup_method = st.radio("역할 뽑기 방식", ["사회자 방식으로 뽑기", "참가자 방식으로 뽑기"], horizontal=True)
    
    st.divider()

    # --- 사회자 방식 ---
    if setup_method == "사회자 방식으로 뽑기":
        name_method = st.radio("이름 설정 방식", ["이름을 숫자로 만들기 (P1, P2...)", "이름 직접 입력하기"], horizontal=True)
        
        player_names = []
        if "직접" in name_method:
            st.write("플레이어 이름을 입력하세요:")
            cols = st.columns(2)
            for i in range(st.session_state.player_count):
                with cols[i % 2]:
                    name = st.text_input(f"플레이어 {i+1} 이름", key=f"name_input_{i}")
                    player_names.append(name if name else f"P{i+1}")
        else:
            player_names = [f"P{i+1}" for i in range(st.session_state.player_count)]

        if st.button("👥 역할 생성 및 배정완료", use_container_width=True, type="primary"):
            roles = setup_roles(st.session_state.player_count)
            st.session_state.draw_log = []
            st.session_state.players_info = {}
            for i in range(st.session_state.player_count):
                role = roles[i]
                st.session_state.players_info[i+1] = {
                    "name": player_names[i], "role": role, "alive": True, "shield": "군인" in role
                }
                st.session_state.draw_log.append(f"{player_names[i]} → {role}")
            start_game_init()

    # --- 참가자 방식 ---
    else:
        # (수정) roles_pool이 비어있는지가 아니라, pool_created 상태를 기준으로 판단
        if not st.session_state.pool_created:
            if st.button("🎲 역할 풀 생성하기", use_container_width=True):
                st.session_state.roles_pool = setup_roles(st.session_state.player_count)
                st.session_state.setup_turn_idx = 0
                st.session_state.players_info = {}
                st.session_state.draw_log = []
                st.session_state.pool_created = True
                st.rerun()

        if st.session_state.pool_created:
            turn = st.session_state.setup_turn_idx
            
            if turn < st.session_state.player_count:
                st.subheader(f"🙋‍♂️ {turn+1}번째 플레이어")
                p_name = st.text_input("이름을 입력하고 직업을 배정 받으세요.", key="p_name", disabled=st.session_state.role_revealed)
                
                if not st.session_state.role_revealed:
                    if st.button("확인하기", use_container_width=True):
                        if not p_name: p_name = f"P{turn+1}"
                        role = st.session_state.roles_pool.pop()
                        st.session_state.players_info[turn+1] = {
                            "name": p_name, "role": role, "alive": True, "shield": "군인" in role
                        }
                        st.session_state.draw_log.append(f"{p_name} → {role}")
                        st.session_state.role_revealed = True
                        st.rerun()
                else:
                    role_assigned = st.session_state.players_info[turn+1]['role']
                    st.success(f"당신의 직업은 **[{role_assigned}]** 입니다!\n\n({role_desc[role_assigned]})")
                    
                    is_last = (turn == st.session_state.player_count - 1)
                    
                    st.markdown("""
                    <style>
                    button:has(div:contains('설정 마치기')) { background-color: #ff4b4b !important; color: white !important; border-color: #ff4b4b !important; }
                    button:has(div:contains('다음사람')) { background-color: #00cc66 !important; color: white !important; border-color: #00cc66 !important; }
                    </style>
                    """, unsafe_allow_html=True)

                    if not is_last:
                        st.info("직업 확인을 마쳤으면, 다음사람 버튼을 누르고 다음 사람에게 기기를 전달하세요.")
                        if st.button("다음사람 ➡️", use_container_width=True):
                            st.session_state.role_revealed = False
                            st.session_state.setup_turn_idx += 1
                            st.rerun()
                    else:
                        st.warning("직업 확인을 마쳤으면, 사회자에게 기기를 전달하세요.")
                        if st.button("설정 마치기", use_container_width=True):
                            start_game_init()

def start_game_init():
    st.session_state.phase = 'game'
    st.session_state.history = []
    st.session_state.day = 1
    st.session_state.is_night = True
    alive_roles = get_alive_roles()
    st.session_state.night_queue = [r for r in night_order if r in alive_roles]
    st.session_state.current_role_idx = -1
    st.session_state.sys_msg = "🌙 1일차 밤이 되었습니다. [다음 직업 ▶] 버튼을 눌러주세요."
    st.rerun()

# ==========================================
# 4. 게임 화면 렌더링
# ==========================================
def render_game():
    # -----------------------------------------------------
    # (수정) 1. 스크롤을 내려도 고정되는 요일 헤더 (Sticky)
    # -----------------------------------------------------
    bg_color = "#1e1e1e" if st.session_state.is_night else "#ffebcc"
    text_color = "white" if st.session_state.is_night else "black"
    phase_text = f"🌙 {st.session_state.day}일차 밤" if st.session_state.is_night else f"☀️ {st.session_state.day}일차 낮"
    
    st.markdown(f"""
        <style>
        .fixed-header {{
            position: fixed;
            top: 2.875rem; /* Streamlit 기본 상단바 바로 아래 */
            left: 0;
            width: 100%;
            background-color: {bg_color};
            color: {text_color};
            z-index: 9999;
            text-align: center;
            padding: 12px 0;
            font-size: 1.3rem;
            font-weight: bold;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        .spacer {{ height: 60px; }}
        </style>
        <div class="fixed-header">{phase_text}</div>
        <div class="spacer"></div>
    """, unsafe_allow_html=True)

    # -----------------------------------------------------
    # (수정) 2. 게임 초기화 버튼 (최상단)
    # -----------------------------------------------------
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 게임 초기화 (처음으로)", use_container_width=True):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
    with col2:
        with st.expander("👁️ 역할 로그 (사회자용)"):
            for log in st.session_state.draw_log: st.write(log)

    st.write("---")

    # -----------------------------------------------------
    # (수정) 3. 시스템 메시지 (두번째)
    # -----------------------------------------------------
    win_status = check_win()
    if win_status:
        st.error(f"🏆 게임 종료: {win_status}")
    else:
        st.info(f"**시스템:**\n\n{st.session_state.sys_msg}")

    st.write("---")

    # -----------------------------------------------------
    # (수정) 4. 다음 행동 조작 (세번째)
    # -----------------------------------------------------
    if st.session_state.is_night:
        st.subheader("🌙 밤 행동 조작")
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.button("◀ 이전 직업", use_container_width=True, disabled=st.session_state.current_role_idx <= -1):
                st.session_state.current_role_idx -= 1
                update_night_sys_msg()
                st.rerun()
        with c2:
            if st.session_state.current_role_idx == -1:
                st.markdown("<div style='text-align:center; padding:10px;'>대기 중</div>", unsafe_allow_html=True)
            elif st.session_state.current_role_idx >= len(st.session_state.night_queue):
                st.markdown("<div style='text-align:center; padding:10px;'>행동 완료됨</div>", unsafe_allow_html=True)
            else:
                current_r = st.session_state.night_queue[st.session_state.current_role_idx]
                st.markdown(f"<div style='text-align:center; padding:10px; font-weight:bold; color:red;'>[{current_r}] 차례</div>", unsafe_allow_html=True)
        with c3:
            if st.button("다음 직업 ▶", use_container_width=True, disabled=st.session_state.current_role_idx >= len(st.session_state.night_queue)):
                st.session_state.current_role_idx += 1
                update_night_sys_msg()
                st.rerun()
    else:
        st.subheader("☀️ 낮 행동 조작")
        st.session_state.vote_mode = st.toggle("🗳️ '투표로 죽이기' 모드 켜기", value=st.session_state.vote_mode)
        if st.session_state.vote_mode:
            st.warning("아래 플레이어 버튼을 눌러 처형하거나, 실수로 죽인 사람을 살릴 수 있습니다.")

    st.write("---")

    # -----------------------------------------------------
    # (수정) 5. 시간선 이동 (네번째)
    # -----------------------------------------------------
    st.subheader("⏳ 시간선 이동")
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        if st.button("⏪ 이전 시간선으로", use_container_width=True, disabled=len(st.session_state.history)==0):
            restore_timeline()
            st.rerun()
    with t_col2:
        btn_label = "다음 시간선 (낮으로) ⏩" if st.session_state.is_night else "다음 시간선 (밤으로) ⏩"
        if st.button(btn_label, type="primary", use_container_width=True):
            save_timeline()
            
            if st.session_state.is_night:
                st.session_state.is_night = False
                st.session_state.vote_mode = False
                msg_list = [f"☀️ {st.session_state.day}일차 아침이 밝았습니다."]
                
                if "마피아" in st.session_state.night_targets:
                    target = st.session_state.night_targets["마피아"]
                    t_info = st.session_state.players_info[target]
                    
                    if "의사" in st.session_state.night_targets and st.session_state.night_targets["의사"] == target:
                        msg_list.append("💉 의사의 활약으로 간밤에 아무도 죽지 않았습니다!")
                    elif "군인" in t_info['role'] and t_info['shield']:
                        st.session_state.players_info[target]['shield'] = False
                        msg_list.append(f"🪖 군인({t_info['name']})님이 마피아의 공격을 버텼습니다!")
                    else:
                        msg_list.append(f"💀 밤 사이 {t_info['name']}님이 마피아에게 암살당했습니다.")
                        st.session_state.players_info[target]['alive'] = False
                else:
                    msg_list.append("🕊️ 간밤에 아무도 죽지 않았습니다.")

                if st.session_state.reporter_target_day:
                    t_pid = st.session_state.reporter_target_day
                    t_role = st.session_state.players_info[t_pid]['role']
                    msg_list.append(f"📰 [특종] {st.session_state.players_info[t_pid]['name']}님의 직업은 [{t_role}]로 밝혀졌습니다!")
                    st.session_state.reporter_target_day = None

                st.session_state.sys_msg = "\n".join(msg_list)
            else:
                st.session_state.day += 1
                st.session_state.is_night = True
                st.session_state.night_targets = {}
                alive_roles = get_alive_roles()
                st.session_state.night_queue = [r for r in night_order if r in alive_roles]
                st.session_state.current_role_idx = -1
                st.session_state.sys_msg = f"🌙 {st.session_state.day}일차 밤이 되었습니다. [다음 직업 ▶] 버튼을 눌러주세요."
            st.rerun()

    st.write("---")

    # -----------------------------------------------------
    # (수정) 6. 플레이어 목록 (마지막) 및 정렬 문제 수정
    # -----------------------------------------------------
    st.write("### 👥 플레이어 목록")
    cols = st.columns(2)
    
    # 딕셔너리의 키(pid)를 기준으로 1, 2, 3, 4 순으로 정렬되게 처리
    sorted_players = sorted(st.session_state.players_info.items(), key=lambda x: x[0])
    
    for i, (pid, pinfo) in enumerate(sorted_players):
        status = "💀 사망" if not pinfo['alive'] else "🙂 생존"
        btn_text = f"{pinfo['name']} ({pinfo['role']})\n{status}"
        
        with cols[i % 2]:
            if not st.session_state.is_night and st.session_state.vote_mode:
                btn_action_text = f"💖 살리기: {pinfo['name']}" if not pinfo['alive'] else f"💀 처형: {pinfo['name']}"
                if st.button(btn_action_text, key=f"v_{pid}", use_container_width=True):
                    st.session_state.players_info[pid]['alive'] = not pinfo['alive']
                    act = "살렸습니다" if st.session_state.players_info[pid]['alive'] else "처형했습니다"
                    st.session_state.sys_msg = f"⚖️ [수동 조작] {pinfo['name']}님을 {act}."
                    st.rerun()
            
            else:
                is_disabled = True
                if st.session_state.is_night:
                    if 0 <= st.session_state.current_role_idx < len(st.session_state.night_queue):
                        if pinfo['alive']: 
                            is_disabled = False

                if st.button(btn_text, key=f"p_{pid}", use_container_width=True, disabled=is_disabled):
                    handle_night_action(pid, pinfo)

def update_night_sys_msg():
    if st.session_state.current_role_idx == -1:
        st.session_state.sys_msg = "🌙 대기 중입니다. [다음 직업 ▶]을 누르세요."
    elif st.session_state.current_role_idx >= len(st.session_state.night_queue):
        st.session_state.sys_msg = "🌙 모든 밤 행동이 끝났습니다. 아래의 [다음 시간선 (낮으로) ⏩] 버튼을 누르세요."
    else:
        role = st.session_state.night_queue[st.session_state.current_role_idx]
        if role == "스파이": msg = "📝 스파이: 확인할 사람을 선택하세요."
        elif role == "마피아": msg = "📝 마피아: 암살할 사람을 선택하세요."
        elif role == "의사": msg = "📝 의사: 살릴 사람을 선택하세요."
        elif role == "경찰": msg = "📝 경찰: 조사할 사람을 선택하세요."
        elif role == "기자":
            if st.session_state.day == 1: msg = "🚫 기자는 1일차에 취재할 수 없습니다."
            elif st.session_state.reporter_used: msg = "🚫 기자는 이미 특종을 냈습니다."
            else: msg = "📝 기자: 취재할 대상을 선택하세요."
        elif role == "탐정": msg = "📝 탐정: 추리할 대상을 선택하세요."
        st.session_state.sys_msg = f"[{role}] 차례입니다. {msg}"

def handle_night_action(pid, pinfo):
    role = st.session_state.night_queue[st.session_state.current_role_idx]
    target_role = pinfo['role']
    target_name = pinfo['name']
    
    if role == "기자" and (st.session_state.day == 1 or st.session_state.reporter_used):
        return 
        
    st.session_state.night_targets[role] = pid
    
    if role == "스파이":
        if "마피아" in target_role:
            st.session_state.spy_connected = True
            st.session_state.sys_msg = f"🤝 [접선 성공] 마피아({target_name})를 찾았습니다."
        else:
            st.session_state.sys_msg = f"👁️ [확인] {target_name}님은 [{target_role}] 입니다."
    elif role == "마피아":
        st.session_state.sys_msg = f"🔫 {target_name}님을 암살 지목했습니다."
    elif role == "의사":
        st.session_state.sys_msg = f"💉 {target_name}님을 치료 지목했습니다."
    elif role == "경찰":
        if "마피아" in target_role: st.session_state.sys_msg = f"🚨 {target_name}님은 마피아가 맞습니다!!"
        else: st.session_state.sys_msg = f"✅ {target_name}님은 마피아가 아닙니다."
    elif role == "기자":
        st.session_state.reporter_used = True
        st.session_state.reporter_target_day = pid
        st.session_state.sys_msg = f"📸 {target_name} 취재 완료. (직업: [{target_role}])"
    elif role == "탐정":
        target_visited = None
        for r, t_pid in st.session_state.night_targets.items():
            if r in target_role: 
                target_visited = st.session_state.players_info[t_pid]['name']
                break
        if target_visited:
            st.session_state.sys_msg = f"🔍 {target_name}님은 오늘 밤 [{target_visited}]님을 지목했습니다."
        else:
            st.session_state.sys_msg = f"🔍 {target_name}님은 오늘 밤 아무도 지목하지 않았습니다."
    
    st.rerun()

# ==========================================
# 메인 라우팅
# ==========================================
if st.session_state.phase == 'setup':
    render_setup()
else:
    render_game()
