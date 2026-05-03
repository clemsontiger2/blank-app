# Travel Planner + VQS (Hugging Face Space Ready)

This app now focuses on travel planning and generates three required deliverables:

1. `*-vqs-dashboard.jsx`
2. `*-trip-summary-flyer.html`
3. `*-travel-plan.md`

Output directory: `/mnt/user-data/outputs`

## Run

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy

```bash
git remote add space https://huggingface.co/spaces/Clemsontiger2k/PersonalAgent
git push space main
```
