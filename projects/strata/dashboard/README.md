# STRATA Dashboard

Run the lightweight dashboard against CSVs in `outputs/`:

```bash
pip install -e ".[dashboard]"
streamlit run dashboard/app.py
```

The dashboard reads benchmark CSV outputs and exposes quick box plots and tables.
