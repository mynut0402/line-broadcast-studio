import json
import os
import random
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

import requests


FLEX_IMAGES = [
    "https://img2.pic.in.th/highcompress_ChatGPT-Image-9-..-2569-14_52_56.jpeg",
    "https://img2.pic.in.th/highcompress_photo_2026-05-06_19-10-27de15435b46424406.jpg",
    "https://img1.pic.in.th/images/highcompress_ChatGPT-Image-9-..-2569-21_37_10-3.jpeg",
    "https://img2.pic.in.th/photo_--_--d5cf6643ec8d8097.jpg",
]

COLORS = {
    "bg": "#0B1020",
    "surface": "#131A2E",
    "surface_alt": "#192238",
    "border": "#263451",
    "text": "#F3F6FC",
    "muted": "#91A0BB",
    "accent": "#35C46A",
    "accent_hover": "#2AAD5B",
    "danger": "#FF6B6B",
    "input": "#0E1528",
}

SOURCE_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", SOURCE_DIR))
APP_DATA_DIR = Path(os.getenv("APPDATA", Path.home())) / "LINE Broadcast Studio"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
TOKEN_STORE = APP_DATA_DIR / "line_tokens.json"
SETTINGS_STORE = APP_DATA_DIR / "cloudflare_settings.json"
LEGACY_TOKEN_STORE = SOURCE_DIR / "line_tokens.json"
LEGACY_SETTINGS_STORE = SOURCE_DIR / "cloudflare_settings.json"
ICON_PATH = RESOURCE_DIR / "1.ico"
VERSION_PATH = RESOURCE_DIR / "version.txt"
GITHUB_REPOSITORY = "mynut0402/line-broadcast-studio"
GITHUB_LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
UPDATE_ASSET_NAME = "LINE Broadcast Studio.exe"
saved_tokens = []
update_check_running = False
DEFAULT_BROADCAST_MESSAGE = "สิทธิพิเศษระดับ SVIP สำหรับคุณ คืนยอดเสียทันที"


def read_app_version():
    try:
        return VERSION_PATH.read_text(encoding="utf-8").strip() or "1.0.0"
    except OSError:
        return "1.0.0"


APP_VERSION = read_app_version()


def get_flex_payload(chat_id, image_url, broadcast_message):
    broadcast_message = broadcast_message.strip() or DEFAULT_BROADCAST_MESSAGE
    return {
        "to": chat_id,
        "messages": [{
            "type": "flex",
            "altText": broadcast_message,
            "contents": {
                "type": "carousel",
                "contents": [{
                    "type": "bubble",
                    "size": "giga",
                    "hero": {
                        "type": "image", "size": "full", "aspectRatio": "1:1",
                        "url": image_url, "aspectMode": "cover", "animated": True,
                        "action": {"type": "uri", "label": "action", "uri": "https://startupwin.toppestrich.com/customer/regi/SVIP2"},
                    },
                    "body": {
                        "type": "box", "layout": "vertical", "spacing": "none",
                        "paddingAll": "none",
                        "background": {"type": "linearGradient", "angle": "0deg", "endColor": "#000000", "startColor": "#000000"},
                        "contents": [
                            {"type": "image", "url": "https://img1.pic.in.th/images/animatedd4a83a3c6dd34890.png", "size": "full", "aspectRatio": "12:4", "aspectMode": "cover", "animated": True, "action": {"type": "uri", "label": "action", "uri": "https://startupwin.toppestrich.com/customer/regi/SVIP2"}},
                            {"type": "box", "layout": "vertical", "contents": [{"type": "image", "url": "https://img1.pic.in.th/images/animatedda556ac6c52a2f36.png", "size": "full", "aspectRatio": "10:2.5", "aspectMode": "cover", "animated": True, "action": {"type": "uri", "label": "action", "uri": "https://startupwin.toppestrich.com/customer/regi/SVIP2"}}]},
                        ],
                    },
                    "footer": {
                        "type": "box", "layout": "vertical", "backgroundColor": "#000000",
                        "contents": [{"type": "image", "url": "https://img1.pic.in.th/images/animated51cc56b7f1c5575e.png", "animated": True, "size": "full", "aspectRatio": "10:3", "backgroundColor": "#000000", "aspectMode": "cover", "action": {"type": "uri", "label": "action", "uri": "https://lin.ee/qSH8sIV"}}],
                    },
                }],
            },
        }],
    }


def ui_call(callback, *args, **kwargs):
    root.after(0, lambda: callback(*args, **kwargs))


def add_log(message, tag=None):
    def write():
        txt_log.configure(state="normal")
        txt_log.insert(tk.END, message + "\n", tag)
        txt_log.see(tk.END)
        txt_log.configure(state="disabled")

    ui_call(write)


def set_running(running):
    def update():
        btn_start.configure(state="disabled" if running else "normal")
        status_dot.configure(fg=COLORS["accent"] if running else COLORS["muted"])
        status_text.configure(text="กำลังส่งข้อความ..." if running else "พร้อมเริ่มงาน")

    ui_call(update)


