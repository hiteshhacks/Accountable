"""Rebuild the exploratory baseline from the provisional review workbook.
This reproduces the current exploratory training approach; it is not a gold-standard training recipe.
"""
from pathlib import Path
import argparse, json, pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from vyom.preprocessing import make_text

ROOT = Path(__file__).resolve().parents[2]
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--dataset', default=str(ROOT/'data/synthetic/synthetic_voucher_dataset_v5_review_ready.xlsx'))
    ap.add_argument('--comparison', default=str(ROOT/'data/synthetic/VYOM_plus_reviewer_comparison_adjudication.xlsx'))
    ap.add_argument('--output', default=str(ROOT/'models/vyom_plus_tfidf_baseline_model.pkl'))
    args=ap.parse_args()
    queue=pd.read_excel(args.dataset,sheet_name='human_review_queue')
    pc=pd.read_excel(args.comparison,sheet_name='Provisional_Consensus')
    pc['queue_row_index']=pc['review_case_id'].str.extract(r'HR-(\d+)').astype(int)-1
    meta=queue.reset_index().rename(columns={'index':'queue_row_index'})
    pc=pc.merge(meta[['queue_row_index','split_group']],on='queue_row_index',how='left',validate='one_to_one')
    pc['text_input']=pc.apply(make_text,axis=1)
    pc['target']=pc['provisional_consensus_label'].astype(str).str.strip()
    pc=pc[(pc.target!='') & pc.split_group.notna() & (pc.text_input.str.len()>0)].copy()
    ix=np.arange(len(pc)); groups=pc.split_group.astype(str).to_numpy()
    trv,te=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42).split(ix,pc.target,groups))
    temp=pc.iloc[trv]
    tr,va=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=43).split(np.arange(len(temp)),temp.target,temp.split_group))
    train_df=temp.iloc[tr]; val=temp.iloc[va]; test=pc.iloc[te]
    model=Pipeline([('features',FeatureUnion([('word',TfidfVectorizer(analyzer='word',ngram_range=(1,2),sublinear_tf=True,max_features=100000)),('char',TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),sublinear_tf=True,max_features=100000))])),('clf',LogisticRegression(max_iter=3000,class_weight='balanced',C=2.0,random_state=42))])
    model.fit(train_df.text_input,train_df.target)
    vp=model.predict(val.text_input); tp=model.predict(test.text_input)
    metrics={'n_train':len(train_df),'n_validation':len(val),'n_test':len(test),'classes_in_model':len(model.classes_),'validation_accuracy':accuracy_score(val.target,vp),'validation_macro_f1':f1_score(val.target,vp,average='macro',zero_division=0),'test_accuracy':accuracy_score(test.target,tp),'test_macro_f1':f1_score(test.target,tp,average='macro',zero_division=0),'test_weighted_f1':f1_score(test.target,tp,average='weighted',zero_division=0),'warning':'Exploratory only: provisional labels, synthetic data, incomplete class coverage.'}
    print(json.dumps(metrics,indent=2))
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('wb') as f: pickle.dump(model,f)
    (ROOT/'reports'/'retrained_baseline_metrics.json').write_text(json.dumps(metrics,indent=2))
if __name__=='__main__': main()
