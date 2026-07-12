# main.py - Resume Genie (Groq Powered) — Enterprise UI
import streamlit as st
import os
import re
import time
import tempfile
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ───────────────────────────────────────────────
# CONFIG (shared across all tools)
# ───────────────────────────────────────────────
st.set_page_config(
    page_title="Resume Genie",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

from PIL import Image

# ───────────────────────────────────────────────
# DESIGN TOKENS
# ink        #0B0E14   base background
# surface    #12161F   card / panel background
# surface-2  #171C27   elevated panel / hover
# border     rgba(255,255,255,.08)
# text-1     #ECEEF2   primary text
# text-2     #8A93A3   secondary text
# accent     #2F5CFF   primary action (executive blue)
# accent-2   #C9A24B   signature gold (verification / premium)
# good       #21C08A   success / high score
# warn       #E2A63B   mid score
# bad        #E5484D   low score / error
#
# Display type : "Sora"       — headlines, nav, buttons
# Body type    : "Inter"      — paragraphs, inputs
# Data type    : "IBM Plex Mono" — scores, metadata, status
# ───────────────────────────────────────────────

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
    --ink: #0B0E14;
    --surface: #12161F;
    --surface-2: #171C27;
    --border: rgba(255,255,255,0.08);
    --border-strong: rgba(255,255,255,0.14);
    --text-1: #ECEEF2;
    --text-2: #8A93A3;
    --accent: #2F5CFF;
    --accent-hover: #4E74FF;
    --accent-2: #C9A24B;
    --good: #21C08A;
    --warn: #E2A63B;
    --bad: #E5484D;
}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ---------- BACKGROUND ---------- */
.stApp {
    background:
        radial-gradient(ellipse 900px 500px at 15% -10%, rgba(47,92,255,0.10), transparent),
        radial-gradient(ellipse 700px 500px at 100% 0%, rgba(201,162,75,0.06), transparent),
        var(--ink);
}

/* ---------- TOP STATUS RAIL (signature motif) ---------- */
.status-rail {
    height: 3px;
    width: 100%;
    background: linear-gradient(90deg, var(--accent) 0%, var(--accent-2) 100%);
    opacity: 0.9;
    margin-bottom: 28px;
    border-radius: 2px;
}

/* ---------- SIDEBAR ---------- */
section[data-testid="stSidebar"] {
    background: #0D1017;
    border-right: 1px solid var(--border);
    position: relative;
    overflow: hidden;
}

/* Slow-moving ambient glow sweep behind sidebar content — subtle, not rainbow */
section[data-testid="stSidebar"]::before {
    content: "";
    position: absolute;
    top: -20%; left: -40%;
    width: 220%; height: 60%;
    background: radial-gradient(ellipse at center, rgba(47,92,255,0.16), transparent 65%);
    animation: sidebarDrift 10s ease-in-out infinite;
    pointer-events: none;
    z-index: 0;
}
section[data-testid="stSidebar"]::after {
    content: "";
    position: absolute;
    bottom: -25%; right: -30%;
    width: 180%; height: 55%;
    background: radial-gradient(ellipse at center, rgba(201,162,75,0.10), transparent 65%);
    animation: sidebarDrift2 13s ease-in-out infinite;
    pointer-events: none;
    z-index: 0;
}
@keyframes sidebarDrift {
    0%, 100% { transform: translate(0, 0) scale(1); }
    50%      { transform: translate(6%, 8%) scale(1.08); }
}
@keyframes sidebarDrift2 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    50%      { transform: translate(-6%, -6%) scale(1.1); }
}
section[data-testid="stSidebar"] > div { position: relative; z-index: 1; }

section[data-testid="stSidebar"] * { color: var(--text-1) !important; }
section[data-testid="stSidebar"] .stCaption, section[data-testid="stSidebar"] small {
    color: var(--text-2) !important;
}

