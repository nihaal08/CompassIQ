import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import and run training
from CompassIQ.train_model import train_and_save_all_models

if __name__ == "__main__":
    print("Retraining models with CORRECTED dataset (812 login tickets relabeled)...")
    metrics = train_and_save_all_models()
    print("\nTraining completed successfully!")
    print(f"Category accuracy: {metrics['category']['accuracy']:.4f}")
    print(f"Priority accuracy: {metrics['priority']['accuracy']:.4f}")
    print(f"Category macro F1: {metrics['category']['macro_f1']:.4f}")
    print(f"Priority macro F1: {metrics['priority']['macro_f1']:.4f}")
