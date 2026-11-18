"""LanBridge PySide6 desktop app."""

from __future__ import annotations

import argparse
import json
import os
import queue
import sys
import time
from pathlib import Path

import core
import server
import theme


def build_parser():
    p = argparse.ArgumentParser(prog="lanbridge", description="LAN bridge between PC and Android phone")
    p.add_argument("--version", action="version", version=f"lanbridge {core.VERSION}")
    p.add_argument("--no-gui", action="store_true", help=argparse.SUPPRESS)
    return p


class LanBridgeWindow:
    """Built lazily to keep --help/--version Qt-free."""

    def __new__(cls, config):
        from PySide6 import QtCore, QtGui, QtWidgets

        class _Window(QtWidgets.QMainWindow):
            def __init__(self, cfg):
                super().__init__()
                self.cfg = cfg
                self.state = server.BridgeState(cfg)
                self.server_thread: server.ServerThread | None = None
                self.ui_queue: queue.Queue = queue.Queue(maxsize=500)
                self.state.bus.subscribe(self.ui_queue)
                self.setWindowTitle(f"{core.APP_NAME} {core.VERSION}")
                self.resize(1080, 720)
                self._build_ui()
                self._timer = QtCore.QTimer(self)
                self._timer.timeout.connect(self._poll_events)
                self._timer.start(200)
                self._screen_timer = QtCore.QTimer(self)
                self._screen_timer.timeout.connect(self._refresh_screen)
                self._screen_timer.start(700)
                self._refresh_all()

            # ---- UI ----
            def _build_ui(self):
                QtWidgets = __import__('PySide6.QtWidgets', fromlist=['*'])
                central = QtWidgets.QWidget()
                self.setCentralWidget(central)
                root = QtWidgets.QVBoxLayout(central)
                root.setContentsMargins(14, 14, 14, 10)
                root.setSpacing(10)

                header = QtWidgets.QHBoxLayout()
                title = QtWidgets.QLabel("LanBridge")
                title.setObjectName("title")
                subtitle = QtWidgets.QLabel("PC ↔ Android over your LAN")
                subtitle.setObjectName("muted")
                tbox = QtWidgets.QVBoxLayout()
                tbox.addWidget(title)
                tbox.addWidget(subtitle)
                header.addLayout(tbox)
                header.addStretch(1)
                self.status_pill = QtWidgets.QLabel("Server stopped")
                self.status_pill.setObjectName("pill")
                self.phone_pill = QtWidgets.QLabel("Phone: not connected")
                self.phone_pill.setObjectName("pill")
                header.addWidget(self.status_pill)
                header.addWidget(self.phone_pill)
                root.addLayout(header)

                self.tabs = QtWidgets.QTabWidget()
                root.addWidget(self.tabs, 1)
                self.tabs.addTab(self._dashboard_tab(), "Dashboard")
                self.tabs.addTab(self._screen_tab(), "Phone Screen")
                self.tabs.addTab(self._commands_tab(), "Commands")
                self.tabs.addTab(self._clipboard_tab(), "Clipboard")
                self.tabs.addTab(self._files_tab(), "Files")
                self.tabs.addTab(self._messages_tab(), "Messages & Calls")
                self.tabs.addTab(self._media_tab(), "Media")
                self.tabs.addTab(self._settings_tab(), "Settings")

                self.status = self.statusBar()
                self.status.showMessage("Ready")

            def _dashboard_tab(self):
                from PySide6 import QtWidgets
                w = QtWidgets.QWidget(); l = QtWidgets.QVBoxLayout(w); l.setContentsMargins(12,12,12,12); l.setSpacing(10)
                cards = QtWidgets.QHBoxLayout()
                self.card_server = self._info_card("Server", "Stopped")
                self.card_phone = self._info_card("Phone", "Not connected")
                self.card_addrs = self._info_card("LAN addresses", "Unknown")
                cards.addWidget(self.card_server, 1); cards.addWidget(self.card_phone, 1); cards.addWidget(self.card_addrs, 1)
                l.addLayout(cards)
                actions = QtWidgets.QHBoxLayout()
                self.btn_start = theme.make_button("Start server", "primary")
                self.btn_stop = theme.make_button("Stop server", "danger")
                self.btn_refresh = theme.make_button("Refresh")
                actions.addWidget(self.btn_start); actions.addWidget(self.btn_stop); actions.addWidget(self.btn_refresh); actions.addStretch(1)
                l.addLayout(actions)
                self.log_view = QtWidgets.QPlainTextEdit(); self.log_view.setReadOnly(True); self.log_view.setPlaceholderText("Event log…")
                l.addWidget(self.log_view, 1)
                self.btn_start.clicked.connect(self.start_server)
                self.btn_stop.clicked.connect(self.stop_server)
                self.btn_refresh.clicked.connect(self._refresh_all)
                return w

            def _info_card(self, title, value):
                from PySide6 import QtWidgets
                box = QtWidgets.QGroupBox(title)
                v = QtWidgets.QVBoxLayout(box)
                label = QtWidgets.QLabel(value); label.setWordWrap(True)
                v.addWidget(label)
                box.value_label = label
                return box

            def _screen_tab(self):
                from PySide6 import QtWidgets, QtCore
                w = QtWidgets.QWidget(); l = QtWidgets.QHBoxLayout(w); l.setContentsMargins(12,12,12,12); l.setSpacing(10)
                left = QtWidgets.QVBoxLayout()
                self.screen_label = QtWidgets.QLabel("No screen frame yet.\nStart screen sharing on the Android app.")
                self.screen_label.setAlignment(QtCore.Qt.AlignCenter)
                self.screen_label.setMinimumSize(360, 640)
                self.screen_label.setStyleSheet("background:#0f141b; border:1px solid #243244; border-radius:12px; color:#9fb0c3;")
                left.addWidget(self.screen_label, 1)
                l.addLayout(left, 3)
                right = QtWidgets.QVBoxLayout()
                info = QtWidgets.QLabel("Phone → PC screen view. For remote control, enable LanBridge Accessibility Service on Android, then use actions below (sent as commands/events).")
                info.setWordWrap(True); info.setObjectName("muted")
                right.addWidget(info)
                grid = QtWidgets.QGridLayout()
                def btn(text, r,c, payload):
                    b = theme.make_button(text)
                    b.clicked.connect(lambda: self._send_phone_input(payload))
                    grid.addWidget(b, r, c)
                    return b
                btn("Back",0,0,{"type":"nav","key":"back"})
                btn("Home",0,1,{"type":"nav","key":"home"})
                btn("Recents",0,2,{"type":"nav","key":"recents"})
                btn("Tap center",1,0,{"type":"tap","x":0.5,"y":0.5})
                btn("Swipe up",1,1,{"type":"swipe","x1":0.5,"y1":0.8,"x2":0.5,"y2":0.2})
                btn("Swipe down",1,2,{"type":"swipe","x1":0.5,"y1":0.2,"x2":0.5,"y2":0.8})
                right.addLayout(grid)
                right.addWidget(QtWidgets.QLabel("Custom input JSON (advanced):"))
                self.input_json = QtWidgets.QPlainTextEdit('{"type":"tap","x":0.5,"y":0.5}')
                self.input_json.setMaximumHeight(120)
                right.addWidget(self.input_json)
                send = theme.make_button("Send input event", "primary")
                send.clicked.connect(self._send_custom_input)
                right.addWidget(send)
                right.addStretch(1)
                l.addLayout(right, 2)
                return w

            def _commands_tab(self):
                from PySide6 import QtWidgets
                w = QtWidgets.QWidget(); l = QtWidgets.QVBoxLayout(w); l.setContentsMargins(12,12,12,12)
                form = QtWidgets.QHBoxLayout()
                self.cmd_name = QtWidgets.QLineEdit(); self.cmd_name.setPlaceholderText("Command name")
                self.cmd_target = QtWidgets.QComboBox(); self.cmd_target.addItems(["phone", "pc"])
                self.cmd_action = QtWidgets.QComboBox(); self.cmd_action.addItems(["open_url", "notify", "shell", "media", "clipboard_get"])
                self.cmd_payload = QtWidgets.QLineEdit(); self.cmd_payload.setPlaceholderText('Payload JSON, e.g. {"url":"https://example.com"}')
                form.addWidget(self.cmd_name,2); form.addWidget(self.cmd_target,1); form.addWidget(self.cmd_action,1); form.addWidget(self.cmd_payload,3)
                add = theme.make_button("Add", "primary"); add.clicked.connect(self._add_command)
                form.addWidget(add)
                l.addLayout(form)
                self.cmd_list = QtWidgets.QTableWidget(0,4)
                self.cmd_list.setHorizontalHeaderLabels(["Name","Target","Action","Payload"])
                self.cmd_list.horizontalHeader().setStretchLastSection(True)
                self.cmd_list.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
                l.addWidget(self.cmd_list,1)
                row = QtWidgets.QHBoxLayout()
                run = theme.make_button("Run selected", "success"); run.clicked.connect(self._run_selected_command)
                send_phone = theme.make_button("Push list to phone"); send_phone.clicked.connect(self._push_commands)
                remove = theme.make_button("Remove selected", "danger"); remove.clicked.connect(self._remove_selected_command)
                row.addWidget(run); row.addWidget(send_phone); row.addWidget(remove); row.addStretch(1)
                l.addLayout(row)
                hint = QtWidgets.QLabel("PC 'shell' commands require enabling local command execution in Settings and use argv payload: {\"argv\":[\"notify-send\",\"Hi\"]}. Android command support depends on app permissions.")
                hint.setWordWrap(True); hint.setObjectName("muted"); l.addWidget(hint)
                return w

            def _clipboard_tab(self):
                from PySide6 import QtWidgets
                w = QtWidgets.QWidget(); l = QtWidgets.QVBoxLayout(w); l.setContentsMargins(12,12,12,12)
                self.clip_text = QtWidgets.QPlainTextEdit(); self.clip_text.setPlaceholderText("Shared clipboard text…")
                l.addWidget(self.clip_text,1)
                row = QtWidgets.QHBoxLayout()
                push_pc = theme.make_button("Set as PC/Shared clipboard", "primary"); push_pc.clicked.connect(self._clipboard_push)
                pull = theme.make_button("Refresh from shared"); pull.clicked.connect(self._clipboard_pull)
                copy_local = theme.make_button("Copy to local PC clipboard"); copy_local.clicked.connect(self._clipboard_copy_local)
                row.addWidget(push_pc); row.addWidget(pull); row.addWidget(copy_local); row.addStretch(1)
                l.addLayout(row)
                return w

            def _files_tab(self):
                from PySide6 import QtWidgets
                w = QtWidgets.QWidget(); l = QtWidgets.QVBoxLayout(w); l.setContentsMargins(12,12,12,12)
                split = QtWidgets.QSplitter()
                left = QtWidgets.QGroupBox("Received files (downloads)")
                ll = QtWidgets.QVBoxLayout(left)
                self.files_received = QtWidgets.QListWidget(); ll.addWidget(self.files_received)
                rrow = QtWidgets.QHBoxLayout(); open_dir = theme.make_button("Open download folder"); open_dir.clicked.connect(self._open_download_dir); ref = theme.make_button("Refresh"); ref.clicked.connect(self._refresh_files)
                rrow.addWidget(open_dir); rrow.addWidget(ref); ll.addLayout(rrow)
                right = QtWidgets.QGroupBox("Share to phone (outgoing)")
                rl = QtWidgets.QVBoxLayout(right)
                self.files_out = QtWidgets.QListWidget(); rl.addWidget(self.files_out)
                orow = QtWidgets.QHBoxLayout(); addf = theme.make_button("Add file…", "primary"); addf.clicked.connect(self._add_outgoing_file); refo = theme.make_button("Refresh"); refo.clicked.connect(self._refresh_files)
                orow.addWidget(addf); orow.addWidget(refo); rl.addLayout(orow)
                split.addWidget(left); split.addWidget(right)
                l.addWidget(split,1)
                note = QtWidgets.QLabel("Phone downloads from PC via /api/pc-files endpoints. PC receives uploads at /api/files into the configured download directory.")
                note.setWordWrap(True); note.setObjectName("muted"); l.addWidget(note)
                return w

            def _messages_tab(self):
                from PySide6 import QtWidgets
                w = QtWidgets.QWidget(); l = QtWidgets.QHBoxLayout(w); l.setContentsMargins(12,12,12,12)
                left = QtWidgets.QGroupBox("Notifications / messages")
                ll = QtWidgets.QVBoxLayout(left); self.msg_view = QtWidgets.QPlainTextEdit(); self.msg_view.setReadOnly(True); ll.addWidget(self.msg_view)
                right = QtWidgets.QGroupBox("Calls")
                rl = QtWidgets.QVBoxLayout(right); self.call_view = QtWidgets.QPlainTextEdit(); self.call_view.setReadOnly(True); rl.addWidget(self.call_view)
                l.addWidget(left,2); l.addWidget(right,1)
                return w

            def _media_tab(self):
                from PySide6 import QtWidgets
                w = QtWidgets.QWidget(); l = QtWidgets.QVBoxLayout(w); l.setContentsMargins(12,12,12,12)
                pcbox = QtWidgets.QGroupBox("PC media (MPRIS/playerctl)")
                pl = QtWidgets.QVBoxLayout(pcbox)
                self.pc_media_label = QtWidgets.QLabel("Unknown"); self.pc_media_label.setObjectName("muted")
                pl.addWidget(self.pc_media_label)
                prow = QtWidgets.QHBoxLayout()
                for label, cmd in [("Prev","previous"),("Play/Pause","play-pause"),("Next","next"),("Stop","stop")]:
                    b = theme.make_button(label)
                    b.clicked.connect(lambda _=False, c=cmd: self._pc_media(c))
                    prow.addWidget(b)
                ref = theme.make_button("Refresh"); ref.clicked.connect(self._refresh_pc_media)
                prow.addWidget(ref); prow.addStretch(1)
                pl.addLayout(prow)
                phonebox = QtWidgets.QGroupBox("Phone media (reported by Android)")
                phl = QtWidgets.QVBoxLayout(phonebox)
                self.phone_media_view = QtWidgets.QPlainTextEdit(); self.phone_media_view.setReadOnly(True); self.phone_media_view.setMaximumHeight(180)
                phl.addWidget(self.phone_media_view)
                note = QtWidgets.QLabel("To control phone media, send a saved command/event supported by the Android app (e.g. action 'media' with payload {\"cmd\":\"play_pause\"}).")
                note.setWordWrap(True); note.setObjectName("muted"); phl.addWidget(note)
                l.addWidget(pcbox); l.addWidget(phonebox); l.addStretch(1)
                return w

            def _settings_tab(self):
                from PySide6 import QtWidgets
                w = QtWidgets.QWidget(); l = QtWidgets.QFormLayout(w); l.setContentsMargins(16,16,16,16); l.setSpacing(10)
                self.set_name = QtWidgets.QLineEdit(str(self.cfg.get("device_name","")))
                self.set_host = QtWidgets.QLineEdit(str(self.cfg.get("listen_host","0.0.0.0")))
                self.set_port = QtWidgets.QSpinBox(); self.set_port.setRange(1,65535); self.set_port.setValue(int(self.cfg.get("port", core.DEFAULT_PORT)))
                self.set_token = QtWidgets.QLineEdit(str(self.cfg.get("token",""))); self.set_token.setEchoMode(QtWidgets.QLineEdit.Password)
                self.set_download = QtWidgets.QLineEdit(str(self.cfg.get("download_dir", str(core.DOWNLOAD_DIR))))
                self.set_allow_exec = QtWidgets.QCheckBox("Allow phone to trigger saved local PC commands (shell/open_url actions)")
                self.set_allow_exec.setChecked(bool(self.cfg.get("allow_pc_command_exec", False)))
                l.addRow("Device name", self.set_name)
                l.addRow("Listen host", self.set_host)
                l.addRow("Port", self.set_port)
                l.addRow("Pairing token", self.set_token)
                l.addRow("Download directory", self.set_download)
                l.addRow("Security", self.set_allow_exec)
                btns = QtWidgets.QHBoxLayout()
                save = theme.make_button("Save settings", "primary"); save.clicked.connect(self._save_settings)
                regen = theme.make_button("Regenerate token"); regen.clicked.connect(self._regen_token)
                btns.addWidget(save); btns.addWidget(regen); btns.addStretch(1)
                l.addRow(btns)
                self.addrs_label = QtWidgets.QLabel(""); self.addrs_label.setWordWrap(True); self.addrs_label.setObjectName("muted")
                l.addRow("LAN addresses", self.addrs_label)
                tut = QtWidgets.QLabel(f"See TUTORIAL.md in the project for pairing, permissions, firewall and Tailscale setup. Tutorial path: {Path(__file__).with_name('TUTORIAL.md')}")
                tut.setWordWrap(True); tut.setObjectName("muted"); l.addRow(tut)
                return w

            # ---- actions ----
            def log(self, msg):
                ts = time.strftime('%H:%M:%S')
                self.log_view.appendPlainText(f"[{ts}] {msg}")
                self.status.showMessage(msg, 5000)

            def start_server(self):
                if self.server_thread and self.server_thread.is_alive():
                    self.log("Server already running"); return
                self.state.config = dict(self.cfg)
                self.server_thread = server.ServerThread(self.state)
                self.server_thread.start()
                time.sleep(0.15)
                if self.server_thread.error:
                    self.log(f"Server failed: {self.server_thread.error}")
                else:
                    host = self.cfg.get('listen_host'); port = self.cfg.get('port')
                    self.log(f"Server listening on {host}:{port}")
                self._refresh_all()

            def stop_server(self):
                if self.server_thread:
                    self.server_thread.stop(); self.server_thread = None
                self.log("Server stopped")
                self._refresh_all()

            def _poll_events(self):
                while True:
                    try:
                        evt = self.ui_queue.get_nowait()
                    except queue.Empty:
                        break
                    self._handle_event(evt)

            def _handle_event(self, evt):
                et = evt.get('type')
                payload = evt.get('payload') or {}
                if et == 'phone_status':
                    connected = payload.get('connected')
                    info = payload.get('info') or {}
                    if connected:
                        self.log(f"Phone connected: {info.get('name') or info}")
                        self.phone_pill.setText(f"Phone: {info.get('name') or 'connected'}")
                    else:
                        self.log("Phone disconnected")
                        self.phone_pill.setText("Phone: not connected")
                    self._refresh_all()
                elif et == 'clipboard':
                    src = payload.get('source','')
                    if src == 'phone':
                        self.clip_text.setPlainText(str(payload.get('text') or ''))
                        self.log('Clipboard updated from phone')
                elif et == 'pc_clipboard':
                    self.clip_text.setPlainText(str(payload.get('text') or ''))
                elif et == 'file_received':
                    self.log(f"File received: {payload.get('name')}")
                    self._refresh_files()
                elif et == 'notification':
                    self.msg_view.appendPlainText(json.dumps(payload, ensure_ascii=False))
                elif et == 'call':
                    self.call_view.appendPlainText(json.dumps(payload, ensure_ascii=False))
                elif et == 'media':
                    self.phone_media_view.setPlainText(json.dumps(payload, indent=2, ensure_ascii=False))
                elif et == 'command_result':
                    self.log(f"Command result: {json.dumps(payload, ensure_ascii=False)[:300]}")
                elif et == 'phone_log':
                    self.log(f"Phone: {payload.get('message') or payload}")

            def _refresh_all(self):
                running = bool(self.server_thread and self.server_thread.is_alive() and not self.server_thread.error)
                self.status_pill.setText("Server running" if running else "Server stopped")
                self.card_server.value_label.setText(f"{self.cfg.get('listen_host')}:{self.cfg.get('port')}\nToken set: {'yes' if self.cfg.get('token') else 'no'}")
                addrs = core.lan_addresses() or ["(none detected)"]
                self.card_addrs.value_label.setText("\n".join(addrs))
                self.addrs_label.setText("\n".join(addrs))
                phone = self.state.phone
                self.card_phone.value_label.setText((phone.get('name') if phone else 'Not connected') + (f"\n{phone.get('model','')}" if phone else ""))
                self._refresh_commands_table(); self._refresh_files(); self._refresh_pc_media()

            def _refresh_screen(self):
                from PySide6 import QtGui, QtCore
                data = self.state.last_screen_jpeg
                if not data:
                    return
                pix = QtGui.QPixmap(); ok = pix.loadFromData(data)
                if not ok:
                    return
                scaled = pix.scaled(self.screen_label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                self.screen_label.setPixmap(scaled)

            def _send_phone_input(self, payload):
                self.state.publish(core.Event('phone_input', payload, source='pc').to_dict())
                self.log(f"Sent input: {payload}")

            def _send_custom_input(self):
                try:
                    payload = json.loads(self.input_json.toPlainText() or '{}')
                except Exception as e:
                    self.log(f'Invalid JSON: {e}'); return
                self._send_phone_input(payload)

            def _refresh_commands_table(self):
                cmds = self.state.saved_commands
                self.cmd_list.setRowCount(0)
                for cmd in cmds:
                    r = self.cmd_list.rowCount(); self.cmd_list.insertRow(r)
                    from PySide6 import QtWidgets
                    self.cmd_list.setItem(r,0,QtWidgets.QTableWidgetItem(str(cmd.get('name',''))))
                    self.cmd_list.setItem(r,1,QtWidgets.QTableWidgetItem(str(cmd.get('target',''))))
                    self.cmd_list.setItem(r,2,QtWidgets.QTableWidgetItem(str(cmd.get('action',''))))
                    self.cmd_list.setItem(r,3,QtWidgets.QTableWidgetItem(json.dumps(cmd.get('payload') or {}, ensure_ascii=False)))
                self.cmd_list.resizeColumnsToContents()

            def _add_command(self):
                name = self.cmd_name.text().strip()
                if not name:
                    self.log('Command name required'); return
                try:
                    payload = json.loads(self.cmd_payload.text().strip() or '{}')
                    if not isinstance(payload, dict): raise ValueError('payload must be object')
                except Exception as e:
                    self.log(f'Invalid payload JSON: {e}'); return
                cmd = {"id": core.make_id('cmd'), "name": name, "target": self.cmd_target.currentText(), "action": self.cmd_action.currentText(), "payload": payload}
                self.state.saved_commands.append(cmd)
                core.save_commands(self.state.saved_commands)
                self.cmd_name.clear(); self.cmd_payload.clear()
                self._refresh_commands_table(); self.log(f'Added command: {name}')

            def _selected_command(self):
                row = self.cmd_list.currentRow()
                if row < 0 or row >= len(self.state.saved_commands):
                    return None
                return self.state.saved_commands[row]

            def _remove_selected_command(self):
                row = self.cmd_list.currentRow()
                if row < 0: return
                cmd = self.state.saved_commands.pop(row)
                core.save_commands(self.state.saved_commands)
                self._refresh_commands_table(); self.log(f"Removed: {cmd.get('name')}")

            def _run_selected_command(self):
                cmd = self._selected_command()
                if not cmd: self.log('Select a command'); return
                target = cmd.get('target','phone')
                if target == 'phone':
                    self.state.publish(core.Event('run_command', {'command': cmd}, source='pc').to_dict())
                    self.log(f"Sent command to phone: {cmd.get('name')}")
                else:
                    if not self.cfg.get('allow_pc_command_exec', False):
                        self.log('PC command execution is disabled in Settings'); return
                    result = server.run_pc_command(cmd)
                    self.log(f"PC command result: {result}")

            def _push_commands(self):
                self.state.publish(core.Event('commands_sync', {'commands': self.state.saved_commands}, source='pc').to_dict())
                self.log('Pushed command list to phone')

            def _clipboard_push(self):
                text = self.clip_text.toPlainText()
                self.state.clipboard_text = text
                self.state.publish(core.Event('pc_clipboard', {'text': text}, source='pc').to_dict())
                self.log('Shared clipboard updated (sent to phone if connected)')

            def _clipboard_pull(self):
                self.clip_text.setPlainText(self.state.clipboard_text or '')
                self.log('Refreshed shared clipboard')

            def _clipboard_copy_local(self):
                from PySide6 import QtWidgets
                QtWidgets.QApplication.clipboard().setText(self.clip_text.toPlainText())
                self.log('Copied to local PC clipboard')

            def _refresh_files(self):
                self.files_received.clear(); self.files_out.clear()
                ddir = Path(self.cfg.get('download_dir') or core.DOWNLOAD_DIR)
                ddir.mkdir(parents=True, exist_ok=True)
                for p in sorted(ddir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:200]:
                    if p.is_file():
                        self.files_received.addItem(f"{p.name}  ({p.stat().st_size} bytes)")
                try:
                    for f in server.list_pc_outgoing(self.state):
                        self.files_out.addItem(f"{f['name']}  ({f['size']} bytes)")
                except Exception:
                    pass

            def _open_download_dir(self):
                ddir = Path(self.cfg.get('download_dir') or core.DOWNLOAD_DIR)
                ddir.mkdir(parents=True, exist_ok=True)
                import subprocess
                subprocess.Popen(['xdg-open', str(ddir)])

            def _add_outgoing_file(self):
                from PySide6 import QtWidgets
                path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select file to share to phone')
                if not path: return
                try:
                    meta = server.add_pc_outgoing(self.state, path)
                    self.log(f"Added outgoing file: {meta['name']}")
                    self._refresh_files()
                except Exception as e:
                    self.log(f'Failed to add file: {e}')

            def _pc_media(self, cmd):
                res = server.pc_media_command(cmd)
                self.log(f'PC media {cmd}: {res}')
                self._refresh_pc_media()

            def _refresh_pc_media(self):
                st = server.pc_media_status()
                if not st.get('available'):
                    self.pc_media_label.setText('playerctl not available (install playerctl for MPRIS control)')
                else:
                    self.pc_media_label.setText(f"{st.get('player','')} | {st.get('status','')} | {st.get('title','')} — {st.get('artist','')}")

            def _save_settings(self):
                self.cfg['device_name'] = self.set_name.text().strip() or (os.uname().nodename if hasattr(os,'uname') else 'pc')
                self.cfg['listen_host'] = self.set_host.text().strip() or '0.0.0.0'
                self.cfg['port'] = int(self.set_port.value())
                self.cfg['token'] = self.set_token.text().strip() or self.cfg.get('token') or core.generate_token()
                self.cfg['download_dir'] = self.set_download.text().strip() or str(core.DOWNLOAD_DIR)
                self.cfg['allow_pc_command_exec'] = bool(self.set_allow_exec.isChecked())
                core.save_config(self.cfg)
                self.state.config = self.cfg
                self.log('Settings saved (restart server to apply listen address/port changes)')
                self._refresh_all()

            def _regen_token(self):
                self.cfg['token'] = core.generate_token()
                self.set_token.setText(self.cfg['token'])
                self.log('Generated new token (save settings and re-pair phone)')

            def closeEvent(self, event):  # noqa: N802
                try:
                    self.state.bus.unsubscribe(self.ui_queue)
                except Exception:
                    pass
                if self.server_thread:
                    self.server_thread.stop()
                super().closeEvent(event)

        return _Window(config)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = core.load_config()
    if args.no_gui:
        print(json.dumps({"ok": True, "version": core.VERSION, "port": cfg.get("port")}))
        return 0
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    app.setApplicationName(core.APP_NAME)
    theme.apply(app)
    win = LanBridgeWindow(cfg)
    win.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
