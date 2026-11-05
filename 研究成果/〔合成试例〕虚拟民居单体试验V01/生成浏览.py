#!/usr/bin/env python3
"""Build the self-contained, offline V01 case browser from its JSON inputs."""

from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
MODEL_FILE = HERE / "案例模型.json"
RESULT_FILE = HERE / "验证" / "推演结果.json"
OUTPUT_FILE = HERE / "案例浏览.html"

CLASS_ZH = {
    "Building": "建筑整体",
    "Space": "空间",
    "Element": "构件",
    "Interface": "界面",
    "Evidence": "证据记录",
    "Wall": "墙体",
    "Column": "柱",
    "Roof": "屋顶系统",
    "RoofSurface": "屋面坡面",
}
LABEL_ZH = {
    "Building": "建筑整体",
    "Space": "空间",
    "Element": "构件",
    "Interface": "界面",
    "Evidence": "证据",
    "Wall": "墙体",
    "Column": "柱",
    "Roof": "屋顶",
    "RoofSurface": "屋面坡面",
    "材质_木": "木",
    "材质_砖": "砖",
    "材质_灰泥": "灰泥",
    "材质_陶瓦": "陶瓦",
}
MATERIAL_ZH = {
    "材质_木": "木",
    "材质_砖": "砖",
    "材质_灰泥": "灰泥",
    "材质_陶瓦": "陶瓦",
}
PROPERTY_ZH = {
    "caseId": "案例编号",
    "recordStatus": "记录状态",
    "storeys": "层数",
    "axisWidthM": "主屋轴网宽度",
    "axisDepthM": "主屋轴网进深",
    "axisFootprintAreaM2": "主屋轴网投影面积",
    "facingAzimuthDeg": "朝向方位角",
    "wallSupportHeightM": "外墙轴线处承托线标高",
    "ridgeHeightM": "屋脊标高",
    "use": "用途（合成设定）",
    "enclosure": "围合状态",
    "floorZ": "地坪标高",
    "areaM2": "平面分析面积",
    "areaBasis": "面积口径",
    "divisionBasis": "分区依据",
    "axisAzimuthDeg": "主轴方位角",
    "lengthM": "轴线长度",
    "thicknessM": "墙厚",
    "referenceHeightM": "参照标高",
    "heightBasis": "墙顶高度口径",
    "maxHeightM": "最高点标高",
    "diameterM": "柱径",
    "heightM": "柱高",
    "form": "屋面形式",
    "slopeDeg": "几何坡度",
    "eaveHeightM": "外挑檐口标高",
    "overhangM": "屋面外挑",
    "ridgeAzimuthDeg": "屋脊方位角",
    "materialLabelMeaning": "材料标签含义",
    "kind": "界面类型",
    "widthM": "跨度／宽度",
    "sillZ": "窗台标高",
    "headZ": "洞口顶标高",
    "passage": "基准通行判断",
    "accessContext": "通行情境",
    "physicalSeparation": "实体分隔",
    "boundaryBasis": "界面依据",
    "widthBasis": "宽度口径",
    "evidenceKind": "证据类型",
    "origin": "来源",
    "locator": "证据编号",
    "description": "说明",
    "observationDate": "观测日期",
    "isRealWorldEvidence": "真实世界证据",
    "slopeAzimuthDeg": "坡向方位角",
    "representation": "几何表示方式",
}

RELATION_STATUS_ZH = {
    "synthetic_assignment": "人工合成设定",
    "rule_derived": "规则推导",
    "geometry_derived": "几何推导",
    "derived_from_synthetic_evidence": "由合成输入推导",
    "supported": "输入有依据",
    "derived": "推导结果",
    "unknown": "未知",
    "synthetic_geometry_derived": "由合成几何推导",
}
RELATION_TYPE_ZH = {
    "AXIS_JOINS": "墙轴交会",
    "ENVELOPE_INTERSECTS": "墙柱简化包络相交",
    "SHARES_BOUNDARY": "坡面共享边界",
}
ANALYSIS_KIND_ZH = {
    "geometry_calculation": "几何计算",
    "graph_rule": "关系规则",
    "spatial_measurement": "空间量测",
}
ANALYSIS_VALUE_LABEL_ZH = {
    "direction": "方向",
    "distanceM": "距离",
    "azimuthDeg": "方位角",
    "axisAngleDeg": "轴线夹角",
}


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def js_json(value: Any) -> str:
    """JSON safe to embed in an inline script element."""
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def nfmt(value: float, digits: int = 2) -> str:
    rounded = round(float(value), digits)
    return f"{rounded:.{digits}f}".rstrip("0").rstrip(".")


def node_title(node: dict[str, Any]) -> str:
    return f"{node['id']} · {node['name']}"


def node_attrs(node: dict[str, Any], extra: str = "") -> str:
    labels = " ".join(node.get("labels", []))
    title = node_title(node)
    return (
        f'class="geo selectable {extra}" data-node-id="{esc(node["id"])}" '
        f'data-labels="{esc(labels)}" tabindex="0" role="button" '
        f'aria-label="{esc(title)}"'
    )