/* Animated shimmering logo text */
.sidebar-logo {
    font-family: 'Sora', sans-serif;
    font-size: 18px;
    font-weight: 800;
    margin-bottom: 2px;
    background: linear-gradient(100deg, #ECEEF2 20%, var(--accent) 45%, var(--accent-2) 55%, #ECEEF2 80%);
    background-size: 250% auto;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent !important;
    animation: logoShine 5s linear infinite;
}
@keyframes logoShine {
    to { background-position: -250% center; }
}

/* Small orbiting dot motion graphic beside the logo */
.sidebar-brand-row { display: flex; align-items: center; gap: 10px; margin-bottom: 2px; }
.orbit {
    position: relative;
    width: 20px; height: 20px;
    flex: none;
}
.orbit-core {
    position: absolute;
    top: 50%; left: 50%;
    width: 6px; height: 6px;
    margin: -3px 0 0 -3px;
    border-radius: 50%;
    background: var(--accent-2);
    box-shadow: 0 0 8px rgba(201,162,75,0.7);
}
.orbit-ring {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    border: 1px solid rgba(47,92,255,0.35);
    border-top-color: var(--accent);
    animation: orbitSpin 3s linear infinite;
}
@keyframes orbitSpin {
    to { transform: rotate(360deg); }
}

/* Active nav item indicator — animated pulse dot */
.nav-pulse {
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--good);
    margin-right: 6px;
    box-shadow: 0 0 0 0 rgba(33,192,138,0.5);
    animation: navPulse 2s ease-out infinite;
}
@keyframes navPulse {
    0%   { box-shadow: 0 0 0 0 rgba(33,192,138,0.45); }
    70%  { box-shadow: 0 0 0 6px rgba(33,192,138,0); }
    100% { box-shadow: 0 0 0 0 rgba(33,192,138,0); }
}

/* Animated divider line in sidebar */
.sidebar-divider {
    height: 1px;
    width: 100%;
    margin: 14px 0;
    background: linear-gradient(90deg, transparent, var(--border-strong), transparent);
    background-size: 200% auto;
    animation: dividerSweep 6s linear infinite;
}
@keyframes dividerSweep {
    to { background-position: -200% center; }
}

/* ---------- SUBTLE ENTRANCE (restrained, single pass) ---------- */
@keyframes riseIn {
    0%   { opacity: 0; transform: translateY(10px); }
    100% { opacity: 1; transform: translateY(0); }
}
.block-container { animation: riseIn 0.45s ease-out; }

/* ---------- TYPOGRAPHY ---------- */
h1, h2, h3 { font-family: 'Sora', sans-serif !important; color: var(--text-1) !important; letter-spacing: -0.01em; }
h1 { font-weight: 800 !important; }
h2, h3 { font-weight: 700 !important; }
p, span, label, .stMarkdown, div { color: var(--text-1); }

.eyebrow {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11.5px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent-2);
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.eyebrow::before {
    content: "";
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--good);
    box-shadow: 0 0 0 3px rgba(33,192,138,0.18);
}

/* ---------- HERO PANEL ---------- */
.hero-panel {
    border: 1px solid var(--border);
    background:
        radial-gradient(ellipse 520px 260px at 50% 0%, rgba(47,92,255,0.12), transparent 70%),
        linear-gradient(180deg, var(--surface) 0%, var(--ink) 100%);
    border-radius: 16px;
    padding: 30px 32px 26px 32px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
}
.hero-panel .eyebrow { justify-content: center; margin-bottom: 12px; }
.hero-title {
    font-family: 'Sora', sans-serif;
    font-size: 24px;
    line-height: 1.32;
    font-weight: 800;
    color: var(--text-1);
    margin: 0 0 10px 0;
    max-width: 620px;
}
.hero-title .accent-word {
    background: linear-gradient(100deg, var(--accent) 0%, var(--accent-2) 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}
.hero-sub {
    font-size: 13.5px;
    color: var(--text-2);
    max-width: 500px;
    line-height: 1.6;
    margin: 0 auto;
}
.hero-badges { display: flex; gap: 8px; margin-top: 18px; flex-wrap: wrap; justify-content: center; }
.badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10.5px;
    padding: 4px 9px;
    border-radius: 6px;
    border: 1px solid var(--border-strong);
    color: var(--text-2);
    background: rgba(255,255,255,0.02);
}

/* ---------- TOOL CARDS ---------- */
/* Streamlit's native bordered container (st.container(border=True)) restyled
   to match the surface/border tokens, so content actually renders inside the
   box instead of next to an empty one. */
div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
    border: 1px solid var(--border);
    background: var(--surface);
    border-radius: 12px;
    padding: 18px 20px 6px 20px;
    transition: border-color 0.2s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover > div[data-testid="stVerticalBlock"] {
    border-color: var(--border-strong);
}

