import pandas as pd
from vyom.preprocessing import normalize_columns, make_text

def test_aliases_and_text():
    df = normalize_columns(pd.DataFrame([{'Narration':'Paid supplier','Amount':100}]))
    assert 'transaction_narration' in df.columns
    assert 'transaction narration: Paid supplier' in make_text(df.iloc[0])
