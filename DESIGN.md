# DESIGN.md — Level 2 Design System
# Inherits from: C:/Users/Lenovo/.claude/DESIGN.md
# Project: ClaudeRevit Extension

# ============================================================
# COLOUR PALETTE
# ============================================================
- Background dark:   #12121a
- Background mid:    #1a1a26
- Background card:   #1e1e2c
- Background input:  #22222e
- Gold accent:       #c8a96e
- Gold hover:        #d4b97a
- Text primary:      #e8e8f0
- Text secondary:    #9999bb
- Text dim:          #555566
- Border:            #2a2a3a
- Success:           #50d27a
- Warning:           #e8a838
- Error:             #e85858

# ============================================================
# TYPOGRAPHY
# ============================================================
- UI labels:         system-ui, 12–13px
- Code editor:       Consolas, 13px
- Headers:           600 weight, gold
- Monospace output:  Consolas

# ============================================================
# WPF COMPONENT CONVENTIONS
# ============================================================
- All windows: base_window() from wpf_helper.py
- Title bar: traffic-light dots (red/amber/green) + doc name + panel name
- Buttons: gold (primary action) / grey (secondary/cancel)
- Input: BG_INP background, BORDER border, GOLD caret
- Cards/sections: BG_CARD background, BORDER border, 8px radius
- Dividers: 1px BORDER colour horizontal lines

# ============================================================
# DASHBOARD (Next.js)
# ============================================================
- Same dark palette as WPF
- Cards: 1a1a26 background, 10px radius
- Grid: auto-fill minmax(260px, 1fr)
- Gold accent for model name card border
- Port 3333
