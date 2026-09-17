#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw, ImageFont

# Canvas size 16:9 (1920x1080)
W, H = 1920, 1080
img = Image.new('RGB', (W, H), color='#F8FAFC')
draw = ImageDraw.Draw(img)

# True heavy bold font: Hiragino Sans GB W6 (index 2)
font_w6_path = '/System/Library/Fonts/Hiragino Sans GB.ttc'

# Typography hierarchy (All crisp native W6 Bold without artificial stroke smudging!)
title_font = ImageFont.truetype(font_w6_path, 42, index=2)
subtitle_font = ImageFont.truetype(font_w6_path, 23, index=2)
subtitle_big = ImageFont.truetype(font_w6_path, 29, index=2)

card_title_font = ImageFont.truetype(font_w6_path, 35, index=2)
card_score_label = ImageFont.truetype(font_w6_path, 23, index=2)
card_score_val = ImageFont.truetype(font_w6_path, 30, index=2)
card_gate_font = ImageFont.truetype(font_w6_path, 26, index=2)

# Bullet typography hierarchy
f_reg_24 = ImageFont.truetype(font_w6_path, 24, index=2)
f_reg_25 = ImageFont.truetype(font_w6_path, 25, index=2)
f_bold_27 = ImageFont.truetype(font_w6_path, 27, index=2)
f_bold_28 = ImageFont.truetype(font_w6_path, 28, index=2)
f_huge_30 = ImageFont.truetype(font_w6_path, 30, index=2)
f_huge_34 = ImageFont.truetype(font_w6_path, 34, index=2)

bottom_badge_font = ImageFont.truetype(font_w6_path, 26, index=2)
f_bot_24 = ImageFont.truetype(font_w6_path, 24, index=2)
f_bot_26 = ImageFont.truetype(font_w6_path, 26, index=2)
f_bot_28 = ImageFont.truetype(font_w6_path, 28, index=2)
f_bot_32 = ImageFont.truetype(font_w6_path, 32, index=2)
f_bot_34 = ImageFont.truetype(font_w6_path, 34, index=2)

# Assets directory
assets_dir = '1810_小米集团/assets/emojis'

def get_emoji(name, size):
    path = os.path.join(assets_dir, name)
    im = Image.open(path).convert('RGBA')
    return im.resize((size, size), Image.Resampling.LANCZOS)

emoji_building = get_emoji('emoji_building.png', 44)
emoji_people = get_emoji('emoji_people.png', 44)
emoji_money = get_emoji('emoji_money.png', 44)
emoji_lightning = get_emoji('emoji_lightning.png', 42)
emoji_target = get_emoji('emoji_target.png', 42)
emoji_green = get_emoji('emoji_green_dot.png', 32)
emoji_yellow = get_emoji('emoji_yellow_dot.png', 32)

def draw_elevation_card(xy, fill='#FFFFFF', outline='#CBD5E1', radius=20):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1, y1 + 4, x2, y2 + 4], radius=radius, fill='#E2E8F0')
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=1)

def draw_segments_baseline(d, x, y, segments):
    """Draws text segments aligned with sub-pixel baseline precision."""
    max_ascent = max(font.getmetrics()[0] for _, font, _ in segments)
    baseline_y = y + max_ascent
    curr_x = x
    for text, font, fill in segments:
        ascent, _ = font.getmetrics()
        draw_y = baseline_y - ascent
        d.text((curr_x, draw_y), text, font=font, fill=fill)
        curr_x += int(d.textlength(text, font=font))
    return curr_x

# 1. Top Orange accent bar
draw.rectangle([0, 0, W, 8], fill='#FF6900')

# -------------------------------------------------------------
# Top Header Area (y: 36 ~ 164)
# -------------------------------------------------------------
# Xiaomi Logo
draw.rounded_rectangle([70, 36, 128, 94], radius=14, fill='#FF6900')
mi_font = ImageFont.truetype(font_w6_path, 34, index=2)
draw.text((82, 44), 'mi', font=mi_font, fill='#FFFFFF')

# Main Title (Crisp heavy bold)
draw.text((148, 42), 'XIAOMI 小米集团-W（1810.HK）3R 投资决策看板', font=title_font, fill='#0F172A')

# Subtitle Banner Pill
badge_y = 108
badge_w = 1260
badge_h = 50
draw.rounded_rectangle([70, badge_y, 70 + badge_w, badge_y + badge_h], radius=12, fill='#E2E8F0')

