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

DB_CONFIG = {
    'host': '172.30.1.41',
    'user': 'root',
    'password': 'PEURUSEU',
    'db': 'lockerdb',
    'charset': 'utf8mb4'
}

ADMIN_PASSWORD = "020115"
CURRENT_VERSION = "1.0"  # 이 값을 새 exe를 배포할 때마다 변경하세요

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
    root.geometry("800x400") 
    root.resizable(False, False)
    root.withdraw()
    # 1. 학번 입력
    student_id = simpledialog.askstring("자리 예약", "학번을 입력하세요:")
    if not student_id:
        root.destroy()
        return False
    # 2. 비밀번호 입력
    pw = simpledialog.askstring("자리 예약", "사용자 비밀번호를 입력하세요:", show="*")
    if not pw:
        root.destroy()
        return False
    # 3. 힌트 입력
    hint = simpledialog.askstring("자리 예약", "비밀번호 힌트를 입력하세요 (선택):")
    # 4. 타이머 입력
    timer_min = simpledialog.askinteger("자리 예약", "타이머(분)를 입력하세요:", minvalue=1, maxvalue=60)
    if not timer_min:
        root.destroy()
        return False
    save_user_info(student_id, pw, hint or "", timer_min)
    messagebox.showinfo("설정 완료", "비밀번호와 타이머가 저장되었습니다.")
    root.destroy()
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
                if messagebox.askyesno("업데이트 안내", f"최신 버전({latest_version})이 있습니다.\n지금 다운로드 하시겠습니까?"):
                    webbrowser.open(download_url)
                else:
                    messagebox.showinfo("알림", "계속해서 현재 버전으로 실행합니다.")
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