/* ---------- BUTTONS — solid, disciplined, one accent ---------- */
.stButton > button, .stDownloadButton > button {
    background: var(--accent) !important;
    color: #FFFFFF !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    padding: 0.62em 1.4em !important;
    box-shadow: 0 1px 0 rgba(255,255,255,0.06) inset, 0 6px 16px rgba(47,92,255,0.18);
    transition: background 0.16s ease, transform 0.12s ease, box-shadow 0.16s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: var(--accent-hover) !important;
    transform: translateY(-1px);
    box-shadow: 0 1px 0 rgba(255,255,255,0.08) inset, 0 10px 22px rgba(47,92,255,0.28);
}
.stButton > button:active, .stDownloadButton > button:active {
    transform: translateY(0);
    background: #274CDB !important;
}
.stButton > button:focus-visible {
    outline: 2px solid var(--accent-2);
    outline-offset: 2px;
}

/* ---------- FILE UPLOADER ---------- */
[data-testid="stFileUploaderDropzone"] {
    background: var(--surface) !important;
    border: 1px dashed var(--border-strong) !important;
    border-radius: 10px !important;
    transition: border-color 0.2s ease, background 0.2s ease;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--accent) !important;
    background: var(--surface-2) !important;
}

/* ---------- INPUTS ---------- */
.stTextArea textarea, .stTextInput input {
    background: var(--surface) !important;
    color: var(--text-1) !important;
    border-radius: 8px !important;
    border: 1px solid var(--border) !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(47,92,255,0.16) !important;
}

/* ---------- SIDEBAR NAV (radio) ---------- */
[data-testid="stSidebar"] .stRadio > label { display: none; }
[data-testid="stSidebar"] .stRadio [role="radiogroup"] { gap: 4px; display: flex; flex-direction: column; }
[data-testid="stSidebar"] .stRadio label {
    padding: 9px 10px 9px 12px;
    border-radius: 8px;
    font-family: 'Sora', sans-serif;
    font-size: 13.5px;
    font-weight: 500;
    border-left: 2px solid transparent;
    transition: background 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(47,92,255,0.10);
    border-left-color: var(--accent);
    transform: translateX(2px);
}
[data-testid="stSidebar"] .stRadio label[data-checked="true"],
[data-testid="stSidebar"] .stRadio input:checked + div {
    color: var(--text-1) !important;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) {
    background: rgba(47,92,255,0.14);
    border-left-color: var(--accent-2);
    animation: navPulse 2.4s ease-out infinite;
}

/* ---------- ALERTS ---------- */
div[data-testid="stAlert"] {
    border-radius: 10px;
    border: 1px solid var(--border);
}

/* ---------- STATUS / LOADING BAR (signature: "verification scan") ---------- */
.scan-wrap {
    border: 1px solid var(--border);
    background: var(--surface);
    border-radius: 10px;
    padding: 14px 16px;
    margin: 10px 0 18px 0;
}
.scan-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.scan-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--accent-2);
    animation: dotPulse 1.1s ease-in-out infinite;
}
@keyframes dotPulse {
    0%, 100% { opacity: 0.35; transform: scale(0.85); }
    50% { opacity: 1; transform: scale(1); }
}
.scan-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12.5px;
    color: var(--text-2);
    letter-spacing: 0.02em;
}
.scan-track {
    height: 3px;
    width: 100%;
    background: var(--surface-2);
    border-radius: 3px;
    overflow: hidden;
}
.scan-fill {
    height: 100%;
    width: 40%;
    background: linear-gradient(90deg, var(--accent), var(--accent-2));
    border-radius: 3px;
    animation: scanMove 1.3s ease-in-out infinite;
}
@keyframes scanMove {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(350%); }
}

/* ---------- RESULT / VERIFICATION BADGE ---------- */
.verify-card {
    border: 1px solid var(--border-strong);
    background: linear-gradient(180deg, var(--surface) 0%, var(--surface-2) 100%);
    border-radius: 12px;
    padding: 18px 20px;
    margin: 4px 0 18px 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
}
.verify-left { display: flex; align-items: center; gap: 14px; }
.verify-icon {
    width: 40px; height: 40px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    background: rgba(201,162,75,0.12);
    border: 1px solid rgba(201,162,75,0.3);
    color: var(--accent-2);
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
}
.verify-title { font-family: 'Sora', sans-serif; font-weight: 700; font-size: 14.5px; color: var(--text-1); }
.verify-sub { font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; color: var(--text-2); margin-top: 2px; }
.verify-tag {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 20px;
    background: rgba(33,192,138,0.12);
    border: 1px solid rgba(33,192,138,0.35);
    color: var(--good);
}

