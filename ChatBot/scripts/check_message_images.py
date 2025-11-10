"""
Check messages in MongoDB for images
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.mongodb_config import get_db
from datetime import datetime

def check_messages():
    db = get_db()
    
    print("=" * 80)
    print("🔍 CHECKING MESSAGES COLLECTION FOR IMAGES")
    print("=" * 80)
    
    # Count total messages
    total_messages = db.messages.count_documents({})
    print(f"\n📊 Total messages: {total_messages}")
    
    # Count messages with images
    messages_with_images = db.messages.count_documents({"images": {"$exists": True, "$ne": []}})
    print(f"🖼️  Messages with images field (non-empty): {messages_with_images}")
    
    # Get recent messages
    print("\n" + "=" * 80)
    print("📝 RECENT MESSAGES (Last 10)")
    print("=" * 80)
    
    recent_messages = list(db.messages.find().sort("created_at", -1).limit(10))
    
    for idx, msg in enumerate(recent_messages, 1):
        print(f"\n{idx}. Message ID: {msg['_id']}")
        print(f"   Conversation: {msg.get('conversation_id')}")
        print(f"   Role: {msg.get('role')}")
        print(f"   Content: {msg.get('content', '')[:60]}...")
        print(f"   Created: {msg.get('created_at')}")
        
        # Check images
        images = msg.get('images', [])
        print(f"   Images: {len(images)} items")
        
        if images:
            for img_idx, img in enumerate(images, 1):
                print(f"\n   📷 Image {img_idx}:")
                print(f"      - URL: {img.get('url', 'N/A')}")
                print(f"      - Cloud URL: {img.get('cloud_url', 'N/A')}")
                print(f"      - Delete URL: {img.get('delete_url', 'N/A')}")
                print(f"      - Service: {img.get('service', 'N/A')}")
                print(f"      - Generated: {img.get('generated', False)}")
                print(f"      - Caption: {img.get('caption', 'N/A')[:50]}")
        else:
            print(f"      ⚠️ No images in this message")
        
        # Check metadata
        metadata = msg.get('metadata', {})
        if metadata:
            print(f"   Metadata: model={metadata.get('model')}, cloud_service={metadata.get('cloud_service')}")
    
    # Search for messages with cloud_url
    print("\n" + "=" * 80)
    print("🌐 MESSAGES WITH CLOUD URLs")
    print("=" * 80)
    
    cloud_messages = list(db.messages.find({"images.cloud_url": {"$exists": True}}))
    print(f"\nFound {len(cloud_messages)} messages with cloud_url field")
    
    for msg in cloud_messages[:5]:  # Show first 5
        print(f"\n✅ Message: {msg['_id']}")
        for img in msg.get('images', []):
            if img.get('cloud_url'):
                print(f"   🌐 Cloud URL: {img['cloud_url']}")
                print(f"   📁 Local URL: {img.get('url')}")
    
    # Check if any messages have images array but empty
    print("\n" + "=" * 80)
    print("⚠️  MESSAGES WITH EMPTY IMAGES ARRAY")
    print("=" * 80)
    
    empty_images = db.messages.count_documents({"images": []})
    print(f"\nMessages with empty images array: {empty_images}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Total messages: {total_messages}")
    print(f"Messages with images (non-empty): {messages_with_images}")
    print(f"Messages with cloud URLs: {len(cloud_messages)}")
    print(f"Messages with empty images: {empty_images}")
    print("=" * 80)

if __name__ == "__main__":
    check_messages()