def version_tuple(version):
    numbers = re.findall(r"\d+", version.lstrip("vV"))
    return tuple(int(number) for number in numbers[:4]) or (0,)


def set_update_button(text=None, enabled=True):
    def update():
        btn_update.configure(
            text=text or f"v{APP_VERSION}  •  ตรวจอัปเดต",
            state="normal" if enabled else "disabled",
        )

    ui_call(update)


def check_for_updates(silent=False):
    global update_check_running
    if update_check_running:
        return
    update_check_running = True
    set_update_button("กำลังตรวจอัปเดต...", False)
    threading.Thread(target=check_update_worker, args=(silent,), daemon=True).start()


def check_update_worker(silent):
    global update_check_running
    update_offered = False
    try:
        response = requests.get(
            GITHUB_LATEST_RELEASE_API,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "LINE-Broadcast-Studio-Updater",
            },
            timeout=15,
        )
        if response.status_code == 404:
            if not silent:
                ui_call(messagebox.showinfo, "ยังไม่มี Release", "ยังไม่พบ Release ใน GitHub repository")
            return
        response.raise_for_status()
        release = response.json()
        latest_version = str(release.get("tag_name", "0.0.0")).lstrip("vV")
        if version_tuple(latest_version) <= version_tuple(APP_VERSION):
            if not silent:
                ui_call(messagebox.showinfo, "เป็นเวอร์ชันล่าสุดแล้ว", f"ขณะนี้ใช้เวอร์ชัน {APP_VERSION}")
            return

        assets = release.get("assets", [])
        asset = next((item for item in assets if item.get("name") == UPDATE_ASSET_NAME), None)
        if asset is None:
            asset = next((item for item in assets if str(item.get("name", "")).lower().endswith(".exe")), None)
        if asset is None:
            if not silent:
                ui_call(messagebox.showwarning, "ไม่พบไฟล์อัปเดต", f"Release v{latest_version} ไม่มีไฟล์ .exe")
            return
        update_offered = True
        ui_call(offer_update, latest_version, asset["browser_download_url"])
    except (requests.RequestException, ValueError) as error:
        if not silent:
            ui_call(messagebox.showerror, "ตรวจอัปเดตไม่สำเร็จ", str(error))
    finally:
        update_check_running = False
        if not update_offered:
            set_update_button()


def offer_update(latest_version, download_url):
    accepted = messagebox.askyesno(
        "มีเวอร์ชันใหม่",
        f"พบ LINE Broadcast Studio v{latest_version}\n"
        f"เวอร์ชันปัจจุบันคือ v{APP_VERSION}\n\n"
        "ดาวน์โหลดและติดตั้งตอนนี้หรือไม่?",
    )
    if not accepted:
        set_update_button()
        return
    if not getattr(sys, "frozen", False):
        messagebox.showinfo("โหมดพัฒนา", "ระบบติดตั้งอัตโนมัติทำงานเมื่อเปิดจากไฟล์ .exe เท่านั้น")
        set_update_button()
        return
    set_update_button("กำลังดาวน์โหลด...", False)
    threading.Thread(
        target=download_update_worker,
        args=(latest_version, download_url),
        daemon=True,
    ).start()


def download_update_worker(latest_version, download_url):
    download_path = APP_DATA_DIR / f"LINE-Broadcast-Studio-{latest_version}.download"
    try:
        with requests.get(
            download_url,
            headers={"User-Agent": "LINE-Broadcast-Studio-Updater"},
            stream=True,
            timeout=60,
        ) as response:
            response.raise_for_status()
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            with download_path.open("wb") as output:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    output.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        percent = int(downloaded * 100 / total)
                        set_update_button(f"กำลังดาวน์โหลด {percent}%", False)
        ui_call(install_downloaded_update, download_path, latest_version)
    except (requests.RequestException, OSError) as error:
        try:
            download_path.unlink(missing_ok=True)
        except OSError:
            pass
        ui_call(messagebox.showerror, "ดาวน์โหลดไม่สำเร็จ", str(error))
        set_update_button()


def batch_value(value):
    return str(value).replace("%", "%%")