/* ---------- FOOTER ---------- */
.genie-footer {
    margin-top: 30px;
    padding: 14px 18px;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--surface);
    display: flex;
    justify-content: center;
    gap: 26px;
    flex-wrap: wrap;
}
.footer-item {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: var(--text-2);
}

/* ---------- SCROLLBAR ---------- */
::-webkit-scrollbar { width: 9px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--surface-2); border-radius: 8px; border: 1px solid var(--border); }

/* ---------- AMBIENT PARTICLE FIELD ---------- */
/* Slow-drifting motes across the whole app — depth without noise */
.bg-particles {
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    overflow: hidden;
}
.particle {
    position: absolute;
    bottom: -6%;
    width: 3px; height: 3px;
    border-radius: 50%;
    background: var(--accent-2);
    opacity: 0;
    animation: floatUp linear infinite;
}
.particle.blue { background: var(--accent); }
.particle:nth-child(1)  { left: 6%;  width: 2px; height: 2px; animation-duration: 22s; animation-delay: 0s; }
.particle:nth-child(2)  { left: 16%; width: 3px; height: 3px; animation-duration: 28s; animation-delay: 3s; }
.particle:nth-child(3)  { left: 27%; width: 2px; height: 2px; animation-duration: 19s; animation-delay: 6s; }
.particle:nth-child(4)  { left: 38%; width: 3px; height: 3px; animation-duration: 25s; animation-delay: 1s; }
.particle:nth-child(5)  { left: 49%; width: 2px; height: 2px; animation-duration: 30s; animation-delay: 9s; }
.particle:nth-child(6)  { left: 61%; width: 3px; height: 3px; animation-duration: 21s; animation-delay: 4s; }
.particle:nth-child(7)  { left: 72%; width: 2px; height: 2px; animation-duration: 26s; animation-delay: 7s; }
.particle:nth-child(8)  { left: 83%; width: 3px; height: 3px; animation-duration: 23s; animation-delay: 2s; }
.particle:nth-child(9)  { left: 91%; width: 2px; height: 2px; animation-duration: 29s; animation-delay: 11s; }
.particle:nth-child(10) { left: 12%; width: 2px; height: 2px; animation-duration: 24s; animation-delay: 13s; }
@keyframes floatUp {
    0%   { transform: translate(0, 0); opacity: 0; }
    8%   { opacity: 0.55; }
    92%  { opacity: 0.35; }
    100% { transform: translate(24px, -108vh); opacity: 0; }
}

/* ---------- SIGNATURE MOTIF: FLYING DOCUMENT ---------- */
/* A resume, sent — arcs across the hero once per load, banking like a paper plane
   finding its destination. This is the one bold moment; everything else stays quiet. */
