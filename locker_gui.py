# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import simpledialog, messagebox
import time
import threading
import os
import datetime
import sys
import subprocess
import ctypes
import webbrowser
import requests
import platform
import shutil

ADMIN_PASSWORD = "020115"
CURRENT_VERSION = "1.0.0"  # 이 값을 새 exe를 배포할 때마다 변경하세요
API_SERVER = "http://172.30.1.41:8888" #테스트 실행 할 땐 내부망 : http://172.30.1.41:8888 / 배포할 땐 외부망 : http://118.44.154.168:8888

def save_user_info(student_id, pw, hint, timer_min):
    url = f"{API_SERVER}/save_user"
    data = {
        "student_id": student_id,
        "password": pw,
        "hint": hint,
        "timer_min": timer_min
    }
    try:
        response = requests.post(url, json=data, timeout=5)
        if response.ok and response.json().get("result") == "ok":
            return True
        else:
            print("API 오류:", response.text)
            return False
    except Exception as e:
        print("API 서버 연결 오류:", e)
        return False

def load_user_info(student_id):
    url = f"{API_SERVER}/get_user"
    try:
        response = requests.post(url, json={"student_id": student_id}, timeout=5)
        if response.ok and response.json().get("result") == "ok":
            user = response.json().get("user")
            return user["password"], user["hint"], user["timer_min"]
        else:
            print("사용자 정보 조회 실패:", response.text)
            return None, None, None
    except Exception as e:
        print("API 서버 연결 오류:", e)
        return None, None, None

def load_hint():
    # 서버에 hint 조회용 API를 추가해야 함
    # 임시로 빈 문자열 반환
    return ""

class LockScreen(tk.Tk):
    def __init__(self, user_pw, hint, timer_min):
        super().__init__()
        self.user_pw = user_pw
        self.hint = hint
        self.timer_min = timer_min
        self.remaining = timer_min * 60
        self.unlocked = False

        self.title("자리 예약")
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.configure(bg="black")
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        self.datetime_label = tk.Label(
            self,
            text="",
            font=("맑은 고딕", 40, "bold"),
            fg="white",
            bg="black"
        )
        self.datetime_label.place(relx=0.5, rely=0.18, anchor="center")

        self.power_button = tk.Menubutton(
            self,
            text="?",
            font=("맑은 고딕", 24, "bold"),
            fg="white",
            bg="#222222",
            activebackground="#444444",
            activeforeground="white",
            relief="flat"
        )
        self.power_menu = tk.Menu(self.power_button, tearoff=0, font=("맑은 고딕", 14))
        self.power_menu.add_command(label="다시 시작", command=self.restart_system)
        self.power_menu.add_command(label="시스템 종료", command=self.shutdown_system)
        self.power_button.config(menu=self.power_menu)
        self.power_button.place(relx=0.98, rely=0.02, anchor="ne")

        self.timer_label = tk.Label(self, text="", font=("맑은 고딕", 20), fg="white", bg="black")
        self.timer_label.place(relx=0.5, rely=0.38, anchor="center")

        self.pw_entry = tk.Entry(self, show="*", font=("맑은 고딕", 20), width=18, justify="center")
        self.pw_entry.place(relx=0.5, rely=0.60, anchor="center")
        self.pw_entry.focus()

        self.hint_label = tk.Label(self, text="", font=("맑은 고딕", 18), fg="gray", bg="black")
        self.hint_label.place(relx=0.5, rely=0.68, anchor="center")

        self.help_button = tk.Button(
            self,
            text="도움말",
            font=("맑은 고딕", 14, "bold"),
            fg="white",
            bg="#444444",
            activebackground="#666666",
            activeforeground="white",
            command=self.show_help
        )
        self.help_button.place(relx=0.98, rely=0.98, anchor="se")

        self.pw_entry.bind("<Return>", self.check_password)

        self.update_datetime()
        self.update_timer()
        self.lock_thread = threading.Thread(target=self.timer_countdown, daemon=True)
        self.lock_thread.start()

    def update_datetime(self):
        now = datetime.datetime.now()
        weekday = ["월", "화", "수", "목", "금", "토", "일"][now.weekday()]
        datetime_str = now.strftime(f"%Y-%m-%d (%a) %H:%M:%S").replace(now.strftime("%a"), weekday)
        self.datetime_label.config(text=datetime_str)
        if not self.unlocked:
            self.after(1000, self.update_datetime)

    def update_timer(self):
        min_, sec = divmod(self.remaining, 60)
        self.timer_label.config(text=f"남은 시간: {min_}분 {sec:02d}초")
        if not self.unlocked and self.remaining > 0:
            self.after(1000, self.update_timer)

    def timer_countdown(self):
        while self.remaining > 0 and not self.unlocked:
            time.sleep(1)
            self.remaining -= 1
        if not self.unlocked:
            self.unlocked = True
            self.after(0, self.unlock_screen, "타이머 만료로 자동 해제되었습니다.")

    def check_password(self, event=None):
        pw = self.pw_entry.get()
        if pw == self.user_pw:
            self.unlocked = True
            self.unlock_screen("비밀번호가 맞습니다. 잠금 해제!")
        elif pw == ADMIN_PASSWORD:
            self.unlocked = True
            self.unlock_screen("관리자 권한으로 잠금 해제!")
        else:
            self.hint_label.config(text=self.hint)
            messagebox.showerror("오류", "비밀번호가 틀렸습니다.")
            self.pw_entry.delete(0, tk.END)

    def unlock_screen(self, msg):
        messagebox.showinfo("잠금 해제", msg)
        self.destroy()

    def on_focus_out(self, event):
        if not self.unlocked:
            self.after(100, self.restore_focus)

    def restore_focus(self):
        try:
            self.focus_force()
            self.pw_entry.focus_set()
        except:
            pass

    def show_help(self):
        messagebox.showinfo("도움말", "관리자 : 010-9903-5655")

    def restart_system(self):
        if messagebox.askyesno("다시 시작", "시스템을 다시 시작하시겠습니까?"):
            try:
                subprocess.Popen("shutdown /r /t 0", shell=True)
                self.destroy()
            except Exception as e:
                messagebox.showerror("오류", f"다시 시작 실패: {e}")

    def shutdown_system(self):
        if messagebox.askyesno("시스템 종료", "시스템을 종료하시겠습니까?"):
            try:
                subprocess.Popen("shutdown /s /t 0", shell=True)
                self.destroy()
            except Exception as e:
                messagebox.showerror("오류", f"시스템 종료 실패: {e}")

