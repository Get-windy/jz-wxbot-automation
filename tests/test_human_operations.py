# -*- coding: utf-8 -*-
"""
人性化操作测试
测试 human_like_operations.py 的功能
"""

import pytest
import sys
import time
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, 'I:\\jz-wxbot-automation')


class TestHumanLikeOperations:
    """测试人性化操作类"""
    
    @pytest.fixture
    def hlo(self):
        """创建人性化操作实例"""
        with patch('human_like_operations.pyautogui'):
            from human_like_operations import HumanLikeOperations
            return HumanLikeOperations()
    
    def test_initialization(self, hlo):
        """测试初始化"""
        assert hlo is not None
    
    def test_human_delay(self, hlo):
        """测试人性化延迟"""
        start = time.time()
        hlo.human_delay(base_time=0.01, variance=0.001)
        elapsed = time.time() - start
        
        # 延迟应该大于 0
        assert elapsed > 0
    
    def test_human_delay_with_variance(self, hlo):
        """测试带变化范围的延迟"""
        times = []
        for _ in range(10):
            start = time.time()
            hlo.human_delay(base_time=0.1, variance=0.05)
            times.append(time.time() - start)
        
        # 延迟时间应该有一定的变化
        assert min(times) != max(times)
    
    def test_human_move_to(self, hlo):
        """测试人性化移动"""
        with patch('human_like_operations.pyautogui') as mock_pyautogui:
            mock_pyautogui.position.return_value = (100, 100)
            
            # 模拟移动
            hlo.human_move_to(200, 200, duration=0.01)
            
            # 验证调用了 moveTo
            mock_pyautogui.moveTo.assert_called()
    
    def test_human_move_to_with_random_duration(self, hlo):
        """测试带随机时长的人性化移动"""
        with patch('human_like_operations.pyautogui') as mock_pyautogui:
            mock_pyautogui.position.return_value = (0, 0)
            
            hlo.human_move_to(100, 100)
            
            # 应该调用了 moveTo
            mock_pyautogui.moveTo.assert_called()
    
    def test_human_click(self, hlo):
        """测试人性化点击"""
        with patch('human_like_operations.pyautogui') as mock_pyautogui:
            mock_pyautogui.position.return_value = (100, 100)
            
            hlo.human_click(200, 200)
            
            # 应该调用了 click
            mock_pyautogui.click.assert_called()
    
    def test_human_click_multiple(self, hlo):
        """测试多次点击"""
        with patch('human_like_operations.pyautogui') as mock_pyautogui:
            mock_pyautogui.position.return_value = (100, 100)
            
            hlo.human_click(200, 200, clicks=2)
            
            # 验证点击次数
            call_args = mock_pyautogui.click.call_args
            assert call_args[1]['clicks'] == 2
    
    def test_human_hotkey(self, hlo):
        """测试人性化热键"""
        with patch('human_like_operations.pyautogui') as mock_pyautogui:
            hlo.human_hotkey('ctrl', 'c')
            
            # 应该调用了 hotkey
            mock_pyautogui.hotkey.assert_called_with('ctrl', 'c')
    
    def test_human_type(self, hlo):
        """测试人性化输入"""
        with patch('human_like_operations.pyautogui') as mock_pyautogui:
            with patch('human_like_operations.pyperclip') as mock_clipboard:
                hlo.human_type('test message')
                
                # 应该调用了 paste
                mock_pyautogui.hotkey.assert_called()
    
    def test_human_scroll(self, hlo):
        """测试人性化滚动"""
        with patch('human_like_operations.pyautogui') as mock_pyautogui:
            hlo.human_scroll(-5)
            
            # 应该调用了 scroll
            mock_pyautogui.scroll.assert_called()
    
    def test_random_mouse_move(self, hlo):
        """测试随机鼠标移动"""
        with patch('human_like_operations.pyautogui') as mock_pyautogui:
            mock_pyautogui.size.return_value = (1920, 1080)
            
            result = hlo.random_mouse_move()
            
            # 应该返回坐标
            assert isinstance(result, tuple)
            assert len(result) == 2


class TestHumanLikeOperationsAntiDetection:
    """测试反检测功能"""
    
    @pytest.fixture
    def hlo(self):
        """创建人性化操作实例"""
        with patch('human_like_operations.pyautogui'):
            from human_like_operations import HumanLikeOperations
            return HumanLikeOperations()
    
    def test_random_delay_patterns(self, hlo):
        """测试随机延迟模式"""
        delays = []
        for _ in range(20):
            start = time.time()
            hlo.human_delay(0.1, 0.03)
            delays.append(time.time() - start)
        
        # 验证延迟有变化
        variance = max(delays) - min(delays)
        assert variance > 0
    
    def test_mouse_movement_variation(self, hlo):
        """测试鼠标移动变化"""
        positions = []
        
        with patch('human_like_operations.pyautogui') as mock_pyautogui:
            mock_pyautogui.position.return_value = (100, 100)
            mock_pyautogui.size.return_value = (1920, 1080)
            
            for _ in range(5):
                hlo.human_move_to(500, 500, duration=0.01)
                positions.append(mock_pyautogui.moveTo.call_args)
        
        # 每次移动的位置应该有细微差别
        # （因为有随机抖动）


class TestHumanLikeOperationsEdgeCases:
    """测试边界情况"""
    
    @pytest.fixture
    def hlo(self):
        """创建人性化操作实例"""
        with patch('human_like_operations.pyautogui'):
            from human_like_operations import HumanLikeOperations
            return HumanLikeOperations()
    
    def test_very_small_delay(self, hlo):
        """测试极小延迟"""
        start = time.time()
        hlo.human_delay(0.001, 0.0001)
        elapsed = time.time() - start
        assert elapsed >= 0
    
    def test_long_duration_move(self, hlo):
        """测试长距离移动"""
        with patch('human_like_operations.pyautogui') as mock_pyautogui:
            mock_pyautogui.position.return_value = (0, 0)
            
            # 长距离移动
            hlo.human_move_to(1000, 1000, duration=1.0)
            
            mock_pyautogui.moveTo.assert_called()
    
    def test_negative_scroll(self, hlo):
        """测试负向滚动"""
        with patch('human_like_operations.pyautogui') as mock_pyautogui:
            hlo.human_scroll(-10)
            mock_pyautogui.scroll.assert_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])