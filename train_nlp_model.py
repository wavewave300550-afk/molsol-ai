import json
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.multioutput import MultiOutputClassifier

def main():
    print("🤖 Preparing Dataset for MolSol NLP Core...")
    
    # Dataset structure: (text, intent, objective, receptor)
    data = [
        # Conversational
        ("hello", "conversation", "None", "None"),
        ("hi there", "conversation", "None", "None"),
        ("how are you?", "conversation", "None", "None"),
        ("what is your name?", "conversation", "None", "None"),
        ("who are you?", "conversation", "None", "None"),
        ("help me", "conversation", "None", "None"),
        ("can you design drugs?", "conversation", "None", "None"),
        ("what can you do?", "conversation", "None", "None"),
        
        # Design - Solubility
        ("i need a highly soluble compound", "design", "Maximize Solubility", "None"),
        ("design something that dissolves well in water", "design", "Maximize Solubility", "None"),
        ("make it very soluble", "design", "Maximize Solubility", "None"),
        ("water solubility is important", "design", "Maximize Solubility", "None"),
        ("optimize for logS", "design", "Maximize Solubility", "None"),
        
        # Design - Toxicity
        ("make a deadly poison", "design", "Maximize Toxicity", "None"),
        ("i want something highly toxic", "design", "Maximize Toxicity", "None"),
        ("design a lethal molecule", "design", "Maximize Toxicity", "None"),
        ("maximize toxicity", "design", "Maximize Toxicity", "None"),
        ("create a toxic compound", "design", "Maximize Toxicity", "None"),
        
        # Design - Safe Drug
        ("design a safe drug", "design", "Create Best Drug (Multi-Objective)", "None"),
        ("i need a safe medicine", "design", "Create Best Drug (Multi-Objective)", "None"),
        ("optimize for safety and drug-likeness", "design", "Create Best Drug (Multi-Objective)", "None"),
        ("make a viable drug candidate", "design", "Create Best Drug (Multi-Objective)", "None"),
        ("best drug", "design", "Create Best Drug (Multi-Objective)", "None"),
        
        # Design - Receptors
        ("soluble kinase inhibitor", "design", "Maximize Solubility", "🦠 Kinase (มะเร็ง/อักเสบ)"),
        ("target kinase and make it safe", "design", "Create Best Drug (Multi-Objective)", "🦠 Kinase (มะเร็ง/อักเสบ)"),
        ("find a gpcr ligand", "design", "Create Best Drug (Multi-Objective)", "🧠 GPCR (ระบบประสาท/หัวใจ)"),
        ("soluble gpcr target", "design", "Maximize Solubility", "🧠 GPCR (ระบบประสาท/หัวใจ)"),
        ("toxic protease inhibitor", "design", "Maximize Toxicity", "🛡️ Protease (ไวรัส/แบคทีเรีย)"),
        ("safe drug for virus protease", "design", "Create Best Drug (Multi-Objective)", "🛡️ Protease (ไวรัส/แบคทีเรีย)"),
        ("protease drug", "design", "Create Best Drug (Multi-Objective)", "🛡️ Protease (ไวรัส/แบคทีเรีย)"),
        ("kinase poison", "design", "Maximize Toxicity", "🦠 Kinase (มะเร็ง/อักเสบ)"),
    ]
    
    # Unpack data
    X = [item[0] for item in data]
    y_intent = [item[1] for item in data]
    y_obj = [item[2] for item in data]
    y_receptor = [item[3] for item in data]
    
    # Combine Y into a structured array for MultiOutputClassifier
    # Actually, simpler to just train 3 separate pipelines or one MultiOutput.
    # Let's train 3 separate models in a dictionary to be safe.
    
    model_dict = {}
    
    print("🧠 Training Intent Classifier...")
    pipe_intent = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1,2))),
        ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
    ])
    pipe_intent.fit(X, y_intent)
    model_dict['intent'] = pipe_intent
    
    print("🧠 Training Objective Classifier...")
    pipe_obj = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1,2))),
        ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
    ])
    pipe_obj.fit(X, y_obj)
    model_dict['objective'] = pipe_obj
    
    print("🧠 Training Receptor Classifier...")
    pipe_receptor = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1,2))),
        ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
    ])
    pipe_receptor.fit(X, y_receptor)
    model_dict['receptor'] = pipe_receptor
    
    # Test
    test_phrase = "give me a safe gpcr drug"
    print(f"\n🧪 Testing phrase: '{test_phrase}'")
    print(f"Intent: {pipe_intent.predict([test_phrase])[0]}")
    print(f"Objective: {pipe_obj.predict([test_phrase])[0]}")
    print(f"Receptor: {pipe_receptor.predict([test_phrase])[0]}")
    
    # Save
    save_path = "nlp_intent_model.pkl"
    with open(save_path, "wb") as f:
        pickle.dump(model_dict, f)
        
    print(f"✅ NLP Model saved to {save_path}!")

if __name__ == "__main__":
    main()
