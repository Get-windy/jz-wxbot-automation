# -*- coding: utf-8 -*-
"""
pywechat Module Integration Test
Test Config and Exceptions module integration
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.wechat_config import GlobalConfig, WeChatConfig
from core.exceptions import (
    WeChatError,
    WeChatNotStartError,
    NoSuchFriendError,
    ElementNotFoundError,
    TimeoutError,
    EmptyFileError,
    NotFileError,
    NotFolderError,
    NotFriendError,
    NoGroupsError,
    NoPermissionError,
    NoChatHistoryError,
    TimeNotCorrectError,
    get_error_by_code,
    ERROR_CODE_MAP,
)


def test_config_singleton():
    print("\n[TEST 1] Config Singleton")
    
    config1 = GlobalConfig
    config2 = GlobalConfig
    
    assert config1 is config2, "Singleton test failed"
    print("[PASS] Singleton pattern works")
    
    assert config1.is_maximize == False
    assert config1.close_wechat == True
    assert config1.load_delay == 3.5
    print("[PASS] Default values correct")


def test_config_properties():
    print("\n[TEST 2] Config Properties")
    
    config = GlobalConfig
    
    config.is_maximize = True
    assert config.is_maximize == True
    
    config.close_wechat = False
    assert config.close_wechat == False
    
    config.load_delay = 2.5
    assert config.load_delay == 2.5
    
    config.search_pages = 10
    assert config.search_pages == 10
    
    config.send_delay = 0.5
    assert config.send_delay == 0.5
    
    config.window_size = (1920, 1080)
    assert config.window_size == (1920, 1080)
    
    # Reset defaults
    config.is_maximize = False
    config.close_wechat = True
    config.load_delay = 3.5
    config.search_pages = 5
    config.send_delay = 0.2
    config.window_size = (1000, 800)
    
    print("[PASS] Property read/write")


def test_config_type_validation():
    print("\n[TEST 3] Type Validation")
    
    config = GlobalConfig
    
    try:
        config.is_maximize = "yes"
        raise AssertionError("Should raise TypeError")
    except TypeError as e:
        print(f"[PASS] Bool type validation: {type(e).__name__}")
    
    try:
        config.load_delay = "slow"
        raise AssertionError("Should raise TypeError")
    except TypeError as e:
        print(f"[PASS] Number type validation: {type(e).__name__}")
    
    try:
        config.window_size = [1000, 800]
        raise AssertionError("Should raise TypeError")
    except TypeError as e:
        print(f"[PASS] Tuple type validation: {type(e).__name__}")


def test_config_to_dict():
    print("\n[TEST 4] Config Export/Import")
    
    config = GlobalConfig
    
    config.is_maximize = True
    config.load_delay = 2.0
    config.retry_count = 5
    
    config_dict = config.to_dict()
    print(f"[INFO] Exported config keys: {list(config_dict.keys())}")
    
    original = config.is_maximize
    
    config.reset()
    assert config.is_maximize == False
    
    config.from_dict(config_dict)
    assert config.is_maximize == True
    assert config.load_delay == 2.0
    assert config.retry_count == 5
    
    config.is_maximize = original
    
    print("[PASS] Export/Import works")


def test_exceptions_hierarchy():
    print("\n[TEST 5] Exception Hierarchy")
    
    assert issubclass(WeChatNotStartError, WeChatError)
    assert issubclass(NoSuchFriendError, WeChatError)
    assert issubclass(ElementNotFoundError, WeChatError)
    
    print("[PASS] Exception inheritance")
    
    e = WeChatNotStartError()
    assert len(str(e)) > 0
    
    e = NoSuchFriendError("custom message")
    assert "custom message" in str(e)
    
    print("[PASS] Exception messages")


def test_exceptions_raise():
    print("\n[TEST 6] Exception Raising")
    
    try:
        raise WeChatNotStartError()
    except WeChatError as e:
        print(f"[PASS] Caught WeChatNotStartError: {type(e).__name__}")
    
    try:
        raise NoSuchFriendError()
    except WeChatError as e:
        print(f"[PASS] Caught NoSuchFriendError: {type(e).__name__}")
    
    try:
        raise EmptyFileError()
    except WeChatError as e:
        print(f"[PASS] Caught EmptyFileError: {type(e).__name__}")


def test_error_code_map():
    print("\n[TEST 7] Error Code Map")
    
    error_class = get_error_by_code('WECHAT_NOT_START')
    assert error_class == WeChatNotStartError
    
    error_class = get_error_by_code('NO_SUCH_FRIEND')
    assert error_class == NoSuchFriendError
    
    error_class = get_error_by_code('UNKNOWN_ERROR')
    assert error_class == WeChatError
    
    print("[PASS] Error code mapping works")
    print(f"[INFO] Total error codes: {len(ERROR_CODE_MAP)}")


def test_independent_config():
    print("\n[TEST 8] Independent Config Instance")
    
    # WeChatConfig uses singleton pattern
    config1 = WeChatConfig()
    config2 = WeChatConfig()
    
    # They should be the same instance (singleton)
    assert config1 is config2
    assert config1 is GlobalConfig
    
    print("[PASS] Singleton behavior confirmed")


def run_all_tests():
    print("=" * 50)
    print("pywechat Module Integration Test")
    print("=" * 50)
    
    try:
        test_config_singleton()
        test_config_properties()
        test_config_type_validation()
        test_config_to_dict()
        test_exceptions_hierarchy()
        test_exceptions_raise()
        test_error_code_map()
        test_independent_config()
        
        print("\n" + "=" * 50)
        print("[SUCCESS] All tests passed!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)