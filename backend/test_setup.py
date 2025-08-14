#!/usr/bin/env python3
"""
Quick test to verify database and config are working properly
Run this to make sure everything is set up correctly before proceeding
"""

def test_imports():
    """Test if all imports work"""
    print("Testing imports...")
    try:
        import config
        print("✅ Config import successful")
        
        from database import User, VerificationSession, init_database, SessionLocal
        print("✅ Database imports successful")
        
        import os
        from dotenv import load_dotenv
        print("✅ Environment imports successful")
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    return True


def test_environment():
    """Test environment variables"""
    print("\nTesting environment variables...")
    try:
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        
        db_url = os.getenv("DB_URL")
        encryption_key = os.getenv("ENCRYPTION_KEY")
        secret_key = os.getenv("SECRET_KEY")
        
        if db_url and encryption_key and secret_key:
            print("✅ All environment variables loaded")
            print(f"   DB_URL: {db_url}")
            print(f"   Keys loaded: {len(encryption_key) if encryption_key else 0} chars encryption, {len(secret_key) if secret_key else 0} chars secret")
            return True
        else:
            print("❌ Missing environment variables")
            return False
            
    except Exception as e:
        print(f"❌ Environment test failed: {e}")
        return False


def test_database():
    """Test database operations"""
    print("\nTesting database operations...")
    try:
        from database import init_database, SessionLocal, User
        
        # Initialize database
        init_database()
        print("✅ Database tables created")
        
        # Test basic database operation
        db = SessionLocal()
        
        # Create a test user
        test_user = User(
            email="test@example.com",
            full_name="Test User"
        )
        
        db.add(test_user)
        db.commit()
        print("✅ Test user created")
        
        # Query the user back
        user = db.query(User).filter(User.email == "test@example.com").first()
        if user:
            print(f"✅ Test user retrieved: {user.full_name}")
        else:
            print("❌ Could not retrieve test user")
            return False
            
        # Clean up
        db.delete(user)
        db.commit()
        db.close()
        print("✅ Test user cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🔍 Testing Biometric Project Setup")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Environment", test_environment), 
        ("Database", test_database)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        if test_func():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Tests Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Your setup is ready.")
        print("Next step: Implement core services (OCR, Liveness, Face Matching)")
    else:
        print("⚠️  Some tests failed. Fix the issues before proceeding.")


if __name__ == "__main__":
    main()