#!/usr/bin/env python3
"""
AI 협상 시뮬레이터 서버 실행 스크립트
FastAPI 서버를 백그라운드에서 실행하고 Streamlit 앱을 시작합니다.
"""

import subprocess
import time
import sys
import os
import signal
import requests
from pathlib import Path

# 프로젝트 루트 디렉토리 설정
PROJECT_ROOT = Path(__file__).parent
API_DIR = PROJECT_ROOT / "api"
APP_DIR = PROJECT_ROOT / "app"

# 서버 설정
API_HOST = "127.0.0.1"
API_PORT = 8000
STREAMLIT_PORT = 8501

def check_dependencies():
    """필요한 패키지가 설치되어 있는지 확인"""
    required_packages = ['fastapi', 'uvicorn', 'streamlit', 'requests']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 다음 패키지들이 설치되지 않았습니다: {', '.join(missing_packages)}")
        print("💡 다음 명령어로 설치하세요:")
        print("   pip install -r requirements.txt")
        return False
    
    return True

def check_file_structure():
    """파일 구조가 올바른지 확인"""
    required_files = [
        API_DIR / "main.py",
        API_DIR / "logic.py",
        APP_DIR / "streamlit_ui.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not file_path.exists():
            missing_files.append(str(file_path))
    
    if missing_files:
        print(f"❌ 다음 파일들이 없습니다: {', '.join(missing_files)}")
        return False
    
    return True

def is_port_in_use(port):
    """포트가 사용 중인지 확인"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex(('127.0.0.1', port))
        return result == 0

def wait_for_server(host, port, timeout=30):
    """서버가 시작될 때까지 대기"""
    print(f"🔄 서버 시작 대기 중... ({host}:{port})")
    
    for i in range(timeout):
        try:
            response = requests.get(f"http://{host}:{port}/health", timeout=1)
            if response.status_code == 200:
                print("✅ 서버가 성공적으로 시작되었습니다!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(1)
        if i % 5 == 0:
            print(f"   대기 중... ({i}/{timeout}초)")
    
    print("❌ 서버 시작 타임아웃")
    return False

def start_api_server():
    """FastAPI 서버 시작"""
    print("🚀 FastAPI 서버 시작 중...")
    
    # 포트 확인
    if is_port_in_use(API_PORT):
        print(f"⚠️  포트 {API_PORT}이 이미 사용 중입니다.")
        response = input("기존 서버를 종료하고 계속하시겠습니까? (y/N): ")
        if response.lower() != 'y':
            return None
        
        # 기존 프로세스 종료 시도
        try:
            subprocess.run(["pkill", "-f", "uvicorn.*main:app"], check=False)
            time.sleep(2)
        except:
            pass
    
    # 서버 시작
    cmd = [
        sys.executable, "-m", "uvicorn",
        "api.main:app",
        "--host", API_HOST,
        "--port", str(API_PORT),
        "--reload"
    ]
    
    try:
        # 백그라운드에서 실행
        process = subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 서버 시작 대기
        if wait_for_server(API_HOST, API_PORT):
            return process
        else:
            process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ API 서버 시작 실패: {str(e)}")
        return None

def start_streamlit_app():
    """Streamlit 앱 시작"""
    print("🎨 Streamlit 앱 시작 중...")
    
    # 포트 확인
    if is_port_in_use(STREAMLIT_PORT):
        print(f"⚠️  포트 {STREAMLIT_PORT}이 이미 사용 중입니다.")
        response = input("기존 앱을 종료하고 계속하시겠습니까? (y/N): ")
        if response.lower() != 'y':
            return None
    
    cmd = [
        sys.executable, "-m", "streamlit",
        "run", str(APP_DIR / "streamlit_ui.py"),
        "--server.port", str(STREAMLIT_PORT),
        "--server.address", "127.0.0.1",
        "--browser.gatherUsageStats", "false"
    ]
    
    try:
        # Streamlit은 포그라운드에서 실행
        process = subprocess.Popen(cmd, cwd=PROJECT_ROOT)
        return process
        
    except Exception as e:
        print(f"❌ Streamlit 앱 시작 실패: {str(e)}")
        return None

def cleanup_processes(*processes):
    """프로세스 정리"""
    print("\n🛑 서버 종료 중...")
    
    for process in processes:
        if process and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except:
                pass
    
    print("✅ 모든 프로세스가 종료되었습니다.")

def main():
    """메인 실행 함수"""
    print("🤝 AI 협상 시뮬레이터 시작")
    print("=" * 50)
    
    # 사전 검사
    if not check_dependencies():
        sys.exit(1)
    
    if not check_file_structure():
        sys.exit(1)
    
    api_process = None
    streamlit_process = None
    
    try:
        # API 서버 시작
        api_process = start_api_server()
        if not api_process:
            print("❌ API 서버 시작에 실패했습니다.")
            sys.exit(1)
        
        print(f"✅ API 서버: http://{API_HOST}:{API_PORT}")
        
        # Streamlit 앱 시작
        streamlit_process = start_streamlit_app()
        if not streamlit_process:
            print("❌ Streamlit 앱 시작에 실패했습니다.")
            cleanup_processes(api_process)
            sys.exit(1)
        
        print(f"✅ Streamlit 앱: http://127.0.0.1:{STREAMLIT_PORT}")
        print("\n🎉 시스템이 성공적으로 시작되었습니다!")
        print("📱 브라우저에서 Streamlit 주소로 접속하세요.")
        print("⏹️  종료하려면 Ctrl+C를 누르세요.")
        
        # 메인 프로세스 대기
        try:
            streamlit_process.wait()
        except KeyboardInterrupt:
            print("\n⏹️  사용자가 종료를 요청했습니다.")
    
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {str(e)}")
    
    finally:
        cleanup_processes(api_process, streamlit_process)

if __name__ == "__main__":
    main()