header_segments = [
    ('3R 总分：', subtitle_font, '#475569'),
    ('68.5 / 100', subtitle_big, '#EA580C'),
    ('  ｜  当前评级：', subtitle_font, '#475569'),
    ('【观察】', subtitle_big, '#D97706'),
    ('  ｜  门槛状态：', subtitle_font, '#475569'),
    ('三项全部通过（36 / 12 / 10）', subtitle_big, '#16A34A')
]
draw_segments_baseline(draw, 95, badge_y + 11, header_segments)


# -------------------------------------------------------------
# Middle Area: 3 Cards (Right Business, Right People, Right Price)
# -------------------------------------------------------------
card_y1 = 184
card_h = 608
card_w = 569
gap = 36
card_x_starts = [70, 70 + card_w + gap, 70 + (card_w + gap) * 2]

cards_data = [
    {
        'title': 'Right Business',
        'icon': emoji_building,
        'accent': '#2563EB',
        'score_num': '40.5 / 60',
        'score_clr': '#2563EB',
        'bullets': [
            (True, [
                ('人车家全生态协同壁垒', f_bold_28, '#0F172A')
            ]),
            (True, [
                ('手机高端化', f_bold_28, '#0F172A'),
                (' 与 ', f_reg_24, '#64748B'),
                ('全球排名前三', f_huge_30, '#0F172A')
            ]),
            (False, [
                ('手机&造车', f_bold_28, '#0F172A'),
                (' ', f_reg_24, '#0F172A'),
                ('双红海激烈内卷', f_bold_28, '#C2410C')
            ]),
            (False, [
                ('重资产扩张', f_bold_28, '#0F172A'),
                (' ', f_reg_24, '#0F172A'),
                ('挤压自由现金流', f_bold_28, '#C2410C')
            ])
        ]
    },
    {
        'title': 'Right People',
        'icon': emoji_people,
        'accent': '#7C3AED',
        'score_num': '15.0 / 20',
        'score_clr': '#7C3AED',
        'bullets': [
            (True, [
                ('雷军战役动员力', f_bold_28, '#0F172A'),
                (' ', f_reg_24, '#0F172A'),
                ('行业顶尖', f_bold_28, '#15803D')
            ]),
            (True, [
                ('年内回购 ', f_reg_25, '#0F172A'),
                ('117亿港元', f_huge_34, '#0F172A'),
                (' 重回报', f_bold_28, '#15803D')
            ]),
            (False, [
                ('造车战略下注', f_bold_28, '#0F172A'),
                (' ', f_reg_24, '#0F172A'),
                ('耗资巨大', f_bold_28, '#C2410C')
            ]),
            (False, [
                ('极度考验', f_bold_28, '#C2410C'),
                (' ', f_reg_24, '#0F172A'),
                ('资本配置纪律', f_bold_28, '#0F172A')
            ])
        ]
    },
    {
        'title': 'Right Price',
        'icon': emoji_money,
        'accent': '#059669',
        'score_num': '13.0 / 20',
        'score_clr': '#059669',
        'bullets': [
            (True, [
                ('扣现金后PE仅 ', f_reg_24, '#0F172A'),
                ('13.65x', f_huge_34, '#0F172A'),
                (' (安全垫厚)', f_bold_27, '#15803D')
            ]),
            (True, [
                ('Q2净利环比翻倍', f_reg_24, '#0F172A'),
                ('(+100%)', f_huge_30, '#16A34A'),
                ('确认利润底', f_bold_27, '#0F172A')
            ]),
            (False, [
                ('造车全周期现金流回流', f_bold_27, '#0F172A'),
                (' ', f_reg_24, '#0F172A'),
                ('待验证', f_bold_28, '#C2410C')
            ]),
            (False, [
                ('尚不具备', f_bold_28, '#C2410C'),
                (' ', f_reg_24, '#0F172A'),
                ('消费白马高估值溢价', f_bold_27, '#0F172A')
            ])
        ]
    }
]

