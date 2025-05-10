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
import pymysql
import webbrowser
import requests  # 코드 상단에 추가

DB_CONFIG = {
    'host': '172.30.1.41',
    'user': 'root',
    'password': 'PEURUSEU',
    'db': 'lockerdb',
    'charset': 'utf8mb4'
}

ADMIN_PASSWORD = "020115"
CURRENT_VERSION = "2.0"  # 이 값을 새 exe를 배포할 때마다 변경하세요

def save_user_info(student_id, pw, hint, timer_min):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = pymysql.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute(
        "INSERT INTO user_info (created_at, student_id, password, timer_min, hint) VALUES (%s, %s, %s, %s, %s)",
        (now, student_id, pw, timer_min, hint)
    )
    conn.commit()
    conn.close()

def load_user_info():
    conn = pymysql.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute("SELECT password, timer_min FROM user_info ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    if row:
        return row[0], row[1]
    return None, None

def load_hint():
    conn = pymysql.connect(**DB_CONFIG)
    c = conn.cursor()
    c.execute("SELECT hint FROM user_info ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]
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
        self.attributes("-fullscreen", True)  # 화면 보호 시작 시 전체화면
        self.attributes("-topmost", True)
        self.configure(bg="black")
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        # 날짜/시간 라벨 (중앙 위)
        self.datetime_label = tk.Label(
            self,
            text="",
            font=("맑은 고딕", 40, "bold"),
            fg="white",
            bg="black"
        )
        self.datetime_label.place(relx=0.5, rely=0.18, anchor="center")

        # 전원 버튼 (우측 상단)
        self.power_button = tk.Menubutton(
            self,
            text="?",  # 전원 아이콘
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

        # 타이머 라벨 (중앙)
        self.timer_label = tk.Label(self, text="", font=("맑은 고딕", 20), fg="white", bg="black")
        self.timer_label.place(relx=0.5, rely=0.38, anchor="center")

        # 비밀번호 입력 칸 (중앙)
        self.pw_entry = tk.Entry(self, show="*", font=("맑은 고딕", 20), width=18, justify="center")
        self.pw_entry.place(relx=0.5, rely=0.60, anchor="center")
        self.pw_entry.focus()

        # 힌트 라벨 (비밀번호 입력 칸 바로 아래)
        self.hint_label = tk.Label(self, text="", font=("맑은 고딕", 18), fg="gray", bg="black")
        self.hint_label.place(relx=0.5, rely=0.68, anchor="center")

        # 도움말 버튼 (우측 하단)
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
            # 비밀번호 틀리면 힌트 표시
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

    # 학번
    tk.Label(root, text="학번 :", font=font_label).place(x=40, y=30)
    entry_id = tk.Entry(root, font=font_entry, width=20)
    entry_id.place(x=220, y=30)

    # 비밀번호
    tk.Label(root, text="비밀번호:", font=font_label).place(x=40, y=80)
    entry_pw = tk.Entry(root, font=font_entry, show="*", width=20)
    entry_pw.place(x=220, y=80)

    # 힌트
    tk.Label(root, text="비밀번호 힌트(선택) :", font=font_label).place(x=40, y=130)
    entry_hint = tk.Entry(root, font=font_entry, width=20)
    entry_hint.place(x=220, y=130)

    # 타이머
    tk.Label(root, text="타이머(분, 1~60분 사이) :", font=font_label).place(x=40, y=180)
    entry_timer = tk.Entry(root, font=font_entry, width=20)
    entry_timer.place(x=220, y=180)

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
        root.destroy()
        root.quit()

    def on_cancel():
        root.destroy()
        sys.exit(0)  # 프로그램 완전 종료

    root.protocol("WM_DELETE_WINDOW", on_cancel)  # 창 닫기(X) 버튼도 완전 종료
    btn_ok = tk.Button(root, text="OK", font=font_btn, width=8, command=on_ok)
    btn_ok.place(x=150, y=230)
    btn_cancel = tk.Button(root, text="Cancel", font=font_btn, width=8, command=on_cancel)
    btn_cancel.place(x=270, y=230)

    root.mainloop()
    return True

def check_update():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        c = conn.cursor()
        c.execute("SELECT version, download_url FROM program_update ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        if row:
            latest_version, download_url = row
            if latest_version != CURRENT_VERSION:
                # 자동 다운로드
                save_path = os.path.join(os.path.dirname(sys.argv[0]), f"locker_gui_v{latest_version}.exe")
                try:
                    response = requests.get(download_url, stream=True)
                    with open(save_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    messagebox.showinfo("업데이트 완료", f"최신 버전({latest_version})이 자동으로 다운로드 되었습니다.\n{save_path} 파일을 실행해 주세요.")
                except Exception as e:
                    messagebox.showerror("다운로드 오류", str(e))
                sys.exit(0)  # 구버전은 실행하지 않고 종료
    except Exception as e:
        messagebox.showerror("업데이트 확인 오류", str(e))

if __name__ == "__main__":
    check_update()
    if not setup_user():
        sys.exit(0)
    user_pw, timer_min = load_user_info()
    hint = load_hint()
    app = LockScreen(user_pw, hint, timer_min)
    app.mainloop()

