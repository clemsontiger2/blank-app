import json
import os
import re
from datetime import date
from pathlib import Path

import streamlit as st
from huggingface_hub import InferenceClient

OUTPUT_DIR = Path('/mnt/user-data/outputs')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title='Travel Planner + VQS', page_icon='🧭', layout='wide')
st.title('🧭 Travel Planner + VQS')

DEFAULT_MODEL = 'Qwen/Qwen2.5-72B-Instruct'

WEIGHTS = {
    'Financial Efficiency': 5,
    'Loyalty': 4,
    'Culinary': 4,
    'Activity': 3,
    'Friction': 3,
}

def tier(vqs: int) -> str:
    if vqs >= 160:
        return '🟢 Excellent'
    if vqs >= 130:
        return '🟡 Great'
    if vqs >= 100:
        return '🟠 Good'
    if vqs >= 70:
        return '🔴 Fair'
    return '⛔ Below Average'

def slugify(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

def compute_vqs(cost_per_day: int, loyalty: int, culinary: int, activity: int, friction: int):
    fin = max(1, min(10, round(12 - cost_per_day / 80)))
    ratings = {
        'Financial Efficiency': fin,
        'Loyalty': loyalty,
        'Culinary': culinary,
        'Activity': activity,
        'Friction': friction,
    }
    weighted = {k: ratings[k] * WEIGHTS[k] for k in ratings}
    total = sum(weighted.values())
    return ratings, weighted, total

with st.sidebar:
    st.header('Trip Inputs')
    destination = st.text_input('Destination', 'Barcelona, Spain')
    start = st.date_input('Start date', value=date(2026, 6, 15))
    end = st.date_input('End date', value=date(2026, 6, 22))
    travelers = st.number_input('Travelers', min_value=1, max_value=10, value=2)
    budget_total = st.number_input('Budget total (USD)', min_value=200, value=2800)
    purpose = st.selectbox('Purpose', ['vacation', 'business', 'special occasion'])
    st.markdown('### VQS rating inputs')
    loyalty = st.slider('Loyalty (1-10)', 1, 10, 7)
    culinary = st.slider('Culinary (1-10)', 1, 10, 8)
    activity = st.slider('Activity (1-10)', 1, 10, 7)
    friction = st.slider('Friction (1-10)', 1, 10, 6)

    st.markdown('### LLM settings')
    hf_token = st.text_input('HF_TOKEN', value=os.getenv('HF_TOKEN', ''), type='password')
    model_id = st.text_input('HF_MODEL', value=os.getenv('HF_MODEL', DEFAULT_MODEL))

n_days = max(1, (end - start).days)
cost_per_day = int(budget_total / n_days)
ratings, weighted, vqs = compute_vqs(cost_per_day, loyalty, culinary, activity, friction)
value_score = vqs / max(1, cost_per_day)

st.metric('VQS', f'{vqs} / 190', f'{(vqs/190*100):.1f}% · {tier(vqs)}')
st.metric('Value Score (VQS ÷ $/day)', f'{value_score:.2f} pts/$')

if 'messages' not in st.session_state:
    st.session_state.messages = [{'role': 'assistant', 'content': 'I can build itineraries and travel deliverables. Click Generate Deliverables.'}]

for m in st.session_state.messages:
    with st.chat_message(m['role']):
        st.markdown(m['content'])

user_prompt = st.chat_input('Ask for itinerary updates...')
if user_prompt:
    st.session_state.messages.append({'role': 'user', 'content': user_prompt})
    with st.chat_message('assistant'):
        try:
            client = InferenceClient(token=hf_token or None)
            system = 'You are a travel planner. Keep answers concise and actionable.'
            msgs = [{'role': 'system', 'content': system}] + st.session_state.messages
            out = client.chat.completions.create(model=model_id, messages=msgs, stream=False, max_tokens=700)
            answer = out.choices[0].message.content
        except Exception as exc:
            answer = f'LLM error: {exc}'
        st.markdown(answer)
    st.session_state.messages.append({'role': 'assistant', 'content': answer})

if st.button('Generate Deliverables'):
    dest_slug = slugify(destination.split(',')[0])
    date_slug = start.strftime('%b%Y').lower()

    jsx_path = OUTPUT_DIR / f'{dest_slug}-{date_slug}-vqs-dashboard.jsx'
    html_path = OUTPUT_DIR / f'{dest_slug}-{date_slug}-trip-summary-flyer.html'
    md_path = OUTPUT_DIR / f'{dest_slug}-{date_slug}-travel-plan.md'

    score_rows = '\n'.join([f"<li>{k}: {ratings[k]}/10 × {WEIGHTS[k]} = {weighted[k]}</li>" for k in ratings])

    jsx_path.write_text(f"""import React from 'react';
export default function VQSDashboard() {{
  return (
    <div style={{{{padding: 24, fontFamily: 'Georgia'}}}}>
      <h1>{destination} — VQS {vqs} / 190</h1>
      <p>{tier(vqs)} · Value Score (VQS ÷ $/day): {value_score:.2f} pts/$</p>
      <ul>{''.join([f'<li>{k}: {ratings[k]}/10 × {WEIGHTS[k]} = {weighted[k]}</li>' for k in ratings])}</ul>
    </div>
  );
}}
""")

    html_path.write_text(f"""<!doctype html><html><head><meta charset='utf-8'><title>{destination} summary</title>
<style>body{{font-family: 'Palatino', serif; padding:24px;}} .badge{{font-size:24px;}}</style></head><body>
<h1>{destination}</h1><p>{start} to {end} · {n_days} days · {travelers} travelers</p>
<div class='badge'>{vqs} / 190 · {tier(vqs)}</div>
<p>Value Score (VQS ÷ $/day): {value_score:.2f} pts/$</p>
<h2>Top 3 highlights</h2><ol><li>Historic center walking route</li><li>Local food market and tasting</li><li>Sunset viewpoint + dinner</li></ol>
</body></html>""")

    md_path.write_text(f"""# {destination} Travel Plan

## 1) Trip Overview
- Dates: {start} to {end}
- Duration: {n_days} days
- Travelers: {travelers}
- Budget: ${budget_total}
- Purpose: {purpose}

## 2) Vacation Quality Score (VQS) Analysis
- VQS: **{vqs} / 190 ({(vqs/190*100):.1f}%)**
- Tier: **{tier(vqs)}**
- Value Score (VQS ÷ $/day): **{value_score:.2f} pts/$**

| Category | Rating | Weight | Weighted Score | Notes |
|---|---|---:|---:|---|
| Financial Efficiency | {ratings['Financial Efficiency']}/10 | 5 | {weighted['Financial Efficiency']} | Derived from ${cost_per_day}/day |
| Loyalty | {ratings['Loyalty']}/10 | 4 | {weighted['Loyalty']} | Airline/hotel fit |
| Culinary | {ratings['Culinary']}/10 | 4 | {weighted['Culinary']} | Dining quality |
| Activity | {ratings['Activity']}/10 | 3 | {weighted['Activity']} | Variety + access |
| Friction | {ratings['Friction']}/10 | 3 | {weighted['Friction']} | Transit complexity |

## 3) Day-by-Day Itinerary
- Day 1: Arrival + orientation walk + dinner.
- Day 2: Landmark tour + local neighborhood food crawl.
- Day 3: Museum + market + evening show.

## 4) Budget Breakdown
- Accommodation: 40%
- Food: 25%
- Activities: 15%
- Transportation: 15%
- Misc: 5%

## 5) Packing Checklist
- Passport, adapters, meds, walking shoes, light layers.

## 6) Cultural Do's and Don'ts
- Learn greeting basics, respect quiet hours, book top attractions ahead.

## 7) Pre-Trip Preparation Timeline
- 3 months: passport/visa check
- 1 month: major bookings
- 1 week: documents + weather check

## 8) Practical Information
- Currency, emergency numbers, local transit app, tipping norms.
""")

    st.success('Generated 3 deliverables in /mnt/user-data/outputs')
    st.code(json.dumps({'jsx': str(jsx_path), 'html': str(html_path), 'md': str(md_path)}, indent=2))