for idx, (cx, cdata) in enumerate(zip(card_x_starts, cards_data)):
    # Outer white pillar card with elevation
    draw_elevation_card([cx, card_y1, cx + card_w, card_y1 + card_h], fill='#FFFFFF', outline='#CBD5E1', radius=20)
    
    # Left accent line
    draw.rounded_rectangle([cx + 28, card_y1 + 24, cx + 34, card_y1 + 68], radius=3, fill=cdata['accent'])
    
    # Header Icon + Title
    img.paste(cdata['icon'], (cx + 46, card_y1 + 24), cdata['icon'])
    draw.text((cx + 100, card_y1 + 25), cdata['title'], font=card_title_font, fill='#0F172A')
    
    # Score line: 得分：XX.X / XX / 通过
    score_y = card_y1 + 78
    draw.rounded_rectangle([cx + 28, score_y, cx + 380, score_y + 46], radius=8, fill='#F8FAFC', outline='#CBD5E1', width=1)
    
    score_segments = [
        ('得分：', card_score_label, '#475569'),
        (cdata['score_num'], card_score_val, cdata['score_clr']),
        ('  /  ', card_score_label, '#94A3B8'),
        ('通过', card_gate_font, '#16A34A')
    ]
    draw_segments_baseline(draw, cx + 42, score_y + 9, score_segments)
    
    # Divider line
    div_y = card_y1 + 142
    draw.line([cx + 28, div_y, cx + card_w - 28, div_y], fill='#CBD5E1', width=1)
    
    # 4 Bullets with exact spacing and styled background cards
    b_start_y = div_y + 16
    b_box_h = 92
    b_gap = 14
    
    for b_idx, (is_good, segments) in enumerate(cdata['bullets']):
        by = b_start_y + b_idx * (b_box_h + b_gap)
        
        # Container styling
        if is_good:
            bg_fill = '#F8FDF9'
            bd_stroke = '#86EFAC'
            dot_img = emoji_green
        else:
            bg_fill = '#FFFDF5'
            bd_stroke = '#FCD34D'
            dot_img = emoji_yellow
            
        draw.rounded_rectangle([cx + 24, by, cx + card_w - 24, by + b_box_h], radius=14, fill=bg_fill, outline=bd_stroke, width=1)
        
        # Dot emoji
        img.paste(dot_img, (cx + 42, by + 30), dot_img)
        
        # Text segments with baseline alignment
        draw_segments_baseline(draw, cx + 86, by + 30, segments)


# -------------------------------------------------------------
# Bottom Area (Full Width Card: Core Contradiction & Guidance)
# -------------------------------------------------------------
bottom_y = 820
bottom_h = 222
draw_elevation_card([70, bottom_y, W - 70, bottom_y + bottom_h], fill='#FFFFFF', outline='#CBD5E1', radius=20)

# Left orange accent bar
draw.rounded_rectangle([95, bottom_y + 24, 101, bottom_y + 198], radius=3, fill='#FF6900')

# Row 1: 核心投资矛盾
row1_y = bottom_y + 26
row_h = 76
draw.rounded_rectangle([118, row1_y, W - 95, row1_y + row_h], radius=12, fill='#FFF7ED', outline='#FED7AA', width=1)
img.paste(emoji_lightning, (136, row1_y + 17), emoji_lightning)

row1_segments = [
    ('核心投资矛盾：', bottom_badge_font, '#C2410C'),
    ('手握 ', f_bot_24, '#0F172A'),
    ('1,262 亿', f_bot_34, '#0F172A'),
    (' 超强净现金安全垫   ', f_bot_24, '#0F172A'),
    ('VS', f_bot_26, '#EA580C'),
    ('   汽车扩张期存货与资本开支', f_bot_24, '#0F172A'),
    ('挤压 FCF', f_bot_28, '#DC2626')
]
draw_segments_baseline(draw, 188, row1_y + 23, row1_segments)

# Row 2: 决策指引
row2_y = bottom_y + 118
draw.rounded_rectangle([118, row2_y, W - 95, row2_y + row_h], radius=12, fill='#EFF6FF', outline='#BFDBFE', width=1)
img.paste(emoji_target, (136, row2_y + 17), emoji_target)

row2_segments = [
    ('决策指引：', bottom_badge_font, '#1D4ED8'),
    ('【放入观察池】', f_bot_32, '#1E40AF'),
    ('—— 胜率有底牌，赔率健康；', f_bot_24, '#0F172A'),
    ('重点跟踪汽车造血闭环与现金流企稳', f_bot_26, '#0F172A')
]
draw_segments_baseline(draw, 188, row2_y + 23, row2_segments)

# Save Image
out_path = '1810_小米集团/charts/小米集团_3R投资决策看板.png'
os.makedirs('1810_小米集团/charts', exist_ok=True)
img.save(out_path, quality=95)
print('Successfully generated bold & punchy 3R dashboard image to:', out_path)
