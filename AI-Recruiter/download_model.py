from sentence_transformers import SentenceTransformer
import sys
import os

def main():
    print("Downloading all-MiniLM-L6-v2...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    target_path = r"c:\Users\HARSHIT MENDIRATTA\OneDrive\Desktop\Hackwars-1\India-runs Hack\AI-Recruiter\models\all-MiniLM-L6-v2"
    os.makedirs(target_path, exist_ok=True)
    
    print(f"Saving model to {target_path}...")
    model.save(target_path)
    print("Model downloaded and saved successfully!")

if __name__ == "__main__":
    main()