def setup_user():
    root = tk.Tk()
    root.title("자리 예약")
    root.geometry("530x300")
    root.resizable(False, False)

    font_label = ("맑은 고딕", 10, "bold")
    font_entry = ("맑은 고딕", 10, "bold")
    font_btn = ("맑은 고딕", 14, "bold")

    tk.Label(root, text="학번 :", font=font_label).place(x=40, y=30)
    entry_id = tk.Entry(root, font=font_entry, width=20)
    entry_id.place(x=220, y=30)

    def only_numeric(event):
        value = entry_id.get()
        if not value.isdigit():
            entry_id.delete(0, tk.END)
            entry_id.insert(0, ''.join(filter(str.isdigit, value)))

    entry_id.bind("<KeyRelease>", only_numeric)

    tk.Label(root, text="비밀번호:", font=font_label).place(x=40, y=80)
    entry_pw = tk.Entry(root, font=font_entry, show="*", width=20)
    entry_pw.place(x=220, y=80)

    tk.Label(root, text="비밀번호 힌트(선택) :", font=font_label).place(x=40, y=130)
    entry_hint = tk.Entry(root, font=font_entry, width=20)
    entry_hint.place(x=220, y=130)

    tk.Label(root, text="타이머(분, 1~60분 사이) :", font=font_label).place(x=40, y=180)
    entry_timer = tk.Entry(root, font=font_entry, width=20)
    entry_timer.place(x=220, y=180)

    def only_timer_numeric(event):
        value = entry_timer.get()
        if not value.isdigit():
            entry_timer.delete(0, tk.END)
            entry_timer.insert(0, ''.join(filter(str.isdigit, value)))

    entry_timer.bind("<KeyRelease>", only_timer_numeric)

    # 결과 저장용 딕셔너리
    result = {}

    def on_ok():
        student_id = entry_id.get().strip()
        pw = entry_pw.get().strip()
        hint = entry_hint.get().strip()
        try:
            timer_min = int(entry_timer.get().strip())
        except:
            timer_min = 0

        if not student_id:
            messagebox.showwarning("입력 오류", "학번을 입력하세요.", parent=root)
            return
        if not pw:
            messagebox.showwarning("입력 오류", "비밀번호를 입력하세요.", parent=root)
            return
        if not (1 <= timer_min <= 60):
            messagebox.showwarning("입력 오류", "타이머는 1~60 사이의 숫자여야 합니다.", parent=root)
            return

        save_user_info(student_id, pw, hint, timer_min)
        messagebox.showinfo("설정 완료", "비밀번호와 타이머가 저장되었습니다.", parent=root)
        # 값 저장
        result["student_id"] = student_id
        result["pw"] = pw
        result["hint"] = hint
        result["timer_min"] = timer_min
        root.destroy()
        root.quit()

    def on_cancel():
        root.destroy()
        sys.exit(0)

    root.protocol("WM_DELETE_WINDOW", on_cancel)
    btn_ok = tk.Button(root, text="OK", font=font_btn, width=8, command=on_ok)
    btn_ok.place(x=150, y=230)
    btn_cancel = tk.Button(root, text="Cancel", font=font_btn, width=8, command=on_cancel)
    btn_cancel.place(x=270, y=230)

    root.mainloop()
    # Entry에서 읽지 말고 result에서 반환
    return result.get("student_id"), result.get("pw"), result.get("hint"), result.get("timer_min")

def check_update():
    url = f"{API_SERVER}/check_update"
    try:
        response = requests.get(url, timeout=5)
        if response.ok:
            data = response.json()
            latest_version = data.get("latest_version")
            download_url = data.get("download_url")
            if latest_version and latest_version != CURRENT_VERSION:
                # 사용자에게 묻지 않고 바로 업데이트
                download_and_replace(download_url)
        else:
            print("업데이트 서버 오류:", response.text)
    except Exception as e:
        print("업데이트 서버 연결 오류:", e)

def download_and_replace(download_url):
    try:
        import requests
        exe_path = sys.argv[0]
        tmp_path = exe_path + ".new"
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        # 윈도우에서는 실행 중인 파일을 바로 교체할 수 없으므로 안내만
        messagebox.showinfo("업데이트 완료", "새 버전이 다운로드되었습니다.\n프로그램을 재시작해 주세요.")
    except Exception as e:
        messagebox.showerror("업데이트 실패", f"다운로드 오류: {e}")

def allow_mariadb_port():
    if platform.system() == "Windows":
        try:
            subprocess.run(
                [
                    "netsh", "advfirewall", "firewall", "add", "rule",
                    "name=locker", "dir=in", "action=allow",
                    "protocol=TCP", "localport=3306"
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            pass

if __name__ == "__main__":
    allow_mariadb_port()
    check_update()  # 자동 업데이트 확인
    student_id, user_pw, hint, timer_min = setup_user()
    app = LockScreen(user_pw, hint, timer_min)
    app.mainloop()

