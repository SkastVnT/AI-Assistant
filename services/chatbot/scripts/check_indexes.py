"""
Quick script to check all MongoDB indexes
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.mongodb_config import get_db

def check_indexes():
    db = get_db()
    
    collections = [
        'conversations',
        'messages', 
        'chatbot_memory',
        'uploaded_files',
        'users',
        'user_settings'
    ]
    
    print("=" * 60)
    print("📊 MONGODB INDEXES CHECK")
    print("=" * 60)
    
    for coll_name in collections:
        print(f"\n📦 Collection: {coll_name}")
        print("-" * 60)
        
        indexes = list(db[coll_name].list_indexes())
        
        for idx in indexes:
            name = idx['name']
            keys = idx.get('key', {})
            unique = idx.get('unique', False)
            sparse = idx.get('sparse', False)
            
            # Format keys
            key_str = ', '.join([f"{k}: {v}" for k, v in keys.items()])
            
            # Status
            status = "✅"
            if unique:
                status += " [UNIQUE]"
            if sparse:
                status += " [SPARSE]"
            
            print(f"  {status} {name}")
            print(f"      Keys: {{{key_str}}}")
        
        print(f"\n  Total indexes: {len(indexes)}")
    
    print("\n" + "=" * 60)
    print("✅ Index check complete!")
    print("=" * 60)

if __name__ == "__main__":
    check_indexes()
