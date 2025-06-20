#!/usr/bin/env python3
"""
Demo script showing how to use the FastAPI ChromaDB API.

This script demonstrates:
1. Creating documents
2. Searching documents
3. Updating documents
4. Listing documents
5. Deleting documents
"""

import requests
import json
from typing import Dict, List

# API base URL
BASE_URL = "http://localhost:8000/api/v1"


def check_health() -> bool:
    """Check if the API is healthy."""
    try:
        response = requests.get("http://localhost:8000/health")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def create_document(doc_id: str, content: str, metadata: Dict = None) -> Dict:
    """Create a new document."""
    data = {
        "id": doc_id,
        "content": content,
        "metadata": metadata or {}
    }
    response = requests.post(f"{BASE_URL}/documents", json=data)
    response.raise_for_status()
    return response.json()


def get_document(doc_id: str) -> Dict:
    """Get a document by ID."""
    response = requests.get(f"{BASE_URL}/documents/{doc_id}")
    response.raise_for_status()
    return response.json()


def update_document(doc_id: str, content: str = None, metadata: Dict = None) -> Dict:
    """Update an existing document."""
    data = {}
    if content is not None:
        data["content"] = content
    if metadata is not None:
        data["metadata"] = metadata
    
    response = requests.put(f"{BASE_URL}/documents/{doc_id}", json=data)
    response.raise_for_status()
    return response.json()


def search_documents(query: str, n_results: int = 5) -> Dict:
    """Search for similar documents."""
    data = {
        "query_text": query,
        "n_results": n_results
    }
    response = requests.post(f"{BASE_URL}/documents/search", json=data)
    response.raise_for_status()
    return response.json()


def list_documents(limit: int = 10, offset: int = 0) -> Dict:
    """List all documents with pagination."""
    params = {"limit": limit, "offset": offset}
    response = requests.get(f"{BASE_URL}/documents", params=params)
    response.raise_for_status()
    return response.json()


def delete_document(doc_id: str) -> Dict:
    """Delete a document."""
    response = requests.delete(f"{BASE_URL}/documents/{doc_id}")
    response.raise_for_status()
    return response.json()


def main():
    """Run the demo."""
    print("FastAPI ChromaDB API Demo")
    print("=" * 50)
    
    # Check health
    print("\n1. Checking API health...")
    if not check_health():
        print("❌ API is not running. Please start the server first.")
        print("   Run: python -m src.main")
        return
    print("✅ API is healthy")
    
    # Create documents
    print("\n2. Creating sample documents...")
    documents = [
        {
            "id": "doc_ai_intro",
            "content": "Artificial Intelligence (AI) is the simulation of human intelligence in machines that are programmed to think and learn like humans.",
            "metadata": {"category": "AI", "level": "beginner", "author": "Demo"}
        },
        {
            "id": "doc_ml_basics",
            "content": "Machine Learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed.",
            "metadata": {"category": "ML", "level": "beginner", "author": "Demo"}
        },
        {
            "id": "doc_dl_neural",
            "content": "Deep Learning uses neural networks with multiple layers to progressively extract higher-level features from raw input.",
            "metadata": {"category": "DL", "level": "intermediate", "author": "Demo"}
        },
        {
            "id": "doc_nlp_transformers",
            "content": "Transformers revolutionized NLP by introducing self-attention mechanisms, enabling models like BERT and GPT to understand context better.",
            "metadata": {"category": "NLP", "level": "advanced", "author": "Demo"}
        }
    ]
    
    for doc in documents:
        try:
            result = create_document(doc["id"], doc["content"], doc["metadata"])
            print(f"✅ Created: {doc['id']}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                print(f"⚠️  Document {doc['id']} already exists")
            else:
                print(f"❌ Failed to create {doc['id']}: {e}")
    
    # Search documents
    print("\n3. Searching for documents about 'neural networks'...")
    search_results = search_documents("neural networks and deep learning", n_results=3)
    print(f"Found {len(search_results['ids'])} relevant documents:")
    for i, (doc_id, content, distance) in enumerate(zip(
        search_results['ids'], 
        search_results['documents'], 
        search_results['distances']
    )):
        print(f"  {i+1}. ID: {doc_id} (distance: {distance:.3f})")
        print(f"     Content: {content[:100]}...")
    
    # Update a document
    print("\n4. Updating a document...")
    try:
        update_result = update_document(
            "doc_ai_intro",
            metadata={"category": "AI", "level": "beginner", "author": "Demo", "updated": True}
        )
        print(f"✅ Updated document: {update_result['id']}")
    except Exception as e:
        print(f"❌ Failed to update: {e}")
    
    # List documents
    print("\n5. Listing all documents...")
    doc_list = list_documents(limit=5)
    print(f"Total documents: {doc_list['total']}")
    print("Documents:")
    for doc in doc_list['documents']:
        print(f"  - {doc['id']}: {doc['content'][:60]}...")
    
    # Get specific document
    print("\n6. Getting specific document...")
    try:
        doc = get_document("doc_ml_basics")
        print(f"Document ID: {doc['id']}")
        print(f"Content: {doc['content']}")
        print(f"Metadata: {json.dumps(doc['metadata'], indent=2)}")
    except Exception as e:
        print(f"❌ Failed to get document: {e}")
    
    # Cleanup (optional)
    print("\n7. Cleanup (press Enter to delete all demo documents, or Ctrl+C to keep them)")
    try:
        input()
        for doc in documents:
            try:
                delete_document(doc["id"])
                print(f"✅ Deleted: {doc['id']}")
            except Exception as e:
                print(f"❌ Failed to delete {doc['id']}: {e}")
    except KeyboardInterrupt:
        print("\n✅ Demo documents kept in database")
    
    print("\n✅ Demo completed!")


if __name__ == "__main__":
    main()