.flight-path {
    position: absolute;
    top: 14px; left: 0;
    width: 100%; height: 90px;
    pointer-events: none;
    overflow: visible;
    z-index: 2;
}
.flight-path svg {
    position: absolute;
    width: 34px; height: 34px;
    offset-path: path("M -40,70 C 120,10 280,90 460,20 C 600,-30 700,50 820,-10");
    offset-rotate: auto;
    animation: sendResume 3.6s cubic-bezier(0.65, 0, 0.35, 1) 0.5s 1 both;
}
@keyframes sendResume {
    0%   { opacity: 0; offset-distance: 0%; }
    6%   { opacity: 1; }
    88%  { opacity: 1; }
    100% { opacity: 0; offset-distance: 100%; }
}
.flight-trail {
    position: absolute;
    top: 14px; left: 0;
    width: 100%; height: 90px;
    pointer-events: none;
    z-index: 1;
}
.flight-trail path {
    fill: none;
    stroke: url(#trailGrad);
    stroke-width: 1.4;
    stroke-dasharray: 4 6;
    stroke-linecap: round;
    opacity: 0;
    animation: trailFade 3.6s ease 0.5s 1 both;
}
@keyframes trailFade {
    0%   { opacity: 0; }
    10%  { opacity: 0.5; }
    85%  { opacity: 0.35; }
    100% { opacity: 0; }
}

/* ---------- CARD LIFT (premium hover weight) ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
    transition: border-color 0.25s ease, transform 0.28s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.28s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover > div[data-testid="stVerticalBlock"] {
    transform: translateY(-3px);
    box-shadow: 0 18px 34px rgba(0,0,0,0.32), 0 0 0 1px rgba(255,255,255,0.03);
}

/* ---------- IDLE-FLOATING BADGES ---------- */
.hero-badges .badge {
    animation: badgeBob 4.5s ease-in-out infinite;
}
.hero-badges .badge:nth-child(1) { animation-delay: 0s; }
.hero-badges .badge:nth-child(2) { animation-delay: 0.5s; }
.hero-badges .badge:nth-child(3) { animation-delay: 1s; }
@keyframes badgeBob {
    0%, 100% { transform: translateY(0); }
    50%      { transform: translateY(-3px); }
}

/* ---------- BUTTON CENTERING ---------- */
div[data-testid="stButton"], div[data-testid="stDownloadButton"] {
    display: flex;
    justify-content: center;
    margin: 10px 0;
}

/* ---------- BUTTON LAUNCH MICRO-INTERACTION ---------- */
.stButton > button::after, .stDownloadButton > button::after {
    content: "";
}

/* ---------- REDUCED MOTION ---------- */
@media (prefers-reduced-motion: reduce) {
    * { animation: none !important; transition: none !important; }
    .flight-path, .flight-trail, .bg-particles { display: none !important; }
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="bg-particles">
    <div class="particle blue"></div>
    <div class="particle"></div>
    <div class="particle blue"></div>
    <div class="particle"></div>
    <div class="particle blue"></div>
    <div class="particle"></div>
    <div class="particle blue"></div>
    <div class="particle"></div>
    <div class="particle blue"></div>
    <div class="particle"></div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="status-rail"></div>', unsafe_allow_html=True)


def scan_loader(label: str):
    """Signature 'verification scan' loading indicator — returns placeholder to clear later."""
    placeholder = st.empty()
    placeholder.markdown(f"""
    <div class="scan-wrap">
        <div class="scan-row">
            <div class="scan-dot"></div>
            <div class="scan-label">{label}</div>
        </div>
        <div class="scan-track"><div class="scan-fill"></div></div>
    </div>
    """, unsafe_allow_html=True)
    return placeholder


def verify_badge(title: str, subtitle: str, tag: str = "COMPLETE"):
    st.markdown(f"""
    <div class="verify-card">
        <div class="verify-left">
            <div class="verify-icon">✓</div>
            <div>
                <div class="verify-title">{title}</div>
                <div class="verify-sub">{subtitle}</div>
            </div>
        </div>
        <div class="verify-tag">{tag}</div>
    </div>
    """, unsafe_allow_html=True)


# ───────────────────────────────────────────────
# SIDEBAR BRANDING
# ───────────────────────────────────────────────
try:
    logo = Image.open("logo.png")
    st.sidebar.image(logo, width=64)
except Exception:
    pass

st.sidebar.markdown("""
<div class="sidebar-brand-row">
    <div class="orbit">
        <div class="orbit-ring"></div>
        <div class="orbit-core"></div>
    </div>
    <div class="sidebar-logo">Resume Genie</div>
</div>
<div style="font-family:'IBM Plex Mono',monospace; font-size:11px; letter-spacing:0.05em; color:#8A93A3; margin-bottom:4px;">
AI CAREER PLATFORM
</div>
<div class="sidebar-divider"></div>
""", unsafe_allow_html=True)

# Load environment variables from .env file
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    try:
        GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        GROQ_API_KEY = ""

if not GROQ_API_KEY:
    st.error("❌ **GROQ_API_KEY missing**. Add to `.env` file or `.streamlit/secrets.toml`.")
    st.stop()


@st.cache_resource(show_spinner="Initializing model...")
def get_llm():
    return ChatGroq(model="llama-3.3-70b-versatile", api_key=GROQ_API_KEY, temperature=0.2, max_tokens=2000)


llm = get_llm()

# ───────────────────────────────────────────────
# SHARED PDF LOADER
# ───────────────────────────────────────────────
@st.cache_data
def extract_resume_text(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    try:
        loader = PyPDFLoader(tmp_path)
        docs = loader.load()
        text = "\n\n".join(doc.page_content for doc in docs)
        return text
    finally:
        os.unlink(tmp_path)


# ───────────────────────────────────────────────
# PROMPTS (pre-defined for each tool)
# ───────────────────────────────────────────────
COVER_LETTER_PROMPT = PromptTemplate.from_template("""
Write a professional cover letter (300–450 words) for this job. Match resume to JD exactly. Standard format.
Job Description: {job_description}
Resume: {resume_text}
Do not invent facts.
""")

RESUME_SCORER_PROMPT = """You are an expert resume scorer. Analyze the resume's match to the job description.

Respond ONLY in valid Markdown, following this EXACT structure. Every bullet must be its own Markdown
list item starting with "- " on its own line (never inline, never separated by "•"). Leave a blank line
between sections.

**Score**: X/100

**Overall Match**: X%

**Keywords matched**
- keyword one
- keyword two

**Missing keywords**
- keyword one
- keyword two

**Readability Score**: X/100

**ATS Compatibility Score**: X/100

**Summary**
One or two sentences.

**Skill gap analysis**
- point one
- point two

**Improvement suggestions**
- point one
- point two

**Industry specific feedback**
- point one
- point two

Job: {job_description}
Resume: {context}
Be honest, use rubrics. Do not merge bullets into a single paragraph."""

RESUME_CHECKER_PROMPT = PromptTemplate.from_template("""
Score the resume standalone (clarity, format, ATS-friendliness, skills).

Respond ONLY in valid Markdown, following this EXACT structure. Every bullet must be its own Markdown
list item starting with "- " on its own line (never inline, never separated by "•"). Leave a blank line
between sections.

**Score**: X/100

**Strengths**
- point one
- point two

**Weaknesses**
- point one
- point two

**Skills Mentioned**
- skill one
- skill two

**Recommended Skills**
- skill one
- skill two

**Next Career Steps**
- step one
- step two

Resume: {context}
Do not merge bullets into a single paragraph.
""")

# ───────────────────────────────────────────────
# MARKDOWN SAFETY NET
# Some models still ignore formatting instructions and return bullets
# separated by "•" with no real line breaks. This normalizes any response
# into valid Markdown before rendering, regardless of what the model does.
# ───────────────────────────────────────────────

def normalize_markdown(text: str) -> str:
    if not text:
        return text
    # Break inline bullets ("... • item • item") onto their own lines
    text = re.sub(r'\s*•\s*', '\n- ', text)
    # If the model used "- " inline instead of "•", also split those
    text = re.sub(r'(?<!\n)(?<!^)\s(-\s)', r'\n\1', text)
    # Ensure bold section headers (e.g. **Score**:) start a fresh paragraph
    text = re.sub(r'(?<!\n)\n?(\*\*[A-Za-z][^*\n]{0,60}\*\*:?)', r'\n\n\1', text)
    # Collapse 3+ blank lines down to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def generate_cover_letter_pdf(text: str) -> bytes:
    """Render plain cover letter text into a clean, printable PDF and return the bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
    )
    styles = getSampleStyleSheet()
    body_style = styles["Normal"]
    body_style.fontSize = 11
    body_style.leading = 16

    story = []
    for para in text.strip().split("\n\n"):
        para = para.strip()
        if not para:
            continue
        # Escape XML special chars, then convert single newlines to <br/> for reportlab markup
        safe = para.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe = safe.replace("\n", "<br/>")
        story.append(Paragraph(safe, body_style))
        story.append(Spacer(1, 12))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# ───────────────────────────────────────────────
# BRIEF LOAD STATE (single subtle pass, not a splash screen)
# ───────────────────────────────────────────────
if "booted" not in st.session_state:
    st.session_state.booted = False

if not st.session_state.booted:
    boot_ph = st.empty()
    boot_ph.markdown("""
    <div class="scan-wrap" style="max-width:420px; margin: 80px auto 0 auto;">
        <div class="scan-row">
            <div class="scan-dot"></div>
            <div class="scan-label">INITIALIZING WORKSPACE...</div>
        </div>
        <div class="scan-track"><div class="scan-fill"></div></div>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(0.7)
    boot_ph.empty()
    st.session_state.booted = True

# ───────────────────────────────────────────────
# MAIN UI — Hero panel
# ───────────────────────────────────────────────
st.markdown("""
<div class="hero-panel">
    <svg class="flight-trail" viewBox="0 0 820 90" preserveAspectRatio="none">
        <defs>
            <linearGradient id="trailGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#2F5CFF" stop-opacity="0"/>
                <stop offset="50%" stop-color="#2F5CFF" stop-opacity="0.9"/>
                <stop offset="100%" stop-color="#C9A24B" stop-opacity="0.9"/>
            </linearGradient>
        </defs>
        <path d="M -40,70 C 120,10 280,90 460,20 C 600,-30 700,50 820,-10"/>
    </svg>
    <div class="flight-path">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M21.5 2.5L2 10.5L10.5 13.5L14 21L21.5 2.5Z" fill="#ECEEF2" stroke="#2F5CFF" stroke-width="1.1" stroke-linejoin="round"/>
            <path d="M21.5 2.5L10.5 13.5" stroke="#C9A24B" stroke-width="1.1"/>
        </svg>
    </div>
    <div class="eyebrow">RESUME GENIE · GROQ / LLAMA 3.3</div>
    <div class="hero-title">Land the interview — not just the application.<br>Your resume, <span class="accent-word">engineered for every job</span>.</div>
    <div class="hero-sub">Tailored cover letters, honest ATS scoring, and a career coach that actually
    knows your background — one fast, focused workspace, powered by Groq.</div>
    <div class="hero-badges">
        <div class="badge">MODEL · Llama 3.3 70B</div>
        <div class="badge">LATENCY · Groq inference</div>
        <div class="badge">4 TOOLS · 1 WORKSPACE</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── LEFT SIDEBAR: Tool Selector ───
st.sidebar.markdown("<div style='font-family:IBM Plex Mono,monospace; font-size:11px; letter-spacing:0.08em; color:#8A93A3; margin-bottom:8px; display:flex; align-items:center;'><span class='nav-pulse'></span>SELECT TOOL</div>", unsafe_allow_html=True)
tool = st.sidebar.radio("Choose a service:", [
    "✉️ Cover Letter Generator",
    "📊 Resume-JD Matcher",
    "🔍 Resume Checker",
    "💬 Career Coach Chat"
], index=0, horizontal=False, label_visibility="collapsed")

# Shared inputs (positioned based on tool)
if tool in ["✉️ Cover Letter Generator", "📊 Resume-JD Matcher"]:
    st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    st.sidebar.markdown("<div style='font-family:IBM Plex Mono,monospace; font-size:11px; letter-spacing:0.08em; color:#8A93A3; margin-bottom:8px;'>INPUTS</div>", unsafe_allow_html=True)
    job_desc = st.sidebar.text_area("Job Description", height=200, key="jd_shared")
    resume_file = st.sidebar.file_uploader("Resume PDF", type="pdf", key="resume_shared")

# ───────────────────────────────────────────────
# TOOL 1: COVER LETTER
# ───────────────────────────────────────────────
if tool == "✉️ Cover Letter Generator":
    st.header("Cover Letter Generator")
    col1, col2 = st.columns([1, 1])

    with col1:
        with st.container(border=True):
            st.subheader("Job Description")
            job_description = st.text_area(
                "Paste JD", value=job_desc or "", height=350, key="jd_cl",
                label_visibility="collapsed", placeholder="Paste the job description here…"
            )

    with col2:
        with st.container(border=True):
            st.subheader("Your Resume")
            uploaded_file = st.file_uploader("Upload PDF", type="pdf", key="cl_resume")
            if uploaded_file:
                if st.button("Generate cover letter", type="primary"):
                    loader_ph = scan_loader("EXTRACTING RESUME AND DRAFTING LETTER...")
                    resume_text = extract_resume_text(uploaded_file)
                    chain = COVER_LETTER_PROMPT | llm
                    full_response = ""
                    resp_container = st.empty()
                    for chunk in chain.stream({"job_description": job_description, "resume_text": resume_text}):
                        content = chunk.content if hasattr(chunk, "content") else str(chunk)
                        full_response += content
                        resp_container.markdown(full_response + "▌")
                    resp_container.markdown(full_response)
                    loader_ph.empty()
                    verify_badge("Cover letter generated", "Matched against job description", "COMPLETE")
                    pdf_bytes = generate_cover_letter_pdf(full_response)
                    st.download_button(
                        "Download as PDF",
                        data=pdf_bytes,
                        file_name="cover_letter.pdf",
                        mime="application/pdf"
                    )

# ───────────────────────────────────────────────
# TOOL 2: RESUME SCORER/MATCHER
# ───────────────────────────────────────────────
elif tool == "📊 Resume-JD Matcher":
    st.header("Resume vs Job Description Matcher")
    col1, col2 = st.columns([1, 1])

    with col1:
        with st.container(border=True):
            st.subheader("Job Description")
            job_description = st.text_area(
                "Paste full JD", value=job_desc or "", height=350, key="jd_scorer",
                label_visibility="collapsed", placeholder="Paste the job description here…"
            )

    with col2:
        with st.container(border=True):
            st.subheader("Resume")
            uploaded_file = st.file_uploader("Upload PDF", type="pdf", key="scorer_resume")
            if uploaded_file:
                verify_badge("Resume loaded", uploaded_file.name, "READY")
                if st.button("Score match", type="primary"):
                    loader_ph = scan_loader("ANALYZING MATCH · TYPICALLY 30–60S...")
                    context = extract_resume_text(uploaded_file)
                    prompt = RESUME_SCORER_PROMPT.format(job_description=job_description, context=context)
                    response = llm.invoke(prompt)
                    loader_ph.empty()
                    st.markdown("### Analysis result")
                    st.markdown(normalize_markdown(response.content))

# ───────────────────────────────────────────────
# TOOL 3: RESUME CHECKER
# ───────────────────────────────────────────────
elif tool == "🔍 Resume Checker":
    st.header("Standalone Resume Evaluator")
    with st.container(border=True):
        uploaded_file = st.file_uploader("Upload resume PDF", type="pdf", key="checker_resume")

        if uploaded_file and st.button("Evaluate resume", type="primary"):
            loader_ph = scan_loader("RUNNING EVALUATION...")
            context = extract_resume_text(uploaded_file)
            chain = RESUME_CHECKER_PROMPT | llm
            response = chain.invoke({"context": context})
            loader_ph.empty()
            verify_badge("Evaluation complete", uploaded_file.name, "COMPLETE")
            st.markdown("### Detailed evaluation")
            st.markdown(normalize_markdown(response.content))

# ───────────────────────────────────────────────
# TOOL 4: CAREER COACH CHAT
# ───────────────────────────────────────────────
elif tool == "💬 Career Coach Chat":
    st.header("Career Coach Chatbot")

    # Resume upload (session-persisted)
    if "resume_context" not in st.session_state:
        st.session_state.resume_context = None
        st.session_state.chat_history = []

    uploaded_file = st.file_uploader("Upload resume first", type="pdf", key="chat_resume")
    if uploaded_file and st.session_state.resume_context is None:
        loader_ph = scan_loader("READING RESUME...")
        context = extract_resume_text(uploaded_file)
        loader_ph.empty()
        st.session_state.resume_context = context
        st.rerun()

    if not st.session_state.resume_context:
        st.warning("Upload your resume to start chatting.")
        st.stop()

    # Layout: Left=Resume | Right=Chat
    left_col, right_col = st.columns([1, 1])

    with left_col:
        with st.container(border=True):
            st.subheader("Your Resume")
            with st.expander("View full text", expanded=True):
                st.text_area("", st.session_state.resume_context, height=500, disabled=True, label_visibility="collapsed")

    with right_col:
        with st.container(border=True):
            st.subheader("Career Coach")
            system_msg = SystemMessage(content=f"""You are a career coach. Use this resume: {st.session_state.resume_context}""")

            # Chat history
            for msg in st.session_state.chat_history:
                role = "user" if isinstance(msg, HumanMessage) else "assistant"
                with st.chat_message(role):
                    st.markdown(msg.content)

            # Chat input
            if prompt := st.chat_input("Ask about career, resume, interviews..."):
                st.session_state.chat_history.append(HumanMessage(content=prompt))
                with st.chat_message("assistant"):
                    messages = [system_msg] + st.session_state.chat_history
                    resp_container = st.empty()
                    full_resp = ""
                    for chunk in llm.stream(messages):
                        full_resp += chunk.content
                        resp_container.markdown(full_resp + "▌")
                    resp_container.markdown(full_resp)
                st.session_state.chat_history.append(AIMessage(content=full_resp))
                st.rerun()

# ───────────────────────────────────────────────
# FOOTER
# ───────────────────────────────────────────────
st.markdown("""
<div class="genie-footer">
    <span class="footer-item">STATUS · All tools live</span>
    <span class="footer-item">MODEL · Groq / Llama 3.3</span>
    <span class="footer-item">BUILD · Jan 2026 · BISWAJIT PATTANAIK</span>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
st.sidebar.caption("Use the sidebar to switch tools instantly.")