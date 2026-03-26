# -*- coding: utf-8 -*-
"""
jz-wxbot 兼容性综合测试

测试覆盖:
1. Windows版本兼容性 (Windows 10/11)
2. 微信版本兼容性 (个人微信/企业微信)
3. Python版本兼容性 (3.8+)
4. 依赖库兼容性

输出: compatibility-test-report.md
"""

import sys
import os
import platform
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import json

# ============================================================
# 兼容性测试配置
# ============================================================

@dataclass
class CompatibilityConfig:
    """兼容性测试配置"""
    # 支持的Windows版本
    supported_windows_versions = [
        "Windows 10",
        "Windows 11",
        "Windows Server 2019",
        "Windows Server 2022"
    ]
    
    # 支持的Python版本
    supported_python_versions = [
        (3, 8),
        (3, 9),
        (3, 10),
        (3, 11),
        (3, 12),
        (3, 13),
        (3, 14)
    ]
    
    # 支持的微信版本
    wechat_versions = {
        "personal": {
            "min_version": "3.9.0",
            "recommended": "4.1+",
            "process_names": ["WeChat.exe", "Weixin.exe"]
        },
        "work": {
            "min_version": "4.0.0",
            "recommended": "4.1+",
            "process_names": ["WXWork.exe", "WeCom.exe"]
        }
    }
    
    # 必需的依赖库
    required_dependencies = [
        "pyautogui",
        "pyperclip",
        "psutil",
        "win32gui",
        "win32con",
        "win32api",
        "websockets",
        "PyYAML",
        "aiohttp"
    ]
    
    # 可选依赖库
    optional_dependencies = [
        "opencv-python",
        "pillow",
        "numpy"
    ]


CONFIG = CompatibilityConfig()


# ============================================================
# 系统信息收集器
# ============================================================

class SystemInfoCollector:
    """系统信息收集器"""
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
            },
            "python": {
                "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "implementation": platform.python_implementation(),
                "compiler": platform.python_compiler(),
                "build": platform.python_build(),
            },
            "environment": {
                "executable": sys.executable,
                "prefix": sys.prefix,
                "path": sys.path[:5],  # 前5个路径
            }
        }
    
    @staticmethod
    def check_windows_version() -> Tuple[bool, str]:
        """检查Windows版本兼容性"""
        if platform.system() != "Windows":
            return False, "非Windows系统"
        
        version = platform.release()
        
        # Windows 10 或更高版本
        try:
            build_number = int(platform.version().split('.')[-1])
            if build_number >= 10240:  # Windows 10 RTM
                return True, f"Windows 10/11 (Build {build_number})"
            else:
                return False, f"Windows版本过低 (Build {build_number})"
        except:
            return False, f"无法解析Windows版本: {version}"
    
    @staticmethod
    def check_python_version() -> Tuple[bool, str, Tuple[int, int]]:
        """检查Python版本兼容性"""
        current = (sys.version_info.major, sys.version_info.minor)
        
        if current >= (3, 8):
            status = "✅ 支持"
            compatible = True
        else:
            status = "❌ 不支持"
            compatible = False
        
        version_str = f"{current[0]}.{current[1]}.{sys.version_info.micro}"
        return compatible, f"Python {version_str} - {status}", current
    
    @staticmethod
    def check_dependencies() -> Dict[str, Dict[str, Any]]:
        """检查依赖库"""
        results = {}
        
        for dep in CONFIG.required_dependencies + CONFIG.optional_dependencies:
            is_optional = dep in CONFIG.optional_dependencies
            
            try:
                module = __import__(dep.replace("-", "_"))
                version = getattr(module, "__version__", "未知版本")
                results[dep] = {
                    "status": "✅ 已安装",
                    "version": version,
                    "optional": is_optional
                }
            except ImportError:
                results[dep] = {
                    "status": "❌ 未安装" if not is_optional else "⚠️ 未安装（可选）",
                    "version": "N/A",
                    "optional": is_optional
                }
        
        return results


