from pathlib import Path
p=Path('d:/GitHub/projects/strata/paper/submission_jmlr/manuscript_draft.tex')
s=p.read_text(encoding='utf-8')
# Fix common malformed sequences introduced earlier
s=s.replace('\\$\\approx\\$','$\\approx$')
s=s.replace('\\\\$\\approx\\\\$','$\\approx$')
s=s.replace('3\\\\times','$3\\times$')
s=s.replace('3\\\times','$3\\times$')
s=s.replace('~3\\\times','$3\\times$')
s=s.replace('~3\\times','$3\\times$')
# Also fix sequences with extra backslashes
s=s.replace('\\\\approx','\\approx')
# Ensure end{abstract} is on its own line
s=s.replace(') at roughly $3\\times$ training cost; other CHMP variants primarily redistribute width spatially.\\end{abstract}',') at roughly $3\\times$ training cost; other CHMP variants primarily redistribute width spatially.\n\\end{abstract}')
# Write back
p.write_text(s,encoding='utf-8')
print('patched')
