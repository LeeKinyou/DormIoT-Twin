from __future__ import annotations

from dormiot.schemas.device import DeviceStatus


def _status_color(status: str) -> str:
    """设备状态 → SVG 填充色"""
    return {
        "ALARM": "#ef4444",     # 红
        "WARNING": "#f59e0b",   # 黄
        "NORMAL": "#22c55e",    # 绿
    }.get(status, "#94a3b8")    # 灰（离线/无数据）


def render_floor_svg(
    building_id: str,
    rooms: list[str],
    device_status: dict[str, dict],
    selected_room: str | None = None,
) -> str:
    """生成单层楼 SVG 楼层平面图

    Args:
        building_id: 楼栋号
        rooms: 房间号列表
        device_status: {device_id: {"status": str, "current_power": str, ...}}
        selected_room: 当前选中的房间号

    Returns:
        SVG HTML 字符串
    """
    room_w, room_h = 120, 80
    gap = 10
    cols = 3
    rows = (len(rooms) + cols - 1) // cols
    svg_w = cols * (room_w + gap) + gap
    svg_h = rows * (room_h + gap) + gap + 30  # 30 for title

    rects = []
    for i, room_id in enumerate(rooms):
        col = i % cols
        row = i // cols
        x = gap + col * (room_w + gap)
        y = 30 + gap + row * (room_h + gap)

        device_id = f"MOCK_METER_BLDG{building_id}_RM{room_id}"
        info = device_status.get(device_id, {})
        status = info.get("status", "UNKNOWN")
        color = _status_color(status)
        power_raw = info.get("current_power")
        try:
            power_text = f"{float(power_raw):.0f}W"
        except (TypeError, ValueError):
            power_text = "--"

        stroke = 'stroke="#1e40af" stroke-width="3"' if room_id == selected_room else 'stroke="#cbd5e1" stroke-width="1"'

        rects.append(f'''
        <g class="room" data-room="{room_id}" style="cursor:pointer">
            <rect x="{x}" y="{y}" width="{room_w}" height="{room_h}"
                  rx="6" fill="{color}" fill-opacity="0.85" {stroke}/>
            <text x="{x + room_w/2}" y="{y + 28}" text-anchor="middle"
                  font-size="14" font-weight="bold" fill="#1e293b">{room_id}</text>
            <text x="{x + room_w/2}" y="{y + 50}" text-anchor="middle"
                  font-size="11" fill="#334155">{power_text}</text>
            <text x="{x + room_w/2}" y="{y + 68}" text-anchor="middle"
                  font-size="10" fill="#475569">{status}</text>
        </g>''')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}"
         style="font-family:system-ui,sans-serif">
        <text x="{svg_w/2}" y="20" text-anchor="middle" font-size="16" font-weight="bold" fill="#1e293b">
            {building_id}号楼 楼层平面图
        </text>
        {"".join(rects)}
    </svg>'''
    return svg


def render_building_selector(buildings: list[str]) -> str:
    """渲染楼栋选择器，返回选中的 building_id"""
    import streamlit as st
    return st.selectbox("选择楼栋", buildings, index=0)


def render_floor_plan_html(
    building_id: str,
    rooms: list[str],
    device_status: dict[str, dict],
    selected_room: str | None = None,
) -> str:
    """生成带点击交互的完整 HTML（用于 st.components.v1.html）"""
    svg = render_floor_svg(building_id, rooms, device_status, selected_room)
    return f'''
    <div id="floor-plan">{svg}</div>
    <script>
    document.querySelectorAll('.room').forEach(el => {{
        el.addEventListener('click', function() {{
            const room = this.getAttribute('data-room');
            const url = new URL(window.location);
            url.searchParams.set('room', room);
            window.history.replaceState(null, '', url);
            window.parent.postMessage({{type: 'streamlit:setQueryParams', room: room}}, '*');
        }});
    }});
    </script>
    '''