def install_downloaded_update(download_path, latest_version):
    current_exe = Path(sys.executable).resolve()
    update_log = APP_DATA_DIR / "updater.log"
    backup_exe = current_exe.with_suffix(current_exe.suffix + ".bak")
    updater_script = APP_DATA_DIR / "install_update.cmd"
    script = (
        "@echo off\n"
        "setlocal\n"
        f"set \"SOURCE={batch_value(download_path)}\"\n"
        f"set \"TARGET={batch_value(current_exe)}\"\n"
        f"set \"BACKUP={batch_value(backup_exe)}\"\n"
        f"set \"LOG={batch_value(update_log)}\"\n"
        "set \"UPDATED=0\"\n"
        "for /l %%I in (1,1,120) do (\n"
        "  if not exist \"%SOURCE%\" goto done\n"
        "  if not exist \"%TARGET%\" (\n"
        "    move /Y \"%SOURCE%\" \"%TARGET%\" >nul 2>nul && set \"UPDATED=1\" && goto done\n"
        "  )\n"
        "  del /F /Q \"%BACKUP%\" >nul 2>nul\n"
        "  move /Y \"%TARGET%\" \"%BACKUP%\" >nul 2>nul\n"
        "  if not errorlevel 1 (\n"
        "    move /Y \"%SOURCE%\" \"%TARGET%\" >nul 2>nul\n"
        "    if not errorlevel 1 (\n"
        "      del /F /Q \"%BACKUP%\" >nul 2>nul\n"
        "      set \"UPDATED=1\"\n"
        "      goto done\n"
        "    )\n"
        "    move /Y \"%BACKUP%\" \"%TARGET%\" >nul 2>nul\n"
        "  )\n"
        "  timeout /t 1 /nobreak >nul\n"
        ")\n"
        ":done\n"
        "if not \"%UPDATED%\"==\"1\" echo %date% %time% update failed>>\"%LOG%\"\n"
        "if exist \"%TARGET%\" start \"\" \"%TARGET%\"\n"
        "del /F /Q \"%~f0\" >nul 2>nul\n"
    )
    try:
        updater_script.write_text(script, encoding="utf-8")
        subprocess.Popen(
            ["cmd.exe", "/c", str(updater_script)],
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                | subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NEW_PROCESS_GROUP
            ),
            close_fds=True,
        )
    except OSError as error:
        messagebox.showerror("ติดตั้งไม่สำเร็จ", str(error))
        set_update_button()
        return

    messagebox.showinfo("พร้อมติดตั้ง", f"ดาวน์โหลด v{latest_version} แล้ว โปรแกรมจะเปิดใหม่อัตโนมัติ")
    save_cloudflare_settings()
    root.quit()
    root.destroy()