# ============================================================
# 微信兼容性测试
# ============================================================

class WeChatCompatibilityTester:
    """微信兼容性测试器"""
    
    @staticmethod
    def check_wechat_installed() -> Dict[str, Any]:
        """检查微信安装情况"""
        results = {
            "personal": {"installed": False, "version": None, "path": None},
            "work": {"installed": False, "version": None, "path": None}
        }
        
        try:
            # 检查个人微信
            import win32api
            import win32con
            
            # 常见的微信安装路径
            wechat_paths = [
                r"C:\Program Files\Tencent\WeChat\WeChat.exe",
                r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Tencent\WeChat\WeChat.exe"),
            ]
            
            for path in wechat_paths:
                if os.path.exists(path):
                    results["personal"]["installed"] = True
                    results["personal"]["path"] = path
                    try:
                        # 尝试获取版本信息
                        info = win32api.GetFileVersionInfo(path, "\\")
                        version = "%d.%d.%d.%d" % (
                            info['FileVersionMS'] >> 16,
                            info['FileVersionMS'] & 0xFFFF,
                            info['FileVersionLS'] >> 16,
                            info['FileVersionLS'] & 0xFFFF
                        )
                        results["personal"]["version"] = version
                    except:
                        results["personal"]["version"] = "未知"
                    break
            
            # 检查企业微信
            wxwork_paths = [
                r"C:\Program Files\WXWork\WXWork.exe",
                r"C:\Program Files (x86)\WXWork\WXWork.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\WXWork\WXWork.exe"),
            ]
            
            for path in wxwork_paths:
                if os.path.exists(path):
                    results["work"]["installed"] = True
                    results["work"]["path"] = path
                    try:
                        info = win32api.GetFileVersionInfo(path, "\\")
                        version = "%d.%d.%d.%d" % (
                            info['FileVersionMS'] >> 16,
                            info['FileVersionMS'] & 0xFFFF,
                            info['FileVersionLS'] >> 16,
                            info['FileVersionLS'] & 0xFFFF
                        )
                        results["work"]["version"] = version
                    except:
                        results["work"]["version"] = "未知"
                    break
        
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    @staticmethod
    def check_wechat_running() -> Dict[str, Any]:
        """检查微信运行状态"""
        results = {
            "personal": {"running": False, "pid": None},
            "work": {"running": False, "pid": None}
        }
        
        try:
            import psutil
            
            for proc in psutil.process_iter(['pid', 'name']):
                name = proc.info['name'].lower()
                pid = proc.info['pid']
                
                # 个人微信
                if name in ["wechat.exe", "weixin.exe"]:
                    results["personal"]["running"] = True
                    results["personal"]["pid"] = pid
                
                # 企业微信
                if name in ["wxwork.exe", "wecom.exe"]:
                    results["work"]["running"] = True
                    results["work"]["pid"] = pid
        
        except Exception as e:
            results["error"] = str(e)
        
        return results


# ============================================================
# 测试报告生成器
# ============================================================