def node_map(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {node["id"]: node for node in model["nodes"]}


def get_node(model: dict[str, Any], node_id: str) -> dict[str, Any]:
    return node_map(model)[node_id]


def material_labels(node: dict[str, Any]) -> list[str]:
    return [label for label in node.get("labels", []) if label in MATERIAL_ZH]


def svg_text(x: float, y: float, content: str, size: int = 16, cls: str = "svg-label", anchor: str = "middle") -> str:
    return f'<text class="{esc(cls)}" x="{nfmt(x, 1)}" y="{nfmt(y, 1)}" text-anchor="{anchor}" font-size="{size}">{esc(content)}</text>'


def shape_attrs(cls: str, attrs: str) -> str:
    match = re.search(r'\bclass="([^"]*)"', attrs)
    if match:
        cls = " ".join(part for part in (cls, match.group(1)) if part)
        attrs = attrs[:match.start()] + attrs[match.end():]
    return f'class="{esc(cls)}" {attrs}'


def rect(x: float, y: float, w: float, h: float, cls: str = "", attrs: str = "") -> str:
    return f'<rect x="{nfmt(x, 1)}" y="{nfmt(y, 1)}" width="{nfmt(w, 1)}" height="{nfmt(h, 1)}" {shape_attrs(cls, attrs)}/>'


def line(x1: float, y1: float, x2: float, y2: float, cls: str = "", attrs: str = "") -> str:
    return f'<line x1="{nfmt(x1, 1)}" y1="{nfmt(y1, 1)}" x2="{nfmt(x2, 1)}" y2="{nfmt(y2, 1)}" {shape_attrs(cls, attrs)}/>'


def poly(points: list[tuple[float, float]], cls: str = "", attrs: str = "") -> str:
    pairs = " ".join(f"{nfmt(x,1)},{nfmt(y,1)}" for x, y in points)
    return f'<polygon points="{pairs}" {shape_attrs(cls, attrs)}/>'


def polyline(points: list[tuple[float, float]], cls: str = "", attrs: str = "") -> str:
    pairs = " ".join(f"{nfmt(x,1)},{nfmt(y,1)}" for x, y in points)
    return f'<polyline points="{pairs}" {shape_attrs(cls, attrs)}/>'


def make_svg(view_id: str, width: int, height: int, content: str) -> str:
    return (
        f'<svg class="drawing-svg" data-view="{esc(view_id)}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(view_id)}示意图">'
        f'<defs>'
        f'<pattern id="{view_id}-roof-hatch" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(38)">'
        f'<line x1="0" y1="0" x2="0" y2="9" stroke="#b5c1b9" stroke-width="1"/></pattern>'
        f'<marker id="{view_id}-arrow" markerWidth="7" markerHeight="7" refX="3.5" refY="3.5" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 7 3.5 L 0 7 z" fill="#59736a"/></marker>'
        f'</defs><rect class="svg-paper" x="0" y="0" width="{width}" height="{height}"/>{content}</svg>'
    )


def view_caption(view_id: str, title: str, subtitle: str) -> str:
    return f'<div class="view-heading"><div><span class="drawing-id">{esc(view_id)}</span><strong>{esc(title)}</strong></div><span>{esc(subtitle)}</span></div>'


def plan_svg(model: dict[str, Any]) -> str:
    nodes = node_map(model)
    p = model["parameters"]
    w, d = p["width_m"], p["depth_m"]
    veranda, yard = p["veranda_depth_m"], p["courtyard_depth_m"]
    s = 46.0
    ox, top_y = 125.0, 60.0
    north_edge = 8.0

    def X(x: float) -> float:
        return ox + (x + 0.8) * s

    def Y(y: float) -> float:
        return top_y + (north_edge - y) * s

    body: list[str] = []
    # Room fills are explicitly planar analysis regions, not a claim of sealed 3D volumes.
    for node_id, fill, name in [
        ("S02", "space-blue", "西室"),
        ("S01", "space-center", "堂屋"),
        ("S03", "space-blue", "东室"),
        ("S04", "space-veranda", "前廊"),
        ("S05", "space-yard", "前院"),
    ]:
        node = nodes[node_id]
        geo = node["geometry"]
        x0, y0 = geo["min"]
        x1, y1 = geo["max"]
        attrs = node_attrs(node, "space-region")
        body.append(rect(X(x0), Y(y1), (x1 - x0) * s, (y1 - y0) * s, fill, attrs))
        body.append(svg_text(X((x0 + x1) / 2), Y((y0 + y1) / 2), name, 17, "room-label"))
        if node_id in ("S01", "S02", "S03"):
            body.append(svg_text(X((x0 + x1) / 2), Y((y0 + y1) / 2) + 22, node_id, 12, "room-id"))

    # South-side external reference region is shown as an outside reference only.
    outside = nodes["S06"]["geometry"]
    x0, y0 = outside["min"]
    x1, y1 = outside["max"]
    body.append(rect(X(x0), Y(y1), (x1 - x0) * s, (y1 - y0) * s, "space-reference", node_attrs(nodes["S06"], "space-region")))
    body.append(svg_text(X((x0 + x1) / 2), Y((y0 + y1) / 2), "南侧外部参照区", 12, "small-label"))

    # Building outline is an interactive, lightly emphasized reference frame.
    b01 = nodes["B01"]
    body.append(rect(X(0), Y(d), w * s, d * s, "building-frame", node_attrs(b01, "outline-hit")))

    # Draw walls in pieces so every modeled wall interface is a true gap in plan.
    relationships = model["relationships"]
    realized = {rel["source"]: rel["target"] for rel in relationships if rel["type"] == "REALIZED_IN"}
    interfaces = {node["id"]: node for node in model["nodes"] if node["class"] == "Interface"}
    for wall in [node for node in model["nodes"] if "Wall" in node.get("labels", [])]:
        geo = wall["geometry"]
        a, b = geo["a"], geo["b"]
        horizontal = abs(b[0] - a[0]) >= abs(b[1] - a[1])
        axis0, axis1 = (a[0], b[0]) if horizontal else (a[1], b[1])
        low, high = min(axis0, axis1), max(axis0, axis1)
        cuts: list[tuple[float, float]] = []
        for interface_id, wall_id in realized.items():
            if wall_id != wall["id"]:
                continue
            ig = interfaces[interface_id]["geometry"]
            ia, ib = ig["a"], ig["b"]
            start, end = (ia[0], ib[0]) if horizontal else (ia[1], ib[1])
            cuts.append((max(low, min(start, end)), min(high, max(start, end))))
        cuts.sort()
        pieces: list[tuple[float, float]] = []
        cursor = low
        for c0, c1 in cuts:
            if c0 > cursor:
                pieces.append((cursor, c0))
            cursor = max(cursor, c1)
        if cursor < high:
            pieces.append((cursor, high))
        group_attrs = node_attrs(wall, "wall-group")
        body.append(f"<g {group_attrs}>")
        t = geo.get("thickness", p["wall_thickness_m"])
        fixed = (a[1] + b[1]) / 2 if horizontal else (a[0] + b[0]) / 2
        for lo, hi in pieces:
            if hi - lo <= 0.002:
                continue
            if horizontal:
                body.append(rect(X(lo), Y(fixed + t / 2), (hi - lo) * s, t * s, "wall-fill"))
            else:
                body.append(rect(X(fixed - t / 2), Y(hi), t * s, (hi - lo) * s, "wall-fill"))
        body.append("</g>")

    # Interface glyphs differentiate door openings, windows, and open boundaries.
    for iid, wall_id in realized.items():
        iface = interfaces[iid]
        kind = iface["properties"]["kind"]
        a, b = iface["geometry"]["a"], iface["geometry"]["b"]
        x1, y1, x2, y2 = X(a[0]), Y(a[1]), X(b[0]), Y(b[1])
        attrs = node_attrs(iface, "interface-mark")
        if kind == "window_opening":
            dx, dy = x2 - x1, y2 - y1
            length = max(math.hypot(dx, dy), 1)
            nx, ny = -dy / length * 2.5, dx / length * 2.5
            body.append(f'<g {attrs}>')
            body.append(line(x1 + nx, y1 + ny, x2 + nx, y2 + ny, "window-mark"))
            body.append(line(x1 - nx, y1 - ny, x2 - nx, y2 - ny, "window-mark"))
            body.append("</g>")
        else:
            body.append(f'<g {attrs}>{line(x1, y1, x2, y2, "door-mark")}</g>')

    # Open boundaries have no host wall; dashed green lines are only interface locations.
    for iface in interfaces.values():
        if iface["properties"].get("physicalSeparation") != "none":
            continue
        a, b = iface["geometry"]["a"], iface["geometry"]["b"]
        body.append(f'<g {node_attrs(iface, "interface-mark")}>{line(X(a[0]), Y(a[1]), X(b[0]), Y(b[1]), "open-mark")}</g>')

    # Porch posts use their actual 0.28 m plan diameter.
    for column in [node for node in model["nodes"] if "Column" in node.get("labels", [])]:
        c = column["geometry"]["center"]
        r = column["geometry"]["radius"] * s
        body.append(f'<g {node_attrs(column, "column-group")}><circle cx="{nfmt(X(c[0]),1)}" cy="{nfmt(Y(c[1]),1)}" r="{nfmt(r,1)}" class="column-fill"/></g>')
        body.append(svg_text(X(c[0]), Y(c[1]) + 22, column["id"], 11, "small-label"))

    # Room and opening notes are labels, not additional model objects.
    body.append(svg_text(X(4.8), Y(1.5) - 10, "I01 开放分界", 12, "interface-label"))
    body.append(svg_text(X(4.8), Y(-0.9), "I04 跨柱列9.32 m（含中间柱；非连续净宽）", 12, "interface-label"))
    body.append(svg_text(X(4.8), Y(-4.8) + 24, "I05 院门", 12, "interface-label"))

    # Dimension strings: three 3.2 m bays, total width, main depth, veranda, and yard.
    dim_y = Y(8.1)
    body.append(line(X(0), dim_y, X(w), dim_y, "dimension-line", f'marker-start="url(#{"EV02"}-arrow)" marker-end="url(#{"EV02"}-arrow)"'))
    for i in range(4):
        xx = X(i * p["bay_width_m"])
        body.append(line(xx, dim_y - 7, xx, dim_y + 7, "dimension-tick"))
        if i < 3:
            body.append(svg_text((X(i * p["bay_width_m"]) + X((i + 1) * p["bay_width_m"])) / 2, dim_y - 8, "3.2", 12, "dimension-text"))
    body.append(svg_text((X(0) + X(w)) / 2, dim_y + 18, "主屋轴网宽 9.6 m", 14, "dimension-text"))

    for y0, y1, x, label_text in [
        (0, d, -0.45, "主屋进深 7.2 m"),
        (-yard, 0, 10.05, "前院深 4.8 m"),
        (0, veranda, 10.05, "前廊 1.5 m"),
    ]:
        x0, x1 = X(x), X(x)
        body.append(line(x0, Y(y0), x1, Y(y1), "dimension-line", 'marker-start="url(#EV02-arrow)" marker-end="url(#EV02-arrow)"'))
        body.append(line(x0 - 6, Y(y0), x0 + 6, Y(y0), "dimension-tick"))
        body.append(line(x1 - 6, Y(y1), x1 + 6, Y(y1), "dimension-tick"))
        tx = x0 - 8 if x < 0 else x0 + 12
        ty = (Y(y0) + Y(y1)) / 2
        body.append(svg_text(tx, ty, label_text, 12, "dimension-text", "end" if x < 0 else "start"))

    # North arrow and coordinate cues.
    nx, ny = 775, 104
    body.append(line(nx, ny + 42, nx, ny, "north-arrow", 'marker-end="url(#EV02-arrow)"'))
    body.append(svg_text(nx, ny - 10, "北 / +Y", 14, "north-label"))
    body.append(svg_text(nx, ny + 63, "东为 +X", 12, "small-label"))

    # Key notes and legend occupy a stable right-side margin.
    body.append(svg_text(630, 265, "图例", 15, "legend-title", "start"))
    body.append(rect(630, 280, 20, 14, "wall-legend"))
    body.append(svg_text(660, 293, "墙体", 13, "legend-text", "start"))
    body.append('<line x1="630" y1="316" x2="650" y2="316" class="door-mark"/>')
    body.append(svg_text(660, 321, "门洞／院门（留空）", 13, "legend-text", "start"))
    body.append('<line x1="630" y1="344" x2="650" y2="344" class="window-mark"/>')
    body.append(svg_text(660, 349, "窗洞（留空）", 13, "legend-text", "start"))
    body.append('<line x1="630" y1="372" x2="650" y2="372" class="open-mark"/>')
    body.append(svg_text(660, 377, "无实体开放分界", 13, "legend-text", "start"))
    body.append('<circle cx="640" cy="404" r="7" class="column-fill"/>')
    body.append(svg_text(660, 409, "前廊柱（轴线 y=0）", 13, "legend-text", "start"))
    body.append(svg_text(630, 465, "平面分析区域", 13, "small-label", "start"))
    body.append(svg_text(630, 486, "示意尺寸来自合成设定", 13, "small-label", "start"))
    body.append(svg_text(630, 507, "不代表实测或施工放样", 13, "small-label", "start"))

    body.append(svg_text(26, 28, "平面北向向上 · X东、Y北、Z上", 13, "drawing-note", "start"))
    body.append(svg_text(26, 714, "尺寸单位：m · 墙上界面按几何留空；开放分界无实体墙", 12, "drawing-note", "start"))
    return make_svg("EV02", 940, 730, "".join(body))


def add_dimension_h(body: list[str], x0: float, x1: float, y: float, label_text: str, marker: str, size: int = 14) -> None:
    body.append(line(x0, y, x1, y, "dimension-line", f'marker-start="url(#{marker}-arrow)" marker-end="url(#{marker}-arrow)"'))
    body.append(line(x0, y - 7, x0, y + 7, "dimension-tick"))
    body.append(line(x1, y - 7, x1, y + 7, "dimension-tick"))
    body.append(svg_text((x0 + x1) / 2, y + 21, label_text, size, "dimension-text"))


def add_dimension_v(body: list[str], x: float, y0: float, y1: float, label_text: str, marker: str) -> None:
    body.append(line(x, y0, x, y1, "dimension-line", f'marker-start="url(#{marker}-arrow)" marker-end="url(#{marker}-arrow)"'))
    body.append(line(x - 7, y0, x + 7, y0, "dimension-tick"))
    body.append(line(x - 7, y1, x + 7, y1, "dimension-tick"))
    body.append(svg_text(x + 13, (y0 + y1) / 2, label_text, 13, "dimension-text", "start"))


def facade_svg(model: dict[str, Any], which: str) -> str:
    nodes = node_map(model)
    p = model["parameters"]
    is_south = which == "south"
    view_id = "EV03" if is_south else "EV04"
    wall_ids = ["W06", "W07"] if is_south else ["W03"]
    window_ids = ["I06", "I07"] if is_south else ["I08", "I09", "I10"]
    view_text = "视向：北（从南向北）" if is_south else "视向：南（从北向南）"
    scale = 54.0
    X = (lambda x: 180 + x * scale) if is_south else (lambda x: 180 + (p["width_m"] - x) * scale)
    Z = lambda z: 495 - z * scale

    def x_rect(x0: float, x1: float, z0: float, z1: float, cls: str) -> str:
        sx0, sx1 = sorted((X(x0), X(x1)))
        return rect(sx0, Z(z1), sx1 - sx0, (z1 - z0) * scale, cls)

    body: list[str] = []
    body.append(svg_text(35, 29, "主屋立面 · 前院围墙省略", 13, "drawing-note", "start"))
    body.append(svg_text(35, 50, view_text, 12, "drawing-note", "start"))

    # A long-side projection collapses roof depth. The roof band is drawn last so
    # it obscures wall/post portions behind the eave in this view.
    roof = nodes["RF01"]
    rg = roof["geometry"]

    # Rear/front wall tops follow roof_z at their own Y position. Interfaces cut holes.
    y_wall = p["veranda_depth_m"] if is_south else p["depth_m"]
    wall_top = roof_z(model, y_wall)
    openings = [nodes[iid] for iid in window_ids]
    for wall_id in wall_ids:
        wall = nodes[wall_id]
        geo = wall["geometry"]
        xlo, xhi = sorted([geo["a"][0], geo["b"][0]])
        attrs = node_attrs(wall, "wall-group")
        body.append(f"<g {attrs}>")
        cuts = []
        for win in openings:
            a, b = win["geometry"]["a"], win["geometry"]["b"]
            lo, hi = sorted([a[0], b[0]])
            if lo >= xlo - .001 and hi <= xhi + .001:
                cuts.append((lo, hi, win["properties"]["sillZ"], win["properties"]["headZ"]))
        cuts.sort()
        cursor = xlo
        for lo, hi, sill, head in cuts:
            if lo > cursor:
                body.append(x_rect(cursor, lo, 0, wall_top, "wall-fill-piece"))
            body.append(x_rect(lo, hi, 0, sill, "wall-fill-piece"))
            if head < wall_top:
                body.append(x_rect(lo, hi, head, wall_top, "wall-fill-piece"))
            cursor = hi
        if cursor < xhi:
            body.append(x_rect(cursor, xhi, 0, wall_top, "wall-fill-piece"))
        sxlo, sxhi = sorted((X(xlo), X(xhi)))
        body.append(line(sxlo, Z(0), sxlo, Z(wall_top), "wall-outline"))
        body.append(line(sxlo, Z(wall_top), sxhi, Z(wall_top), "wall-outline"))
        body.append(line(sxhi, Z(wall_top), sxhi, Z(0), "wall-outline"))
        body.append(line(sxhi, Z(0), sxlo, Z(0), "wall-outline"))
        body.append("</g>")

    # Front porch posts align with the y=0 axis; no beams are inferred.
    if is_south:
        for col in [n for n in model["nodes"] if "Column" in n.get("labels", [])]:
            cx = col["geometry"]["center"][0]
            cw = col["properties"]["diameterM"]
            body.append(f'<g {node_attrs(col, "column-group")}>{rect(X(cx - cw / 2), Z(col["properties"]["heightM"]), cw * scale, col["properties"]["heightM"] * scale, "column-fill")}</g>')

    # Window frames emphasize openings without inventing panes or shutters.
    for win in openings:
        a, b = win["geometry"]["a"], win["geometry"]["b"]
        x0, x1 = sorted([a[0], b[0]])
        sill, head = win["properties"]["sillZ"], win["properties"]["headZ"]
        body.append(f'<g {node_attrs(win, "interface-mark")}>{x_rect(x0, x1, sill, head, "window-elevation")}{line(X(x0), Z(sill), X(x1), Z(sill), "window-mark")}</g>')

    # Central I01 is an open boundary. Dashed jamb/header guides do not depict a door leaf.
    if is_south:
        open_iface = nodes["I01"]
        a, b = open_iface["geometry"]["a"], open_iface["geometry"]["b"]
        x0, x1 = sorted([a[0], b[0]])
        ztop = open_iface["properties"]["headZ"]
        body.append(f'<g {node_attrs(open_iface, "interface-mark")}>')
        body.append(line(X(x0), Z(0), X(x0), Z(ztop), "open-mark"))
        body.append(line(X(x1), Z(0), X(x1), Z(ztop), "open-mark"))
        body.append(line(X(x0), Z(ztop), X(x1), Z(ztop), "open-mark"))
        body.append("</g>")

    roof_x0, roof_x1 = sorted((X(rg["x"][0]), X(rg["x"][1])))
    body.append(f'<g {node_attrs(roof, "roof-group")}>')
    body.append(rect(roof_x0, Z(rg["ridgeZ"]), roof_x1 - roof_x0, (rg["ridgeZ"] - rg["eaveZ"]) * scale, "roof-projection"))
    body.append(line(X(0), Z(rg["ridgeZ"]), X(p["width_m"]), Z(rg["ridgeZ"]), "roof-ridge"))
    body.append(line(X(-p["roof_overhang_m"]), Z(rg["eaveZ"]), X(p["width_m"] + p["roof_overhang_m"]), Z(rg["eaveZ"]), "roof-eave"))
    body.append("</g>")
    # Dashed post/wall levels are hidden references beneath the projected eave.
    body.append(line(X(0), Z(p["wall_support_height_m"]), X(p["width_m"]), Z(p["wall_support_height_m"]), "hidden-reference"))
    if is_south:
        for ref_lo, ref_hi in ((0, 3.2), (6.4, 9.6)):
            body.append(line(X(ref_lo), Z(wall_top), X(ref_hi), Z(wall_top), "hidden-reference"))
        body.append(svg_text((X(x0) + X(x1)) / 2, Z(ztop) + 24, "I01 开放口 · 无门扇", 13, "interface-label"))
    body.append(svg_text(835, 205, "虚线是隐藏构件", 12, "small-label", "start"))
    body.append(svg_text(835, 222, "的标高参考", 12, "small-label", "start"))

    # Ground and dimensions.
    body.append(line(X(-.6), Z(0), X(10.2), Z(0), "ground-line"))
    add_dimension_h(body, X(0), X(p["width_m"]), 548, "主屋轴网宽 9.6 m（3 × 3.2 m）", view_id)
    body.append(line(X(0), Z(0), X(0), 540, "dimension-extension"))
    body.append(line(X(p["width_m"]), Z(0), X(p["width_m"]), 540, "dimension-extension"))
    # Height callouts preserve outer eave, support line, wall top, and ridge as distinct levels.
    call_x = 770
    body.append(line(call_x, Z(0), call_x, Z(5.6), "dimension-line", f'marker-start="url(#{view_id}-arrow)" marker-end="url(#{view_id}-arrow)"'))
    body.append(svg_text(call_x + 12, Z(5.6), "屋脊 5.6 m", 13, "dimension-text", "start"))
    if is_south:
        body.append(svg_text(call_x + 12, Z(wall_top), f"前墙顶 {nfmt(wall_top,4)} m", 13, "dimension-text", "start"))
        body.append(svg_text(call_x + 12, Z(3.6) + 15, "支承线 3.6 m", 13, "dimension-text", "start"))
    else:
        body.append(svg_text(call_x + 12, Z(3.6) + 7, "北墙顶 3.6 m", 13, "dimension-text", "start"))
    body.append(svg_text(call_x + 12, Z(3.2666666667) + 17, "真正檐口 3.2667 m", 13, "dimension-text", "start"))
    body.append(line(X(9.6), Z(wall_top), call_x - 12, Z(wall_top), "leader-line"))
    body.append(svg_text(835, 95, "屋面在南北立面中", 13, "small-label", "start"))
    body.append(svg_text(835, 116, "按Y向投影重叠表示", 13, "small-label", "start"))
    body.append(svg_text(835, 137, "山墙轮廓见东西立面", 13, "small-label", "start"))
    body.append(svg_text(835, 183, "示意非施工图", 13, "drawing-note", "start"))
    body.append(svg_text(35, 600, "窗洞按界面几何留空；门洞／开放分界按其类型表示；前院围墙省略", 12, "drawing-note", "start"))
    return make_svg(view_id, 960, 620, "".join(body))


def roof_z(model: dict[str, Any], y: float) -> float:
    contract = model["drawingContract"]
    # The defined contract is symmetric around the ridge at y=3.6.
    ridge = float(model["parameters"]["ridge_height_m"])
    support = float(model["parameters"]["wall_support_height_m"])
    half = float(model["parameters"]["depth_m"]) / 2
    center = half
    return ridge - abs(y - center) * (ridge - support) / half


def side_svg(model: dict[str, Any], east: bool) -> str:
    nodes = node_map(model)
    p = model["parameters"]
    view_id = "EV05" if east else "EV06"
    wall = nodes["W02" if east else "W01"]
    scale = 66.0
    X = (lambda y: 170 + (y + .6) * scale) if east else (lambda y: 170 + (7.8 - y) * scale)
    Z = lambda z: 500 - z * scale
    body: list[str] = []
    body.append(svg_text(35, 29, "完整山墙侧立面 · 不展开梁架或榫卯", 13, "drawing-note", "start"))
    body.append(svg_text(35, 50, "视向：西（从东向西）" if east else "视向：东（从西向东）", 12, "drawing-note", "start"))

    roof = nodes["RF01"]
    rg = roof["geometry"]
    roof_points = [
        (X(rg["y"][0]), Z(rg["eaveZ"])),
        (X(rg["ridgeY"]), Z(rg["ridgeZ"])),
        (X(rg["y"][1]), Z(rg["eaveZ"])),
    ]
    body.append(f'<g {node_attrs(roof, "roof-group")}>{polyline(roof_points, "roof-plane-outline")}</g>')

    # Side wall is a gable whose top follows the same roof_z function.
    wall_points = [
        (X(0), Z(0)),
        (X(0), Z(roof_z(model, 0))),
        (X(3.6), Z(roof_z(model, 3.6))),
        (X(7.2), Z(roof_z(model, 7.2))),
        (X(7.2), Z(0)),
    ]
    body.append(f'<g {node_attrs(wall, "wall-group")}>{poly(wall_points, "gable-wall")}</g>')
    # Re-outline the overhang beyond both gable walls; this is the actual 0.6 m projection.
    body.append(f'<g {node_attrs(roof, "roof-group")}>')
    body.append(line(X(-.6), Z(roof_z(model, -.6)), X(0), Z(roof_z(model, 0)), "roof-edge"))
    body.append(line(X(7.2), Z(roof_z(model, 7.2)), X(7.8), Z(roof_z(model, 7.8)), "roof-edge"))
    body.append(line(X(0), Z(roof_z(model, 0)), X(3.6), Z(roof_z(model, 3.6)), "gable-roof-line"))
    body.append(line(X(3.6), Z(roof_z(model, 3.6)), X(7.2), Z(roof_z(model, 7.2)), "gable-roof-line"))
    body.append("</g>")

    # Porch columns collapse to the same Y-Z projection; show a single representative hit target.
    column = nodes["C04" if east else "C01"]
    colw = column["properties"]["diameterM"]
    col_left, col_right = sorted((X(-colw / 2), X(colw / 2)))
    body.append(f'<g {node_attrs(column, "column-group")}>{rect(col_left, Z(3.6), col_right - col_left, 3.6 * scale, "column-fill")}</g>')
    body.append(svg_text(830, 442, "前廊柱列投影", 12, "small-label", "start"))
    body.append(svg_text(830, 462, "C01–C04位置重合", 12, "small-label", "start"))
    body.append(line(X(-.6), Z(0), X(7.8), Z(0), "ground-line"))
    add_dimension_h(body, X(0), X(7.2), 548, "主屋轴网进深 7.2 m", view_id)
    body.append(line(X(0), Z(0), X(0), 540, "dimension-extension"))
    body.append(line(X(7.2), Z(0), X(7.2), 540, "dimension-extension"))

    # Height callouts explicitly separate the support line and outer roof eaves.
    body.append(line(790, Z(0), 790, Z(5.6), "dimension-line", f'marker-start="url(#{view_id}-arrow)" marker-end="url(#{view_id}-arrow)"'))
    for z, label_text, dy in [
        (5.6, "屋脊 5.6 m", 0),
        (3.6, "墙体支承线 3.6 m", 0),
        (roof_z(model, -.6), "外挑檐口 3.2667 m", 18),
    ]:
        body.append(svg_text(805, Z(z) + dy, label_text, 13, "dimension-text", "start"))
    body.append(svg_text(190, 94, "南" if east else "北", 13, "small-label"))
    body.append(svg_text(715, 94, "北" if east else "南", 13, "small-label"))
    body.append(svg_text(35, 578, "东西外墙墙顶随坡顶；屋面外挑 0.6 m；无结构体系推断", 12, "drawing-note", "start"))
    return make_svg(view_id, 960, 600, "".join(body))


def section_svg(model: dict[str, Any]) -> str:
    nodes = node_map(model)
    p = model["parameters"]
    view_id = "EV07"
    # Section x=4.8, so its horizontal coordinate is northing Y.
    scale = 54.0
    X = lambda y: 160 + (y + 5.2) * scale
    Z = lambda z: 500 - z * scale
    body: list[str] = []
    body.append(svg_text(35, 29, "A—A剖面 · X=4.8 m · 南在左、北在右", 13, "drawing-note", "start"))
    body.append(svg_text(35, 51, "切过堂屋、前廊与北墙；梁架省略", 12, "drawing-note", "start"))

    # Section space bands allow selection without suggesting 3D closure beyond the model.
    s04 = nodes["S04"]
    body.append(rect(X(0), Z(2.9), (1.5 - 0) * scale, 2.9 * scale, "space-veranda", node_attrs(s04, "space-region")))
    s01 = nodes["S01"]
    body.append(rect(X(1.5), Z(2.9), (7.08 - 1.5) * scale, 2.9 * scale, "space-center", node_attrs(s01, "space-region")))
    body.append(svg_text((X(0) + X(1.5)) / 2, Z(1.55), "前廊 S04", 13, "room-label"))
    body.append(svg_text((X(1.5) + X(7.08)) / 2, Z(1.55), "堂屋 S01", 15, "room-label"))

    # Roof section generated from roof node extents, ridge, and contract formula.
    roof = nodes["RF01"]
    rg = roof["geometry"]
    body.append(f'<g {node_attrs(roof, "roof-group")}>')
    body.append(line(X(-.6), Z(rg["eaveZ"]), X(3.6), Z(rg["ridgeZ"]), "gable-roof-line"))
    body.append(line(X(3.6), Z(rg["ridgeZ"]), X(7.8), Z(rg["eaveZ"]), "gable-roof-line"))
    body.append("</g>")

    # North wall W03 has a 1 m high window where the cut plane crosses I09.
    north_wall = nodes["W03"]
    north_y = p["depth_m"]
    thickness = north_wall["geometry"]["thickness"]
    nw = nodes["I09"]
    sill, head = nw["properties"]["sillZ"], nw["properties"]["headZ"]
    body.append(f'<g {node_attrs(north_wall, "wall-group")}>')
    body.append(rect(X(north_y - thickness / 2), Z(sill), thickness * scale, sill * scale, "wall-fill-piece"))
    body.append(rect(X(north_y - thickness / 2), Z(3.6), thickness * scale, (3.6 - head) * scale, "wall-fill-piece"))
    body.append(rect(X(north_y - thickness / 2), Z(3.6), thickness * scale, 3.6 * scale, "wall-outline-only"))
    body.append("</g>")
    body.append(f'<g {node_attrs(nw, "interface-mark")}>{rect(X(north_y - thickness / 2), Z(head), thickness * scale, (head - sill) * scale, "window-elevation")}</g>')

    # A vertical green guide marks the open I01 boundary in the section cut; it is not a wall.
    i01 = nodes["I01"]
    body.append(f'<g {node_attrs(i01, "interface-mark")}>{line(X(1.5), Z(0), X(1.5), Z(i01["properties"]["headZ"]), "open-mark")}</g>')
    body.append(svg_text(X(1.5) + 8, Z(3.05), "I01 开放分界（无墙）", 12, "interface-label", "start"))

    # Yard gate is beyond the main section but the x=4.8 cut passes through its opening.
    i05 = nodes["I05"]
    body.append(f'<g {node_attrs(i05, "interface-mark")}>{line(X(-4.8), Z(0), X(-4.8), Z(1.6), "open-mark")}</g>')
    body.append(svg_text(X(-4.8), Z(1.6) - 10, "I05 院门：切面过门洞", 11, "interface-label"))

    # Ground lines, orientation, and dimensions.
    body.append(line(X(-4.8), Z(0), X(7.8), Z(0), "ground-line"))
    body.append(svg_text(X(-2.4), Z(0) - 11, "前院（深 4.8 m）", 12, "small-label"))
    body.append(svg_text(X(.75), Z(0) - 11, "前廊 1.5 m", 12, "small-label"))
    body.append(svg_text(X(4.35), Z(0) - 11, "主屋轴网进深 7.2 m", 12, "small-label"))
    add_dimension_h(body, X(-4.8), X(0), 553, "前院深 4.8 m", view_id, 12)
    add_dimension_h(body, X(0), X(1.5), 553, "1.5 m", view_id, 12)
    add_dimension_h(body, X(0), X(7.2), 580, "主屋轴网进深 7.2 m", view_id, 12)
    body.append(line(X(0), Z(0), X(0), 546, "dimension-extension"))
    body.append(line(X(1.5), Z(0), X(1.5), 546, "dimension-extension"))
    body.append(line(X(7.2), Z(0), X(7.2), 546, "dimension-extension"))

    # Heights: eave, support line, and ridge are independent markers.
    body.append(line(870, Z(0), 870, Z(5.6), "dimension-line", f'marker-start="url(#{view_id}-arrow)" marker-end="url(#{view_id}-arrow)"'))
    body.append(svg_text(882, Z(5.6), "屋脊 5.6 m", 12, "dimension-text", "start"))
    body.append(svg_text(882, Z(3.6), "支承线 3.6 m", 12, "dimension-text", "start"))
    body.append(svg_text(882, Z(3.2666666667) + 17, "外挑檐口 3.2667 m", 12, "dimension-text", "start"))
    body.append(svg_text(35, 620, "北墙 W03 在剖切处含 I09 窗洞；前廊柱列不在 X=4.8 切面内；空间色块仅供分区识别，不表示顶棚或净高", 12, "drawing-note", "start"))
    return make_svg(view_id, 1000, 640, "".join(body))


def roof_plan_svg(model: dict[str, Any]) -> str:
    nodes = node_map(model)
    p = model["parameters"]
    roof = nodes["RF01"]
    rg = roof["geometry"]
    s = 55.0
    X = lambda x: 180 + (x + 1) * s
    Y = lambda y: 520 - (y + 1) * s
    body: list[str] = []
    body.append(svg_text(35, 29, "主屋屋顶投影 · 不含梁架分解", 13, "drawing-note", "start"))
    roof_surfaces = [
        node for node in model["nodes"]
        if "RoofSurface" in node.get("labels", []) or node.get("class") == "RoofSurface"
    ]
    if roof_surfaces:
        for surface in roof_surfaces:
            vertices = surface.get("geometry", {}).get("vertices", [])
            points = []
            for vertex in vertices:
                if isinstance(vertex, dict):
                    vx, vy = vertex.get("x", vertex.get("X")), vertex.get("y", vertex.get("Y"))
                elif isinstance(vertex, (list, tuple)) and len(vertex) >= 2:
                    vx, vy = vertex[0], vertex[1]
                else:
                    continue
                if isinstance(vx, (int, float)) and isinstance(vy, (int, float)):
                    points.append((float(vx), float(vy)))
            if len(points) < 3:
                continue
            center_x = sum(point[0] for point in points) / len(points)
            center_y = sum(point[1] for point in points) / len(points)
            side = "south" if center_y < float(rg["ridgeY"]) else "north"
            body.append(f'<g {node_attrs(surface, "roof-surface-group")}>')
            body.append(poly([(X(x), Y(y)) for x, y in points], f"roof-surface-fill roof-surface-{side}"))
            body.append(svg_text(X(center_x), Y(center_y), surface.get("name", surface["id"]), 13, "roof-surface-label"))
            body.append("</g>")
    else:
        # Compatibility view for the original model before explicit slope surfaces exist.
        body.append(f'<g {node_attrs(roof, "roof-group")}>{rect(X(rg["x"][0]), Y(rg["y"][1]), (rg["x"][1] - rg["x"][0]) * s, (rg["y"][1] - rg["y"][0]) * s, "roof-plan-fill")}</g>')
        body.append(svg_text(X(4.8), Y(1.8), "屋面系统投影", 18, "room-label"))
    # RF01 stays independently selectable as the whole roof system by its outline and ridge.
    roof_frame_attrs = node_attrs(roof, "roof-system")
    body.append(rect(X(rg["x"][0]), Y(rg["y"][1]), (rg["x"][1] - rg["x"][0]) * s, (rg["y"][1] - rg["y"][0]) * s, "roof-system-outline", roof_frame_attrs))
    body.append(f'<g {node_attrs(roof, "roof-system-group")}>{line(X(rg["x"][0]), Y(rg["ridgeY"]), X(rg["x"][1]), Y(rg["ridgeY"]), "roof-ridge")}</g>')
    # Draw the comparison frame above the roof fill so the 0.6 m offset remains visible.
    body.append(f'<g {node_attrs(nodes["B01"], "outline-hit")}>{rect(X(0), Y(p["depth_m"]), p["width_m"] * s, p["depth_m"] * s, "building-frame")}</g>')
    body.append(svg_text(X(4.8), Y(3.6) - 13, "屋脊线 · X向", 14, "roof-label"))
    # Main dimensions and overhang dimensions.
    add_dimension_h(body, X(-.6), X(10.2), 606, "屋面投影宽 10.8 m = 9.6 + 两侧各 0.6", "EV08", 13)
    body.append(line(X(-.6), Y(7.8), X(-.6), 598, "dimension-extension"))
    body.append(line(X(10.2), Y(7.8), X(10.2), 598, "dimension-extension"))
    body.append(line(160, Y(7.8), 160, Y(-.6), "dimension-line", 'marker-start="url(#EV08-arrow)" marker-end="url(#EV08-arrow)"'))
    body.append(svg_text(145, (Y(7.8)+Y(-.6))/2, "进深 8.4 m", 13, "dimension-text", "end"))
    body.append(svg_text(815, 112, "轴网 9.6 × 7.2 m", 14, "dimension-text", "start"))
    body.append(svg_text(815, 137, "檐口挑出 0.6 m", 14, "dimension-text", "start"))
    body.append(svg_text(815, 162, "屋脊沿 X 方向", 14, "dimension-text", "start"))
    body.append(svg_text(815, 207, "坡度按A—A剖面", 13, "small-label", "start"))
    body.append(svg_text(815, 228, "屋脊与支承线计算", 13, "small-label", "start"))
    body.append(line(944, 480, 944, 430, "north-arrow", 'marker-end="url(#EV08-arrow)"'))
    body.append(svg_text(944, 415, "北 / +Y", 12, "north-label"))
    body.append(line(820, 284, 860, 284, "roof-ridge"))
    body.append(svg_text(870, 289, "屋脊", 12, "small-label", "start"))
    body.append('<rect x="820" y="306" width="40" height="18" class="roof-surface-south"/>')
    body.append(svg_text(870, 320, "南坡面", 12, "small-label", "start"))
    body.append('<rect x="820" y="338" width="40" height="18" class="roof-surface-north"/>')
    body.append(svg_text(870, 352, "北坡面", 12, "small-label", "start"))
    body.append('<rect x="820" y="370" width="40" height="18" class="roof-outline-legend"/>')
    body.append(svg_text(870, 384, "RF01屋顶系统边界", 12, "small-label", "start"))
    body.append('<rect x="820" y="402" width="40" height="18" class="building-legend"/>')
    body.append(svg_text(870, 416, "主屋轴网范围", 12, "small-label", "start"))
    body.append(svg_text(35, 692, "屋面由模型几何边界生成；此图只表示投影，不是瓦件排布图", 12, "drawing-note", "start"))
    return make_svg("EV08", 1020, 710, "".join(body))


def access_network_svg(model: dict[str, Any]) -> str:
    nodes = node_map(model)
    space_order = ["S02", "S01", "S03", "S04", "S05", "S06"]
    positions = {
        "S02": (175, 135), "S01": (480, 135), "S03": (785, 135),
        "S04": (480, 300), "S05": (480, 440), "S06": (480, 565),
    }
    body: list[str] = []
    access = [rel for rel in model["relationships"] if rel["type"] == "DIRECT_ACCESS_TO"]
    body.append(svg_text(35, 27, f"基准情境：正常步行 · {len(access)}组双向直接通行", 14, "drawing-note", "start"))
    for rel in access:
        a, b = rel["source"], rel["target"]
        x1, y1 = positions[a]
        x2, y2 = positions[b]
        # Stop at rounded node edges; use arrows at both ends to show bidirectionality.
        if y1 == y2:
            dx = 94 if x2 > x1 else -94
            start, end = (x1 + dx, y1), (x2 - dx, y2)
        elif x1 == x2:
            dy = 42 if y2 > y1 else -42
            start, end = (x1, y1 + dy), (x2, y2 - dy)
        else:
            start, end = (x1, y1), (x2, y2)
        body.append(line(start[0], start[1], end[0], end[1], "network-edge", f'marker-start="url(#EVNET-arrow)" marker-end="url(#EVNET-arrow)"'))
        mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
        via = rel.get("properties", {}).get("via", "")
        iface = nodes.get(via, {})
        kind = iface.get("properties", {}).get("kind", "")
        kind_zh = {"open_boundary": "开放界面", "door_opening": "门洞", "gate_opening": "院门"}.get(kind, "界面")
        label_y = my - 10 if y1 == y2 else my
        body.append(f'<rect x="{nfmt(mx-37,1)}" y="{nfmt(label_y-15,1)}" width="74" height="24" rx="8" class="network-label-bg"/>')
        body.append(svg_text(mx, label_y + 2, f"{via} · {kind_zh}", 11, "network-label"))
    for node_id in space_order:
        node = nodes[node_id]
        x, y = positions[node_id]
        xx, yy = x - 88, y - 38
        body.append(f'<g {node_attrs(node, "network-node")}>')
        body.append(rect(xx, yy, 176, 76, "network-box"))
        body.append(svg_text(x, y - 5, node["name"], 15, "network-node-title"))
        use = node["properties"].get("use", "")
        body.append(svg_text(x, y + 18, use, 11, "network-node-subtitle"))
        body.append("</g>")
    body.append(svg_text(30, 627, "箭头仅表示模型中的成对通行关系；界面是通行依据，不代表实地通行已验证。", 12, "drawing-note", "start"))
    return make_svg("EVNET", 960, 650, "".join(body))


def human_value(key: str, value: Any) -> str:
    if key == "recordStatus":
        return RELATION_STATUS_ZH.get(str(value), str(value))
    if key == "enclosure":
        return {"indoor": "室内", "semi_open": "半开敞", "open": "露天", "external_reference": "外部参照"}.get(str(value), str(value))
    if key == "kind":
        return {"open_boundary": "开放分界", "door_opening": "门洞", "window_opening": "窗洞", "gate_opening": "院门洞"}.get(str(value), str(value))
    if key == "passage":
        return {"yes": "是（按合成基准情境）", "no": "否（窗不作步行通道）"}.get(str(value), str(value))
    if key == "physicalSeparation":
        return {"none": "无实体分隔", "opening_in_wall": "墙体开口"}.get(str(value), str(value))
    if key == "intersectionKind":
        return {
            "interior_overlap": "包络内部相交（几何关系）",
            "boundary_contact": "包络边界接触（几何关系）",
        }.get(str(value), str(value))
    if key == "boundaryRole":
        return {"ridge": "屋脊", "valley": "屋谷", "unclassified": "未分类"}.get(str(value), str(value))
    if key in {"atSource", "atTarget"}:
        return {"ATSTART": "轴线起点", "ATEND": "轴线终点", "ATPATH": "轴线上"}.get(str(value), str(value))
    if key == "atWall":
        return {"ATSTART": "墙轴起点", "ATEND": "墙轴终点", "ATPATH": "墙轴上"}.get(str(value), str(value))
    if key == "representation":
        return {"ideal_zero_thickness_roof_patch": "理想化零厚度屋面片"}.get(str(value), str(value))
    if key == "isRealWorldEvidence":
        return "是" if value else "否"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if key == "slopeAzimuthDeg":
            bearing = float(value) % 360
            direction = "北" if abs(bearing) < .01 else "南" if abs(bearing - 180) < .01 else "东" if abs(bearing - 90) < .01 else "西" if abs(bearing - 270) < .01 else ""
            return f"{nfmt(bearing,2)}°" + (f"（{direction}）" if direction else "")
        if key.endswith("M2") or key == "areaM2":
            return f"{nfmt(value, 3)} m²"
        if key.endswith("M") or key in ("widthM", "lengthM", "thicknessM", "diameterM", "heightM"):
            return f"{nfmt(value, 4)} m"
        if key.endswith("Deg") or key.endswith("Z") or key in ("floorZ", "sillZ", "headZ"):
            return f"{nfmt(value, 4)}{ '°' if key.endswith('Deg') else ' m'}"
        return nfmt(value, 4)
    if isinstance(value, list):
        if key == "commonZ" and len(value) == 2 and all(isinstance(item, (int, float)) for item in value):
            return f"z={nfmt(value[0],4)}–{nfmt(value[1],4)} m"
        if value and all(isinstance(item, (int, float)) for item in value):
            axes = ("X", "Y", "Z")[:len(value)]
            return "（" + "，".join(f"{axis}={nfmt(item,4)} m" for axis, item in zip(axes, value)) + "）"
        return "；".join(human_value(key, item) if isinstance(item, list) else str(item) for item in value)
    return str(value)


def relation_property_value(key: str, value: Any) -> str:
    if key in {"atSource", "atTarget", "junctionXY", "boundaryStart", "boundaryEnd"}:
        if isinstance(value, dict):
            axes = [(axis, value.get(axis, value.get(axis.lower()))) for axis in ("X", "Y", "Z")]
            coordinates = [f"{axis}={nfmt(number,4)} m" for axis, number in axes if isinstance(number, (int, float))]
            if coordinates:
                return "（" + "，".join(coordinates) + "）"
        return human_value(key, value)
    return human_value(key, value)


def build_ui_data(model: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    by_id = node_map(model)
    ui_nodes = []
    for node in model["nodes"]:
        props = []
        is_roof_surface = "RoofSurface" in node.get("labels", []) or node.get("class") == "RoofSurface"
        for key, value in node.get("properties", {}).items():
            label = PROPERTY_ZH.get(key, key)
            if is_roof_surface:
                label = {
                    "areaM2": "坡面面积",
                    "slopeDeg": "坡度角",
                    "slopeAzimuthDeg": "坡向方位角",
                }.get(key, label)
            props.append({"label": label, "value": human_value(key, value)})
        if "Wall" in node.get("labels", []):
            geometry = node.get("geometry", {})
            mode = geometry.get("heightMode", "roof_profile")
            props.append({
                "label": "墙顶模式",
                "value": "按屋面坡顶变化" if mode == "roof_profile" else "恒高",
            })
            profile = geometry.get("topProfile", [])
            if profile:
                if all(abs(float(point[2]) - float(profile[0][2])) < 1e-6 for point in profile):
                    first, last = profile[0], profile[-1]
                    axis = "Y" if abs(float(last[1]) - float(first[1])) > 1e-6 else "X"
                    profile_text = f"沿{axis}方向恒高 {nfmt(first[2],4)} m"
                else:
                    axis = "Y" if len({round(float(point[1]), 6) for point in profile}) > 1 else "X"
                    coord_i = 1 if axis == "Y" else 0
                    profile_text = "；".join(
                        f"{axis.lower()}={nfmt(point[coord_i],3)} m → z={nfmt(point[2],4)} m"
                        for point in profile
                    )
                props.append({"label": "墙顶控制点", "value": profile_text})
        ui_nodes.append({
            "id": node["id"],
            "name": node["name"],
            "class": node["class"],
            "classZh": CLASS_ZH.get(node["class"], node["class"]),
            "labels": node.get("labels", []),
            "labelsZh": [LABEL_ZH.get(label, label) for label in node.get("labels", [])],
            "materials": material_labels(node),
            "materialsZh": [MATERIAL_ZH[label] for label in material_labels(node)],
            "evidence": node.get("evidence", [node["id"]] if node["class"] == "Evidence" else []),
            "properties": props,
        })
    rel_vocab = []
    vocab_map = {item["type"]: item for item in model["relationVocabulary"]}
    relation_counts: dict[str, int] = {}
    for rel in model["relationships"]:
        relation_counts[rel["type"]] = relation_counts.get(rel["type"], 0) + 1
    for item in model["relationVocabulary"]:
        vocab_map[item["type"]]["zh"] = RELATION_TYPE_ZH.get(item["type"], item["zh"])
        rel_vocab.append({
            "type": item["type"],
            "zh": item.get("zh") or RELATION_TYPE_ZH.get(item["type"], item["type"]),
            "definition": item["definition"],
            "direction": item["direction"],
            "minimum": item["minimum"],
            "example": item["example"],
            "count": relation_counts.get(item["type"], 0),
        })
    for rel_type, count in relation_counts.items():
        if rel_type in vocab_map:
            continue
        fallback = {
            "type": rel_type,
            "zh": RELATION_TYPE_ZH.get(rel_type, rel_type),
            "definition": "模型记录了该关系，但当前关系词表没有提供单独定义。",
            "direction": "按记录中的源对象→目标对象",
            "minimum": "关系端点与模型提供的几何属性",
            "example": "见本类型关系记录",
            "count": count,
        }
        vocab_map[rel_type] = fallback
        rel_vocab.append(fallback)
    ui_rels = []
    for rel in model["relationships"]:
        vocab = vocab_map.get(rel["type"], {"zh": RELATION_TYPE_ZH.get(rel["type"], rel["type"])})
        prop_parts = []
        for key, value in rel.get("properties", {}).items():
            prop_key = {
                "via": "经界面", "bidirectional": "双向", "context": "情境",
                "meaning": "含义", "extent": "适用范围", "role": "角色",
                "scope": "证据范围", "dependency": "证据依赖", "distanceM": "中心距",
                "direction": "方向", "azimuthDeg": "方位角", "axisAngleDeg": "轴夹角",
                "distanceBasis": "距离口径", "directionBasis": "方位口径", "angleBasis": "夹角口径",
                "atSource": "源端部位", "atTarget": "目标端部位", "junctionXY": "交会点坐标",
                "ruleId": "几何规则", "intersectionKind": "包络相交类型", "atWall": "墙轴部位",
                "commonZ": "共同标高范围", "boundaryStart": "共用边界起点", "boundaryEnd": "共用边界终点",
                "boundaryRole": "共用边界类别",
            }.get(key, key)
            prop_parts.append(f"{prop_key}：{relation_property_value(key, value)}")
        ui_rels.append({
            "id": rel.get("id", ""),
            "type": rel["type"],
            "zh": vocab["zh"],
            "source": rel["source"],
            "target": rel["target"],
            "sourceName": by_id.get(rel["source"], {}).get("name", rel["source"]),
            "targetName": by_id.get(rel["target"], {}).get("name", rel["target"]),
            "status": RELATION_STATUS_ZH.get(rel.get("status", ""), rel.get("status", "")),
            "evidence": rel.get("evidence", []),
            "properties": "；".join(prop_parts),
        })
    analysis = []
    for row in model.get("analysisResults", []):
        value = row.get("value")
        if isinstance(value, dict):
            value_text = "；".join(f"{ANALYSIS_VALUE_LABEL_ZH.get(key, PROPERTY_ZH.get(key, key))}：{human_value(key, val)}" for key, val in value.items())
        elif isinstance(value, (int, float)):
            value_text = f"{nfmt(value, 4)} {row.get('unit', '')}".strip()
        else:
            value_text = str(value)
        analysis.append({
            "id": row["id"], "kind": row["kind"], "name": row["name"],
            "value": value_text, "formula": row.get("formula", "按合成几何或关系规则计算"),
            "inputs": row.get("inputs", []),
            "status": RELATION_STATUS_ZH.get(row.get("status", ""), row.get("status", "")),
            "kindZh": ANALYSIS_KIND_ZH.get(row.get("kind", ""), row.get("kind", "")),
        })
    answers = []
    for row in result.get("answers", []):
        structured = row.get("structuredValue", {})
        value_text = ""
        if row["id"] == "P1" and structured:
            value_text = (
                f"升高：{nfmt(structured.get('rise_m', 0),3)} m；"
                f"半跨：{nfmt(structured.get('run_m', 0),3)} m；"
                f"坡度：{nfmt(structured.get('slope_degrees', 0),4)}°"
            )
        elif row["id"] == "P2" and structured:
            value_text = (
                f"{structured.get('from','')} 与 {structured.get('to','')} 经 {structured.get('interface','')} "
                f"（{structured.get('wall','')} {structured.get('interface_location','')}）直接通行；"
                f"{structured.get('scenario','')}；方向：{structured.get('direction','')}"
            )
        elif row["id"] == "P3" and structured:
            labels = "、".join(MATERIAL_ZH.get(label, label) for label in structured.get("labels", []))
            mapping = structured.get("component_mapping", {})
            value_text = f"补充材料标签：{labels}；" + "；".join(
                f"{part}：{MATERIAL_ZH.get(label, label)}" for part, label in mapping.items()
            )
        answers.append({
            "id": row["id"], "status": RELATION_STATUS_ZH.get(row.get("status", ""), row.get("status", "")),
            "statusCode": row.get("status", ""), "answer": row.get("answer", ""),
            "evidence": row.get("evidence", []),
            "reasoning": row.get("reasoning_summary", ""),
            "verification": row.get("verification_needed", ""),
            "valueText": value_text,
        })
    return {
        "nodes": ui_nodes,
        "relationships": ui_rels,
        "relationVocabulary": rel_vocab,
        "analysis": analysis,
        "answers": answers,
        "materials": [{"key": k, "name": v} for k, v in MATERIAL_ZH.items()],
        "parameters": model["parameters"],
        "modelBoundary": model.get("modelBoundary", {}),
        "drawingContract": model.get("drawingContract", {}),
        "caseTitle": model.get("meta", {}).get("title", "V01 合成民居案例"),
        "created": model.get("meta", {}).get("created", ""),
    }


def render_node_options(nodes: list[dict[str, Any]]) -> str:
    options = []
    for node in nodes:
        selected = " selected" if node["id"] == "S01" else ""
        options.append(f'<option value="{esc(node["id"])}"{selected}>{esc(node["id"])} · {esc(node["name"])}（{esc(node["classZh"])}）</option>')
    return "".join(options)


def render_svg_views(model: dict[str, Any]) -> str:
    views = [
        ("EV02", "平面", plan_svg(model)),
        ("EV03", "南立面", facade_svg(model, "south")),
        ("EV04", "北立面", facade_svg(model, "north")),
        ("EV05", "东立面", side_svg(model, True)),
        ("EV06", "西立面", side_svg(model, False)),
        ("EV07", "A—A剖面", section_svg(model)),
        ("EV08", "屋顶投影", roof_plan_svg(model)),
    ]
    parts = []
    for idx, (view_id, name, svg) in enumerate(views):
        hidden = "" if idx == 0 else " hidden"
        parts.append(f'<section class="diagram-panel" data-drawing="{view_id}"{hidden}>{view_caption(view_id, name, "模型几何生成 · 单位 m")}{svg}</section>')
    return "".join(parts)


def render_network_svg(model: dict[str, Any]) -> str:
    return access_network_svg(model)


def page_html(model: dict[str, Any], result: dict[str, Any]) -> str:
    data = build_ui_data(model, result)
    svg_views = render_svg_views(model)
    network_svg = render_network_svg(model)
    node_options = render_node_options(data["nodes"])
    data_js = js_json(data)
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>V01 虚拟民居单体试验 · 案例浏览</title>
<style>
:root {{ color-scheme: light; --ink:#203b32; --muted:#64736c; --line:#d9ded8; --paper:#fbfaf6; --card:#fffefa; --green:#527d69; --green-pale:#e7efe9; --sand:#efe9dc; --blue:#dce8ee; --rust:#a96043; --violet:#80668d; }}
* {{ box-sizing:border-box; }}
html {{ background:#f3f2ec; }}
body {{ margin:0; color:#25372f; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif; line-height:1.55; }}
button,select {{ font:inherit; }}
.shell {{ max-width:1440px; margin:0 auto; padding:20px clamp(14px,3vw,38px) 38px; }}
.topline {{ display:flex; justify-content:space-between; align-items:flex-start; gap:18px; }}
h1 {{ margin:0; font-size:clamp(24px,3vw,34px); letter-spacing:.01em; color:var(--ink); }}
.subtitle {{ margin:4px 0 0; color:var(--muted); font-size:14px; }}
.status-pill {{ flex:none; margin-top:5px; padding:6px 12px; border:1px solid #b9cec0; border-radius:999px; color:#315f47; background:#edf4ee; font-size:13px; font-weight:700; }}
.boundary-banner {{ margin:18px 0 16px; padding:11px 14px; border-left:4px solid #b97a52; border-radius:8px; background:#f6eee5; color:#63432f; font-size:14px; }}
.tabs {{ display:flex; gap:8px; margin:16px 0 18px; border-bottom:1px solid var(--line); }}
.tab {{ appearance:none; border:0; border-bottom:3px solid transparent; padding:11px 17px 10px; background:transparent; color:#66756d; cursor:pointer; font-weight:700; }}
.tab[aria-selected="true"] {{ color:var(--ink); border-color:var(--green); }}
.pane[hidden] {{ display:none !important; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; box-shadow:0 4px 16px rgba(39,57,47,.045); }}
.drawing-controls {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px; padding:13px 15px; border-bottom:1px solid var(--line); }}
.control-label {{ color:var(--muted); font-size:13px; font-weight:700; margin-right:4px; }}
.view-button {{ border:1px solid #d7ddd7; border-radius:8px; padding:7px 11px; background:#fff; color:#42534a; cursor:pointer; }}
.view-button[aria-pressed="true"] {{ color:#fff; border-color:var(--green); background:var(--green); }}
.drawing-grid {{ display:grid; grid-template-columns:minmax(0,1fr) 300px; gap:16px; align-items:start; }}
.drawing-main {{ min-width:0; overflow:hidden; }}
.diagram-panel {{ padding:10px 12px 8px; }}
.diagram-panel[hidden] {{ display:none; }}
.view-heading {{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px 18px; margin:2px 4px 6px; color:var(--muted); font-size:12px; }}
.view-heading > div {{ display:flex; align-items:center; gap:9px; }}
.view-heading strong {{ color:var(--ink); font-size:17px; }}
.drawing-id {{ display:inline-flex; border-radius:6px; padding:2px 6px; background:#edf1ec; color:#557164; font-size:11px; font-weight:800; letter-spacing:.04em; }}
.drawing-svg {{ display:block; width:100%; height:auto; border-radius:8px; background:var(--paper); }}
.inspector {{ position:sticky; top:12px; padding:15px; }}
.inspector h2,.subcard h2 {{ margin:0 0 11px; font-size:18px; color:var(--ink); }}
.field-label {{ display:block; margin:10px 0 5px; color:var(--muted); font-size:12px; font-weight:700; }}
select {{ width:100%; min-height:40px; border:1px solid #cbd4cd; border-radius:8px; padding:7px 9px; background:#fff; color:#243b31; }}
.object-title {{ margin:15px 0 8px; font-size:17px; font-weight:800; color:var(--ink); }}
.object-id {{ margin-right:5px; color:#73877c; font-size:12px; letter-spacing:.04em; }}
.chip-row {{ display:flex; flex-wrap:wrap; gap:6px; margin:6px 0 11px; }}
.chip {{ display:inline-flex; align-items:center; border-radius:999px; padding:3px 8px; background:#edf1ec; color:#3d5d4d; font-size:12px; }}
.chip.material {{ background:#f2ead9; color:#705a2f; }}
.props {{ display:grid; grid-template-columns:minmax(90px,.8fr) 1.4fr; gap:5px 9px; margin:12px 0 0; font-size:12px; }}
.props dt {{ color:#728078; }} .props dd {{ margin:0; color:#2d4037; overflow-wrap:anywhere; }}
.evidence-row {{ margin-top:14px; padding-top:11px; border-top:1px solid var(--line); }}
.evidence-row strong {{ display:block; margin-bottom:6px; color:#64736c; font-size:12px; }}
.evidence-chip {{ border:0; cursor:pointer; }}
.evidence-chip:hover {{ background:#d9e7dd; }}
.legend-row {{ display:flex; flex-wrap:wrap; gap:8px 14px; padding:11px 16px 13px; color:#5d6c64; font-size:12px; }}
.legend-item {{ display:inline-flex; gap:6px; align-items:center; }}
.swatch {{ width:18px; height:12px; border:1px solid #b1bcb3; border-radius:3px; }}
.material-card {{ margin-top:15px; padding:15px; }}
.material-head {{ display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:10px; }}
.material-head h2 {{ margin:0; color:var(--ink); font-size:18px; }}
.material-head p {{ margin:3px 0 0; color:var(--muted); font-size:12px; }}
.material-filter {{ width:auto; min-width:210px; }}
.count-grid {{ display:grid; grid-template-columns:repeat(3,minmax(100px,1fr)); gap:8px; margin:14px 0; }}
.count-cell {{ padding:9px 10px; border:1px solid #e0e4df; border-radius:9px; background:#fafbf8; }}
.count-cell span {{ display:block; color:var(--muted); font-size:12px; }} .count-cell strong {{ display:block; margin-top:2px; color:var(--ink); font-size:21px; }}
.material-list {{ display:flex; flex-wrap:wrap; gap:7px; }}
.material-item {{ border:1px solid #d8e0d9; border-radius:8px; padding:7px 10px; background:#fff; color:#354a3e; cursor:pointer; text-align:left; }}
.material-item:hover {{ border-color:var(--green); background:#f2f7f2; }}
.material-item small {{ display:block; color:#708078; font-size:11px; }}
.help-note {{ margin:13px 0 0; color:#66756e; font-size:12px; }}
.two-col {{ display:grid; grid-template-columns:minmax(0,1.35fr) minmax(310px,.9fr); gap:16px; align-items:start; }}
.subcard {{ padding:16px; }}
.subcard p {{ margin:4px 0 12px; color:var(--muted); font-size:13px; }}
.network-wrap {{ overflow:auto; }}
.network-svg {{ min-width:620px; width:100%; height:auto; display:block; }}
.relation-tools {{ display:flex; flex-wrap:wrap; gap:10px 14px; align-items:end; margin:12px 0; }}
.relation-tools > label {{ flex:1; min-width:180px; }}
.relation-tools select {{ min-width:185px; }}
.relation-list {{ max-height:440px; overflow:auto; border-top:1px solid var(--line); }}
.relation-row {{ display:grid; grid-template-columns:54px minmax(90px,.8fr) minmax(120px,1.2fr); gap:7px; padding:9px 3px; border-bottom:1px solid #edf0ec; font-size:12px; }}
.relation-direction {{ color:#557464; font-weight:800; }}
.relation-row strong {{ display:block; color:#30483b; }}
.relation-row small {{ color:#748078; }}
.relation-evidence {{ grid-column:2 / 4; color:#748078; }}
.relation-empty {{ padding:15px 5px; color:var(--muted); font-size:13px; }}
.vocab-list {{ display:grid; gap:8px; }}
.vocab-list details {{ border:1px solid #e0e5df; border-radius:9px; background:#fff; }}
.vocab-list summary {{ padding:9px 11px; cursor:pointer; color:#334a3d; font-weight:700; font-size:13px; }}
.vocab-list summary span {{ margin-left:6px; color:#7a877f; font-weight:500; }}
.vocab-body {{ padding:0 11px 11px; color:#5b6b62; font-size:12px; }}
.vocab-body p {{ margin:4px 0; font-size:12px; }}
.analysis-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; margin:14px 0 18px; }}
.analysis-card {{ padding:14px; border:1px solid #dee4de; border-radius:12px; background:#fffefa; }}
.analysis-card h3 {{ margin:0 0 6px; color:var(--ink); font-size:16px; }}
.result-value {{ margin:8px 0; color:#284f3d; font-size:18px; font-weight:800; }}
.formula {{ display:block; margin:8px 0; padding:8px 9px; border-radius:7px; background:#f3f4ef; color:#43534a; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; overflow-wrap:anywhere; }}
.meta-line {{ margin-top:7px; color:#69786f; font-size:12px; }}
.answer-list {{ display:grid; gap:10px; }}
.answer-card {{ padding:13px 14px; border:1px solid #dfe4df; border-radius:11px; background:#fffefa; }}
.answer-top {{ display:flex; justify-content:space-between; align-items:center; gap:8px; }}
.answer-top h3 {{ margin:0; color:var(--ink); font-size:15px; }}
.state {{ padding:3px 8px; border-radius:999px; background:#edf3ec; color:#3f644d; font-size:11px; font-weight:800; }}
.state.unknown {{ background:#f2eee8; color:#795d43; }}
.answer-text {{ margin:8px 0; color:#34473d; }}
.answer-detail {{ margin:4px 0; color:#65736c; font-size:12px; }}
.warning {{ margin:12px 0; padding:12px 14px; border:1px solid #e7d3ba; border-radius:10px; background:#faf2e7; color:#694b31; font-size:13px; }}
.footer {{ display:flex; flex-wrap:wrap; justify-content:space-between; gap:8px; margin-top:22px; padding:14px 2px 0; border-top:1px solid var(--line); color:#758078; font-size:12px; }}
.footer a {{ color:#365c49; font-weight:700; text-decoration:none; }} .footer a:hover {{ text-decoration:underline; }}
/* SVG drawing styles */
.drawing-svg {{ background:#fbfaf6; }}
.svg-paper {{ fill:#fbfaf6; }}
.geo {{ cursor:pointer; }}
.geo:focus-visible {{ outline:3px solid #b27a3e; outline-offset:3px; }}
.geo.is-selected > rect,.geo.is-selected > polygon,.geo.is-selected > polyline,.geo.is-selected > path,.geo.is-selected > circle,rect.geo.is-selected,polygon.geo.is-selected,polyline.geo.is-selected,path.geo.is-selected,circle.geo.is-selected {{ stroke:#a35f35 !important; stroke-width:3 !important; vector-effect:non-scaling-stroke; }}
.wall-fill {{ fill:#d5d0c4; stroke:#7d8178; stroke-width:1.1; }}
.wall-fill-piece {{ fill:#d5d0c4; stroke:none; }} .wall-outline {{ fill:none; stroke:#7d8178; stroke-width:1.3; }} .wall-outline-only {{ fill:none; stroke:#7d8178; stroke-width:1.3; }}
.space-blue {{ fill:#e4ecef; stroke:#d1dcdf; stroke-width:1; }} .space-center {{ fill:#f2eadb; stroke:#dfd5c5; stroke-width:1; }}
.space-veranda {{ fill:#e4eee5; stroke:#cddbcf; stroke-width:1; }} .space-yard {{ fill:#edf0e7; stroke:#d9dfd2; stroke-width:1; }} .space-reference {{ fill:#f2f0e9; stroke:#b9c2b9; stroke-width:1; stroke-dasharray:5 4; }}
.building-frame {{ fill:none; stroke:#829489; stroke-width:1.5; stroke-dasharray:6 5; pointer-events:stroke; }}
.column-fill {{ fill:#6e4937; stroke:#49392e; stroke-width:1.1; }}
.room-label {{ fill:#344b3d; font-weight:800; }} .room-id {{ fill:#728179; }} .small-label {{ fill:#65756c; }}
.door-mark {{ stroke:#aa6344; stroke-width:3; }} .window-mark {{ stroke:#487991; stroke-width:2.4; }} .open-mark {{ stroke:#54846a; stroke-width:2; stroke-dasharray:5 4; }}
.interface-label {{ fill:#557364; font-weight:700; }} .dimension-line {{ stroke:#59736a; stroke-width:1.2; }} .dimension-tick {{ stroke:#59736a; stroke-width:1.2; }}
.dimension-extension {{ stroke:#aeb9b1; stroke-width:1; stroke-dasharray:3 3; }} .dimension-text {{ fill:#485c50; font-weight:600; }} .north-arrow {{ stroke:#355c49; stroke-width:2; }} .north-label,.roof-label {{ fill:#315a45; font-weight:800; }}
.legend-title {{ fill:#365c49; font-weight:800; }} .legend-text {{ fill:#5d6d64; }} .wall-legend {{ fill:#d5d0c4; stroke:#7d8178; }}
.drawing-note {{ fill:#66756d; }} .roof-projection {{ fill:#dfe8e1; fill-opacity:1; stroke:#738a7b; stroke-width:1.4; }} .roof-fill {{ fill:#e4e9e3; stroke:#60796b; stroke-width:1.6; }} .roof-plane-outline {{ fill:none; stroke:#60796b; stroke-width:2; }} .hidden-reference {{ stroke:#8c765b; stroke-width:1.5; stroke-dasharray:5 4; }}
.roof-ridge {{ stroke:#496a59; stroke-width:2; stroke-dasharray:8 3; }} .roof-eave {{ stroke:#668373; stroke-width:2.4; }} .support-guide {{ stroke:#8b755b; stroke-width:1.4; stroke-dasharray:4 4; }}
.wall-group .wall-fill {{ stroke:#777b73; }} .window-elevation {{ fill:#dbe9ef; fill-opacity:1; stroke:#47768b; stroke-width:2; }}
.gable-wall {{ fill:#d8d4ca; stroke:#747b73; stroke-width:1.6; }} .roof-edge,.gable-roof-line {{ stroke:#466957; stroke-width:2; }} .ground-line {{ stroke:#65766d; stroke-width:1.8; }} .leader-line {{ stroke:#87948b; stroke-width:1; stroke-dasharray:3 3; }}
.network-edge {{ stroke:#577a66; stroke-width:2; }} .network-label-bg {{ fill:#fbfaf6; stroke:#d7dfd7; stroke-width:1; }} .network-label {{ fill:#536e5e; font-weight:800; }}
.network-box {{ fill:#f7f8f3; stroke:#aab9ad; stroke-width:1.4; rx:14; }} .network-node-title {{ fill:#2f4c3c; font-weight:800; }} .network-node-subtitle {{ fill:#758078; }}
.roof-plan-fill {{ fill:#e8ede7; stroke:#60796b; stroke-width:2; }} .roof-surface-south {{ fill:#dce9e0; stroke:#678573; stroke-width:1.5; }} .roof-surface-north {{ fill:#e8e5d9; stroke:#8a8062; stroke-width:1.5; }} .roof-surface-label {{ fill:#385b47; font-weight:800; }} .roof-system-outline {{ fill:none; stroke:#526b5b; stroke-width:1.8; pointer-events:stroke; }} .roof-outline-legend {{ fill:none; stroke:#526b5b; stroke-width:2; }} .building-legend {{ fill:none; stroke:#829489; stroke-dasharray:5 3; }}
@media (max-width:1050px) {{ .drawing-grid {{ grid-template-columns:minmax(0,1fr); }} .inspector {{ position:static; }} .two-col {{ grid-template-columns:minmax(0,1fr); }} }}
@media (max-width:700px) {{ .shell {{ padding:13px 12px 26px; }} .topline {{ display:block; }} .status-pill {{ display:inline-flex; margin-top:10px; }} .tabs {{ gap:2px; overflow:auto; }} .tab {{ flex:1; min-width:max-content; padding:10px 9px 9px; font-size:13px; }} .analysis-grid {{ grid-template-columns:1fr; }} .count-grid {{ grid-template-columns:repeat(3,minmax(78px,1fr)); }} .diagram-panel {{ padding:8px 6px; }} .drawing-svg {{ min-width:680px; }} .drawing-main {{ overflow-x:auto; }} }}
</style>
</head>
<body>
<main class="shell">
  <header class="topline">
    <div><h1>V01 虚拟民居单体试验</h1><p class="subtitle">三开间 · 单层 · 前廊 · 前院 · 对象与几何浏览</p></div>
    <span class="status-pill">人工合成 · 非实测案例</span>
  </header>
  <div class="boundary-banner"><strong>范围说明：</strong>本页展示为语义与几何一致性讨论而人工设定的虚拟民居；不代表已验证的江浙典型案例，也不构成畲族建筑发现。图纸均为示意，非施工图。</div>
  <nav class="tabs" role="tablist" aria-label="案例浏览页面">
    <button class="tab" role="tab" id="tab-building" aria-controls="pane-building" aria-selected="true">看建筑</button>
    <button class="tab" role="tab" id="tab-relations" aria-controls="pane-relations" aria-selected="false">看对象与关系</button>
    <button class="tab" role="tab" id="tab-analysis" aria-controls="pane-analysis" aria-selected="false">看计算与推演</button>
  </nav>

  <section class="pane" id="pane-building" role="tabpanel" aria-labelledby="tab-building">
    <div class="drawing-grid">
      <section class="card drawing-main" aria-label="建筑图纸浏览">
        <div class="drawing-controls"><span class="control-label">切换图纸</span>
          <button class="view-button" data-view-button="EV02" aria-pressed="true">平面</button>
          <button class="view-button" data-view-button="EV03" aria-pressed="false">南立面</button>
          <button class="view-button" data-view-button="EV04" aria-pressed="false">北立面</button>
          <button class="view-button" data-view-button="EV05" aria-pressed="false">东立面</button>
          <button class="view-button" data-view-button="EV06" aria-pressed="false">西立面</button>
          <button class="view-button" data-view-button="EV07" aria-pressed="false">A—A剖面</button>
          <button class="view-button" data-view-button="EV08" aria-pressed="false">屋顶投影</button>
        </div>
        {svg_views}
        <div class="legend-row">
          <span class="legend-item"><i class="swatch" style="background:#d5d0c4"></i>墙体</span>
          <span class="legend-item"><i class="swatch" style="background:#6e4937"></i>柱</span>
          <span class="legend-item"><i class="swatch" style="background:#dbe9ef"></i>窗洞</span>
          <span class="legend-item"><i class="swatch" style="background:#e4e9e3"></i>屋面</span>
          <span class="legend-item">棕线：门洞　蓝线：窗洞　绿虚线：无实体开放分界</span>
        </div>
      </section>
      <aside class="card inspector" aria-label="对象信息">
        <h2>对象信息</h2>
        <label class="field-label" for="object-select">选择对象</label>
        <select id="object-select">{node_options}</select>
        <div id="object-detail" aria-live="polite"></div>
      </aside>
    </div>
    <section class="card material-card" aria-label="材料标签筛选">
      <div class="material-head"><div><h2>材料标签筛选</h2><p>统一标签表示对象“含有”该材料，不表示面积、体积或质量比例。</p></div>
        <label><span class="field-label">选择材料标签</span><select class="material-filter" id="material-select"><option value="">查看全部材料标签</option><option value="材质_木">木</option><option value="材质_砖">砖</option><option value="材质_灰泥">灰泥</option><option value="材质_陶瓦">陶瓦</option></select></label>
      </div>
      <div class="count-grid" id="material-counts"></div>
      <div class="material-list" id="material-list"></div>
    </section>
  </section>

  <section class="pane" id="pane-relations" role="tabpanel" aria-labelledby="tab-relations" hidden>
    <div class="warning" style="margin-top:0">轴线交会、包络相交与共享边界表示几何关系。墙柱包络相交不表示实体连接、构造连接或受力关系。</div>
    <div class="two-col">
      <section class="card subcard">
        <h2>空间通行网络</h2>
        <p>只展示空间通行网络。每条边标出对应界面，避免将全部对象挤成一张全图。</p>
        <div class="network-wrap">{network_svg}</div>
        <p class="help-note">几何邻接不自动等于通行；本图只呈现模型中明确记录的 <strong>直接通行</strong> 关系及基准情境。</p>
      </section>
      <section class="card subcard">
        <h2>选中对象的入边与出边</h2>
        <div class="relation-tools">
          <label><span class="field-label">对象</span><select id="relation-object-select">{node_options}</select></label>
          <label><span class="field-label">关系类型</span><select id="relation-type-select"><option value="">全部关系类型</option></select></label>
        </div>
        <div class="relation-list" id="object-relations" aria-live="polite"></div>
      </section>
    </div>
    <section class="card subcard" style="margin-top:16px">
      <h2>关系类型定义</h2>
      <p>优先展示本案例模型词表中的定义；关系列表会包含模型记录的全部关系类型。</p>
      <div class="vocab-list" id="relation-vocabulary"></div>
    </section>
  </section>

  <section class="pane" id="pane-analysis" role="tabpanel" aria-labelledby="tab-analysis" hidden>
    <div class="warning"><strong>推演边界：</strong>计算输入来自人工合成几何与规则，推演结果没有实测验证。未知项保留为未知；墙面饰层不能推出墙芯材料，平面形状也不能推出空间真实用途。</div>
    <section class="card subcard">
      <h2>模型内的计算结果</h2>
      <p>每项均显示公式或规则、输入证据编号和结果状态；图纸与模型由同一套合成输入生成，不是彼此独立的证据。</p>
      <div class="analysis-grid" id="analysis-results"></div>
    </section>
    <section class="card subcard" style="margin-top:16px">
      <h2>遮蔽输入后的推演结果</h2>
      <p>展示验证／推演结果文件中的回答、引用输入、推理摘要与待核查事项。</p>
      <div class="answer-list" id="answer-results"></div>
    </section>
  </section>

  <footer class="footer"><span>离线单文件浏览 · 页面、脚本、SVG、样式与数据均内嵌，无外部资源</span><a href="README.md">查看详解 README.md</a></footer>
</main>
<script>
"use strict";
const DATA = {data_js};
const byId = new Map(DATA.nodes.map(node => [node.id, node]));
let selectedId = "S01";
let materialFilter = "";

function escText(value) {{
  const replacements = {{"&":"&amp;","<":"&lt;",">":"&gt;"}};
  return String(value ?? "").replace(/[&<>"']/g, ch => ch.charCodeAt(0) === 34 ? "&quot;" : ch.charCodeAt(0) === 39 ? "&#39;" : replacements[ch]);
}}
function chooseObject(id, fromRelations = false) {{
  if (!byId.has(id)) return;
  selectedId = id;
  document.getElementById("object-select").value = id;
  document.getElementById("relation-object-select").value = id;
  renderObjectDetail();
  renderObjectRelations();
  document.querySelectorAll(".geo.is-selected").forEach(el => el.classList.remove("is-selected"));
  document.querySelectorAll(`.geo[data-node-id="${{CSS.escape(id)}}"]`).forEach(el => el.classList.add("is-selected"));
  if (fromRelations) document.getElementById("pane-relations").scrollIntoView({{block:"nearest"}});
}}
function renderObjectDetail() {{
  const node = byId.get(selectedId);
  if (!node) return;
  const labels = node.labelsZh.map(label => `<span class="chip">${{escText(label)}}</span>`).join("");
  const materials = node.materialsZh.map(label => `<span class="chip material">材质：${{escText(label)}}</span>`).join("");
  const props = node.properties.map(item => `<dt>${{escText(item.label)}}</dt><dd>${{escText(item.value)}}</dd>`).join("");
  const evidence = node.evidence.length
    ? node.evidence.map(id => `<button class="chip evidence-chip" data-select-node="${{escText(id)}}">${{escText(id)}}</button>`).join("")
    : `<span class="chip">未单列证据编号</span>`;
  document.getElementById("object-detail").innerHTML = `
    <div class="object-title"><span class="object-id">${{escText(node.id)}}</span>${{escText(node.name)}}</div>
    <div class="chip-row">${{labels}}${{materials}}</div>
    ${{props ? `<dl class="props">${{props}}</dl>` : `<p class="help-note">该记录没有展开属性。</p>`}}
    <div class="evidence-row"><strong>证据编号（点击可查看记录）</strong><div class="chip-row">${{evidence}}</div></div>`;
}}
function renderMaterialList() {{
  const candidates = DATA.nodes.filter(node => node.class === "Element" && node.materials.length && (!materialFilter || node.materials.includes(materialFilter)));
  const classes = ["Wall", "Column", "Roof"];
  document.getElementById("material-counts").innerHTML = classes.map(cls => {{
    const count = candidates.filter(node => node.labels.includes(cls)).length;
    const name = {{Wall:"墙体",Column:"柱",Roof:"屋顶系统"}}[cls];
    return `<div class="count-cell"><span>${{name}} · 匹配对象数</span><strong>${{count}}</strong></div>`;
  }}).join("");
  document.getElementById("material-list").innerHTML = candidates.length
    ? candidates.map(node => `<button class="material-item" data-select-node="${{escText(node.id)}}">${{escText(node.id)}} · ${{escText(node.name)}}<small>${{escText(node.classZh)}} · ${{node.materialsZh.map(escText).join("、")}}</small></button>`).join("")
    : `<div class="relation-empty">当前筛选没有匹配构件。</div>`;
}}
function renderObjectRelations() {{
  const type = document.getElementById("relation-type-select").value;
  const relations = DATA.relationships.filter(rel => (rel.source === selectedId || rel.target === selectedId) && (!type || rel.type === type));
  const html = relations.map(rel => {{
    const outgoing = rel.source === selectedId;
    const otherId = outgoing ? rel.target : rel.source;
    const otherName = outgoing ? rel.targetName : rel.sourceName;
    const evidence = rel.evidence?.length ? `依据 ${{rel.evidence.join("、")}}` : "未列证据编号";
    return `<article class="relation-row"><div class="relation-direction">${{outgoing ? "出 →" : "入 ←"}}</div><div><strong>${{escText(rel.zh)}}</strong><small>${{escText(rel.type)}} · ${{escText(rel.status)}}</small></div><div><button class="material-item" data-select-node="${{escText(otherId)}}">${{escText(otherId)}} · ${{escText(otherName)}}</button>${{rel.properties ? `<div class="meta-line">${{escText(rel.properties)}}</div>` : ""}}</div><div class="relation-evidence">${{escText(evidence)}}</div></article>`;
  }}).join("");
  document.getElementById("object-relations").innerHTML = html || `<div class="relation-empty">该对象在当前关系类型下没有入边或出边。</div>`;
}}
function renderVocabulary() {{
  document.getElementById("relation-type-select").innerHTML = `<option value="">全部关系类型</option>` + DATA.relationVocabulary.map(row => `<option value="${{escText(row.type)}}">${{escText(row.zh)}} · ${{row.count}}</option>`).join("");
    document.getElementById("relation-vocabulary").innerHTML = DATA.relationVocabulary.map(row => `
    <details><summary>${{escText(row.zh)}} <span>${{escText(row.type)}} · ${{row.count}}条</span></summary>
    <div class="vocab-body"><p><strong>定义：</strong>${{escText(row.definition)}}</p><p><strong>方向：</strong>${{escText(row.direction)}}</p><p><strong>最少记录：</strong>${{escText(row.minimum)}}</p><p><strong>示例：</strong>${{escText(row.example)}}</p></div></details>`).join("");
}}
function renderAnalysis() {{
  document.getElementById("analysis-results").innerHTML = DATA.analysis.map(row => `
    <article class="analysis-card"><h3>${{escText(row.id)}} · ${{escText(row.name)}}</h3>
      <div class="result-value">${{escText(row.value)}}</div>
      <span class="formula">${{escText(row.formula)}}</span>
      <div class="meta-line">输入证据：${{row.inputs.map(escText).join("、") || "—"}}</div>
      <div class="meta-line">状态：${{escText(row.status)}} · 结果类型：${{escText(row.kindZh)}}</div></article>`).join("");
  document.getElementById("answer-results").innerHTML = DATA.answers.map(row => {{
    const unknown = row.statusCode === "unknown";
    const value = row.valueText ? `<div class="answer-detail">补充计算值：${{escText(row.valueText)}}</div>` : "";
    return `<article class="answer-card"><div class="answer-top"><h3>${{escText(row.id)}} · 推演回答</h3><span class="state ${{unknown ? "unknown" : ""}}">${{escText(row.status)}}</span></div>
      <div class="answer-text">${{escText(row.answer)}}</div>
      <div class="answer-detail">推演引用：${{row.evidence.map(escText).join("、") || "—"}}</div>
      <div class="answer-detail">推理摘要：${{escText(row.reasoning)}}</div>
      <div class="answer-detail">仍需核查：${{escText(row.verification)}}</div>${{value}}</article>`;
  }}).join("");
}}
function activateTab(tabId) {{
  document.querySelectorAll(".tab").forEach(tab => tab.setAttribute("aria-selected", String(tab.id === tabId)));
  document.querySelectorAll(".pane").forEach(pane => pane.hidden = pane.id !== document.getElementById(tabId).getAttribute("aria-controls"));
}}
document.querySelectorAll(".tab").forEach(tab => tab.addEventListener("click", () => activateTab(tab.id)));
document.querySelectorAll("[data-view-button]").forEach(button => button.addEventListener("click", () => {{
  const view = button.dataset.viewButton;
  document.querySelectorAll("[data-view-button]").forEach(item => item.setAttribute("aria-pressed", String(item === button)));
  document.querySelectorAll(".diagram-panel").forEach(panel => panel.hidden = panel.dataset.drawing !== view);
}}));
document.getElementById("object-select").addEventListener("change", event => chooseObject(event.target.value));
document.getElementById("relation-object-select").addEventListener("change", event => chooseObject(event.target.value, true));
document.getElementById("relation-type-select").addEventListener("change", renderObjectRelations);
document.getElementById("material-select").addEventListener("change", event => {{ materialFilter = event.target.value; renderMaterialList(); }});
document.addEventListener("click", event => {{
  const hit = event.target.closest("[data-node-id], [data-select-node]");
  if (!hit) return;
  const id = hit.dataset.nodeId || hit.dataset.selectNode;
  if (id) chooseObject(id);
}});
document.addEventListener("keydown", event => {{
  if ((event.key === "Enter" || event.key === " ") && event.target.matches(".geo[data-node-id]")) {{
    event.preventDefault(); chooseObject(event.target.dataset.nodeId);
  }}
}});
renderVocabulary();
renderAnalysis();
renderObjectDetail();
renderObjectRelations();
renderMaterialList();
chooseObject("S01");
</script>
</body>
</html>
'''


def main() -> None:
    if not MODEL_FILE.exists():
        raise SystemExit(f"缺少模型输入：{MODEL_FILE.name}")
    if not RESULT_FILE.exists():
        raise SystemExit(f"缺少推演输入：{RESULT_FILE.relative_to(HERE)}")
    model = json.loads(MODEL_FILE.read_text(encoding="utf-8"))
    result = json.loads(RESULT_FILE.read_text(encoding="utf-8"))
    page = page_html(model, result)
    OUTPUT_FILE.write_text(page, encoding="utf-8")
    print(f"已生成：{OUTPUT_FILE.name}（{len(page):,} 字符）")


if __name__ == "__main__":
    main()
