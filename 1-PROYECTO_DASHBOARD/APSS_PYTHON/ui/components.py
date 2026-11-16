# ============================================================
#  COMPONENTES REUTILIZABLES DE UI
# ============================================================
import pandas as pd


def tarjeta_turnos_html(operativos: int, inoperativos: int, disponibilidad: float) -> str:
    total = operativos + inoperativos
    if total == 0:
        return (
            '<div style="padding:0;">'
            '<div style="font-size:14px;color:#fafafa;margin-bottom:8px;">'
            'Turnos Operativos / Inoperativos</div>'
            '<div style="font-size:32px;font-weight:600;color:#666;">0 / 0</div>'
            '<div style="font-size:12px;color:#888;margin-top:8px;">Sin datos</div>'
            '</div>'
        )
    return f"""
    <div style="padding:0;">
        <div style="font-size:14px;color:#fafafa;margin-bottom:8px;">
            TURNOS: Operativos / Inoperativos
        </div>
        <div style="display:flex;gap:16px;align-items:baseline;">
            <div style="text-align:center;min-width:50px;">
                <div style="font-size:32px;font-weight:600;color:#48BB78;line-height:1;">
                    {operativos}
                </div>
                <div style="font-size:11px;color:#48BB78;margin-top:2px;">OPERATIVOS</div>
            </div>
            <div style="font-size:20px;color:#666;">/</div>
            <div style="text-align:center;min-width:50px;">
                <div style="font-size:32px;font-weight:600;color:#F56565;line-height:1;">
                    {inoperativos}
                </div>
                <div style="font-size:11px;color:#F56565;margin-top:2px;">INOPERATIVOS</div>
            </div>
        </div>
        <div style="font-size:12px;color:#888;margin-top:8px;">
            Total: {total} turnos · Disp: {disponibilidad:.1f}%
        </div>
    </div>
    """


def svg_llanta(pos_label: str, fila_opt, horometro,
               cocada_nueva_max: float,
               color_estado_hex: dict) -> str:
    if fila_opt is None:
        return (
            '<div style="display:flex;flex-direction:column;align-items:center;'
            'padding:10px;border:2px dashed #555;border-radius:12px;'
            'background:#1a1a2e;margin:4px;min-height:180px;justify-content:center;">'
            f'<div style="font-size:13px;color:#aaa;font-weight:bold;'
            f'margin-bottom:8px;">{pos_label}</div>'
            '<svg viewBox="0 0 140 90" width="150" height="95">'
            '<rect x="10" y="20" width="120" height="50" rx="8" '
            'fill="#2d2d44" stroke="#444" stroke-width="2"/>'
            '<text x="70" y="50" text-anchor="middle" font-size="11" fill="#777">'
            'SIN DATOS</text></svg></div>'
        )

    ext = fila_opt.get("EXTERIOR", pd.NA)
    int_ = fila_opt.get("INTERIOR", pd.NA)
    estado = fila_opt["ESTADO"]
    rotacion = fila_opt["ROTACION"]
    delta = fila_opt["DELTA"]
    color, color_dark = color_estado_hex.get(estado, ("#888888", "#555555"))

    h_max_px = 55
    ext_val = 0 if pd.isna(ext) else float(ext)
    int_val = 0 if pd.isna(int_) else float(int_)
    h_ext = max(4, min(h_max_px, (ext_val / cocada_nueva_max) * h_max_px)) if ext_val > 0 else 0
    h_int = max(4, min(h_max_px, (int_val / cocada_nueva_max) * h_max_px)) if int_val > 0 else 0
    base_y = 75
    y_ext = base_y - h_ext
    y_int = base_y - h_int
    dash = 'stroke-dasharray="5,3"' if rotacion.startswith("🔄") else ""
    borde_rot = "#F6E05E" if rotacion.startswith("🔄") else "transparent"
    hor_txt = f"{horometro:,.0f} h" if pd.notna(horometro) else "—"

    ext_txt = f"{ext:.1f}" if pd.notna(ext) else "—"
    int_txt = f"{int_:.1f}" if pd.notna(int_) else "—"
    delta_txt = f"{delta:+.1f}" if pd.notna(delta) else "—"

    return (
        '<div style="display:flex;flex-direction:column;align-items:center;'
        f'padding:10px;border:3px solid {borde_rot};border-radius:14px;'
        'background:#1a1a2e;margin:4px;min-height:180px;'
        f'box-shadow:0 0 0 1px {color_dark};">'
        f'<div style="font-size:13px;color:#ddd;font-weight:bold;'
        f'margin-bottom:6px;">{pos_label}</div>'
        '<svg viewBox="0 0 140 90" width="160" height="100">'
        f'<rect x="10" y="15" width="120" height="62" rx="10" '
        f'fill="#2d2d44" stroke="{color}" stroke-width="2"/>'
        f'<rect x="20" y="{y_int:.2f}" width="45" height="{h_int:.2f}" rx="4" '
        f'fill="{color}" opacity="0.85" {dash}/>'
        f'<rect x="75" y="{y_ext:.2f}" width="45" height="{h_ext:.2f}" rx="4" '
        f'fill="{color}" opacity="0.85" {dash}/>'
        f'<line x1="14" y1="{base_y}" x2="126" y2="{base_y}" '
        'stroke="#555555" stroke-width="1" stroke-dasharray="2,2"/>'
        '<text x="42" y="86" text-anchor="middle" font-size="9" fill="#aaaaaa">INT</text>'
        '<text x="97" y="86" text-anchor="middle" font-size="9" fill="#aaaaaa">EXT</text>'
        f'<text x="42" y="{max(12, y_int - 3):.2f}" text-anchor="middle" '
        f'font-size="10" fill="#ffffff" font-weight="bold">{int_txt}</text>'
        f'<text x="97" y="{max(12, y_ext - 3):.2f}" text-anchor="middle" '
        f'font-size="10" fill="#ffffff" font-weight="bold">{ext_txt}</text>'
        '</svg>'
        f'<div style="font-size:11px;color:{color};font-weight:bold;'
        f'margin-top:4px;">{estado} · Δ {delta_txt} mm</div>'
        f'<div style="font-size:10px;color:#888888;margin-top:2px;">'
        f'{rotacion} · {hor_txt}</div>'
        '</div>'
    )