def save_tokens():
    try:
        TOKEN_STORE.write_text(
            json.dumps(saved_tokens, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as error:
        messagebox.showerror("บันทึกไม่สำเร็จ", f"ไม่สามารถบันทึกรายการ Token ได้\n{error}")


def load_tokens():
    global saved_tokens
    source = TOKEN_STORE if TOKEN_STORE.exists() else LEGACY_TOKEN_STORE
    if source.exists():
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
            saved_tokens = []
            for index, item in enumerate(data):
                if isinstance(item, dict) and item.get("token"):
                    saved_tokens.append({
                        "name": str(item.get("name") or f"LINE OA {index + 1}"),
                        "token": item["token"],
                        "enabled": bool(item.get("enabled", True)),
                    })
        except (OSError, json.JSONDecodeError, TypeError):
            saved_tokens = []
        if source == LEGACY_TOKEN_STORE and saved_tokens:
            save_tokens()
    refresh_token_list()


def save_cloudflare_settings(_event=None):
    settings = {
        "account_id": ent_account.get().strip(),
        "kv_namespace_id": ent_kv.get().strip(),
        "api_token": ent_cf_token.get().strip(),
        "send_delay": ent_send_delay.get().strip(),
        "broadcast_message": get_broadcast_message(),
    }
    try:
        SETTINGS_STORE.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as error:
        messagebox.showerror("บันทึกไม่สำเร็จ", f"ไม่สามารถบันทึกการตั้งค่า Cloudflare ได้\n{error}")


def load_cloudflare_settings():
    source = SETTINGS_STORE if SETTINGS_STORE.exists() else LEGACY_SETTINGS_STORE
    if not source.exists():
        return
    try:
        settings = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return

    for entry, key in (
        (ent_account, "account_id"),
        (ent_kv, "kv_namespace_id"),
        (ent_cf_token, "api_token"),
        (ent_send_delay, "send_delay"),
    ):
        value = settings.get(key, "")
        if isinstance(value, str):
            entry.delete(0, tk.END)
            entry.insert(0, value)
    broadcast_message = settings.get("broadcast_message", DEFAULT_BROADCAST_MESSAGE)
    if isinstance(broadcast_message, str):
        txt_broadcast_message.delete("1.0", tk.END)
        txt_broadcast_message.insert("1.0", broadcast_message)
    if source == LEGACY_SETTINGS_STORE:
        save_cloudflare_settings()


def close_app():
    save_cloudflare_settings()
    root.destroy()


def get_broadcast_message():
    return txt_broadcast_message.get("1.0", tk.END).strip()


def get_send_delay():
    raw_value = ent_send_delay.get().strip().replace(",", ".")
    if not raw_value:
        return 0.0
    try:
        delay = float(raw_value)
    except ValueError:
        raise ValueError("กรุณาใส่ Delay เป็นตัวเลข เช่น 0, 1, 2.5")
    if delay < 0:
        raise ValueError("Delay ต้องไม่น้อยกว่า 0 วินาที")
    if delay > 3600:
        raise ValueError("Delay สูงสุดได้ไม่เกิน 3600 วินาที")
    return delay


def masked_token(token):
    if len(token) <= 18:
        return "•" * len(token)
    return f"{token[:10]}{'•' * 14}{token[-6:]}"


def refresh_token_list():
    for item in token_list.get_children():
        token_list.delete(item)
    for index, item in enumerate(saved_tokens):
        enabled = item["enabled"]
        token_list.insert(
            "", "end", iid=str(index),
            values=(
                "☑  พร้อมส่ง" if enabled else "☐  ปิดใช้งาน",
                item.get("name", f"LINE OA {index + 1}"),
                masked_token(item["token"]),
            ),
            tags=("enabled" if enabled else "disabled",),
        )
    active = sum(item["enabled"] for item in saved_tokens)
    token_count.configure(text=f"พร้อมส่ง {active} / {len(saved_tokens)}")


def add_tokens(_event=None):
    oa_name = ent_oa_name.get().strip()
    token = ent_line_token.get().strip()
    if not oa_name:
        messagebox.showwarning("ยังไม่ได้ตั้งชื่อ", "กรุณาใส่ชื่อ LINE OA ก่อนเพิ่ม Token")
        ent_oa_name.focus_set()
        return
    if not token:
        messagebox.showwarning("ยังไม่มี Token", "กรุณาใส่ Channel Access Token")
        ent_line_token.focus_set()
        return
    existing = {item["token"] for item in saved_tokens}
    if token in existing:
        messagebox.showinfo("มี Token นี้แล้ว", "Token ที่กรอกมีอยู่ในรายการแล้ว")
        return

    saved_tokens.append({"name": oa_name, "token": token, "enabled": True})
    ent_oa_name.delete(0, tk.END)
    ent_line_token.delete(0, tk.END)
    save_tokens()
    refresh_token_list()
    token_list.selection_set(str(len(saved_tokens) - 1))
    token_list.see(str(len(saved_tokens) - 1))
    ent_oa_name.focus_set()


def selected_token_index():
    selection = token_list.selection()
    return int(selection[0]) if selection else None


def toggle_selected_token(_event=None):
    index = selected_token_index()
    if index is None:
        messagebox.showinfo("เลือกรายการ", "กรุณาเลือก Token ที่ต้องการเปิดหรือปิด")
        return
    saved_tokens[index]["enabled"] = not saved_tokens[index]["enabled"]
    save_tokens()
    refresh_token_list()
    token_list.selection_set(str(index))


def token_list_click(event):
    row_id = token_list.identify_row(event.y)
    column = token_list.identify_column(event.x)
    if not row_id or column != "#1":
        return
    index = int(row_id)
    saved_tokens[index]["enabled"] = not saved_tokens[index]["enabled"]
    save_tokens()
    refresh_token_list()
    token_list.selection_set(row_id)
    return "break"


def remove_selected_token():
    index = selected_token_index()
    if index is None:
        messagebox.showinfo("เลือกรายการ", "กรุณาเลือก Token ที่ต้องการลบ")
        return
    if not messagebox.askyesno("ลบ Token", "ต้องการลบ Token นี้ออกจากรายการหรือไม่?"):
        return
    saved_tokens.pop(index)
    save_tokens()
    refresh_token_list()


def edit_selected_oa_name():
    index = selected_token_index()
    if index is None:
        return
    current_name = saved_tokens[index].get("name", f"LINE OA {index + 1}")
    new_name = simpledialog.askstring(
        "แก้ไขชื่อ LINE OA",
        "ชื่อใหม่:",
        initialvalue=current_name,
        parent=root,
    )
    if new_name is None:
        return
    new_name = new_name.strip()
    if not new_name:
        messagebox.showwarning("ชื่อไม่ถูกต้อง", "ชื่อ LINE OA ต้องไม่เป็นค่าว่าง")
        return
    saved_tokens[index]["name"] = new_name
    save_tokens()
    refresh_token_list()
    token_list.selection_set(str(index))
    token_list.see(str(index))


def show_token_context_menu(event):
    row_id = token_list.identify_row(event.y)
    if not row_id:
        return
    token_list.selection_set(row_id)
    token_list.focus(row_id)
    try:
        token_context_menu.tk_popup(event.x_root, event.y_root)
    finally:
        token_context_menu.grab_release()


def start_broadcast():
    cf_account = ent_account.get().strip()
    cf_kv_id = ent_kv.get().strip()
    cf_token = ent_cf_token.get().strip()
    line_tokens = [item["token"] for item in saved_tokens if item["enabled"]]
    broadcast_message = get_broadcast_message()

    if not cf_account or not cf_kv_id or not cf_token:
        messagebox.showwarning("ข้อมูลไม่ครบ", "กรุณากรอกข้อมูล Cloudflare ให้ครบทุกช่อง")
        return
    if not broadcast_message:
        messagebox.showwarning("ยังไม่มีข้อความ", "กรุณาใส่ข้อความ Broadcast ก่อนเริ่มส่ง")
        txt_broadcast_message.focus_set()
        return
    if len(broadcast_message) > 400:
        messagebox.showwarning("ข้อความยาวเกินไป", "ข้อความ Broadcast สำหรับ LINE ต้องไม่เกิน 400 ตัวอักษร")
        txt_broadcast_message.focus_set()
        return
    try:
        send_delay = get_send_delay()
    except ValueError as error:
        messagebox.showwarning("Delay ไม่ถูกต้อง", str(error))
        ent_send_delay.focus_set()
        ent_send_delay.selection_range(0, tk.END)
        return
    if not re.fullmatch(r"[a-fA-F0-9]{32}", cf_account):
        messagebox.showwarning(
            "Account ID ไม่ถูกต้อง",
            "กรุณาใส่ Cloudflare Account ID จริง (ตัวอักษรและตัวเลข 32 ตัว)\n\n"
            "ค่าอย่าง ntwfiber02 เป็นชื่อบัญชี จึงใช้เรียก API ไม่ได้",
        )
        ent_account.focus_set()
        ent_account.selection_range(0, tk.END)
        return
    if not re.fullmatch(r"[a-fA-F0-9]{32}", cf_kv_id):
        messagebox.showwarning(
            "KV Namespace ID ไม่ถูกต้อง",
            "กรุณาใส่ KV Namespace ID ที่เป็นตัวอักษรและตัวเลข 32 ตัว",
        )
        ent_kv.focus_set()
        ent_kv.selection_range(0, tk.END)
        return
    if not line_tokens:
        messagebox.showwarning("ยังไม่มี Token ที่พร้อมส่ง", "กรุณาเพิ่มหรือเปิดใช้งาน LINE Token อย่างน้อย 1 รายการ")
        return

    save_cloudflare_settings()
    progress["value"] = 0
    txt_log.configure(state="normal")
    txt_log.delete("1.0", tk.END)
    txt_log.configure(state="disabled")
    set_running(True)
    threading.Thread(
        target=process_broadcast,
        args=(cf_account, cf_kv_id, cf_token, line_tokens, send_delay, broadcast_message),
        daemon=True,
    ).start()


def process_broadcast(cf_account, cf_kv_id, cf_token, line_tokens, send_delay, broadcast_message):
    add_log("กำลังดึงรายชื่อกลุ่มแชทจาก Cloudflare KV...", "info")
    group_ids = []
    headers = {"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"}

    try:
        kv_url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/storage/kv/namespaces/{cf_kv_id}/keys?prefix=group:"
        response = requests.get(kv_url, headers=headers, timeout=20)
        response.raise_for_status()
        kv_data = response.json()
        if not kv_data.get("success"):
            raise RuntimeError(str(kv_data.get("errors")))

        for key_obj in kv_data.get("result", []):
            val_url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/storage/kv/namespaces/{cf_kv_id}/values/{key_obj['name']}"
            val_res = requests.get(val_url, headers={"Authorization": f"Bearer {cf_token}"}, timeout=20)
            val_res.raise_for_status()
            if val_res.text.strip():
                group_ids.append(val_res.text.strip())
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code == 404:
            add_log("ไม่พบ Account หรือ KV Namespace — กรุณาตรวจสอบ ID ทั้งสองช่อง", "error")
        elif error.response is not None and error.response.status_code in (401, 403):
            add_log("Cloudflare ปฏิเสธการเข้าถึง — กรุณาตรวจสอบ API Token และสิทธิ์ Workers KV Storage", "error")
        else:
            add_log(f"Cloudflare API ตอบกลับผิดพลาด: {error}", "error")
        set_running(False)
        return
    except Exception as error:
        add_log(f"เชื่อมต่อ Cloudflare KV ไม่สำเร็จ: {error}", "error")
        set_running(False)
        return

    if not group_ids:
        add_log("เชื่อมต่อ Cloudflare KV สำเร็จ แต่ยังไม่มีข้อมูล group:*", "warning")
        add_log("กรุณาตั้ง LINE Webhook และส่งข้อความในกลุ่มอย่างน้อย 1 ครั้ง", "info")
        set_running(False)
        return

    total_groups = len(group_ids)
    ui_call(progress.configure, maximum=total_groups)
    add_log(f"พบ {total_groups} กลุ่ม • พร้อมใช้งาน {len(line_tokens)} บอท", "success")
    if send_delay > 0:
        add_log(f"ตั้ง Delay การส่ง {send_delay:g} วินาทีต่อกลุ่ม", "info")

    success_count = 0
    for index, chat_id in enumerate(group_ids):
        bot_index = index % len(line_tokens)
        add_log(f"[{index + 1}/{total_groups}] บอท {bot_index + 1} → {chat_id}")

        try:
            response = requests.post(
                "https://api.line.me/v2/bot/message/push",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {line_tokens[bot_index]}"},
                json=get_flex_payload(chat_id, random.choice(FLEX_IMAGES), broadcast_message),
                timeout=20,
            )
            if response.status_code == 200:
                success_count += 1
                add_log("   ส่งสำเร็จ", "success")
            else:
                try:
                    detail = response.json().get("message", response.text)
                except ValueError:
                    detail = response.text
                add_log(f"   ส่งไม่สำเร็จ: {detail}", "error")
        except Exception as error:
            add_log(f"   เกิดข้อผิดพลาดจาก LINE: {error}", "error")

        ui_call(progress.configure, value=index + 1)
        if send_delay > 0 and index < total_groups - 1:
            time.sleep(send_delay)

    add_log(f"เสร็จสิ้น • สำเร็จ {success_count} จาก {total_groups} กลุ่ม", "success")
    set_running(False)
    ui_call(messagebox.showinfo, "ส่งข้อความเสร็จแล้ว", f"ส่งสำเร็จ {success_count} จาก {total_groups} กลุ่ม")


def make_entry(parent, label, row, secret=False):
    tk.Label(parent, text=label, bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(
        row=row * 2, column=0, sticky="w", pady=(0 if row == 0 else 12, 6)
    )
    entry = tk.Entry(
        parent, bg=COLORS["input"], fg=COLORS["text"], insertbackground=COLORS["text"],
        relief="flat", font=("Segoe UI", 10), show="•" if secret else "",
        highlightthickness=1, highlightbackground=COLORS["border"], highlightcolor=COLORS["accent"],
    )
    entry.grid(row=row * 2 + 1, column=0, sticky="ew", ipady=9)
    return entry


root = tk.Tk()
root.title("LINE FLEX : NTW")
if ICON_PATH.exists():
    try:
        root.iconbitmap(default=str(ICON_PATH))
    except tk.TclError:
        pass
root.geometry("1060x720")
root.resizable(False, False)
root.configure(bg=COLORS["bg"])

style = ttk.Style(root)
style.theme_use("clam")
style.configure("Modern.Horizontal.TProgressbar", troughcolor=COLORS["input"], background=COLORS["accent"], borderwidth=0, thickness=8)
style.configure(
    "Token.Treeview", background=COLORS["input"], fieldbackground=COLORS["input"],
    foreground=COLORS["text"], borderwidth=0, rowheight=30, font=("Segoe UI", 9),
)
style.configure(
    "Token.Treeview.Heading", background=COLORS["surface_alt"], foreground=COLORS["muted"],
    borderwidth=0, relief="flat", font=("Segoe UI Semibold", 8),
)
style.map("Token.Treeview", background=[("selected", COLORS["border"])], foreground=[("selected", COLORS["text"])])

app = tk.Frame(root, bg=COLORS["bg"])
app.pack(fill="both", expand=True, padx=26, pady=18)
app.grid_columnconfigure(0, weight=0, minsize=360)
app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(1, weight=1)

header = tk.Frame(app, bg=COLORS["bg"])
header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
tk.Label(header, text="Ntw", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI Semibold", 22)).pack(side="left")
tk.Label(header, text="STUDIO", bg=COLORS["accent"], fg="#07140C", font=("Segoe UI Semibold", 8), padx=8, pady=4).pack(side="left", padx=10)
status_box = tk.Frame(header, bg=COLORS["bg"])
status_box.pack(side="right")
status_dot = tk.Label(status_box, text="●", bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 10))
status_dot.pack(side="left", padx=(0, 6))
status_text = tk.Label(status_box, text="พร้อมเริ่มงาน", bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 9))
status_text.pack(side="left")
btn_update = tk.Button(
    header, text=f"v{APP_VERSION}  •  ตรวจอัปเดต", command=check_for_updates,
    bg=COLORS["bg"], fg=COLORS["muted"], activebackground=COLORS["bg"],
    activeforeground=COLORS["accent"], relief="flat", cursor="hand2",
    font=("Segoe UI", 8), padx=12,
)
btn_update.pack(side="right", padx=(0, 18))

left_card = tk.Frame(app, bg=COLORS["surface"], padx=22, pady=18, highlightthickness=1, highlightbackground=COLORS["border"])
left_card.grid(row=1, column=0, sticky="nsew", padx=(0, 18))
left_card.grid_columnconfigure(0, weight=1)
tk.Label(left_card, text="การเชื่อมต่อ", bg=COLORS["surface"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).grid(row=0, column=0, sticky="w")
tk.Label(left_card, text="ใช้ Account ID จาก Cloudflare Dashboard", bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=(4, 20))

fields = tk.Frame(left_card, bg=COLORS["surface"])
fields.grid(row=2, column=0, sticky="ew")
fields.grid_columnconfigure(0, weight=1)
ent_account = make_entry(fields, "ACCOUNT ID", 0)
ent_kv = make_entry(fields, "KV NAMESPACE ID", 1)
ent_cf_token = make_entry(fields, "API TOKEN", 2, secret=True)
for cloudflare_entry in (ent_account, ent_kv, ent_cf_token):
    cloudflare_entry.bind("<FocusOut>", save_cloudflare_settings)

tk.Label(left_card, text="บันทึกอัตโนมัติไว้ในเครื่องนี้", bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 8)).grid(row=3, column=0, sticky="w", pady=(20, 0))

right = tk.Frame(app, bg=COLORS["bg"])
right.grid(row=1, column=1, sticky="nsew")
right.grid_columnconfigure(0, weight=1)
right.grid_rowconfigure(2, weight=1)

token_card = tk.Frame(right, bg=COLORS["surface"], padx=20, pady=14, highlightthickness=1, highlightbackground=COLORS["border"])
token_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
token_card.grid_columnconfigure(0, weight=1)
token_head = tk.Frame(token_card, bg=COLORS["surface"])
token_head.grid(row=0, column=0, sticky="ew", pady=(0, 10))
tk.Label(token_head, text="LINE Channel Tokens", bg=COLORS["surface"], fg=COLORS["text"], font=("Segoe UI Semibold", 12)).pack(side="left")
token_count = tk.Label(token_head, text="พร้อมส่ง 0 / 0", bg=COLORS["surface_alt"], fg=COLORS["accent"], font=("Segoe UI Semibold", 8), padx=8, pady=4)
token_count.pack(side="right")

add_labels = tk.Frame(token_card, bg=COLORS["surface"])
add_labels.grid(row=1, column=0, sticky="ew", pady=(0, 5))
tk.Label(add_labels, text="ชื่อ LINE OA", width=18, anchor="w", bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack(side="left")
tk.Label(add_labels, text="CHANNEL ACCESS TOKEN", anchor="w", bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack(side="left", padx=(8, 0))

add_row = tk.Frame(token_card, bg=COLORS["surface"])
add_row.grid(row=2, column=0, sticky="ew", pady=(0, 8))
add_row.grid_columnconfigure(1, weight=1)
ent_oa_name = tk.Entry(
    add_row, width=18, bg=COLORS["input"], fg=COLORS["text"], insertbackground=COLORS["text"],
    relief="flat", font=("Segoe UI", 9),
    highlightthickness=1, highlightbackground=COLORS["border"], highlightcolor=COLORS["accent"],
)
ent_oa_name.grid(row=0, column=0, sticky="ew", ipady=9)
ent_oa_name.bind("<Return>", lambda _event: ent_line_token.focus_set())
ent_line_token = tk.Entry(
    add_row, bg=COLORS["input"], fg=COLORS["text"], insertbackground=COLORS["text"],
    relief="flat", font=("Cascadia Mono", 9), show="•",
    highlightthickness=1, highlightbackground=COLORS["border"], highlightcolor=COLORS["accent"],
)
ent_line_token.grid(row=0, column=1, sticky="ew", ipady=9, padx=(8, 0))
ent_line_token.bind("<Return>", add_tokens)
btn_add_token = tk.Button(
    add_row, text="+ เพิ่ม Token", command=add_tokens, bg=COLORS["accent"], fg="#06130B",
    activebackground=COLORS["accent_hover"], relief="flat", cursor="hand2",
    font=("Segoe UI Semibold", 9), padx=14, pady=8,
)
btn_add_token.grid(row=0, column=2, padx=(8, 0))

token_wrap = tk.Frame(token_card, bg=COLORS["input"], highlightthickness=1, highlightbackground=COLORS["border"])
token_wrap.grid(row=3, column=0, sticky="ew")
token_list = ttk.Treeview(
    token_wrap, columns=("status", "name", "token"), show="headings", height=3,
    selectmode="browse", style="Token.Treeview",
)
token_list.heading("status", text="สถานะ")
token_list.heading("name", text="ชื่อ LINE OA")
token_list.heading("token", text="TOKEN ที่บันทึกไว้")
token_list.column("status", width=105, minwidth=105, stretch=False, anchor="center")
token_list.column("name", width=145, minwidth=100, stretch=False, anchor="w")
token_list.column("token", width=245, minwidth=180, anchor="w")
token_list.pack(side="left", fill="both", expand=True)
token_list.bind("<Button-1>", token_list_click)
token_list.bind("<Button-3>", show_token_context_menu)
token_scroll = ttk.Scrollbar(token_wrap, command=token_list.yview)
token_scroll.pack(side="right", fill="y")
token_list.configure(yscrollcommand=token_scroll.set)
token_list.tag_configure("enabled", foreground=COLORS["text"])
token_list.tag_configure("disabled", foreground=COLORS["muted"])

token_context_menu = tk.Menu(
    root, tearoff=False, bg=COLORS["surface_alt"], fg=COLORS["text"],
    activebackground=COLORS["border"], activeforeground=COLORS["text"],
    relief="flat", borderwidth=1, font=("Segoe UI", 9),
)
token_context_menu.add_command(label="แก้ไขชื่อ LINE OA", command=edit_selected_oa_name)

token_actions = tk.Frame(token_card, bg=COLORS["surface"])
token_actions.grid(row=4, column=0, sticky="ew", pady=(9, 0))
tk.Label(token_actions, text="คลิก Checkbox ด้านหน้าสถานะเพื่อเปิด/ปิด", bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack(side="left")
tk.Button(token_actions, text="ลบ", command=remove_selected_token, bg=COLORS["surface"], fg=COLORS["danger"], activebackground=COLORS["surface_alt"], activeforeground=COLORS["danger"], relief="flat", cursor="hand2", font=("Segoe UI", 8), padx=8).pack(side="right")

settings_card = tk.Frame(right, bg=COLORS["surface"], padx=20, pady=12, highlightthickness=1, highlightbackground=COLORS["border"])
settings_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
settings_card.grid_columnconfigure(1, weight=1)
tk.Label(settings_card, text="Broadcast Settings", bg=COLORS["surface"], fg=COLORS["text"], font=("Segoe UI Semibold", 11)).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
tk.Label(settings_card, text="Delay ส่ง / กลุ่ม (วินาที)", bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w", padx=(0, 12))
ent_send_delay = tk.Entry(
    settings_card, width=10, bg=COLORS["input"], fg=COLORS["text"], insertbackground=COLORS["text"],
    relief="flat", font=("Segoe UI", 9),
    highlightthickness=1, highlightbackground=COLORS["border"], highlightcolor=COLORS["accent"],
)
ent_send_delay.grid(row=2, column=0, sticky="w", ipady=7, padx=(0, 12))
ent_send_delay.insert(0, "0")
ent_send_delay.bind("<FocusOut>", save_cloudflare_settings)
tk.Label(settings_card, text="ข้อความ Broadcast / altText", bg=COLORS["surface"], fg=COLORS["muted"], font=("Segoe UI", 8)).grid(row=1, column=1, sticky="w")
txt_broadcast_message = tk.Text(
    settings_card, height=1, bg=COLORS["input"], fg=COLORS["text"], insertbackground=COLORS["text"],
    relief="flat", font=("Segoe UI", 9), padx=8, pady=6, wrap="word",
    highlightthickness=1, highlightbackground=COLORS["border"], highlightcolor=COLORS["accent"],
)
txt_broadcast_message.grid(row=2, column=1, sticky="ew")
txt_broadcast_message.insert("1.0", DEFAULT_BROADCAST_MESSAGE)
txt_broadcast_message.bind("<FocusOut>", save_cloudflare_settings)

log_card = tk.Frame(right, bg=COLORS["surface"], padx=20, pady=14, highlightthickness=1, highlightbackground=COLORS["border"])
log_card.grid(row=2, column=0, sticky="nsew")
log_card.grid_columnconfigure(0, weight=1)
log_card.grid_rowconfigure(2, weight=1, minsize=92)
tk.Label(log_card, text="Activity log", bg=COLORS["surface"], fg=COLORS["text"], font=("Segoe UI Semibold", 12)).grid(row=0, column=0, sticky="w")
progress = ttk.Progressbar(log_card, style="Modern.Horizontal.TProgressbar", mode="determinate")
progress.grid(row=1, column=0, sticky="ew", pady=(10, 10))

log_wrap = tk.Frame(log_card, bg=COLORS["input"])
log_wrap.grid(row=2, column=0, sticky="nsew")
txt_log = tk.Text(log_wrap, bg=COLORS["input"], fg=COLORS["muted"], insertbackground=COLORS["text"], relief="flat", font=("Cascadia Mono", 9), padx=12, pady=10, state="disabled", wrap="word")
txt_log.pack(side="left", fill="both", expand=True)
log_scroll = ttk.Scrollbar(log_wrap, command=txt_log.yview)
log_scroll.pack(side="right", fill="y")
txt_log.configure(yscrollcommand=log_scroll.set)
txt_log.tag_configure("success", foreground=COLORS["accent"])
txt_log.tag_configure("error", foreground=COLORS["danger"])
txt_log.tag_configure("warning", foreground="#F7C65C")
txt_log.tag_configure("info", foreground="#65B7FF")

btn_start = tk.Button(
    right, text="เริ่ม Broadcast  →", command=start_broadcast,
    bg=COLORS["accent"], fg="#06130B", activebackground=COLORS["accent_hover"],
    activeforeground="#FFFFFF", disabledforeground="#647067", relief="flat",
    font=("Segoe UI Semibold", 11), cursor="hand2", pady=10,
)
btn_start.grid(row=3, column=0, sticky="ew", pady=(12, 0))

load_tokens()
load_cloudflare_settings()
root.protocol("WM_DELETE_WINDOW", close_app)
root.after(1500, lambda: check_for_updates(silent=True))
root.mainloop()