class CompatibilityReportGenerator:
    """兼容性测试报告生成器"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.results = {
            "system_info": {},
            "windows_compatibility": {},
            "python_compatibility": {},
            "dependencies": {},
            "wechat_compatibility": {},
            "summary": {
                "total_checks": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("jz-wxbot 兼容性测试")
        print("=" * 60)
        print(f"测试时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("")
        
        # 1. 系统信息
        print("[1/5] 收集系统信息...")
        self.results["system_info"] = SystemInfoCollector.get_system_info()
        
        # 2. Windows兼容性
        print("[2/5] 检查Windows兼容性...")
        compatible, message = SystemInfoCollector.check_windows_version()
        self.results["windows_compatibility"] = {
            "compatible": compatible,
            "message": message,
            "details": self.results["system_info"]["platform"]
        }
        self._update_summary(compatible)
        
        # 3. Python兼容性
        print("[3/5] 检查Python兼容性...")
        compatible, message, version = SystemInfoCollector.check_python_version()
        self.results["python_compatibility"] = {
            "compatible": compatible,
            "message": message,
            "version": version,
            "supported_versions": CONFIG.supported_python_versions
        }
        self._update_summary(compatible)
        
        # 4. 依赖库检查
        print("[4/5] 检查依赖库...")
        self.results["dependencies"] = SystemInfoCollector.check_dependencies()
        for dep, info in self.results["dependencies"].items():
            if info["optional"]:
                if "未安装" in info["status"]:
                    self.results["summary"]["warnings"] += 1
                else:
                    self.results["summary"]["passed"] += 1
            else:
                self._update_summary("✅" in info["status"])
        
        # 5. 微信兼容性
        print("[5/5] 检查微信兼容性...")
        installed = WeChatCompatibilityTester.check_wechat_installed()
        running = WeChatCompatibilityTester.check_wechat_running()
        
        self.results["wechat_compatibility"] = {
            "installed": installed,
            "running": running
        }
        
        # 更新摘要
        if installed["personal"]["installed"] or installed["work"]["installed"]:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["warnings"] += 1
        
        print("")
        print("测试完成！")
    
    def _update_summary(self, passed: bool):
        """更新摘要"""
        self.results["summary"]["total_checks"] += 1
        if passed:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1
    
    def generate_markdown_report(self) -> str:
        """生成Markdown报告"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        report = []
        report.append("# 兼容性测试报告 - jz-wxbot")
        report.append("")
        report.append(f"**生成时间**: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**测试时长**: {duration:.2f}秒")
        report.append("")
        
        # 测试概要
        report.append("## 测试概要")
        report.append("")
        summary = self.results["summary"]
        report.append(f"| 项目 | 数量 |")
        report.append(f"|------|------|")
        report.append(f"| 总检查数 | {summary['total_checks'] + summary['warnings']} |")
        report.append(f"| 通过 | {summary['passed']} |")
        report.append(f"| 失败 | {summary['failed']} |")
        report.append(f"| 警告 | {summary['warnings']} |")
        
        pass_rate = (summary['passed'] / summary['total_checks'] * 100) if summary['total_checks'] > 0 else 0
        report.append(f"| **通过率** | **{pass_rate:.1f}%** |")
        report.append("")
        
        # 系统信息
        report.append("## 1. 系统信息")
        report.append("")
        sys_info = self.results["system_info"]
        report.append("### 平台信息")
        report.append("")
        report.append(f"| 项目 | 值 |")
        report.append(f"|------|-----|")
        for key, value in sys_info["platform"].items():
            report.append(f"| {key} | {value} |")
        report.append("")
        
        report.append("### Python信息")
        report.append("")
        report.append(f"| 项目 | 值 |")
        report.append(f"|------|-----|")
        for key, value in sys_info["python"].items():
            if key == "path":
                report.append(f"| {key} | {', '.join(value)} |")
            else:
                report.append(f"| {key} | {value} |")
        report.append("")
        
        # Windows兼容性
        report.append("## 2. Windows兼容性")
        report.append("")
        win_compat = self.results["windows_compatibility"]
        status = "✅ 兼容" if win_compat["compatible"] else "❌ 不兼容"
        report.append(f"**状态**: {status}")
        report.append(f"**信息**: {win_compat['message']}")
        report.append("")
        
        # Python兼容性
        report.append("## 3. Python兼容性")
        report.append("")
        py_compat = self.results["python_compatibility"]
        status = "✅ 兼容" if py_compat["compatible"] else "❌ 不兼容"
        report.append(f"**状态**: {status}")
        report.append(f"**信息**: {py_compat['message']}")
        report.append("")
        report.append("**支持的Python版本**:")
        report.append("")
        supported = ", ".join([f"{v[0]}.{v[1]}" for v in py_compat["supported_versions"]])
        report.append(f"- {supported}")
        report.append("")
        
        # 依赖库
        report.append("## 4. 依赖库状态")
        report.append("")
        report.append("### 必需依赖")
        report.append("")
        report.append("| 库名 | 状态 | 版本 |")
        report.append("|------|------|------|")
        
        for dep, info in self.results["dependencies"].items():
            if not info["optional"]:
                report.append(f"| {dep} | {info['status']} | {info['version']} |")
        report.append("")
        
        report.append("### 可选依赖")
        report.append("")
        report.append("| 库名 | 状态 | 版本 |")
        report.append("|------|------|------|")
        
        for dep, info in self.results["dependencies"].items():
            if info["optional"]:
                report.append(f"| {dep} | {info['status']} | {info['version']} |")
        report.append("")
        
        # 微信兼容性
        report.append("## 5. 微信兼容性")
        report.append("")
        wechat = self.results["wechat_compatibility"]
        
        report.append("### 个人微信")
        report.append("")
        personal = wechat["installed"]["personal"]
        if personal["installed"]:
            report.append(f"- **状态**: ✅ 已安装")
            report.append(f"- **版本**: {personal['version']}")
            report.append(f"- **路径**: {personal['path']}")
        else:
            report.append(f"- **状态**: ❌ 未安装")
        report.append("")
        
        running = wechat["running"]["personal"]
        if running["running"]:
            report.append(f"- **运行状态**: ✅ 运行中 (PID: {running['pid']})")
        else:
            report.append(f"- **运行状态**: ⏸️ 未运行")
        report.append("")
        
        report.append("### 企业微信")
        report.append("")
        work = wechat["installed"]["work"]
        if work["installed"]:
            report.append(f"- **状态**: ✅ 已安装")
            report.append(f"- **版本**: {work['version']}")
            report.append(f"- **路径**: {work['path']}")
        else:
            report.append(f"- **状态**: ❌ 未安装")
        report.append("")
        
        running = wechat["running"]["work"]
        if running["running"]:
            report.append(f"- **运行状态**: ✅ 运行中 (PID: {running['pid']})")
        else:
            report.append(f"- **运行状态**: ⏸️ 未运行")
        report.append("")
        
        # 兼容性问题
        if summary['failed'] > 0 or summary['warnings'] > 0:
            report.append("## 6. 兼容性问题")
            report.append("")
            
            if not self.results["windows_compatibility"]["compatible"]:
                report.append("### Windows版本问题")
                report.append(f"- {self.results['windows_compatibility']['message']}")
                report.append("")
            
            if not self.results["python_compatibility"]["compatible"]:
                report.append("### Python版本问题")
                report.append(f"- {self.results['python_compatibility']['message']}")
                report.append("")
            
            missing_deps = [dep for dep, info in self.results["dependencies"].items() 
                          if "未安装" in info["status"] and not info["optional"]]
            if missing_deps:
                report.append("### 缺失依赖")
                report.append("以下必需依赖库未安装:")
                for dep in missing_deps:
                    report.append(f"- {dep}")
                report.append("")
        
        # 建议
        report.append("## 7. 建议")
        report.append("")
        
        if summary['failed'] > 0:
            report.append("### 必需修复")
            report.append("1. 升级或安装缺失的依赖库")
            report.append("2. 确保Windows版本符合要求")
            report.append("3. 安装支持的Python版本")
            report.append("")
        
        if summary['warnings'] > 0:
            report.append("### 可选优化")
            report.append("1. 安装微信客户端（个人版或企业版）")
            report.append("2. 安装可选依赖库以获得更好的体验")
            report.append("")
        
        report.append("---")
        report.append("*自动生成的兼容性测试报告*")
        
        return '\n'.join(report)
    
    def save_report(self, filepath: str):
        """保存报告"""
        markdown = self.generate_markdown_report()
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)
        print(f"\n报告已保存: {filepath}")
        return markdown


# ============================================================
# 主程序
# ============================================================

def main():
    """主函数"""
    report = CompatibilityReportGenerator()
    report.run_all_tests()
    
    # 保存报告
    output_path = r"I:\jz-wxbot-automation\docs\compatibility-test-report.md"
    report.save_report(output_path)


if __name__ == "__main__":
    main()